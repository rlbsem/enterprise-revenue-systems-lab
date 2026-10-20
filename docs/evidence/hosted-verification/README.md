# Hosted explorer verification · October 20, 2026

These observations test the recorded evidence explorer. They do not represent new model inference, Salesforce/Snowflake execution, AWS execution or client outcomes. Existing source bundles, native records and historical screenshots are unchanged.

## Public deployment

[Actual public observations](2026-10-20-public.json) were captured from `https://rlbsem.github.io/enterprise-revenue-systems-lab/` using real Chromium. The latest successful [Pages deployment](https://github.com/rlbsem/enterprise-revenue-systems-lab/actions/runs/39318481410) was revision `e4031c4c043876193741d9d09969797f9b81dfc5`. Its HTML, CSS, JavaScript and catalog matched the inspected checkout's original web files; the report records their SHA-256 values.

Passed observations:

- All ten cases loaded by deep link at 1440×1000 and 390×844, across four investigations. All four evidence views rendered; no horizontal page overflow was observed.
- Browser integrity checks passed. Each of ten downloaded reproduction ZIPs matched its pinned manifest and original artifact bytes, passed CRC checks, and passed the standalone domain verifier.
- All four distinct pinned original-source links returned HTTP 200. Unchanged portable JSON was accepted; altered artifact content was refused.
- Recorded/synthetic limitations were visible and fresh-execution controls were hidden. No browser HTTP writes or off-site requests occurred; read-only execution-endpoint probes returned 404.

The aggregate public check **failed**, correctly, on two groups: case navigation did not update the address, and a nonexistent `api/config` probe generated repeated 404 console errors. Independent interactive browser inspection also confirmed that the existing skip link left focus on `BODY`. The automated navigation group stops at its first failure; it does not claim the later skip-link assertion passed on the public deployment.

## Candidate implementation, locally executed

[Local static-build observations](2026-10-20-local-static.json) use the same verifier against an isolated build served under the Pages repository prefix. All 25 check groups passed, including case URLs, reload/Back/Forward, keyboard tabs and skip-link focus. Static assets in that report are bound by hash; this is **not a deployed-fix result**.

The complete local suite passed **67 tests** (60 existing plus seven new). New negative checks reject changed ZIP artifacts, changed manifests, extra/path-traversal members, duplicate members and missing members. The shared browser check also tests accepted and tampered imports, all cases at both sizes, and the static-only boundary. Unsupported target hosts are rejected before a browser opens.

The changes fix URL/history synchronization, make the main landmark focusable through the skip link, and limit local-API discovery to loopback hosts. Existing server-side execution authorization remains intact. No evidence or business logic was changed.

## Reproduce and interpret

Follow [deployment verification](../../deployment.md). `python scripts/verify_hosted.py` always checks the actual public URL; it must not be relabeled a success while the old deployment remains live. After an approved merge/deployment, the read-only hosted workflow must pass against the deployed revision before claiming these fixes are verified publicly. A local pass or green PR CI cannot establish that result.

Chromium checks and visual inspection cover the exercised desktop/mobile paths and keyboard controls. They are not a comprehensive accessibility certification or a Safari/Firefox/device-lab assessment. Source-link reachability is time-specific. The new workflow cannot be observed running on `main` until it is merged; PR checks exercise its verifier locally instead. No merge or deployment was performed during this review.
