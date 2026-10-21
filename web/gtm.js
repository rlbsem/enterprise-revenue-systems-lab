// Read-only projections of pinned execution records. No business engine or vendor client.
export function gtmMetrics(id, read, metric) {
  if (id === "gtm-enterprise") {
    const d = read("execution.json"), arms = Object.values(d.measurement.arms);
    return [metric("Synthetic accounts", d.account_records.length, "Full assigned-account denominator"),
      metric("Accepted opportunities", arms.reduce((n,a)=>n+a.accepted_opportunities,0), "CRM outcome events · synthetic ACV"),
      metric("Qualified pipeline", cash(d, arms.reduce((n,a)=>n+a.pipeline_cents,0)), "Synthetic estimates · not revenue"),
      metric("Independent local effects", d.reconciliation.remote_effects, "Local HTTP receiver · not Salesforce")];
  }
  if (id === "gtm-salesforce") {
    const a=read("acceptance.json"), n=read("native-details.json"), c=read("post-cleanup.json");
    return [metric("Native API requests", a.authenticated_requests, "Recorded Developer Edition acceptance"),
      metric("Exact SDR Task effects", a.receipt.task_count, "Independent readback · one receipt"),
      metric("Apex tests", n.apex_deployment.tests_completed, "Recorded native execution"),
      metric("Cleanup readbacks", c.authenticated_requests, "GET only · original grants restored")];
  }
  const a=read("evaluation.json");
  return [metric("Actual model responses", a.records.length, "Recorded Qwen3-14B inference"),
    metric("Exact citation passes", a.exact_citation_checks_passed, "Mechanical check, not semantic usefulness"),
    metric("Preserved failures", a.records.filter(r=>r.validation_error).length, "Rejected citations remain inspectable"),
    metric("CRM authority", "Separate", "Advice cannot authorize a native write")];
}

function cash(d, cents) {
  return d.scenario.currency+" "+new Intl.NumberFormat(d.scenario.locale, {
    style:"currency",currency:d.scenario.currency,maximumFractionDigits:0,
  }).format(cents/100);
}

export function gtmPanel(id, ui) {
  const {el, section, raw, json:read, facts, finding}=ui, p=el("div",undefined,"gtm-investigation");
  p.append(finding("Three executions, three boundaries",
    "The enterprise pipeline, native Salesforce acceptance and Qwen3 evaluation are separate recorded runs. Inspect complementary capabilities; no continuous vendor funnel, prospect communication or commercial uplift is claimed."));
  const lanes=el("nav",undefined,"gtm-lanes"); lanes.setAttribute("aria-label","GTM evidence boundaries");
  for(const [key,label] of [["gtm-enterprise","01 · Enterprise pipeline"],["gtm-salesforce","02 · Native Salesforce"],["gtm-qwen","03 · Qwen3 advice"]]) {
    const a=el("a",label);a.href="?case="+key;if(key===id)a.setAttribute("aria-current","page");lanes.append(a);
  }
  p.append(lanes);
  if(id==="gtm-enterprise") enterprise(p,ui);
  else if(id==="gtm-salesforce") native(p,ui);
  else advice(p,ui);
  const origin=section("Original artifacts · pinned provenance");
  for(const a of read("upstream.json").artifacts) {
    const link=el("a",a.source_path+" ↗");link.href=a.source_url;
    const line=el("div",undefined,"gtm-origin");line.append(link,el("code",a.sha256),el("small","Recorded source revision: "+a.recorded_source_revision));origin.append(line);
  }
  p.append(origin);return p;
}

