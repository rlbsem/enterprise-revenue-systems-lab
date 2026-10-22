// Read-only projections of pinned execution records. No business engine or vendor client.
import {researchMetrics, researchPanel} from "./research.js";
export function gtmMetrics(id, read, metric) {
  if(id === "gtm-research") return researchMetrics(read, metric);
  if (id === "gtm-enterprise") {
    const d = read("execution.json"), arms = Object.values(d.measurement.arms);
    return [metric("Synthetic accounts", d.account_records.length, "Full assigned-account denominator"),
      metric("Accepted opportunities", arms.reduce((n,a)=>n+a.accepted_opportunities,0), "CRM outcome events · synthetic ACV"),
      metric("Qualified pipeline", cash(d, arms.reduce((n,a)=>n+a.pipeline_cents,0)), "Synthetic estimates · not revenue"),
      metric("Qualified meetings", arms.reduce((n,a)=>n+a.qualified_meetings,0), "Synthetic feedback · both cohorts")];
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
  if(id==="gtm-research") {
    p.append(el("p", "Research, local seller review, native Salesforce and pipeline measurement are separate recorded evidence sets. This viewer makes no new approvals, model calls or CRM writes.", "gtm-boundary"));
  } else {
    p.append(el("p", "The SDR workflow: find an account → understand the signals → review advice → approve a handoff → measure what follows.", "gtm-journey"));
    p.append(el("p", "Evidence boundary: the enterprise scenario, Qwen3 research and native Salesforce handoff are three separate recorded runs. They show complementary capabilities, not a continuous vendor deployment or commercial uplift.", "gtm-boundary"));
  }
  const lanes=el("nav",undefined,"gtm-lanes"); lanes.setAttribute("aria-label","GTM evidence boundaries");
  for(const [key,label] of [["gtm-research","SDR account intelligence"],["gtm-enterprise","01 · Enterprise pipeline"],["gtm-salesforce","02 · Native Salesforce"],["gtm-qwen","03 · Qwen3 advice"]]) {
    const a=el("a",label);a.href="?case="+key;if(key===id)a.setAttribute("aria-current","page");lanes.append(a);
  }
  p.append(lanes);
  if(id==="gtm-research") researchPanel(p,ui);
  else if(id==="gtm-enterprise") enterprise(p,ui);
  else if(id==="gtm-salesforce") native(p,ui);
  else advice(p,ui);
  const origin=el("details"); origin.append(el("summary", "Evidence lineage · original artifacts and recorded revisions"));
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
    const q=JSON.parse(decision.body), col=el("div",undefined,"columns"), left=section("Why this account?"),right=section("What the SDR reviews");
    left.append(facts([["Account",a.name],["Company identity",a.domain],["Responsible owner",a.owner],["Fit / intent",q.fit+" / "+q.intent],["Eligible at recorded decision",q.eligible?"Yes":"No"],["Recorded buying signals",q.signals.map(s=>s.signal).join(" · ")||"None qualifying"]]));
    const action=d.actions.find(x=>x.account_id===a.id), routes=d.routes.filter(x=>x.account_id===a.id);
    const cohort=d.measurement.accounts.find(c=>c.account_id===a.id);
    if(action) right.append(el("div",JSON.parse(action.payload).message,"draft"));
    else right.append(el("p",cohort.arm==="holdout"?"This account is in holdout: no sequence enrollment is authorized. Organic outcomes still count.":"No approved seller action is recorded for this account."));
    right.append(facts([["Routing",routes.length?routes.map(r=>r.owner+" · "+r.reason).join("; "):"No recorded inbound route"],["Review",action?"Exact content approved by "+action.reviewer:"No approved action recorded"],["Recorded handoff",action? action.status+" · "+action.attempts+" attempts":"Not enrolled"],["Block reason",action?.last_error||"None recorded"]]));
    right.append(el("p","This is the local synthetic scenario. No Qwen response or native Salesforce record is attributed to this selected account.","gtm-boundary"));
    const model=el("a","Inspect the separate recorded AI research example →");model.href="?case=gtm-qwen";right.append(model);
    const inspect=el("details");inspect.append(el("summary","Inspect source records and score contributions"),raw({account:a,qualification:q,sources:d.source_records.filter(s=>s.account_id===a.id).map(s=>({...s,payload:JSON.parse(s.payload)}))}));left.append(inspect);
    if(action){const log=el("details");log.append(el("summary","Inspect exact approval, payload and receipt"),raw({action,approval:d.audit.filter(x=>x.event==="exact_approval"&&x.subject===action.action_key)}));right.append(log);}
    const follow=section("What happened next?"),feedback=d.feedback.filter(f=>f.account_id===a.id);
    if(feedback.length)follow.append(...feedback.map(f=>el("p",({reply_positive:"Positive reply",reply_negative:"Negative reply",meeting_qualified:"Qualified meeting",opportunity_accepted:"Accepted opportunity"}[f.kind]||f.kind)+" · "+f.occurred_at.slice(0,10)+(f.amount_cents?" · "+cash(d,f.amount_cents):""))));
    else follow.append(el("p","No meeting or opportunity feedback is recorded for this account. It stays in the assigned-account denominator."));
    follow.append(el("small", "Synthetic CRM/engagement events · "+cohort.arm+" cohort · not actual prospect communications"));
    col.append(left,right);details.replaceChildren(col,follow);
  };
  choice.addEventListener("change",render);render();accountBlock.append(label,choice);
  const failures=el("div",undefined,"gtm-failures");
  for(const [kind,title] of [["owner","Explore changed owner"],["consent","Explore revoked consent"]]){
    const blocked=d.actions.find(a=>a.status==="blocked"&&d.source_records.some(s=>s.account_id===a.account_id&&s.kind===kind));
    if(blocked){const b=el("button",title);b.addEventListener("click",()=>{choice.value=blocked.account_id;render();});failures.append(b);}
  }
  accountBlock.append(failures,details);p.append(accountBlock);
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
  left.append(facts([["Environment","Isolated Salesforce Developer Edition"],["Account + Contact","Matched to the same synthetic account and owner"],["SDR next step","One internal Salesforce Task; no prospect message"],["Lost acknowledgment","Committed Task recovered by readback; no second POST"],["Changed owner or consent","Further actions rejected"],["Duplicate attempt","Extra Task rolled back"]]));
  right.append(finding("The seller gets one owned handoff","The integration user creates the Task. A different identity independently reads it back and confirms the Account, Contact, owner and exact content. Four temporary grants were removed afterward."));
  const identities=el("details");identities.append(el("summary","Inspect independent readback and hashed relationships"),raw(n.relationships));right.append(identities);grid.append(left,right);p.append(grid);
  const permissions=section("Effective permissions, rejection responses and restoration");
  for(const [title,value] of [["Effective object / field permissions",n.effective_permissions],["Actual rejected operations",n.rejected_operations],["Three native Apex test results",n.apex_deployment],["Controlled retention and grant restoration",{cleanup:a.cleanup,independent_cleanup:c}]]){const detail=el("details");detail.append(el("summary",title),raw(value));permissions.append(detail);}p.append(permissions);
  const ops=el("details");ops.append(el("summary","Inspect original native API operations"));const label=el("label","Recorded Salesforce request");label.htmlFor="gtm-request";const select=el("select");select.id="gtm-request";
  a.requests.forEach((r,i)=>{const o=el("option",(i+1)+" · "+r.role+" · "+r.method+" "+r.resource+" · HTTP "+r.http);o.value=i;select.append(o);});const output=raw(a.requests[0]);select.addEventListener("change",()=>output.textContent=JSON.stringify(a.requests[select.value],null,2));ops.append(label,select,output);p.append(ops);
}

