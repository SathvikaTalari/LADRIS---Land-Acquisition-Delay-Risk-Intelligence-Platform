"""
LandPulse AI — ML Tests Package
Ensure sys.path includes parent directories for `import ml...`
"""

import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent
ML_DIR = TESTS_DIR.parent
ROOT_DIR = ML_DIR.parent

for p in (str(ROOT_DIR), str(ML_DIR.parent), "/ml", "/"):
    if p not in sys.path and Path(p).exists():
        sys.path.insert(0, p)