function enterprise(p,{el,section,raw,json:read,facts,finding}) {
  const d=read("execution.json"), accountBlock=section("Account intelligence → qualification → owned review");
  const label=el("label","Inspect a synthetic enterprise account");label.htmlFor="gtm-account";
  const choice=el("select");choice.id="gtm-account";
  for(const a of d.account_records){const o=el("option",a.name+" · "+a.territory);o.value=a.id;choice.append(o);}
  choice.value=d.financial_audit.opportunities.find(o=>o.arm==="treatment").account_id;
  const details=el("div");
  const render=()=>{
    const a=d.account_records.find(x=>x.id===choice.value);
    const decision=d.qualification_decisions.filter(x=>x.account_id===a.id).at(-1);
    const q=JSON.parse(decision.body), col=el("div",undefined,"columns"), left=section("Identity, fit and intent"),right=section("Authority and action history");
    left.append(facts([["Account",a.name],["Identity",a.domain],["CRM owner",a.owner],["Fit / intent",q.fit+" / "+q.intent],["Eligible at recorded decision",q.eligible?"Yes":"No"],["Policy",q.policy_version]]));
    const action=d.actions.find(x=>x.account_id===a.id), routes=d.routes.filter(x=>x.account_id===a.id);
    right.append(facts([["Local CRM context","Synthetic; not a native Salesforce account"],["Routing",routes.length?routes.map(r=>r.owner+" · "+r.reason).join("; "):"No recorded inbound route"],["Review",action?"Exact content approved by "+action.reviewer:"No approved action recorded"],["Execution",action? action.status+" · "+action.attempts+" attempts":"Not enrolled"],["Block reason",action?.last_error||"None recorded"]]));
    const inspect=el("details");inspect.append(el("summary","Inspect source records and score contributions"),raw({account:a,qualification:q,sources:d.source_records.filter(s=>s.account_id===a.id).map(s=>({...s,payload:JSON.parse(s.payload)}))}));left.append(inspect);
    if(action){const log=el("details");log.append(el("summary","Inspect exact approval, payload and receipt"),raw({action,approval:d.audit.filter(x=>x.event==="exact_approval"&&x.subject===action.action_key)}));right.append(log);}
    col.append(left,right);details.replaceChildren(col);
  };
  choice.addEventListener("change",render);render();accountBlock.append(label,choice,details);p.append(accountBlock);
  const ledger=section("Five synthetic opportunities · original CRM outcome evidence");
  const table=el("table"),cap=el("caption","Illustrative 12-month opportunity ACV · "+d.scenario.currency+" · not revenue, bookings or ARR");
  table.append(cap);const head=el("thead"),hr=el("tr");
  for(const t of ["Account / opportunity","Cohort","Scope","Synthetic ACV"]){const th=el("th",t);th.scope="col";hr.append(th);}head.append(hr);table.append(head);const body=el("tbody");
  for(const o of d.financial_audit.opportunities){const q=d.scenario.scope_quotes.find(x=>x.business_id===o.business_id),r=el("tr");
    const first=el("td");first.append(el("strong",o.account_name),el("small",o.business_id));
    r.append(first,el("td",o.arm),el("td",q.sites+" sites × "+cash(d,q.annual_site_value_cents)),el("td",cash(d,o.amount_cents)));body.append(r);
  }table.append(body);ledger.append(table);
  const original=el("details");original.append(el("summary","Inspect admitted opportunity events and independent audit"),raw({source_events:d.source_records.filter(s=>s.kind==="outcome"&&JSON.parse(s.payload).data.kind==="opportunity_accepted"),audit:d.financial_audit}));ledger.append(original);p.append(ledger);
  const comparison=section("Treatment and holdout · retain the denominator"),grid=el("div",undefined,"columns");
  for(const [name,a] of Object.entries(d.measurement.arms)){const arm=section(name.toUpperCase());arm.append(facts([["Assigned / mature accounts",a.assigned+" / "+a.mature_accounts],["Qualified meetings",a.qualified_meetings],["Accepted opportunities",a.accepted_opportunities],["Synthetic pipeline",cash(d,a.pipeline_cents)],["Meeting rate",(a.meeting_rate*100).toFixed(1)+"%"]]));grid.append(arm);}
  comparison.append(grid,finding("Activity is not incrementality","Outcome accounts and deal scopes were specified independently of assignment. Large deals can dominate this small synthetic observation. Holdout outcomes are organic; these results establish neither causal improvement nor AI-driven pipeline lift."));p.append(comparison);
}

