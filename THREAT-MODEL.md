# secstudy — Threat Model

This is a security project; the artifact is built to model the practice it teaches. This document
states what we protect, the trust boundaries, the threats considered, and the residual/accepted risks.

## Assets
1. **Content integrity & provenance** — study answers must be correct, cited, and dated; a reader
   should be able to trust and verify every card.
2. **The public/private boundary** — no PII or employer/private content may ever reach the public
   artifact or its git history.
3. **The user's local study state** — `known` flags and prefs in `localStorage` (low sensitivity).

## Trust boundaries
- **Build time vs run time.** `tools/build.py` (Python stdlib) is trusted tooling run by a human/CI.
  The runtime app is fully untrusted-input-tolerant: it treats all card content as data, never code.
- **Manifest integrity == build integrity.** The app loads data only via `<script src>` files listed
  in the build-generated `dist/manifest.js`. The loader injects exactly those paths; no card/user data
  ever reaches a script `src`. If an attacker can rewrite the built `manifest.js`, they already own the
  build output — CSP `script-src 'self'` still constrains them to same-origin scripts.
- **Content sources are untrusted at render.** Even though sources are human-approved at build time,
  the renderer assumes card fields (`q/a/deck/tags/source/refs`) could be hostile and handles them safely.

## Threats & mitigations

| Threat | Mitigation |
|---|---|
| **Supply-chain compromise** (malicious dependency) | **Zero runtime dependencies**; no CDN scripts, no web-font fetches. The build is Python-stdlib-only. Nothing to compromise transitively. |
| **XSS / DOM injection** via card content | All content rendered with `textContent` / `createElement` / `replaceChildren` — **never** `innerHTML`/`insertAdjacentHTML`/`document.write`/`eval`. CSP `script-src 'self'` (no `'unsafe-inline'`, no inline handlers). The only data-driven attribute is a provenance link `href`, validated `^https://` and given `rel="noopener noreferrer" target="_blank"`. |
| **PII / private-content leak** to the public repo | Two-repo split (private master → sanitized public); a layered trust gate (`build.py --check`) over the **built** bundle: structural (bare `Company` deck), provenance (source/verified/host), schema, PII (email + denylist), filename (`*.private.*`). Denylist is **fail-closed** (committed public-safe regexes in `config/gate.json` + gitignored sensitive tokens in `config/local.json`). CI runs the gate on every PR. |
| **Prototype pollution** via card-controlled `deck`/`tag` keys | Registry and all maps keyed by card data use `Object.create(null)`; `buildGrouped()` is wrapped so a poison card can't blank the app; the build gate rejects deck segments named `__proto__`/`constructor`/`prototype`. |
| **Network exfiltration / telemetry** | No `fetch`/`XHR`/`WebSocket`/`sendBeacon`/external requests anywhere at runtime; no analytics. CSP `connect-src 'self'` (permits only same-origin, needed for the SW precache) and `default-src 'self'`. |
| **Clickjacking** | A `<meta>` CSP **cannot** set `frame-ancestors`, and GitHub Pages cannot send `X-Frame-Options`. Mitigated by a runtime **framebuster** that **fails safe** (any throw reading `window.top` is treated as framed), attempts to break out of the frame, and otherwise **neutralizes** the document (no-op data registry + `display:none` + emptied `<body>`) so the app neither renders nor boots when framed. A `sandbox`ed iframe can defeat any JS framebuster, so on header-capable hosts also send `frame-ancestors 'none'` / `X-Frame-Options: DENY`. Residual risk is low — the app performs no sensitive action (toggles local `known` flags, opens external source links). |
| **localStorage tampering / poisoning** | Keys are namespaced `secstudy:<subject>:*`; all reads are `try/catch` around `JSON.parse` and coerced; values flow only into string comparisons and `textContent`, never a DOM/exec sink. Treated as trusted-local-only. |
| **Malicious local data file on `file://`** | The loader settles on `onload` **or** `onerror` and boots on a counter **or** a last-resort watchdog, so a missing/garbage content file degrades to the empty-state, never a hang or blank page. |

## CSP (shipped via `<meta http-equiv>`)
```
default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:;
font-src 'self'; connect-src 'self'; manifest-src 'self'; worker-src 'self';
object-src 'none'; base-uri 'none'; form-action 'none'
```
- `script-src 'self'` with **no** `'unsafe-inline'` — the code earns this (no inline scripts/handlers/eval).
- `connect-src 'self'` (not `'none'`) because the service worker precaches same-origin assets via
  `cache.addAll`/`fetch`, which `connect-src` governs; `'self'` still blocks every external request.
- `object-src 'none'`, `base-uri 'none'`, `form-action 'none'` close embed/base/form vectors.
- `frame-ancestors` and `X-Frame-Options` are **ignored** in a `<meta>` CSP — covered by the framebuster above.

## Offline / PWA notes
- Service workers do **not** run on `file://`; offline-from-disk works because the files are local.
  The SW is registered **only** on `http(s)` and precaches the shell + content (hashed cache version).
- On iOS, **home-screen install is the durability switch**: installed apps are exempt from ITP's
  ~7-day eviction of script-writable storage that wipes uninstalled tabs. The app shows an install hint
  and calls `navigator.storage.persist()` opportunistically. JSON export/import is the planned backstop.

## Accepted risks / non-goals
- **Clickjacking on header-less hosts** (GitHub Pages) — mitigated by the fail-safe, break-out framebuster
  only; JS framebusters are bypassable by a `sandbox`ed iframe, so this is accepted as low given the app
  takes no sensitive action. Header-level `frame-ancestors`/`X-Frame-Options` is the complete fix where the
  host supports it.
- **The trust gate is high-recall, not a proof.** The two-repo separation + a human checkpoint before
  the first publish are the real backstops; the gate catches the known leak classes mechanically.
- **No integrity hashing of content files at runtime** (SRI) — out of scope; integrity is a build/CI property.
- PNG app icons are a follow-up; an SVG icon ships now (sufficient for identity + the iOS install hint).
