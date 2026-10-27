# Eight-investigation presentation reconciliation

PR #10 is reconciled with main `834750dcc50b1759c736e0e081d1bf8aca41fb5a`, the PR #11 merge. Its original head was `219fceffa63fae618593f48646c0ddbfc4b4eb31`. A normal merge updates the existing branch; no history is rewritten and no replacement PR is needed.

## What changed

- Retain PR #10's intended copy improvements: clearer invoice/cash wording, punctuation in research hypotheses and release boundaries, and the Revenue Integrity display title. Only that catalog title changes; all 17 case IDs, eight investigation groups, source pins, bundle hashes and verification hashes remain intact.
- Preserve Analytics Engineering's 15-model lineage, typed fixture examples, six paired benchmark records, rejected optimization and separate historical Snowflake evidence. No financial definitions, datasets or recorded outcomes change.
- Correct the secondary "Six investigations" label to eight and update current documentation to acknowledge that PR #11 is merged. Model-evaluation candidates remain correctly described as candidates.
- Point README images at new current captures. Earlier main and PR #10 images, raw records and contemporaneous provenance remain unchanged. Archived notes describing an unmerged source or fewer investigations describe their capture-time state, not current release status.

## Genuine current screenshots

[All presentation captures and 340 view checks](evidence/release-qa-eight/presentation.json) · [Research](evidence/release-qa-eight/research.json) · [Model release](evidence/release-qa-eight/release.json) · [Revenue Integrity](evidence/release-qa-eight/integrity.json) · [Analytics Engineering](evidence/release-qa-eight/analytics.json).

These five runners produce 34 unedited screenshots and 490 layout/contrast observations. The dedicated runners also check 36 automated accessibility states. Widths include 320, 390, 768, 1024 and 1440 pixels. Artifact validation, all four evidence tabs, keyboard navigation, exact ZIP downloads and refusal of altered imports remain covered. Automated results are not a complete assistive-technology audit.

![Reconciled eight-investigation seller page](images/release-qa-eight/presentation/seller-overview.png)

![Preserved Analytics Engineering investigation](images/release-qa-eight/analytics/analytics-engineering-desktop.png)

[Analytics mobile](images/release-qa-eight/analytics/analytics-engineering-mobile.png) · [Recovered financial comparison](images/release-qa-eight/integrity/revenue-integrity-recovery.png) · [Native CRM record view](images/release-qa-eight/presentation/connected-overview.png).

Each provenance record binds the current source files and exact PNG hashes. New captures are under `docs/images/release-qa-eight`; no historical image is replaced. The first working capture exposed the stale secondary count, which was corrected before final capture; those working files remain private under `.cache`.

## Evidence preservation and verification

[Preservation hashes](evidence/release-qa-eight/preserved-files.json) protect 368 pre-existing evidence/image files from both heads. [Main UI snapshot](evidence/release-qa-eight/prior-ui-main.json) and [PR #10 UI snapshot](evidence/release-qa-eight/prior-ui-pr10.json) retain capture-time source text. Historical screenshot tests use their historical source; current release tests require fresh images to match current code. They do not rewrite original hashes to make old captures look current.

The regression contract explicitly permits only the intended Revenue Integrity display-title change. It requires all other catalog fields and the complete source lock to match merged main. The original Analytics Engineering acceptance gates still execute.

[Executed local regression](evidence/release-qa-eight/tests.json): **195 tests passed**, zero failures, errors or skips. This includes the original Analytics Engineering gates and new preservation/current-capture checks.

Run locally with the locked environment and Chromium:

```text
python -m pytest -q --basetemp .cache/release-tests
python scripts/capture_presentation.py --images .cache/release-images --evidence .cache/release-presentation.json
python scripts/capture_research.py --images .cache/release-research --output .cache/release-research.json
python scripts/capture_release.py --images .cache/release-model --output .cache/release-model.json
python scripts/capture_integrity.py --images .cache/release-integrity --output .cache/release-integrity.json
python scripts/capture_analytics.py --images .cache/release-analytics --output .cache/release-analytics.json
python scripts/check_repository.py
python scripts/build.py
python scripts/package.py
```

The package manifest is regenerated from the resulting source and documentation. Package ZIPs are reopened and their contents checked. Existing byte-preserving Git attributes remain in force for imported evidence.

## Public baseline versus this release

The [read-only public observation](evidence/release-qa-eight/public-main.json) passed 40 checks against an isolated export of merged main, including desktop/mobile cases, source links and downloads. [Context and source binding](evidence/release-qa-eight/public-main-context.json). Existing main [Pages deployment](https://github.com/rlbsem/enterprise-revenue-systems-lab/actions/runs/40426684205) and [hosted verification](https://github.com/rlbsem/enterprise-revenue-systems-lab/actions/runs/40426758284) also succeeded.

Those results verify the already-published main baseline. They do not claim this PR's reconciled typography or count fix is deployed. This task performs no deployment, merge into main, native vendor execution, inference, new benchmark or cloud provisioning. The static public viewer still has no execution API; local execution remains separately authorized and opt-in.

After approval and merge, the existing main-only Pages workflow may publish the reviewed static files. Confirm both merge and publication approval first, then run hosted verification against that exact deployed revision. This reconciliation does not change the deployment workflow or its permissions.
