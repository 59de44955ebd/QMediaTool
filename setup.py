import sys
from cx_Freeze import Executable, setup
from const import APP_VERSION
from datetime import datetime

base = 'Win32GUI' if sys.platform == 'win32' else None

build_exe_options = {
    'excludes': [
        'tkinter', 'unittest', 'PyQtWebEngine',
        'distutils', 'html', 'http',
        'pydoc_data', 'test', 'win32com', 'xmlrpc'
    ],
    'bin_excludes' : [
        'QtMultimedia', 'QtPrintSupport', 'QtQml', 'QtQmlModels',
        'QtQuick', 'QtSvg', 'QtDBus', 'QtWebSockets'
    ],
    'bin_path_excludes': [
        'resources', 'qml', '__pycache__'
    ],
    'includes': ['mytreewidget', 'taskmanager']
}

bdist_mac_options = {
    'bundle_name': 'QMediaTool',
}

bdist_dmg_options = {
    'volume_label': 'QMediaTool',
}

executables = [
    Executable(
        'main.py',
        copyright='Copyright (c) {} fx'.format(datetime.now().year),
        base=base,
        target_name='QMediaTool',
        icon='app.ico',
    ),
]

setup(
    name='QMediaTool',
    version='0.{}'.format(APP_VERSION),
    description='QMediaTool',
    options={
        'build_exe': build_exe_options,
        'bdist_mac': bdist_mac_options,
        'bdist_dmg': bdist_dmg_options,
    },
    executables=executables,
)
