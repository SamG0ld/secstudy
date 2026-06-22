#!/usr/bin/env python3
"""Apply provenance (source + verified) to cards in src/<subject>/cards.json.

T-Prov application step: agents PROPOSE allowlisted-host primary-doc sources per
subdeck, a human REVIEWS them and sets the `verified` date, then this tool writes
the approved values. It never fabricates a verified date — the date is read from
the proposals file (human-gated rule). Reserializes cards.json with the same
style as migrate_seed.py (json.dumps indent=2, ensure_ascii=False, trailing
newline), so the diff is additive-only.

Proposals JSON shape:
  {"deck": "AWS::IAM", "verified": "2026-06-17",
   "sources": {"<card-id>": "<https url>", ...},
   "unverified": ["<card-id>", ...]}   # optional: flag cards whose source could
                                       # not be independently fetch-verified

Usage:
  python tools/apply_sources.py [proposals.json]   # default: tools/_proposals.local.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CARDS = ROOT / "src" / "aws-cloud-security" / "cards.json"
DEFAULT_PROPOSALS = ROOT / "tools" / "_proposals.local.json"


def apply_proposals(proposals, cards):
    """Mutate the in-memory `cards` list per `proposals`. IO-free so it is unit
    testable; the CLI handles file read/write and exit codes around it. Returns a
    report dict describing what was applied and any problems found."""
    deck = proposals.get("deck")
    verified = proposals.get("verified")
    sources = proposals.get("sources") or {}
    unverified_ids = set(proposals.get("unverified") or [])
    by_id = {c["id"]: c for c in cards}

    applied, not_found, deck_mismatch = [], [], []
    for cid, url in sources.items():
        c = by_id.get(cid)
        if c is None:
            not_found.append(cid)
            continue
        if deck and c.get("deck") != deck:
            deck_mismatch.append((cid, c.get("deck")))
            continue
        c["source"] = url
        c["verified"] = verified
        if cid in unverified_ids:
            c["unverified"] = True
        applied.append(cid)

    still = [c["id"] for c in cards if deck and c.get("deck") == deck and not c.get("source")]
    stray_unv = [cid for cid in unverified_ids if cid not in sources]
    return {
        "deck": deck, "verified": verified, "applied": applied,
        "not_found": not_found, "deck_mismatch": deck_mismatch,
        "still": still, "stray_unv": stray_unv,
        "n_unverified": sum(1 for cid in applied if cid in unverified_ids),
    }


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    prop_path = Path(argv[0]) if argv else DEFAULT_PROPOSALS
    proposals = json.loads(prop_path.read_text(encoding="utf-8"))
    if not proposals.get("verified"):
        sys.exit("error: proposals missing 'verified' date (human-set, required)")

    cards = json.loads(CARDS.read_text(encoding="utf-8"))
    r = apply_proposals(proposals, cards)
    CARDS.write_text(json.dumps(cards, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    msg = f"applied {len(r['applied'])} card(s) verified={r['verified']}"
    if r["n_unverified"]:
        msg += f" ({r['n_unverified']} flagged unverified)"
    print(msg)
    for cid in r["stray_unv"]:
        print(f"  UNVERIFIED-ID not in this file's sources: {cid}")
    if r["deck"]:
        print(f"deck {r['deck']}: {len(r['still'])} card(s) still missing source")
        for cid in r["still"]:
            print(f"  MISSING {cid}")
    for cid in r["not_found"]:
        print(f"  NOT-FOUND in cards.json: {cid}")
    for cid, d in r["deck_mismatch"]:
        print(f"  DECK-MISMATCH {cid}: file={d!r} proposals={r['deck']!r}")
    total_unsourced = sum(1 for c in cards if not c.get("source"))
    print(f"total unsourced remaining (all decks): {total_unsourced}")

    # Non-zero exit on any problem so a commit loop stops instead of committing a
    # half-sourced deck (unknown id, deck mismatch, card left unsourced, stray flag).
    if r["not_found"] or r["deck_mismatch"] or r["still"] or r["stray_unv"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
