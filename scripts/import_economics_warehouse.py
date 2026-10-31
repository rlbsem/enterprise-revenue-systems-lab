"""Import a finite set of exact Git blobs. No source engine, model or vendor execution."""
import argparse
import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from revenue_lab.bundle import ROOT, LOCK, seal, write_json
from revenue_lab.integration_checks import economics, warehouse

PINS = {
    'economics': ('rlbsem/martech-stack-economics', '80cfd61882cd916406edf8b9fba6ba2ff02f4715'),
    'warehouse': ('rlbsem/first-party-measurement-assurance', 'a1438e3eef101e23d61f0fd7889272098e50f9f6'),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('economics', type=Path)
    parser.add_argument('warehouse', type=Path)
    parser.add_argument('--case', choices=PINS)
    args = parser.parse_args()
    lock = json.loads((ROOT / 'sources.lock.json').read_bytes())
    for key in PINS:
        if args.case and args.case != key:
            continue
        repository, revision = PINS[key]
        source = getattr(args, key)
        read = lambda path: subprocess.check_output(['git', '-C', str(source), 'show', revision + ':' + path])
        revisions = {}
        if key == 'economics':
            paths = {'scenario.json': 'fixtures/enterprise/multibrand-2026.json',
                     'decision.json': 'docs/evidence/enterprise/acceptance/decision.json',
                     'acceptance.json': 'docs/evidence/enterprise/acceptance/verification.json',
                     'http-summary.json': 'docs/evidence/execution/acceptance/execution/summary.json',
                     'accounting-source.py': 'src/stack_economics/enterprise/accounting.py',
                     'contract-source.py': 'src/stack_economics/enterprise/contract.py'}
            summary = json.loads(read(paths['http-summary.json']))
            for trial in summary['trials']:
                if 'result' in trial:
                    paths['http/' + trial['name'] + '-result.json'] = 'docs/evidence/execution/acceptance/execution/' + trial['name'] + '/result.json'
            # Two independent receiver journals are enough for exact receipt/request drilldown.
            for name in ('normal', 'transient-recovery'):
                paths['http/' + name + '-journal.txt'] = 'docs/evidence/execution/acceptance/execution/' + name + '/observations.json.gz'
            case, checker = 'economics-integration', economics
            limitations = ['All annual demand and USD prices are synthetic planning inputs, not vendor quotes or commercial savings.',
                           'Annual architecture calculations and bounded local HTTP trials are separate execution sets. No enterprise-scale load test or native vendor integration is claimed.',
                           'Hourly modeled capacity assumes balanced within-hour emission and declared route lag; it does not establish queue-tail, strict rolling-arrival or production SLA guarantees.']
        else:
            base = 'docs/evidence/warehouse-review/'
            paths = {name: base + path for name, path in {
                'native.json': 'native-readonly/acceptance.json', 'model-results.json': 'native-readonly/model-results.json',
                'source-results.json': 'native-readonly/source-results.json', 'jobs.json': 'native-readonly/job-statistics-results.json',
                'guard.json': 'local/guard-observations.json', 'local.json': 'local/complete-oracle-acceptance.json',
                'application.json': 'local/application-verification.json', 'access.json': 'access-assessment.json'}.items()}
            native, local = json.loads(read(paths['native.json'])), json.loads(read(paths['local.json']))
            for path in set(native['source_sha256']) | set(local['source_sha256']):
                paths[path] = path
            # Reports are immutable: retain source bytes from their recorded execution revision
            # when a later verifier-only fix changed the current-main file.
            for record in (native, local):
                for path, digest in record['source_sha256'].items():
                    if hashlib.sha256(read(path)).hexdigest() != digest:
                        revisions[path] = record['source_revision']
            for name in ('warehouse_models_preview', 'warehouse_source_oracle', 'warehouse_job_metadata'):
                paths['bigquery/' + name + '.sql'] = 'bigquery/' + name + '.sql'
            case, checker = 'warehouse-verification', warehouse
            limitations = ['Native read-only SELECT bodies and an independent source query ran on a purchase-user cohort of one public obfuscated GA4 shard; not a production GA4 export.',
                           'Native dbt compilation, build and MERGE were not executed. Browser authentication is not SDK authentication; the recorded billing-disabled sandbox excludes DML.',
                           'Local synthetic dbt correction, late-arrival, replay and complete-oracle checks are a separate execution. Snapshot event keys do not establish cross-export correction identity.']
        data, entries = {}, []
        for name, path in sorted(paths.items()):
            blob_revision = revisions.get(path, revision)
            original = subprocess.check_output(['git', '-C', str(source), 'show', blob_revision + ':' + path])
            content = base64.b64encode(original) if path.endswith('.gz') else original
            data[name] = content
            entries.append(dict(file=name, source_path=path, sha256=hashlib.sha256(content).hexdigest(),
                                source_sha256=hashlib.sha256(original).hexdigest(),
                                encoding='base64-gzip' if path.endswith('.gz') else 'original',
                                blob_revision=blob_revision,
                                source_url=f'https://github.com/{repository}/blob/{blob_revision}/{path}'))
        upstream = dict(repository=repository, import_revision=revision, artifacts=entries,
                        execution_note='Imported committed records; importing and offline inspection do not repeat source execution.')
        lock['sources'][key] = dict(repository=repository, commit=revision)
        lock.setdefault('integration_imports', {})[case] = upstream
        write_json(ROOT / 'sources.lock.json', lock)
        LOCK.update(lock)
        parsed = {n: json.loads(b) if n.endswith('.json') else b.decode() for n, b in data.items()}
        parsed['upstream.json'] = upstream
        projection = checker(parsed)
        data.update({'upstream.json': upstream, 'projection.json': projection,
                     'observation.json': {'scope': 'Read-only recorded evidence inspection', 'new_native_execution': False, 'new_source_execution': False},
                     'timeline.json': [{'action': k.replace('_', ' '), 'body': v} for k, v in projection.items()]})
        dest = ROOT / 'web/evidence' / case
        if dest.exists():
            raise FileExistsError('Preserve existing capture; import into a new version instead')
        manifest = seal(dest, case, key, data, 'recorded', limitations)
        manifest['input_hashes'] = {e['file']: e['sha256'] for e in entries}
        manifest['reproduce'] = ['python scripts/import_economics_warehouse.py <economics-checkout> <measurement-checkout>',
                                 'python -m revenue_lab.cli verify web/evidence/' + case]
        write_json(dest / 'bundle.json', manifest)
        print(case, len(entries), revision)


if __name__ == '__main__':
    main()
