@echo off
setlocal enableextensions enabledelayedexpansion

:: get python version as strings, e.g. "3.10" and "310"
for /f "usebackq delims=" %%a in (`python -V`) do set V=%%a
set V=%V:Python =%
for /f "tokens=1,2 delims=." %%a in ("%V%") do set VERSION_DOT=%%a.%%b
set VERSION_NUM=%VERSION_DOT:.=%

set EXE_DIR=exe.win-amd64-%VERSION_DOT%

md build 2>nul
rd /s /q %EXE_DIR% 2>nul

python setup.py build_exe

::######################################
:: post-processing
::######################################

:: bug fix: python3.dll must be located in lib
move build\%EXE_DIR%\python3.dll build\%EXE_DIR%\lib\ >nul

:: copy resources to target dir
md build\%EXE_DIR%\resources
md build\%EXE_DIR%\resources\ui
copy resources\ui\help.ui build\%EXE_DIR%\resources\ui\ >nul
copy resources\ui\main.ui build\%EXE_DIR%\resources\ui\ >nul
copy resources\ui\presets.ui build\%EXE_DIR%\resources\ui\ >nul
copy resources\ui\taskmanager.ui build\%EXE_DIR%\resources\ui\ >nul
copy resources\ui\res.rcc build\%EXE_DIR%\resources\ui\ >nul
xcopy /q resources\bash build\%EXE_DIR%\resources\bash\ /E >nul
xcopy /q resources\bin\win build\%EXE_DIR%\resources\bin\win\ /E >nul
copy README.md build\%EXE_DIR%\ >nul
md build\%EXE_DIR%\output

:: copy current presets.db to target dir
copy /y presets.db build\%EXE_DIR%\ >nul

:: remove redundant DLLs
del /q build\%EXE_DIR%\lib\PyQt5\Qt5*.dll
del build\%EXE_DIR%\lib\PyQt5\Qt5\bin\libcrypto-1_1-x64.dll
del /q build\%EXE_DIR%\lib\win32*.pyd 2>nul
del build\%EXE_DIR%\lib\pywintypes37.dll 2>nul

:: remove needless folders
rd /s /q build\%EXE_DIR%\PyQt5.uic.widget-plugins
rd /s /q build\%EXE_DIR%\lib\PyQt5\Qt 2>nul
rd /s /q build\%EXE_DIR%\lib\PyQt5\Qt5\qml 2>nul
if exist build\%EXE_DIR%\lib\PyQt5\Qt5\qml rd /s /q build\%EXE_DIR%\lib\PyQt5\Qt5\qml
rd /s /q build\%EXE_DIR%\lib\PyQt5\Qt5\qsci 2>nul
rd /s /q build\%EXE_DIR%\lib\PyQt5\Qt5\resources 2>nul
rd /s /q build\%EXE_DIR%\lib\PyQt5\Qt5\translations 2>nul

:: remove needless plugins
set PLUGINS_NEEDED="platforms:styles"
for /d %%a in ("build\%EXE_DIR%\lib\PyQt5\Qt5\plugins\*") do (
	call set str=%%PLUGINS_NEEDED:%%~nxa=%%
	if !str! == %PLUGINS_NEEDED% rd /s /q  "%%a"
)

:: remove needless platforms
for %%a in ("build\%EXE_DIR%\lib\PyQt5\Qt5\plugins\platforms\*") do (
	if /i not "%%~nxa"=="qwindows.dll" del "%%a"
)

:: remove needless dlls
set DLLS_NEEDED="libcrypto-1_1-x64.dll:msvcp140.dll:msvcp140_1.dll:msvcp140_2.dll:qt.conf:Qt5Core.dll:Qt5Gui.dll:Qt5Network.dll:Qt5Widgets.dll:Qt5WinExtras.dll:vcruntime140.dll:vcruntime140_1.dll"
for %%a in ("build\%EXE_DIR%\lib\PyQt5\Qt5\bin\*") do (
	call set str=%%DLLS_NEEDED:%%~nxa=%%
	if !str! == %DLLS_NEEDED% del "%%a"
)

:: remove needless bindings
rd /s /q build\%EXE_DIR%\lib\PyQt5\bindings

:: remove needless pyi files
set PYI_NEEDED="QtCore.pyi:QtGui.pyi:QtNetwork.pyi:QtWidgets.pyi:QtWinExtras.pyi:sip.pyi"
for %%a IN ("build\%EXE_DIR%\lib\PyQt5\*.pyi") do (
	call set str=%%PYI_NEEDED:%%~nxa=%%
	if !str! == %PYI_NEEDED% del "%%a"
)

:: remove needless pyd files
set PYD_NEEDED="pylupdate.pyd:pyrcc.pyd:Qt.pyd:QtCore.pyd:QtGui.pyd:QtNetwork.pyd:QtWidgets.pyd:QtWinExtras.pyd:sip.cp%VERSION_NUM%-win_amd64.pyd"
for %%a in ("build\%EXE_DIR%\lib\PyQt5\*.pyd") do (
	call set str=%%PYD_NEEDED:%%~nxa=%%
	if !str! == %PYD_NEEDED% del "%%a"
)

:: create zip
cd build
ren %EXE_DIR% QMediaTool
del QMediaTool-windows-x64.zip 2>nul
zip -q -r QMediaTool-windows-x64.zip QMediaTool
ren QMediaTool %EXE_DIR%
cd ..

echo.
echo Done.
