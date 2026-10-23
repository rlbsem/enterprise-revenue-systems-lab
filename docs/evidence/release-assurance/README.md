# Release investigation browser verification

The [browser record](browser.json) records genuine Chromium execution against the built static distribution under `/enterprise-revenue-systems-lab/`. It is a local candidate check, not a public deployment or another model evaluation.

The capture checks seven release states at 1440, 1024, 768, 390 and 320 CSS pixels, plus all three other evidence tabs at each width. It checks horizontal overflow and rendered text contrast. Automated axe-core 4.10.3 WCAG 2 A/AA and 2.1 AA checks cover each state at desktop and mobile widths; incomplete rules remain reported. These automated observations are not an accessibility certification.

Three images are direct browser viewport captures, without compositing or invented outcomes:

- [Desktop comparison and acceptance](../../images/release-assurance/release-assurance-desktop.png)
- [Controlled fault and reference routing](../../images/release-assurance/release-assurance-rollback.png)
- [Mobile release-state controls](../../images/release-assurance/release-assurance-mobile.png)

The browser record hashes the exact UI/build inputs, capture script and images. [Preserved-file hashes](preserved-files.json) independently pin all five prior investigations' evidence and historical screenshots to the starting main revision. They must remain byte-exact.

The previous SDR screenshot record still describes its original UI. A [source snapshot](prior-research-ui.json) preserves those exact UI bytes, so its historical hashes remain independently checked after shared navigation changes. CI also renders the current SDR interface into temporary output; the original screenshot record is not rewritten.

New regression tests additionally exercise rejected records, all seven interactive states, keyboard controls, task filters, exact destination readback, downloaded ZIP verification and refusal when verification JSON is corrupted. The full existing Pages-shaped smoke suite covers every catalog case at desktop and mobile sizes. [Actual local test results](tests.xml).

Reproduce without overwriting committed screenshots:

```shell
python scripts/capture_release.py --images .cache/release/screenshots --output .cache/release/browser.json
```

The browser makes no model/vendor calls or HTTP writes. Complete source evaluation evidence remains in the [pinned Agent Runtime repository](https://github.com/rlbsem/enterprise-agent-runtime-evaluation/tree/84b7bbaa92b08d3238aa321ada52b4881a62b4c2). [Investigation and limitations](../../model-release-assurance.md).
