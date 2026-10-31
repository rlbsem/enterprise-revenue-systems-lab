# Integration economics and warehouse browser proof

These captures come from the actual static `dist/` application at the GitHub Pages subpath. They are new records, separate from every historical source or Lab screenshot. No model, vendor, solver or source-engine execution occurs during capture.

[Current browser record](font-fix/browser.json) binds the UI files and exact image hashes, responsive layouts, automated accessibility observations and every catalog route. Automated accessibility checks do not replace assistive-technology review.

- [Architecture alternatives](../../images/integration-economics/font-fix/economics-integration-desktop.png)
- [Recorded sensitivity](../../images/integration-economics/font-fix/economics-integration-detail.png)
- [Separate bounded HTTP outcomes](../../images/integration-economics/font-fix/economics-integration-http.png)
- [Economics mobile](../../images/integration-economics/font-fix/economics-integration-mobile.png)
- [Native SQL comparison](../../images/integration-economics/font-fix/warehouse-verification-desktop.png)
- [Corrected guard and preserved failures](../../images/integration-economics/font-fix/warehouse-verification-detail.png)
- [Warehouse mobile](../../images/integration-economics/font-fix/warehouse-verification-mobile.png)

[540 preserved historical files](preserved-main.json) · [Previous main UI/source-lock snapshot](prior-main-ui.json) · [Evidence architecture and exact source links](../../integration-economics.md).

[Initial local verification](local-verification.json): 281 passing tests, zero skipped/failed tests; 184 catalog states, 40 new responsive/contrast states and 16 automated accessibility states with no violations or incomplete observations. Seven genuine screenshots. No external requests, HTTP writes or vendor/model execution.

## Narrow-screen CI correction

Linux CI at `89d6a1e` preserved a failed 320-pixel rejected-trial layout assertion. The correction constrains the new selectors and gives fact labels/values shrinkable columns; it does not hide overflow or change evidence. [Original capture](browser.json), [original local regression](local-verification.json) and [its exact source snapshot](prior-capture-source.json) remain unchanged. Current captures add all eight HTTP trial and fourteen regression-fault selections at 320/390 pixels (44 additional layout/contrast states). [Intermediate local regression](mobile-fix/local-verification.json).

Current acceptance: **282 tests passed**, plus 184 catalog states, 84 new responsive/contrast states, 32 additional font-fallback states and 16 automated accessibility states with zero violations/incomplete observations. Seven fresh screenshots accompany the preserved first capture. [Initial CI observations](mobile-fix/ci-regression.json). The shared presentation review also executes its full 460-view registry; it now uses the established canonical archive builder.

## Font-fallback verification

The selector/fact correction alone did not resolve the Linux metric-grid overflow. A separate local diagnostic reproduced it with Arial: the document grew to 321 pixels at a 320-pixel viewport. The final scoped fix uses a single metric column for this economics case below 420 pixels, without hiding content or changing values. The regression explicitly forces Arial, and capture adds 32 Arial/serif stage-width checks. [Recorded second CI failure and local diagnosis](font-fix/ci-regression.json). [Current local verification](font-fix/local-verification.json). Earlier source-bound captures remain unchanged at their published commits, including [the intermediate capture](mobile-fix/browser.json) at `0cdd6a7`.
