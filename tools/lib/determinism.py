"""Determinism helpers — every emitted byte must be reproducible across runs.

Output is independent of dict/set iteration order (sort_keys + explicit sorts),
so PYTHONHASHSEED does not affect it; tests still pin PYTHONHASHSEED=0 to catch
accidental ordering reliance.
"""
import hashlib
import json


def canonical_json(obj):
    """Stable JSON: sorted keys, 2-space indent, no ASCII escaping (preserve em-dashes)."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2)


def hash_files(pairs):
    """Content hash over (relative_posix_path, bytes) pairs, order-independent."""
    h = hashlib.sha256()
    for rel, data in sorted(pairs, key=lambda p: p[0]):
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(data)
    return h.hexdigest()[:12]
