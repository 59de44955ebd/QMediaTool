"""
QMediaTool - Main class
"""

from const import *

import os
import sys
import traceback
import re
import sqlite3
import time
import pymediainfo

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtNetwork import QTcpServer, QHostAddress
from PyQt5 import uic
if IS_WIN:
    from PyQt5.QtWinExtras import QWinTaskbarButton

from presets import PresetsManager
from task import Task
from myprocess import MyProcess

class Main (QMainWindow):

    ########################################
    # @constructor
    ########################################
    def __init__ (self, app, theme='default'):
        super().__init__()
        self._app = app
        self.setWindowTitle(APP_NAME)
        # load settings
        self._state = QSettings('fx', APP_NAME)
        # load theme
        if theme == 'dark':
            import themes.dark
        else:
            import themes.default
        self._outputSep = '-' * 80
        # load UI
        QResource.registerResource(RES_DIR + '/ui/res.rcc')
        uic.loadUi(RES_DIR + '/ui/main.ui', self)
        # setup drop support
        self.setAcceptDrops(True)
        # defaults
        self._supportedFileExtensions = []
        self._mediaInfos = {}
        self._duration = 0
        self._currentPreset = None
        # set env vars
        os.environ['IS_WIN'] = 'true' if IS_WIN else 'false'
        self.setupToolEnvVars()
        # single file mode
        self.pushButtonInputSelect.released.connect(self.slotInputSelect)
        # URL mode
        self.lineEditURL.textEdited.connect(self.slotUrlEdited)
        # multi file mode
        self.groupBoxInputs.hide()
        self.listWidgetInput.setDragDropMode(QAbstractItemView.InternalMove)
        self.listWidgetInput.currentRowChanged.connect(self.slotInputRowChangedChanged)
        self.pushButtonInputAdd.released.connect(self.slotInputSelect)
        self.pushButtonInputDelete.released.connect(self.slotInputDelete)
        self.pushButtonInputClear.released.connect(self.slotInputClear)
        # other buttons
        self.pushButtonOutputFolder.released.connect(self.slotSetOutputFolder)
        self.pushButtonRunTask.released.connect(self.slotRunTask)
        self.pushButtonStopTask.released.connect(self.slotStopTask)
        # config widgets
        self.groupBoxArguments.hide()
        self._configVars = ['Track','Start','Duration','Fps','End','Container','ContainerVideo','ContainerAudio',
                'ContainerImage','CodecVideo','CodecAudio','BitrateAudio','Crf', 'Preset','DeviceVideo','DeviceAudio']
        self._configLabels = {}
        self._configWidgets = {}
        for c in self._configVars:
            self._configLabels[c] = self.findChild(QLabel, 'label' + c)
            self._configWidgets[c] = self.findChild(QWidget, 'widget' + c)
        self._configWidgets['Start'].timeChanged.connect(self.slotStartTimeChanged)
        self._configWidgets['Duration'].timeChanged.connect(self.slotDurationTimeChanged)
        self._configWidgets['End'].timeChanged.connect(self.slotEndTimeChanged)
        w = self._configWidgets['Track']
        w.setRange(0, 0)
        w = self._configWidgets['Container']
        for c in CONTAINERS:
            w.addItem(c)
        w = self._configWidgets['ContainerVideo']
        for c in CONTAINERS_VIDEO:
            w.addItem(c)
        w = self._configWidgets['ContainerAudio']
        for c in CONTAINERS_AUDIO:
            w.addItem(c)
        w = self._configWidgets['ContainerImage']
        for c in CONTAINERS_IMAGE:
            w.addItem(c)
        w = self._configWidgets['CodecVideo']
        for c in CODECS_VIDEO:
            w.addItem(c)
        w = self._configWidgets['CodecAudio']
        for c in CODECS_AUDIO:
            w.addItem(c)
        w = self._configWidgets['BitrateAudio']
        for c in [192, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 224, 256, 320]:
            w.addItem(str(c)+'k')
        w = self._configWidgets['Preset']
        for c in PRESETS:
            w.addItem(c)
        w.setCurrentText('medium')
        # task queue
        self.pushButtonAddTaskToQueue.released.connect(self.slotAddTaskToQueue)
        self.taskManager.statusMessage.connect(self.msg)
        self.taskManager.outputMessage.connect(self.out)
        self.taskManager.outputClear.connect(self.plainTextEditOutput.clear)
        self.taskManager._proc.errorOccurred.connect(self.slotErrorOccurred)
        self.taskManager.pushButtonTaskAdd.released.connect(lambda: self.tabWidget.setCurrentIndex(0))
        # setup app menu
        self.setupMenuActions()
        # presets treeWidget
        self.treeWidgetPresets.itemDoubleClicked.connect(self.slotPresetDoubleClicked)
        self.treeWidgetPresets.setContextMenuPolicy(Qt.CustomContextMenu)
        self.treeWidgetPresets.customContextMenuRequested.connect(self.slotPresetContextMenu)
        # load presets DB
        self._presetsDB = sqlite3.connect(DATA_DIR + '/presets.db')
        self._presetsDB.row_factory = sqlite3.Row
        # check if tables exist, otherwise create them
        c = self._presetsDB.cursor()
        sql = "SELECT * FROM sqlite_master WHERE type='table' AND name='categories'"
        c.execute(sql)
        res = c.fetchone()
        if not res:
            sql = "CREATE TABLE categories(id INTEGER PRIMARY KEY, name TEXT)"
            c.execute(sql)
            self._presetsDB.commit()
        sql = "SELECT * FROM sqlite_master WHERE type='table' AND name='presets'"
        c.execute(sql)
        res = c.fetchone()
        if not res:
            sql = """
            CREATE TABLE presets(id INTEGER PRIMARY KEY, category_id INTEGER, name TEXT, desc TEXT, cmd TEXT,
            ext TEXT NOT NULL DEFAULT '*', input_type INTEGER NOT NULL DEFAULT 0)
            """
            c.execute(sql)
            self._presetsDB.commit()
        lastPresetID = int(self._state.value('LastSession/LastPreset', 0))
        self.loadPresets(lastPresetID)
        self._presetManager = PresetsManager(self)
        self._presetManager.presetChanged.connect(self.loadPresets)
        # setup process
        self._proc = MyProcess()
        self._proc.readyReadStandardOutput.connect(self.slotStdout)
        self._proc.readyReadStandardError.connect(self.slotStderr)
        self._proc.finished.connect(self.slotComplete)
        self._proc.errorOccurred.connect(self.slotErrorOccurred)
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
        self._server.newConnection.connect(self.slotNewConnection)
        self._socket = None
        # get list of available devices
        self.loadDevices()
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
            self._trayIcon.activated.connect(self.slotActivated)
            self._trayIcon.setContextMenu(menu_tray)
            # taskbar progress
            self._taskBarButton = QWinTaskbarButton(self)
            self._taskBarButton.setWindow(self.windowHandle())
            self._taskBarProgress = self._taskBarButton.progress()

    ########################################
    #
    ########################################
    def selectPreset (self, presetID):
        c = self._presetsDB.cursor()
        sql = """
        SELECT presets.*,categories.name AS category FROM presets
        LEFT JOIN categories ON presets.category_id=categories.id WHERE presets.id=?
        """
        c.execute(sql, (presetID,))
        preset = c.fetchone()
        if preset is None:
            return
        self._currentPreset = dict(preset)
        self.lineEditPreset.setText(preset['name'])
        #self.labelPresetName.setText('Preset: ' + preset['name'].strip())
        # show/hide custom argument widgets
        show = False
        for c in self._configVars:
            flag = '$' + c.upper() in preset['cmd'] or '${' + c.upper() + '}' in preset['cmd']
            if flag:
                show = True
            self._configLabels[c].setVisible(flag)
            self._configWidgets[c].setVisible(flag)
        flag = '$TRACK' in preset['cmd']
        if flag:
            show = True
        self._configLabels['Track'].setVisible(flag)
        self._configWidgets['Track'].setVisible(flag)
        if '$START' in preset['cmd'] and '$DURATION' in preset['cmd']:
            self._configLabels['End'].setVisible(True)
            self._configWidgets['End'].setVisible(True)
        self.groupBoxArguments.setVisible(show)
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
            self._supportedFileExtensions = preset['ext'].split(',')
        else:
            self.lineEditExtensions.setText('')
            self._supportedFileExtensions = []
        # check if currently selected file(s) are compatible with new preset
        if len(self._supportedFileExtensions) > 0:
            if preset['input_type'] == INPUT_TYPE_FILES:
                unsupported = []
                cnt = self.listWidgetInput.count()
                for i in range(cnt):
                    inputFile = self.listWidgetInput.item(i).text()
                    ext = os.path.splitext(inputFile)[1][1:]
                    if not ext in self._supportedFileExtensions:
                        unsupported.append(i)
                cnt = len(unsupported)
                if cnt>0:
                    msg = 'The extension of ' + str(cnt) + ' currently selected file(s) is not compatible with new preset.\nRemove those files?'
                    tStandardButtons = QMessageBox.Yes | QMessageBox.No
                    res = QMessageBox.warning(self, 'Incompatible Extension', msg, tStandardButtons, QMessageBox.Yes)
                    if res == QMessageBox.Yes:
                        for i in range(cnt, 0, -1):
                            row = unsupported[i]
                            fn = self.listWidgetInput.item(row).text()
                            del self._mediaInfos[fn]
                            self.listWidgetInput.takeItem(row)
            elif preset['input_type'] == INPUT_TYPE_FILE:
                inputFile = self.lineEditInput.text()
                if inputFile != '':
                    ext = os.path.splitext(inputFile)[1][1:]
                    if not ext in self._supportedFileExtensions:
                        msg = 'The currently selected file\'s extension is not compatible with new preset.\nRemove file?'
                        tStandardButtons = QMessageBox.Yes | QMessageBox.No
                        res = QMessageBox.warning(self, 'Incompatible Extension', msg, tStandardButtons, QMessageBox.Yes)
                        if res == QMessageBox.Yes:
                            self.lineEditInput.setText('')
                            self._mediaInfos = {}
        # update infos
        if self._currentPreset['input_type'] == INPUT_TYPE_FILES:
            if len(self._mediaInfos.values()):
                self.listWidgetInput.setCurrentRow(0)
                self.showMediaInfo(list(self._mediaInfos.values())[0])
            else:
                self.plainTextEditInfos.setPlainText('')
        elif self._currentPreset['input_type'] == INPUT_TYPE_FILE:
            if len(self._mediaInfos.values()):
                self.showMediaInfo(list(self._mediaInfos.values())[0])
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
        # enable/disable AddTask/RunTask buttons according to preset's input type
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
    def loadPresets (self, selectID=0):
        selectedItem = None
        self.treeWidgetPresets.clear()
        c = self._presetsDB.cursor()
        sql = "SELECT * FROM categories ORDER BY name"
        c.execute(sql)
        for row in c.fetchall():
            cat = row['name']
            catItem = QTreeWidgetItem()
            catItem.setText(0, cat)
            catItem.setData(0, Qt.UserRole, 0)
            catItem.setData(0, Qt.UserRole+1, row['id'])
            self.treeWidgetPresets.addTopLevelItem(catItem)
            sql = "SELECT * FROM presets WHERE category_id=? ORDER BY name"
            c.execute(sql, (row['id'],))
            presetItems = []
            for row2 in c.fetchall():
                presetItem = QTreeWidgetItem()
                presetItem.setText(0, row2['name'])
                presetItem.setData(0, Qt.UserRole, 1)
                presetItem.setData(0, Qt.UserRole+1, row2['id'])
                presetItem.setToolTip(0, row2['name'])
                presetItems.append(presetItem)
                if row2['id']==selectID:
                    selectedItem = presetItem
            catItem.addChildren(presetItems)
        if selectedItem is not None:
            self.treeWidgetPresets.setCurrentItem(selectedItem)
            self.selectPreset(selectID)

    ########################################
    #
    ########################################
    def loadDevices (self):
        task = Task('$FFMPEG -hide_banner -list_devices true -f dshow -i dummy'
                if IS_WIN else '$FFMPEG -hide_banner -list_devices true -f avfoundation -i /dev/null')
        proc = QProcess()
        task.run(proc)
        proc.waitForFinished(-1)
        lines = proc.readAllStandardError().data().decode().rstrip().splitlines()
        if IS_WIN:
            re_vid = re.compile('^\[[^\]]*\] "(.*)" \(video\)')
            re_aud = re.compile('^\[[^\]]*\] "(.*)" \(audio\)')
            for line in lines:
                res = re.search(re_vid, line)
                if res:
                    self._configWidgets['DeviceVideo'].addItem(res.group(1))
                res = re.search(re_aud, line)
                if res:
                    self._configWidgets['DeviceAudio'].addItem(res.group(1))
        else:
            re_dev = re.compile('^\[[^\]]*\] (.*)')
            for line in lines:
                res = re.search(re_dev, line)
                if res:
                    line = res.group(1)
                    if line.startswith('AVFoundation video'):
                        w = self._configWidgets['DeviceVideo']
                    elif line.startswith('AVFoundation audio'):
                        w = self._configWidgets['DeviceAudio']
                    elif line.startswith('['):
                        w.addItem(line[line.index(']')+2:])

    ########################################
    # Connect menu actions
    ########################################
    def setupMenuActions (self):
        self._actions = {}
        actions = self.findChildren(QAction)
        for a in actions:
            p = a.objectName()
            if p!='':
                self._actions[p] = a
        # File
        self._actions['actionNewPresetCategory'].triggered.connect(self.slotAddCategory)
        self._actions['actionNewPreset'].triggered.connect(self.slotAddPreset)
        # View
        self._actions['actionTaskEditor'].triggered.connect(lambda: self.tabWidget.setCurrentIndex(0))
        self._actions['actionTaskQueue'].triggered.connect(lambda: self.tabWidget.setCurrentIndex(1))
        self._actions['actionOutputLog'].triggered.connect(lambda: self.tabWidget.setCurrentIndex(2))
        # Help
        self._actions['actionHelp'].triggered.connect(self.slotHelp)
        self._actions['actionAbout'].triggered.connect(self.slotAbout)

    ########################################
    # Sets environment variables for all binary modules in folder 'bin'
    ########################################
    def setupToolEnvVars (self):
        modules = os.listdir(BIN_DIR)
        for m in modules:
            p = BIN_DIR + '/' + m + '/' + m
            if ' ' in p:
                p = '"' + p + '"'
            os.environ[m.upper()] = p

    ########################################
    # Single file mode - sets file
    ########################################
    def setInputItem (self, fn):
        if not os.path.isfile(fn):
            return False
        if len(self._supportedFileExtensions) > 0:
            ext = os.path.splitext(fn)[1][1:]
            if not ext in self._supportedFileExtensions:
                msg = 'The selected file\'s extension is not compatible with current preset.\nAdd file anyway?'
                tStandardButtons = QMessageBox.Yes | QMessageBox.No
                res = QMessageBox.warning(self, 'Incompatible Extension', msg, tStandardButtons, QMessageBox.No)
                if res != QMessageBox.Yes:
                    return False  # discard loading
        info = self.getMediaInfo(fn)
        if info is None:
            return False
        # activate buttons
        self.pushButtonAddTaskToQueue.setDisabled(False)
        self.pushButtonRunTask.setDisabled(False)
        self._mediaInfos = {fn: info}
        self.lineEditInput.setText(fn)
        self.showMediaInfo(info)
        return True

    ########################################
    # Multiple file mode - adds file
    ########################################
    def addInputItem (self, fn):
        if os.path.isfile(fn):
            if len(self._supportedFileExtensions) > 0:
                ext = os.path.splitext(fn)[1][1:]
                if not ext in self._supportedFileExtensions:
                    msg = 'The selected file\'s extension is not compatible with current preset.\nAdd file anyway?'
                    tStandardButtons = QMessageBox.Yes | QMessageBox.No
                    res = QMessageBox.warning(self, 'Incompatible Extension', msg, tStandardButtons, QMessageBox.No)
                    if res != QMessageBox.Yes:
                        return False  # discard loading
            self.listWidgetInput.addItem(fn)
            info = self.getMediaInfo(fn)
            if info is None:
                return False
            # activate buttons
            self.pushButtonAddTaskToQueue.setDisabled(False)
            self.pushButtonRunTask.setDisabled(False)
            self._mediaInfos[fn] = info
        else:
            l = os.listdir(fn)
            for f in l:
                self.addInputItem(fn + '/' + f)
        return True

    ########################################
    # Returns media info as dict
    ########################################
    def getMediaInfo (self, fn):
        info = pymediainfo.MediaInfo.parse(fn, cover_data=False).to_data()
        res = {}
        res['general'] = info['tracks'][0]
        del info['tracks'][0]
        res['tracks'] = []
        for t in info['tracks']:
            res['tracks'].append(t)
        return res

    ########################################
    # Creates and returns a new task based on current settings
    ########################################
    def getTask (self):
        env = {}
        if self._currentPreset['input_type'] == INPUT_TYPE_FILE or self._currentPreset['input_type'] == INPUT_TYPE_URL:
            trackNum = self._configWidgets['Track'].value()
            if self._currentPreset['input_type'] == INPUT_TYPE_FILE:
                inputFile = self.lineEditInput.text()
                f, ext = os.path.splitext(inputFile)
                env['INPUT'] = inputFile
                env['INPUTDIR'] = os.path.dirname(f)
                env['INPUTBASENAME'] = os.path.basename(f).replace(' ', '_')
                env['INPUTEXT'] = ext[1:]
                # variables for tracks
                tracks = list(self._mediaInfos.values())[0]['tracks']
                for i in range(len(tracks)):
                    track = tracks[i]
                    if 'format' in track:
                        fmt = track['format']
                        env['FORMAT' + str(i)] = fmt
                    if 'frame_rate' in track:
                        env['FPS' + str(i)] = track['frame_rate']
                # variables for currently selected track
                track = tracks[trackNum]  # -1
                if 'format' in track:
                    fmt = track['format']
                    os.environ['FORMAT'] = fmt
            else:
                env['URL'] = self.lineEditURL.text()
            # arguments variables
            env['TRACK'] = str(trackNum)  # -1
        elif self._currentPreset['input_type'] == INPUT_TYPE_FILES:
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
        env['START'] = self._timeToSec(self._configWidgets['Start'].time())
        env['END'] = self._timeToSec(self._configWidgets['End'].time())
        env['DURATION'] = self._timeToSec(self._configWidgets['Duration'].time())
        env['CONTAINER'] = self._configWidgets['Container'].currentText()
        env['CONTAINERVIDEO'] = self._configWidgets['ContainerVideo'].currentText()
        env['CONTAINERAUDIO'] = self._configWidgets['ContainerAudio'].currentText()
        env['CONTAINERIMAGE'] = self._configWidgets['ContainerImage'].currentText()
        env['CODECVIDEO'] = self._configWidgets['CodecVideo'].currentText()
        env['CODECAUDIO'] = self._configWidgets['CodecAudio'].currentText()
        env['BITRATEAUDIO'] = self._configWidgets['BitrateAudio'].currentText()
        env['PRESET'] = self._configWidgets['Preset'].currentText()
        env['FPS'] = str(self._configWidgets['Fps'].value())
        env['CRF'] = str(self._configWidgets['Crf'].value())
        if IS_WIN:
            env['DEVICEVIDEO'] = self._configWidgets['DeviceVideo'].currentText()
            env['DEVICEAUDIO'] = self._configWidgets['DeviceAudio'].currentText()
        else:
            env['DEVICEVIDEO'] = self._configWidgets['DeviceVideo'].currentIndex()
            env['DEVICEAUDIO'] = self._configWidgets['DeviceAudio'].currentIndex()
        if self.checkBoxOutputFolderInput.isEnabled() and self.checkBoxOutputFolderInput.isChecked():
            if self._currentPreset['input_type'] == INPUT_TYPE_FILE:
                env['OUTPUTDIR'] = os.path.dirname(self.lineEditInput.text())
            elif self._currentPreset['input_type'] == INPUT_TYPE_FILES: # multiple
                env['OUTPUTDIR'] = os.path.dirname(self.listWidgetInput.item(0).text())
        else:
            env['OUTPUTDIR'] = self.lineEditOutputFolder.text()
        env['TIMESTAMP'] = time.strftime("%Y%m%d_%H%M%S")
        task = Task(self.plainTextEditCommandLine.toPlainText().strip(' \t\n'), env, self._currentPreset['name'])
        return task

    ########################################
    #
    ########################################
    def runTask (self, task):
        self.msg('Task running...')
        task.run(self._proc)

    ########################################
    #
    ########################################
    def _msToTime (self, ms):
        s = ms/1000
        ms = ms % 1000
        m = s/60
        s = s % 60
        h = m/60
        m = m % 60
        return QTime(h,m,s,ms)

    ########################################
    #
    ########################################
    def _timeToMS (self, t):
        return t.msec() + 1000*t.second() + 1000*60*t.minute() + 1000*60*60*t.hour()

    ########################################
    #
    ########################################
    def _timeToSec (self, t):
        return t.msec()/1000 + t.second() + 60*t.minute() + 60*60*t.hour()

    ########################################
    # Displays media infos for current file
    ########################################
    def showMediaInfo (self, info):
        # update track spinBox
        trackCnt = len(info['tracks'])
        self._configWidgets['Track'].setRange(0, trackCnt - 1)
        self._configWidgets['Track'].setValue(0)
        # update infos
        fmt = info['general']['format']
        s = 'Format: '+fmt+'\n'
        # update start and duration widgets
        if 'duration' in info['general']:
            self._duration = info['general']['duration']
            t = self._msToTime(info['general']['duration'])
            self._configWidgets['Start'].setMaximumTime(t)
            self._configWidgets['Duration'].setMaximumTime(t)
            self._configWidgets['Duration'].setTime(t)
            self._configWidgets['End'].setMaximumTime(t)
            durStr = t.toString('hh:mm:ss.zzz')
            s += 'Duration: ' + durStr + '\n'
        else:
            self._duration = 0
        s += str(len(info['tracks'])) + ' Tracks:'
        try:
            tracks = sorted(info['tracks'], key=lambda x: x['track_id'])
        except:
            tracks = info['tracks']
        for i in range(len(tracks)):
            track = tracks[i]
            s += '\nTrack ' + str(i) + ': ' + 'Type = ' + track['track_type']
            if 'format' in track:
                s += ', Format = ' + track['format']
                if 'format_info' in track:
                    s += ' (' + track['format_info'] + ')'
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
        if self.isMinimized():
            self._trayIcon.show()
            self.hide()

    ########################################
    #
    ########################################
    def closeEvent (self, e):
        self.slotQuit()

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
        if self._currentPreset['input_type'] == INPUT_TYPE_URL or self._currentPreset['input_type'] == INPUT_TYPE_NONE:
            return
        for u in e.mimeData().urls():
            fn = u.toLocalFile()
            if self._currentPreset['input_type'] == INPUT_TYPE_FILE:
                self.setInputItem(fn)
                break
            else:
                self.addInputItem(fn)

	########################################
	# @callback
	########################################
    def slotActivated (self, activationReason):
        if activationReason == QSystemTrayIcon.Trigger:
            state = (self.windowState() & ~Qt.WindowMinimized) | Qt.WindowActive
            self.setWindowState(state)
            self.show()
            self.activateWindow()
            self._trayIcon.hide()

    ########################################
    # Start geändert -> setze End auf Start + Duration
    # @callback
    ########################################
    def slotStartTimeChanged (self, startTime):
        w = self._app.focusWidget()
        if w is None or w.objectName() != 'widgetStart':
            return
        msDuration = self._timeToMS(self._configWidgets['Duration'].time())
        endTime = startTime.addMSecs(msDuration)
        self._configWidgets['End'].setTime(endTime)

    ########################################
    # @callback
    ########################################
    def slotDurationTimeChanged (self, durTime):
        w = self._app.focusWidget()
        if w is None or w.objectName() != 'widgetDuration':
            return
        msDuration = self._timeToMS(durTime)
        endTime = self._configWidgets['Start'].time().addMSecs(msDuration)
        self._configWidgets['End'].setTime(endTime)

    ########################################
    # @callback
    ########################################
    def slotEndTimeChanged (self, endTime):
        w = self._app.focusWidget()
        if w is None or w.objectName() != 'widgetEnd':
            return
        msStart = self._timeToMS(self._configWidgets['Start'].time())
        durTime = endTime.addMSecs(-msStart)
        self._configWidgets['Duration'].setTime(durTime)

    ########################################
    # @callback
    ########################################
    def slotErrorOccurred (self, err):
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
    # @callback
    ########################################
    def slotStdout (self):
        s = self._proc.readAllStandardOutput().data().decode(errors='ignore').strip(' \n\r')
        # remove false UTF-8 BOM (needed for AtomicParsely)
        if s.startswith('ï»¿'):
            s = s[3:]
        self.out(s)

    ########################################
    # @callback
    ########################################
    def slotStderr (self):
        s = self._proc.readAllStandardError().data().decode().strip(' \n\r')
        self.out(s)

    ########################################
    # @callback
    ########################################
    def slotComplete (self, exitCode, exitStatus):
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

    ########################################
    # @callback
    ########################################
    def slotInputRowChangedChanged (self):
        row = self.listWidgetInput.currentRow()
        if row<0:
            self.plainTextEditInfos.setPlainText('')
        else:
            fn = self.listWidgetInput.item(row).text()
            info = self._mediaInfos[fn]
            self.showMediaInfo(info)

    ########################################
    # @callback
    ########################################
    def slotInputSelect (self):
        fltr = ''
        if len(self._supportedFileExtensions) > 0:
            fltr = 'Supported Files ('
            for ext in self._supportedFileExtensions:
                fltr += '*.'+ext+' '
            fltr = fltr[:-1]
            fltr += ');;'
        fltr += 'All Files (*.*)'
        if self._currentPreset['input_type'] == INPUT_TYPE_FILE:
            fn, _ = QFileDialog.getOpenFileName(self, 'Select Input File', DATA_DIR, fltr)
            if fn == '':
                return
            self.setInputItem(os.path.normpath(fn))
        else:
            resList, _ = QFileDialog.getOpenFileNames(self, 'Add Input Files', DATA_DIR, fltr)
            for fn in resList:
                self.addInputItem(os.path.normpath(fn))

    ########################################
    # @callback
    ########################################
    def slotInputDelete (self):
        row = self.listWidgetInput.currentRow()
        if row >= 0:
            fn = self.listWidgetInput.item(row).text()
            del self._mediaInfos[fn]
            self.listWidgetInput.takeItem(row)
            if self.listWidgetInput.count()==0:
                # deactivate buttons
                self.pushButtonAddTaskToQueue.setDisabled(True)
                self.pushButtonRunTask.setDisabled(True)

    ########################################
    # @callback
    ########################################
    def slotInputClear (self):
        self._mediaInfos = {}
        self.listWidgetInput.clear()
        # deactivate buttons
        self.pushButtonAddTaskToQueue.setDisabled(True)
        self.pushButtonRunTask.setDisabled(True)

    ########################################
    # @callback
    ########################################
    def slotUrlEdited (self, urlText):
        isUrl = '://' in urlText
        self.pushButtonAddTaskToQueue.setDisabled(not isUrl)
        self.pushButtonRunTask.setDisabled(not isUrl)

    ########################################
    # @callback
    ########################################
    def slotSetOutputFolder (self):
        d = QFileDialog.getExistingDirectory(self, 'Select folder', DATA_DIR)
        if d == '':
            return
        self.lineEditOutputFolder.setText(d)

    ########################################
    # @callback
    ########################################
    def slotRunTask (self):
        self.msg('')
        self.plainTextEditOutput.clear()
        self.pushButtonRunTask.setDisabled(True)
        self.pushButtonStopTask.setDisabled(False)
        self._task = self.getTask()
        self.runTask(self._task)
        self.tabWidget.setCurrentIndex(2) # ???

    ########################################
    # @callback
    ########################################
    def slotStopTask (self):
        if self._proc.state() == QProcess.NotRunning:
            return
        self._proc.kill()
        self.out('\nTask was stopped by User.')

    ########################################
    # @callback
    ########################################
    def slotQuit (self):
        self.slotStopTask()
        self.taskManager.quit()
        # save LastPreset
        if self._currentPreset is not None:
            self._state.setValue('LastSession/LastPreset', self._currentPreset['id'])
        # save LastOutputDir
        val = self.lineEditOutputFolder.text()
        self._state.setValue('LastSession/LastOutputDir', val)
        # save window settings
        val = self.saveGeometry()
        self._state.setValue('MainWindow/Geometry', val)
        val = self.saveState()
        self._state.setValue('MainWindow/State', val)

    ########################################
    # @callback
    ########################################
    def slotEditPresets (self):
        self._presetManager.show()

    ########################################
    # @callback
    ########################################
    def slotHelp (self):
        w = QMainWindow(self)
        uic.loadUi(RES_DIR + '/ui/help.ui', w)
        w.show()

    ########################################
    # @callback
    ########################################
    def slotAbout (self):
        msg = '<b>' + APP_NAME + ' v0.' + str(APP_VERSION) + '</b><br><br>'
        msg += 'A general purpose media conversion tool based on<br>Python 3, PyQt5, SQLite and <a href="https://ffmpeg.org/">FFmpeg</a>.'
        QMessageBox.about(self, 'About ' + APP_NAME, msg)

    ########################################
    # @callback
    ########################################
    def slotPresetDoubleClicked (self, presetItem, col):
        if presetItem.data(0, Qt.UserRole) == 1:
            self.tabWidget.setCurrentIndex(0)
            presetID = presetItem.data(0, Qt.UserRole+1)
            self.selectPreset(presetID)

    ########################################
    # @callback
    ########################################
    def slotPresetContextMenu (self, p):
        treeItem = self.treeWidgetPresets.currentItem()
        if treeItem is not None:
            if treeItem.data(0, Qt.UserRole) == 0:
                m = QMenu()
                action = QAction(m)
                action.setText('&Rename Category')
                action.triggered.connect(self.slotRenameCategory)
                m.addAction(action)
                action = QAction(m)
                action.setText('&Delete Category')
                action.triggered.connect(self.slotDeleteCategory)
                m.addAction(action)
                m.addSeparator()
                action = QAction(m)
                action.setText('&Add New Preset')
                action.triggered.connect(self.slotAddPreset)
                m.addAction(action)
                m.exec_(self.treeWidgetPresets.mapToGlobal(p))
            else:
                m = QMenu()
                action = QAction(m)
                action.setText('&Edit Preset')
                action.triggered.connect(self.slotEditPreset)
                m.addAction(action)
                action = QAction(m)
                action.setText('&Delete Preset')
                action.triggered.connect(self.slotDeletePreset)
                m.addAction(action)
                m.exec_(self.treeWidgetPresets.mapToGlobal(p))
        else:
            m = QMenu()
            action = QAction(m)
            action.setText('&Add New Category')
            action.triggered.connect(self.slotAddCategory)
            m.addAction(action)
            m.exec_(self.treeWidgetPresets.mapToGlobal(p))

    ########################################
    # @callback
    ########################################
    def slotRenameCategory (self):
        treeItem = self.treeWidgetPresets.currentItem()
        catName = treeItem.text(0)
        newName, ok = QInputDialog.getText(self, 'Rename Category', 'Enter new category name:', 0, catName)
        if not ok or newName == catName:
            return
        # check if unique?
        catID = treeItem.data(0, Qt.UserRole + 1)
        try:
            c = self._presetsDB.cursor()
            sql = "UPDATE categories SET name=? WHERE id=?"
            c.execute(sql, (newName, catID))
            self._presetsDB.commit()
            treeItem.setText(0, newName)
