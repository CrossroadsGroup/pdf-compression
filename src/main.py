"""Entry point for PDF Compressor application."""

import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent
if str(src_dir.parent) not in sys.path:
    sys.path.insert(0, str(src_dir.parent))

if __name__ == "__main__":
    from src.gui.app import main

    main()
