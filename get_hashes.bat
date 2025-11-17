@echo off
REM Generate file hashes for the PDF Compressor executable

set EXE_PATH=dist\PDF_Compressor\PDF_Compressor.exe

if not exist "%EXE_PATH%" (
    echo Error: %EXE_PATH% not found
    echo Please build the executable first with build.bat
    pause
    exit /b 1
)

echo ======================================
echo PDF Compressor - File Hashes
echo ======================================
echo.
echo File: %EXE_PATH%
echo.

echo **SHA256 Hash:**
echo.
echo ```
certutil -hashfile "%EXE_PATH%" SHA256 | findstr /v ":" | findstr /v "CertUtil"
echo ```
echo.

echo **MD5 Hash:**
echo.
echo ```
certutil -hashfile "%EXE_PATH%" MD5 | findstr /v ":" | findstr /v "CertUtil"
echo ```
echo.

echo ======================================
echo Copy the hashes above to update the
echo README.md 'File Verification' section
echo ======================================
echo.
pause
