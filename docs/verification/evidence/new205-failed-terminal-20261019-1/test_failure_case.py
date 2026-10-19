"""Small actual-caller checks; ordinary saved records only, no root or retention.

Exercises production helper functions directly. It does not execute configure,
observe, copy, export, cleanup, build or a Docker command.
"""
from pathlib import Path
import ast
import copy
import hashlib
import importlib.util
import json

F = Path(__file__).resolve().parent
A = F.parent
checks = []

def load(name):
    path = F / name
    spec = importlib.util.spec_from_file_location('_actual_new205_' + path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def check(ok, name):
    assert ok, name
    checks.append(name)

def refused(action, name):
    try:
        action()
    except (RuntimeError, ValueError, AssertionError):
        checks.append(name)
    else:
        raise AssertionError('accepted invalid input: ' + name)

def main():
    retention = load('retain_failed_logs.py')
    gate = load('failed_operation_authority.py')
    cleanup = load('cleanup_failed.py')
    inputs = json.loads((F / 'FAILED-CASE-INPUTS.json').read_bytes())
    rows = json.loads((F / 'failed-log-original-authorities.json').read_bytes())
    check(retention.validate_artifact_rows(rows) == rows and len(rows) == 12, 'actual twelve finite copy-only log authorities')
    check(all(row['action'] == 'copy' for row in rows), 'no source move or mutation route')
    check(sum(row['original']['size'] for row in rows) < 8 << 20, 'finite actual failed log bytes')
    bad = copy.deepcopy(rows)
    bad.pop()
    refused(lambda: retention.validate_artifact_rows(bad), 'missing log refused')
    bad = copy.deepcopy(rows)
    bad[-1]['retained'] = str(F / 'wrong-destination')
    refused(lambda: retention.validate_artifact_rows(bad), 'retention destination substitution refused')
    bad = copy.deepcopy(rows)
    bad[-1]['action'] = 'reuse'
    refused(lambda: retention.validate_artifact_rows(bad), 'retention action substitution refused')
    review = gate.validate_retirement_evidence(inputs['retirement'])
    check(review['positive_client_retirement'] and not review['physical_retirement_accepted'], 'actual failed retirement evidence without physical release')
    bad = dict(inputs['retirement'], sha256='0' * 64)
    refused(lambda: gate.validate_retirement_evidence(bad), 'retirement review substitution refused')
    request = json.loads((A / 'image-request.json').read_bytes())
    inspection = json.loads((F / 'failed-owner-terminal-inspection.json').read_bytes())
    command, mounts = cleanup.image_layout(request)
    check(inspection['Config']['Cmd'] == command and inspection['Args'] == ['-I', '-B'] + command, 'actual full producer argv exact no remaining suffix')
    actual = sorted((row['Destination'], row['Source'], row['Type'], row['RW']) for row in inspection['Mounts'])
    check(actual == mounts, 'actual full producer mounts exact')
    check('--retained-phase-proof' not in command and '--retained-phase-sha256' not in command, 'remaining phase suffix absent from full producer')
    bad = copy.deepcopy(request)
    bad['jobs'] = request['jobs'] + 1
    check(cleanup.image_layout(bad)[0] != inspection['Config']['Cmd'], 'jobs change breaks actual argv join')
    bad = copy.deepcopy(request)
    bad['toolchain_roots'] = []
    refused(lambda: cleanup.image_layout(bad), 'missing toolchain roots refused')
    source11 = json.loads((A / 'heavy-proposal-1/source-sha256.json').read_bytes())
    actual12 = dict(source11['source_sha256'])
    additional = source11['additional_dispatcher']
    check(len(actual12) == 11 and request['host_owner_path'] in actual12 and additional['path'] not in actual12, 'boot source11 contains declared actual owner')
    actual12[additional['path']] = additional['sha256']
    check(len(actual12) == 12 and all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest for path, digest in actual12.items()), 'actual twelve control source bytes exact')
    raw = cleanup.canonical(dict(status='NOT_RELEASED', observation=None))
    check(not raw.endswith(b'\n') and raw == b'{"observation":null,"status":"NOT_RELEASED"}', 'actual cleanup canonical has no LF')
    old = Path('/home/holden/mckernel-work/host-preparation/future-four-callback-compiler-preparation-20261019-1/terminal-preparation-1/failure-preparation-1')
    def functions(path):
        return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(path.read_text()).body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    check(functions(old / 'cleanup_failed.py') == functions(F / 'cleanup_failed.py'), 'all accepted cleanup function ASTs unchanged')
    check(cleanup.PUBLISHED_SCRIPT.endswith('/new205-failed-terminal-20261019-1/cleanup_failed.py'), 'new publication role explicit')
    check('/root/clone_thread_affinity_rust_repair' in (F / 'cleanup_failed.py').read_text(), 'actual implementation author metadata')
    result = dict(status='PASS_ACTUAL_FAILURE_CALLERS_ONLY', checks=checks, count=len(checks), root=False, docker=False, copied_logs=False, observed_five=False, full_configure_executed=False, cleanup_authorized=False, physical_release=False, application_acceptance=False)
    with (F / 'fixture-result.json').open('x') as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print('PASS_ACTUAL_FAILURE_CALLERS_ONLY checks=' + str(len(checks)))

if __name__ == '__main__':
    main()
