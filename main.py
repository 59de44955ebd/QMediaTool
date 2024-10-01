"""
QMediaTool - Main class
"""

import json
from math import floor
import os
import sys
import re
import sqlite3
import time

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import QTcpServer, QHostAddress
from PyQt5 import uic, sip

from const import *

if IS_WIN:
    from PyQt5.QtWinExtras import QWinTaskbarButton
    import winreg
    from ctypes import windll, c_int, byref
    from ctypes.wintypes import HWND, DWORD, LPCVOID
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    windll.dwmapi.DwmSetWindowAttribute.argtypes = (HWND, DWORD, LPCVOID, DWORD)

from presets import PresetsManager
from task import Task
from myprocess import MyProcess


class Main (QMainWindow):

    ########################################
    #
    ########################################
    def __init__ (self):
        super().__init__()

        QApplication.setStyle('Fusion')

        self.setWindowTitle(APP_NAME)

        # load settings
        self._state = QSettings('fx', APP_NAME)

        # load theme
        theme = self._state.value('Theme', 'dark')
        if IS_WIN:
            # check system theme
            system_theme = 'default'
            try:
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize')
                if winreg.QueryValueEx(key, 'AppsUseLightTheme')[0] == 0:
                    system_theme = 'dark'
            except:
                pass
            # if system uses dark mode, overwrite stored setting
            if system_theme == 'dark':
                theme = 'dark'
        self.set_theme(theme == 'dark')

        self._outputSep = '-' * 80

        # load UI
        QResource.registerResource(os.path.join(RES_DIR, 'ui', 'res.rcc'))
        uic.loadUi(os.path.join(RES_DIR, 'ui', 'main.ui'), self)
        self.actionDarkTheme.setChecked(theme == 'dark')
        self.actionDarkTheme.toggled.connect(self.set_theme)

        # setup drop support
        self.setAcceptDrops(True)

        # defaults
        self._supported_file_extensions = []
        self._media_infos = {}
        self._duration = 0
        self._track_cnt = 0
        self._current_preset = None
        self._config_widgets = {}

        # set env vars
        os.environ['IS_WIN'] = 'true' if IS_WIN else 'false'
        os.environ['IS_MAC'] = 'true' if IS_MAC else 'false'
        os.environ['IS_LINUX'] = 'true' if IS_LINUX else 'false'
        if IS_WIN:
            os.environ['TMPDIR'] = os.environ['TMP'] + '\\'

        self.setup_tool_env_vars()

        # single file mode
        self.pushButtonInputSelect.released.connect(self.slot_input_select)
        # URL mode
        self.lineEditURL.textEdited.connect(self.slot_url_edited)
        # multi file mode
        self.groupBoxInputs.hide()
        self.listWidgetInput.setDragDropMode(QAbstractItemView.InternalMove)
        self.listWidgetInput.currentRowChanged.connect(self.slot_input_current_row_changed)
        self.pushButtonInputAdd.released.connect(self.slot_input_select)
        self.pushButtonInputDelete.released.connect(self.slot_input_delete)
        self.pushButtonInputClear.released.connect(self.slot_input_clear)
        # other buttons
        self.pushButtonOutputFolder.released.connect(self.slot_set_output_folder)
        self.pushButtonRunTask.released.connect(self.slot_run_task)
        self.pushButtonStopTask.released.connect(self.slot_stop_task)

        # config widgets
        self.groupBoxArguments.hide()

        # task queue
        self.pushButtonAddTaskToQueue.released.connect(self.slot_add_task_to_queue)
        self.taskManager.statusMessage.connect(self.msg)
        self.taskManager.outputMessage.connect(self.out)
        self.taskManager.outputClear.connect(self.plainTextEditOutput.clear)
        self.taskManager._proc.errorOccurred.connect(self.slot_error_occurred)
        self.taskManager.pushButtonTaskAdd.released.connect(lambda: self.tabWidget.setCurrentIndex(0))

        self.setup_menu_actions()

        self.treeWidgetPresets.itemDoubleClicked.connect(self.slot_preset_double_clicked)
        self.treeWidgetPresets.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeWidgetPresets.customContextMenuRequested.connect(self.slot_preset_context_menu)

        # get available devices and codecs from ffmpeg
        self.load_devices()
        self.load_codecs()

        # load presets DB
        self._presets_db = sqlite3.connect(DATA_DIR + '/presets.db')
        self._presets_db.row_factory = sqlite3.Row
        # check if tables exist, otherwise create them
        c = self._presets_db.cursor()
        sql = "SELECT * FROM sqlite_master WHERE type='table' AND name='categories'"
        c.execute(sql)
        res = c.fetchone()
        if not res:
            sql = "CREATE TABLE categories(id INTEGER PRIMARY KEY, name TEXT)"
            c.execute(sql)
            self._presets_db.commit()
        sql = "SELECT * FROM sqlite_master WHERE type='table' AND name='presets'"
        c.execute(sql)
        res = c.fetchone()
        if not res:
            sql = """
            CREATE TABLE presets(id INTEGER PRIMARY KEY, category_id INTEGER, name TEXT, desc TEXT, cmd TEXT,
            ext TEXT NOT NULL DEFAULT '*', input_type INTEGER NOT NULL DEFAULT 0)
            """
            c.execute(sql)
            self._presets_db.commit()
        last_preset_id = int(self._state.value('LastSession/LastPreset', 0))
        self.load_presets(last_preset_id)

        self._preset_manager = PresetsManager(self, self._presets_db)
        self._preset_manager.presetChanged.connect(self.load_presets)
        self._preset_manager.message.connect(self.msg)
        self._preset_manager.error.connect(self.err)

        # setup process
        self._proc = MyProcess()
        self._proc.readyReadStandardOutput.connect(self.slot_stdout)
        self._proc.readyReadStandardError.connect(self.slot_stderr)
        self._proc.finished.connect(self.slot_complete)
        self._proc.errorOccurred.connect(self.slot_error_occurred)

        # restore window settings
        val = self._state.value('MainWindow/Geometry')
        if val:
            self.restoreGeometry(val)
        val = self._state.value('MainWindow/State')
        if val:
            self.restoreState(val)
        # LastOutputDir
        d = self._state.value('LastSession/LastOutputDir', '')
        if d == '' or not os.path.isdir(d):
            if os.path.isdir(DATA_DIR + '/output'):
                d = DATA_DIR + '/output'
            else:
                d = DATA_DIR
        self.lineEditOutputFolder.setText(d)

        # tcp server for ffmpeg progress updates
        self._progressBar = QProgressBar(self.statusBar)
        self._progressBar.setAlignment(Qt.AlignHCenter)
        self.statusBar.addPermanentWidget(self._progressBar)
        self._server = QTcpServer(self)
        self._server.listen(QHostAddress.LocalHost, 9999)
        self._server.newConnection.connect(self.slot_new_connection)
        self._socket = None

        self.treeWidgetPresets.setFocus()

        self.show()

        if IS_WIN:
            # setup tray icon
            menu_tray = QMenu(self)
            action = QAction(menu_tray)
            action.setText('&Quit')
            action.triggered.connect(self.close)
            menu_tray.addAction(action)
            self._trayIcon = QSystemTrayIcon(self.windowIcon(), self)
            self._trayIcon.setToolTip(APP_NAME)
            self._trayIcon.activated.connect(self.slot_activated)
            self._trayIcon.setContextMenu(menu_tray)

            # taskbar progress
            self._taskBarButton = QWinTaskbarButton(self)
            self._taskBarButton.setWindow(self.windowHandle())
            self._taskBarProgress = self._taskBarButton.progress()

        if len(sys.argv) > 1:
            self.set_input_item(sys.argv[1])

    ########################################
    #
    ########################################
    def set_theme (self, is_dark):
        if IS_WIN:
            windll.dwmapi.DwmSetWindowAttribute(int(self.winId()), 20, byref(c_int(int(is_dark))), 4)
        pal = QPalette()
        if is_dark:
            pal.setColor(QPalette.Window, QColor('#353535'))
            pal.setColor(QPalette.WindowText, Qt.white)
            pal.setColor(QPalette.Disabled, QPalette.WindowText, QColor('#7F7F7F'))
            pal.setColor(QPalette.Base, QColor('#2A2A2A'))
            pal.setColor(QPalette.AlternateBase, QColor('#424242'))
            pal.setColor(QPalette.ToolTipBase, Qt.white)
            pal.setColor(QPalette.ToolTipText, Qt.white)
            pal.setColor(QPalette.Text, Qt.white)
            pal.setColor(QPalette.Disabled, QPalette.Text, QColor('#7F7F7F'))
            pal.setColor(QPalette.Dark, QColor('#232323'))
            pal.setColor(QPalette.Shadow, QColor('#141414'))
            pal.setColor(QPalette.Button, QColor('#353535'))
            pal.setColor(QPalette.ButtonText, Qt.white)
            pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor('#7F7F7F'))
            pal.setColor(QPalette.BrightText, Qt.red)
            pal.setColor(QPalette.Link, QColor('#2A82DA'))
            pal.setColor(QPalette.Highlight, QColor('#2A82DA'))
            pal.setColor(QPalette.Disabled, QPalette.Highlight, QColor('#505050'))
            pal.setColor(QPalette.HighlightedText, Qt.white)
            pal.setColor(QPalette.Disabled, QPalette.HighlightedText, QColor('#7F7F7F'))
            with open(os.path.join(RES_DIR, 'styles', 'dark.css'), 'r') as f:
                qss = f.read()
        else:
            with open(os.path.join(RES_DIR, 'styles', 'default.css'), 'r') as f:
                qss = f.read()
        qApp.setPalette(pal)

        if IS_WIN:
            qss += 'QPlainTextEdit, QLabel#labelNotes{font-family: Consolas,"Courier New";}'
        elif IS_MAC:
            qss += 'QPlainTextEdit, QLabel#labelNotes{font-family: Menlo,Courier;}'
        else:
            qss += 'QPlainTextEdit, QLabel#labelNotes{font-family: "Noto Sans Mono","DejaVu Sans Mono",Courier;}'

        qApp.setStyleSheet(qss)
        self._state.setValue('Theme', 'dark' if is_dark else 'default')

    ########################################
    #
    ########################################
    def delete_layout(self, cur_lay):
        if cur_lay is not None:
            while cur_lay.count():
                item = cur_lay.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.delete_layout(item.layout())
            sip.delete(cur_lay)

    ########################################
    #
    ########################################
    def select_preset (self, preset_id):
        c = self._presets_db.cursor()
        sql = """
        SELECT presets.*,categories.name AS category FROM presets
        LEFT JOIN categories ON presets.category_id=categories.id WHERE presets.id=?
        """
        c.execute(sql, (preset_id,))
        preset = c.fetchone()
        if preset is None:
            return
        self._current_preset = dict(preset)
        self.lineEditPreset.setText(preset['name'])

        # test
        layout = self.groupBoxArguments.layout()
        if layout:
            self.delete_layout(layout)

        vars_found = []
        for c in CONFIG_VARS:
            flag = '$' + c.upper() in preset['cmd'] or '${' + c.upper() + '}' in preset['cmd']
            if flag:
                vars_found.append(c)

        self._config_widgets = {}
        if vars_found:
            layout = QGridLayout(self.groupBoxArguments)
            for c in vars_found:
                self.add_config_widget(layout, c)
            layout.setColumnStretch(layout.columnCount(), 1)
            self.groupBoxArguments.setVisible(True)
        else:
            self.groupBoxArguments.setVisible(False)

        # show input widgets according to input mode
        if preset['input_type'] == INPUT_TYPE_FILE:
            self.groupBoxInput.show()
            self.groupBoxURL.hide()
            self.groupBoxInputs.hide()
        elif preset['input_type'] == INPUT_TYPE_FILES:
            self.groupBoxInput.hide()
            self.groupBoxURL.hide()
            self.groupBoxInputs.show()
        elif preset['input_type'] == INPUT_TYPE_URL:
            self.groupBoxInput.hide()
            self.groupBoxURL.show()
            self.groupBoxInputs.hide()
        elif preset['input_type'] == INPUT_TYPE_NONE:
            self.groupBoxInput.hide()
            self.groupBoxURL.hide()
            self.groupBoxInputs.hide()
        # notes
        self.labelNotes.setText(preset['notes'])
        # code
        self.plainTextEditCommandLine.setPlainText(preset['cmd'])
        # extensions
        if preset['ext'] != '':
            self.lineEditExtensions.setText(preset['ext'])
            self._supported_file_extensions = preset['ext'].split(',')
        else:
            self.lineEditExtensions.setText('')
            self._supported_file_extensions = []
        # check if currently selected file(s) are compatible with new preset
        if len(self._supported_file_extensions) > 0:
            if preset['input_type'] == INPUT_TYPE_FILES:
                unsupported = []
                cnt = self.listWidgetInput.count()
                for i in range(cnt):
                    inputFile = self.listWidgetInput.item(i).text()
                    ext = os.path.splitext(inputFile)[1][1:]
                    if not ext in self._supported_file_extensions:
                        unsupported.append(i)
                cnt = len(unsupported)
                if cnt > 0:
                    dialog = QMessageBox(QMessageBox.Warning, 'Incompatible Extension',
                            f'The extension of {cnt} currently selected file(s) is not compatible with new preset.\nRemove those files?',
                            QMessageBox.Yes | QMessageBox.No, self)
                    if IS_WIN and self.actionDarkTheme.isChecked():
                        windll.dwmapi.DwmSetWindowAttribute(int(dialog.winId()), 20, byref(c_int(1)), 4)
                    if dialog.exec() == QMessageBox.Yes:
                        for i in range(cnt, 0, -1):
                            row = unsupported[i]
                            fn = self.listWidgetInput.item(row).text()
                            del self._media_infos[fn]
                            self.listWidgetInput.takeItem(row)
            elif preset['input_type'] == INPUT_TYPE_FILE:
                inputFile = self.lineEditInput.text()
                if inputFile != '':
                    ext = os.path.splitext(inputFile)[1][1:]
                    if not ext in self._supported_file_extensions:
                        dialog = QMessageBox(QMessageBox.Warning, 'Incompatible Extension',
                                'The currently selected file\'s extension is not compatible with new preset.\nRemove file?',
                                QMessageBox.Yes | QMessageBox.No, self)
                        if IS_WIN and self.actionDarkTheme.isChecked():
                            windll.dwmapi.DwmSetWindowAttribute(int(dialog.winId()), 20, byref(c_int(1)), 4)
                        if dialog.exec() == QMessageBox.Yes:
                            self.lineEditInput.setText('')
                            self._media_infos = {}
        # update infos
        if self._current_preset['input_type'] == INPUT_TYPE_FILES:
            if len(self._media_infos.values()):
                self.listWidgetInput.setCurrentRow(0)
                self.show_mediainfo(list(self._media_infos.values())[0])
            else:
                self.plainTextEditInfos.setPlainText('')
        elif self._current_preset['input_type'] == INPUT_TYPE_FILE:
            if len(self._media_infos.values()):
                self.show_mediainfo(list(self._media_infos.values())[0])
            else:
                self.plainTextEditInfos.setPlainText('')
        else:
            self.plainTextEditInfos.setPlainText('')
        self.checkBoxOutputFolderInput.setEnabled(preset['input_type'] == INPUT_TYPE_FILE or
                preset['input_type'] == INPUT_TYPE_FILES)
        self.lineEditOutputFolder.setEnabled(not self.checkBoxOutputFolderInput.isEnabled() or
                not self.checkBoxOutputFolderInput.isChecked())
        self.pushButtonOutputFolder.setEnabled(not self.checkBoxOutputFolderInput.isEnabled() or
                not self.checkBoxOutputFolderInput.isChecked())
        # enable/disable AddTask/run_task buttons according to preset's input type
        if preset['input_type'] == INPUT_TYPE_FILE:
            isIncomplete = self.lineEditInput.text() == ''
        elif preset['input_type'] == INPUT_TYPE_FILES:
            isIncomplete = self.listWidgetInput.count() == 0
        elif preset['input_type'] == INPUT_TYPE_URL:
            isIncomplete = not '://' in self.lineEditURL.text()
        elif preset['input_type'] == INPUT_TYPE_NONE:
            isIncomplete = False
        self.pushButtonAddTaskToQueue.setDisabled(isIncomplete)
        self.pushButtonRunTask.setDisabled(isIncomplete)

    ########################################
    #
    ########################################
    def add_config_widget(self, layout, c):
        cnt = layout.columnCount()
        widget = None

        if c in ('DeviceVideo', 'DeviceAudio',
                'Container', 'ContainerVideo', 'ContainerAudio', 'ContainerImage',
                'CodecVideo', 'CodecAudio',
                'Preset', 'BitrateVideo', 'BitrateAudio'):
            widget = QComboBox(self)

            if c == 'DeviceVideo':
                for dev in self._devices_video:
                    widget.addItem(dev)
            elif c == 'DeviceAudio':
                for dev in self._devices_audio:
                    widget.addItem(dev)

            elif c == 'Container':
                for container in CONTAINERS:
                    widget.addItem(container)
            elif c == 'ContainerVideo':
                for container in CONTAINERS_VIDEO:
                    widget.addItem(container)
            elif c == 'ContainerAudio':
                for container in CONTAINERS_AUDIO:
                    widget.addItem(container)
            elif c == 'ContainerImage':
                for container in CONTAINERS_IMAGE:
                    widget.addItem(container)

            elif c == 'CodecVideo':
                widget.addItem('copy')
                widget.insertSeparator(1)
                for codec in self._codecs_video:
                    widget.addItem(codec)

            elif c == 'CodecAudio':
                widget.addItem('copy')
                widget.insertSeparator(1)
                for codec in self._codecs_audio:
                    widget.addItem(codec)

            elif c == 'Preset':
                for preset in PRESETS:
                    widget.addItem(preset)

            elif c == 'BitrateVideo':
                for v in [256, 512, 1000, 2000, 3000, 4000, 5000, 6000]:
                    widget.addItem(str(v) + 'k')

            elif c == 'BitrateAudio':
                for v in [32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]:
                    widget.addItem(str(v) + 'k')

            if c in DEFAULTS:
                widget.setCurrentText(DEFAULTS[c])

        elif c in ('Track', 'Crf'):
            widget = QSpinBox(self)
            if c in DEFAULTS:
                widget.setValue(DEFAULTS[c])

        elif c in ('Start', 'Duration', 'End'):
            widget = QTimeEdit(self)
            widget.setDisplayFormat('HH:mm:ss.zzz')

        elif c in ('Fps',):
            widget = QDoubleSpinBox(self)
            if c in DEFAULTS:
                widget.setValue(DEFAULTS[c])

        if widget:
            label = QLabel((LABELS[c] if c in LABELS else c) + ':', self)
            layout.addWidget(label, 0, cnt)
            layout.addWidget(widget, 1, cnt)
            self._config_widgets[c] = widget
        else:
            print('MISSING', c)

    ########################################
    #
    ########################################
    def load_presets (self, selectID=0):
        selectedItem = None
        self.treeWidgetPresets.clear()
        c = self._presets_db.cursor()
        sql = "SELECT * FROM categories ORDER BY name"
        c.execute(sql)
        for row in c.fetchall():
            cat = row['name']
            catItem = QTreeWidgetItem()
            catItem.setText(0, cat)
            catItem.setData(0, Qt.UserRole, 0)
            catItem.setData(0, Qt.UserRole + 1, row['id'])
            self.treeWidgetPresets.addTopLevelItem(catItem)
            sql = "SELECT * FROM presets WHERE category_id=? ORDER BY name"
            c.execute(sql, (row['id'],))
            presetItems = []
            for row2 in c.fetchall():
                presetItem = QTreeWidgetItem()
                presetItem.setText(0, row2['name'])
                presetItem.setData(0, Qt.UserRole, 1)
                presetItem.setData(0, Qt.UserRole + 1, row2['id'])
                presetItem.setToolTip(0, row2['name'])
                presetItems.append(presetItem)
                if row2['id'] == selectID:
                    selectedItem = presetItem
            catItem.addChildren(presetItems)
        if selectedItem is not None:
            self.treeWidgetPresets.setCurrentItem(selectedItem)
            self.select_preset(selectID)

    ########################################
    #
    ########################################
    def load_devices (self):
        self._devices_video = []
        self._devices_audio = []
        if IS_WIN or IS_MAC:
            task = Task('$FFMPEG -hide_banner -list_devices true -f dshow -i dummy'
                    if IS_WIN else '$FFMPEG -hide_banner -list_devices true -f avfoundation -i /dev/null')
            proc = QProcess()
            task.run(proc)
            proc.waitForFinished(-1)
            lines = proc.readAllStandardError().data().decode(errors='ignore').rstrip().splitlines()
            if IS_WIN:
                re_vid = re.compile(r'^\[[^\]]*\] "(.*)" \(video\)')
                re_aud = re.compile(r'^\[[^\]]*\] "(.*)" \(audio\)')
                for line in lines:
                    res = re.search(re_vid, line)
                    if res:
                        self._devices_video.append(res.group(1))
                    res = re.search(re_aud, line)
                    if res:
                        self._devices_audio.append(res.group(1))
            else:
                re_dev = re.compile(r'^\[[^\]]*\] (.*)')
                for line in lines:
                    res = re.search(re_dev, line)
                    if res:
                        line = res.group(1)
                        if line.startswith('AVFoundation video'):
                            current_list = self._devices_video
                        elif line.startswith('AVFoundation audio'):
                            current_list = self._devices_audio
                        elif line.startswith('['):
                            current_list.append(line[line.index(']') + 2:])
