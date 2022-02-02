#!/bin/bash

rm -R -f build/exe.macosx-10.9-x86_64-3.7 2>/dev/null
rm -R -f build/QMediaTool.app 2>/dev/null

python3 setup.py bdist_mac --iconfile app.icns

########################################
# post-processing
#######################################

# copy resources to target dir
mkdir build/QMediaTool.app/Contents/Resources/ui
cp resources/ui/help.ui build/QMediaTool.app/Contents/Resources/ui/
cp resources/ui/main.ui build/QMediaTool.app/Contents/Resources/ui/
cp resources/ui/presets.ui build/QMediaTool.app/Contents/Resources/ui/
cp resources/ui/taskmanager.ui build/QMediaTool.app/Contents/Resources/ui/
cp resources/ui/res.rcc build/QMediaTool.app/Contents/Resources/ui/
mkdir build/QMediaTool.app/Contents/Resources/bin
cp -R resources/bin/macos build/QMediaTool.app/Contents/Resources/bin/

# copy current presets.db to target dir
cp presets.db build/

# remove needless folders
rm -R -f build/QMediaTool.app/Contents/MacOS/PyQt5.uic.widget-plugins
rm -R -f build/QMediaTool.app/Contents/MacOS/lib/PyQt5/Qt/qml
rm -R -f build/QMediaTool.app/Contents/MacOS/lib/PyQt5/Qt/qsci
rm -R -f build/QMediaTool.app/Contents/MacOS/lib/PyQt5/Qt/translations

# remove needless plugins
find build/QMediaTool.app/Contents/MacOS/lib/PyQt5/Qt/plugins -mindepth 1 -maxdepth 1 -type d \
-not -name 'platforms' -not -name 'platformthemes' \
-print0|xargs -0 -I {} rm -R -f {}
rm /Users/fluxus/Desktop/QMediaTool/build/QMediaTool.app/Contents/MacOS/lib/PyQt5/Qt/plugins/platforms/libqoffscreen.dylib
rm /Users/fluxus/Desktop/QMediaTool/build/QMediaTool.app/Contents/MacOS/lib/PyQt5/Qt/plugins/platforms/libqwebgl.dylib

# remove needless frameworks
find build/QMediaTool.app/Contents/MacOS/lib/PyQt5/Qt/lib -mindepth 1 -maxdepth 1 -type d \
-not -name QtCore.framework -not -name QtDBus.framework -not -name QtGui.framework \
-not -name QtNetwork.framework -not -name QtPrintSupport.framework -not -name QtWidgets.framework \
-print0|xargs -0 -I {} rm -R -f {}

# remove needless bindings
find build/QMediaTool.app/Contents/MacOS/lib/PyQt5/bindings -mindepth 1 -maxdepth 1 -type d \
-not -name QtCore -not -name QtDBus -not -name QtGui \
-not -name QtNetwork -not -name QtPrintSupport -not -name QtWidgets \
-print0|xargs -0 -I {} rm -R -f {}

# remove needless pyi files
find build/QMediaTool.app/Contents/MacOS/lib/PyQt5/*.pyi -maxdepth 1 -type f \
-not -name QtCore.pyi -not -name QtDBus.pyi -not -name QtGui.pyi \
-not -name QtNetwork.pyi -not -name QtPrintSupport.pyi -not -name QtWidgets.pyi \
-print0 | xargs -0 -I {} rm {}

# remove needless so files
find build/QMediaTool.app/Contents/MacOS/lib/PyQt5/*.abi3.so -maxdepth 1 -type f \
-not -name QtCore.abi3.so -not -name QtDBus.abi3.so -not -name QtGui.abi3.so \
-not -name QtNetwork.abi3.so -not -name QtPrintSupport.abi3.so -not -name QtWidgets.abi3.so \
-not -name Qt.abi3.so -not -name pylupdate.abi3.so -not -name pyrcc.abi3.so \
-print0 | xargs -0 -I {} rm {}

# create DMG
rm build/QMediaTool.dmg 2>/dev/null
rm -R -f build/dist 2>/dev/null
mkdir build/dist
mkdir build/dist/QMediaTool
cp -R build/QMediaTool.app build/dist/QMediaTool/QMediaTool.app
cp presets.db build/dist/QMediaTool/
python3 make_dmg.py "build/dist" "build/QMediaTool.dmg" "QMediaTool"

# clean up
rm -R -f build/dist 2>/dev/null
rm -R -f build/exe.macosx-10.9-x86_64-3.7 2>/dev/null

echo
echo "Done."
