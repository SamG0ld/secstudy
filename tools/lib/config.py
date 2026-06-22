"""Trust-gate config: committed gate.json + gitignored local.json, fail-closed.

- config/gate.json (committed, public-safe): host allowlist + email/company/comp
  regexes. Always present; fork PRs are still checked by these.
- config/local.json (gitignored): sensitive deny tokens/regexes (names, codenames).
  CI materializes it from a repo secret, or points SECSTUDY_LOCAL_JSON at it.

Under `--check`, a missing local.json (and no env override) is FAIL-CLOSED:
load_gate_config returns None so the caller exits 3 rather than silently
skipping the sensitive layer.
"""
import json
import os
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parent.parent.parent / "config"

DEFAULT_EMAIL_RE = r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"


def load_gate_config(require_local=False):
    gate_path = CONFIG_DIR / "gate.json"
    if not gate_path.exists():
        raise FileNotFoundError(f"missing committed config: {gate_path}")
    gate = json.loads(gate_path.read_text(encoding="utf-8"))

    env_path = os.environ.get("SECSTUDY_LOCAL_JSON")
    local_path = Path(env_path) if env_path else (CONFIG_DIR / "local.json")
    local = None
    if local_path.exists():
        local = json.loads(local_path.read_text(encoding="utf-8"))

    if require_local and local is None:
        return None  # fail-closed signal

    return {
        "hosts": set(gate.get("hosts", [])),
        "email_regex": gate.get("email_regex", DEFAULT_EMAIL_RE),
        "company_regexes": list(gate.get("company_regexes", [])),
        "comp_regexes": list(gate.get("comp_regexes", [])),
        "public_docs": list(gate.get("public_docs", [])),
        "deny_tokens": list(local.get("deny_tokens", [])) if local else [],
        "deny_regexes": list(local.get("deny_regexes", [])) if local else [],
        "has_local": local is not None,
    }
