# PDF Compressor Desktop Tool

A desktop application to compress PDF files before uploading to file sharing platforms.

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

![PDF Compressor Tool](assets/tool_image.png)

## For Team Members (Using the Tool)

### Quick Start

The pre-built executable is included in this repository at releases.

### What This Tool Does

- Compresses all PDFs larger than 5MB in a selected folder
- Processes all subdirectories automatically
- Reduces file sizes by 85-95% on average
- Replaces original files only if compression helps
- No internet connection required - runs completely offline

### How to Use

1. **Locate** the `PDF_Compressor` folder from the distribution
2. **Double-click** `PDF_Compressor.exe` inside the folder to open the application
3. **Click "Browse..."** to select the folder containing your PDFs
4. **Adjust settings** (optional):
   - Image Quality: 50-100 (default: 90)
     - Lower = smaller files, slightly lower quality
   - Max DPI: 50-600 (default: 250)
     - Lower = smaller files, may affect print quality
5. **Click "Compress PDFs"** and wait for completion
6. **View results** in the progress window

### Expected Performance

- Typical compression: 85-95% size reduction
- Example: 1GB folder → ~100MB after compression

### Safety Features

- Only processes PDFs larger than 5MB
- Original files are kept if compression doesn't help
- Failed compressions leave originals untouched
- Files are compressed in-place (no separate output folder)

### Security Notice

This tool is designed to process trusted PDF files. Only use it with PDFs from trusted sources, as it processes embedded images without sandbox restrictions.

**Path Restrictions:**
For safety, the tool prevents processing files in:

**Completely Blocked (including subfolders):**

- System directories: `C:\Windows`, `C:\Program Files`, `C:\ProgramData`
- System binaries: `/usr`, `/bin`, `/sbin`, `/etc`, `/var`
- User data: `AppData`, `$Recycle.Bin`
- Drive roots: `C:\`, `D:\`, etc.

**Root Only Blocked (subfolders allowed):**

- User home directory: `C:\Users\YourName`
- Common folders: `Desktop`, `Documents`, `Downloads`, `Pictures`, `Music`, `Videos`
- OneDrive roots: `OneDrive`, `OneDrive - Personal`, `OneDrive - CompanyName`

**Examples:**

- ❌ Blocked: `C:\Users\YourName\Downloads`
- ✅ Allowed: `C:\Users\YourName\Downloads\Q2_2025_Reports`
- ❌ Blocked: `OneDrive - CompanyName`
- ✅ Allowed: `OneDrive - CompanyName\ClientProjects\ACME`

### File Verification (tag 0.0.1 for exe)

**SHA256 Hash:**

```
dad6164f8dcdf02fad6ad7a30c9b6a79a34fa00c543f8473424ba0700771d011

```

**Note:** Hash values change with each rebuild. Check the latest release for current hashes.

### Troubleshooting

**Windows SmartScreen Warning**

- Windows may show "Windows protected your PC" when first running the app
- This is normal for unsigned executables
- Click **"More info"** then **"Run anyway"** to proceed
- The app is safe - it's built from this open-source code

**"No PDF files >5MB found"**

- Make sure your folder contains PDFs larger than 5MB
- Check that you selected the correct folder

**Application won't start**

- Make sure you're running on Windows 10 or later
- Try running as Administrator (right-click → Run as administrator)
- Keep all files in the PDF_Compressor folder together - the .exe needs the supporting files

**Compression seems slow**

- This is normal for large files or many files
- You can leave it running in the background
- Typical: 5-10 seconds per 20MB file

---

## For Developers (Building the Tool)

### Prerequisites

- Python 3.12+
- [uv](https://github.com/astral-sh/uv) package manager
- Windows (for building Windows .exe) or macOS/Linux

Note: All dependencies including libvips binaries are automatically installed via `pyvips-binary` when you run `uv sync`.

### Building the Executable

1. Clone this repository
2. Run the build script:

   **Windows:**

   ```bash
   build.bat
   ```

   **macOS/Linux:**

   ```bash
   ./build.sh
   ```

3. The application will be created in `dist/PDF_Compressor/` folder
   - Windows: Run `dist/PDF_Compressor/PDF_Compressor.exe`
   - macOS/Linux: Run `dist/PDF_Compressor/PDF_Compressor`

### Building the Windows Installer (Recommended)

1. Install [Inno Setup](https://jrsoftware.org/isdl.php) (free, Windows only)
2. Run the installer build script:

   ```bash
   .\build_installer.bat
   ```

3. The installer will be created: `dist/installer/PDF_Compressor_Setup.exe`

**Note:** The installer is unsigned (no code signing certificate). Users will see a SmartScreen warning - this is normal for open source apps. Just click "More info" → "Run anyway".

### Manual Build Steps

If you prefer to build manually:

```bash
uv sync

uv run pyinstaller --onedir --windowed --name="PDF_Compressor" \
    --collect-binaries=pyvips \
    --hidden-import=pyvips \
    --hidden-import=PIL \
    --hidden-import=fitz \
    --paths=src \
    src/main.py
