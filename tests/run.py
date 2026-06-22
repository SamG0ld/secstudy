#!/usr/bin/env python3
"""Run the secstudy test suite (stdlib unittest only).

  python tests/run.py

Pins PYTHONHASHSEED=0 for child processes; the build's output is sorted and thus
hash-seed-independent, so this only guards against accidental ordering reliance.
"""
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
os.environ.setdefault("PYTHONHASHSEED", "0")


def main():
    suite = unittest.TestLoader().discover(str(Path(__file__).parent), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
