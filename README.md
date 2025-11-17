# PDF Compressor Desktop Tool

A Windows desktop application to compress PDF files before uploading to SharePoint or FeedbackFusion.

![PDF Compressor Tool](assets/tool_image.png)

## For Team Members (Using the Tool)

### Quick Start

The pre-built executable is included in this repository at `dist/PDF_Compressor.exe` (Windows).

Simply:
1. Clone this repository (or download the latest version)
2. Navigate to the `dist/` folder
3. Run `PDF_Compressor.exe`

No installation or Python required!

### What This Tool Does

- Compresses all PDFs larger than 5MB in a selected folder
- Processes all subdirectories automatically
- Reduces file sizes by 85-95% on average
- Replaces original files only if compression helps
- No internet connection required - runs completely offline

### When to Use

**Use this tool BEFORE uploading PDFs to:**

- External Client SharePoint Site
- FeedbackFusion
- Any other file sharing platform

This saves upload time, storage space, and makes downloads faster for recipients.

### How to Use

1. **Run** `dist/PDF_Compressor.exe` from the repository folder (or copy it anywhere on your computer)
2. **Double-click** to open the application
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

### Troubleshooting

**"No PDF files >5MB found"**

- Make sure your folder contains PDFs larger than 5MB
- Check that you selected the correct folder

**Application won't start**

- Make sure you're running on Windows 10 or later
- Try running as Administrator (right-click → Run as administrator)

**Compression seems slow**

- This is normal for large files or many files
- You can leave it running in the background
- Average: 2-5 seconds per 25MB file

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

3. The executable will be created in `dist/PDF_Compressor.exe` (Windows) or `dist/PDF_Compressor` (macOS/Linux)

### Manual Build Steps

If you prefer to build manually:

```bash
uv sync

uv run pyinstaller --onefile --windowed --name="PDF_Compressor" \
    --add-data="pdf_compress.py:." \
    --collect-binaries=pyvips \
    --hidden-import=pyvips \
    --hidden-import=PIL \
    --hidden-import=fitz \
    app.py
```

Note: On Windows, use `;` instead of `:` in `--add-data` parameter.

### Distribution

After building:

1. The .exe is in `dist/PDF_Compressor.exe`
2. This file is completely standalone - no dependencies needed
3. Distribute this single .exe file to team members
4. Team members do NOT need Python installed

### File Structure

```
pdf-compression/
├── app.py              # Main GUI application
├── pdf_compress.py     # PDF compression logic
├── main.py            # Simple CLI entry point
├── pyproject.toml     # Python project configuration and dependencies
├── uv.lock            # Locked dependencies for reproducible builds
├── build.bat          # Windows build script
├── build.sh           # macOS/Linux build script
├── .gitignore         # Git ignore rules
└── README.md          # This file
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
uv run python app.py
```

To rebuild after making changes:

1. Update the code (app.py, pdf_compress.py, etc.)
2. Rebuild the executable:
   ```bash
   build.bat          # Windows
   ./build.sh         # macOS/Linux
   ```
3. Distribute the new executable to team members

### Known Limitations

- Single-threaded (processes one PDF at a time)
- Platform-specific builds (Windows .exe must be built on Windows, macOS app on macOS, etc.)
