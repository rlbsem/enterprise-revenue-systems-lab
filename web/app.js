const $ = (s) => document.querySelector(s);
const titles = {
  seller: [
    "01 · APPLIED AI",
    "Can this AI seller\naction be trusted?",
    "A valid quotation does not make every sentence safe. Inspect the original evidence, model response, human decision and observed effect.",
    "A proposal is not authority.",
    "Source support, approval and delivery are separate questions.",
  ],
  control: [
    "02 · EXECUTION GOVERNANCE",
    "What happens when\nexecution becomes uncertain?",
    "A timeout cannot tell you whether a write committed. Follow the durable intent, receiver observation and reconciliation.",
    "Uncertainty needs reconciliation.",
    "Retries must preserve authority and prevent duplicate effects.",
  ],
  connected: [
    "04 · CONNECTED ENTERPRISE SYSTEMS",
    "Can a CRM action\nsurvive uncertain delivery?",
    "Follow a real synthetic Salesforce review through a Snowflake decision, a lost acknowledgment, independent readback and feedback.",
    "An acknowledgment is not the effect.",
    "One CRM record. A changed warehouse decision. No duplicate write.",
  ],
  revenue: [
    "03 · REVENUE INTEGRITY",
    "Why do commercial\nnumbers disagree?",
    "ARR is an installed-base measure. Bookings, invoicing and cash are quarterly flows. Inspect their dates, grains and variance bridge.",
    "Different measures. Different clocks.",
    "Installed ARR ≠ quarterly bookings ≠ quarterly invoicing ≠ quarterly cash.",
  ],
};
const names = {
  seller: "SELLER AUTHORITY",
  control: "EXECUTION RECOVERY",
  revenue: "COMMERCIAL INTEGRITY",
  connected: "CRM AND WAREHOUSE",
};
let catalog,
  entry,
  manifest,
  artifacts,
  view = "decision",
  selectedRun = 0,
  step = null,
  localConfig = null,
  freshResult = null,
  loadSequence = 0;
const el = (tag, text, cls) => {
  const n = document.createElement(tag);
  if (text !== undefined) n.textContent = String(text);
  if (cls) n.className = cls;
  return n;
};
const section = (title) => {
  const n = el("section");
  n.append(el("div", title, "panel-title"));
  return n;
};
const raw = (value) =>
  el("pre", typeof value === "string" ? value : JSON.stringify(value, null, 2));
const json = (name) => {
  if (!(name in artifacts)) throw Error("Required artifact missing: " + name);
  return JSON.parse(artifacts[name]);
};
const status = (text, error = false) => {
  $("#status").textContent = text;
  $("#status").className = "status" + (error ? " error" : "");
};
const hash = async (text) =>
  Array.from(
    new Uint8Array(
      await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)),
    ),
  )
    .map((x) => x.toString(16).padStart(2, "0"))
    .join("");
