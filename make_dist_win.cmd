@echo off
setlocal EnableDelayedExpansion
cd /d %~dp0

:: config
set APP_NAME=QMediaTool
set APP_ICON=app.ico
set APP_DIR=dist\%APP_NAME%

:: cleanup
rmdir /s /q "dist\%APP_NAME%" 2>nul
del "dist\%APP_NAME%-x64-portable.7z" 2>nul

echo.
echo ****************************************
echo Checking requirements...
echo ****************************************

pip install -r requirements.txt
pip install -r requirements_dist.txt

echo.
echo ****************************************
echo Running pyinstaller...
echo ****************************************

pyinstaller --noupx -w -i "%APP_ICON%" -n "%APP_NAME%" --version-file=version_res.txt --hidden-import taskmanager --hidden-import mytreewidget -D main.py

echo.
echo ****************************************
echo Optimizing dist folder...
echo ****************************************

md "%APP_DIR%\resources"
xcopy /q /e resources\bash "%APP_DIR%\resources\bash\"
xcopy /q /e resources\bin\win "%APP_DIR%\resources\bin\win\"
xcopy /q /e resources\styles "%APP_DIR%\resources\styles\"
xcopy /q /e resources\ui "%APP_DIR%\resources\ui\"
del "%APP_DIR%\resources\ui\app.png"
del "%APP_DIR%\resources\ui\make_rcc.cmd"
del "%APP_DIR%\resources\ui\res.qrc"

copy presets.db "%APP_DIR%\" >nul

md "%APP_DIR%\output"

del /q "%APP_DIR%\_internal\api-ms-win-core-*"
del /q "%APP_DIR%\_internal\api-ms-win-crt-*"

del "%APP_DIR%\_internal\libssl-3.dll"

del "%APP_DIR%\_internal\PyQt5\Qt5\bin\d3dcompiler_47.dll"
del "%APP_DIR%\_internal\PyQt5\Qt5\bin\libcrypto-1_1-x64.dll"
del "%APP_DIR%\_internal\PyQt5\Qt5\bin\libEGL.dll"
del "%APP_DIR%\_internal\PyQt5\Qt5\bin\libGLESv2.dll"
del "%APP_DIR%\_internal\PyQt5\Qt5\bin\libssl-1_1-x64.dll"
del "%APP_DIR%\_internal\PyQt5\Qt5\bin\opengl32sw.dll"
del "%APP_DIR%\_internal\PyQt5\Qt5\bin\Qt5DBus.dll"
del "%APP_DIR%\_internal\PyQt5\Qt5\bin\Qt5Qml.dll"
del "%APP_DIR%\_internal\PyQt5\Qt5\bin\Qt5QmlModels.dll"
del "%APP_DIR%\_internal\PyQt5\Qt5\bin\Qt5Quick.dll"
del "%APP_DIR%\_internal\PyQt5\Qt5\bin\Qt5Svg.dll"
del "%APP_DIR%\_internal\PyQt5\Qt5\bin\Qt5WebSockets.dll"
del "%APP_DIR%\_internal\PyQt5\Qt5\bin\VCRUNTIME140.dll"

rmdir /S /Q "%APP_DIR%\_internal\pymediainfo-6.1.0.dist-info"
rmdir /S /Q "%APP_DIR%\_internal\PyQt5\Qt5\plugins\bearer"
rmdir /S /Q "%APP_DIR%\_internal\PyQt5\Qt5\plugins\generic"
rmdir /S /Q "%APP_DIR%\_internal\PyQt5\Qt5\plugins\iconengines"
rmdir /S /Q "%APP_DIR%\_internal\PyQt5\Qt5\plugins\imageformats"
rmdir /S /Q "%APP_DIR%\_internal\PyQt5\Qt5\plugins\platformthemes"
rmdir /S /Q "%APP_DIR%\_internal\PyQt5\Qt5\translations"
rmdir /S /Q "%APP_DIR%\_internal\PyQt5\uic"

del "%APP_DIR%\_internal\PyQt5\Qt5\plugins\platforms\qminimal.dll"
del "%APP_DIR%\_internal\PyQt5\Qt5\plugins\platforms\qoffscreen.dll"
del "%APP_DIR%\_internal\PyQt5\Qt5\plugins\platforms\qwebgl.dll"

call :create_7z

echo.
echo ****************************************
echo Done.
echo ****************************************
echo.
pause

endlocal
goto :eof

:create_7z
if not exist "C:\Program Files\7-Zip\" (
	echo.
	echo ****************************************
	echo 7z.exe not found at default location, omitting .7z creation...
	echo ****************************************
	exit /B
)
echo.
echo ****************************************
echo Creating .7z archive...
echo ****************************************
cd dist
set PATH=C:\Program Files\7-Zip;%PATH%
7z a "%APP_NAME%-x64-portable.7z" "%APP_NAME%\*"
cd ..
exit /B
