# Static GitHub Pages deployment and verification

The application publishes a browser-only build from `dist/`. It contains HTML, CSS, JavaScript and recorded synthetic evidence. It needs no secrets, Python service, PostgreSQL database or live model endpoint.

## Current publishing status

- [PR #1](https://github.com/rlbsem/enterprise-revenue-systems-lab/pull/1) was merged to `main`.
- The [original Pages deployment](https://github.com/rlbsem/enterprise-revenue-systems-lab/actions/runs/38435896797) and the [corrected auto-published deployment](https://github.com/rlbsem/enterprise-revenue-systems-lab/actions/runs/38495435399) both completed successfully. The deployed URL is `https://rlbsem.github.io/enterprise-revenue-systems-lab/`.
- The original owner review was a basic browser review. Subsequent independent hosted observations, including limitations that remain until the proposed fixes are deployed, are recorded in [hosted verification](evidence/hosted-verification/README.md).

## Republish or verify

Web-application updates are automatically published from `main` after the evidence checks pass. Source artifact data is not rewritten for display-only changes.

1. Confirm **Settings > Pages > Build and deployment** uses **GitHub Actions**. Changes to `web/**` or the publishing workflow on `main` trigger an automatic deployment. Manual `workflow_dispatch` remains available.
2. If republishing, go to **Actions > Publish static evidence lab > Run workflow**, choose `main`, and authorize the protected `github-pages` environment if requested.
3. Check both `build` and `deploy` jobs are successful. The build verifies recorded evidence and ensures the public artifact includes only static distribution files.
4. Open the Pages URL. Inspect all eight investigations after the approved new route is deployed, navigate evidence cases, validate integrity, download a reproduction ZIP, and check mobile behavior. Fresh-execution controls must be absent from the hosted site.
5. If a run fails, use the job logs to identify the issue. To withdraw the public site, use **Settings > Pages > Unpublish site**.

## Deployment boundary

The [publishing workflow](../.github/workflows/pages.yml) installs locked dependencies, verifies recorded evidence and package inventory, builds `dist/`, and checks that every distribution file exactly matches `web/`. Only `dist/` is uploaded. The build job has read-only repository access; only the separate protected deployment job receives `pages: write` and `id-token: write`. Actions are pinned to immutable commit hashes, checkout credentials are not persisted, and deployments are serialized.

No source checkout, Python execution API, environment file, database, model service or local credential is included in the uploaded artifact. Reproduction commands are instructional text in the recorded explorer. Fresh execution remains a separate opt-in local capability.

Use `python scripts/build.py` to prepare the static files and `python scripts/check_repository.py` to check the underlying evidence. Test the final public URL after deployment. A successful local build is not proof that a hosted deployment or GitHub workflow has succeeded.

## Read-only hosted verification

After a successful Pages workflow, [Verify hosted evidence](../.github/workflows/hosted.yml) checks the public URL against that deployment's exact source revision. It has only `contents: read`, persists no checkout credentials and receives no deployment permission or application secrets. It does not publish anything. It can also be run from **Actions > Verify hosted evidence > Run workflow > main**. Manual runs compare with current `main`; a deliberately older deployment will fail the byte comparison rather than be reported as current.

The check covers every catalog case at desktop and mobile sizes, all evidence views, browser integrity validation, ZIP contents and standalone domain verification, pinned source links, positive and tampered portable imports, keyboard tabs, skip navigation, shareable case URLs and browser history. Browser HTTP writes and off-site requests are blocked and treated as failures. Read-only GET probes require the execution endpoints to return 404. No vendor execution, model inference or production-service acceptance occurs.

Install `requirements.lock` and Chromium, then run `python scripts/verify_hosted.py` to reproduce the public check. Results and downloaded bundles are written to `.cache/hosted/`; CI retains them as an artifact for 14 days, including when verification fails. A cache-stale deployment, unavailable source link or failed case is a failed check; inspect the report and rerun after resolving it. No silent success fallback is used. Local regression tests exercise the same verifier against a Pages-shaped static build without external source requests.

GitHub's official instructions cover [custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) and [manual workflow dispatch](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).

## Revenue Integrity candidate

The seventh investigation is verified locally under the Pages-shaped path; it is not yet a public deployment. Review its PR and screenshots first. The existing workflow automatically publishes `web/**` changes merged into `main`, so approve both merge and publication before merging. After the deployment completes, run the existing hosted verifier against that exact deployment revision and inspect `?case=revenue-integrity`, all stages, integrity validation, downloads and mobile navigation. No workflow dispatch or deployment was performed by this feature build.

## Analytics Engineering candidate

The eighth investigation is verified against the static Pages-shaped build at `?case=analytics-engineering`. No deployment is performed by its feature branch. After explicit merge/publication approval, use the existing hosted verification to compare exact deployed bytes, all eight navigation entries, original source links, artifact validation, downloads and desktop/mobile behavior. The static-only security boundary and Pages workflow remain unchanged.
