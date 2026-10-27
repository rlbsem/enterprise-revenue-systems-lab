// A read-only interpretation of original records. No source engine or service executes here.
const remembered = {};
const stages = {
  estate: [
    ["impact", "Retirement impact"],
    ["review", "Change decisions"],
    ["evidence", "Evidence & uncertainty"],
    ["proof", "Correctness & recovery"],
  ],
  reliability: [
    ["publication", "Trusted reporting"],
    ["candidates", "Rejected publications"],
    ["sources", "Sources & checkpoints"],
    ["recovery", "Recovery evidence"],
  ],
  temporal: [
    ["time", "Two clocks"],
    ["permissions", "Permission boundaries"],
    ["delivery", "Delivery & recovery"],
    ["destination", "Destination assurance"],
  ],
};
const descriptions = {
  estate: [
    "Consolidate with evidence.",
    "A platform can look redundant while carrying a critical business dependency. Follow a recorded retirement, compare replacement revisions and inspect what kept a change blocked.",
  ],
  reliability: [
    "A delivered feed is not a trusted report.",
    "Late or incomplete inputs can produce plausible numbers. Follow source bytes and checkpoints to the report, then inspect a rejected candidate with the right row count and the wrong value.",
  ],
  temporal: [
    "Yesterday's answer. Today's permission.",
    "Late information can correct an earlier audience without rewriting the original decision. Follow that distinction through approval, uncertain delivery and independently stored destination effects.",
  ],
};
const utc = (value) =>
  new Date(value * 1000).toISOString().replace(".000Z", " UTC");
const amount = (n, currency = "USD") =>
  new Intl.NumberFormat("en-US", { style: "currency", currency }).format(
    n / 100,
  );

export function assuranceMetrics(kind, read, metric) {
  const p = read("projection.json");
  if (kind === "estate")
    return [
      metric("Company scopes", p.companies, "Distinct local identities"),
      metric(
        "Business requirements",
        p.requirements,
        "Supported / Unsupported / Unknown",
      ),
      metric(
        "Proposal revisions",
        p.proposal_revisions,
        "Six change classes; retained history",
      ),
      metric(
        "Independent outcomes",
        p.independent_requirement_outcomes,
        "Recorded recursive-oracle comparisons",
      ),
    ];
  if (kind === "reliability")
    return [
      metric(
        "Independent sources",
        p.sources,
        "Synthetic HTTP / separate stores",
      ),
      metric(
        "Reported spend",
        amount(p.totals.cost_cents),
        "Synthetic USD, reconciled from bytes",
      ),
      metric(
        "Observed conversions",
        p.totals.conversions,
        "Separate event grain",
      ),
      metric(
        "Reported CRM value",
        amount(p.totals.revenue_cents),
        "Synthetic closed-won value, not cash",
      ),
    ];
  return [
    metric(
      "Historical decisions",
      p.historical_decisions,
      "Two recorded time coordinates",
    ),
    metric(
      "Current eligibility rows",
      p.eligibility_rows,
      "At the recorded brand clocks",
    ),
    metric(
      "Independent effects",
      p.effects,
      "Historical effects, not current members",
    ),
    metric("Brand scopes", p.brands, "Same local ID is not the same person"),
  ];
}

