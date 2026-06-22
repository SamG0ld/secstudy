#!/usr/bin/env python3
"""secstudy build — Python stdlib only.

Generates the dist/ artifact (content register files, manifest, PWA assets, app
shell) from the editable src/ tree, and runs the public/private trust gate.

  python tools/build.py            # PUBLIC build, provenance ENFORCED
  python tools/build.py --private  # full LOCAL build (incl. private), provenance relaxed
  python tools/build.py --draft    # public file set, provenance relaxed (local study)
  python tools/build.py --check    # clean PUBLIC rebuild + trust gate (exit 2 on violation)
  python tools/build.py --strict   # non-allowlisted source host -> error (not warn)

Exit codes: 0 ok · 1 validate/build error · 2 gate violation · 3 config fail-closed.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import emit, normalize, validate
from lib.config import load_gate_config
from lib.determinism import hash_files
from lib.gate import run_gate, scan_public_docs

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

EXIT_OK, EXIT_BUILD, EXIT_GATE, EXIT_CONFIG = 0, 1, 2, 3


def discover_subjects():
    if not SRC.exists():
        return []
    return sorted(p for p in SRC.iterdir() if p.is_dir() and (p / "subject.json").exists())


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def build(out_dir, *, include_private, enforce_provenance, strict, host_allowlist):
    """Build into out_dir. Returns (exit_code, errors, warnings)."""
    errors, warnings = [], []
    dist = Path(out_dir)
    if dist.exists():
        shutil.rmtree(dist)
    (dist / "content").mkdir(parents=True)

    content_relpaths = []
    unverified_count = 0
    for subject_dir in discover_subjects():
        subject = _load(subject_dir / "subject.json")
        errors += validate.validate_subject(subject)

        public = normalize.strip_company(_load(subject_dir / "cards.json"))
        unverified_count += sum(1 for c in public if c.get("unverified"))
        for c in public:
            errs, warns = validate.validate_card(
                c, enforce_provenance=enforce_provenance,
                host_allowlist=host_allowlist, strict=strict)
            errors += errs
            warnings += warns
        errors += validate.check_ids_unique(public)
        errors += validate.check_fronts_unique(public)

        stem = f"{subject['slug']}.cards"
        (dist / "content" / f"{stem}.js").write_text(
            emit.render_content(normalize.public_envelope(subject, public)), encoding="utf-8")
        content_relpaths.append(f"content/{stem}.js")

        priv_path = subject_dir / "cards.private.json"
        if include_private and priv_path.exists():
            private = _load(priv_path)
            for c in private:  # private must still be structurally valid (no provenance gate)
                errs, _ = validate.validate_card(
                    c, enforce_provenance=False, host_allowlist=host_allowlist, strict=False)
                errors += errs
            errors += validate.check_ids_unique(private)
            pstem = f"{subject['slug']}.cards.private"
            (dist / "content" / f"{pstem}.js").write_text(
                emit.render_content(normalize.private_envelope(subject["slug"], private)),
                encoding="utf-8")
            content_relpaths.append(f"content/{pstem}.js")

    if errors:
        return EXIT_BUILD, errors, warnings

    if unverified_count:
        warnings.append(
            f"{unverified_count} public card(s) carry an unverified source "
            "(intentional; rendered with an 'unverified' badge)")

    (dist / "manifest.js").write_text(emit.render_manifest(content_relpaths), encoding="utf-8")
    missing = emit.copy_shell(ROOT, dist)
    if missing:
        warnings.append(f"app shell not present yet (ok before D6): {missing}")
    (dist / "manifest.webmanifest").write_text(emit.render_webmanifest(), encoding="utf-8")

    # SW cache version = hash over everything written so far (sw.js excluded).
    pairs, precache = [], []
    for p in sorted(dist.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(dist).as_posix()
        pairs.append((rel, p.read_bytes()))
        if ".private." not in p.name:   # defense-in-depth: never let the SW serve a private file
            precache.append(rel)
    cache_version = "secstudy-" + hash_files(pairs)
    (dist / "sw.js").write_text(emit.render_sw(cache_version, precache), encoding="utf-8")

    return EXIT_OK, errors, warnings


def _report(errors, warnings):
    for w in warnings:
        print(f"warn: {w}", file=sys.stderr)
    for e in errors:
        print(f"error: {e}", file=sys.stderr)


def main(argv=None):
    ap = argparse.ArgumentParser(description="secstudy stdlib build + trust gate")
    ap.add_argument("--private", action="store_true", help="full local build incl. private content")
    ap.add_argument("--draft", action="store_true", help="public set, provenance relaxed")
    ap.add_argument("--check", action="store_true", help="clean public rebuild + trust gate")
    ap.add_argument("--strict", action="store_true", help="non-allowlisted source host is an error")
    ap.add_argument("--out", default=str(ROOT / "dist"))
    args = ap.parse_args(argv)

    if args.private and args.draft:
        print("error: --private and --draft are mutually exclusive", file=sys.stderr)
        return EXIT_BUILD

    cfg = load_gate_config(require_local=args.check)
    if cfg is None:
        print("error: config/local.json missing — fail-closed under --check. "
              "Create it or set SECSTUDY_LOCAL_JSON.", file=sys.stderr)
        return EXIT_CONFIG

    if args.check:
        # Build emits a clean public bundle (structural validation still hard-fails);
        # provenance/PII/structural-Company are enforced by the gate over the built
        # bundle, so violations surface as exit 2 (gate), not exit 1 (build).
        code, errors, warnings = build(
            args.out, include_private=False, enforce_provenance=False,
            strict=False, host_allowlist=cfg["hosts"])
        _report(errors, warnings)
        if code != EXIT_OK:
            return code
        violations = run_gate(args.out, cfg) + scan_public_docs(ROOT, cfg)
        if violations:
            for layer, loc, detail in violations:
                print(f"GATE[{layer}] {loc}: {detail}", file=sys.stderr)
            print(f"gate: {len(violations)} violation(s)", file=sys.stderr)
            return EXIT_GATE
        print("gate: clean OK")
        return EXIT_OK

    enforce = not (args.private or args.draft)
    code, errors, warnings = build(
        args.out, include_private=args.private, enforce_provenance=enforce,
        strict=args.strict, host_allowlist=cfg["hosts"])
    _report(errors, warnings)
    if code != EXIT_OK:
        return code
    print(f"built {args.out} OK")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
