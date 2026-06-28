@echo off
REM ===================================================================
REM  Rebuild the Kebbet Zamen Windows app (KebbetZamen.exe) from source.
REM  Run this on a Windows PC that has Python 3 installed.
REM  Double-click this file, or run it from a command prompt.
REM ===================================================================

echo Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
  echo.
  echo ERROR: Could not install dependencies. Is Python installed and on PATH?
  pause
  exit /b 1
)

echo.
echo Building KebbetZamen.exe ...
pyinstaller --noconfirm KebbetZamen.spec
if errorlevel 1 (
  echo.
  echo ERROR: Build failed. See the messages above.
  pause
  exit /b 1
)

echo.
echo ===================================================================
echo  DONE. The new app is here:   dist\KebbetZamen.exe
echo.
echo  Next steps:
echo   1. Close the Kebbet Zamen app if it is currently running.
echo   2. Replace your old .exe / shortcut target with dist\KebbetZamen.exe
echo   3. Start the new app, then re-send the order from the extension.
echo ===================================================================
pause
