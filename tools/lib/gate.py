"""The trust gate. Layers 1-5 run over the BUILT public dist/ bundle; layer 6
(scan_public_docs) runs over repo docs destined for the public repo.

Returns a list of (layer, location, detail) violations; empty means clean.
Layers: 1 structural (bare Company) · 2+3 provenance+schema (validate_card) ·
4 PII (email + company/comp/deny regexes + deny tokens) · 5 filename (*.private.*) ·
6 public-doc (PII/company markers in docs hand-copied to the public repo).
"""
import re
from pathlib import Path

from .emit import parse_content
from .validate import validate_card


def _compile(patterns):
    return [re.compile(p, re.IGNORECASE) for p in patterns]


def run_gate(dist_dir, cfg):
    violations = []
    dist = Path(dist_dir)
    content_dir = dist / "content"
    content_files = sorted(content_dir.glob("*.js")) if content_dir.exists() else []

    items = []  # (filename, card)
    for cf in content_files:
        env = parse_content(cf.read_text(encoding="utf-8"))
        for it in env.get("items", []):
            items.append((cf.name, it))

    # Layer 1 — structural: bare Company deck must never reach a public bundle.
    for fname, it in items:
        if it.get("deck") == "Company":
            violations.append(("structural", fname, f"Company item leaked: {it.get('id')}"))

    # Layers 2+3 — provenance + schema, on the built items.
    for fname, it in items:
        errs, _warns = validate_card(
            it, enforce_provenance=True, host_allowlist=cfg["hosts"], strict=True
        )
        for e in errs:
            violations.append(("schema/provenance", fname, e))

    # Layer 4 — PII / denylist.
    email_re = re.compile(cfg["email_regex"], re.IGNORECASE)
    regexes = _compile(cfg["company_regexes"] + cfg["comp_regexes"] + cfg["deny_regexes"])
    deny_tokens = [t.lower() for t in cfg["deny_tokens"]]
    for fname, it in items:
        blob = " ".join([
            str(it.get("q", "")), str(it.get("a", "")),
            str(it.get("deck", "")), " ".join(it.get("tags", []) or []),
        ])
        low = blob.lower()
        if email_re.search(blob):
            violations.append(("pii", fname, f"email-like token in {it.get('id')}"))
        for rx in regexes:
            if rx.search(blob):
                violations.append(("pii", fname, f"denylist match {rx.pattern!r} in {it.get('id')}"))
        for tok in deny_tokens:
            if tok and tok in low:
                violations.append(("pii", fname, f"deny token {tok!r} in {it.get('id')}"))

    # Layer 5 — filename: no private file may sit in dist/.
    for p in dist.rglob("*"):
        if p.is_file() and ".private." in p.name:
            violations.append(("filename", str(p.relative_to(dist)), "private file present in dist/"))

    return violations


def scan_public_docs(repo_root, cfg):
    """Layer 6 — scan docs destined for the public repo for PII/company markers.

    Docs in cfg['public_docs'] are hand-copied to the public repo at publish time
    and never pass through dist/, so run_gate (which only sees the built bundle) is
    structurally blind to them. This closes that gap: every listed doc must be
    marker-clean. Fail-closed. Deny-token / deny-regex hits are reported REDACTED —
    those patterns come from the gitignored local.json and must not land in CI logs.
    """
    violations = []
    repo = Path(repo_root)
    email_re = re.compile(cfg["email_regex"], re.IGNORECASE)
    public_rx = _compile(cfg["company_regexes"] + cfg["comp_regexes"])
    deny_rx = _compile(cfg.get("deny_regexes", []))
    deny_tokens = [t.lower() for t in cfg.get("deny_tokens", [])]
    for rel in cfg.get("public_docs", []):
        p = repo / rel
        if not p.exists():
            continue  # listed-but-absent is fine; not every public doc exists yet
        text = p.read_text(encoding="utf-8")
        low = text.lower()
        if email_re.search(text):
            violations.append(("public-doc", rel, "email-like token"))
        for rx in public_rx:
            if rx.search(text):
                violations.append(("public-doc", rel, f"company/comp match {rx.pattern!r}"))
        for rx in deny_rx:
            if rx.search(text):
                violations.append(("public-doc", rel, "deny-regex match (redacted)"))
        for tok in deny_tokens:
            if tok and tok in low:
                violations.append(("public-doc", rel, "deny-token match (redacted)"))
    return violations
