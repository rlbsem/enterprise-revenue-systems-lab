// Separately executed and source-bound native dbt-BigQuery acceptance.
// This is NOT part of the pinned October read-only warehouse bundle.
// Public records: https://github.com/rlbsem/first-party-measurement-assurance/blob/8259a65a6a9ceb3ccb08827733ab6a703c2de99d/docs/evidence/native-dbt-bigquery/README.md
// Browser presentation only: no credentials, new cloud jobs or native calls.
export const nativeBigQuery = Object.freeze({
  date: "2026-11-07 UTC",
  sourceRevision: "a1438e3eef101e23d61f0fd7889272098e50f9f6",
  publishedRevision: "8259a65a6a9ceb3ccb08827733ab6a703c2de99d",
  planSha256: "137a97bfc54a05f9cfab55eec22ed3ec3c31f21b8b135c7ff8a3fb99ca795d0f",
  source: "https://github.com/rlbsem/first-party-measurement-assurance/blob/8259a65a6a9ceb3ccb08827733ab6a703c2de99d/docs/evidence/native-dbt-bigquery/",
  hashes: {
    acceptance: "f6e5ef35bf6774f30e0cd6f2fab11648370db4f4b57d3e1fc996b41557dcd0c6",
    jobs: "c009c0a1aa3e9f6d9e005e859a67ae1a2c20da68be8464b6d9647d22d6b18616",
    independentAudit: "0085c704bd7a7be04def1178d05ea0df1b077734b5a53c2017591a481ee80840",
  },
  phases: [
    {name: "First admitted batch", events: 5, items: 4, purchases: 3, sessions: 3, daily: 3, models: 7, tests: 30},
    {name: "Correction + late event", events: 10, items: 8, purchases: 7, sessions: 6, daily: 5, models: 7, tests: 30},
    {name: "Replay (no new input)", events: 10, items: 8, purchases: 7, sessions: 6, daily: 5, models: 7, tests: 30},
    {name: "Independent full refresh", events: 10, items: 8, purchases: 7, sessions: 6, daily: 5, models: 7, tests: 30},
  ],
  mergeJobs: [
    {phase: "Correction", id: "d59a1ff0-0672-4543-88cc-806a61990676", statement: "MERGE", affectedRows: 6},
    {phase: "Replay", id: "f9581672-4e00-486f-909c-ae14e8636b72", statement: "MERGE", affectedRows: 0},
  ],
  expectedUniquenessFailures: 1,
  independentRowsetsMatched: 5,
  terminalJobs: 178,
  queryJobs: 174,
  loadedBatches: 4,
  datasetCleanup: ["landing", "incremental", "full"],
  observedProcessedBytes: 45741,
  reportedBilledBytes: 2306867200,
  providerReportedBilledBytesAreNotInvoice: true,
  actualBillingClearanceVerified: false,
  productionGA4Export: false,
  productionMeasurementProtocolValidation: false,
});
