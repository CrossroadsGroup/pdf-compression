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
uv run pyinstaller --onefile --windowed --name="PDF_Compressor" --icon=NONE ^
    --add-data="pdf_compress.py;." ^
    --collect-binaries=pyvips ^
    --hidden-import=pyvips ^
    --hidden-import=PIL ^
    --hidden-import=fitz ^
    app.py

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
echo The executable is located in: dist\PDF_Compressor.exe
echo.
echo You can now distribute this .exe file to your team.
echo No Python installation required on their machines!
echo.
pause