```

**Why `--onedir` instead of `--onefile`?**

- `--onedir` creates a folder with the .exe and all dependencies
- Avoids Windows security issues with temp file extraction
- More reliable in corporate environments with antivirus/security software
- Prevents "Failed to load Python DLL" errors

### Distribution

After building:

1. The application is in the `dist/PDF_Compressor/` folder
2. Distribute the **entire folder** to team members (as a .zip file)
3. Team members should:
   - Extract the entire folder
   - Keep all files together in the same folder
   - Run `PDF_Compressor.exe` from inside the folder
4. Team members do NOT need Python installed

### File Structure

```
pdf-compression/
├── src/
│   ├── main.py                    # Application entry point
│   ├── gui/
│   │   ├── app.py                 # Main GUI application
│   │   └── path_validator.py     # Path restriction logic
│   └── compression/
│       ├── pdf_processor.py       # PDF compression functions
│       └── image_optimizer.py     # Image optimization (pyvips/PIL)
├── tests/
│   ├── test_path_validator.py     # Path validation tests (Windows/Mac)
│   ├── test_pdf_processor.py      # PDF compression tests
│   ├── test_image_optimizer.py    # Image optimization tests
│   └── conftest.py                # Pytest configuration
├── pyproject.toml                 # Python project configuration
├── pytest.ini                     # Pytest configuration
├── uv.lock                        # Locked dependencies
├── build.bat                      # Windows build script
├── build.sh                       # macOS/Linux build script
├── build_installer.bat            # Build Windows installer
├── build_installer.sh             # Installer build info (Mac/Linux)
├── installer.iss                  # Inno Setup installer script
├── get_hashes.bat                 # Generate file hashes (Windows)
├── get_hashes.sh                  # Generate file hashes (macOS/Linux)
├── .gitignore                     # Git ignore rules
├── LICENSE                        # AGPL-3.0 license
└── README.md                      # This file
```

### Performance Notes

- Uses pyvips for fast image processing (3-5x faster than PIL)
- Typical processing time: 5-10 seconds per 20MB PDF
- Processes one file at a time (no concurrent processing in desktop version)
- Compression time depends on:
  - File size
  - Number of images in PDF
  - Image resolution and complexity
  - CPU speed

### Development Workflow

To test changes locally:

```bash
uv run python -m src.main
```

To rebuild after making changes:

1. Update the code in `src/` directory
2. Rebuild the executable:
   ```bash
   build.bat          # Windows
   ./build.sh         # macOS/Linux
   ```
3. Generate new file hashes:
   ```bash
   get_hashes.bat     # Windows
   ./get_hashes.sh    # macOS/Linux
   ```
4. Update the README with the new hashes (if needed for IT approval)
5. Distribute the new executable to team members

### Running Tests

The project includes comprehensive tests for path validation, PDF compression, and image optimization.

**Install test dependencies:**

```bash
uv sync --extra dev
```

**Run all tests:**

```bash
uv run pytest
```

**Run specific test files:**

```bash
uv run pytest tests/test_path_validator.py
uv run pytest tests/test_pdf_processor.py
uv run pytest tests/test_image_optimizer.py
```

**Run tests with coverage:**

```bash
uv run pytest --cov=src --cov-report=term-missing
```

**Platform-Specific Tests:**

The path validation tests are platform-specific and will automatically skip tests for other platforms:

- **On Mac/Linux**: Windows tests are skipped, Unix tests run
- **On Windows**: Unix tests are skipped, Windows tests run

```bash
# On Mac - Windows tests will be skipped
uv run pytest tests/test_path_validator.py::TestPathValidatorWindows -v

# On Windows - Mac/Linux tests will be skipped
uv run pytest tests/test_path_validator.py::TestPathValidatorMacLinux -v
```

This ensures tests run with real platform-specific path behavior, making them more reliable.

### Known Limitations

- Single-threaded (processes one PDF at a time)
- Platform-specific builds (Windows .exe must be built on Windows, macOS app on macOS, etc.)

---

## License

This project is licensed under the **GNU Affero General Public License v3.0** (AGPL-3.0).

This license is required due to the use of [PyMuPDF](https://github.com/pymupdf/PyMuPDF), which is licensed under AGPL-3.0.

### What this means:

- ✅ You can use, modify, and distribute this software freely
- ✅ Source code is publicly available
- ⚠️ If you modify and distribute it, you must share your modifications under the same license
- ⚠️ If you use it in a network service, you must make the source available to users

See the [LICENSE](LICENSE) file for full details.

### Third-Party Licenses

This project uses the following open-source libraries:

- **PyMuPDF** (AGPL-3.0) - PDF processing
- **Pillow** (HPND) - Image processing
- **pyvips** (MIT) - Fast image processing
- **PyInstaller** (GPL with exception) - Executable bundling
