// Recorded synthetic evidence only. No query engine, vendor connection or writes.
const stages = [["models", "01", "Model & grain"], ["metrics", "02", "Metric contracts"], ["quality", "03", "Corrections & quality"], ["performance", "04", "Measured performance"], ["native", "05", "Native warehouse"]];
const number = n => new Intl.NumberFormat("en-US").format(n);
const seconds = n => n.toFixed(3) + "s";
let selected = "models", selectedModel = "fct_opportunity_daily", profile = "stress", pair = 1;

export function analyticsMetrics(read, metric) {
  const p = read("projection.json");
  return [metric("SQL/dbt models", p.models.length, "Explicit grains and dependencies"),
    metric("Corrected stress fact", (p.profiles.stress.fact_rows / 1e6).toFixed(2) + "M", "Recorded opportunity-day rows"),
    metric("Paired repetitions", "3 + 3", "Local 60K / 180K account scenarios"),
    metric("Selective rebuild", "REJECTED", "Total build time regressed at both scales")];
}

export function analyticsPanel(ui) {
  const {el, facts, finding, json: read} = ui, p = read("projection.json"), up = read("upstream.json");
  const root = el("div", undefined, "analytics-investigation release-investigation");
  const section = title => { const n = ui.section(title); n.querySelector(".panel-title").replaceWith(el("h3", title, "panel-title")); return n; };
  const raw = value => { const n = ui.raw(value); n.tabIndex = 0; return n; };
  const inspect = (parent, title, value) => { const d = el("details"); d.append(el("summary", title), raw(value)); parent.append(d); };
  const origin = (file, label) => { const a = el("a", label + " ↗"); a.href = up.artifacts.find(x => x.file === file).source_url; return a; };
  function table(headers, rows, caption) {
    const wrap = el("div", undefined, "analytics-table"); wrap.tabIndex = 0; wrap.setAttribute("role", "region"); wrap.setAttribute("aria-label", caption);
    const t = el("table"), head = el("thead"), tr = el("tr"); t.append(el("caption", caption));
    for (const h of headers) { const cell = el("th", h); cell.scope = "col"; tr.append(cell); } head.append(tr); t.append(head);
    const body = el("tbody"); for (const row of rows) { const tr = el("tr"); for (const v of row) tr.append(el("td", v)); body.append(tr); } t.append(body); wrap.append(t); return wrap;
  }
  const hero = el("div", undefined, "release-hero"); hero.append(el("small", "RECORDED ANALYTICS ENGINEERING · SYNTHETIC DATA", "release-kicker"),
    el("h2", "Correct results. Measured tradeoffs."), el("p", "A faster aggregation did not make a faster build. Inspect the financial grains, complete-model comparisons and actual measurements behind the decision to keep the original default."));
  root.append(hero);
  const nav = el("nav", undefined, "release-stages"); nav.setAttribute("aria-label", "Analytics investigation stages");
  const announce = el("p", undefined, "release-announcement"); announce.setAttribute("role", "status");
  const content = el("div", undefined, "release-detail"); content.id = "analytics-detail";
  function choose(label, id, options, value, action) {
    const box = el("div", undefined, "analytics-control"), l = el("label", label), s = el("select"); l.htmlFor = id; s.id = id;
    for (const [v, title] of options) { const o = el("option", title); o.value = v; s.append(o); } s.value = value;
    s.addEventListener("change", () => action(s.value)); box.append(l, s); return box;
  }
  function show() {
    for (const b of nav.querySelectorAll("button")) b.setAttribute("aria-pressed", String(b.dataset.analyticsStage === selected));
    announce.textContent = "Viewing recorded evidence: " + stages.find(s => s[0] === selected)[2]; content.replaceChildren();
    if (selected === "models") {
      const box = section("What is one row supposed to mean?");
      box.append(el("p", "Facts retain their own grain before aggregation. A booking event is not an invoice line, a payment allocation or a period-end subscription balance. Joining those raw facts together can multiply money."));
      const controls = choose("Choose a dbt model", "analytics-model", p.models.map(m => [m.name, m.name]), selectedModel, value => { selectedModel = value; show(); });
      const model = p.models.find(m => m.name === selectedModel), lineage = read("lineage.json");
      box.append(controls, facts([["Selected model", model.name], ["Declared grain", model.grain || "Aggregate model: inspect its SQL grouping below"],
        ["60K corrected model rows", number(p.profiles.enterprise.model_rows[model.name])], ["180K corrected model rows", number(p.profiles.stress.model_rows[model.name])]]));
      const graph = el("div", undefined, "analytics-lineage");
      function edges(title, ids) { const card = section(title); if (!ids.length) card.append(el("p", "No direct model descendants in this graph."));
        for (const id of ids) { const name = id.split(".").at(-1); if (id.startsWith("model.")) { const b = el("button", name); b.type = "button"; b.addEventListener("click", () => { selectedModel = name; show(); }); card.append(b); } else card.append(el("code", "raw." + name)); } return card; }
      graph.append(edges("Reads from", model.parents), edges("Feeds into", Object.entries(lineage).filter(([_, v]) => v.resource_type === "model" && v.depends_on.includes("model.revenue_metrics." + model.name)).map(([k]) => k)));
      box.append(graph);
      const execution = read("fixture-execution.json"), modeled = execution.models[model.name];
      const modeledBox = section("Executed modeled rows · small local fixture");
      modeledBox.append(el("p", "Actual local DuckDB/dbt fixture execution at " + execution.executed_at + ". First " + modeled.sample.length + " of " + modeled.rows + " ordered rows. This is separate from the historical Snowflake fixture and the large local benchmarks.", "gtm-boundary"));
      inspect(modeledBox, "Inspect typed model columns and recorded rows", {columns: modeled.columns, rows: modeled.sample}); box.append(modeledBox);
      inspect(box, "Inspect exact SQL · " + model.name, ui.text(model.sql)); box.append(origin(model.sql, "Open pinned source SQL"));
      const sources = new Set(); function walk(id) { if (id.startsWith("source.")) sources.add(id.split(".").at(-1)); else for (const parent of lineage[id]?.depends_on || []) walk(parent); }
      model.parents.forEach(walk);
      const sourceBox = section("Small fixture source records"); sourceBox.append(el("p", "Original hand-authored fixture CSVs, not a sample of the 60K/180K enterprise dataset. Showing at most 12 source rows per table; the download contains the complete small fixture. Model counts above come from separate recorded benchmark comparisons.", "gtm-boundary"));
      for (const name of [...sources].sort()) { const rows = p.fixture_sources[name]; if (!rows) continue; inspect(sourceBox, "raw." + name + " · first " + Math.min(rows.length, 12) + " of " + rows.length + " fixture rows", rows.slice(0, 12)); }
      box.append(sourceBox); content.append(box);
    } else if (selected === "metrics") {
      const box = section("One governed meaning for each number");
      box.append(finding("Installed ARR ≠ bookings ≠ invoices ≠ cash", "The six metric identities use different grains and clocks. ARR and pipeline are stocks; bookings, invoices and allocated cash are flows. None is recognized revenue."));
      let index = 0; const detail = el("div"); function contract() { detail.replaceChildren(); const m = p.metrics[index]; detail.append(facts(Object.entries(m).filter(([k]) => !["metric_id", "title"].includes(k)).map(([k, v]) => [k.replaceAll("_", " "), Array.isArray(v) ? v.join(", ") : v]))); }
      box.append(choose("Choose a metric definition and version", "analytics-metric", p.metrics.map((m, i) => [String(i), m.title + " · v" + m.version]), "0", v => { index = Number(v); contract(); }), detail);
      contract(); box.append(origin("metrics.json", "Open all six metric contracts and retained ARR versions"));
      box.append(table(["Account", "Bookings", "Net invoiced", "Allocated cash"], read("fixture-publication.json").bridge.map(r => [r.account_name, r.bookings.toFixed(2), r.invoiced.toFixed(2), r.cash.toFixed(2)]), "Executed current fixture publication · synthetic USD · selected bridge rows, not enterprise economics"));
      inspect(box, "Inspect complete recorded fixture publication", read("fixture-publication.json")); content.append(box);
    } else if (selected === "quality") {
      const box = section("A late correction must not leave old history behind."); const cases = read("fixture-cases.json");
      box.append(facts([["Recorded software tests", p.software_tests], ["dbt quality gates", "30 per recorded build"],
        ["Fixture pipeline before / after correction", cases.historical_pipeline_correction.base_cents / 100 + " / " + cases.historical_pipeline_correction.corrected_cents / 100 + " USD"],
        ["Fanout: correct / naive join", cases.invoice_join_fanout.correct_cents / 100 + " / " + cases.invoice_join_fanout.naive_join_cents / 100 + " USD"]]));
      box.append(el("p", "Original opportunity processing replaces the full history of changed opportunities. The selective candidate additionally rebuilds affected account histories downstream. Complete typed-export comparisons, not probabilistic signatures, were recorded for all 15 models against original incremental and independent full builds, plus no-op comparisons."));
      const tests = el("div"), label = el("label", "Filter recorded regression tests"), input = el("input"); label.htmlFor = "analytics-test-filter"; input.id = label.htmlFor; input.type = "search";
      function filtered() { const results = read("software.json").filter(t => t.test.toLowerCase().includes(input.value.toLowerCase())); tests.replaceChildren(table(["Recorded regression", "Outcome"], results.map(t => [t.test, t.status]), results.length + " recorded tests match")); }
      input.addEventListener("input", filtered); box.append(label, input, tests); filtered();
      inspect(box, "Fixture correction and fanout observations", cases);
      box.append(finding("Recorded equality is evidence, not a new comparison here", "The compact package preserves complete upstream comparison records. It does not contain millions of exported fact rows. The Lab validates records, arithmetic and hashes offline; fresh warehouse equality requires reproducing the source benchmark."), origin("software.json", "Open exact executed test results")); content.append(box);
    } else if (selected === "performance") {
      const box = section("Less aggregation work. More total elapsed time.");
      box.append(choose("Choose a recorded benchmark scale", "analytics-profile", [["enterprise", "60,000 accounts · enterprise"], ["stress", "180,000 accounts · stress"]], profile, v => { profile = v; show(); }));
      const stats = p.profiles[profile], protocol = read(profile + "-execution-protocol.json");
      box.append(facts([["Corrected opportunity-day fact", number(stats.fact_rows)], ["Original median incremental", seconds(stats.baseline_median_seconds)],
        ["Candidate median total", seconds(stats.candidate_median_seconds)], ["Elapsed regression", "+" + stats.wall_change_percent.toFixed(1) + "% · candidate not promoted"]]));
      const bars = el("div", undefined, "analytics-bars"); for (const [label, value] of [["Original", stats.baseline_median_seconds], ["Selective candidate", stats.candidate_median_seconds]]) { const row = el("div"); row.append(el("span", label + " · " + seconds(value))); const track = el("div"); track.style.width = (value / stats.candidate_median_seconds * 100) + "%"; row.append(track); bars.append(row); } box.append(bars);
      box.append(table(["Pair", "Original incremental", "Candidate total", "Original no-op", "Candidate no-op"], stats.pairs.map(r => [r.repetition, seconds(r.baseline), seconds(r.candidate), seconds(r.baseline_noop), seconds(r.candidate_noop)]), "All three recorded repetitions · wall seconds including controller overhead"));
      box.append(choose("Inspect one measured repetition", "analytics-pair", stats.pairs.map(r => [String(r.repetition), "Pair " + r.repetition]), String(pair), v => { pair = Number(v); show(); }));
      const record = read(profile + "-pair-" + pair + ".json"), stage = record.stages.optimized_incremental, original = record.stages.baseline_incremental;
      box.append(facts([["Affected opportunities", number(record.affected_opportunities) + " / " + number(record.total_opportunities)], ["Affected accounts", stage.result.affected_accounts],
        ["Detection + snapshot overhead", seconds(stage.result.detection_and_snapshot_seconds)], ["Candidate sampled process-tree RSS", (stage.sampled_tree_rss_max_bytes / 1e6).toFixed(1) + " MB"],
        ["Original / candidate database size", (record.warehouse_bytes.baseline / 1e6).toFixed(1) + " / " + (record.warehouse_bytes.optimized / 1e6).toFixed(1) + " MB"]]));
      box.append(table(["Model", "Complete corrected rows", "Exact original/candidate", "Exact candidate/full"], record.optimized_full_parity.models.map(m => [m.model, number(m.rows), record.baseline_optimized_parity.models.find(x => x.model === m.model).exact_multiset_equal ? "Equal" : "DIFFERENT", m.exact_multiset_equal ? "Equal" : "DIFFERENT"]), "All 15 model comparisons · recorded complete rowsets"));
      inspect(box, "Inspect model timings and complete stage costs", {original, candidate: stage, independent_full: record.stages.independent_full});
      inspect(box, "Exact comparison method, partitions and export sizes", record.optimized_full_parity);
      inspect(box, "Machine, dependencies, source revision and conditions", protocol);
      box.append(finding("Keep the original default", "The predeclared target required at least 15% median improvement. Both scales regressed despite faster mart_pipeline execution. Exact detection, retained snapshots, quality gates and checkpointing are real costs."),
        el("p", "One Windows host, one DuckDB/dbt thread and a 2GB engine setting. Fresh database files; OS caches were not flushed. RSS is sampled and may double-count shared pages; 2GB is not a process memory cap. Loading and independent comparisons are separately measured, not hidden inside transformation timings. These are not Snowflake performance or commercial savings.", "gtm-boundary"), origin(profile + "-pair-" + pair + ".json", "Open this complete original repetition")); content.append(box);
    } else {
      const box = section("Native Snowflake: a separate historical fixture run."); const n = read("snowflake.json");
      box.append(facts([["Recorded execution", p.native.started_at + " → " + p.native.finished_at], ["Builds", "Initial / corrected incremental / independent full"],
        ["Models and tests per build", "15 models · 30 tests"], ["Archived query IDs", p.native.query_ids], ["Final warehouse state", n.warehouse_final_state]]));
      box.append(finding("Managed-warehouse proof, not a cloud-scale benchmark", "All 15 complete model multisets matched after late correction. Separate consumer identity, raw-read/write/role denials and publication safety were exercised. This historical fixture predates the USD unit correction; it does not validate the current USD-specific models or the local selective candidate."));
      box.append(table(["Consumer operation", "Recorded denial", "SQLSTATE"], n.denied_operations.map(d => [d.operation, String(d.denied), d.sqlstate]), "Separate consumer identity · effective native access tests"));
      inspect(box, "Native model comparisons and late correction", {models: n.model_comparison, correction: n.late_correction});
      inspect(box, "Publication safety and consumer boundary", {publication_safety: n.publication_safety, credential_boundary: n.credential_boundary, run_isolation: n.run_isolation});
      inspect(box, "Exact native build nodes and their query IDs", read("snowflake-corrected_incremental_build.json"));
      inspect(box, "All archived query IDs", n.query_ids); inspect(box, "Consumption reporting boundary", n.consumption);
      box.append(el("p", "No new Snowflake connection is made by this page. Elapsed seconds and query attribution do not establish final billed credits. Native contention acceptance and enterprise-scale warehouse performance remain outside this record.", "gtm-boundary"), origin("snowflake.json", "Open the original native acceptance record")); content.append(box);
    }
  }
  for (const [key, n, title] of stages) { const b = el("button"); b.type = "button"; b.dataset.analyticsStage = key; b.setAttribute("aria-controls", "analytics-detail"); b.append(el("small", n + " · EVIDENCE"), el("strong", title)); b.addEventListener("click", () => { selected = key; show(); }); nav.append(b); }
  root.append(nav, announce, content); show();
  const provenance = el("details"); provenance.append(el("summary", "Provenance · original bytes, execution revisions and derived views"), el("p", up.execution_revision_note));
  for (const a of up.artifacts) { const row = el("div", undefined, "gtm-origin"); row.append(origin(a.file, a.source_path), el("code", a.sha256)); provenance.append(row); } root.append(provenance);
  return root;
}
