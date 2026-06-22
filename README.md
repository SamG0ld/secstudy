# secstudy — Security Study Platform

> An MVP built for an upcoming technical interview — a focused, offline-first cards app for security &
> cloud-engineering interview prep. Expected to grow into a fuller web app.

A **zero-dependency, offline-first, mobile-first** study app built around a **self-verifying, cited
knowledge base**: every card links to an authoritative primary source and carries a last-verified date.

## Highlights
- **Zero runtime dependencies** — vanilla HTML/CSS/JS. Opens from `file://`, works fully offline,
  installable as a PWA.
- **Cited & dated** — provenance is a first-class feature; every card has a `source` + `verified` date
  with a freshness-aware badge.
- **Honest about confidence** — a source that can't be checked by an automated fetcher (e.g. a
  regulator site that blocks bots) ships the real link with an explicit **"unverified"** badge, never
  disguised as verified.
- **Secure by design** — strict CSP, XSS-safe DOM rendering (no `innerHTML` with content), no
  telemetry, no external runtime requests. See [THREAT-MODEL.md](./THREAT-MODEL.md).
- **AWS cloud security** ships first (289 cards: IAM, networking, S3, EC2, Lambda, ECS/EKS, RDS, KMS,
  detection, HIPAA/FDA/PHI, DevSecOps, agentic-AI, incident response).

## Using it
- **Offline / from disk:** open `index.html` in any modern browser.
- **Hosted / installable:** visit the GitHub Pages URL; "Add to Home Screen" installs it as an offline
  PWA (on iOS, installing is also what makes your study progress durable).
- Flip cards, mark known/again, filter by topic, shuffle, search the whole deck, and open each card's
  primary source to verify the answer yourself.

## Design methodology
This MVP is partly a demonstration of a small, repeatable methodology:

- **Constraint-driven.** One hard rule (zero runtime dependencies; must run from `file://`) drives every
  choice — data loads via `<script src>` registry globals (not `fetch`/imports), rendering is
  `textContent`-only, and the build is Python-stdlib-only.
- **Provenance-first, honest about confidence.** Every card is cited + dated; a build-time trust gate
  refuses to ship anything unsourced, and citations that can't be machine-verified are flagged
  "unverified" rather than hidden or over-claimed.
- **AI-assisted, human-gated.** Primary sources were proposed by AI agents (each link verified to
  resolve), with a human approving and setting the verified date — never the agent — and a mechanical
  trust gate (schema + host allowlist + PII/leak scan, fail-closed) enforcing the result in CI. AI for
  breadth, humans for attestation, code for the guarantee.

**Pairs well with autonomous-research tooling** such as
[karpathy/autoresearch](https://github.com/karpathy/autoresearch): where autoresearch is the autonomous
*generation* loop (an agent iterating ML experiments), secstudy is the *verification + provenance* layer
that turns machine-generated findings into knowledge you can cite, date, and trust.

## Roadmap
Interview-timed MVP today (one subject, cards, offline-first). Next: spaced repetition, quiz and
interviewer modes, `docs`/`resources` content types, a freshness view, and an optional online
AI-interviewer companion — without breaking the zero-dependency offline core.

## License
- **Code:** MIT — see [LICENSE](./LICENSE).
- **Content** (study cards): **CC BY 4.0** — attribution required, no warranty.