const dollarAmount = new Intl.NumberFormat("en-US", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});
const money = (n) => (n < 0 ? "-$" : "$") + dollarAmount.format(Math.abs(n));
function metric(label, value, note) {
  const n = el("div", undefined, "metric");
  n.append(
    el("div", label, "metric-label"),
    el("strong", value),
    el("small", note),
  );
  return n;
}
function facts(rows) {
  const n = el("div", undefined, "facts");
  for (const [label, value] of rows) {
    const p = el("p");
    p.append(el("span", label), el("b", value));
    n.append(p);
  }
  return n;
}
function finding(title, text) {
  const n = el("div", undefined, "finding");
  n.append(el("strong", title), el("p", text));
  return n;
}
function selectRun() {
  return entry.id === "seller-support-review"
    ? {
        snapshot: json("trace.json").input_snapshot,
        proposal: json("trace.json").raw_proposal,
        inference: json("trace.json").inference,
      }
    : json("application.json").runs[selectedRun];
}
function sourcesPanel() {
  const panel = el("div");
  const data =
    entry.investigation === "seller" ? selectRun().snapshot.documents : [];
  if (data.length) {
    for (const d of data) {
      const card = el("article", undefined, "source-card");
      card.append(
        el("h3", d.title),
        el("code", d.id + " · " + d.kind),
        el("p", d.text),
      );
      panel.append(card);
    }
    const claims = selectRun().proposal?.claims || [];
    const q = section("Exact source quotations");
    for (const c of claims) {
      q.append(el("blockquote", c.quote), el("code", c.source));
    }
    panel.append(q);
  }
  const label = el("label", "Inspect an original artifact", "panel-title");
  label.htmlFor = "artifact";
  panel.append(label);
  const choice = el("select", undefined, "artifact-select");
  choice.id = "artifact";
  for (const name of Object.keys(artifacts)) {
    const o = el("option", name);
    o.value = name;
    choice.append(o);
  }
  const output = raw(artifacts[choice.value]);
  choice.addEventListener(
    "change",
    () => (output.textContent = artifacts[choice.value]),
  );
  panel.append(choice, output);
  return panel;
}
function sellerPanel() {
  const p = el("div");
  const run = selectRun();
  if (entry.id === "seller-application") {
    const s = el("select", undefined, "row-select");
    s.setAttribute("aria-label", "Recorded account run");
    json("application.json").runs.forEach((r, i) => {
      const o = el("option", r.snapshot.account + " · " + r.proposal.action);
      o.value = i;
      s.append(o);
    });
    s.value = selectedRun;
    s.addEventListener("change", () => {
      selectedRun = Number(s.value);
      renderPanel();
    });
    p.append(s);
  }
  const cols = el("div", undefined, "columns"),
    left = section("Original saved model response"),
    right = section("Observed authority & effect");
  left.append(el("div", run.proposal?.draft || run.error, "draft"));
  if (run.proposal?.uncertainties?.length)
    left.append(
      el(
        "p",
        "Uncertainties: " + run.proposal.uncertainties.join(" "),
        "quotes",
      ),
    );
  const obs = json("observation.json");
  const actions =
    entry.id === "seller-support-review"
      ? []
      : json("application.json").actions.filter((a) => a.run_id === run.id);
  const action = actions[0];
  right.append(
    facts([
      [
        "Model",
        run.inference?.model ||
          run.configuration?.model ||
          "Recorded Qwen3-14B",
      ],
      ["Selected action", run.proposal?.action || "Unavailable"],
      ["Authority", run.snapshot.decision.stage],
      ["Consent", run.snapshot.decision.consent ? "Allowed" : "Blocked"],
      ["Approval", action ? "Recorded approval" : "No approval"],
      ["Delivery", action?.state || "No observed effect"],
    ]),
  );
  if (action) {
    const payload =
      typeof action.payload === "string"
        ? JSON.parse(action.payload)
        : action.payload;
    left.append(
      el("div", "Recorded reviewer edit", "panel-title"),
      el("div", payload.proposal.draft, "draft"),
    );
    right.append(
      el("div", "Bound delivery receipt", "panel-title"),
      raw(
        typeof action.receipt === "string"
          ? JSON.parse(action.receipt)
          : action.receipt,
      ),
    );
  }
  if (entry.id === "seller-support-review") {
    left.append(
      finding(
        "Review finding · unsupported availability",
        "The customer requested support. The sources do not confirm that staff are available. The original mechanical check passed; this targeted review found a semantic support defect.",
      ),
    );
    const review = el("details");
    review.append(
      el("summary", "Read the preserved source-support review"),
      raw(artifacts["review.md"]),
    );
    left.append(review);
  }
  if (obs.refusal)
    right.append(
      finding(
        "Original engine refused the action",
        obs.refusal + " · receiver rows: " + obs.receiver_rows,
      ),
    );
  cols.append(left, right);
  p.append(cols);
  return p;
}
function connectedPanel() {
  const o = json("observation.json");
  const before = json("source-before.json").body;
  const after = json("source-after.json").body;
  const intent = json("intent.json");
  const p = el("div");
  const cols = el("div", undefined, "columns");
  const left = section("Snowflake decision before CRM delivery");
  left.append(facts([
    ["Account", o.initial_decision.account_key],
    ["Brand and owner", o.initial_decision.brand + " / " + o.initial_decision.owner_key],
    ["Reviewed records", o.initial_decision.reviewed_count],
    ["Pending reviews", o.initial_decision.pending_count],
    ["Recommendation", o.initial_decision.decision_action],
  ]));
  const right = section("Feedback after Salesforce readback");
  right.append(facts([
    ["Prior reviews preserved", before.reviews.length],
    ["Reviews after", after.reviews.length],
    ["Pending reviews after", o.feedback_decision.pending_count],
    ["Next recommendation", o.feedback_decision.decision_action],
    ["Independent exact fields", o.delivery.readback_exact_fields],
  ]));
  cols.append(left, right);
  p.append(cols);
  p.append(finding("Recovery with one real CRM effect",
    "The approved internal review was created once. Its acknowledgment was deliberately lost, the dispatcher recovered the existing record, and a second dispatch did not create another POST."));
  p.append(facts([
    ["Action key (prefix)", intent.id.slice(0, 16) + "…"],
    ["Create requests", o.delivery.post_requests],
    ["Independent effect count", o.delivery.independent_action_count],
    ["Original CRM account", "Unchanged"],
    ["Warehouse cleanup", o.cleanup.warehouse + ", " + o.cleanup.remaining_schemas + " integration schemas"],
  ]));
  p.append(finding("Execution boundary",
    "This is a recorded native Salesforce Developer Edition and Snowflake synthetic review workflow. Approval was owner-authorized synthetic policy, not a salesperson sign-off. No new LLM inference, customer contact or vendor execution occurred in the Lab."));
  return p;
}

