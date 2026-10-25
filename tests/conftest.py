import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

# Browser regression must never overwrite immutable historical screenshots.
import os
os.environ.setdefault("LAB_SCREENSHOT_DIR", str(Path(__file__).resolve().parents[1] / ".cache/screenshots"))
