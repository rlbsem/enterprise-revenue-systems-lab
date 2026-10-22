// Read-only views of pinned records. No model, approval, CRM or outreach endpoint.
export function researchMetrics(read, metric) {
  return [metric("Synthetic study accounts", read("queue.json").length, "Separate from the 120-account pipeline"),
    metric("Actual evaluation responses", read("evaluation.json").records.length, "Three prompts · failures retained"),
    metric("Saved seller decision", "1 local", "Separate fresh source + inference run"),
    metric("Source regression tests", read("regression.json").tests.tests, "Recorded source revision · not new Lab tests")];
}

const pretty = value => String(value).replaceAll("_", " ");
export function researchPanel(p, ui) {
  const {el, section, raw, json:read, facts, finding} = ui;
  const scenario = read("scenario.json"), queue = read("queue.json"), evaluation = read("evaluation.json");
  const operator = read("operator-proof.json"), assessment = read("reviewer-assessment.json");
  const rounds = evaluation.rounds.flatMap((r,i) => [...new Set(read(r.evaluation).records.map(x=>x.approach))]
    .map(approach=>({label:`Round ${i+1} · ${approach}`, records:read(r.evaluation).records.filter(x=>x.approach===approach)})));
  const root = el("div",undefined,"research-case");
  const hero = el("div",undefined,"research-hero");
  hero.append(el("span","SDR ACCOUNT INTELLIGENCE","research-eyebrow"), el("h2","Give the seller a reason to investigate."),
    el("p","Prioritize an account, inspect what changed and challenge the opening before any handoff. Hiring and expansion signals support a planning question; they do not establish a purchase."),
    el("small","Recorded synthetic study · January 21, 2026 context · Qwen3 execution in October 2026 · read-only viewer"));
  root.append(hero);
  const split = el("div",undefined,"research-layout"), queuePanel = section("Account queue"), detail = el("div");
  queuePanel.classList.add("research-queue");
  queuePanel.append(el("p","Ranked by curated ICP fit and dated signals. Priority is not purchase intent or authorization.","gtm-boundary"));
  const buttons = new Map();
  for(const a of queue) {
    const b = el("button",undefined,"research-account"); b.type="button";b.setAttribute("aria-pressed","false");
    b.append(el("strong",a.name), el("span",`${a.priority} priority · ${a.fit} fit · ${a.signal_points}/60 signal`),
      el("small",a.eligible?"Research candidate · review still required":"Hold · "+a.blocks.map(pretty).join("; ")));
    b.addEventListener("click",()=>{contextSelect.value=a.case_id;render();});buttons.set(a.case_id,b);queuePanel.append(b);
  }
  const scoring=el("details");scoring.append(el("summary","How the priority is calculated"),
    el("p","40% × curated synthetic fit + signal points capped at 60. Signal points use category weight × confidence × max(0, 1 − age/90 days). Expired, undated, duplicate or mismatched sources contribute zero. CRM ownership, consent and open-opportunity blocks remain independent."),
    el("p","A high deterministic score can coexist with model abstention. Neither score nor model advice authorizes a CRM write."));queuePanel.append(scoring);
  const controls = el("div",undefined,"research-controls");
  const contextLabel=el("label","Research context"),contextSelect=el("select");contextLabel.htmlFor="research-context";contextSelect.id="research-context";
  for(const c of scenario.cases){const o=el("option",c.name+(scenario.workspace_cases.includes(c.id)?"":" · adversarial variant"));o.value=c.id;contextSelect.append(o);}
  const roundLabel=el("label","Recorded evaluation approach"),roundSelect=el("select");roundLabel.htmlFor="research-round";roundSelect.id="research-round";
  rounds.forEach((r,i)=>{const o=el("option",r.label);o.value=i;roundSelect.append(o);});roundSelect.value=rounds.length-1;
  controls.append(contextLabel,contextSelect,roundLabel,roundSelect);
  const live=el("p",undefined,"research-selection");live.setAttribute("role","status");
  detail.append(controls,live);const account=el("div"),model=el("div");detail.append(account,model);
  contextSelect.addEventListener("change",render);roundSelect.addEventListener("change",render);
  split.append(queuePanel,detail);root.append(split);

  function render() {
    const id=contextSelect.value, round=rounds[+roundSelect.value], r=round.records.find(x=>x.case_id===id);
    const context=r.context, q=queue.find(x=>x.case_id===id), index=evaluation.records.findIndex(x=>x.request_hash===r.request_hash&&x.executed_at===r.executed_at);
    const quality=assessment.records[index]; // exact record ordering is checked by the offline verifier
    for(const [key,b] of buttons)b.setAttribute("aria-pressed",String(key===id));
    live.textContent=`${context.name} · ${round.label} · ${r.error?"Rejected output":r.parsed.action==="abstain"?"Model abstained":"Seller review candidate"}`;
    const summary=section("Why this account?"), grid=el("div",undefined,"columns");
    grid.append(facts([["Company identity",context.domain],["Responsible owner",context.crm.owner||"Unverified"],["Known CRM history",context.crm.history],
      ["Contact permission",context.crm.consent?"Recorded as permitted":"Not permitted"],["Open opportunities",context.crm.open_opportunities],
      ["Buying intent / budget","Not established"]]));
    const position=el("div");position.append(el("h4","Review the evidence, not just the score"),
      el("p",q?`${q.priority} priority = ${q.fit} × 0.4 + ${q.signal_points} signal points. ${q.eligible?"Passes deterministic research gate; seller and semantic review still required.":"Held: "+q.blocks.map(pretty).join("; ")}`:"Adversarial evaluation variant, outside the six-account queue."),
      el("p","Sources below are the exact context of this selected response, not substituted with newer evidence. Earlier rounds retain the original synthetic company-name errors.","gtm-boundary"));
    grid.append(position);summary.append(grid);
    const sources=el("details");sources.open=false;sources.append(el("summary",`Source evidence · ${context.sources.length} recorded inputs`));
    for(const s of context.sources) {
      const card=el("article",undefined,"research-source");
      const c=q?.contributions.find(x=>x.source_id===s.source_id);
      card.append(el("h4",pretty(s.kind)+" · "+s.source_id),el("blockquote",s.text),
        el("small",`Published ${s.published_at||"unknown"} · observed ${s.observed_at} · expires ${s.expires_at}`),
        el("p",`Confidence ${Math.round(s.confidence*100)}% · ${c?`${c.age_days} days old · ${c.points} points · ${pretty(c.reason)} in current queue`:"evaluation-only input"}`,"gtm-boundary"),
        el("code",s.url),el("small","Synthetic source URL; .example is not a live job posting."));sources.append(card);
    }
    summary.append(sources);
    if(q){const enrichment=el("details");enrichment.append(el("summary","Enrichment and source authority · fixture adapters"),
      el("p","CRM keeps its owned values. Fallback providers can fill gaps but cannot overwrite the CRM on conflict. These are fixtures, not native Clay calls."),
      facts([["Provider attempts",q.enrichment.attempts.map(a=>a.provider+": "+a.status).join(" → ")],["Conflicts",q.enrichment.conflicts.length? q.enrichment.conflicts.map(c=>`${c.field}: keep ${c.kept}, reject ${c.rejected} (${c.provider})`).join("; "):"None in this fixture"]]),raw(q.enrichment));summary.append(enrichment);}
    account.replaceChildren(summary);
    const brief=section("What would the SDR review?");
    brief.append(el("span",r.error?"REJECTED · EXACT CITATION CONTRACT":r.parsed.action==="abstain"?"ABSTAIN · NO OPENING":"CANDIDATE · NOT AUTHORITY","research-state"));
    if(r.error)brief.append(finding("Rejected recommendation preserved",`${r.error}. Original text remains available below. Rejection is a recorded contract result, not a new model call.`));
    else {
      const b=r.parsed;
      brief.append(el("p",b.relevance));
      if(b.opening)brief.append(el("blockquote",b.opening,"research-opening"));
      else brief.append(el("p","The model did not propose an outreach opening. Inspect its gaps before investing seller attention."));
      const claims=el("details");claims.append(el("summary","Observations, hypotheses and missing information"));
      claims.append(el("h4","Model observations · citations checked, semantic support still needs review"));
      for(const f of b.facts)claims.append(el("p",f.text),el("blockquote",f.quote),el("small",f.source_id));
      if(!b.facts.length)claims.append(el("p","No observations admitted."));
      claims.append(el("h4","Hypotheses · explicitly uncertain"));for(const h of b.hypotheses)claims.append(el("p",h.text+" — "+h.rationale),el("small",h.source_ids.join(", ")));
      if(!b.hypotheses.length)claims.append(el("p","No hypotheses proposed."));
      claims.append(el("h4","Unknowns and contradictions"));for(const gap of b.gaps)claims.append(el("p",gap));brief.append(claims);
    }
    brief.append(finding("Qualitative review · separate AI engineering assessment",`${pretty(quality.seller_usefulness)}. ${quality.note} This is not a blind human SDR study.`));
    const inspect=el("details");inspect.append(el("summary","Exact prompt, raw model response and rubric"),el("p",`Executed ${r.executed_at} · ${r.latency_seconds.toFixed(2)} seconds · ${r.model}`),
      el("h4","What the model was asked"),el("pre",r.prompt),el("h4","Original response · including invalid outputs"),el("pre",r.raw_response),raw({contract_assessment:r.contract_assessment,context_hash:r.context_hash,request_hash:r.request_hash,quality}));brief.append(inspect);
    model.replaceChildren(brief);
  }
  render();

  const evolution=section("An agent improves by exposing its mistakes");
  const stats=el("div",undefined,"research-rounds");
  for(const round of rounds){const n=round.records.length,ok=round.records.filter(r=>Object.values(r.contract_assessment).every(Boolean)).length,card=el("div");
    card.append(el("strong",round.label),el("p",`${ok}/${n} finite rubric passes`),el("small",`${round.records.filter(r=>r.error).length} rejected · ${round.records.filter(r=>r.parsed?.action==="abstain").length} abstained`));stats.append(card);}
  evolution.append(stats,el("p","Rounds 2 and 3 use the same v3 prompt. Round 3 corrects synthetic source company names. Differences are not a controlled prompt-only benchmark. Exact citations are necessary but do not prove semantic entailment or seller usefulness. A conservative injection-case abstention remains a rubric false negative."));root.append(evolution);
  const review=section("A real recorded seller decision · local only");review.id="research-saved-review";
  review.append(el("p","Separate operator execution: a new synthetic continuity source was admitted, fresh Qwen3 research ran, and the opening was approved through the actual local HTTP application. This record saved the model opening unchanged. It is not an approval of whichever evaluation response you selected above."));
  const newSource=operator.record.context.sources.find(s=>s.source_id==="operator-continuity-update");
  review.append(finding("New source before fresh inference",newSource.text));
  const compare=el("div",undefined,"columns"),before=section("Model opening"),after=section("Saved seller text");
  before.append(el("blockquote",operator.record.parsed.opening));after.append(el("blockquote",operator.review.opening,"research-opening"));compare.append(before,after);review.append(compare,
    facts([["Recorded decision",operator.review.decision+" · "+operator.review.reviewer],["Actual execution",operator.executed_at],["Study decision clock",operator.review.at],["Exact replay",operator.repeat_review_identical?"Identical saved review; no duplicate decision":"Not verified"],["Authority","Local internal review only · CRM write authorized: false"]]));
  const original=el("details");original.append(el("summary","Inspect immutable run and approval hashes"),raw({run_hash:operator.run_hash,review:operator.review,transport:operator.transport,primary_120_account_state_unchanged:operator.primary_120_account_state_unchanged}));review.append(original);root.append(review);
  const edited=section("Recorded editable-opening check · separate browser run");
  edited.append(el("p","The source browser test edited the saved evaluation opening, approved its exact text and verified the saved field became immutable. This is a different local run from the fresh operator proof above. The hosted viewer only inspects it."),el("blockquote",read("browser-edit.json").opening));
  const editLink=el("a","Inspect original saved-edit screenshot ↗");editLink.href="https://github.com/rlbsem/gtm-pipeline-orchestration/blob/81d9381169456ca8893be0ddea483296ac77e12e/docs/images/research/seller-research-review.png";
  edited.append(editLink,el("small","Original image SHA-256: "+read("browser-provenance.json").image_sha256["seller-research-review.png"]));root.append(edited);
  const boundary=section("Where this fits in the GTM workflow");
  boundary.append(el("p","Account context → grounded research → seller review → separately authorized execution. New evidence invalidates stale approval; owner changes and revoked consent block new actions in the source engine. This hosted viewer cannot create, edit or submit approvals."));
  for(const [id,title,copy] of [["gtm-salesforce","Inspect native Salesforce Task proof →","Separate Account/Contact resolution, independent Task readback and lost-ack recovery."],["gtm-enterprise","Inspect qualified-pipeline measurement →","Separate 120-account USD $3.46M synthetic scenario; treatment and holdout retained. Not revenue or AI uplift."]]){
    const a=el("a",title);a.href="?case="+id;boundary.append(a,el("p",copy,"gtm-boundary"));}
  boundary.append(el("p","The richer desk has not delivered these research openings through Salesforce. The genuine connected Qwen3-to-Task run uses a different, finite contract. Clay adapters are fixtures; n8n is an unexecuted reference. No prospect communications occur."));root.append(boundary);
  const jobs=read("public-jobs.json"),publicBlock=el("details");publicBlock.append(el("summary","Separate public job API archive · real, read-only reference"),
    el("p",`${jobs.company} · one recorded HTTP ${jobs.http_status} GET at ${jobs.fetched_at}. ${jobs.publication_date_limit} This company is not a synthetic CRM target; these jobs do not feed the account queue.`));
  for(const job of jobs.records){const a=el("a",job.title+" ↗");a.href=job.absolute_url;publicBlock.append(a,el("p","API updated_at: "+job.updated_at));}publicBlock.append(raw({endpoint:jobs.endpoint,response_sha256:jobs.response_sha256}));root.append(publicBlock);
  p.append(root);
}
