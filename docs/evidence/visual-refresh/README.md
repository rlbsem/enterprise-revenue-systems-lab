# Navy/slate presentation review

The [capture record](capture.json) comes from Chromium serving the real `web/` application on loopback. It uses the nine existing recorded synthetic bundles. This review performs no new model inference, original-engine execution or external-system write. The [local regression record](verification.json) and [test cases](tests.xml) are separate from the historical engineering evidence.

## Visible review

- Seller Authority: original response, reviewer edit, recorded approval/delivery and bound receipt remain visible. The independent-usefulness limitation remains explicit.
- Execution Recovery: delivery attempts, independently observed effects, lost acknowledgment, interruption and the execution-boundary warning remain readable.
- Revenue Integrity: installed ARR and quarterly flows, economic/collection boundaries, account bridge and recorded rebuild comparison remain intact.
- Navy navigation, slate text, neutral surfaces and muted teal actions preserve the existing PR design. At tablet widths, metrics use two columns to avoid overflowing long financial values. On mobile, the breadcrumb stacks above the investigation name without crowding the recorded-evidence badge.

All nine cases were checked at widths **1440, 1280, 768, 390 and 320 pixels**, across all four evidence views: **180 rendered views**. The runner checks page overflow, computed text contrast on solid backgrounds, keyboard tab navigation/focus, successful integrity status, real invalid-import refusal, exact-byte reproduction ZIP downloads and reproduction commands. It confirms that the static server has no execution configuration and that the execution button remains hidden. No JavaScript page errors or non-loopback/mutating browser requests were observed. These measured contrast checks supplement visual inspection; they are not a complete WCAG audit.

## Captures

The README uses full-page, unedited **1440 × 1000 viewport** captures: [Seller](../../images/seller-overview.png), [Recovery](../../images/control-overview.png), [Revenue](../../images/revenue-overview.png). Full-page export height varies with the actual content. Separate **390 × 844 viewport** captures support mobile review: [Seller](../../images/visual-refresh/seller-mobile.png), [Recovery](../../images/visual-refresh/control-mobile.png), [Revenue](../../images/visual-refresh/revenue-mobile.png).

The original README images remain in `docs/images/archive/pre-navy-*-overview.png`, with their hashes in the capture record. Other historical screenshots, recorded artifacts, original suites and native-engine evidence are preserved. [Preservation check](preservation.json).

## Repeat

```shell
python -m playwright install chromium
python scripts/capture_presentation.py --images .cache/new-visual-review --evidence .cache/new-visual-review/capture.json
```

Use fresh output paths to retain previous captures. Normal regression tests should set `LAB_SCREENSHOT_DIR` to an ignored cache directory so they do not overwrite repository screenshots. GitHub CI already sets this variable. Refreshing the README assets intentionally requires `--images docs/images`, followed by package-manifest regeneration and repository checks.

The Pages workflow and static-only distribution boundary are unchanged. This branch does not publish the visual refresh; it remains subject to owner review and merge/deployment approval.
