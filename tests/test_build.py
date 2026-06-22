import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build
from lib import normalize, emit

FIX_CLEAN = Path(__file__).resolve().parent / "fixtures" / "clean"
HOSTS = {"docs.aws.amazon.com"}


class TestBuild(unittest.TestCase):
    def setUp(self):
        self._orig_src = build.SRC

    def tearDown(self):
        build.SRC = self._orig_src

    def test_clean_public_build(self):
        build.SRC = FIX_CLEAN
        with tempfile.TemporaryDirectory() as d:
            code, errs, _ = build.build(
                d, include_private=False, enforce_provenance=True,
                strict=True, host_allowlist=HOSTS)
            self.assertEqual(code, build.EXIT_OK, errs)
            content = Path(d) / "content" / "aws-cloud-security.cards.js"
            self.assertTrue(content.exists())
            env = emit.parse_content(content.read_text(encoding="utf-8"))
            self.assertEqual(env["subject"], "aws-cloud-security")
            self.assertEqual(env["module"], "cards")
            self.assertEqual(len(env["items"]), 3)
            self.assertIn("subjectMeta", env)
            self.assertTrue((Path(d) / "manifest.js").exists())
            self.assertTrue((Path(d) / "sw.js").exists())

    def test_strip_company(self):
        items = [{"id": "a", "deck": "AWS::IAM"}, {"id": "b", "deck": "Company"}]
        kept = normalize.strip_company(items)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["id"], "a")

    def test_private_envelope_has_no_subject_meta(self):
        env = normalize.private_envelope("aws-cloud-security", [{"id": "x", "deck": "Company"}])
        self.assertNotIn("subjectMeta", env)

    def test_public_envelope_has_subject_meta(self):
        env = normalize.public_envelope({"slug": "s", "title": "S"}, [])
        self.assertIn("subjectMeta", env)

    def test_dup_id_fails_build(self):
        with tempfile.TemporaryDirectory() as srcd, tempfile.TemporaryDirectory() as out:
            sub = Path(srcd) / "aws-cloud-security"
            sub.mkdir()
            (sub / "subject.json").write_text(
                json.dumps({"slug": "aws-cloud-security", "title": "X"}), encoding="utf-8")
            card = {"deck": "AWS::IAM", "a": "A",
                    "source": "https://docs.aws.amazon.com/x", "verified": "2026-06-17"}
            (sub / "cards.json").write_text(json.dumps([
                {"id": "dup", "q": "Q1?", **card},
                {"id": "dup", "q": "Q2?", **card},
            ]), encoding="utf-8")
            build.SRC = Path(srcd)
            code, errs, _ = build.build(
                out, include_private=False, enforce_provenance=True,
                strict=True, host_allowlist=HOSTS)
            self.assertEqual(code, build.EXIT_BUILD)
            self.assertTrue(any("duplicate id" in e for e in errs))


if __name__ == "__main__":
    unittest.main()
