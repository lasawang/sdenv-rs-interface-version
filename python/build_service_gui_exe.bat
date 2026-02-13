@echo off
setlocal

set ROOT_DIR=%~dp0..
cd /d "%ROOT_DIR%"
set BUILD_ROOT=%TEMP%\sdenv_pyinstaller

echo [1/3] Check PyInstaller...
where pyinstaller >nul 2>nul
if errorlevel 1 (
  echo PyInstaller is not installed.
  echo Run: pip install pyinstaller
  exit /b 1
)

echo [2/3] Build EXE...
if exist "%BUILD_ROOT%" rmdir /s /q "%BUILD_ROOT%"
mkdir "%BUILD_ROOT%\spec"
mkdir "%BUILD_ROOT%\build"
mkdir "%BUILD_ROOT%\dist"
copy /y "python\sdenv_service_gui.py" "%BUILD_ROOT%\sdenv_service_gui.py" >nul

pyinstaller --noconfirm --clean --onefile --windowed --name sdenv-service-gui ^
  --specpath "%BUILD_ROOT%\spec" ^
  --workpath "%BUILD_ROOT%\build" ^
  --distpath "%BUILD_ROOT%\dist" ^
  "%BUILD_ROOT%\sdenv_service_gui.py"
if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

if not exist "%ROOT_DIR%\dist" mkdir "%ROOT_DIR%\dist"
copy /y "%BUILD_ROOT%\dist\sdenv-service-gui.exe" "%ROOT_DIR%\dist\sdenv-service-gui.exe" >nul
if errorlevel 1 (
  echo Copy EXE failed.
  exit /b 1
)

echo [3/3] Done.
echo EXE: %ROOT_DIR%\dist\sdenv-service-gui.exe
echo.
echo Usage:
echo 1. Double click the EXE.
echo 2. Service auto-starts on app launch (or click "Start Service").
echo 3. Call API from python/sdenv_client.py with the shown host/port.

exit /b 0
