@echo off
setlocal enableextensions enabledelayedexpansion

md build 2>nul
rd /S /Q build\exe.win-amd64-3.7 2>nul

python setup.py build_exe

::######################################
:: post-processing
::######################################

:: bug fix: python3.dll must be located in lib
move build\exe.win-amd64-3.7\python3.dll build\exe.win-amd64-3.7\lib\ >nul

:: copy resources to target dir
md build\exe.win-amd64-3.7\resources
md build\exe.win-amd64-3.7\resources\ui
copy resources\ui\help.ui build\exe.win-amd64-3.7\resources\ui\ >nul
copy resources\ui\main.ui build\exe.win-amd64-3.7\resources\ui\ >nul
copy resources\ui\presets.ui build\exe.win-amd64-3.7\resources\ui\ >nul
copy resources\ui\taskmanager.ui build\exe.win-amd64-3.7\resources\ui\ >nul
copy resources\ui\res.rcc build\exe.win-amd64-3.7\resources\ui\ >nul
xcopy /q resources\bash build\exe.win-amd64-3.7\resources\bash\ /E >nul
xcopy /q resources\bin\win build\exe.win-amd64-3.7\resources\bin\win\ /E >nul
copy README.md build\exe.win-amd64-3.7\ >nul
md build\exe.win-amd64-3.7\output

:: copy current presets.db to target dir
copy /y presets.db build\exe.win-amd64-3.7\ >nul

:: remove redundant DLLs
del /q build\exe.win-amd64-3.7\lib\PyQt5\Qt5*.dll
del build\exe.win-amd64-3.7\lib\PyQt5\Qt5\bin\libcrypto-1_1-x64.dll
del /q build\exe.win-amd64-3.7\lib\win32*.pyd
del build\exe.win-amd64-3.7\lib\pywintypes37.dll

:: remove needless folders
rd /S /Q build\exe.win-amd64-3.7\PyQt5.uic.widget-plugins
rd /S /Q build\exe.win-amd64-3.7\lib\PyQt5\Qt 2>nul
rd /S /Q build\exe.win-amd64-3.7\lib\PyQt5\Qt5\qml 2>nul
if exist build\exe.win-amd64-3.7\lib\PyQt5\Qt5\qml rd /s /q build\exe.win-amd64-3.7\lib\PyQt5\Qt5\qml
rd /S /Q build\exe.win-amd64-3.7\lib\PyQt5\Qt5\resources 2>nul
rd /S /Q build\exe.win-amd64-3.7\lib\PyQt5\Qt5\translations

:: remove needless plugins
set PLUGINS_NEEDED="platforms"
for /d %%a IN ("build\exe.win-amd64-3.7\lib\PyQt5\Qt5\plugins\*") do (
	call set str=%%PLUGINS_NEEDED:%%~nxa=%%
	if !str! == %PLUGINS_NEEDED% rd /S /Q  "%%a"
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
rd /s /q build\exe.win-amd64-3.7\lib\PyQt5\bindings

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
