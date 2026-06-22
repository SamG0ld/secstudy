"""Slug / normalization helpers — the canonical id/tag/front conventions.

Copied verbatim from tools/migrate_seed.py so build-time validation uses the
exact rules the one-shot migration used to GENERATE ids/tags. build.py uses
these only to VALIDATE and detect duplicates — it never regenerates ids/tags
or rewrites src/.
"""
import re
import unicodedata


def slugify(text, maxlen=None):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    t = t.lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    if maxlen and len(t) > maxlen:
        t = t[:maxlen]
        if "-" in t.strip("-"):
            t = t.rsplit("-", 1)[0]
        t = t.strip("-")
    return t


def norm_front(text):
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    t = re.sub(r"[^a-z0-9]+", " ", t).strip()
    return re.sub(r"\s+", " ", t)


def derive_tags(subdeck):
    parts = [slugify(p) for p in subdeck.split("::")]
    return sorted({p for p in parts if p})
