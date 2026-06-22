import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from apply_sources import apply_proposals


def cards():
    return [
        {"id": "a", "deck": "AWS::IAM", "q": "Qa?", "a": "Aa."},
        {"id": "b", "deck": "AWS::IAM", "q": "Qb?", "a": "Ab."},
    ]


class TestApplyProposals(unittest.TestCase):
    def test_applies_source_and_verified(self):
        cs = cards()
        r = apply_proposals(
            {"deck": "AWS::IAM", "verified": "2026-06-17",
             "sources": {"a": "https://docs.aws.amazon.com/x"}}, cs)
        self.assertEqual(r["applied"], ["a"])
        self.assertEqual(cs[0]["source"], "https://docs.aws.amazon.com/x")
        self.assertEqual(cs[0]["verified"], "2026-06-17")
        self.assertNotIn("unverified", cs[0])

    def test_flags_unverified(self):
        cs = cards()
        r = apply_proposals(
            {"deck": "AWS::IAM", "verified": "2026-06-17",
             "sources": {"a": "https://x"}, "unverified": ["a"]}, cs)
        self.assertEqual(r["n_unverified"], 1)
        self.assertTrue(cs[0]["unverified"])

    def test_incomplete_deck_reports_still(self):
        # 'b' left unsourced -> the CLI must exit nonzero so a commit loop stops.
        cs = cards()
        r = apply_proposals(
            {"deck": "AWS::IAM", "verified": "2026-06-17",
             "sources": {"a": "https://x"}}, cs)
        self.assertEqual(r["still"], ["b"])

    def test_not_found_id(self):
        cs = cards()
        r = apply_proposals(
            {"deck": "AWS::IAM", "verified": "2026-06-17",
             "sources": {"zzz": "https://x"}}, cs)
        self.assertEqual(r["not_found"], ["zzz"])

    def test_deck_mismatch(self):
        cs = cards()
        r = apply_proposals(
            {"deck": "AWS::S3", "verified": "2026-06-17",
             "sources": {"a": "https://x"}}, cs)
        self.assertEqual([m[0] for m in r["deck_mismatch"]], ["a"])

    def test_stray_unverified_id(self):
        cs = cards()
        r = apply_proposals(
            {"deck": "AWS::IAM", "verified": "2026-06-17",
             "sources": {"a": "https://x"}, "unverified": ["zzz"]}, cs)
        self.assertEqual(r["stray_unv"], ["zzz"])


if __name__ == "__main__":
    unittest.main()
