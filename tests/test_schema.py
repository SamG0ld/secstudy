import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from lib.validate import (
    validate_card, validate_subject, check_ids_unique, check_fronts_unique,
)

HOSTS = {"docs.aws.amazon.com"}


def good():
    return {
        "id": "iam-x", "deck": "AWS::IAM", "tags": ["aws", "iam"],
        "q": "Q?", "a": "A.",
        "source": "https://docs.aws.amazon.com/x", "verified": "2026-06-17",
    }


class TestSchema(unittest.TestCase):
    def test_good(self):
        errs, _ = validate_card(good(), enforce_provenance=True, host_allowlist=HOSTS, strict=True)
        self.assertEqual(errs, [])

    def test_missing_source_enforced(self):
        c = good(); del c["source"]
        errs, _ = validate_card(c, enforce_provenance=True, host_allowlist=HOSTS, strict=True)
        self.assertTrue(any("missing source" in e for e in errs))

    def test_provenance_relaxed_in_draft(self):
        c = good(); del c["source"]; del c["verified"]
        errs, _ = validate_card(c, enforce_provenance=False, host_allowlist=HOSTS)
        self.assertEqual(errs, [])

    def test_non_https(self):
        c = good(); c["source"] = "http://docs.aws.amazon.com/x"
        errs, _ = validate_card(c, enforce_provenance=True, host_allowlist=HOSTS, strict=True)
        self.assertTrue(any("not https" in e for e in errs))

    def test_bad_date(self):
        c = good(); c["verified"] = "2026-13-40"
        errs, _ = validate_card(c, enforce_provenance=True, host_allowlist=HOSTS, strict=True)
        self.assertTrue(any("verified" in e for e in errs))

    def test_unknown_key(self):
        c = good(); c["xyz"] = 1
        errs, _ = validate_card(c, enforce_provenance=True, host_allowlist=HOSTS, strict=True)
        self.assertTrue(any("unknown keys" in e for e in errs))

    def test_unverified_flag_accepted(self):
        c = good(); c["unverified"] = True
        errs, _ = validate_card(c, enforce_provenance=True, host_allowlist=HOSTS, strict=True)
        self.assertEqual(errs, [])

    def test_unverified_must_be_bool(self):
        c = good(); c["unverified"] = "yes"
        errs, _ = validate_card(c, enforce_provenance=True, host_allowlist=HOSTS, strict=True)
        self.assertTrue(any("unverified not a boolean" in e for e in errs))

    def test_unverified_requires_verified_even_in_draft(self):
        c = good(); c["unverified"] = True; del c["verified"]
        errs, _ = validate_card(c, enforce_provenance=False, host_allowlist=HOSTS)
        self.assertTrue(any("must still carry a verified" in e for e in errs))

    def test_level_accepted(self):
        for lvl in ("foundational", "intermediate", "advanced", "expert"):
            c = good(); c["level"] = lvl
            errs, _ = validate_card(c, enforce_provenance=True, host_allowlist=HOSTS, strict=True)
            self.assertEqual(errs, [], lvl)

    def test_level_optional(self):
        c = good()  # no level key
        errs, _ = validate_card(c, enforce_provenance=True, host_allowlist=HOSTS, strict=True)
        self.assertEqual(errs, [])

    def test_level_must_be_in_enum(self):
        c = good(); c["level"] = "expret"
        errs, _ = validate_card(c, enforce_provenance=True, host_allowlist=HOSTS, strict=True)
        self.assertTrue(any("level not one of" in e for e in errs))

    def test_level_wrong_type_rejected(self):
        c = good(); c["level"] = 3  # non-string is not in the enum tuple -> rejected
        errs, _ = validate_card(c, enforce_provenance=True, host_allowlist=HOSTS, strict=True)
        self.assertTrue(any("level not one of" in e for e in errs))

    def test_level_not_provenance_gated(self):
        # level is editorial — its absence is never a provenance failure, even under --check
        c = good()
        errs, _ = validate_card(c, enforce_provenance=True, host_allowlist=HOSTS, strict=True)
        self.assertFalse(any("level" in e for e in errs))

    def test_reserved_deck_name_rejected(self):
        for bad in ("__proto__", "AWS::__proto__", "constructor", "prototype"):
            c = good(); c["deck"] = bad
            errs, _ = validate_card(c, enforce_provenance=True, host_allowlist=HOSTS, strict=True)
            self.assertTrue(any("reserved name" in e for e in errs), bad)

    def test_host_not_allowlisted_is_error_when_strict(self):
        c = good(); c["source"] = "https://evil.example.com/x"
        errs, _ = validate_card(c, enforce_provenance=True, host_allowlist=HOSTS, strict=True)
        self.assertTrue(any("not allowlisted" in e for e in errs))

    def test_host_not_allowlisted_is_warning_when_lenient(self):
        c = good(); c["source"] = "https://evil.example.com/x"
        errs, warns = validate_card(c, enforce_provenance=True, host_allowlist=HOSTS, strict=False)
        self.assertEqual(errs, [])
        self.assertTrue(any("not allowlisted" in w for w in warns))

    def test_dup_id(self):
        self.assertTrue(check_ids_unique([{"id": "a"}, {"id": "a"}]))

    def test_dup_normalized_front(self):
        self.assertTrue(check_fronts_unique([{"id": "a", "q": "Same Q?"},
                                             {"id": "b", "q": "same q"}]))

    def test_subject(self):
        self.assertEqual(validate_subject({"slug": "aws-cloud-security", "title": "X"}), [])
        self.assertTrue(validate_subject({"slug": "X Y", "title": "X"}))


if __name__ == "__main__":
    unittest.main()
