"""Independent, offline checks of recorded economics and warehouse relationships.

No imported Python is executed. No solver, HTTP receiver, dbt or vendor is invoked.
"""
import base64
import gzip
import hashlib
import json
from collections import Counter
from .bundle import LOCK, canonical
from .gtm_checks import require


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def verify_import(path, case, files):
    up = files['upstream.json']
    require(up == LOCK['integration_imports'][case], 'source provenance differs')
    for a in up['artifacts']:
        raw = (path / a['file']).read_bytes()
        require(sha(raw) == a['sha256'], 'original imported bytes differ')
        original = base64.b64decode(raw, validate=True) if a['encoding'] == 'base64-gzip' else raw
        require(sha(original) == a['source_sha256'], 'original source blob differs')
    checker = economics if case == 'economics-integration' else warehouse
    result = checker(files)
    require(result == files['projection.json'], 'display projection differs from underlying records')
    require(files['observation.json']['new_native_execution'] is False and
            files['observation.json']['new_source_execution'] is False, 'new execution falsely claimed')
    return result


def ceil(n, d):
    return (n + d - 1) // d


def check_line(workload, route, month, condition, row):
    """Recompute integer demand, emission, retries and billing from source units."""
    events = ceil(workload['source_events_month'] * month['demand_percent'] * condition['demand_percent'], 10000)
    records = events * workload['downstream_multiplier']
    windows = month['days'] * 1440 // route['lag_minutes']
    peak_windows = 60 // route['lag_minutes']
    peak_population = min(records, ceil(records * workload['peak_hour_ppm'] * condition['peak_percent'], 100000000) * month['days'])
    populations = [(peak_population, peak_windows * month['days']), (records - peak_population, windows - peak_windows * month['days'])]
    batches = 0
    for population, count in populations:
        q, r = divmod(population, count)
        batches += (count - r) * ceil(q, route['batch_size']) + r * ceil(q + 1, route['batch_size'])
    retries = ceil(batches * condition['retry_percent'], 100)
    peak = ceil(peak_population, month['days'])
    q, r = divmod(peak, peak_windows)
    peak_batches = (peak_windows - r) * ceil(q, route['batch_size']) + r * ceil(q + 1, route['batch_size'])
    peak_attempts = peak_batches + ceil(peak_batches * condition['retry_percent'], 100)
    payload = records * workload['payload_bytes']
    components = dict(processing=ceil(records * route['event_cents_per_1000'], 1000),
                      requests=ceil((batches + retries) * route['request_cents_per_1000'], 1000),
                      egress=ceil(payload * route['egress_cents_per_gib'], 2**30),
                      warehouse=ceil(payload * route['warehouse_cents_per_tib'], 2**40))
    expected = dict(source_events=events, downstream_records=records, payload_bytes=payload,
                    records_in_daily_peak_hours=peak_population, peak_records_hour=peak, emission_windows=windows,
                    batches=batches, retry_requests=retries, attempts=batches + retries,
                    peak_attempts_hour=peak_attempts, crm_peak_calls_hour=peak_attempts * route['crm_calls_per_request'],
                    work_peak_units_hour=peak_attempts * route['work_units_per_request'], components_cents=components,
                    variable_cents=sum(components.values()))
    require(all(row[k] == v for k, v in expected.items()), 'monthly source-to-cost arithmetic differs')


