"""Adapter suite — sys.path for the adapter package (no fork import)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