export function assurancePanel(kind, ui) {
  const { el, facts, finding, json: read } = ui;
  const r = read("record.json"),
    projection = read("projection.json"),
    upstream = read("upstream.json");
  const state = (remembered[kind] ||= {
    stage: stages[kind][0][0],
    company: "atlas",
    platform: "explore:atlas/workbench",
    requirement: "atlas/campaign",
    proposal: "replacement:2",
    fact: "ownership:atlas/workbench",
    source: "website",
    position: "",
    candidate: 9,
    brand: "atlas",
    person: "100",
    publication: "",
    intent: "",
    checkpoint: "receiver_drift",
  });
  const root = el(
    "div",
    undefined,
    "assurance-investigation release-investigation",
  );
  root.dataset.assurance = kind;
  const section = (title) => {
    const n = ui.section(title);
    n.querySelector(".panel-title").replaceWith(el("h3", title, "panel-title"));
    return n;
  };
  const raw = (value) => {
    const n = ui.raw(value);
    n.tabIndex = 0;
    return n;
  };
  function inspect(parent, title, value) {
    const d = el("details");
    d.append(el("summary", title), raw(value));
    parent.append(d);
    return d;
  }
  function badge(value) {
    const good = [
        "SUPPORTED",
        "ACCEPTED",
        "confirmed",
        "published",
        "MATCH",
      ].includes(value),
      bad = [
        "UNSUPPORTED",
        "BLOCKED",
        "REJECTED",
        "exception",
        "DIFFERENCE",
      ].includes(value);
    return el(
      "span",
      value.replaceAll("_", " "),
      "assurance-state " + (good ? "good" : bad ? "bad" : "unknown"),
    );
  }
  function origin(file, label) {
    const a = el("a", label + " ↗");
    a.href = upstream.artifacts.find((a) => a.file === file).source_url;
    return a;
  }
  function choose(label, id, options, current, change) {
    const box = el("div", undefined, "assurance-control"),
      l = el("label", label),
      s = el("select");
    l.htmlFor = id;
    s.id = id;
    for (const [value, text] of options) {
      const o = el("option", text);
      o.value = value;
      s.append(o);
    }
    s.value = String(current);
    s.addEventListener("change", () => change(s.value));
    box.append(l, s);
    return box;
  }
  function table(headers, rows, caption) {
    const wrap = el("div", undefined, "assurance-table");
    wrap.tabIndex = 0;
    wrap.setAttribute("role", "region");
    wrap.setAttribute("aria-label", caption);
    const t = el("table"),
      h = el("thead"),
      tr = el("tr");
    t.append(el("caption", caption));
    for (const name of headers) {
      const th = el("th", name);
      th.scope = "col";
      tr.append(th);
    }
    h.append(tr);
    t.append(h);
    const body = el("tbody");
    for (const row of rows) {
      const tr = el("tr");
      for (const value of row) {
        const td = el("td");
        td.append(value instanceof Node ? value : el("span", String(value)));
        tr.append(td);
      }
      body.append(tr);
    }
    t.append(body);
    wrap.append(t);
    return wrap;
  }
  function button(text, action) {
    const b = el("button", text);
    b.type = "button";
    b.addEventListener("click", action);
    return b;
  }
  const hero = el("div", undefined, "release-hero");
  hero.append(
    el(
      "small",
      "RECORDED LOCAL EXECUTION · SYNTHETIC SOURCES",
      "release-kicker",
    ),
    el("h2", descriptions[kind][0]),
    el("p", descriptions[kind][1]),
  );
  root.append(hero);
  root.append(
    el(
      "p",
      "Original local execution is recorded below. This static explorer makes no new database, vendor or model calls. Captured readiness and permissions are historical observations, not authority to act today.",
      "gtm-boundary",
    ),
  );
  const nav = el("nav", undefined, "release-stages");
  nav.setAttribute("aria-label", kind + " assurance stages");
  const announce = el("p", undefined, "release-announcement");
  announce.setAttribute("role", "status");
  const content = el("div", undefined, "release-detail");
  content.id = "assurance-detail";
  function show() {
    for (const b of nav.querySelectorAll("button"))
      b.setAttribute(
        "aria-pressed",
        String(b.dataset.assuranceStage === state.stage),
      );
    announce.textContent =
      "Inspecting recorded " +
      stages[kind].find((s) => s[0] === state.stage)[1].toLowerCase();
    content.replaceChildren();
    ({ estate: estate, reliability: reliability, temporal: temporal })[kind]();
  }

  function requirementTable(v) {
    return table(
      ["Requirement", "Before", "Recorded after", "Proof"],
      Object.entries(v.assessment.requirements).map(([id, x]) => {
        const d = el("details");
        d.append(el("summary", "Inspect witness"), raw(x.witness));
        return [x.label, badge(x.before), badge(x.state), d];
      }),
      "Recorded before / after requirement outcomes",
    );
  }
  function estate() {
    const snapshot = r.snapshot;
    if (state.stage === "impact") {
      const box = section("What would this retirement interrupt?");
      box.append(
        choose(
          "Operating company",
          "assurance-company",
          Object.entries(r.catalog.companies),
          state.company,
          (value) => {
            state.company = value;
            state.platform = "";
            show();
          },
        ),
      );
      const choices = r.versions.filter(
        (v) =>
          v.id.startsWith("explore:") &&
          v.proposal.systems[0].startsWith(state.company + "/"),
      );
      if (!choices.some((v) => v.id === state.platform))
        state.platform = choices[0]?.id;
      if (!choices.length) {
        box.append(el("p", "No active collected platform in this scope."));
        content.append(box);
        return;
      }
      const v = choices.find((v) => v.id === state.platform);
      box.append(
        choose(
          "Platform to inspect",
          "assurance-platform",
          choices.map((v) => [
            v.id,
            v.proposal.title.replace("Retirement impact: ", ""),
          ]),
          state.platform,
          (value) => {
            state.platform = value;
            show();
          },
        ),
      );
      box.append(
        facts([
          [
            "Unsupported after retirement",
            v.assessment.failed_requirements.length,
          ],
          [
            "Unknown after retirement",
            v.assessment.unknown_requirements.length,
          ],
          ["Recorded company scope", v.proposal.companies.join(" / ")],
          ["Authoritative snapshot", snapshot.id.slice(0, 16) + "…"],
        ]),
      );
      const requirements = Object.entries(v.assessment.requirements);
      if (!requirements.some(([id]) => id === state.requirement))
        state.requirement = requirements[0][0];
      box.append(
        choose(
          "Follow a business requirement",
          "assurance-requirement",
          requirements.map(([id, x]) => [id, x.label]),
          state.requirement,
          (value) => {
            state.requirement = value;
            show();
          },
        ),
      );
      const q = v.assessment.requirements[state.requirement],
        graph = el("div", undefined, "assurance-flow");
      const inputs = section("Declared inputs"),
        outcome = section(q.label),
        downstream = section("Feeds onward");
      const detail = el("div", undefined, "assurance-selected-record");
      detail.setAttribute("role", "status");
      for (const [id, input] of Object.entries(q.inputs)) {
        const target = input.provider,
          card = el("div", undefined, "assurance-node");
        card.append(
          badge(input.state),
          el("p", target || "Unresolved dependency"),
        );
        if (
          target?.startsWith("req:") &&
          v.assessment.requirements[target.slice(4)]
        )
          card.append(
            button("Follow " + target, () => {
              state.requirement = target.slice(4);
              show();
            }),
          );
        card.append(
          button("Inspect input evidence", () => {
            detail.replaceChildren(el("h4", target || id));
            inspect(detail, "Recorded typed input", input);
            const claim = snapshot.facts[id];
            if (claim)
              inspect(
                detail,
                "Original source assertions",
                snapshot.assertions.filter((a) =>
                  claim.evidence.includes(a.id),
                ),
              );
            detail.tabIndex = -1;
            detail.focus();
          }),
        );
        inputs.append(card);
      }
      outcome.append(
        badge(q.state),
        el("p", "Before: " + q.before),
        el("code", state.requirement),
      );
      inspect(outcome, "Recorded witness chain", q.witness);
      const next = Object.entries(v.assessment.requirements).filter(([, x]) =>
        Object.values(x.inputs).some(
          (e) => e.provider === "req:" + state.requirement,
        ),
      );
      for (const [id, x] of next)
        downstream.append(
          button(x.label, () => {
            state.requirement = id;
            show();
          }),
        );
      if (!next.length)
        downstream.append(
          el("p", "No dependent requirement in this recorded scope."),
        );
      graph.append(inputs, outcome, downstream);
      box.append(
        el(
          "p",
          "Follow the typed requirement chain. Connectivity alone does not establish a business dependency.",
          "gtm-boundary",
        ),
        graph,
        detail,
        requirementTable(v),
      );
      content.append(box);
    } else if (state.stage === "review") {
      const box = section(
        "Repairing an interface is not a clean readiness decision.",
      );
      const versions = r.versions.filter((v) => !v.id.startsWith("explore:"));
      const v =
        versions.find((v) => v.id + ":" + v.revision === state.proposal) ||
        versions[0];
      box.append(
        choose(
          "Recorded proposal revision",
          "assurance-proposal",
          versions.map((v) => [
            v.id + ":" + v.revision,
            v.proposal.title + " · revision " + v.revision,
          ]),
          v.id + ":" + v.revision,
          (value) => {
            state.proposal = value;
            show();
          },
        ),
      );
      box.append(
        badge(v.state),
        el("p", "Recorded state at capture; never a present-day approval."),
        facts([
          ["Change class", v.proposal.change_kind],
          ["Company scope", v.proposal.companies.join(" / ")],
          ["Ready at capture", String(v.gates.ready)],
          ["Base evidence clock", snapshot.as_of],
        ]),
      );
      box.append(
        table(
          ["Readiness gate", "Recorded finding"],
          Object.entries(v.gates.checks).map(([k, x]) => [
            k.replaceAll("_", " "),
            badge(x ? "SUPPORTED" : "BLOCKED"),
          ]),
          "All gates must pass before scoped acceptance",
        ),
      );
      inspect(box, "Exact proposed architecture changes", v.proposal.actions);
      inspect(box, "Unresolved owners and omitted scope", v.gates);
      const history = section("Immutable decision history");
      if (!v.decisions.length)
        history.append(el("p", "No decision recorded for this revision."));
      else
        for (const d of v.decisions)
          history.append(
            badge(d.decision === "ACCEPT" ? "ACCEPTED" : "REJECTED"),
            el("p", d.reason),
            el("p", d.principal + " · " + d.recorded_at, "gtm-boundary"),
          );
      history.append(
        el(
          "p",
          "The source engine invalidates acceptance after a new evidence snapshot, a later revision, expiry or revoked reviewer authority. This viewer cannot approve a change.",
        ),
      );
      box.append(
        history,
        requirementTable(v),
        origin("governance.sql", "Inspect native reviewer authorization"),
      );
      content.append(box);
    } else if (state.stage === "evidence") {
      const box = section("Missing evidence must stay visible.");
      const items = Object.entries(snapshot.facts).sort(
        (a, b) =>
          (a[1].state === "UNKNOWN" ? -1 : 0) -
          (b[1].state === "UNKNOWN" ? -1 : 0),
      );
      box.append(
        choose(
          "Source claim group",
          "assurance-fact",
          items.map(([id, x]) => [id, id + " · " + x.state]),
          state.fact,
          (value) => {
            state.fact = value;
            show();
          },
        ),
      );
      const fact = snapshot.facts[state.fact];
      box.append(badge(fact.state));
      for (const assertion of snapshot.assertions.filter((a) =>
        fact.evidence.includes(a.id),
      )) {
        const card = section(assertion.source + " · " + assertion.location);
        card.append(
          facts([
            ["Collected", assertion.collected_at],
            ["Disposition", fact.dispositions[assertion.id]],
            ["Collection status", assertion.collection_status],
          ]),
        );
        inspect(card, "Exact assertion and value", assertion);
        box.append(card);
      }
      box.append(
        finding(
          "No observed annual execution does not mean unused.",
          "The annual adapter is declared but missing from collected inventory. October's partial observation window and the disputed Atlas owner remain in the source evidence.",
        ),
      );
      inspect(
        box,
        "Collection coverage and seasonal exclusions",
        snapshot.manifests,
      );
      inspect(box, "Source authority by assertion type", snapshot.policy);
      box.append(
        origin("catalog-source.json", "Open scoped source catalog"),
        origin("owner-source.json", "Open original owner attestations"),
      );
      content.append(box);
    } else {
      const box = section("Challenge the decision, not just the diagram.");
      const report = read("regression.json"),
        comparison = read("comparison.json");
      box.append(
        facts([
          ["Original tests", report.suites.tests.tests],
          ["Additional native tests", report.suites.change_tests.tests],
          [
            "Independent requirement outcomes",
            comparison.requirements_compared,
          ],
          ["Original files preserved", report.original_files_unchanged],
        ]),
      );
      box.append(
        el(
          "p",
          "The source ran PostgreSQL permission tests, concurrent revisions and actual child-process death before publication commit. Its separate recursive evaluator compared all recorded target requirement states. The Lab checks those records; it does not execute PostgreSQL or repeat the graph experiment.",
        ),
      );
      inspect(box, "Exact independent graph comparisons", comparison);
      inspect(box, "Named native regression cases", report.suites);
      box.append(
        origin("regression.json", "Open executed verification"),
        origin(
          "governance-source.py",
          "Inspect transactional publication and stale-review gates",
        ),
      );
      content.append(box);
    }
  }

  function reportTable(rows, caption) {
    return table(
      ["Day", "Campaign", "Spend", "Conversions", "Reported CRM value"],
      rows.map((x) => [
        x[0],
        x[2],
        amount(x[3], r.currency),
        x[6],
        amount(x[7], r.currency),
      ]),
      caption,
    );
  }
  function reliability() {
    const s = r.snapshot,
      w = s.warehouse;
    if (state.stage === "publication") {
      const box = section(
        "Which published values can be traced to source bytes?",
      );
      box.append(
        facts([
          ["Published run", w.active_run],
          ["Reporting grain", "campaign / day"],
          ["Admitted source versions", w.admitted_versions],
          ["Latest records incl. tombstones", projection.latest_records],
        ]),
      );
      box.append(
        reportTable(
          w.published,
          "Final independently reconciled publication · synthetic USD",
        ),
      );
      const final = s.candidates.find((c) => c.run.id === w.active_run);
      inspect(box, "Inspect 19 exact source-line relationships", final.lineage);
      box.append(
        finding(
          "Spend, conversions and CRM value are different measures.",
          "The figures are synthetic. Reported closed-won CRM value is not collected cash, booked revenue or incremental marketing lift.",
        ),
      );
      content.append(box);
    } else if (state.stage === "candidates") {
      const box = section("The row count passed. The value did not.");
      const c = s.candidates.find((c) => c.run.id === Number(state.candidate));
      box.append(
        choose(
          "Recorded reporting candidate",
          "assurance-candidate",
          s.candidates.map((c) => [
            String(c.run.id),
            c.name + " · run " + c.run.id,
          ]),
          state.candidate,
          (value) => {
            state.candidate = Number(value);
            show();
          },
        ),
      );
      const blocked = s.journal.audit
        .filter(
          (a) =>
            a.operation === "publication_blocked" &&
            JSON.parse(a.body).run === c.run.id,
        )
        .map((a) => JSON.parse(a.body));
      box.append(
        badge(c.run.status),
        facts([
          [
            "Actual / expected row count",
            c.table.length + " / " + c.raw_oracle.expected.length,
          ],
          ["Independent value differences", c.raw_oracle.differences.length],
          ["Core quality blockers", c.run.evidence.blockers.length],
          ["Retained failed publication attempts", blocked.length],
        ]),
      );
      box.append(
        reportTable(
          c.table,
          "Actual recorded SQL candidate values; built does not mean published",
        ),
      );
      if (c.raw_oracle.differences.length)
        box.append(
          finding(
            "A wrong value blocks publication.",
            "Independent raw-source reconciliation found " +
              c.raw_oracle.differences.length +
              " difference despite matching row counts. The candidate remains built; the later corrected publication does not erase it.",
          ),
        );
      inspect(
        box,
        "Expected versus actual value differences",
        c.raw_oracle.differences,
      );
      inspect(
        box,
        "Exact publication gate findings",
        blocked.length ? blocked : c.run.evidence,
      );
      inspect(
        box,
        "Source changes contributing to this candidate",
        c.source_variances,
      );
      content.append(box);
    } else if (state.stage === "sources") {
      const box = section(
        "A source checkpoint requires an independently stored acknowledgment.",
      );
      box.append(
        choose(
          "Independently persisted source",
          "assurance-source",
          Object.keys(r.independent_source_receipts).map((k) => [k, k]),
          state.source,
          (value) => {
            state.source = value;
            state.position = "";
            show();
          },
        ),
      );
      const deliveries = s.retained_remote_deliveries.filter(
        (d) => d.service === state.source,
      );
      if (!deliveries.some((d) => String(d.seq) === state.position))
        state.position = String(deliveries[0].seq);
      const d = deliveries.find((d) => String(d.seq) === state.position),
        journal = s.journal.deliveries.find(
          (j) => j.service === d.service && j.seq === d.seq,
        ),
        source = r.independent_source_receipts[state.source],
        ack = source.acknowledgments.find((a) => a.seq === d.seq);
      box.append(
        choose(
          "Recorded delivery position",
          "assurance-delivery",
          deliveries.map((d) => [String(d.seq), d.service + " / " + d.seq]),
          state.position,
          (value) => {
            state.position = value;
            show();
          },
        ),
        facts([
          ["Controller disposition", journal.state],
          [
            "Controller checkpoint",
            s.journal.checkpoints.find((c) => c.service === d.service).seq,
          ],
          ["Source byte hash", d.sha256],
          ["Independent acknowledgment", ack ? "Recorded" : "Unobserved"],
        ]),
      );
      const readback = el("div", undefined, "assurance-selected-record");
      box.append(
        button("Inspect recorded acknowledgment", () => {
          readback.replaceChildren(
            el("h4", "Saved independent readback — no live request"),
          );
          inspect(
            readback,
            "Source acknowledgment",
            ack ? JSON.parse(ack.body) : { state: "UNOBSERVED" },
          );
          inspect(readback, "Controller journal position", journal);
          readback.tabIndex = -1;
          readback.focus();
        }),
        readback,
      );
      const bytes = Uint8Array.from(atob(d.exact_base64), (c) =>
        c.charCodeAt(0),
      );
      inspect(
        box,
        "Exact recorded source bytes · decoded base64",
        new TextDecoder().decode(bytes),
      );
      inspect(box, "Source requests and uncertain outcomes", source.requests);
      inspect(box, "Closed data contracts", ui.text("contracts-source.py"));
      box.append(
        origin(
          "controller-source.py",
          "Inspect checkpoint and recovery implementation",
        ),
      );
      content.append(box);
    } else {
      const box = section("Recovery preserves the last verified report.");
      box.append(
        el(
          "p",
          "Actual source HTTP outages, lost acknowledgments, worker termination and changed source inventories were challenged upstream. A checkpoint accounts for a delivery; it is not approval to publish its contents.",
        ),
      );
      box.append(
        table(
          ["Recorded check", "Observed", "Passed"],
          r.checks
            .filter((c) =>
              /checkpoint|ack|crash|termination|outage|source_change|publication/.test(
                c.check,
              ),
            )
            .map((c) => [
              c.check.replaceAll("_", " "),
              JSON.stringify(c.observed),
              String(c.passed),
            ]),
          "Selected original recovery assertions; full set in download",
        ),
      );
      inspect(
        box,
        "Eight original process-death experiments",
        read("crashes.json"),
      );
      inspect(box, "Durable controller audit", s.journal.audit);
      inspect(box, "All executed scenario assertions", r.checks);
      box.append(origin("record.json", "Open exact original acceptance"));
      content.append(box);
    }
  }

  function temporal() {
    const o = r.snapshot.operating,
      receiver = r.snapshot.receiver;
    const scope = choose(
      "Operating brand",
      "assurance-brand",
      o.brands.map((b) => [b.brand, b.brand]),
      state.brand,
      (value) => {
        state.brand = value;
        state.person = "100";
        state.publication = "";
        state.intent = "";
        show();
      },
    );
    content.append(scope);
    const people = o.subjects.filter((s) => s.brand === state.brand);
    if (["time", "permissions"].includes(state.stage))
      content.append(
        choose(
          "Scoped synthetic person",
          "assurance-person",
          people.map((s) => [s.person, s.brand + " / " + s.person]),
          state.person,
          (value) => {
            state.person = value;
            show();
          },
        ),
      );
    if (state.stage === "time") {
      const box = section(
        "A late event changes history, not what was known then.",
      );
      const pubs = o.publications.filter((p) => p.brand === state.brand);
      if (!pubs.some((p) => p.id === state.publication))
        state.publication =
          pubs.find((p) => p.request === "day3-original")?.id || pubs[0].id;
      const p = pubs.find((p) => p.id === state.publication);
      box.append(
        choose(
          "Recorded publication",
          "assurance-publication",
          pubs.map((p) => [p.id, p.request + " · " + p.mode]),
          state.publication,
          (value) => {
            state.publication = value;
            show();
          },
        ),
        facts([
          ["Business time", utc(p.clock)],
          ["Known through source sequence", p.known],
          ["Publication mode", p.mode],
          ["Brand-local identity", state.brand + " / " + state.person],
        ]),
      );
      const rows = o.decisions.filter(
        (d) => d.publication === p.id && d.person === state.person,
      );
      box.append(
        table(
          ["Audience", "Member", "Covered", "Decision reason"],
          rows.map((d) => [
            d.segment,
            String(d.member),
            String(d.covered),
            d.evidence.reasons[d.segment],
          ]),
          "Recorded person/audience decisions at both time coordinates",
        ),
      );
      const history = r.observations.history,
        old = o.decisions.find(
          (d) =>
            d.publication === history.original &&
            d.brand === state.brand &&
            d.person === state.person &&
            d.segment === "engaged_trial",
        ),
        restated = o.decisions.find(
          (d) =>
            d.publication === history.restated &&
            d.brand === state.brand &&
            d.person === state.person &&
            d.segment === "engaged_trial",
        );
      if (old && restated)
        box.append(
          facts([
            ["Original day-3 engagement", String(old.member)],
            ["Restated same-business-time engagement", String(restated.member)],
            [
              "New HTTP actions from backfill",
              history.new_http_actions_from_backfill,
            ],
          ]),
        );
      else
        box.append(
          el(
            "p",
            "This brand has no recorded restatement pair. It is not merged with the other brand's person 100.",
            "gtm-boundary",
          ),
        );
      inspect(box, "Original and restated records", {
        original: old || null,
        restated: restated || null,
      });
      inspect(
        box,
        "Source batches at the selected knowledge boundary",
        o.inbox.filter((b) => b.brand === state.brand && b.seq <= p.known),
      );
      box.append(origin("temporal-proof.json", "Open original two-time proof"));
      content.append(box);
    } else if (state.stage === "permissions") {
      const box = section("Membership is not permission to contact.");
      const eligible = o.activation_eligibility.filter(
          (e) => e.brand === state.brand && e.person === state.person,
        ),
        grants = o.permissions.filter(
          (g) => g.brand === state.brand && g.person === state.person,
        );
      box.append(
        el(
          "p",
          "The eligibility view evaluates the recorded brand clock, audience membership, coverage, channel, purpose and latest permission. Nothing here grants present-day marketing authority.",
          "gtm-boundary",
        ),
      );
      box.append(
        table(
          ["Audience", "Member", "Coverage", "Recorded authorization"],
          eligible.map((e) => [
            e.segment,
            String(e.member),
            String(e.covered),
            e.reason,
          ]),
          "Actual current-eligibility SQL rows at the recorded clock",
        ),
      );
      box.append(
        table(
          [
            "Revision",
            "Channel / purpose",
            "Allowed",
            "Suppressed",
            "Valid window (UTC)",
          ],
          grants.map((g) => [
            g.revision,
            g.channel + " / " + g.purpose,
            String(g.allowed),
            String(g.suppressed),
            utc(g.valid_from) + " → " + utc(g.expires),
          ]),
          "Scoped permission journal, including wrong-purpose and withdrawal revisions",
        ),
      );
      inspect(box, "Exact permission and current eligibility rows", {
        grants,
        eligibility: eligible,
      });
      box.append(
        origin(
          "permission-source.py",
          "Inspect approval and current-permission gates",
        ),
        origin("operating.sql", "Inspect declared SQL view grains"),
      );
      content.append(box);
    } else if (state.stage === "delivery") {
      const box = section("A lost acknowledgment is not a failed effect.");
      const intents = o.intents.filter((i) => i.brand === state.brand),
        lost = receiver.requests.find(
          (q) => q.brand === state.brand && q.result === "committed_ack_lost",
        );
      if (!intents.some((i) => i.id === state.intent))
        state.intent = lost?.effect || intents[0]?.id;
      if (!state.intent) {
        box.append(el("p", "No activation intent recorded for this brand."));
        content.append(box);
        return;
      }
      const i = intents.find((i) => i.id === state.intent),
        effect = receiver.effects.find((e) => e.id === i.id),
        record = receiver.records.find((x) => x.id === i.id);
      box.append(
        choose(
          "Recorded activation intent",
          "assurance-intent",
          intents.map((i) => [
            i.id,
            i.person +
              " / " +
              i.segment +
              " / " +
              (i.desired ? "add" : "remove") +
              " / " +
              i.seq,
          ]),
          state.intent,
          (value) => {
            state.intent = value;
            show();
          },
        ),
        badge(i.state),
        facts([
          ["Scoped person", i.brand + " / " + i.person],
          ["Reserved POST attempts", i.attempts],
          ["Independent read checks", i.checks],
          ["Independent effect present", effect ? "Recorded" : "Unobserved"],
        ]),
      );
      inspect(box, "Frozen, exactly approved intent", i);
      const detail = el("div", undefined, "assurance-selected-record");
      box.append(
        button("Inspect independent receipt and business record", () => {
          detail.replaceChildren(
            el(
              "h4",
              "Recorded independent destination evidence — no live call",
            ),
          );
          inspect(detail, "Exact receipt and independently stored record", {
            effect: effect || null,
            business_record: record || null,
            sender_receipt: i.receipt || null,
          });
          detail.tabIndex = -1;
          detail.focus();
        }),
        detail,
      );
      box.append(
        table(
          ["Recorded receiver request", "Observed time"],
          receiver.requests
            .filter((q) => q.effect === i.id)
            .map((q) => [q.result, q.observed_at]),
          "Actual receiver journal for the selected effect",
        ),
      );
      inspect(
        box,
        "Lost-ack and actual worker-death assertions",
        r.checks.filter((c) =>
          /lost_ack|process_termination|reservation|restart|duplicate/.test(
            c.check,
          ),
        ),
      );
      box.append(
        origin(
          "delivery-source.py",
          "Inspect bounded delivery and reconciliation",
        ),
      );
      content.append(box);
    } else {
      const box = section(
        "Reconcile current authorization, not just old receipts.",
      );
      const eligible = o.activation_eligibility.filter(
          (e) => e.brand === state.brand,
        ),
        membership = receiver.membership.filter((m) => m.brand === state.brand);
      box.append(
        table(
          [
            "Person / audience",
            "Expected at recorded clock",
            "Destination state",
            "Observation",
          ],
          eligible.map((e) => {
            const m = membership.find(
                (m) =>
                  m.person === e.person &&
                  m.segment === e.segment &&
                  m.channel === e.channel &&
                  m.purpose === e.purpose,
              ),
              expected = e.reason === "eligible";
            return [
              e.person + " / " + e.segment,
              String(expected),
              m ? String(m.active) : "Unobserved",
              m
                ? badge(expected === m.active ? "MATCH" : "DIFFERENCE")
                : badge("UNKNOWN"),
            ];
          }),
          "Full scoped person/audience grain; missing destination rows are unobserved, not assumed synchronized",
        ),
      );
      box.append(
        choose(
          "Earlier reconciliation finding",
          "assurance-reconciliation",
          Object.keys(r.observations)
            .filter((k) => k !== "history")
            .map((k) => [k, k.replaceAll("_", " ")]),
          state.checkpoint,
          (value) => {
            state.checkpoint = value;
            show();
          },
        ),
      );
      inspect(
        box,
        "Original before-remediation observation",
        r.observations[state.checkpoint],
      );
      inspect(
        box,
        "Recorded final reconciliation assertions",
        r.checks.filter((c) => c.check.startsWith("reconciliation_restores")),
      );
      inspect(box, "Independent oracle comparisons", r.oracle);
      box.append(
        finding(
          "Historical proof does not become new action authority.",
          "Receipts remain inspectable after permission withdrawal or changed historical qualification. Protective removal and destination reconciliation are separate operations; no message was sent by this viewer.",
        ),
      );
      content.append(box);
    }
  }
  for (const [id, title] of stages[kind]) {
    const b = button(title, () => {
      state.stage = id;
      show();
    });
    b.dataset.assuranceStage = id;
    b.setAttribute("aria-pressed", String(id === state.stage));
    nav.append(b);
  }
  root.append(nav, announce, content);
  show();
  return root;
}