#            self.reloadCategories()
            self.msg('Category successfully updated')
        except sqlite3.Error as e:
            self.err(e.args[0])

    ########################################
    # @callback
    ########################################
    def slotDeleteCategory (self):
        treeItem = self.treeWidgetPresets.currentItem()
        catID = treeItem.data(0, Qt.UserRole+1)
        try:
            c = self._presetsDB.cursor()
            sql = "SELECT COUNT(id) FROM presets WHERE category_id=?"
            c.execute(sql, (catID,))
            cnt = c.fetchone()[0]
            if cnt > 0:
                return QMessageBox.information(self, 'Category not empty', 'Only empty Categories can be deleted.')
            sql = "DELETE FROM categories WHERE id=?"
            c.execute(sql, (catID,))
            self._presetsDB.commit()
            idx = self.treeWidgetPresets.indexOfTopLevelItem(treeItem)
            self.treeWidgetPresets.takeTopLevelItem(idx)
            self.msg('Category successfully deleted')
        except sqlite3.Error as e:
            self.err(e.args[0])

    ########################################
    # @callback
    ########################################
    def slotAddCategory (self):
        newName, ok = QInputDialog.getText(self, 'New Category', 'Enter new category name:', 0, '')
        if not ok or newName == '':
            return
        # check if unique?
        try:
            c = self._presetsDB.cursor()
            sql = "INSERT INTO categories(name) VALUES(?)"
            c.execute(sql, (newName,))
            self._presetsDB.commit()
