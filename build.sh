#!/bin/bash

echo "========================================"
echo "Building PDF Compressor"
echo "========================================"
echo ""

echo "Installing dependencies..."
uv sync
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

echo ""
echo "Building executable with PyInstaller..."

# For Mac, we use .app bundle instead of .exe
uv run pyinstaller --onedir --windowed --name="PDF_Compressor" \
    --collect-binaries=pyvips \
    --hidden-import=pyvips \
    --hidden-import=PIL \
    --hidden-import=fitz \
    --paths=src \
    src/main.py

if [ $? -ne 0 ]; then
    echo "ERROR: PyInstaller build failed"
    exit 1
fi

echo ""
echo "========================================"
echo "Build complete!"
echo "========================================"
echo ""
echo "The application is located in: dist/PDF_Compressor/"
echo "Main executable: dist/PDF_Compressor/PDF_Compressor"
echo ""
echo "Distribute the entire PDF_Compressor folder."
echo ""
echo "Note: This builds a Mac app. For Windows .exe,"
echo "you need to run build.bat on a Windows machine."
echo ""