#        TODO: Linux
#        else:
#            $FFMPEG -hide_banner -list_devices true -f openal -i /dev/null
#            [openal @ 0x55b9dc490e00] List of OpenAL capture devices on this system:
#            [openal @ 0x55b9dc490e00]   ES1371/ES1373 / Creative Labs CT2518 (Audio PCI 64V/128/5200 / Creative CT4810/CT5803/CT5806 [Sound Blaster PCI]) Analog Stereo
#            [openal @ 0x55b9dc490e00]   Monitor of ES1371/ES1373 / Creative Labs CT2518 (Audio PCI 64V/128/5200 / Creative CT4810/CT5803/CT5806 [Sound Blaster PCI]) Analog Stereo
#            /dev/null: Immediate exit requested

    ########################################
    #
    ########################################
    def load_codecs (self):
        task = Task('$FFMPEG -hide_banner -encoders')
        proc = QProcess()
        task.run(proc)
        proc.waitForFinished(-1)
        lines = proc.readAllStandardOutput().data().decode(errors='ignore').rstrip().splitlines()
        lines = lines[lines.index(' ------') + 1:]
#        print(lines)
        self._codecs_video = list(sorted(l.split(' ')[2] for l in lines if l.startswith(' V')))
        self._codecs_audio = list(sorted(l.split(' ')[2] for l in lines if l.startswith(' A')))

    ########################################
    # Connect menu actions
    ########################################
    def setup_menu_actions (self):
        self._actions = {}
        actions = self.findChildren(QAction)
        for a in actions:
            p = a.objectName()
            if p != '':
                self._actions[p] = a
        # File
        self._actions['actionNewPresetCategory'].triggered.connect(self.slot_add_category)
        self._actions['actionNewPreset'].triggered.connect(self.slot_add_preset)
        # View
        self._actions['actionTaskEditor'].triggered.connect(lambda: self.tabWidget.setCurrentIndex(0))
        self._actions['actionTaskQueue'].triggered.connect(lambda: self.tabWidget.setCurrentIndex(1))
        self._actions['actionOutputLog'].triggered.connect(lambda: self.tabWidget.setCurrentIndex(2))
        # Help
        self._actions['actionHelp'].triggered.connect(self.slot_help)
        self._actions['actionAbout'].triggered.connect(self.slot_about)

    ########################################
    # Sets environment variables for all binary modules in folder 'bin'
    ########################################
    def setup_tool_env_vars (self):
        modules = os.listdir(BIN_DIR)
        for m in modules:
            if m.startswith('_'):
                continue
            p = BIN_DIR + '/' + m + '/' + m
            if ' ' in p:
                p = '"' + p + '"'
            os.environ[m.upper()] = p

    ########################################
    # Single file mode - sets file
    ########################################
    def set_input_item (self, fn):
        if not os.path.isfile(fn):
            return False
        if len(self._supported_file_extensions) > 0:
            ext = os.path.splitext(fn)[1][1:]
            if not ext in self._supported_file_extensions:
                dialog = QMessageBox(QMessageBox.Warning, 'Incompatible Extension',
                        'The selected file\'s extension is not compatible with current preset.\nAdd file anyway?',
                        QMessageBox.Yes | QMessageBox.No, self)
                if IS_WIN and self.actionDarkTheme.isChecked():
                    windll.dwmapi.DwmSetWindowAttribute(int(dialog.winId()), 20, byref(c_int(1)), 4)
                if dialog.exec() != QMessageBox.Yes:
                    return False  # discard loading
        info = self.get_mediainfo(fn)
        if info is None:
            return False
        # activate buttons
        self.pushButtonAddTaskToQueue.setDisabled(False)
        self.pushButtonRunTask.setDisabled(False)
        self._media_infos = {fn: info}
        self.lineEditInput.setText(fn)
        self.show_mediainfo(info)
        return True

    ########################################
    # Multiple file mode - adds file
    ########################################
    def add_input_item (self, fn):
        if os.path.isfile(fn):
            if len(self._supported_file_extensions) > 0:
                ext = os.path.splitext(fn)[1][1:]
                if not ext in self._supported_file_extensions:
                    dialog = QMessageBox(QMessageBox.Warning, 'Incompatible Extension',
                            'The selected file\'s extension is not compatible with current preset.\nAdd file anyway?',
                            QMessageBox.Yes | QMessageBox.No, self)
                    if IS_WIN and self.actionDarkTheme.isChecked():
                        windll.dwmapi.DwmSetWindowAttribute(int(dialog.winId()), 20, byref(c_int(1)), 4)
                    if dialog.exec() != QMessageBox.Yes:
                        return False  # discard loading
            self.listWidgetInput.addItem(fn)
            info = self.get_mediainfo(fn)
            if info is None:
                return False
            # activate buttons
            self.pushButtonAddTaskToQueue.setDisabled(False)
            self.pushButtonRunTask.setDisabled(False)
            self._media_infos[fn] = info
        else:
            l = os.listdir(fn)
            for f in l:
                self.add_input_item(fn + '/' + f)
        return True

    ########################################
    # Returns media info as dict
    ########################################
    def get_mediainfo (self, fn):
        task = Task(f'$MEDIAINFO --Output=JSON "{fn}"')
        proc = QProcess()
        task.run(proc)
        proc.waitForFinished(-1)
        res = proc.readAllStandardOutput().data().decode(errors='ignore')
        info = json.loads(res)['media']
        info['general'] = info['track'][0]
        del info['track'][0]
        return info

    ########################################
    # Creates and returns a new task based on current settings
    ########################################
    def get_task (self):
        env = {}
        if self._current_preset['input_type'] == INPUT_TYPE_FILE or self._current_preset['input_type'] == INPUT_TYPE_URL:
            trackNum = self._config_widgets['Track'].value() if 'Track' in self._config_widgets else 0
            if self._current_preset['input_type'] == INPUT_TYPE_FILE:
                inputFile = self.lineEditInput.text()
                f, ext = os.path.splitext(inputFile)
                env['INPUT'] = inputFile
                env['INPUTDIR'] = os.path.dirname(f)
                env['INPUTBASENAME'] = os.path.basename(f).replace(' ', '_')
                env['INPUTEXT'] = ext[1:]
                # variables for tracks
                tracks = list(self._media_infos.values())[0]['track']
                for i in range(len(tracks)):
                    track = tracks[i]
                    if 'Format' in track:
                        env['FORMAT' + str(i)] = track['Format']
                    if 'FrameRate' in track:
                        env['FPS' + str(i)] = float(track['FrameRate'])
                # variables for currently selected track
                track = tracks[trackNum]  # -1
                if 'Format' in track:
                    env['FORMAT'] = track['Format']
            else:
                env['URL'] = self.lineEditURL.text()
            # arguments variables
            if 'Track' in self._config_widgets:
                env['TRACK'] = str(trackNum)  # -1
        elif self._current_preset['input_type'] == INPUT_TYPE_FILES:
            cnt = self.listWidgetInput.count()
            if cnt==0:
                return
            env['CNT'] = str(cnt)
            inputFile = self.listWidgetInput.item(0).text()
            f, ext = os.path.splitext(inputFile)
            env['INPUTEXT'] = ext[1:]
            env['INPUTBASENAME'] = os.path.basename(f).replace(' ', '_')
            for i in range(cnt):
                inputFile = self.listWidgetInput.item(i).text()
                env['INPUT' + str(i)] = inputFile
        # general variables
        # env['LANG'] = 'C.UTF-8'

        if 'Start' in self._config_widgets:
            env['START'] = self._time_to_sec(self._config_widgets['Start'].time())
        if 'End' in self._config_widgets:
            env['END'] = self._time_to_sec(self._config_widgets['End'].time())
        if 'Duration' in self._config_widgets:
            env['DURATION'] = self._time_to_sec(self._config_widgets['Duration'].time())
        if 'Container' in self._config_widgets:
            env['CONTAINER'] = self._config_widgets['Container'].currentText()
        if 'ContainerVideo' in self._config_widgets:
            env['CONTAINERVIDEO'] = self._config_widgets['ContainerVideo'].currentText()
        if 'ContainerAudio' in self._config_widgets:
            env['CONTAINERAUDIO'] = self._config_widgets['ContainerAudio'].currentText()
        if 'ContainerImage' in self._config_widgets:
            env['CONTAINERIMAGE'] = self._config_widgets['ContainerImage'].currentText()
        if 'CodecVideo' in self._config_widgets:
            env['CODECVIDEO'] = self._config_widgets['CodecVideo'].currentText()
        if 'BitrateVideo' in self._config_widgets:
            env['BITRATEVIDEO'] = self._config_widgets['BitrateVideo'].currentText()
        if 'CodecAudio' in self._config_widgets:
            env['CODECAUDIO'] = self._config_widgets['CodecAudio'].currentText()
        if 'BitrateAudio' in self._config_widgets:
            env['BITRATEAUDIO'] = self._config_widgets['BitrateAudio'].currentText()
        if 'Preset' in self._config_widgets:
            env['PRESET'] = self._config_widgets['Preset'].currentText()
        if 'Fps' in self._config_widgets:
            env['FPS'] = str(self._config_widgets['Fps'].value())
        if 'Crf' in self._config_widgets:
            env['CRF'] = str(self._config_widgets['Crf'].value())

        if 'DeviceVideo' in self._config_widgets:
            env['DEVICEVIDEO'] = self._config_widgets['DeviceVideo'].currentText() if IS_WIN else self._config_widgets['DeviceVideo'].currentIndex()
        if 'DeviceAudio' in self._config_widgets:
            env['DEVICEAUDIO'] = self._config_widgets['DeviceAudio'].currentText() if IS_WIN else self._config_widgets['DeviceAudio'].currentIndex()

        if self.checkBoxOutputFolderInput.isEnabled() and self.checkBoxOutputFolderInput.isChecked():
            if self._current_preset['input_type'] == INPUT_TYPE_FILE:
                env['OUTPUTDIR'] = os.path.dirname(self.lineEditInput.text())
            elif self._current_preset['input_type'] == INPUT_TYPE_FILES: # multiple
                env['OUTPUTDIR'] = os.path.dirname(self.listWidgetInput.item(0).text())
        else:
            env['OUTPUTDIR'] = self.lineEditOutputFolder.text()
        env['TIMESTAMP'] = time.strftime("%Y%m%d_%H%M%S")
        task = Task(self.plainTextEditCommandLine.toPlainText().strip(' \t\n'), env,
                self._current_preset['name'])
        return task

    ########################################
    #
    ########################################
    def run_task (self, task):
        self.msg('Task running...')
        #self._progressBar.setValue(0)
        if IS_WIN:
            self._taskBarProgress.setValue(0)
            self._taskBarProgress.setVisible(True)

        task.run(self._proc)

    ########################################
    #
    ########################################
    def _ms_to_time (self, ms):
        ms = floor(ms)
        s = ms // 1000
        ms = ms % 1000
        m = s // 60
        s = s % 60
        h = m // 60
        m = m % 60
        return QTime(h, m, s, ms)

    ########################################
    #
    ########################################
    def _time_to_ms (self, t):
        return t.msec() + 1000 * t.second() + 60000 * t.minute() + 3600000 * t.hour()

    ########################################
    #
    ########################################
    def _time_to_sec (self, t):
        return t.msec() / 1000 + t.second() + 60 * t.minute() + 3600 * t.hour()

    ########################################
    # Displays media infos for current file
    ########################################
    def show_mediainfo (self, info):
        # update track spinBox
        self._track_cnt = len(info['track']) if 'track' in info else 0
        if 'Track' in self._config_widgets:
            self._config_widgets['Track'].setRange(0, self._track_cnt - 1)
            self._config_widgets['Track'].setValue(0)

        # update infos
        fmt = info['general']['Format'] if 'Format' in info['general'] else '-'
        s = f'Format: {fmt}\n'

        # update start and duration widgets
        if 'Duration' in info['general']:
            self._duration = float(info['general']['Duration']) * 1000
            t = self._ms_to_time(self._duration)
            if 'Start' in self._config_widgets:
                self._config_widgets['Start'].setMaximumTime(t)
            if 'Duration' in self._config_widgets:
                self._config_widgets['Duration'].setMaximumTime(t)
                self._config_widgets['Duration'].setTime(t)
            if 'End' in self._config_widgets:
                self._config_widgets['End'].setMaximumTime(t)
            s += f'Duration: {t.toString("hh:mm:ss.zzz")}\n'
        else:
            self._duration = 0

        s += f'{len(info["track"])} Tracks:'
        try:
            tracks = sorted(info['track'], key=lambda x: x['ID'])
        except:
            tracks = info['track']
        for i in range(len(tracks)):
            track = tracks[i]
            s += f'\nTrack {i}: Type = {track["@type"]}'
            if 'Format' in track:
                s += f', Format = {track["Format"]}'
                if 'Format_Info' in track:
                    s += f' ({track["Format_Info"]})'
        self.plainTextEditInfos.setPlainText(s)

    ########################################
    # Shows status info in status bar
    ########################################
    def msg (self, s, forceRepaint=False):
        self.statusBar.showMessage(s) #--, 5000)
        if forceRepaint:
            self.statusBar.repaint()

    ########################################
    # Shows error message in status bar
    ########################################
    def err (self, s):
        self.statusBar.showMessage('Error: ' + s)

    ########################################
    # Appends text to Output Log
    ########################################
    def out (self, s):
        self.plainTextEditOutput.appendPlainText(s)
        self.plainTextEditOutput.ensureCursorVisible()

    ########################################
    #
    ########################################
    def changeEvent (self, e):
        if IS_WIN and self.isMinimized():
            self._trayIcon.show()
            self.hide()

    ########################################
    #
    ########################################
    def closeEvent (self, e):
        self.slot_quit()

    ########################################
    #
    ########################################
    def dragEnterEvent (self, e):
        if e.mimeData().hasUrls():
            e.accept()

    ########################################
    #
    ########################################
    def dropEvent (self, e):
        if self._current_preset and (self._current_preset['input_type'] == INPUT_TYPE_URL or self._current_preset['input_type'] == INPUT_TYPE_NONE):
            return
        for u in e.mimeData().urls():
            fn = u.toLocalFile()
            if self._current_preset and self._current_preset['input_type'] == INPUT_TYPE_FILE:
                self.set_input_item(fn)
                break
            else:
                self.add_input_item(fn)

    ########################################
    #
    ########################################
    def slot_activated (self, activationReason):
        if activationReason == QSystemTrayIcon.Trigger:
            self.setWindowState((self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive)
            self.show()
            self.activateWindow()
            self._trayIcon.hide()

    ########################################
    #
    ########################################
    def slot_error_occurred (self, err):
        self.pushButtonRunTask.setDisabled(False)
        self.pushButtonStopTask.setDisabled(True)
        self.msg('An error occured')
        if err == QProcess.FailedToStart:
            msg = 'The process failed to start. Either the invoked program is missing, or you may have insufficient permissions to invoke the program.'
        elif err == QProcess.Crashed:
            msg = 'The process crashed some time after starting successfully.'
        elif err == QProcess.Timedout:
            msg = 'The last waitFor...() function timed out. The state of QProcess is unchanged, and you can try calling waitFor...() again.'
        elif err == QProcess.WriteError:
            msg = 'An error occurred when attempting to write to the process. For example, the process may not be running, or it may have closed its input channel.'
        elif err == QProcess.ReadError:
            msg = 'An error occurred when attempting to read from the process. For example, the process may not be running.'
        else:
            msg = 'An unknown error occurred. This is the default return value of error().'
        self.out(msg)
        self.tabWidget.setCurrentIndex(2) # ???

    ########################################
    #
    ########################################
    def slot_stdout (self):
        s = self._proc.readAllStandardOutput().data().decode(errors='ignore').strip(' \n\r')

        # remove false UTF-8 BOM (needed for AtomicParsely)
#        if s.startswith('ï»¿'):
#            s = s[3:]

        for l in s.splitlines():
            l = l.strip()
            self.out(l)
            try:
                prog = int(l.split()[1][:-1])
                self._progressBar.setValue(prog)
                if IS_WIN:
                    self._taskBarProgress.setValue(prog)
            except:
                pass

       # self.out(s)

    ########################################
    #
    ########################################
    def slot_stderr (self):
        s = self._proc.readAllStandardError().data().decode(errors='ignore').strip(' \n\r')
        self.out(s)

    ########################################
    #
    ########################################
    def slot_complete (self, exitCode, exitStatus):
        self._task = None
        if exitCode == 0:
            msg = 'Task successfully executed'
        else:
            msg = 'Error: Task execution failed'
            self.tabWidget.setCurrentIndex(2)
        self.msg(msg)
        #self.out(msg)
        self.out('\nDone.')
        self.pushButtonRunTask.setDisabled(False)
        self.pushButtonStopTask.setDisabled(True)

#        time.sleep(0.25)
#        self._progressBar.reset()
#        if IS_WIN:
#            self._taskBarProgress.setVisible(False)

        QTimer.singleShot(500, lambda:
            self._progressBar.reset() or (self._taskBarProgress.setVisible(False) if IS_WIN else None))

    ########################################
    #
    ########################################
    def slot_input_current_row_changed (self):
        row = self.listWidgetInput.currentRow()
        if row < 0:
            self.plainTextEditInfos.setPlainText('')
        else:
            fn = self.listWidgetInput.item(row).text()
            info = self._media_infos[fn]
            self.show_mediainfo(info)

    ########################################
    #
    ########################################
    def slot_input_select (self):
        fltr = ''
        if len(self._supported_file_extensions) > 0:
            fltr = 'Supported Files ('
            for ext in self._supported_file_extensions:
                fltr += '*.'+ext+' '
            fltr = fltr[:-1]
            fltr += ');;'
        fltr += 'All Files (*.*)'
        if self._current_preset['input_type'] == INPUT_TYPE_FILE:
            fn, _ = QFileDialog.getOpenFileName(self, 'Select Input File', DATA_DIR, fltr)
            if fn == '':
                return
            self.set_input_item(os.path.normpath(fn))
        else:
            resList, _ = QFileDialog.getOpenFileNames(self, 'Add Input Files', DATA_DIR, fltr)
            for fn in resList:
                self.add_input_item(os.path.normpath(fn))

    ########################################
    #
    ########################################
    def slot_input_delete (self):
        row = self.listWidgetInput.currentRow()
        if row >= 0:
            fn = self.listWidgetInput.item(row).text()
            del self._media_infos[fn]
            self.listWidgetInput.takeItem(row)
            if self.listWidgetInput.count() == 0:
                # deactivate buttons
                self.pushButtonAddTaskToQueue.setDisabled(True)
                self.pushButtonRunTask.setDisabled(True)

    ########################################
    #
    ########################################
    def slot_input_clear (self):
        self._media_infos = {}
        self.listWidgetInput.clear()
        # deactivate buttons
        self.pushButtonAddTaskToQueue.setDisabled(True)
        self.pushButtonRunTask.setDisabled(True)

    ########################################
    #
    ########################################
    def slot_url_edited (self, urlText):
        isUrl = '://' in urlText
        self.pushButtonAddTaskToQueue.setDisabled(not isUrl)
        self.pushButtonRunTask.setDisabled(not isUrl)

    ########################################
    #
    ########################################
    def slot_set_output_folder (self):
        d = QFileDialog.getExistingDirectory(self, 'Select folder', DATA_DIR)
        if d == '':
            return
        self.lineEditOutputFolder.setText(d)

    ########################################
    #
    ########################################
    def slot_run_task (self):
        self.msg('')
        self.plainTextEditOutput.clear()
        self.pushButtonRunTask.setDisabled(True)
        self.pushButtonStopTask.setDisabled(False)
        self._task = self.get_task()
        self.run_task(self._task)
        self.tabWidget.setCurrentIndex(2) # ???

    ########################################
    #
    ########################################
    def slot_stop_task (self):
        if self._proc.state() == QProcess.NotRunning:
            return
        self._proc.kill()
        self.out('\nTask was stopped by User.')

    ########################################
    #
    ########################################
    def slot_quit (self):
        self.slot_stop_task()
        self.taskManager.quit()
        # save LastPreset
        if self._current_preset is not None:
            self._state.setValue('LastSession/LastPreset', self._current_preset['id'])
        # save LastOutputDir
        val = self.lineEditOutputFolder.text()
        self._state.setValue('LastSession/LastOutputDir', val)
        # save window settings
        val = self.saveGeometry()
        self._state.setValue('MainWindow/Geometry', val)
        val = self.saveState()
        self._state.setValue('MainWindow/State', val)

    ########################################
    #
    ########################################
    def slot_help (self):
        win = QTextBrowser(self)
        win.setWindowFlags(Qt.Window)
        uic.loadUi(os.path.join(RES_DIR, 'ui', 'help.ui'), win)
        if IS_WIN and self.actionDarkTheme.isChecked():
            windll.dwmapi.DwmSetWindowAttribute(int(win.winId()), 20, byref(c_int(1)), 4)
        win.show()

    ########################################
    #
    ########################################
    def slot_about (self):
        msg = f'''<b>{APP_NAME} v0.{APP_VERSION}</b><br><br>
        A general purpose media conversion tool based on<br>Python 3, PyQt5, SQLite and <a href="https://ffmpeg.org/">FFmpeg</a>.'''
        dialog = QMessageBox(QMessageBox.Information, f'About {APP_NAME}', msg,
                QMessageBox.Ok, self)
        if IS_WIN and self.actionDarkTheme.isChecked():
            windll.dwmapi.DwmSetWindowAttribute(int(dialog.winId()), 20, byref(c_int(1)), 4)
        dialog.exec()

    ########################################
    #
    ########################################
    def slot_preset_double_clicked (self, presetItem, col):
        if presetItem.data(0, Qt.UserRole) == 1:
            self.tabWidget.setCurrentIndex(0)
            preset_id = presetItem.data(0, Qt.UserRole+1)
            self.select_preset(preset_id)

    ########################################
    #
    ########################################
    def slot_preset_context_menu (self, p):
        tree_item = self.treeWidgetPresets.currentItem()
        if tree_item is not None:
            if tree_item.data(0, Qt.UserRole) == 0:
                m = QMenu()
                action = QAction(m)
                action.setText('&Rename Category')
                action.triggered.connect(self.slot_rename_category)
                m.addAction(action)
                action = QAction(m)
                action.setText('&Delete Category')
                action.triggered.connect(self.slot_delete_category)
                m.addAction(action)
                m.addSeparator()
                action = QAction(m)
                action.setText('&Add New Preset')
                action.triggered.connect(self.slot_add_preset)
                m.addAction(action)
                m.exec_(self.treeWidgetPresets.mapToGlobal(p))
            else:
                m = QMenu()
                action = QAction(m)
                action.setText('&Edit Preset')
                action.triggered.connect(self.slot_edit_preset)
                m.addAction(action)
                action = QAction(m)
                action.setText('&Delete Preset')
                action.triggered.connect(self.slot_delete_preset)
                m.addAction(action)
                m.exec_(self.treeWidgetPresets.mapToGlobal(p))
        else:
            m = QMenu()
            action = QAction(m)
            action.setText('&Add New Category')
            action.triggered.connect(self.slot_add_category)
            m.addAction(action)
            m.exec_(self.treeWidgetPresets.mapToGlobal(p))

    ########################################
    #
    ########################################
    def slot_rename_category (self):
        tree_item = self.treeWidgetPresets.currentItem()
        catName = tree_item.text(0)
        newName, ok = QInputDialog.getText(self, 'Rename Category',
                'Enter new category name:', 0, catName)
        if not ok or newName == catName:
            return
        # check if unique?
        cat_id = tree_item.data(0, Qt.UserRole + 1)
        try:
            c = self._presets_db.cursor()
            sql = "UPDATE categories SET name=? WHERE id=?"
            c.execute(sql, (newName, cat_id))
            self._presets_db.commit()
            tree_item.setText(0, newName)
#            self.reloadCategories()
            self.msg('Category successfully updated')
        except sqlite3.Error as e:
            self.err(e.args[0])

    ########################################
    #
    ########################################
    def slot_delete_category (self):
        tree_item = self.treeWidgetPresets.currentItem()
        cat_id = tree_item.data(0, Qt.UserRole + 1)
        try:
            c = self._presets_db.cursor()
            sql = "SELECT COUNT(id) FROM presets WHERE category_id=?"
            c.execute(sql, (cat_id,))
            cnt = c.fetchone()[0]
            if cnt > 0:
                dialog = QMessageBox(QMessageBox.Information, 'Category not empty',
                        'Only empty Categories can be deleted.', QMessageBox.Ok, self)
                if IS_WIN and self.actionDarkTheme.isChecked():
                    windll.dwmapi.DwmSetWindowAttribute(int(dialog.winId()), 20, byref(c_int(1)), 4)
                return dialog.exec()
            sql = "DELETE FROM categories WHERE id=?"
            c.execute(sql, (cat_id,))
            self._presets_db.commit()
            idx = self.treeWidgetPresets.indexOfTopLevelItem(tree_item)
            self.treeWidgetPresets.takeTopLevelItem(idx)
            self.msg('Category successfully deleted')
        except sqlite3.Error as e:
            self.err(e.args[0])

    ########################################
    #
    ########################################
    def slot_add_category (self):
        dialog = QInputDialog(self)
        if IS_WIN and self.actionDarkTheme.isChecked():
            windll.dwmapi.DwmSetWindowAttribute(int(dialog.winId()), 20, byref(c_int(1)), 4)
        dialog.setWindowTitle('New Category')
        dialog.setLabelText('Enter new category name:')
        ok = dialog.exec()
        if not ok or dialog.textValue() == '':
            return
        # check if unique?
        try:
            new_name = dialog.textValue()
            c = self._presets_db.cursor()
            sql = "INSERT INTO categories(name) VALUES(?)"
            c.execute(sql, (new_name,))
            self._presets_db.commit()
#            self.reloadCategories()
            catItem = QTreeWidgetItem()
            catItem.setText(0, new_name)
            catItem.setData(0, Qt.UserRole, 0)
            catItem.setData(0, Qt.UserRole + 1, c.lastrowid)
            self.treeWidgetPresets.addTopLevelItem(catItem)
            self.treeWidgetPresets.sortItems(0, Qt.AscendingOrder)
            self.msg('New Category successfully created')
        except sqlite3.Error as e:
            self.err(e.args[0])

    ########################################
    #
    ########################################
    def slot_edit_preset (self):
        tree_item = self.treeWidgetPresets.currentItem()
        preset_id = tree_item.data(0, Qt.UserRole + 1)
        if IS_WIN and self.actionDarkTheme.isChecked():
            windll.dwmapi.DwmSetWindowAttribute(int(self._preset_manager.winId()), 20, byref(c_int(1)), 4)
        self._preset_manager.show(preset_id)

    ########################################
    #
    ########################################
    def slot_delete_preset (self):
        dialog = QMessageBox(QMessageBox.Question, 'Delete Preset?',
                'Really delete the selected preset?', QMessageBox.Yes | QMessageBox.No, self)
        if IS_WIN and self.actionDarkTheme.isChecked():
            windll.dwmapi.DwmSetWindowAttribute(int(dialog.winId()), 20, byref(c_int(1)), 4)
        if dialog.exec() != QMessageBox.Yes:
            return
        tree_item = self.treeWidgetPresets.currentItem()
        preset_id = tree_item.data(0, Qt.UserRole + 1)
        try:
            c = self._presets_db.cursor()
            sql = "DELETE FROM presets WHERE id=?"
            c.execute(sql, (preset_id,))
            self._presets_db.commit()
            idx = tree_item.parent().indexOfChild(tree_item)
            tree_item.parent().takeChild(idx)
            self.msg('Preset successfully deleted')
        except sqlite3.Error as e:
            self.err(e.args[0])

    ########################################
    #
    ########################################
    def slot_add_preset (self):
        tree_item = self.treeWidgetPresets.currentItem()
        if tree_item.data(0, Qt.UserRole) == 1:
            tree_item = tree_item.parent()
        cat_id = tree_item.data(0, Qt.UserRole + 1)
        if IS_WIN and self.actionDarkTheme.isChecked():
            windll.dwmapi.DwmSetWindowAttribute(int(self._preset_manager.winId()), 20, byref(c_int(1)), 4)
        self._preset_manager.show(None, cat_id)

    ########################################
    #
    ########################################
    def slot_new_connection (self):
        if self._socket is not None:
            self._socket.close()
        self._socket = self._server.nextPendingConnection()
        self._socket.readyRead.connect(self.slot_socket_ready_read)

    ########################################
    #
    ########################################
    def slot_socket_ready_read (self):
        s = self._socket.readAll().data().decode(errors='ignore')
        res = re.search('progress=([a-z]*)', s)
        if res is not None and res.group(1) == 'end':
            self._progressBar.setValue(100)
            if IS_WIN:
                self._taskBarProgress.setValue(100)
            time.sleep(0.25)
            self._progressBar.reset()
            if IS_WIN:
                self._taskBarProgress.setVisible(False)
        elif self._duration > 0:
            res = re.search('out_time_ms=([0-9]*)', s)
            if res is not None:
                prog = int(int(res.group(1)) / self._duration / 10)
                self._progressBar.setValue(prog)
                if IS_WIN:
                    self._taskBarProgress.setValue(prog)
                    self._taskBarProgress.setVisible(True)

    ########################################
    #
    ########################################
    def slot_add_task_to_queue (self):
        self.taskManager.add_task(self.get_task())
        self.tabWidget.setCurrentIndex(1)


########################################
#
########################################
if __name__ == '__main__':
    import traceback
    sys.excepthook = traceback.print_exception
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    main = Main()
    sys.exit(app.exec())
