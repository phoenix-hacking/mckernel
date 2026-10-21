#!/usr/bin/env python3
"""Finite guard source preparation; no imports of execution authorities.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
import ast
import hashlib
from pathlib import Path

R = Path(__file__).resolve().parent
P = R.parent
OLD = Path('/home/holden/mckernel-work/host-preparation/settid-current-production-link-preparation-20261021-1/owned-fork-pin-successor-1/coupled-current-pin-correction-1')
basis = OLD / 'control-successor-1/native_exact_current_optin_image_guard.py'
raw = basis.read_bytes()
assert hashlib.sha256(raw).hexdigest() == '68820d05f5c6e7cdc726e62d983891f83387706b4d945e2ba991c0762356f97d'
s = raw.decode()
s = s.replace('import argparse\n', 'import argparse\nimport importlib.util\n', 1)
s = s.replace("sys.path.insert(0, '" + str(OLD) + "')\nimport native_rust_exact_mckernel_image_container_owner as image\nfrom native_rust_exact_build_container_owner import CliSignals, Docker, digest, inspect\n", '''# Import the entire exact current private owner, including its authenticated
# private host owner/provenance. Never resolve the retired settid owner by name.
_CURRENT_OWNER = Path(''' + repr(str(P / 'native_rust_exact_mckernel_image_container_owner.py')) + ''')
if hashlib.sha256(_CURRENT_OWNER.read_bytes()).hexdigest() != '533c805e5be249505e3ff0e09508a54bf346421881a99bf96349e2e5b4d7d730':
    raise RuntimeError('current private image owner hash differs')
_spec = importlib.util.spec_from_file_location('native_rust_exact_mckernel_image_container_owner', str(_CURRENT_OWNER))
image = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = image
_spec.loader.exec_module(image)
CliSignals, Docker = image._HOST_OWNER.CliSignals, image._HOST_OWNER.Docker
digest, inspect = image._HOST_OWNER.digest, image._HOST_OWNER.inspect
# Bind helper transitive imports to this same authenticated private runtime.
sys.modules['native_rust_exact_build_container_owner'] = image._HOST_OWNER
sys.modules['native_rust_exact_build_offline'] = image._HOST_OWNER.provenance
''')
oldself = str(basis)
newself = str(R / 'native_exact_current_optin_image_guard.py')
s = s.replace(oldself, newself)
s = s.replace(str(OLD / 'native_rust_exact_mckernel_image_container_owner.py'), str(P / 'native_rust_exact_mckernel_image_container_owner.py'))
s = s.replace(str(OLD / 'native_rust_exact_mckernel_image_offline.py'), str(P / 'native_rust_exact_mckernel_image_offline.py'))
s = s.replace('/home/holden/mckernel-work/host-preparation/settid-current-production-link-preparation-20261021-1/native_rust_exact_build_offline.py', str(P / 'native_rust_exact_build_offline.py'))
s = s.replace('f783466fea0907a7a3e04b761c1e8cea9c61251c2d4b3d6f756920d90b89279c','ea825bb5fd67fb5165d578dfb17831c00c399663f34049d6e132b4c701f994f7')
s = s.replace('58e0845c6706818971522d6873bf1ed4d4f4043e5b9fe2fcb2a54a351015294f','1b584ee5b65f39467c8215bb2fc272e1fb0e9c95ee23e01e16e523a8a551a3fa')
start = s.index('def require_actual_ordinary(')
end = s.index('\n\ndef authenticate(', start)
replacement = '''# Deliberately unresolved. Only bind_guard_source.py may fill these two exact
# externally reviewed references; None can never authorize even source admission.
BINDINGS = None


def require_actual_ordinary(request, request_sha, release, ordinary, acceptance, identity):
    """Genuine new6959 receipt and whole source gates; no compile/image acceptance."""
    if not isinstance(BINDINGS, dict) or set(BINDINGS) != {'runtime_ref', 'basis_ref'}:
        raise RuntimeError('new runtime review and source-bound request remain unbound')
    source_ref = SOURCE_REF
    gates_ref = GATES_REF
    runtime_ref, basis_ref = BINDINGS['runtime_ref'], BINDINGS['basis_ref']
    if (release.get('source_materialization_acceptance') != source_ref or
            release.get('whole_source_gate_acceptance') != gates_ref or
            release.get('runtime_binding_acceptance') != runtime_ref or
            release.get('bound_request_basis') != basis_ref):
        raise RuntimeError('exact new source/whole-gate/runtime/request authority required')
    source, gates, runtime = bound(source_ref), bound(gates_ref), bound(runtime_ref)
    if (acceptance != gates or
            source.get('status') != 'PASS_ACTUAL6959_PRIVATE_SOURCE_RECEIPT_JOURNAL_CLOSED_CAPTURE_ONLY' or
            gates.get('schema') != 'mckernel.root-recorded-independent-whole-source-gate-acceptance.v1' or
            gates.get('status') != 'PASS_WHOLE_OWNED_VALIDATOR_AND_ACTUAL_AFFINITY_SOURCE_GATES_ONLY' or
            gates.get('actual_source_acceptance') != source_ref or
            gates.get('result') != RESULT_REF or gates.get('closed_capture') != VALIDATOR_CAPTURE_REF or
            runtime.get('status') != 'PASS_EXACT_FULL_RUNTIME_ADAPTER_OWNER_AND_REQUEST_BINDINGS_ONLY' or
            runtime.get('implementation_ownership') is not False or not runtime.get('reviewer') or
            runtime.get('reviewed_request_proposal') != basis_ref or
            runtime.get('actual_source_materialization_acceptance') != source_ref or
            runtime.get('actual_coupled_source_gate_acceptance') != gates_ref):
        raise RuntimeError('genuine independent new source/runtime review differs')
    if (release.get('ordinary_result_acceptance') != gates_ref or
            release.get('prerequisites', {}).get('ordinary') != VALIDATOR_CAPTURE_REF or
            ordinary != bound(VALIDATOR_CAPTURE_REF)):
        raise RuntimeError('actual whole-validator closed result required')
    receipt = bound(source['receipt'])
    if (source.get('receipt') != RECEIPT_REF or source.get('closed_capture') != MATERIAL_CAPTURE_REF or
            receipt.get('status') != 'PASS_SOURCE_MATERIALIZATION_ONLY' or
            receipt.get('source') != request.get('source_root') or
            source.get('source_entries') != 6959 or receipt.get('source_entries') != 6959 or
            source.get('tracked_symlinks') != 49 or receipt.get('tracked_symlinks') != 49 or
            source.get('regular_files') != 6910 or receipt.get('regular_files') != 6910):
        raise RuntimeError('exact new source receipt/counts/path differ')
    for key in ('source_derivative_sha256', 'materialization_sha256'):
        if not (source.get(key) == receipt.get(key) == gates.get(key) == request.get(key)):
            raise RuntimeError('reviewed new source derivation/materialization differs')
    accepted = source['source_identity']
    expected_identity = {'path': receipt['source'], 'dev': accepted['device'],
        'inode': accepted['inode'], 'uid': accepted['uid'], 'gid': accepted['gid'],
        'mode': int(accepted['mode'], 8), 'file_type': 16384}
    if (gates.get('source_identity') != accepted or request.get('source_identity') != expected_identity or
            [expected_identity[k] for k in ('dev', 'inode', 'uid', 'gid', 'mode')] != identity):
        raise RuntimeError('actual new source identity differs')
    result = bound(RESULT_REF)
    if (result.get('status') != gates['status'] or result.get('same_current_source') != receipt['source'] or
            any(result.get(k) is not True for k in ('whole_owned_current_positive',
                'whole_owned_genuine_old_pin_refusal', 'whole_affinity_current_source_gates_completed',
                'whole_affinity_genuine_old_pin_refusal', 'entire_modules_imported')) or
            any(result.get(k) is not False for k in ('whole_affinity_function_PASS',
                'whole_affinity_compiler_output_acceptance', 'function_extraction_or_monkeypatch_or_stubs',
                'compiler_root_Docker_lock_lease_materialization'))):
        raise RuntimeError('actual whole source-only validator observations differ')
    # Journal and both actual single-command captures are authenticated by their
    # independently accepted exact references; no synthetic two-command schema.
    journal = source['journal']
    journal_raw = Path(journal['path']).read_bytes()
    if len(journal_raw) != journal['bytes'] or hashlib.sha256(journal_raw).hexdigest() != journal['sha256']:
        raise RuntimeError('actual materialization journal drift')
    for row in (bound(MATERIAL_CAPTURE_REF), ordinary):
        if (row.get('returncode') != 0 or row.get('direct_child_joined') is not True or
                row.get('group_absent') is not True or row.get('closed_streams') is not True or
                row.get('timed_out') is not False or row.get('remaining_group_members') != [] or
                row.get('unexpected_group_members') != [] or row.get('error') is not None or
                row.get('retirement_error') is not None):
            raise RuntimeError('actual source/validator directjoin retirement differs')
        if set(row.get('captures', {})) != {'stdout', 'stderr'}:
            raise RuntimeError('actual source/validator streams differ')
        for stream in row['captures'].values():
            raw = Path(stream['path']).read_bytes()
            if len(raw) != stream['size'] or hashlib.sha256(raw).hexdigest() != stream['sha256']:
                raise RuntimeError('actual source/validator closed capture drift')
    basis = bound(basis_ref)
    # Preserve original finite late backup/device identity boundary.
    expected = dict(basis)
    expected['backup_identity'] = request.get('backup_identity')
    expected['disk_admission'] = dict(basis['disk_admission'])
    for key in ('host_device', 'scratch_device'):
        expected['disk_admission'][key] = request['disk_admission'].get(key)
    if request != expected:
        raise RuntimeError('current request changed outside exact late identity fields')
'''
# Freeze finite evidence pointers, using their actual bytes (not future claims).
import json
refs = {
 'SOURCE_REF': P / 'actual-whole-validators-capture-1/actual-source-acceptance.json',
 'GATES_REF': P / 'ROOT-RECORDED-WHOLE-SOURCE-GATE-ACCEPTANCE.json',
 'RESULT_REF': P / 'WHOLE-ACTUAL-SOURCE-VALIDATOR-RESULT.json',
 'VALIDATOR_CAPTURE_REF': P / 'actual-whole-validators-capture-1/whole.json',
 'MATERIAL_CAPTURE_REF': P / 'actual-materialization-capture-1/whole.json',
 'RECEIPT_REF': P / 'source-materialization-1/materialization-receipt.json',
}
assignments = []
for name, path in refs.items():
    data = path.read_bytes()
    assignments.append(name + ' = ' + repr({'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}))
s = s[:start] + '\n'.join(assignments) + '\n\n' + replacement + s[end:]
ast.parse(s)
# Ensure all non-admission algorithms retain their exact original AST bodies.
a, b = ast.parse(raw), ast.parse(s)
afunc = {n.name: ast.dump(n, include_attributes=False) for n in a.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
bfunc = {n.name: ast.dump(n, include_attributes=False) for n in b.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
assert set(afunc) == set(bfunc)
assert {name for name in afunc if afunc[name] != bfunc[name]} == {'require_actual_ordinary', 'authenticate'}
# authenticate differs only in the two new literal fingerprints.
new_auth = next(n for n in b.body if isinstance(n, ast.FunctionDef) and n.name == 'authenticate')
old_auth = next(n for n in a.body if isinstance(n, ast.FunctionDef) and n.name == 'authenticate')
for n in ast.walk(new_auth):
    if isinstance(n, ast.Constant) and n.value == 'ea825bb5fd67fb5165d578dfb17831c00c399663f34049d6e132b4c701f994f7': n.value = 'f783466fea0907a7a3e04b761c1e8cea9c61251c2d4b3d6f756920d90b89279c'
    elif isinstance(n, ast.Constant) and n.value == '1b584ee5b65f39467c8215bb2fc272e1fb0e9c95ee23e01e16e523a8a551a3fa': n.value = '58e0845c6706818971522d6873bf1ed4d4f4043e5b9fe2fcb2a54a351015294f'
assert ast.dump(new_auth, include_attributes=False) == ast.dump(old_auth, include_attributes=False)
out = R / 'native_exact_current_optin_image_guard.UNBOUND.py'
with out.open('x') as f: f.write(s)
print(json.dumps({'status': 'SOURCE_PREPARATION_ONLY_UNBOUND', 'path': str(out), 'sha256': hashlib.sha256(s.encode()).hexdigest(), 'bytes': len(s.encode()), 'unchanged_other_function_AST': True}, sort_keys=True))
