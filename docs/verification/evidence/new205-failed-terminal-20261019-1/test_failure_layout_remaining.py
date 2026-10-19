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
    first = json.loads((F / 'affected-failure-run-1/status.json').read_bytes())
    assert hashlib.sha256((F / 'affected-failure-run-1/status.json').read_bytes()).hexdigest() == '207998d7b5156ed8d48f3550337c4b5aa8a3b0bcd9cf93ea35d3e870f6790f5d'
    assert first['returncode'] == 1 and first['direct_child_joined'] and first['process_group_absent']
    assert hashlib.sha256((F / 'test_failure_case.py').read_bytes()).hexdigest() == '06255445ddcb8347cbcdd9ffded2f96d4710e9d255ef17861dbc105ed95d47f7'
    cleanup = load('cleanup_failed.py')
    request = json.loads((A / 'image-request.json').read_bytes())
    inspection = json.loads((F / 'failed-owner-terminal-inspection.json').read_bytes())
    command, mounts = cleanup.image_layout(request)
    check(inspection['Config']['Cmd'] == inspection['Args'] == command and inspection['Path'] == '/usr/bin/python3' and inspection['Config']['Entrypoint'] == ['/usr/bin/python3'], 'actual full producer argv exact no remaining suffix')
    actual = sorted((row['Destination'], row['Source'], row['Type'], row['RW']) for row in inspection['Mounts'])
    check(actual == mounts, 'actual full producer mounts exact')
    check('--retained-phase-proof' not in command and '--retained-phase-sha256' not in command, 'remaining phase suffix absent from full producer')
    bad = copy.deepcopy(request)
    bad['jobs'] = request['jobs'] + 1
    check(cleanup.image_layout(bad)[0] != inspection['Config']['Cmd'], 'jobs change breaks actual argv join')
    bad = copy.deepcopy(request)
    bad['toolchain_roots'] = []
    refused(lambda: cleanup.image_layout(bad), 'missing toolchain roots refused')
    tree = ast.parse((F / 'cleanup_failed.py').read_text())
    configure = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'configure')
    start = next(i for i,n in enumerate(configure.body) if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Tuple) and [x.id for x in n.targets[0].elts] == ['config','host'])
    block = configure.body[start:start+7]
    assert len(block) == 7 and isinstance(block[-1],ast.If)
    function = ast.FunctionDef(name='actual_layout_predicate', args=ast.arguments(posonlyargs=[], args=[ast.arg(arg=x) for x in ('item','request','target')], kwonlyargs=[], kw_defaults=[], defaults=[]), body=block, decorator_list=[])
    module = ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[]))
    scope = dict(image_layout=cleanup.image_layout, canonical=cleanup.canonical, Refusal=cleanup.Refusal)
    exec(compile(module,'<exact seven cleanup.configure layout statements>','exec'),scope)
    predicate = scope['actual_layout_predicate']
    target = dict(image_id=inspection['Image'])
    predicate(inspection,request,target);check(True,'actual seven configure profile/mount statements')
    for role in ('prefixed-args','missing-arg','suffixed-arg','wrong-entrypoint','wrong-cap','wrong-mount'):
        bad = copy.deepcopy(inspection)
        if role == 'prefixed-args': bad['Args'] = ['-I','-B'] + bad['Args']
        elif role == 'missing-arg': bad['Args'] = bad['Args'][:-1]
        elif role == 'suffixed-arg': bad['Args'] += ['--retained-phase-proof','/work/remaining-phase-proof.json']
        elif role == 'wrong-entrypoint': bad['Config']['Entrypoint'] = ['/usr/bin/python3','-I']
        elif role == 'wrong-cap': bad['HostConfig']['Memory'] += 1
        else: bad['Mounts'][0]['RW'] = not bad['Mounts'][0]['RW']
        refused(lambda: predicate(bad,request,target),'exact actual configure refusal '+role)
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
    result = dict(status='PASS_ACTUAL_FAILURE_CALLERS_ONLY', checks=checks, count=len(checks), reused_first8=dict(status_sha256='207998d7b5156ed8d48f3550337c4b5aa8a3b0bcd9cf93ea35d3e870f6790f5d', checks=8), root=False, docker=False, copied_logs=False, observed_five=False, full_configure_executed=False, cleanup_authorized=False, physical_release=False, application_acceptance=False)
    with (F / 'fixture-result.json').open('x') as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print('PASS_ACTUAL_FAILURE_CALLERS_ONLY checks=' + str(len(checks)))

if __name__ == '__main__':
    main()
