# AI Account Intelligence to Qualified Pipeline

Investigation 05 adds three **separate recorded evidence cases** from [GTM Pipeline Orchestration](https://github.com/rlbsem/gtm-pipeline-orchestration/tree/6da3603a8e447dacfdbde25a8aab5c5fa3721328). The Lab is a static reader. No Salesforce credentials, Python installation or LLM endpoint are required by a browser visitor.

| Case | What can be inspected | Execution boundary |
|---|---|---|
| `gtm-enterprise` | 120 accounts; original 163-test regression record; fit/intent contributions; source authority and routing; exact approvals and receipts; five USD opportunities; treatment/holdout denominators | Recorded local synthetic HTTP engine execution. USD $3,460,000 is illustrative qualified pipeline, not revenue. |
| `gtm-salesforce` | 140 API operation observations; Account/Contact/Task association and owner hashes; effective object/field permissions; rejected operations; atomic receipt and lost-ack recovery; three Apex tests; 20 read-only cleanup checks | A separate actual Developer Edition acceptance run. No enterprise pipeline outcomes were executed in Salesforce. |
| `gtm-qwen` | All 16 original Qwen3 responses and supplied evidence; exact quotations; ten mechanical citation passes and six failures; per-case policy/approval observations | A separate actual model evaluation. Exact citations are not independent semantic usefulness. No native Salesforce action is inferred from these responses. |

The cases demonstrate complementary capabilities. There is no shared live vendor funnel, prospect communication, customer deployment, causal AI lift or commercial result. Source qualification does not establish genuine external buying intent. Enterprise CRM owners are local synthetic inputs; the native case's separately hashed relationships establish its own Salesforce ownership checks.

## Provenance and verification

The [source lock](../sources.lock.json) pins the import revision and original file hashes. Each bundle contains exact Git blob bytes, `upstream.json` links and recorded source revisions. Packaging time describes the import, not another execution. Native acceptance, cleanup and Qwen source revisions remain distinct from the USD scenario revision.

The browser validates every artifact against its catalog-pinned manifest. The model case includes the original instruction source and reconstructs each recorded request hash from its prompt, context, seed and parameters. It does not rerun inference. The offline verifier also recomputes source opportunity sums, scope multiplication, the full account denominator, SQL comparisons and exact approvals. It checks native association/readback relationships, protected object grants, cleanup restoration and original response references; the model checks preserve exact responses, context hashes and citation failures. These are author-controlled sanitized records, not vendor-signed attestations.

```shell
python -m revenue_lab.cli verify web/evidence/gtm-enterprise
python -m revenue_lab.cli verify web/evidence/gtm-salesforce
python -m revenue_lab.cli verify web/evidence/gtm-qwen
```

To deliberately reimport the same public artifacts from an existing GTM Git checkout:

```shell
python scripts/import_gtm.py /path/to/gtm-pipeline-orchestration
python scripts/build.py
```

This reads committed blobs at the fixed revision. It does not execute an engine, infer a response, authenticate or change vendor state. Native reproduction remains the GTM repository's explicitly authorized acceptance process; the Lab adds no native execution route. The existing local runner allowlist is unchanged.

## Browser evidence and deployment

The [new browser review](evidence/gtm-integration/browser.json) covers all three cases, four tabs and five viewport sizes (320–1440px), rendered text contrast, keyboard focus, portable imports, artifact validation and exact reproduction ZIP downloads. [Genuine screenshots](images/gtm/gtm-enterprise-overview.png) are captured from real static pages using the existing records. This is a focused automated accessibility review, not full WCAG certification or assistive-technology testing.

Existing cases, execution evidence and historical screenshots are preserved. Source records can be opened in each account/model view or through the original-artifact selector. Shareable `?case=gtm-enterprise`, `?case=gtm-salesforce` and `?case=gtm-qwen` links work under the existing GitHub Pages repository prefix. These routes are now included on `main`. [Pages deployments](https://github.com/rlbsem/enterprise-revenue-systems-lab/actions/workflows/pages.yml?query=branch%3Amain) and [hosted verification](https://github.com/rlbsem/enterprise-revenue-systems-lab/actions/workflows/hosted.yml?query=branch%3Amain) document public availability independently of local tests.
