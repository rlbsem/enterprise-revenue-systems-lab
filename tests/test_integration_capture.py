"""New captures are source-bound; historical captures keep their original bytes."""
import hashlib
import json
from revenue_lab.bundle import ROOT


def test_current_integration_capture_binds_all_rendered_source_and_images():
    r=json.loads((ROOT/'docs/evidence/integration-economics/browser.json').read_bytes())
    assert len(r['catalog_checks'])==184 and len({c['case'] for c in r['catalog_checks']})==23
    assert len(r['layouts'])==40 and len(r['accessibility'])==16
    assert not r['page_errors'] and not r['http_writes'] and not r['nonlocal_requests']
    assert not r['new_native_execution'] and not r['new_source_execution']
    assert all(not c['overflow'] for c in r['catalog_checks'])
    assert all(not c['overflow'] and not c['contrast']['failures'] for c in r['layouts'])
    assert all(not c['violations'] for c in r['accessibility'])
    for name,digest in r['source_sha256'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    assert len(r['images'])==7
    for name,digest in r['image_sha256'].items():
        assert hashlib.sha256((ROOT/'docs/images/integration-economics'/name).read_bytes()).hexdigest()==digest