function advice(p,{el,section,raw,json:read,facts,finding}) {
  const d=read("evaluation.json"),block=section("AI research brief · what should the SDR ask next?"),label=el("label","Recorded model case");label.htmlFor="gtm-model";const select=el("select");select.id="gtm-model";
  block.append(el("p","The model was asked to summarize supplied account facts, suggest a discovery question and cite exact supporting text. It could not assign ownership, promise delivery or authorize a CRM write."));
  const task=el("details");task.append(el("summary","Inspect the original model instructions and request evidence"),el("p",read("instructions.json").system_prompt),el("small","The offline verifier reconstructs each original request and checks its recorded hash. No inference is rerun."));block.append(task);
  const names={fresh_inbound:"Fresh pricing inquiry",prompt_injection:"Source tries to override instructions",unsupported_personalization:"Unverified meeting or delivery promise",conflicting_enrichment:"Enrichment disagrees with CRM",stale_buying_signal:"Old buying signal",revoked_permission:"Consent already revoked",incorrect_approved_owner:"Owner changes after approval",permission_revoked_after_approval:"Consent changes after approval"};
  d.records.forEach((r,i)=>{const o=el("option",(names[r.case_id]||r.case_id)+" · seed "+r.seed+" · "+(r.validation_error||"exact citations pass"));o.value=i;select.append(o);});const display=el("div");
  const render=()=>{const r=d.records[select.value],col=el("div",undefined,"columns"),left=section("Original model response"),right=section("Policy and execution boundary");
    left.append(el("div",r.parsed?.summary||"Citation check failed · original response preserved below", "draft"));
    if(r.parsed?.suggested_question)left.append(el("div","Suggested discovery question","panel-title"),el("div",r.parsed.suggested_question,"draft"));
    const response=el("details");response.append(el("summary","Read the exact raw inference response"),raw(r.raw_response));left.append(response);
    right.append(facts([["Research account",r.context.account.name],["Responsible owner",r.context.account.owner],["Citation result",r.validation_error||"Exact spans passed"],["Unapproved copy change",r.policy.modified_copy_rejected?"Rejected by exact-content approval":"No copy-change probe needed"],["Independent template action",r.policy.dispatch_status||"Not permitted"],["Native Salesforce linkage","None · separate execution set"]]));
    const policy=el("details");policy.append(el("summary","Inspect policy checks, approval hash and exact response"),raw(r.policy),raw({request_hash:r.request_hash,context_hash:r.context_hash,executed_at:r.executed_at,model:r.model}));right.append(policy);
    if(r.validation_error)right.append(finding("Rejected recommendation preserved",r.validation_error+". This model text was not authorized. A separate unchanged template could still be approved by the finite execution policy; model rejection and workflow refusal are different checks."));
    const evidence=el("details");evidence.append(el("summary","Inspect supplied evidence, ownership and citations"),raw(r.context),raw(r.parsed?.citations||[]));left.append(evidence);
    col.append(left,right);display.replaceChildren(col);};select.addEventListener("change",render);render();block.append(label,select,display);p.append(block,finding("Advice is not authorization","Policy observations and approval hashes belong to this recorded local evaluation. They do not prove semantic usefulness, Salesforce delivery or commercial results. No model call occurs when you change the selected case."));
}