#            self.reloadCategories()
            catItem = QTreeWidgetItem()
            catItem.setText(0, newName)
            catItem.setData(0, Qt.UserRole, 0)
            catItem.setData(0, Qt.UserRole+1, c.lastrowid)
            self.treeWidgetPresets.addTopLevelItem(catItem)
            self.treeWidgetPresets.sortItems(0, Qt.AscendingOrder)
            self.msg('New Category successfully created')
        except sqlite3.Error as e:
            self.err(e.args[0])

    ########################################
    # @callback
    ########################################
    def slotEditPreset (self):
        treeItem = self.treeWidgetPresets.currentItem()
        presetID = treeItem.data(0, Qt.UserRole+1)
        self._presetManager.show(presetID)

    ########################################
    # @callback
    ########################################
    def slotDeletePreset (self):
        tStandardButtons = QMessageBox.Yes | QMessageBox.No
        ret = QMessageBox.question(self, 'Delete Preset?', 'Really delete the selected preset?', tStandardButtons)
        if ret != QMessageBox.Yes:
            return
        treeItem = self.treeWidgetPresets.currentItem()
        presetID = treeItem.data(0, Qt.UserRole+1)
        try:
            c = self._presetsDB.cursor()
            sql = "DELETE FROM presets WHERE id=?"
            c.execute(sql, (presetID,))
            self._presetsDB.commit()
            idx = treeItem.parent().indexOfChild(treeItem)
            treeItem.parent().takeChild(idx)
            self.msg('Preset successfully deleted')
        except sqlite3.Error as e:
            self.err(e.args[0])

    ########################################
    # @callback
    ########################################
    def slotAddPreset (self):
        treeItem = self.treeWidgetPresets.currentItem()
        if treeItem.data(0, Qt.UserRole)==1:
            treeItem = treeItem.parent()
        catID = treeItem.data(0, Qt.UserRole+1)
        self._presetManager.show(None, catID)

    ########################################
    # @callback
    ########################################
    def slotNewConnection (self):
        if self._socket is not None:
            self._socket.close()
        self._socket = self._server.nextPendingConnection()
        self._socket.readyRead.connect(self.slotSocketReadyRead)

    ########################################
    # @callback
    ########################################
    def slotSocketReadyRead (self):
        s = self._socket.readAll().data().decode()
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
                prog = int(res.group(1))/self._duration/10
                self._progressBar.setValue(int(res.group(1))/self._duration/10)
                if IS_WIN:
                    self._taskBarProgress.setValue(prog)
                    self._taskBarProgress.setVisible(True)

    ########################################
    # @callback
    ########################################
    def slotAddTaskToQueue (self):
        self.taskManager.addTask(self.getTask())
        self.tabWidget.setCurrentIndex(1)

########################################
#
########################################
def main(theme='default'):
    app = QApplication(sys.argv)
    Main(app, theme)
    sys.exit(app.exec())

if __name__ == '__main__':
    sys.excepthook = traceback.print_exception
    main('dark')
