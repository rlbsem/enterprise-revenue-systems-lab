"""Original-byte preservation plus independently calculated decision relationships."""
import copy
import hashlib
import json
import re
import shutil
import pytest
from revenue_lab.bundle import ROOT, LOCK, canonical, load_verified, verify, write_json
from revenue_lab.integration_checks import economics, warehouse

CASES = ('economics-integration', 'warehouse-verification')


def test_all_twelve_prior_investigations_and_540_evidence_files_survive():
    folder=ROOT/'docs/evidence/integration-economics'
    for path,h in json.loads((folder/'preserved-main.json').read_bytes())['sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==h,path
    prior=json.loads((folder/'prior-main-ui.json').read_bytes())['files']
    before=json.loads(prior['web/catalog.json'])['scenarios']
    after=json.loads((ROOT/'web/catalog.json').read_bytes())['scenarios']
    assert len(before)==21 and len(after)==23
    assert len({c['investigation'] for c in after})==13
    assert all(row in after for row in before)
    old=json.loads(prior['sources.lock.json'])
    assert all(LOCK[k]==v for k,v in old.items() if k!='sources')
    assert all(LOCK['sources'][k]==v for k,v in old['sources'].items())


@pytest.mark.parametrize('case',CASES)
def test_source_pins_and_offline_relationships(case):
    assert verify(ROOT/'web/evidence'/case)['integrity']=='verified'
    manifest,f=load_verified(ROOT/'web/evidence'/case)
    assert manifest['mode']=='recorded'
    assert not f['observation.json']['new_native_execution']


def test_exact_economics_and_native_scope():
    _,f=load_verified(ROOT/'web/evidence/economics-integration')
    p=economics(f)
    assert p['annual_source_events']==1200000000
    assert {k:v['annual_cents'] for k,v in p['alternatives'].items()}=={
        'reference':{'operating':28192323,'campaign-disruption':28579716},
        'optimized':{'operating':18758995,'campaign-disruption':21950617},
        'resilient':{'operating':19675209,'campaign-disruption':20063045}}
    assert p['sensitivity_comparisons']==22 and len(p['http_trials'])==8
    _,f=load_verified(ROOT/'web/evidence/warehouse-verification')
    assert warehouse(f)['native_row_counts']==dict(daily=1,events=1856,items=4828,purchases=14,sessions=12)
    assert warehouse(f)['bytes_processed']==19631768


@pytest.mark.parametrize('fault',['line','capacity','annual','sensitivity','false_acceptance','journal','receipt_get'])
def test_economics_rejects_wrong_underlying_results_even_with_updated_report_hash(fault):
    _,f=load_verified(ROOT/'web/evidence/economics-integration');f=copy.deepcopy(f)
    d=f['decision.json'];m=d['alternatives']['optimized']['assessment']['conditions'][0]['months'][0]
    if fault=='line':m['lines'][0]['source_events']+=1
    elif fault=='capacity':m['shared_work']['headroom']+=1
    elif fault=='annual':d['alternatives']['reference']['assessment']['conditions'][0]['annual_cents']+=1
    elif fault=='sensitivity':d['sensitivity'][0]['independent_annual_cents']+=1
    elif fault=='false_acceptance':f['http/launch-surge-result.json']['acceptable']=True
    elif fault=='journal':f['http/normal-journal.txt']=f['http/transient-recovery-journal.txt']
    else:
        # Dropping the recovery GET undercounts actual independently observed requests.
        f['http/transient-recovery-result.json']['actual_requests']['destination-api']-=1
        t=next(t for t in f['http-summary.json']['trials'] if t['name']=='transient-recovery')
        t['result']=f['http/transient-recovery-result.json']
        t['result_hash']=hashlib.sha256(canonical(t['result']).encode()).hexdigest()
    f['acceptance.json']['decision_sha256']=hashlib.sha256(canonical(d).encode()).hexdigest()
    with pytest.raises(ValueError):economics(f)


@pytest.mark.parametrize('fault',['model_signature','job_sql','build_claim','local_oracle','missed_fault','guard_sql'])
def test_warehouse_rejects_changed_results_or_false_native_claims(fault):
    _,f=load_verified(ROOT/'web/evidence/warehouse-verification');f=copy.deepcopy(f)
    if fault=='model_signature':f['model-results.json'][0]['multiset_sha256']='0'*64
    elif fault=='job_sql':f['jobs.json'][0]['sql_sha256']='0'*64
    elif fault=='build_claim':f['native.json']['evidence_boundaries']['native_dbt_build']=True
    elif fault=='local_oracle':f['local.json']['complete_python_oracle']['independent_full_matches']=False
    elif fault=='missed_fault':f['guard.json']['observations'][0]['revised_guard_findings']=0
    else:f['ga4_pipeline/tests/assert_no_regression.sql']+='-- changed'
    with pytest.raises(ValueError):warehouse(f)


@pytest.mark.parametrize('case',CASES)
def test_resealing_original_bytes_cannot_replace_locked_source(tmp_path,case):
    p=tmp_path/case;shutil.copytree(ROOT/'web/evidence'/case,p)
    name='decision.json' if case.startswith('economics') else 'native.json'
    raw=(p/name).read_bytes()+b' ';(p/name).write_bytes(raw)
    m=json.loads((p/'bundle.json').read_bytes());a=next(a for a in m['artifacts'] if a['path']==name)
    a.update(sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw));m['input_hashes'][name]=a['sha256'];write_json(p/'bundle.json',m)
    with pytest.raises(ValueError,match='original imported bytes differ'):verify(p)


def test_new_panels_are_read_only_and_excluded_from_execution():
    from revenue_lab.server import ALLOWED
    assert not set(CASES)&set(ALLOWED)
    for name in ('economics.js','warehouse.js','evidence-ui.js'):
        code=(ROOT/'web'/name).read_text(encoding='utf8')
        assert not re.search(r'\b(fetch|XMLHttpRequest|WebSocket|sendBeacon|innerHTML)\b',code)
    for case in CASES:
        for p in (ROOT/'web/evidence'/case).rglob('*'):
            if p.is_file() and p.suffix in ('.json','.txt'):
                assert not re.search(r'"(?:password|access_token|api_secret|private_key)"\s*:',p.read_text(encoding='utf8'))
