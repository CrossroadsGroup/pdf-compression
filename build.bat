@echo off
echo ========================================
echo Building PDF Compressor .exe
echo ========================================
echo.

echo Installing dependencies...
uv sync
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo Building executable with PyInstaller...
uv run pyinstaller --onedir --windowed --name="PDF_Compressor" --icon=NONE ^
    --collect-binaries=pyvips ^
    --hidden-import=pyvips ^
    --hidden-import=PIL ^
    --hidden-import=fitz ^
    --paths=src ^
    src/main.py

if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build complete!
echo ========================================
echo.
echo The application is located in: dist\PDF_Compressor\
echo Main executable: dist\PDF_Compressor\PDF_Compressor.exe
echo.
echo Distribute the entire PDF_Compressor folder to your team.
echo No Python installation required on their machines!
echo.
pause
