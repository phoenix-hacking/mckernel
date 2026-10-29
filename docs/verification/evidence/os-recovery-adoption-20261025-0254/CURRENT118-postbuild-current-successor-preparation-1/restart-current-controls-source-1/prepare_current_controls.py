"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Mechanical source/data constructor only. Never imports guardian or cleanup modules.
"""
import argparse
import ast
import copy
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent
SOURCE2 = HERE.parent / 'source-2'
SOURCE1 = HERE.parent / 'source-1'
ACTUAL = BASE / 'restart-adoption-20261029T0234'
NEWSC = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/new-run-until-20261028-2300-pacific-1/restart-20261028-1930-pacific-1')
STATE = Path('/home/holden/mckernel/.git/os-autopilot/state.json')
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
PINS = {
    'observer': (SOURCE2 / 'observe_current64_current118_postjoin.py', 'd216adacf568e3e13c70bc8877a0e6a5af6713dad0c60044b03b87091e03ecfd'),
    'inputs': (SOURCE2 / 'INPUTS.json', '4bd01a601ff4a8293da6a59955da79dfde6f37ab0963b95202dd49425f00a71a'),
    'shared_guard': (SOURCE1 / 'operation_window_guard64.py', '1d62a322620e24b8e25fb140eb60eda64c7356b3d5f1cdc616cc4b3c82e10db0'),
    'custody': (ACTUAL / 'ROOT-CUSTODY-SUPPLEMENT.ACTUAL.json', '90a0ccf3d1293697e21ee5e9bf0eb2244268eee84ffbf970990e7f69a0fe609a'),
    'ledger': (ACTUAL / 'ROOT-CURRENT-NONCE-LEDGER64.SUPPLEMENTED.PENDING.json', '3932659c13ba04997870e1d67b2a356b0205e699951a959dd6fdac4ddc7694ff'),
    'custody_validation': (ACTUAL / 'ACTUAL-CUSTODY-PURE-VALIDATION.json', 'b8e5be77b605fb69a8199d624cbda0b106667e3a8caa3bae793d298f5c3c4488'),
}
FIELDS = {'schema','scope','guardian','guardian_review','armed_receipt','cleanup_executor','cleanup_bindings','cleanup_runtime_files','cleanup_source_ready','cleanup_source_review','thread_id'}

def need(ok, why):
    if not ok:
        raise ValueError(why)

def ref(path):
    path = Path(path)
    need(path.is_absolute() and path.is_file() and not path.is_symlink(), 'absolute regular byte input')
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def auth(row):
    need(type(row) is dict and set(row) == {'path','bytes','sha256'}, 'exact byte reference')
    need(ref(row['path']) == row, 'exact unchanged input bytes')
    return Path(row['path'])

def checked(row):
    return json.loads(auth(row).read_bytes())

def contains(value, row):
    if value == row:
        return True
    if isinstance(value, dict):
        return any(contains(v, row) for v in value.values())
    if isinstance(value, list):
        return any(contains(v, row) for v in value)
    return False

def review_binds(value, rows):
    need(value.get('independent') is True and value.get('implementation_ownership') is False
         and str(value.get('decision','')).startswith('PASS'), 'independent reviewed source binding')
    need(all(contains(value, row) for row in rows), 'review authenticates every supplied source')

def rewrite_guard(source, guardian, thread_id):
    tree = ast.parse(source)
    old = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id in ('GUARDIAN_SOURCE', 'THREAD'):
                old[node.targets[0].id] = node
    need(set(old) == {'GUARDIAN_SOURCE','THREAD'}, 'exact two shared guard assignments')
    lines = source.splitlines(True)
    for name, value in [('GUARDIAN_SOURCE', guardian), ('THREAD', thread_id)]:
        node = old[name]
        need(node.lineno == node.end_lineno, 'one-line exact source assignment')
        lines[node.lineno - 1] = name + ' = ' + repr(value) + '\n'
    result = ''.join(lines)
    after = ast.parse(result)
    for before_node, after_node in zip(tree.body, after.body):
        if before_node not in old.values():
            need(ast.dump(before_node, include_attributes=False) == ast.dump(after_node, include_attributes=False), 'all account/window/clock/operation predicates unchanged')
    return result

def replace_refs(value, replacements):
    for before, after in replacements:
        if value == before:
            return copy.deepcopy(after)
    if isinstance(value, dict):
        return {key: replace_refs(v,replacements) for key,v in value.items()}
    if isinstance(value, list):
        return [replace_refs(v,replacements) for v in value]
    return value

def validate_cleanup(pins, manifest):
    old = checked(pins['retirement_bindings'])
    new = checked(manifest['cleanup_bindings'])
    need(set(old) == set(new), 'same cleanup bindings schema')
    for key in old:
        if key not in ('guardian','output_root_parent'):
            need(new[key] == old[key], 'unchanged cleanup boundary ' + key)
    need(new['guardian'] == manifest['guardian'], 'same actual new guardian in cleanup and observer')
    need(new['output_root_parent'] == str(Path(manifest['cleanup_executor']['path']).parent), 'cleanup output root matches its exact successor source directory')
    original = auth(pins['retirement_source']).read_text()
    anchor = "BINDINGS_SHA='" + pins['retirement_bindings']['sha256'] + "'"
    need(original.count(anchor) == 1, 'one exact cleanup binding digest')
    expected = original.replace(anchor, "BINDINGS_SHA='" + manifest['cleanup_bindings']['sha256'] + "'")
    need(auth(manifest['cleanup_executor']).read_text() == expected, 'cleanup code differs only in binding digest')
    old_runtime = checked(pins['compatibility_runtime_files'])
    new_runtime = checked(manifest['cleanup_runtime_files'])
    expected_runtime = dict(old_runtime, executor=manifest['cleanup_executor'], bindings=manifest['cleanup_bindings'], guardian=manifest['guardian'])
    need(len(new_runtime) == 12 and new_runtime == expected_runtime, 'same12 cleanup runtime subjects, only3 exact reference successors')
    for row in new_runtime.values():
        auth(row)
    checked(manifest['cleanup_source_ready'])
    review_binds(checked(manifest['cleanup_source_review']), [manifest['cleanup_executor'],manifest['cleanup_bindings'],manifest['cleanup_runtime_files']])

def validate_manifest(manifest, pins):
    need(set(manifest) == FIELDS and manifest['schema'] == 'mckernel.current118.postjoin-control-source-inputs.v1'
         and manifest['scope'] == SCOPE, 'exact explicit source-only input manifest')
    for key in FIELDS - {'schema','scope','thread_id'}:
        auth(manifest[key])
    need(manifest['armed_receipt']['path'] == str(NEWSC / 'ACTUAL-CONTROLS-ARMED.json'), 'actual current arm receipt required')
    state = json.loads(STATE.read_bytes())
    need(manifest['thread_id'] == state['thread_id'] and manifest['thread_id'] != '01a183ec-72e5-7400-8f48-b4efb8725520', 'actual new launcher thread identity')
    budget = state['credit_budget']
    need(str(budget['id']) == '7f4af94a83b14cc08f97401f5891d965', 'same original cumulative credit run')
    need(manifest['guardian'] != pins['guardian'], 'new reviewed current guardian required')
    tree = ast.parse(auth(manifest['guardian']).read_bytes())
    need(any(isinstance(n, ast.FunctionDef) and n.name == 'guard' and not n.args.args for n in tree.body), 'existing no-argument guard API')
    review_binds(checked(manifest['guardian_review']), [manifest['guardian']])
    validate_cleanup(pins, manifest)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, required=True)
    parser.add_argument('--inputs-sha256', required=True)
    args = parser.parse_args()
    supplied = ref(args.inputs)
    need(supplied['sha256'] == args.inputs_sha256, 'explicit immutable constructor input digest')
    refs = {}
    for key,(path,digest) in PINS.items():
        row = ref(path)
        need(row['sha256'] == digest, 'unchanged retained ' + key)
        refs[key] = row
    pins = checked(refs['inputs'])
    manifest = checked(supplied)
    validate_manifest(manifest,pins)
    old_observer = auth(refs['observer']).read_text()
    old_shared = auth(refs['shared_guard']).read_text()
    new_shared = rewrite_guard(old_shared,manifest['guardian'],manifest['thread_id'])
    outputs = ['observe_current64_current118_postjoin.py','operation_window_guard64.py','INPUTS.json','CONTROL-SOURCE-CONSTRUCTION.json','ROOT64-RUNTIME-BINDINGS.ACTUAL-CUSTODY.TEMPLATE.NOT-AUTHORITY.json','MINIMAL-DIFF.patch']
    need(not any((HERE/name).exists() for name in outputs), 'never overwrite existing materialization')
    # All authentication and scope checks precede first write. Exclusive creation
    # leaves any interrupted construction retained; this is never an execution grant.
    for name,text in [('observe_current64_current118_postjoin.py',old_observer),('operation_window_guard64.py',new_shared)]:
        with (HERE/name).open('x') as stream:
            stream.write(text)
    newpins = copy.deepcopy(pins)
    changes = dict(guardian=manifest['guardian'],shared_guard=ref(HERE/'operation_window_guard64.py'),retirement_source=manifest['cleanup_executor'],retirement_bindings=manifest['cleanup_bindings'],compatibility_runtime_files=manifest['cleanup_runtime_files'],compatibility_source_ready=manifest['cleanup_source_ready'])
    newpins.update(changes)
    with (HERE/'INPUTS.json').open('x') as stream:
        stream.write(json.dumps(newpins,indent=2)+'\n')
    binding = checked(ref(SOURCE2/'ROOT64-RUNTIME-BINDINGS.TEMPLATE.NOT-AUTHORITY.json'))
    binding.update(ledger=refs['ledger'],custody_supplement=refs['custody'])
    with (HERE/'ROOT64-RUNTIME-BINDINGS.ACTUAL-CUSTODY.TEMPLATE.NOT-AUTHORITY.json').open('x') as stream:
        stream.write(json.dumps(binding,indent=2)+'\n')
    with (HERE/'MINIMAL-DIFF.patch').open('x') as stream:
        for old,new,name in [(auth(refs['inputs']).read_text(),json.dumps(newpins,indent=2)+'\n','INPUTS.json'),(old_shared,new_shared,'operation_window_guard64.py')]:
            stream.writelines(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='retained/'+name,tofile='successor/'+name))
    receipt = dict(scope=SCOPE,status='SOURCE_ONLY_SUCCESSOR_REQUIRES_INDEPENDENT_REVIEW_NO_EXECUTION',runtime_authority=None,constructor_inputs=supplied,retained=refs,explicit_new_sources=manifest,observer=ref(HERE/'observe_current64_current118_postjoin.py'),inputs=ref(HERE/'INPUTS.json'),shared_guard=ref(HERE/'operation_window_guard64.py'),changed_INPUTS_fields=sorted(changes),changed_shared_guard_assignments=['GUARDIAN_SOURCE','THREAD'],observer_source_byte_identical=True,actual_custody=refs['custody'],actual_supplemented_pending_ledger=refs['ledger'],historical_pending_ledger_pin_unchanged=pins['pending_ledger'],original389_rejection_unchanged=True,compiler_guard_cleanup_proc_capture_calls=0)
    with (HERE/'CONTROL-SOURCE-CONSTRUCTION.json').open('x') as stream:
        stream.write(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__ == '__main__':
    main()
