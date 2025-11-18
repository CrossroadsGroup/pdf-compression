import sys
from pathlib import Path

pytest_plugins = []

src_dir = Path(__file__).parent.parent / "src"
if str(src_dir.parent) not in sys.path:
    sys.path.insert(0, str(src_dir.parent))