function native(p,{el,section,raw,json:read,facts,finding}) {
  const a=read("acceptance.json"),n=read("native-details.json"),c=read("post-cleanup.json"),grid=el("div",undefined,"columns"),left=section("One guarded native SDR handoff"),right=section("Independent identity and authority checks");
  left.append(facts([["Environment","Isolated Salesforce Developer Edition"],["Account + Contact","Resolved by exact synthetic identity keys"],["Lost acknowledgment","Discarded after native commit; receipt recovered without repost"],["Duplicate probe","Server transaction rolled back the extra Task"],["Owner / consent / active opportunity","New actions rejected when authority changed"],["Commercial outcomes","Not part of this native run"]]));
  right.append(finding("Associations are inspectable","Account, Contact, Task and original owner relationships are independently read back. Public identifiers are hashed; response hashes are not Salesforce signatures."),raw(n.relationships));grid.append(left,right);p.append(grid);
  const permissions=section("Effective permissions, rejection responses and restoration");
  for(const [title,value] of [["Effective object / field permissions",n.effective_permissions],["Actual rejected operations",n.rejected_operations],["Three native Apex test results",n.apex_deployment],["Controlled retention and grant restoration",{cleanup:a.cleanup,independent_cleanup:c}]]){const detail=el("details");detail.append(el("summary",title),raw(value));permissions.append(detail);}p.append(permissions);
  const ops=section("Inspect a recorded native API operation"),label=el("label","Recorded Salesforce request");label.htmlFor="gtm-request";const select=el("select");select.id="gtm-request";
  a.requests.forEach((r,i)=>{const o=el("option",(i+1)+" · "+r.role+" · "+r.method+" "+r.resource+" · HTTP "+r.http);o.value=i;select.append(o);});const output=raw(a.requests[0]);select.addEventListener("change",()=>output.textContent=JSON.stringify(a.requests[select.value],null,2));ops.append(label,select,output);p.append(ops);
}

function advice(p,{el,section,raw,json:read,facts,finding}) {
  const d=read("evaluation.json"),block=section("Actual Qwen3 responses · inspect accepted and rejected advice"),label=el("label","Recorded model case");label.htmlFor="gtm-model";const select=el("select");select.id="gtm-model";
  d.records.forEach((r,i)=>{const o=el("option",r.case_id+" · "+(r.validation_error||"exact citations pass"));o.value=i;select.append(o);});const display=el("div");
  const render=()=>{const r=d.records[select.value],col=el("div",undefined,"columns"),left=section("Original model response"),right=section("Policy and execution boundary");
    left.append(el("div",r.parsed?.summary||"Rejected response · original text preserved below", "draft"));
    const response=el("details");response.append(el("summary","Read the exact raw inference response"),raw(r.raw_response));left.append(response);
    right.append(facts([["Case",r.case_id],["Model",r.model],["Citation result",r.validation_error||"Exact spans passed"],["Semantic support",r.semantic_support],["Native Salesforce linkage","None · separate execution set"]]),raw(r.policy));
    if(r.validation_error)right.append(finding("Rejected recommendation preserved",r.validation_error+". A failed citation does not become an approved CRM action."));
    const evidence=el("details");evidence.append(el("summary","Inspect supplied evidence, ownership and citations"),raw(r.context),raw(r.parsed?.citations||[]));left.append(evidence);
    col.append(left,right);display.replaceChildren(col);};select.addEventListener("change",render);render();block.append(label,select,display);p.append(block,finding("Advice is not authorization","Policy observations and approval hashes belong to this recorded local evaluation. They do not prove semantic usefulness, Salesforce delivery or commercial results. No model call occurs when you change the selected case."));
}
