#!/bin/bash
# Generate file hashes for the PDF Compressor executable

EXE_PATH="dist/PDF_Compressor/PDF_Compressor.exe"

if [ ! -f "$EXE_PATH" ]; then
    echo "Error: $EXE_PATH not found"
    echo "Please build the executable first with build.bat or build.sh"
    exit 1
fi

echo "======================================"
echo "PDF Compressor - File Hashes"
echo "======================================"
echo ""
echo "File: $EXE_PATH"
echo "Size: $(ls -lh "$EXE_PATH" | awk '{print $5}')"
echo ""

echo "**SHA256 Hash:**"
echo ""
echo "\`\`\`"
if command -v sha256sum &> /dev/null; then
    sha256sum "$EXE_PATH" | awk '{print $1}'
else
    shasum -a 256 "$EXE_PATH" | awk '{print $1}'
fi
echo "\`\`\`"
echo ""

echo "**MD5 Hash:**"
echo ""
echo "\`\`\`"
if command -v md5sum &> /dev/null; then
    md5sum "$EXE_PATH" | awk '{print $1}'
else
    md5 "$EXE_PATH" | awk '{print $4}'
fi
echo "\`\`\`"
echo ""

echo "======================================"
echo "Copy the hashes above to update the"
echo "README.md 'File Verification' section"
echo "======================================"
