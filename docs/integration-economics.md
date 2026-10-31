# Integration architecture economics and GA4 warehouse assurance

## Enterprise Integration Economics

Route: `?case=economics-integration`. The thirteenth investigation compares feasible architecture choices for **1.2 billion annual synthetic source events**, eight workloads and shared capacity. All prices are synthetic USD planning inputs, not vendor quotes or realized commercial savings.

| Recorded architecture | Operating year | Alternative disruption year |
|---|---:|---:|
| Mixed-route reference | $281,923.23 | $285,797.16 |
| Operating-cost optimum | $187,589.95 | $219,506.17 |
| Capacity-resilient choice | $196,752.09 | $200,630.45 |

The disruption year is an alternative demand/retry/quota envelope, not an additional cost or observed production incident. Select an architecture, condition, month and workload to inspect source events, fan-out, partial batches, retries, monthly components, shared cost allocation and hourly headroom. The sensitivity view exposes 22 recorded sweeps; it does not pretend to solve arbitrary new inputs in the browser.

Source: [MarTech Stack Economics at `80cfd618`](https://github.com/rlbsem/martech-stack-economics/tree/80cfd61882cd916406edf8b9fba6ba2ff02f4715). [Exact annual decision](https://github.com/rlbsem/martech-stack-economics/blob/80cfd61882cd916406edf8b9fba6ba2ff02f4715/docs/evidence/enterprise/acceptance/decision.json). The original acceptance records its own execution revision separately from this import revision.

The offline Lab checker independently recalculates integer demand, request/price arithmetic, monthly components, allocated cost conservation, annual totals, eligibility and capacity for all three choices and both envelopes. It checks recorded solver/enumeration agreement, not a newly executed optimization. Assumptions include balanced within-hour emission, a 20% worker reserve and declared route lag. Queue tails, arbitrary synchronized bursts, strict rolling-arrival API guarantees and certified residency remain outside that proof.

### Separate HTTP execution

Eight actual bounded HTTP trials retain accepted and rejected results. They use synthetic records, synthetic prices, an accelerated clock and local independent processes/SQLite. They are **not** a 1.2B-event load test, native vendor integration or a measured production scaling factor.

Two original compressed receiver journals are included as lossless base64 text. Offline checks decode their original bytes, verify the recorded content identity, count every request including recovery GETs, and match each independent receipt to the exact control payload hash. Source/source-result links and a reproduction ZIP are available from the case. Complete upstream trials remain linked; importing them does not rerun their workloads.

## GA4 warehouse verification

Route: `?case=warehouse-verification`, within the existing First-Party Measurement investigation. The preserved `?case=measurement-integrity` conversion/receipt case and all its original files remain available.

Source: [merged First-Party Measurement at `a1438e3e`](https://github.com/rlbsem/first-party-measurement-assurance/tree/a1438e3eef101e23d61f0fd7889272098e50f9f6). [Execution and limitations](https://github.com/rlbsem/first-party-measurement-assurance/blob/a1438e3eef101e23d61f0fd7889272098e50f9f6/docs/warehouse-review.md).

| Evidence lane | What actually executed |
|---|---|
| Native read-only GoogleSQL | Seven existing SELECT bodies rendered into CTEs; separate independent source query, five matching result signatures |
| Public sample scope | One 20210101 obfuscated GA4 shard, purchases and same-day purchaser events; 1,856 events, 4,828 items, 14 purchases, 12 observed sessions, one daily aggregate |
| Native resource record | Two uncached data jobs processed 19,631,768 bytes; provider SQL hashes and actual job IDs retained; job-reported billed bytes are not an invoice |
| Separate local dbt | Synthetic late arrival, correction, replay, incremental/full equivalence and complete Python oracle for all five output rowsets |
| Separate local fault injection | Fourteen negative cases detected by the revised guard; eight were missed by the original. The positive control remains clean |
| Native dbt-BigQuery build / MERGE | **Not executed**. SDK credentials unavailable; the recorded billing-disabled sandbox excludes DML |

The native SQL preview is not dbt compilation/materialization. Observed sessions are slice-censored, item rows include non-purchase interactions, and repeated rows retain multiplicity. Content hash plus occurrence ordinal is snapshot identity, not a canonical event key or cross-export correction identity. Provider-normalized USD fields retain missing values and per-unit integer-cent rounding. No production GA4 export or commercial result is claimed.

Each artifact links its exact blob revision. Where a historical local report hashes a verifier that subsequently changed, the original execution-revision file is imported, not silently replaced by current main. The original report and source bytes remain untouched.

## Read-only architecture and reproduction

No new source-engine execution, inference, vendor call, cloud resource, credential or deployment is introduced. The existing static-only GitHub Pages boundary and local execution allowlist remain unchanged. Focus links expose direct, shareable entry points for integration architecture, MarTech/analytics engineering, AI/GTM and enterprise change governance. The new routes are verified locally under the actual Pages subpath; public availability requires owner-approved merge/deployment and separate hosted verification.

```text
python -m pytest -q
python scripts/capture_integration.py --output .cache/fresh-integration/browser.json --images .cache/fresh-integration/images
python scripts/check_repository.py
python scripts/build.py
python scripts/package.py
```

Use fresh capture paths; historical screenshots are not overwritten. To reproduce a source import into a fresh baseline checkout, fetch the pinned commits in both source repositories and run `python scripts/import_economics_warehouse.py <economics-checkout> <measurement-checkout>`. Existing captures are intentionally refused. Downloaded bundles can be inspected with `python -m revenue_lab.cli verify <bundle-directory>` without credentials or source-engine installation.

[Screenshot provenance and verification](evidence/integration-economics/README.md) · [Source lock](../sources.lock.json).
