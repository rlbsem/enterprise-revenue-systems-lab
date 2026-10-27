# Architecture assurance browser evidence

This folder records Lab verification separately from the original source runs.

- [Local verification](verification.json): 256 passing tests, 721 layout/contrast observations and 76 automated accessibility states across the existing and new investigations. All recorded automated states have zero violations; this is not a complete manual accessibility certification.
- [Pages-shaped static smoke](static-build.json): 48 passing read-only checks, including all 21 cases, exact deployed asset bytes, navigation, downloads, tamper refusal, source links and absence of an execution API. This was a local build, not public deployment.
- [Actual browser capture](browser.json): static Pages-prefix execution, source/image hashes, interactions, desktop/mobile layouts, contrast observations and automated accessibility results.
- [Preserved baseline](preserved-main.json): SHA-256 inventory of 476 pre-existing evidence/image files at main `6135acd0c8ff4e4970d05ece035b31f963120ad6`.
- [Prior main UI](prior-main-ui.json): exact original UI and source-lock text, allowing historical screenshot provenance to remain verifiable without changing its original record.

Original source records are packaged under `web/evidence/estate-assurance`, `web/evidence/reliability-operations` and `web/evidence/temporal-assurance`. Their manifests distinguish original bytes from derived Lab projections. [Pins, checks and execution boundaries](../../architecture-assurance.md).

| Investigation | Actual desktop | Failure / recovery drilldown | Actual mobile |
|---|---|---|---|
| Enterprise Change Assurance | [Retirement impact](../../images/architecture-assurance/estate-desktop.png) | [Readiness decisions](../../images/architecture-assurance/estate-proof.png) | [Mobile](../../images/architecture-assurance/estate-mobile.png) |
| MarTech Data Reliability | [Source-to-report values](../../images/architecture-assurance/reliability-desktop.png) | [Rejected publication](../../images/architecture-assurance/reliability-proof.png) | [Mobile](../../images/architecture-assurance/reliability-mobile.png) |
| Temporal Audience Assurance | [Two clocks](../../images/architecture-assurance/temporal-desktop.png) | [Independent receipt recovery](../../images/architecture-assurance/temporal-proof.png) | [Mobile](../../images/architecture-assurance/temporal-mobile.png) |

Screenshots are uncomposited viewports from the running static application using the original synthetic evidence. No source engine, vendor, model endpoint or cloud service was executed for this capture. The feature is not claimed to be publicly deployed.
