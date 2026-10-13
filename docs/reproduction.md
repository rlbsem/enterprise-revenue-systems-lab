# Reproduce the engineering behavior

Use Python 3.12 and Git. All paths below are relative to the Lab checkout. The `prepare` command downloads only the locked source commits and installs their complete dependency locks in separate environments. Installation may need several minutes on a cold cache.

```shell
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps --no-build-isolation -e .
revenue-lab prepare seller --install
revenue-lab prepare control --install
revenue-lab prepare revenue --install
```

Run credential-free seller software scenarios:

```shell
revenue-lab run seller-delivery
revenue-lab run seller-stale
revenue-lab run seller-suppressed
```

These use unchanged saved model responses with matching source snapshots and the original Workbench. They test approval and delivery software without invoking a model. They are explicitly `fresh_replay`, not fresh inference. The runner prints the new bundle path. Verify it with `revenue-lab verify <bundle-directory>`.

## PostgreSQL recovery

The repository supplies a digest-pinned local Compose alternative. The native PostgreSQL route was executed locally; Compose itself is a supplied convenience, not a claimed local execution result. Hosted CI uses the pinned service image.

```shell
docker compose up -d
```

Set `LAB_POSTGRES_ADMIN_DSN` to `host=127.0.0.1 port=55432 user=lab_admin password=disposable-lab-only dbname=postgres connect_timeout=5`, then run `revenue-lab run control-recovery`. Use PowerShell `$env:LAB_POSTGRES_ADMIN_DSN='...'` or your shell's equivalent. The password belongs only to the disposable local service. No AWS resources are created.

The scenario observes a committed receiver effect while the worker reports uncertainty. It also kills a real worker after receiver commit, expires its lease through the fixture's administrative clock-control mechanism and runs the original reconciliation worker. Receiver effects and durable intent are exported separately. The synthetic receiver's transactional idempotency does not establish arbitrary SaaS exactly-once behavior.

## Revenue pipeline

```shell
revenue-lab run revenue-correction
```

This generates the full established-company enterprise profile, runs three original dbt builds, independently audits source CSV totals, applies the original late correction and compares the complete corrected warehouses. Allow up to the bounded 15-minute scenario window and several GB of disposable workspace storage. The fixture and stress profiles remain in the untouched source repository. The stress profile is not executed by this Lab.

## Fresh model inference

Configure a real local OpenAI-compatible endpoint serving Qwen3-14B, set `SELLER_MODEL_KEY` in the process environment, then:

```shell
revenue-lab run seller-live --model-url http://127.0.0.1:8095/v1
```

This invokes the original Model and Workbench. It uses automatic scenario approval and a synthetic receiver; no real customer communication occurs. An absent endpoint, missing key or failed inference produces a failed local run with no fabricated successful bundle. Keys are never included in evidence.

The committed fresh inference was executed with the already-cached Qwen3-14B Q4_K_M model, authenticated llama.cpp/Vulkan endpoint, 8192-token context, one slot and reasoning budget zero. Model/runtime hashes are recorded in the bundle. This is one execution, not a usefulness benchmark. General model setup instructions belong to the pinned Customer Signal repository.

## Local execution interface

```shell
revenue-lab serve --execute --model-url http://127.0.0.1:8095/v1
```

Without `--execute`, the server is read-only. Without `--model-url`, fresh inference is explicitly unavailable; recorded evidence and non-LLM scenarios remain usable. Expand the reproduction panel of an approved case to run it locally. Successful local runs display **FRESH LOCAL EXECUTION** and provide a new portable JSON download. Reloading a recorded case restores **RECORDED EVIDENCE**.

## Verification and static build

```shell
python -m playwright install chromium
python -m pytest -q
python scripts/check_repository.py
python scripts/build.py
```

The browser tests capture actual pages and test downloads, source inspection, every case, mobile layout and tampered imports. `dist/` is a static site suitable for GitHub Pages after owner approval. Neither the local server nor model endpoint is deployed. No Pages deployment workflow is enabled.
