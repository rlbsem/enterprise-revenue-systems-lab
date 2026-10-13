# Publish after owner approval

The application has a static build in `dist/`. It contains only HTML, CSS, JavaScript and recorded synthetic evidence. It requires no secrets, Python service, PostgreSQL database or live model endpoint.

## Owner publishing steps

These steps require the owner's explicit approval. This update does not merge the PR, change repository settings or publish the application.

1. Review the final green PR head and, after approval, merge PR #1 into `main`. Merging alone does not publish anything. The deployment workflow must exist on the default branch before GitHub shows its manual Run workflow control.
2. In the repository, open **Settings > Actions > General**. Ensure GitHub Actions is enabled and that the pinned official `actions/*` actions are permitted by the repository or organization policy. Leave the default Workflow permissions at **Read repository contents and packages permissions**; the workflow declares its narrowly scoped publishing permissions itself. No repository secret, personal access token or model key is needed.
3. Open **Settings > Pages > Build and deployment**. Set **Source** to **GitHub Actions**. Do not select Deploy from a branch and do not add a second automatic Pages workflow.
4. Open **Settings > Environments > github-pages** (create it if it is not yet listed). Under **Deployment branches and tags**, select **Selected branches and tags**, add a **Branch** rule for `main`, and exclude other branches and tags. Where required reviewers are available, add the owner as a reviewer if a separate approval gate is desired. A sole owner must be allowed to approve their own manually requested deployment. Save these protection rules before running the workflow.
5. Open **Actions > Publish static evidence lab > Run workflow**. Select **Branch: main**, then click **Run workflow**. Approve the `github-pages` environment deployment if a reviewer gate was configured. A feature-branch dispatch is intentionally skipped. Pushes, pull requests and merges never trigger this publishing workflow.
6. Wait for both **build** and **deploy** to succeed. Open the URL emitted by the deploy job's environment, or the published link shown in **Settings > Pages**. Until this deployment and the following browser checks succeed, the application has no verified public URL.
7. On the published site, open all three investigations, select evidence cases, validate artifact integrity, inspect source records and download a reproduction ZIP. Check the attribution link and mobile layout. Confirm that fresh-execution controls are absent. The repository path is supported through relative asset URLs; no custom domain is required.

If a run fails, inspect its step logs, correct the identified issue and manually run it again from `main`. A missing Pages configuration causes failure: the workflow explicitly disables automatic Pages enablement. To withdraw a published site later, use **Settings > Pages > Unpublish site**; this is an owner action, not an automatic PR behavior.

## Deployment boundary

The [manual workflow](../.github/workflows/pages.yml) installs locked dependencies, verifies recorded evidence and package inventory, builds `dist/`, and checks that every distribution file exactly matches `web/`. Only `dist/` is uploaded. The build job has read-only repository access; only the separate protected deployment job receives `pages: write` and `id-token: write`. Actions are pinned to immutable commit hashes, checkout credentials are not persisted, and deployments are serialized.

No source checkout, Python execution API, environment file, database, model service or local credential is included in the uploaded artifact. Reproduction commands are instructional text in the recorded explorer. Fresh execution remains a separate opt-in local capability.

Use `python scripts/build.py` to prepare the static files and `python scripts/check_repository.py` to check the underlying evidence. Test the final public URL after deployment. A successful local build is not proof that a hosted deployment or GitHub workflow has succeeded.

GitHub's official instructions cover [custom Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) and [manual workflow dispatch](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).
