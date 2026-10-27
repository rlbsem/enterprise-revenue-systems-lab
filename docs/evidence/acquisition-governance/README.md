# Acquisition investigation verification

[Local Lab verification](local-verification.json) records 254 passing regression tests, 617 layout/contrast observations and 60 automated accessibility states across all ten investigations. No overflow, contrast failures, page errors or automated accessibility violations remain. Automated accessibility does not establish full assistive-technology conformance.

[Fresh source regression](source-regression.json) records 83 tests actually executed in a disposable checkout of the pinned source, with local PostgreSQL, HTTP and dbt. The original source checkout was not modified. This is separate from the original 62-test software acceptance and historical browser observations.

[New browser capture provenance](browser.json) binds three genuine screenshots to actual current source files and the GitHub Pages-shaped local static build. Historical screenshots and records remain untouched. Existing specialized browser scripts were reexecuted into ignored local output; their observations and report hashes are summarized in the local record and their gates run again in CI.

[Preservation inventory](preserved-files.json) protects 476 historical evidence/image files from the nine-investigation baseline. [Capture-time UI source](prior-ui.json) keeps prior screenshot assertions bound to their actual historical source.

[Original artifact inventory](../../../web/evidence/acquisition-governance/upstream.json) contains 39 exact source blobs. The [main evidence guide](../../acquisition-governance.md) explains the separate financial scenarios, source oracle and execution boundaries.

No source repository, GitHub profile, native vendor state or cloud resources were modified. CI results belong to the pull request's exact head; local success does not claim hosted deployment or GitHub Actions success before it executes.
