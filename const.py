"""
QMediaTool - constants
"""

import os
import sys

APP_NAME = 'QMediaTool'
APP_VERSION = 7

IS_WIN = sys.platform == 'win32'
IS_MAC = sys.platform == 'darwin'
IS_LINUX = sys.platform == 'linux'

if getattr(sys, "frozen", False):
    APP_PATH = os.path.dirname(os.path.realpath(sys.executable))
    if IS_WIN or IS_LINUX:
        APP_PATH = APP_PATH.replace('\\', '/')
        DATA_DIR = APP_PATH
        RES_DIR = APP_PATH + '/resources'
    else:
        DATA_DIR = os.path.realpath(APP_PATH + '/../../..')
        RES_DIR = os.path.realpath(APP_PATH + '/../Resources')
else:
    APP_PATH = os.path.dirname(os.path.realpath(__file__))
    if IS_WIN:
        APP_PATH = APP_PATH.replace('\\', '/')
    DATA_DIR = APP_PATH
    RES_DIR = APP_PATH + '/resources'

if IS_WIN:
    BASH = RES_DIR + '/bash/bin/bash'
    BIN_DIR = RES_DIR + '/bin/win'
elif IS_MAC:
    BASH = '/bin/bash'
    BIN_DIR = RES_DIR + '/bin/macos'
else:
    BASH = '/usr/bin/bash'
    BIN_DIR = RES_DIR + '/bin/linux'

#BIN_DIR = RES_DIR + '/bin/' + ('win' if IS_WIN else 'macos')
#BASH = RES_DIR + '/bash/bin/bash' if IS_WIN else '/bin/bash'

INPUT_TYPE_FILE = 0
INPUT_TYPE_FILES = 1
INPUT_TYPE_URL = 2
INPUT_TYPE_NONE = 3

CONTAINERS = ['aac','ac3','asf','au','avi','caf','flac','flv','gif','h264','m4a','m4v','mkv','mov','mp2','mp3','mp4','mpeg','ogg','rm','vob','wav','webm']

CONTAINERS_AUDIO = ['aac','ac3','aiff','au','flac','m4a','mp3','ogg','wav']

CONTAINERS_VIDEO = ['mp4','mov','mkv','avi','flv']

CONTAINERS_IMAGE = ['bmp','jpg','png']

PRESETS = ['ultrafast','superfast','veryfast','faster','fast','medium','slow','slower','veryslow']

CODECS_NVENCC_VCEENCC = ['av1', 'h264', 'hevc']
CODECS_QSVENCC = ['av1', 'h264', 'hevc', 'mpeg2', 'raw', 'vp9']

CONFIG_VARS = [
    'DeviceVideo',
    'DeviceAudio',

    'Track',
    'Start',
    'Duration',
    'End',

    'Fps',
    'Container',
    'ContainerVideo',
    'ContainerAudio',
    'ContainerImage',

    'CodecVideo',
    'Crf',
    'Preset',
    'BitrateVideo',

    'CodecAudio',
    'BitrateAudio',
]

DEFAULTS = {
    'BitrateVideo': '1000k',
    'BitrateAudio': '128k',
#    'CodecVideo': 'copy',
#    'CodecAudio': 'copy',
    'Preset': 'medium',
    'Crf': 23,
    'Container': 'mp4',
    'ContainerVideo': 'mp4',
    'Fps': 25.0,
}

LABELS = {
    'DeviceVideo': 'V-Device',
    'DeviceAudio': 'A-Device',

    'Fps': 'FPS',

#    'Container': 'Container',
    'ContainerVideo': 'Container',
    'ContainerAudio': 'Format',
    'ContainerImage': 'Format',

    'CodecVideo': 'V-Codec',
    'Crf': 'CRF',
#    'Preset': 'Preset',
    'BitrateVideo': 'V-Bitrate',

    'CodecAudio': 'A-Codec',
    'BitrateAudio': 'A-Bitrate',
}
