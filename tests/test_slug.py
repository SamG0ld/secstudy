import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from lib.slug import slugify, norm_front, derive_tags


class TestSlug(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(slugify("AWS::IAM"), "aws-iam")
        self.assertEqual(slugify("What is the precedence order?"),
                         "what-is-the-precedence-order")

    def test_emdash_and_accents_dropped(self):
        self.assertEqual(slugify("Security group — NACL"), "security-group-nacl")

    def test_truncate_at_boundary(self):
        s = slugify("a" * 30 + " " + "b" * 30, maxlen=50)
        self.assertLessEqual(len(s), 50)
        self.assertFalse(s.startswith("-"))
        self.assertFalse(s.endswith("-"))

    def test_norm_front(self):
        self.assertEqual(norm_front("Security group vs NACL?"), "security group vs nacl")
        self.assertEqual(norm_front("  Foo   Bar!! "), "foo bar")

    def test_derive_tags_sorted_unique(self):
        self.assertEqual(derive_tags("AWS::IAM"), ["aws", "iam"])
        self.assertEqual(derive_tags("Company"), ["company"])
        self.assertEqual(derive_tags("Security::FDA"), ["fda", "security"])


if __name__ == "__main__":
    unittest.main()
