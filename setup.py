import sys
from cx_Freeze import Executable, setup

# base="Win32GUI" should be used only for Windows GUI app
base = None
if sys.platform == "win32":
    base = "Win32GUI"

build_exe_options = {
    "excludes": [
        "tkinter", "unittest", "PyQtWebEngine",
        "distutils", "html", "http",
        "pydoc_data", "test", "xmlrpc"
    ],
    "bin_excludes" : [
        "QtMultimedia", "QtPrintSupport", "QtQml", "QtQmlModels",
        "QtQuick", "QtSvg", "QtDBus", "QtWebSockets"
    ],
    "bin_path_excludes": [
        "resources", "qml"
    ],
    "includes": ["mytreewidget", "taskmanager"]
}

bdist_mac_options = {
    "bundle_name": "QMediaTool",
}

bdist_dmg_options = {
    "volume_label": "QMediaTool",
}

executables = [
    Executable(
        "main.py",
        copyright="Copyright (c) 2022 fx",
        base=base,
        target_name="QMediaTool",
        icon="app.ico",
    ),
]

setup(
    name="QMediaTool",
    version="0.1",
    description="QMediaTool",
    options={
        "build_exe": build_exe_options,
        "bdist_mac": bdist_mac_options,
        "bdist_dmg": bdist_dmg_options,
    },
    executables=executables,
)
