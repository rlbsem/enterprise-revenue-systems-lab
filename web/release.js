// Recorded evidence projection only. No inference, effects, approval or release controls.
let selected = "eligible";
const stages = [
  ["original", "01", "Original limitations", "Qwen2.5"],
  ["blocked", "02", "Release blocked", "First Qwen3"],
  ["eligible", "03", "Suite eligible", "Bounded reasoning"],
  ["shadow", "04", "Shadow", "No effects"],
  ["canary", "05", "Read-only canary", "Actual routing"],
  ["promoted", "06", "Local promotion", "Verified receipt"],
  ["rollback", "07", "Fault → rollback", "Reference restored"],
];

export function releaseMetrics(read, metric) {
  const c=read("projection.json").comparisons.at(-1), l=read("lifecycle.json");
  return [metric("Candidate task outcomes",`${c.passed}/${c.tasks}`,"Recorded finite suite · not general accuracy"),
    metric("Unsafe recommendations",c.unsafe,"Accepted suite · earlier defects retained"),
    metric("Independent local effects",l.independent_effects.length,"Promoted synthetic task · exact readback"),
    metric("Final release state","Rolled back","Controlled fault · reference routing verified")];
}

export function releasePanel(ui) {
  const {el,section,json:read,facts,finding}=ui;
  const raw=value=>{const pre=ui.raw(value);pre.tabIndex=0;return pre;};
  const p=el("div",undefined,"release-investigation"), life=read("lifecycle.json"), comparisons=read("projection.json").comparisons;
  const hero=el("div",undefined,"release-hero");
  hero.append(el("div","RECORDED LOCAL INFERENCE · RELEASE GOVERNANCE","release-kicker"),
    el("h3","A passing model needs a controlled release."),
    el("p","Follow the rejected candidate, the finite acceptance suite and the actual local routing change. Then inspect the fault that sent execution back to the reference."));
  const scores=el("div",undefined,"release-scores");
  for(const [a,b,label] of [[0,1,"Original Qwen2.5"],[2,3,"First Qwen3 · blocked"],[4,5,"Bounded Qwen3 · eligible"]]) {
    const box=el("div");box.append(el("small",label),el("strong",`${comparisons[a].passed}/${comparisons[a].tasks} → ${comparisons[b].passed}/${comparisons[b].tasks}`),el("span","Reference → candidate · recorded tasks"));scores.append(box);
  }
  hero.append(scores);p.append(hero);
  p.append(el("p","Actual model inference, deterministic software tests and synthetic destination effects are separate evidence. Nothing in this viewer performs a new model call or changes a release.","gtm-boundary"));
  const nav=el("nav",undefined,"release-stages");nav.setAttribute("aria-label","Recorded release progression");
  const content=el("div",undefined,"release-detail"); content.id="release-detail";
  const announcement=el("p",undefined,"release-announcement");announcement.setAttribute("role","status");announcement.setAttribute("aria-live","polite");
  function inspect(title,value,parent) { const d=el("details");d.append(el("summary",title),raw(value));parent.append(d); }
  function show() {
    for(const b of nav.querySelectorAll("button"))b.setAttribute("aria-pressed",String(b.dataset.stage===selected));
    content.replaceChildren();const name=stages.find(s=>s[0]===selected)[2];announcement.textContent="Viewing recorded state: "+name;
    const title=section(name);content.append(title);
    if(["original","blocked","eligible"].includes(selected)) {
      const indices=selected==="original"?[0,1]:selected==="blocked"?[2,3]:[4,5];
      const rows=indices.map(i=>comparisons[i]), grid=el("div",undefined,"columns");
      for(const row of rows){const b=section(row.label);b.append(facts([["Task outcomes",`${row.passed}/${row.tasks}`],["Unsafe recommendations",row.unsafe],["Unauthorized / duplicate effects",`${row.unauthorized} / ${row.duplicates}`],["Release decision",row.release]]));grid.append(b);}title.append(grid);
      if(selected==="original"){
        title.append(finding("Correct quotations can still lead to the wrong action.","The original small model made unsafe recommendations even when numeric claims were grounded. Deterministic policy blocked effects; those recommendations remain model defects."));
        inspect("Inspect original rejected adoption decision",read("original-failure.json"),title);
      } else if(selected==="blocked") {
        title.append(finding("35/36 was insufficient for release.","The hostile-case response exhausted the 1,536-token completion allowance and returned an empty final answer. Mandatory oracle and contract checks blocked promotion."));
        title.append(facts([["Gate",read("first-gate.json").decision],["Reasons",read("first-gate.json").reasons.join(" · ")]]));
        inspect("Inspect the actual length-limited response and partial effects",read("first-failure.json"),title);
      } else {
        const c=read("bounded-candidate.json").configuration,r=read("bounded-reference.json").configuration;
        title.append(facts([["Reference / candidate reasoning cap",`${r.decoding.reasoning_cap} / ${c.decoding.reasoning_cap} tokens`],["Total completion allowance",`${c.decoding.total_completion_budget} tokens each`],["Model",c.model_artifact.file],["Gate",read("bounded-gate.json").decision]]));
        title.append(el("p","Reserve answer capacity; derive completion requirements from authenticated facts. Each configuration ran 24 cases at two seeds: six development, twelve known regression and six fresh holdout cases. Both passed; this does not establish superiority of the candidate."));
        inspect("Inspect the source seal, prompts, model identity and holdout protocol",read("seal.json"),title);
      }
      const results=section("Inspect recorded task outcomes"), label=el("label","Evaluation configuration");label.htmlFor="release-config";
      const choice=el("select");choice.id="release-config";
      rows.forEach(r=>{const o=el("option",r.label);o.value=r.file;choice.append(o);});choice.value=rows.at(-1).file;
      const filterLabel=el("label",undefined,"release-filter"), filter=el("input");filter.type="checkbox";filter.id="release-failed";filter.checked=selected!=="eligible";filterLabel.append(filter,document.createTextNode("Show unsuccessful tasks only"));
      const table=el("table"), caption=el("caption","Original result rows · links open the exact upstream task record"),head=el("thead"),hr=el("tr");
      for(const h of ["Task / split","Outcome","Recorded reason"]){const th=el("th",h);th.scope="col";hr.append(th);}head.append(hr);const body=el("tbody");table.append(caption,head,body);
      const empty=el("p");empty.setAttribute("role","status");
      function fill(){const r=rows.find(r=>r.file===choice.value),records=r.results.filter(x=>!filter.checked||!x.passed);body.replaceChildren();for(const row of records){const tr=el("tr"),cell=el("td"),a=el("a",row.task+" ↗");a.href=row.source_url;cell.append(a,el("small",row.split));tr.append(cell,el("td",row.passed?"Passed":"Failed",row.passed?"release-pass":"release-fail"),el("td",row.reason));body.append(tr);}empty.textContent=records.length?`${records.length} recorded task rows shown.`:"No unsuccessful tasks in this recorded configuration.";}
      choice.addEventListener("change",fill);filter.addEventListener("change",fill);fill();results.append(label,choice,filterLabel,table,empty);content.append(results);
    } else if(selected==="shadow" || selected==="canary") {
      const d=life[selected];title.append(facts([["Paired contexts",d.pairs.length],["Observed effects",d.external_effects],["Mode",d.mode]]));
      title.append(el("p",selected==="shadow"?"Fresh reference and candidate inference compared equivalent scoped inputs. Recommendations were non-authoritative.":"The selected candidate actually ran through the registry in shadow mode without write authority. This is a bounded local canary, not production traffic."));
      if(selected==="canary")title.append(facts([["Selected route",life.routed_canary.route.version],["Run status",life.routed_canary.status],["Write effect","None"]]));
      for(const pair of d.pairs){const block=el("details");block.append(el("summary",pair.case+" · inspect paired decisions and authentic context"),raw(pair));title.append(block);}
      inspect("Inspect recorded model requests and responses for this stage",selected==="canary"?{run:life.routed_canary,inference:life.inference}:life.shadow,title);
    } else if(selected==="promoted") {
      title.append(facts([["Active version",life.promoted_run.route.version],["Mode / status",`${life.promoted_run.route.mode} / ${life.promoted_run.status}`],["Independent effects",life.independent_effects.length]]));
      title.append(el("p","The active candidate created one actual internal task in a synthetic local HTTP destination. Its receipt content was read independently and matched exactly. It is not a Salesforce action or commercial result."));
      const receipt=section("Independent destination readback");receipt.id="release-receipt";receipt.append(raw(life.independent_effects));content.append(receipt);
      inspect("Inspect the routed promotion trace and verified receipt",life.promoted_run,title);
    } else {
      const fault=life.injected_context_fault, rollback=life.history.at(-1).detail;
      title.append(finding("Controlled fault detected · no additional effect","A test wrapper corrupted the support count only in the model-input copy. The real model response contradicted authentic evidence; the guard escalated it. This is controlled fault injection, not a naturally observed model regression."));
      title.append(facts([["Candidate fault status",fault.status],["Guardrail",fault.trace.find(t=>t.kind==="guardrail").detail.reason],["Next actual route",life.rollback_run.route.version],["Next run status",life.rollback_run.status],["Prior effects undone",rollback.external_effects_undone?"Yes":"No · rollback changes future routing"]]));
      inspect("Inspect controlled-fault trace",fault,title);
      inspect("Inspect subsequent reference inference and routing",{run:life.rollback_run,actual_requests:life.inference[life.rollback_run.route.version]},title);
    }
  }
  for(const [key,number,label,note] of stages){const b=el("button");b.type="button";b.dataset.stage=key;b.setAttribute("aria-controls","release-detail");b.append(el("small",number+" · "+note),el("strong",label));b.addEventListener("click",()=>{selected=key;show();});nav.append(b);}
  p.append(nav,announcement,content);show();
  const boundaries=section("What this establishes (and what it does not)");
  boundaries.append(el("p","Recorded real inference met this finite synthetic suite and exercised the local release controls. These results do not establish production reliability, general model accuracy or commercial outcomes. The same engineer authored the domain rules and cases; this is not an external blind benchmark."));
  const software=read("software.json"),controls=read("controls.json");
  boundaries.append(facts([["Separate source software regression",`${software.tests} tests · ${software.failures} failures`],["Permission / replay controls",`${Object.values(controls.checks).filter(Boolean).length}/${Object.keys(controls.checks).length}`],["Escalation approvals","Trusted synthetic evaluation harness · not human reviewer quality"]]));
  inspect("Inspect actual approval, permission and duplicate checks",controls,boundaries);
  const origins=el("details");origins.append(el("summary","Pinned source lineage · selected original bytes and full upstream records"));
  for(const a of read("upstream.json").artifacts){const line=el("div",undefined,"gtm-origin"),link=el("a",a.source_path+" ↗");link.href=a.source_url;line.append(link,el("code",a.sha256));origins.append(line);}
  boundaries.append(el("p",read("upstream.json").execution_revision_note),origins);p.append(boundaries);return p;
}
