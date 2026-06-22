"""Normalize src/ card lists into STUDY.register(...) envelope dicts.

Pure functions (no IO) so F9 can test envelope shape directly. Item order is
preserved from the source file (pedagogical order is intentional).
"""


def public_envelope(subject_meta, items):
    return {
        "subject": subject_meta["slug"],
        "subjectMeta": subject_meta,
        "module": "cards",
        "items": items,
    }


def private_envelope(slug, items):
    # No subjectMeta — the public file is the single source of subject metadata.
    return {"subject": slug, "module": "cards", "items": items}


def strip_company(items):
    """Defense-in-depth: a public bundle never contains a bare-Company item."""
    return [c for c in items if c.get("deck") != "Company"]
