# Analytics Engineering — Model Correctness & Performance

The eighth investigation asks whether a model can be trusted, and whether a measured optimization is worth keeping. Preview route: `?case=analytics-engineering`. It is a static, read-only evidence explorer; this feature requires an approved merge and the existing Pages deployment before public availability is established.

## Inspect the implementation

1. **Model & grain:** Choose any of 15 models. Follow its actual dbt parents and descendants, read the pinned SQL, and inspect source CSV rows. Typed modeled rows come from a separately executed small local fixture, with at most four displayed rows per model. They are not invented enterprise samples.
2. **Metric contracts:** Inspect six metric identities and seven retained definitions, including both ARR versions. Opportunities, booking events, invoice/credit lines, cash allocations and subscription periods keep distinct grains and clocks. A recorded fixture bridge shows why bookings, invoices and cash differ.
3. **Corrections & quality:** Filter the 87 recorded source software results, inspect the fixture's historical correction and fanout findings, and distinguish source execution from this Lab's offline record validation.
4. **Measured performance:** Switch between 60,000 and 180,000 accounts, examine all three repetitions at each scale, and select a pair for model comparisons, change-detection overhead, sampled memory and database size. The corrected stress fact has **37,375,442 opportunity-day rows**; the enterprise fact has 12,470,664.
5. **Native warehouse:** Inspect the separate historical Snowflake fixture: three builds of 15 models and 30 tests, all-model equality, four consumer denials, publication safety and 461 archived query IDs.

## Why the candidate was rejected

The original incremental path already replaces changed opportunities. The opt-in candidate narrows downstream pipeline aggregation to affected account histories. It reduced aggregation work, but exact change detection, retained snapshots, quality gates and checkpointing cost more overall.

| Recorded local scale | Original median incremental | Candidate median total | Change |
|---|---:|---:|---:|
| 60,000 accounts | 12.447s | 19.205s | +54.3% |
| 180,000 accounts | 43.923s | 57.634s | +31.2% |

These values are calculated from the original pair records, then checked against their archived summary. The predeclared target required at least 15% improvement. The candidate was not promoted and the default did not change.

One Windows host, one DuckDB/dbt thread, fresh warehouse files and a 2GB engine setting were used in both arms. OS caches were not flushed. Loading, complete comparisons and consumer checks have separately recorded costs. Sampled process-tree RSS may double-count shared pages and miss peaks; 2GB is not a process memory cap. None of these observations is a Snowflake benchmark, production capacity guarantee or commercial saving.

## Provenance and execution boundaries

Original bytes are imported from Revenue Metrics Platform revision [`4cc1480d63f1095584db2ddcde72ed5626eb7ea7`](https://github.com/rlbsem/revenue-metrics-platform/tree/4cc1480d63f1095584db2ddcde72ed5626eb7ea7). [Source lock](../sources.lock.json) and [artifact provenance](../web/evidence/analytics-engineering/upstream.json) bind every imported path and SHA-256. Importing at that revision does not make the historical runs new executions.

- [Enterprise execution protocol](../web/evidence/analytics-engineering/enterprise-execution-protocol.json) records executed source `d26b4300338aa0b78f5434b3fca5ae45ab62033a`.
- [Stress execution protocol](../web/evidence/analytics-engineering/stress-execution-protocol.json) records executed source `b13a011ae08dd11abb05cdea03b956ce6bac83ca`.
- [Historical native fixture](../web/evidence/analytics-engineering/snowflake.json) predates the USD unit correction. It does not establish native acceptance of the current USD-specific version, the selective candidate or enterprise-scale Snowflake performance. Final billed consumption remains unavailable.
- [Small local fixture row capture](evidence/analytics-engineering/fixture-execution.json) ran the pinned source in an isolated copy, passed its independent fixture expectations and 15 models / 30 dbt tests, and produced the same validated fixture release already archived upstream. SQL/CSV source hashes, typed column contracts and bounded actual model rows are recorded. It is not the historical native run or a new large benchmark.

The source README retains an older statement that stress had not executed. This investigation cites the later controlled benchmark records and their execution revisions; it does not rewrite that source or its history. The original third Lab investigation remains pinned to its earlier revenue scenario.

## Validate and reproduce

The public browser needs no credentials, Python, database or model endpoint. Use **Validate artifact integrity**, inspect **Source records** / **Compare & verify**, and download the reproduction ZIP.

With the Lab's locked Python dependencies:

```text
python -m revenue_lab.cli verify web/evidence/analytics-engineering
python scripts/build.py
python scripts/check_repository.py
```

Offline verification checks original-byte hashes, source pins, lineage completeness, median arithmetic, 270 recorded model comparisons, recorded gates, native query relationships and the derived display projection. It does **not** repeat complete warehouse rowset comparisons. Those original records report complete grain-ordered typed exports compared bytewise or value-by-value, not probabilistic signatures. The compact download contains their records, not 37 million rows.

To repeat the small local row capture, export the exact source revision into a fresh isolated directory, install that platform's locked dependencies in its own environment, then run this Lab's `scripts/capture_analytics_fixture.py --source <export> --workspace <new-private-workspace> --output <new-private-record.json>`. The script refuses existing outputs/workspaces and invokes only `revenue demo --profile fixture`. Repeating large benchmarks remains an explicit, resource-intensive source-platform operation; [original performance contract](https://github.com/rlbsem/revenue-metrics-platform/blob/4cc1480d63f1095584db2ddcde72ed5626eb7ea7/docs/performance.md).

[Genuine screenshots and current Lab verification](evidence/analytics-engineering/README.md). The source platform and GitHub profile are unchanged. No cloud resources or new vendor calls are involved.
