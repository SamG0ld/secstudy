import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build


def _snapshot(d):
    return {p.relative_to(d).as_posix(): p.read_bytes()
            for p in Path(d).rglob("*") if p.is_file()}


class TestDeterminism(unittest.TestCase):
    def test_build_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            build.build(a, include_private=True, enforce_provenance=False,
                        strict=False, host_allowlist=set())
            build.build(b, include_private=True, enforce_provenance=False,
                        strict=False, host_allowlist=set())
            sa, sb = _snapshot(a), _snapshot(b)
            self.assertTrue(sa, "build produced no files")
            self.assertTrue(sa == sb, "dist/ not byte-identical across two builds")


if __name__ == "__main__":
    unittest.main()
