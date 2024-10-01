"""
QMediaTool - Task class
"""

import os
import tempfile
from const import IS_WIN, BASH


########################################
#
########################################
class Task():

    def __init__ (self, code, env={}, name=''):
        super().__init__()
        self.code = code
        self.env = env
        self.name = name
        self._tmpfile = None

    def __del__ (self):
        if self._tmpfile:
            os.remove(self._tmpfile)

    def run (self, proc):
        for k,v in self.env.items():
            os.environ[k] = str(v)
        if 'OUTPUTDIR' in self.env:
            proc.setWorkingDirectory(self.env['OUTPUTDIR'])
        command = os.path.expandvars(self.code)
        if IS_WIN or '\n' in command:
            # only when running external script file UTF-8 filenames are handled correctly in Windows!
            f = tempfile.NamedTemporaryFile()
            f.close()
            self._tmpfile = f.name
            with open(self._tmpfile, 'w') as f:
                f.write(command)
            proc.start(BASH, [self._tmpfile])
        else:
            proc.start(BASH, ['-c', command])
