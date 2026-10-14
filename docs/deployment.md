# Static GitHub Pages deployment and verification

The application publishes a browser-only build from `dist/`. It contains HTML, CSS, JavaScript and recorded synthetic evidence. It needs no secrets, Python service, PostgreSQL database or live model endpoint.

## Current publishing status

- [PR #1](https://github.com/rlbsem/enterprise-revenue-systems-lab/pull/1) was merged to `main`.
- The [original Pages deployment](https://github.com/rlbsem/enterprise-revenue-systems-lab/actions/runs/38435896797) and the [corrected auto-published deployment](https://github.com/rlbsem/enterprise-revenue-systems-lab/actions/runs/38495435399) both completed successfully. The deployed URL is `https://rlbsem.github.io/enterprise-revenue-systems-lab/`.
- The site owner reviewed the published application and confirmed the display correction. That is a basic browser review, not independent end-to-end verification of all evidence cases, mobile layouts, downloads, or imported bundles. Check those paths before using them in a live demonstration.

## Republish or verify

Web-application updates are automatically published from `main` after the evidence checks pass. Source artifact data is not rewritten for display-only changes.

1. Confirm **Settings > Pages > Build and deployment** uses **GitHub Actions**. Changes to `web/**` or the publishing workflow on `main` trigger an automatic deployment. Manual `workflow_dispatch` remains available.
2. If republishing, go to **Actions > Publish static evidence lab > Run workflow**, choose `main`, and authorize the protected `github-pages` environment if requested.
3. Check both `build` and `deploy` jobs are successful. The build verifies recorded evidence and ensures the public artifact includes only static distribution files.
4. Open the Pages URL. Inspect all three investigations, navigate evidence cases, validate integrity, download a reproduction ZIP, and check mobile behavior. Fresh-execution controls must be absent from the hosted site.
5. If a run fails, use the job logs to identify the issue. To withdraw the public site, use **Settings > Pages > Unpublish site**.

## Deployment boundary

The [publishing workflow](../.github/workflows/pages.yml) installs locked dependencies, verifies recorded evidence and package inventory, builds `dist/`, and checks that every distribution file exactly matches `web/`. Only `dist/` is uploaded. The build job has read-only repository access; only the separate protected deployment job receives `pages: write` and `id-token: write`. Actions are pinned to immutable commit hashes, checkout credentials are not persisted, and deployments are serialized.

No source checkout, Python execution API, environment file, database, model service or local credential is included in the uploaded artifact. Reproduction commands are instructional text in the recorded explorer. Fresh execution remains a separate opt-in local capability.

Use `python scripts/build.py` to prepare the static files and `python scripts/check_repository.py` to check the underlying evidence. Test the final public URL after deployment. A successful local build is not proof that a hosted deployment or GitHub workflow has succeeded.

GitHub's official instructions cover [custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) and [manual workflow dispatch](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).