function controlPanel() {
  const d = json("observation.json");
  const cols = el("div", undefined, "columns");
  const a = section("Recovery observations"),
    b = section("Independent receiver effects");
  a.append(
    facts(
      Object.entries(d.summary || d)
        .filter(([, v]) => typeof v !== "object")
        .map(([k, v]) => [k.replaceAll("_", " "), v]),
    ),
  );
  b.append(raw(json("receiver.json")));
  a.append(
    finding(
      "Execution boundary",
      "The receiver is synthetic. Its ledger is observed separately from worker state; a timeout alone is not evidence of a failed write.",
    ),
  );
  cols.append(a, b);
  return cols;
}
function revenuePanel() {
  const d = json("observation.json");
  const p = el("div");
  const bridge = el("div", undefined, "bridge");
  for (const [label, key] of [
    ["Installed ARR", "period_end_arr"],
    ["Q1 bookings", "net_bookings"],
    ["Q1 invoiced", "net_invoiced"],
    ["Q1 cash", "cash_received"],
  ]) {
    const c = el("div");
    c.append(
      el("small", label),
      el("strong", money(d.measures[key])),
      el(
        "small",
        key === "period_end_arr" ? "Stock at March 31" : "Quarterly flow",
      ),
    );
    bridge.append(c);
  }
  p.append(bridge);
  p.append(
    finding(
      "Economic boundary",
      "ARR is annualized recurring contract value at period end. Booking events, invoices and allocated payments each have a different recognition date and grain.",
    ),
  );
  const t = el("table");
  const head = el("tr");
  for (const s of ["Reconciliation", "Observed value"])
    head.append(el("th", s));
  t.append(head);
  for (const [k, v] of Object.entries(d.bridge || {})) {
    const r = el("tr");
    r.append(
      el("td", k.replaceAll("_", " ")),
      el("td", typeof v === "number" ? money(v) : v),
    );
    t.append(r);
  }
  p.append(t);
  p.append(
    finding(
      "Collection boundary",
      "Cash includes collections on opening invoices. The invoice–cash flow difference is not an accounts-receivable balance.",
    ),
  );
  const accounts = json("models.json").full.bridge;
  const accountPanel = section("Selected account variance bridge");
  accountPanel.id = "account-bridge";
  const accountChoice = el("select", undefined, "row-select");
  accountChoice.setAttribute("aria-label", "Selected revenue account");
  for (const account of accounts) {
    const option = el(
      "option",
      account.account_name + " · " + account.account_id,
    );
    option.value = account.account_id;
    accountChoice.append(option);
  }
  const accountOutput = el("div");
  function showAccount() {
    const account = accounts.find((a) => a.account_id === accountChoice.value);
    accountOutput.replaceChildren(
      facts([
        ["Q1 bookings", money(account.bookings)],
        ["Q1 invoiced", money(account.invoiced)],
        ["Q1 allocated cash", money(account.cash)],
        ["Bookings less invoices", money(account.bookings_less_invoices)],
        ["Invoices less cash", money(account.invoices_less_cash)],
      ]),
      el("p", account.explanation, "quotes"),
    );
    const selected = json("source-records.json");
    const detail = el("details");
    detail.append(
      el("summary", "Inspect this account's original source rows"),
      raw(
        Object.fromEntries(
          Object.entries(selected).map(([name, rows]) => [
            name,
            rows.filter((row) => row.account_id === account.account_id),
          ]),
        ),
      ),
    );
    accountOutput.append(detail);
  }
  accountChoice.addEventListener("change", showAccount);
  accountPanel.append(accountChoice, accountOutput);
  showAccount();
  p.append(accountPanel);
  if (d.equivalence)
    p.append(finding("Incremental versus full build", d.equivalence));
  return p;
}
function timelinePanel() {
  let events = [];
  if (entry.investigation === "seller") {
    if (entry.id === "seller-support-review")
      events = [
        {
          action: "Original source snapshot",
          body: json("trace.json").input_snapshot,
        },
        {
          action: "Actual saved inference",
          body: json("trace.json").inference,
        },
        { action: "Mechanical rubric passed", body: json("trace.json").score },
        {
          action: "Targeted review found unsupported availability",
          body: artifacts["review.md"],
        },
      ];
    else
      events = [...json("application.json").audit]
        .reverse()
        .map((a) => ({ action: a.action, body: a.body, occurred: a.occurred }));
  } else events = json("timeline.json");
  const p = el("div");
  const list = el("ol", undefined, "timeline");
  events.forEach((a, i) => {
    const li = el("li");
    li.append(el("span", i + 1));
    const body = el("div");
    body.append(
      el("b", a.action),
      el(
        "small",
        a.occurred
          ? new Date(a.occurred * 1000).toISOString()
          : a.detail || "Recorded artifact observation",
      ),
    );
    const btn = el("button", "Inspect this event →");
    btn.addEventListener("click", () => {
      step = i;
      renderPanel();
    });
    body.append(btn);
    if (step === i) body.append(raw(a.body || a));
    li.append(body);
    list.append(li);
  });
  p.append(list);
  return p;
}
function comparePanel() {
  const p = el("div");
  if (entry.id === "seller-support-review") {
    const grid = el("div", undefined, "comparison");
    for (const [name, file] of [
      ["Grounded workflow", "trace.json"],
      ["Simple LLM", "simple.json"],
      ["Template baseline", "template.json"],
    ]) {
      const d = json(file),
        s = el("section");
      s.append(
        el("h3", name),
        el("div", d.raw_proposal.draft, "draft"),
        el("p", "Recorded mechanical success: " + d.score.success),
      );
      grid.append(s);
    }
    p.append(
      grid,
      finding(
        "Comparison scope",
        "Same synthetic case, recorded seed 42. These outcomes do not measure salesperson usefulness. The template is deterministic software, not model inference.",
      ),
    );
  }
  const v = section("Standalone verifier result at packaging");
  v.append(raw(json("verification.json")));
  p.append(v);
  p.append(
    el(
      "p",
      "Browser integrity validation checks the catalog-pinned manifest and original artifact bytes. The Python verifier also checks selected underlying domain relationships. Neither proves all prose is supported or that a system was adopted in production.",
      "quotes",
    ),
  );
  return p;
}
function renderPanel() {
  const panel =
    view === "sources"
      ? sourcesPanel()
      : view === "timeline"
        ? timelinePanel()
        : view === "compare"
          ? comparePanel()
          : entry.investigation === "seller"
            ? sellerPanel()
            : entry.investigation === "control"
              ? controlPanel()
              : entry.investigation === "connected"
                ? connectedPanel()
                : revenuePanel();
  $("#panel").replaceChildren(panel);
}
function render() {
  const m = manifest;
  $("#case-title").textContent = entry.title;
  $("#case-summary").textContent = entry.summary;
  $("#mode").textContent = freshResult
    ? "FRESH LOCAL EXECUTION"
    : m.mode === "recorded"
      ? "RECORDED RUN"
      : "RECORDED ENGINE RUN";
  $(".recording-badge").textContent = freshResult
    ? "FRESH LOCAL EXECUTION"
    : "RECORDED EVIDENCE";
  $("#commit").textContent = m.source.commit;
  const link = $("#source-link");
  link.href =
    "https://github.com/" + m.source.repository + "/tree/" + m.source.commit;
  link.textContent = m.source.repository + " ↗";
  $("#limitations").textContent = m.limitations.join(" ");
  $("#commands").textContent =
    m.reproduce.join("\n") +
    "\npython -m revenue_lab.cli verify <bundle-directory>";
  $("#download").href = "evidence/" + entry.id + "/reproduction.zip";
  $("#portable").href = "evidence/" + entry.id + "/portable.json";
  $("#fresh").hidden = !(
    localConfig?.execution_enabled && localConfig.allowed.includes(entry.id)
  );
  $("#fresh-status").textContent = localConfig?.fresh_inference || "";
  $("#local-note").textContent = entry.investigation === "connected"
    ? "The original native run is archived in Customer Signal & Activation. This case supports offline evidence verification only; no Salesforce or Snowflake calls are made."
    : "Run commands from the Lab checkout. No external CRM writes or paid services are required.";
  const metrics = $("#metrics");
  if (entry.investigation === "seller") {
    const obs = json("observation.json");
    metrics.replaceChildren(
      metric("Inference", "Qwen3-14B", "Actual saved model outputs"),
      metric(
        "Evidence",
        entry.id === "seller-support-review"
          ? json("trace.json").raw_proposal.claims.length
          : selectRun().proposal.claims.length,
        "Exact citations in selected run",
      ),
      metric(
        "Effect",
        entry.id === "seller-support-review"
          ? "Not executed"
          : (obs.receiver_rows ?? obs.actions),
        "Synthetic receiver / recorded actions",
      ),
      metric("Usefulness", "Pending", "Independent human assessment"),
    );
  } else if (entry.investigation === "connected") {
    const d = json("observation.json");
    metrics.replaceChildren(
      metric("Salesforce POSTs", d.delivery.post_requests, "One approved synthetic review"),
      metric("Independent effects", d.delivery.independent_action_count, "Exact native readback"),
      metric("Snowflake decision", d.feedback_decision.decision_action.toUpperCase(), "Was clarify_need"),
      metric("Native SQL queries", d.native_counts.distinct_snowflake_query_ids, "Recorded across stages"),
    );
  } else if (entry.investigation === "control") {
    const d = json("observation.json").summary;
    metrics.replaceChildren(
      metric("Delivery attempts", d.attempts, "Observed worker attempts"),
      metric("Unique effects", d.unique_effects, "Independent receiver ledger"),
      metric(
        "Duplicate effects",
        d.duplicate_effects,
        "Observed in this workload",
      ),
      metric(
        "Lost acknowledgments",
        d.lost_acknowledgments,
        "Reconciled after commit",
      ),
    );
  } else {
    const d = json("observation.json").measures;
    metrics.replaceChildren(
      ...[
        ["Installed ARR", "period_end_arr"],
        ["Q1 bookings", "net_bookings"],
        ["Q1 invoiced", "net_invoiced"],
        ["Q1 cash", "cash_received"],
      ].map(([l, k]) =>
        metric(
          l,
          "$" + (d[k] / 1e6).toFixed(2) + "M",
          k === "period_end_arr" ? "Period-end stock" : "Quarterly flow",
        ),
      ),
    );
  }
  renderPanel();
  status(
    "Recorded evidence loaded · " +
      m.artifacts.length +
      " original artifacts · integrity not yet checked in this browser.",
  );
}
async function load(id) {
  const sequence = ++loadSequence;
  const next = catalog.scenarios.find((x) => x.id === id);
  const p = await fetch("evidence/" + id + "/portable.json").then((r) => {
    if (!r.ok) throw Error("Evidence unavailable");
    return r.json();
  });
  const verificationText = await fetch(
    "evidence/" + id + "/verification.json",
  ).then((r) => r.text());
  if ((await hash(verificationText)) !== next.verification_sha256)
    throw Error("Verification record integrity mismatch");
  const verification = JSON.parse(verificationText);
  if (sequence !== loadSequence) return;
  freshResult = null;
  entry = next;
  selectedRun = 0;
  step = null;
  manifest = p.manifest;
  artifacts = p.artifacts;
  artifacts["verification.json"] = JSON.stringify(verification, null, 2);
  if (id === "seller-application") {
    const a = json("application.json");
    selectedRun = Math.max(
      0,
      a.runs.findIndex((r) => r.id === a.actions[0]?.run_id),
    );
  }
  $("#download").textContent = "Download reproduction ZIP ↓";
  $("#download").download = "reproduction.zip";
  render();
}
async function investigate(key) {
  const t = titles[key];
  $("#crumb").textContent = names[key];
  $("#eyebrow").textContent = "INVESTIGATION " + t[0];
  $("#question").innerText = t[1];
  $("#intro-copy").textContent = t[2];
  $("#principle").textContent = t[3];
  $("#principle-copy").textContent = t[4];
  document
    .querySelectorAll("[data-investigation]")
    .forEach((b) =>
      b.classList.toggle("active", b.dataset.investigation === key),
    );
  const select = $("#scenario");
  select.replaceChildren();
  for (const e of catalog.scenarios.filter((x) => x.investigation === key)) {
    const o = el("option", e.title);
    o.value = e.id;
    select.append(o);
  }
  if (select.options.length) await load(select.value);
  else {
    $("#panel").replaceChildren(
      el("div", "This investigation has no verified bundle yet.", "empty"),
    );
    status("Integration pending");
  }
}
async function validate() {
  try {
    const rawManifest = freshResult
      ? freshResult.manifest_text
      : await fetch("evidence/" + entry.id + "/bundle.json").then((r) =>
          r.text(),
        );
    if (
      (await hash(rawManifest)) !==
      (freshResult?.manifest_sha256 || entry.manifest_sha256)
    )
      throw Error("Catalog manifest mismatch");
    const pinned = JSON.parse(rawManifest);
    if (JSON.stringify(pinned) !== JSON.stringify(manifest))
      throw Error("Imported manifest differs from pinned evidence");
    if (
      manifest.schema_version !== "1.0" ||
      manifest.source.commit !== entry.source.commit
    )
      throw Error("Version or source mismatch");
    const paths = new Set();
    for (const a of manifest.artifacts) {
      if (paths.has(a.path) || !Object.hasOwn(artifacts, a.path))
        throw Error("Duplicate or missing artifact");
      paths.add(a.path);
      const data = artifacts[a.path];
      if (
        new TextEncoder().encode(data).length !== a.bytes ||
        (await hash(data)) !== a.sha256
      )
        throw Error("Artifact integrity mismatch: " + a.path);
    }
    status(
      "Artifact integrity verified · " +
        paths.size +
        " files match the " +
        (freshResult ? "local execution" : "catalog-pinned") +
        " manifest. Domain checks: see Compare & verify.",
    );
  } catch (e) {
    status("Verification refused · " + e.message, true);
  }
}
$("#fresh").addEventListener("click", async () => {
  const button = $("#fresh");
  const runScenario = entry.id;
  button.disabled = true;
  $("#fresh-status").textContent =
    "Executing original engine in an isolated local workspace…";
  try {
    const response = await fetch("api/runs", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Lab-Token": localConfig.token,
      },
      body: JSON.stringify({ scenario: runScenario }),
    });
    const created = await response.json();
    if (!response.ok) throw Error(created.error);
    let result;
    for (let i = 0; i < 940; i++) {
      result = await fetch("api/runs/" + created.id).then((r) => r.json());
      if (result.state !== "running") break;
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
    if (result.state !== "succeeded")
      throw Error(
        result.error || "Execution did not finish within the bounded window",
      );
    if (entry.id !== runScenario)
      throw Error(
        "Execution completed for a previous case; its evidence remains available in local state.",
      );
    freshResult = result;
    manifest = result.manifest;
    artifacts = result.artifacts;
    artifacts["verification.json"] = JSON.stringify(
      result.verification,
      null,
      2,
    );
    render();
    const blob = new Blob([JSON.stringify({ manifest, artifacts }, null, 2)], {
      type: "application/json",
    });
    $("#portable").href = URL.createObjectURL(blob);
    $("#download").href = $("#portable").href;
    $("#download").textContent = "Download fresh portable JSON ↓";
    $("#download").download = "fresh-" + entry.id + ".json";
    $("#fresh-status").textContent =
      "Original engine executed successfully. This result is fresh local execution; inspect its runtime and observed effects.";
    await validate();
  } catch (e) {
    $("#fresh-status").textContent =
      "Execution unavailable or failed · " + e.message;
  } finally {
    button.disabled = false;
  }
});
document
  .querySelectorAll("[data-investigation]")
  .forEach((b) =>
    b.addEventListener("click", () =>
      investigate(b.dataset.investigation).catch((e) =>
        status(e.message, true),
      ),
    ),
  );
