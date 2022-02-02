@echo off
@setlocal enableextensions enabledelayedexpansion

rmdir /S /Q build\exe.win-amd64-3.7 2>nul

python setup.py build_exe

::######################################
:: post-processing
::######################################

:: bug fix: python3.dll must be located in lib
move build\exe.win-amd64-3.7\python3.dll build\exe.win-amd64-3.7\lib\

:: copy resources to target dir
mkdir build\exe.win-amd64-3.7\resources
mkdir build\exe.win-amd64-3.7\resources\ui
copy resources\ui\help.ui build\exe.win-amd64-3.7\resources\ui\
copy resources\ui\main.ui build\exe.win-amd64-3.7\resources\ui\
copy resources\ui\presets.ui build\exe.win-amd64-3.7\resources\ui\
copy resources\ui\taskmanager.ui build\exe.win-amd64-3.7\resources\ui\
copy resources\ui\res.rcc build\exe.win-amd64-3.7\resources\ui\
xcopy resources\bash build\exe.win-amd64-3.7\resources\bash\ /E
xcopy resources\bin\win build\exe.win-amd64-3.7\resources\bin\win\ /E

:: copy current presets.db to target dir
copy /y presets.db build\exe.win-amd64-3.7\

:: remove needless folders
rmdir /S /Q build\exe.win-amd64-3.7\PyQt5.uic.widget-plugins
rmdir /S /Q build\exe.win-amd64-3.7\lib\PyQt5\Qt
rmdir /S /Q build\exe.win-amd64-3.7\lib\PyQt5\Qt5\qml
rmdir /S /Q build\exe.win-amd64-3.7\lib\PyQt5\Qt5\resources
rmdir /S /Q build\exe.win-amd64-3.7\lib\PyQt5\Qt5\translations

:: remove needless plugins
set PLUGINS_NEEDED="platforms;platformthemes"
for /d %%a IN ("build\exe.win-amd64-3.7\lib\PyQt5\Qt5\plugins\*") do (
	call set str=%%PLUGINS_NEEDED:%%~nxa=%%
	if !str! == %PLUGINS_NEEDED% rmdir /S /Q  "%%a"
)

:: remove needless platforms
for %%a IN ("build\exe.win-amd64-3.7\lib\PyQt5\Qt5\plugins\platforms\*") do (
	if /i not "%%~nxa"=="qwindows.dll" del "%%a"
)

:: remove needless dlls
set DLLS_NEEDED="libcrypto-1_1-x64.dll:msvcp140.dll:msvcp140_1.dll:msvcp140_2.dll:qt.conf:Qt5Core.dll:Qt5Gui.dll:Qt5Network.dll:Qt5Widgets.dll:Qt5WinExtras.dll:vcruntime140.dll:vcruntime140_1.dll"
for %%a IN ("build\exe.win-amd64-3.7\lib\PyQt5\Qt5\bin\*") do (
	call set str=%%DLLS_NEEDED:%%~nxa=%%
	if !str! == %DLLS_NEEDED% del "%%a"
)

:: remove needless bindings
set BINDINGS_NEEDED="QtCore:QtGui:QtNetwork:QtWidgets:QtWinExtras"
for /d %%a IN ("build\exe.win-amd64-3.7\lib\PyQt5\bindings\*") do (
	call set str=%%BINDINGS_NEEDED:%%~nxa=%%
	if !str! == %BINDINGS_NEEDED% rmdir /S /Q  "%%a"
)

:: remove needless pyi files
set PYI_NEEDED="QtCore.pyi:QtGui.pyi:QtNetwork.pyi:QtWidgets.pyi:QtWinExtras.pyi:sip.pyi"
for %%a IN ("build\exe.win-amd64-3.7\lib\PyQt5\*.pyi") do (
	call set str=%%PYI_NEEDED:%%~nxa=%%
	if !str! == %PYI_NEEDED% del "%%a"
)

:: remove needless pyd files
set PYD_NEEDED="pylupdate.pyd:pyrcc.pyd:Qt.pyd:QtCore.pyd:QtGui.pyd:QtNetwork.pyd:QtWidgets.pyd:QtWinExtras.pyd:sip.cp37-win_amd64.pyd"
for %%a IN ("build\exe.win-amd64-3.7\lib\PyQt5\*.pyd") do (
	call set str=%%PYD_NEEDED:%%~nxa=%%
	if !str! == %PYD_NEEDED% del "%%a"
)

:: create zip
cd build
ren exe.win-amd64-3.7 QMediaTool
del QMediaTool-windows-x64.zip 2>nul
zip -q -r QMediaTool-windows-x64.zip QMediaTool
ren QMediaTool exe.win-amd64-3.7
cd ..

echo.
echo Done.
