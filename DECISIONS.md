# Decisions

Add dated technical and product decisions here.


## 2026-09-16 - Phase one is research and planning, not the README prototype

The 2026-09-16 assignment scopes this phase to source discovery, data understanding, worked
examples, and an implementation plan. The README's resolver, forecaster, PDF pipeline, and
Supabase proposal move to the backlog. Code in this phase is limited to one artifact validator
and a fetch-and-record helper.

## 2026-09-16 - Deliverables live in research/, on branch trial/navy-navwar-peo-c4i

`build/` is gitignored, so the reviewable package is committed under `research/` with the
README's file names kept where they overlap (source_registry.json, organization_seed.json,
manual_pdf_requests.json, documents_manifest.jsonl). Downloaded bytes stay in `data/raw/`.

## 2026-09-16 - Evidence rules

Official public sources only. A Wayback Machine capture of an official page is a dated copy of
that page and its capture timestamp is the "available by" date. Third-party mirrors are
pointers, never evidence. Chromie's production schema is used as column-level shape only; no
production identifiers or data appear in these artifacts.

## 2026-09-16 - Access paths for Akamai-blocked Navy sites

navwar, peoc4i, navsea, navair, niwc, navy.mil, gao and dodig return HTTP 403 to curl and to
headless Chrome from this machine; secnav's budget library closes the TLS handshake;
comptroller.defense.gov interrupts. Egress is Cloudflare WARP. Approved fallbacks, in order:
Wayback capture, a WARP-off fetch session, Browserbase remote browser, manual retrieval queue.

## 2026-09-16 - "PAE" is a reorganization, not a data system

The README asks for an investigation of the "Navy PAE system". Official releases show PAE means
Portfolio Acquisition Executive: the Department of the Navy stood up PAE Mission Systems on
2026-05-11, consolidating mission-systems elements of PEO C4I, PEO Digital, PEO IWS, PEO MLB,
three DRPMs, Minotaur, NAVWAR, NAVSEA, NAVAIR and MCSC. The organization map models this as a
dated reorganization; there is no PAE record system to crosswalk.
