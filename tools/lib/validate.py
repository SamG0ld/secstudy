"""Lightweight stdlib validation mirroring schema/ (NOT a JSON-Schema interpreter).

The .json schemas remain the documented contract; this module enforces the same
rules with stdlib re/datetime so the build keeps zero dependencies. validate_card
returns (errors, warnings); the caller decides fail-vs-warn by build mode.
"""
import datetime
import re
from urllib.parse import urlparse

from .slug import norm_front

ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DECK_RE = re.compile(r"^[^:]+(::[^:]+)*$")
TAG_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

CARD_KEYS = {"id", "deck", "tags", "level", "q", "a", "source", "verified", "unverified", "refs"}
CARD_BASE_REQUIRED = ("id", "deck", "q", "a")
LEVELS = ("foundational", "intermediate", "advanced", "expert")
SUBJECT_KEYS = {"slug", "title", "blurb", "order"}


def validate_subject(obj):
    errs = []
    if not isinstance(obj, dict):
        return ["subject.json is not an object"]
    for k in ("slug", "title"):
        if not obj.get(k):
            errs.append(f"subject missing required '{k}'")
    if obj.get("slug") and not ID_RE.match(str(obj["slug"])):
        errs.append(f"subject slug not a slug: {obj['slug']!r}")
    extra = set(obj) - SUBJECT_KEYS
    if extra:
        errs.append(f"subject has unknown keys: {sorted(extra)}")
    return errs


def validate_card(card, *, enforce_provenance, host_allowlist, strict=False):
    errs, warns = [], []
    if not isinstance(card, dict):
        return (["card is not an object"], [])
    cid = card.get("id", "<no-id>")

    for k in CARD_BASE_REQUIRED:
        if not card.get(k):
            errs.append(f"[{cid}] missing required '{k}'")
    extra = set(card) - CARD_KEYS
    if extra:
        errs.append(f"[{cid}] unknown keys: {sorted(extra)}")

    if card.get("id") and not ID_RE.match(str(card["id"])):
        errs.append(f"[{cid}] id not a slug")
    if card.get("id") and len(str(card["id"])) > 80:
        errs.append(f"[{cid}] id too long (>80)")
    if card.get("deck"):
        deck = str(card["deck"])
        if not DECK_RE.match(deck):
            errs.append(f"[{cid}] deck invalid: {deck!r}")
        elif any(seg in ("__proto__", "constructor", "prototype") for seg in deck.split("::")):
            errs.append(f"[{cid}] deck uses a reserved name (prototype-pollution guard): {deck!r}")

    tags = card.get("tags")
    if tags is not None:
        if not isinstance(tags, list):
            errs.append(f"[{cid}] tags not a list")
        else:
            for t in tags:
                if not isinstance(t, str) or not TAG_RE.match(t):
                    errs.append(f"[{cid}] bad tag: {t!r}")
            if len(set(tags)) != len(tags):
                errs.append(f"[{cid}] duplicate tags")

    level = card.get("level")
    if level is not None and level not in LEVELS:
        errs.append(f"[{cid}] level not one of {LEVELS}: {level!r}")

    refs = card.get("refs")
    if refs is not None:
        if not isinstance(refs, list):
            errs.append(f"[{cid}] refs not a list")
        else:
            for r in refs:
                if not isinstance(r, dict) or not r.get("label") or not r.get("url"):
                    errs.append(f"[{cid}] bad ref entry")
                elif not str(r["url"]).startswith("https://"):
                    errs.append(f"[{cid}] ref url not https")

    unv = card.get("unverified")
    if unv is not None and not isinstance(unv, bool):
        errs.append(f"[{cid}] unverified not a boolean")
    if unv and not card.get("verified"):
        errs.append(f"[{cid}] unverified card must still carry a verified (date-added) value")

    if enforce_provenance:
        src = card.get("source")
        if not src:
            errs.append(f"[{cid}] missing source")
        elif not str(src).startswith("https://"):
            errs.append(f"[{cid}] source not https")
        else:
            host = (urlparse(src).hostname or "").lower()
            if host not in host_allowlist:
                msg = f"[{cid}] source host not allowlisted: {host}"
                (errs if strict else warns).append(msg)
        ver = card.get("verified")
        if not ver:
            errs.append(f"[{cid}] missing verified")
        elif not DATE_RE.match(str(ver)):
            errs.append(f"[{cid}] verified not ISO date: {ver!r}")
        else:
            try:
                datetime.date.fromisoformat(ver)
            except ValueError:
                errs.append(f"[{cid}] verified not a real date: {ver!r}")

    return (errs, warns)


def check_ids_unique(cards):
    seen, errs = set(), []
    for c in cards:
        cid = c.get("id")
        if cid in seen:
            errs.append(f"duplicate id: {cid}")
        seen.add(cid)
    return errs


def check_fronts_unique(cards):
    seen, errs = {}, []
    for c in cards:
        nf = norm_front(c.get("q", ""))
        if nf in seen:
            errs.append(f"duplicate normalized front: {c.get('id')} == {seen[nf]}")
        else:
            seen[nf] = c.get("id")
    return errs