def economics(files):
    decision, spec = files['decision.json'], files['scenario.json']
    require(decision['scenario'] == spec and decision['synthetic'] is True and decision['currency'] == spec['currency'] == 'USD', 'synthetic economics scenario differs')
    require(sha(canonical(spec).encode()) == decision['input_sha256'], 'scenario content identity differs')
    require(sha(canonical(decision).encode()) == files['acceptance.json']['decision_sha256'] and files['acceptance.json']['verification_passed'], 'recorded enterprise acceptance differs')
    annual_events = sum(ceil(w['source_events_month'] * m['demand_percent'], 100) for w in spec['workloads'] for m in spec['months'])
    alternatives = {}
    for name, alternative in decision['alternatives'].items():
        selection, assessment = alternative['selection'], alternative['assessment']
        tier = next(t for t in spec['tiers'] if t['id'] == selection['tier'])
        require(assessment['feasible'] and not assessment['violations'], 'selected architecture violates constraints')
        require(set(selection['routes']) == {w['id'] for w in spec['workloads']}, 'workload coverage differs')
        platforms = set()
        for w in spec['workloads']:
            route = next(o for o in w['options'] if o['id'] == selection['routes'][w['id']])
            require(route['lag_minutes'] <= w['max_lag_minutes'] and route['region'] in w['allowed_regions'] and
                    set(w['required_capabilities']) <= set(route['capabilities']), 'ineligible route')
            platforms.add(route['platform'])
        totals = {}
        for report in assessment['conditions']:
            c = next(c for c in spec['conditions'] if c['id'] == report['id'])
            require([m['id'] for m in report['months']] == [m['id'] for m in spec['months']], 'month coverage differs')
            for m, record in zip(spec['months'], report['months']):
                require([r['workload'] for r in record['lines']] == [w['id'] for w in spec['workloads']], 'monthly workload grain differs')
                for w, row in zip(spec['workloads'], record['lines']):
                    route = next(o for o in w['options'] if o['id'] == selection['routes'][w['id']])
                    require(row['route'] == route['id'] and row['platform'] == route['platform'], 'selected route differs')
                    check_line(w, route, m, c, row)
                parts = dict(subscriptions=sum(p['monthly_fixed_cents'] for p in spec['platforms'] if p['id'] in platforms),
                             workers=tier['workers'] * tier['worker_month_cents'], operations=tier['support_hours'] * spec['support_hour_cents'])
                for k in ('processing', 'requests', 'egress', 'warehouse'):
                    parts[k] = sum(r['components_cents'][k] for r in record['lines'])
                overage = max(0, sum(r['attempts'] for r in record['lines']) - tier['included_requests_month'])
                parts['shared_overage'] = overage * spec['overage_cents_per_request']
                require(record['components_cents'] == parts and record['cost_cents'] == sum(parts.values()) and record['overage_requests'] == overage, 'monthly shared accounting differs')
                require(sum(r['fully_allocated_cents'] for r in record['lines']) == record['cost_cents'], 'workload allocations do not conserve cost')
                for k, field, limit in [('shared_work', 'work_peak_units_hour', tier['work_units_hour'] * spec['capacity_utilization_percent'] // 100),
                                        ('crm_quota', 'crm_peak_calls_hour', tier['crm_calls_hour'] * c['quota_percent'] // 100)]:
                    used = sum(r[field] for r in record['lines'])
                    require(record[k] == dict(used=used, limit=limit, headroom=limit-used) and used <= limit, 'capacity/CRM quota differs')
            total = sum(m['cost_cents'] for m in report['months'])
            require(total == report['annual_cents'] and total <= spec['annual_budget_cents'], 'annual cost/budget differs')
            totals[report['id']] = total
        require(set(totals) == {c['id'] for c in spec['conditions']}, 'condition coverage differs')
        alternatives[name] = dict(annual_cents=totals, workers=tier['workers'])
        if name != 'reference':
            plan, oracle = decision['plans'][name], decision['independent_oracles'][name]
            objective = max(totals[c] for c in plan['conditions'])
            require(plan['status'] == oracle['status'] == 'optimal' and plan['selection'] == oracle['best']['selection'] == selection and
                    plan['annual_cents'] == oracle['best']['annual_cents'] == objective, 'recorded solver/oracle agreement differs')
    for s in decision['sensitivity']:
        require(s['plan']['status'] == 'optimal' and s['plan']['annual_cents'] == s['independent_annual_cents'], 'recorded sensitivity disagreement')
    require(decision['budget_rejection']['status'] == 'infeasible', 'budget rejection hidden')
    summary = files['http-summary.json']
    trials = []
    for trial in summary['trials']:
        if 'result' not in trial:
            continue
        result = files['http/' + trial['name'] + '-result.json']
        require(result == trial['result'] and sha(canonical(result).encode()) == trial['result_hash'], 'HTTP result identity differs')
        require(sum(w['source_records'] for w in result['workflows'].values()) == result['source_records'], 'HTTP source accounting differs')
        require(sum(w['on_time_records'] for w in result['workflows'].values()) == result['on_time_records'], 'HTTP on-time accounting differs')
        require(result['acceptable'] is (not result['violations']), 'HTTP rejection hidden')
        journal_name = 'http/' + trial['name'] + '-journal.txt'
        if journal_name in files:
            journal = json.loads(gzip.decompress(base64.b64decode(files[journal_name], validate=True)))
            require(sha(canonical(journal).encode()) == trial['evidence_hash'], 'independent HTTP journal differs')
            bodies = {b['key']: b['payload'] for b in journal['control']['batches']}
            for resource, receiver in journal['receivers'].items():
                # Recovery readbacks are billable synthetic attempts too; do not silently drop GETs.
                require(len(receiver['requests']) == result['actual_requests'][resource], 'receiver request count differs')
                for receipt in receiver['receipts']:
                    body = json.loads(receipt['receipt'])
                    require(sha(bodies[receipt['key']].encode()) == receipt['body_hash'] == body['body_hash'] and body['key'] == receipt['key'] and body['resource'] == resource, 'independent receipt content differs')
        trials.append(dict(name=trial['name'], acceptable=result['acceptable'], source_records=result['source_records'],
                           on_time_records=result['on_time_records'], late_records=result['late_records'], unresolved_records=result['unresolved_records'],
                           actual_synthetic_cost_cents=result['actual_synthetic_cost_cents'], violations=result['violations']))
    require(any(not t['acceptable'] for t in trials), 'rejected execution evidence hidden')
    return dict(annual_source_events=annual_events, currency=spec['currency'], alternatives=alternatives,
                sensitivity_comparisons=len(decision['sensitivity']), http_trials=trials,
                native_vendor_execution=False, enterprise_throughput_measured=False)


def warehouse(files):
    native, local = files['native.json'], files['local.json']
    boundaries = native['evidence_boundaries']
    require(native['status'] == 'executed_read_only_sql' and boundaries['native_google_sql'] is True and
            all(boundaries[k] is False for k in ('native_dbt_compile', 'native_dbt_build', 'native_incremental_merge', 'production_ga4_export')), 'native boundary promoted beyond SELECT evidence')
    for record in (native, local):
        for path, digest in record['source_sha256'].items():
            require(sha(files[path].encode()) == digest, 'warehouse source bytes differ')
    models, source = files['model-results.json'], files['source-results.json']
    normalized = lambda rows: sorted((r['model'], int(r['row_count']), r['multiset_sha256']) for r in rows)
    require(len(models) == len(source) == 5 and len({r['model'] for r in models}) == 5 and normalized(models) == normalized(source), 'independent native multisets differ')
    jobs = {j['job_id']: j for j in files['jobs.json']}
    require(len(jobs) == 2 and set(jobs) == {q['job_id'] for q in native['queries'].values()}, 'native job inventory differs')
    for q in native['queries'].values():
        sql = files[q['source_path']]
        require(sha(sql.encode()) == q['source_sha256'], 'native SQL source differs')
        job = jobs[q['job_id']]
        require(sha(sql.replace('\n', '\r\n').encode()) == job['sql_sha256'], 'provider SQL hash differs')
        require(job['state'] == 'DONE' and job['completed_without_error'] == 'true' and job['cache_hit'] == 'false' and job['statement_type'] == 'SELECT', 'native job not completed uncached SELECT')
    metadata = native['metadata_query']
    require(sha(files[metadata['source_path']].encode()) == metadata['source_sha256'], 'job metadata SQL differs')
    require(local['status'] == 'passed' and local['native_bigquery'] == 'not_executed' and
            local['rowset_comparison']['incremental_equals_full_refresh'] and local['rowset_comparison']['same_batch_replay_unchanged'] and
            local['complete_python_oracle'] == dict(models=5, all_fields_and_multiplicities=True, incremental_matches=True, independent_full_matches=True), 'local complete oracle acceptance differs')
    guard = files['guard.json']
    require(sha(files['ga4_pipeline/tests/assert_no_regression.sql'].encode()) == guard['revised_sql_sha256'], 'regression guard SQL differs')
    negatives = [r for r in guard['observations'] if r['fault'] != 'none']
    require(len(negatives) == 14 and all(r['revised_guard_findings'] > 0 for r in negatives) and
            sum(r['original_guard_findings'] == 0 for r in negatives) == guard['missed_negative_cases_in_original'] == 8, 'regression faults/limitations hidden')
    require([r for r in guard['observations'] if r['fault'] == 'none'][0]['revised_guard_findings'] == 0, 'positive guard control failed')
    return dict(native_row_counts={r['model']: int(r['row_count']) for r in models},
                bytes_processed=sum(int(j['total_bytes_processed']) for j in jobs.values()),
                native_data_jobs=len(jobs), complete_local_rowsets=5, negative_guard_cases=len(negatives),
                original_missed_cases=8, native_dbt_build=False, native_incremental_merge=False)
