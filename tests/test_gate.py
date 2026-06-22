import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from lib import emit
from lib import config as config_mod
from lib.gate import run_gate, scan_public_docs

CFG = {
    "hosts": {"docs.aws.amazon.com"},
    "email_regex": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "company_regexes": [],
    "comp_regexes": [],
    "deny_tokens": [],
    "deny_regexes": [],
    "has_local": True,
}


def write_dist(items, *, with_private_file=False):
    dist = Path(tempfile.mkdtemp())
    (dist / "content").mkdir()
    env = {"subject": "s", "subjectMeta": {"slug": "s", "title": "S"},
           "module": "cards", "items": items}
    (dist / "content" / "s.cards.js").write_text(emit.render_content(env), encoding="utf-8")
    if with_private_file:
        (dist / "content" / "s.cards.private.js").write_text(
            emit.render_content(env), encoding="utf-8")
    return dist


def sourced(**over):
    c = {"id": "x", "deck": "AWS::IAM", "q": "Q?", "a": "A.",
         "source": "https://docs.aws.amazon.com/x", "verified": "2026-06-17"}
    c.update(over)
    return c


def _write_repo(docs):
    """docs: {relpath: text}. Returns a temp repo root with those files written."""
    repo = Path(tempfile.mkdtemp())
    for rel, text in docs.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return repo


def _docs_cfg(**over):
    c = dict(CFG)
    c["public_docs"] = ["DOC.md"]
    c.update(over)
    return c


class TestGate(unittest.TestCase):
    def _layers(self, violations):
        return {layer for layer, _, _ in violations}

    def test_clean_passes(self):
        self.assertEqual(run_gate(write_dist([sourced()]), CFG), [])

    def test_layer1_company_structural(self):
        v = run_gate(write_dist([sourced(id="c", deck="Company")]), CFG)
        self.assertIn("structural", self._layers(v))

    def test_layer2_missing_source(self):
        c = sourced(); del c["source"]
        v = run_gate(write_dist([c]), CFG)
        self.assertTrue(any("missing source" in d for _, _, d in v))

    def test_layer2_non_https(self):
        v = run_gate(write_dist([sourced(source="http://docs.aws.amazon.com/x")]), CFG)
        self.assertTrue(any("not https" in d for _, _, d in v))

    def test_layer2_non_allowlisted_host(self):
        v = run_gate(write_dist([sourced(source="https://evil.example.com/x")]), CFG)
        self.assertTrue(any("not allowlisted" in d for _, _, d in v))

    def test_layer5_private_filename(self):
        v = run_gate(write_dist([sourced()], with_private_file=True), CFG)
        self.assertIn("filename", self._layers(v))

    def test_layer6_public_doc_clean_passes(self):
        repo = _write_repo({"DOC.md": "# Design\nGeneric public AWS content only.\n"})
        self.assertEqual(scan_public_docs(repo, _docs_cfg()), [])

    def test_layer6_deny_token_is_redacted(self):
        repo = _write_repo({"DOC.md": "the codename is Bluebird\n"})
        v = scan_public_docs(repo, _docs_cfg(deny_tokens=["Bluebird"]))
        self.assertTrue(v)
        self.assertTrue(all("Bluebird" not in d for _, _, d in v))  # secret never printed

    def test_layer6_absent_listed_doc_is_ok(self):
        repo = _write_repo({})  # DOC.md listed in cfg but not present
        self.assertEqual(scan_public_docs(repo, _docs_cfg()), [])

    def test_fail_closed_without_local(self):
        d = Path(tempfile.mkdtemp())
        (d / "gate.json").write_text('{"hosts":[]}', encoding="utf-8")
        orig = config_mod.CONFIG_DIR
        config_mod.CONFIG_DIR = d
        os.environ.pop("SECSTUDY_LOCAL_JSON", None)
        try:
            self.assertIsNone(config_mod.load_gate_config(require_local=True))
            self.assertIsNotNone(config_mod.load_gate_config(require_local=False))
        finally:
            config_mod.CONFIG_DIR = orig


if __name__ == "__main__":
    unittest.main()
