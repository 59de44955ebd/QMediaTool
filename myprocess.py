"""
QMediaTool - MyProcess class
"""

from PyQt5.QtCore import QProcess


class MyProcess (QProcess):

    def kill (self):
        if 'ffmpeg' in self.program() or 'bash' in self.program():
            # exit cleanly by sending 'q'
            self.write(b'q')
            self.waitForBytesWritten()
            ok = self.waitForFinished(3000)
            if not ok:
                super().kill()
        else:
            super().kill()
            #self._proc.terminate() -> only for GUI apps, sends WM_CLOSE
