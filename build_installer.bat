@echo off
echo ========================================
echo Building PDF Compressor Installer
echo ========================================
echo.

REM Check if Inno Setup is installed
set "INNO_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist "%INNO_PATH%" (
    echo ERROR: Inno Setup not found
    echo Expected location: C:\Program Files ^(x86^)\Inno Setup 6\ISCC.exe
    echo.
    echo Please download and install Inno Setup from:
    echo https://jrsoftware.org/isdl.php
    echo.
    pause
    exit /b 1
)

REM Step 1: Build the application
echo Step 1: Building application with PyInstaller...
call build.bat
if errorlevel 1 (
    echo ERROR: Application build failed
    pause
    exit /b 1
)

echo.
echo Step 2: Creating installer with Inno Setup...
"%INNO_PATH%" installer.iss
if errorlevel 1 (
    echo ERROR: Installer creation failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build complete!
echo ========================================
echo.
echo Installer location: dist\installer\PDF_Compressor_Setup.exe
echo.
echo This installer:
echo - Includes all application files
echo - Creates Start Menu shortcut
echo - Optional Desktop icon
echo - Proper uninstaller in Add/Remove Programs
echo - Requests admin privileges for installation
echo.
pause
