# GTM investigation verification

The [browser record](browser.json) and [screenshots](../../images/gtm/gtm-enterprise-overview.png) observe the Lab's static UI, not new vendor/model execution. The imported original records live in [enterprise](../../../web/evidence/gtm-enterprise/bundle.json), [Salesforce](../../../web/evidence/gtm-salesforce/bundle.json) and [Qwen](../../../web/evidence/gtm-qwen/bundle.json) bundles, each with its own pinned provenance.

The browser review checks all three cases at five viewport sizes and all four evidence tabs, contrast on rendered solid-background text, focus, downloads and import refusal. Full regression results are recorded separately in [JUnit](tests.xml). [Interpretation and limits](../../gtm-investigation.md).

Earlier investigation screenshots and evidence remain historical records; this review does not replace them. Public-site deployment and post-deployment checks remain pending owner approval.

Local result: **96 tests passed**, with no skips, errors or failures. The [all-investigation review](all-investigations.json) checked 260 case/tab/viewport combinations across all five investigations with zero page-overflow, contrast or browser-error findings. The six delivered GTM screenshots retain their own full provenance in `browser.json`.
