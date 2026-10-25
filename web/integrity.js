// Static projections of pinned records only. No operator API or mutation controls.
const stages = [["discrepancy","01","The discrepancy"],["lineage","02","Follow a record"],["delivery","03","Uncertain delivery"],["recovery","04","After reviewed recovery"],["architecture","05","Engineering evidence"]];
let selected="discrepancy";
const usd = cents => new Intl.NumberFormat("en-US",{style:"currency",currency:"USD"}).format(cents/100);
export function integrityMetrics(read,metric) {
  const b=read("projection.json").before;
  return [metric("Billing net invoices",usd(b.billing_cents),"Q1 2026 · synthetic USD"),metric("ERP invoice postings",usd(b.erp_cents),"Same invoice cohort · not recognized revenue"),metric("Allocated cash",usd(b.cash_cents),"Matched settlement allocations"),metric("Period-end ARR",usd(b.arr_cents),"Recurring stock · March 31"),metric("Review Required",usd(b.variance_cents),"Unposted difference remains open")];
}
export function integrityPanel(ui) {
  const {el,section,json:read,facts,finding}=ui,p=read("projection.json"),life=read("lifecycle.json"),delivery=read("delivery.json"),up=read("upstream.json");
  const root=el("div",undefined,"integrity-investigation");
  const raw=value=>{const n=ui.raw(value);n.tabIndex=0;return n;};
  const inspect=(parent,title,value)=>{const d=el("details");d.append(el("summary",title),raw(value));parent.append(d);};
  const origin=(file,label)=>{const a=el("a",label+" ↗");a.href=up.artifacts.find(x=>x.file===file).source_url;return a;};
  const hero=el("div",undefined,"release-hero");hero.append(el("div","RECORDED ORDER-TO-CASH CONTROL · SYNTHETIC USD","release-kicker"),el("h3","Which number should Finance trust?"),el("p","Sales commits the contract. Billing issues an invoice. Finance posts it. Cash arrives on its own schedule. Follow the records, keep the difference visible, and inspect a separately reviewed delivery recovery."));root.append(hero);
  root.append(el("p","Read-only evidence explorer. Every selection opens recorded history; it never approves, retries, posts or contacts a business system.","gtm-boundary"));
  const nav=el("nav",undefined,"release-stages integrity-stages");nav.setAttribute("aria-label","Revenue integrity investigation stages");
  const content=el("div",undefined,"release-detail");content.id="integrity-detail";
  const announcement=el("p",undefined,"release-announcement");announcement.setAttribute("role","status");announcement.setAttribute("aria-live","polite");
  function amounts(parent,values) {const grid=el("div",undefined,"integrity-amounts");for(const [key,label,note] of [["billing_cents","Billing net invoices","Issued Q1 invoice cohort"],["erp_cents","ERP invoice postings","Accounts receivable / deferred revenue"],["cash_cents","Allocated cash","Separate settlement flow"],["arr_cents","Period-end ARR","Recurring stock, not Q1 revenue"]]){const card=el("div");card.append(el("small",label),el("strong",usd(values[key])),el("span",note));grid.append(card);}parent.append(grid);}
  function show(){
    for(const b of nav.querySelectorAll("button"))b.setAttribute("aria-pressed",String(b.dataset.integrityStage===selected));
    content.replaceChildren();announcement.textContent="Viewing recorded evidence: "+stages.find(x=>x[0]===selected)[2];
    if(selected==="discrepancy"){
      const box=section("One invoice basis. Four different measures.");amounts(box,p.before);
      box.append(finding("Review Required · "+usd(p.before.variance_cents),"Billing exceeds the ERP invoice postings. The source-owned $1,500 proration has no matching ERP posting in this period. It remains an open finance review; the viewer does not assume harmless timing."));
      const why=el("div",undefined,"columns");for(const [title,text] of [["Invoice ≠ cash","The $16,500 comes from matched payment allocations. Closed Won and an invoice do not prove collection."],["Invoice ≠ ARR","ARR annualizes active recurring subscriptions at period end. It excludes the one-off credit and proration and reflects the EU cancellation."]]){const a=section(title);a.append(el("p",text));why.append(a);}box.append(why);
      const bridge=section("Read the invoice-level comparison");for(const r of p.lineage){const card=el("article",undefined,"source-card");card.append(el("h4",r.entity+" · "+r.account),facts([["Billing",usd(r.billing_cents)],["ERP",usd(r.erp_cents)],["Cash allocations",usd(r.cash_cents)],["Difference",usd(r.billing_cents-r.erp_cents)]]));bridge.append(card);}box.append(bridge,origin("lifecycle.json","Open the recorded lifecycle comparison"));content.append(box);
    } else if(selected==="lineage"){
      const box=section("Trace an invoice to its authoritative sources"),label=el("label","Choose a recorded invoice");label.htmlFor="integrity-invoice";const choice=el("select");choice.id="integrity-invoice";for(const r of p.lineage){const o=el("option",r.entity+" · "+r.account+" · "+usd(r.billing_cents));o.value=r.invoice_id;choice.append(o);}choice.value=p.lineage.find(r=>r.entity==="US").invoice_id;const chain=el("div",undefined,"integrity-chain");
      function trace(){chain.replaceChildren();const r=p.lineage.find(x=>x.invoice_id===choice.value);for(const [number,title,body] of [
        ["1","Salesforce-contract · commercial authority",r.contract],["2","Control database · canonical identity",r.mappings],
        ["3","Stripe-contract · invoice and adjustments",{invoice:r.invoice,lines:r.invoice_lines,amendments:r.amendments,latest_known_adjustments:r.adjustments}],
        ["4","NetSuite-contract · independent posting",r.postings],["5","Reconciliation · exact invoice grain",{billing_cents:r.billing_cents,erp_cents:r.erp_cents,cash_cents:r.cash_cents,review_required:r.billing_cents!==r.erp_cents}]
      ]){const block=section(number+" · "+title);block.append(raw(body));chain.append(block);}
      const basis=section("Reconstruct the amount");basis.append(facts([["Original invoice lines",usd(r.initial_cents)],["Known contract amendment lines",usd(r.amendment_cents)],["Latest credit / proration net",usd(r.billing_adjustment_cents)],["Billing net invoices",usd(r.billing_cents)]]));inspect(basis,"Inspect matched settlement allocations",r.allocations);chain.append(basis);}
      choice.addEventListener("change",trace);box.append(label,choice,el("p","The scoped mapping connects different system identifiers. These are local contract records, not native Salesforce, Stripe or NetSuite API responses."),chain,origin("lifecycle.json","Inspect the original source snapshot"));trace();content.append(box);
    } else if(selected==="delivery"){
      const box=section("A missing response is not a missing effect.");box.append(finding("Receiver committed before recovery",`${delivery.lost_ack.remote_committed_before_recovery} billing effect already existed when its acknowledgment was lost. The controller recovered by reading its original receipt and business records.`));
      box.append(el("p","This foundation delivery run precedes the lifecycle changes and is separate from the operator recovery capture. Its initial $42,000 invoices are not the later $39,000 comparison."));
      const target=delivery.persisted_state.control.outbox.find(x=>x.destination==="stripe"&&x.entity==="US");const receiver=delivery.persisted_state.stripe;
      box.append(facts([["Durable effect ID",target.effect_id],["Final persisted state",target.status],["Dispatch attempts",target.attempts],["Content hash",target.hash]]));
      inspect(box,"Original durable intent and independently recorded proof",target);
      inspect(box,"Persisted dispatch-start attempts",delivery.persisted_state.control.attempts.filter(a=>a.effect_id===target.effect_id));
      inspect(box,"Receiver request journal · commit and readbacks",receiver.requests.filter(a=>a.effect_id===target.effect_id));
      inspect(box,"Recorded ambiguous identity exception",delivery.persisted_state.control.exceptions);
      inspect(box,"Actual killed-worker recovery",read("process-death.json"));
      box.append(origin("delivery.json","Open original persisted controller and receiver records"));content.append(box);
    } else if(selected==="recovery"){
      const box=section("A delivery recovered. A different variance stayed open.");amounts(box,p.after);
      box.append(finding("Still Review Required · "+usd(p.after.variance_cents),"Recovery added the fourth account’s $6,600 quarterly invoice and matching ERP posting. It did not repair the original $1,500 unposted adjustment. Cash remains $16,500."));
      box.append(el("p","Recorded operator-browser journey · historical observations, not controls you can execute here.","gtm-boundary"));
      const journey=el("ol",undefined,"integrity-journey");for(const [title,detail] of [
        ["Delivery exhausted","Three rejected HTTP dispatches left the exact synthetic intent exhausted."],
        ["First proposal rejected","A separate approver rejected the first proposal; the browser assertion confirms no dispatch."],
        ["Exact retry approved","A new proposal was approved. The worker revalidated source authority and mappings before dispatch."],
        ["Receiver effects verified","Recorded checks establish the fourth billing dispatch, a total cap of six, and independently verified billing and finance effects."],
        ["Financial recheck completed","A durable recheck published $45,600 billing / $44,100 ERP, with $146,400 ARR and the original discrepancy still open."]
      ]){const li=el("li");li.append(el("strong",title),el("p",detail));journey.append(li);}box.append(journey);
      box.append(el("p","Evidence limit: the pin archives the 43 browser assertions, source test and genuine source screenshots, but not complete recovery proposal, decision and per-attempt JSON rows. The exact receipt drilldown in stage 3 belongs to its separately labeled delivery run."));
      inspect(box,"Inspect actual operator-browser assertions",read("operator-browser.json"));inspect(box,"Derived recovery fixture economics and their basis",p.recovery);
      box.append(origin("operator-browser.json","Open archived operator capture"),el("br"));const shot=el("a","Inspect the original recovered-console screenshot ↗");shot.href=`https://github.com/${up.repository}/blob/${up.import_revision}/docs/evidence/operator-console/run02/console-recovered.png`;box.append(shot);content.append(box);
    } else {
      const box=section("Control the effect. Reconcile the meaning.");const grid=el("div",undefined,"columns");for(const [title,text] of [
        ["Three HTTP services · four databases","CRM, billing and ERP each own independent persisted records; a fourth PostgreSQL database owns identity and execution state."],
        ["Durable authority and delivery","Versioned source records, canonical mappings, inbox/outbox, exact-content effect IDs, bounded attempts and independent receiver readback."],
        ["Separate people, bounded recovery","Authenticated operator and approver identities; database scope enforcement, immutable approvals and current-authority checks before new dispatch."],
        ["Six dbt models · independent money checks","Invoice and business-month grains, retained corrections, separate cash/ARR, 23 data tests and incremental/full-build parity for the recorded suite."]
      ]){const card=section(title);card.append(el("p",text));grid.append(card);}box.append(grid);
      box.append(facts([["Recorded source software tests",read("software.json").test_count],["Recorded browser assertions",read("operator-browser.json").cases.length],["Local analytical execution","DuckDB/dbt + translated PostgreSQL SELECTs"],["Native Snowflake execution","Not performed"],["Source release","Pinned unmerged PR · finite acceptance, not certification"]]));
      inspect(box,"Historical repair with zero remote POSTs",read("history-rehydration.json"));inspect(box,"Killed financial publisher result",read("publication-process-death.json"));inspect(box,"Recorded dbt and portability comparisons",{incremental:life.incremental,full:life.independent_full,portability:life.portability});
      box.append(el("p","The pinned implementation has a documented check-to-commit revocation race and shares a single local PostgreSQL host. These records establish this scenario, not production HA, universal exactly-once delivery or general financial correctness."));content.append(box);
    }
  }
  for(const [key,n,title] of stages){const b=el("button");b.type="button";b.dataset.integrityStage=key;b.setAttribute("aria-controls","integrity-detail");b.append(el("small",n+" · RECORDED"),el("strong",title));b.addEventListener("click",()=>{selected=key;show();});nav.append(b);}root.append(nav,announcement,content);show();
  const origins=el("details");origins.append(el("summary","Pinned provenance · original bytes and derived display data"),el("p",up.execution_revision_note),el("p",p.derivation));for(const a of up.artifacts){const line=el("div",undefined,"gtm-origin");line.append(origin(a.file,a.source_path),el("code",a.sha256));origins.append(line);}root.append(origins);return root;
}
