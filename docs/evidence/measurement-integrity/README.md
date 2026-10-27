# Ninth-investigation verification

[Local verification](local-verification.json) records 223 passing regression tests, a final 26-test domain check, 550 browser layout/contrast observations and 46 automated accessibility states across the full application. No overflow, contrast failures, page errors or automated accessibility violations were observed. Automated accessibility does not replace human assistive-technology review.

[New browser capture provenance](browser.json) binds the three genuine screenshots to the current UI and source pin. Existing specialized browser scripts were reexecuted into ignored local output and are repeated by CI; the summary records their observations without replacing historical captures.

[Fresh local GA4 fixture](fixture-execution.json) records five actual DuckDB/dbt rowsets, an independent physical full-build comparison and original fixture replay/correction gates. The Lab also checks every row against a separate CSV-based oracle. This is not native Google execution.

[Preservation inventory](preserved-files.json) protects 413 prior evidence and screenshot files. [Capture-time UI snapshot](prior-ui.json) preserves the original eight-investigation source for historical screenshot assertions.

The source [import inventory](../../../web/evidence/measurement-integrity/upstream.json) contains 45 exact original blobs at the pinned source revision. No source repository files were changed. No new BigQuery, Measurement Protocol, cloud resource or production operation occurred.

Linux, Windows and original-source engine CI results belong to the pull request's exact head. Local results above do not claim GitHub CI success before it finishes. The feature must not be described as publicly deployed before a separately approved release and hosted check.
