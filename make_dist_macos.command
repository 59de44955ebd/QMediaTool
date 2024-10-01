APP_NAME=QMediaTool
APP_ICON=app.icns

cd "$(dirname "$0")"

rm -R "dist/$APP_NAME" 2>/dev/null
rm -R "dist/$APP_NAME.app" 2>/dev/null
rm "dist/presets.db" 2>/dev/null
rm "dist/$APP_NAME.dmg" 2>/dev/null

echo
echo '****************************************'
echo 'Checking requirements...'
echo '****************************************'

pip install -r requirements.txt
pip install -r requirements_dist.txt

echo
echo '****************************************'
echo 'Running pyinstaller...'
echo '****************************************'

pyinstaller "${APP_NAME}_macos.spec"

echo
echo '****************************************'
echo 'Copying resources...'
echo '****************************************'

cp presets.db dist/

cp -R  resources/styles "dist/$APP_NAME.app/Contents/Resources/"
cp -R  resources/ui "dist/$APP_NAME.app/Contents/Resources/"
mkdir "dist/$APP_NAME.app/Contents/Resources/bin"
rsync -aq --exclude='*/.git*' resources/bin/macos "dist/$APP_NAME.app/Contents/Resources/bin"

rm "dist/$APP_NAME.app/Contents/Resources/ui/app.png"
rm "dist/$APP_NAME.app/Contents/Resources/ui/make_rcc.cmd"
rm "dist/$APP_NAME.app/Contents/Resources/ui/res.qrc"

echo
echo '****************************************'
echo 'Optimizing application...'
echo '****************************************'

rm -R "dist/$APP_NAME.app/Contents/Frameworks/PyQt5/uic"
rm -R "dist/$APP_NAME.app/Contents/Frameworks/PyQt5/Qt5/translations"

rm -R "dist/$APP_NAME.app/Contents/Frameworks/PyQt5/Qt5/lib/QtQml.framework"
rm -R "dist/$APP_NAME.app/Contents/Frameworks/PyQt5/Qt5/lib/QtQmlModels.framework"
rm -R "dist/$APP_NAME.app/Contents/Frameworks/PyQt5/Qt5/lib/QtQuick.framework"
rm -R "dist/$APP_NAME.app/Contents/Frameworks/PyQt5/Qt5/lib/QtSvg.framework"
rm -R "dist/$APP_NAME.app/Contents/Frameworks/PyQt5/Qt5/lib/QtWebSockets.framework"

rm -R "dist/$APP_NAME.app/Contents/Frameworks/PyQt5/Qt5/plugins/bearer"
rm -R "dist/$APP_NAME.app/Contents/Frameworks/PyQt5/Qt5/plugins/generic"
rm -R "dist/$APP_NAME.app/Contents/Frameworks/PyQt5/Qt5/plugins/iconengines"
rm -R "dist/$APP_NAME.app/Contents/Frameworks/PyQt5/Qt5/plugins/imageformats"
rm -R "dist/$APP_NAME.app/Contents/Frameworks/PyQt5/Qt5/plugins/platformthemes"

rm -R "dist/$APP_NAME.app/Contents/Frameworks/PyQt5/Qt5/plugins/platforms/libqminimal.dylib"
rm -R "dist/$APP_NAME.app/Contents/Frameworks/PyQt5/Qt5/plugins/platforms/libqoffscreen.dylib"
rm -R "dist/$APP_NAME.app/Contents/Frameworks/PyQt5/Qt5/plugins/platforms/libqwebgl.dylib"

echo
echo '****************************************'
echo 'Creating DMG...'
echo '****************************************'

mkdir dist/dmg
mkdir "dist/dmg/$APP_NAME"
mv "dist/$APP_NAME.app" "dist/dmg/$APP_NAME/"
mv "dist/presets.db" "dist/dmg/$APP_NAME/"

ln -s /Applications "dist/dmg/Applications"
hdiutil create -fs HFSX -format UDZO "dist/$APP_NAME.dmg" -imagekey zlib-level=9 -srcfolder "dist/dmg" -volname "$APP_NAME"

mv "dist/dmg/$APP_NAME/$APP_NAME.app" dist/
mv "dist/dmg/$APP_NAME/presets.db" dist/

rm -R dist/dmg

echo
echo '****************************************'
echo 'Done.'
echo '****************************************'
echo