$("#scenario").addEventListener("change", (e) =>
  load(e.target.value).catch((e) => status(e.message, true)),
);
$("#validate").addEventListener("click", validate);
document.querySelectorAll("[data-view]").forEach((b) =>
  b.addEventListener("click", () => {
    view = b.dataset.view;
    document
      .querySelectorAll("[data-view]")
      .forEach(
        (t) => (
          t.setAttribute("aria-selected", t === b),
          (t.tabIndex = t === b ? 0 : -1)
        ),
      );
    renderPanel();
  }),
);
$("#import").addEventListener("change", async (e) => {
  try {
    if (e.target.files[0].size > 15000000)
      throw Error("Bundle exceeds 15MB limit");
    const p = JSON.parse(await e.target.files[0].text());
    const known = catalog.scenarios.find((s) => s.id === p.manifest.scenario);
    if (!known) throw Error("Unknown scenario");
    await investigate(known.investigation);
    $("#scenario").value = known.id;
    await load(known.id);
    manifest = p.manifest;
    artifacts = p.artifacts;
    artifacts["verification.json"] = JSON.stringify({
      status: "Imported; use standalone verifier for domain checks",
    });
    await validate();
  } catch (error) {
    status("Import refused · " + error.message, true);
  }
});
try {
  try {
    const c = await fetch("api/config");
    if (c.ok) localConfig = await c.json();
  } catch {}
  catalog = await fetch("catalog.json").then((r) => r.json());
  const desired = new URLSearchParams(location.search).get("case");
  const found = catalog.scenarios.find((e) => e.id === desired);
  await investigate(found?.investigation || "seller");
  if (found) {
    $("#scenario").value = found.id;
    await load(found.id);
  }
} catch (e) {
  status("Evidence loading failed · " + e.message, true);
}

const tabButtons = Array.from(document.querySelectorAll("[data-view]"));
tabButtons.forEach((button, index) => {
  button.id = "view-" + button.dataset.view;
  button.setAttribute("aria-controls", "panel");
  button.tabIndex = button.getAttribute("aria-selected") === "true" ? 0 : -1;
  button.addEventListener("keydown", (event) => {
    const target =
      event.key === "ArrowRight"
        ? (index + 1) % tabButtons.length
        : event.key === "ArrowLeft"
          ? (index + tabButtons.length - 1) % tabButtons.length
          : event.key === "Home"
            ? 0
            : event.key === "End"
              ? tabButtons.length - 1
              : null;
    if (target !== null) {
      event.preventDefault();
      tabButtons[target].focus();
      tabButtons[target].click();
    }
  });
  button.addEventListener("click", () =>
    $("#panel").setAttribute("aria-labelledby", button.id),
  );
});
$("#panel").setAttribute("aria-labelledby", "view-decision");
