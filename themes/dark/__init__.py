import os
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

# set style
QApplication.setStyle('Fusion')

# set palette
pal = QPalette()
pal.setColor(QPalette.Window, QColor(53,53,53))
pal.setColor(QPalette.WindowText, Qt.white)
pal.setColor(QPalette.Disabled, QPalette.WindowText, QColor(127,127,127))
pal.setColor(QPalette.Base, QColor(42,42,42))
pal.setColor(QPalette.AlternateBase, QColor(66,66,66))
pal.setColor(QPalette.ToolTipBase, Qt.white)
pal.setColor(QPalette.ToolTipText, Qt.white)
pal.setColor(QPalette.Text, Qt.white)
pal.setColor(QPalette.Disabled, QPalette.Text, QColor(127,127,127))
pal.setColor(QPalette.Dark, QColor(35,35,35))
pal.setColor(QPalette.Shadow, QColor(20,20,20))
pal.setColor(QPalette.Button, QColor(53,53,53))
pal.setColor(QPalette.ButtonText, Qt.white)
pal.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127,127,127))
pal.setColor(QPalette.BrightText, Qt.red)
pal.setColor(QPalette.Link, QColor(42,130,218))
pal.setColor(QPalette.Highlight, QColor(42,130,218))
pal.setColor(QPalette.Disabled, QPalette.Highlight, QColor(80,80,80))
pal.setColor(QPalette.HighlightedText, Qt.white)
pal.setColor(QPalette.Disabled, QPalette.HighlightedText, QColor(127,127,127))
qApp.setPalette(pal)
		
# load style.css
p = os.path.dirname(os.path.realpath(__file__))+'/'
fn = p + 'style.css'
with open(fn, 'r') as f:
	css = f.read()
	qApp.setStyleSheet(css)
		
# load icon recource file
#QResource.registerResource(p+'icons.rcc')
