"""
QMediaTool - constants
"""

import os
import sys

APP_NAME = 'QMediaTool'
APP_VERSION = 4

IS_WIN = os.name == 'nt'

if getattr(sys, "frozen", False):
    APP_PATH = os.path.dirname(os.path.realpath(sys.executable))
    if IS_WIN:
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

BIN_DIR = RES_DIR + '/bin/' + ('win' if IS_WIN else 'macos')
BASH = RES_DIR + '/bash/bin/bash' if IS_WIN else '/bin/bash'

INPUT_TYPE_FILE = 0
INPUT_TYPE_FILES = 1
INPUT_TYPE_URL = 2
INPUT_TYPE_NONE = 3

CONTAINERS = ['aac','ac3','asf','au','avi','caf','flac','flv','gif','h264','m4a','m4v','mkv','mov','mp2','mp3','mp4','mpeg','ogg','rm','vob','wav','webm']
#'ape,flac,3gp'

CONTAINERS_AUDIO = ['aac','ac3','aiff','au','flac','m4a','mp3','ogg','wav']

CONTAINERS_VIDEO = ['mp4','mov','mkv','avi','flv']

CONTAINERS_IMAGE = ['bmp','jpg','png']

CODECS_VIDEO = ['libx264','a64multi','a64multi5','alias_pix','amv','apng','asv1','asv2','libaom-av1','avrp','avui','ayuv','bmp','cinepak','cljr','vc2','dnxhd','dpx','dvvideo','ffv1','ffvhuff','fits','flashsv','flashsv2','flv','gif','h261','h263','h263p','libx264rgb','h264_amf','h264_nvenc','h264_qsv','nvenc','nvenc_h264','hap','libx265','nvenc_hevc','hevc_amf','hevc_nvenc','hevc_qsv','huffyuv','jpeg2000','libopenjpeg','jpegls','ljpeg','magicyuv','mjpeg','mjpeg_qsv','mpeg1video','mpeg2video','mpeg2_qsv','mpeg4','libxvid','msmpeg4v2','msmpeg4','msvideo1','pam','pbm','pcx','pgm','pgmyuv','png','ppm','prores','prores_aw','prores_ks','qtrle','r10k','r210','rawvideo','roqvideo','rv10','rv20','sgi','snow','sunrast','svq1','targa','libtheora','tiff','utvideo','v210','v308','v408','v410','libvpx','libvpx-vp9','libwebp','wmv1','wmv2','wrapped_avframe','xbm','xface','xwd','y41p','yuv4']

CODECS_AUDIO = ['aac','ac3','ac3_fixed','adpcm_adx','g722','g726','g726le','adpcm_ima_qt','adpcm_ima_wav','adpcm_ms','adpcm_swf','adpcm_yamaha','alac','libopencore_amrnb','libvo_amrwbenc','aptx','aptx_hd','comfortnoise','dca','eac3','flac','g723_1','mlp','mp2','mp2fixed','libtwolame','libmp3lame','libshine','nellymoser','opus','libopus','pcm_alaw','pcm_dvd','pcm_f32be','pcm_f32le','pcm_f64be','pcm_f64le','pcm_mulaw','pcm_s16be','pcm_s16be_planar','pcm_s16le','pcm_s16le_planar','pcm_s24be','pcm_s24daud','pcm_s24le','pcm_s24le_planar','pcm_s32be','pcm_s32le','pcm_s32le_planar','pcm_s64be','pcm_s64le','pcm_s8','pcm_s8_planar','pcm_u16be','pcm_u16le','pcm_u24be','pcm_u24le','pcm_u32be','pcm_u32le','pcm_u8','pcm_vidc','real_144','roq_dpcm','s302m','sbc','sonic','sonicls','libspeex','truehd','tta','vorbis','libvorbis','wavpack','libwavpack','wmav1','wmav2']

#CODECS_SUBS = ['ssa','ass','dvbsub','dvdsub','mov_text','srt','subrip','text','webvtt','xsub']

PRESETS = ['ultrafast','superfast','veryfast','faster','fast','medium','slow','slower','veryslow']
