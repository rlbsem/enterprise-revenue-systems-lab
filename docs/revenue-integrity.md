# Revenue Integrity: From Sales Commitment to Collected Cash

Route: `?case=revenue-integrity`. This static investigation is included on main. The current presentation reconciliation is not a deployment; consult the Pages and hosted-verification records for public status.

The recorded scenario starts with $39,000 billing net invoices, $37,500 ERP invoice postings, $16,500 allocated cash and $120,000 period-end ARR. The $1,500 difference stays **Review Required**. A separate operator-browser run recovers a fourth account's delivery and observes $45,600 billing / $44,100 ERP. Cash remains $16,500; ARR becomes $146,400. The original variance stays open.

Five selectable stages expose the discrepancy, scoped source-to-posting lineage, a separate lost-acknowledgment delivery run, the operator recovery observations and the architecture. Invoice amounts are recalculated from raw invoice lines, amendments, latest known credits/proration, ERP postings and payment allocations. ARR is independently reconstructed from active recurring terms. The deterministic [projection/checker](../src/revenue_lab/integrity_checks.py) compares those values with the archived model outputs.

## Provenance and boundaries

The source is [Revenue Integrity Platform at `e299309`](https://github.com/rlbsem/enterprise-revenue-integrity-platform/tree/e2993099acaaae188aac0d83ba840cecef1c0014), its recorded [PR #1] acceptance revision(https://github.com/rlbsem/enterprise-revenue-integrity-platform/pull/1). Nine selected original files retain their exact Git bytes and SHA-256 pins in [the source registry](../sources.lock.json). The importer reads Git objects at that revision, never the moving source branch or private runtime.

| Evidence set | What is present | What it does not establish |
|---|---|---|
| Lifecycle acceptance | Raw source exports, invoice-level model results, corrections, six-model/23-test builds, incremental/full comparisons and local PostgreSQL SELECT portability | General financial correctness for arbitrary contracts or native Snowflake acceptance |
| Foundation delivery | Persisted intents, dispatch attempts, independent receiver effects/records, request journals and lost-ack observation | The later fourth-account operator recovery's complete journal |
| Fault tests | Actual killed worker, killed publisher and historical rehydration observations | Managed-cloud PITR, distributed HA, production RPO/RTO |
| Operator capture | 43 original assertions, source fingerprints, billing/ERP totals and links to genuine original screenshots | Full per-attempt, proposal and approval JSON rows; these were not archived at this pin |

The fourth-account cash and ARR values use the versioned fixture's unit price and quantity, corroborated by executed browser assertions. The UI labels this derivation. It never invents a recovery receipt or approval identity. All records describe synthetic USD business data and actual **local** software execution, with finite Salesforce/Stripe/NetSuite contract services. Independent architecture approval of the source platform is not implied.

The source's check-to-commit authorization race, shared local PostgreSQL host and bounded contract scope remain material limits. This explorer does not certify those away. Its selections display recorded states and cannot approve, dispatch, post, reconnect to an operator API or make vendor calls.

## Verify and inspect

```text
python scripts/import_integrity.py <revenue-integrity-git-checkout>
python -m revenue_lab.cli verify web/evidence/revenue-integrity
python scripts/build.py
python scripts/capture_integrity.py --images .cache/integrity/images --output .cache/integrity/browser.json
```

No original engine, PostgreSQL installation, vendor identity or model endpoint is required to view or verify packaged records. Fresh source execution remains in the pinned source repository's own reproduction instructions.

[Browser evidence and screenshots](evidence/revenue-integrity/README.md) · [Original-byte registry](../web/evidence/revenue-integrity/upstream.json) · [Derived display data](../web/evidence/revenue-integrity/projection.json) · [Deployment boundary](deployment.md)

Current eight-investigation presentation and screenshots: [release QA](release-qa-eight.md). Original execution records and their capture-time provenance remain archived at the links above.
