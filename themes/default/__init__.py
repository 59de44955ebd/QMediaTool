import os
from PyQt5.QtWidgets import qApp

# load style.css
p = os.path.dirname(os.path.realpath(__file__))+'/'
with open(p + 'style.css', 'r') as f:
    qApp.setStyleSheet(f.read())
