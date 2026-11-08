"""PyInstaller ve geliştirme için giriş noktası."""

import sys
from pathlib import Path

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from altyazi.main import main

if __name__ == "__main__":
    sys.exit(main())
