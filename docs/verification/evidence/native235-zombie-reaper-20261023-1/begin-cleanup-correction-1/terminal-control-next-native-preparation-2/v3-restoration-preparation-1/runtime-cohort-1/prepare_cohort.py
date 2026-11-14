"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast, hashlib, json, difflib

D = Path(__file__).resolve().parent
E = Path('/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/begin-cleanup-correction-1/terminal-control-next-native-preparation-2/v3-restoration-preparation-1/runtime-cohort-1')
CURRENT = Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/observer227-successor-2/runtime')
OLD = D.parent.parent/'runtime-first-restoration-1'
HOOK = D.parent/'consumer-correction-1'
ND = D.parent/'runtime-first-restoration-1/native_diagnostic.py'
RESOURCE = Path('/home/holden/mckernel-work/host-preparation/native-second-stop-case-preparation-20261021-1/current053d-normalization-runtime-preparation-1/runtime-source-1')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
def function(source, name):
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name)
    return ast.get_source_segment(source, node)
def assignment(source, name):
    return next(n for n in ast.parse(source).body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
def replace_assignment(source, name, value):
    node = assignment(source, name)
    return source.replace(ast.get_source_segment(source, node), name + ' = ' + repr(value), 1)

assert sha(OLD/'native_diagnostic_container_owner.py') == '46471eb6f40e573a78459a5f8717a47ebfeebae1dab772684af80930fdf1fb34'
assert sha(OLD/'native_diagnostic_runner.py') == '0d2e96db1e2ac8f332c6690460fd2b8e81e37ac921994b6b03e6c66ca8b59cad'
assert sha(CURRENT/'native_diagnostic_container_owner.py') == '251acc456d5c7f6b563cb8e41feeb7e095c8098c1a780c44338f2157d357b0e6'
assert sha(CURRENT/'native_diagnostic_runner.py') == '25ea29f9b07232094e9df1db6094ad0a85ec678281749a1d6998abb7c700d499'
assert sha(ND) == '059c40c95b2306265f21bce2a77c49edc7baeb4792e977b189770fc0d21685f1'
assert sha(HOOK/'case_evaluator.py') == '69f5f5405c9f2bf605f0b02412e22e508e9cf117108a13914387ae5b03e8a864'

for name in ('native_diagnostic_backend.py', 'qmp_capture.py'):
    (D/name).write_bytes((CURRENT/name).read_bytes())
(D/'native_diagnostic.py').write_bytes(ND.read_bytes())
runner_before = (CURRENT/'native_diagnostic_runner.py').read_text()
runner = runner_before.replace('import argparse\n', 'import argparse\nimport hashlib\n', 1)
hook = function((OLD/'native_diagnostic_runner.py').read_text(), '_bind_m05')
hook = hook.replace('250a4d16d67f733331b0242cb62e55ecfadef702f2607caa546144197cf74422', sha(ND))
hook = hook.replace(str(OLD/'case_evaluator.py'), str(HOOK/'case_evaluator.py'))
hook = hook.replace('8049e5d3ee121f5c99ef06c08a3de4f03e90adaefddd208d6d432dc5186e4e7e', sha(HOOK/'case_evaluator.py'))
marker = 'def _canonical_file(value, label):'
assert runner.count(marker) == 1
runner = runner.replace(marker, hook + '\n\n\n' + marker, 1)
marker = '    manifest = diagnostic.load_manifest(str(manifest_path))'
assert runner.count(marker) == 1
runner = runner.replace(marker, marker + '\n    _bind_m05(diagnostic, manifest, manifest_path)', 1)
(D/'native_diagnostic_runner.py').write_text(runner)

owner_before = (CURRENT/'native_diagnostic_container_owner.py').read_text()
owner = owner_before
old_rows = ast.literal_eval(assignment(owner, 'SOURCE_HASHES').value)
historical = {path: value for path, value in old_rows.items() if not path.startswith(str(CURRENT) + '/')}
assert len(old_rows) == 139 and len(historical) == 135
rows = dict(historical)
typed_paths = [D/name for name in ('native_diagnostic.py', 'native_diagnostic_runner.py', 'native_diagnostic_backend.py', 'qmp_capture.py')]
typed_paths += [HOOK/name for name in ('case_evaluator.py', 'second_stop_capture.py', 'reboot_workload_capture.py')]
typed_paths += [ND, RESOURCE/'native_resource_reboot_sequence.py', RESOURCE/'two-generation-namespace-4/reboot_capture.py', Path('/home/holden/mckernel/scripts/application-tests/native_diagnostic.py'), Path('/home/holden/mckernel/scripts/application-tests/native_diagnostic_lifecycle_capture.py'), Path('/home/holden/mckernel/scripts/application-tests/native_resource_release_capture.py'), Path('/home/holden/mckernel-work/scratch/native-resource-release-collector-20261017-1/transport-correction1/resource_capture.py')]
typed = {}
for path in typed_paths:
    typed[str(path)] = sha(path)
    if str(path) in rows:
        assert rows[str(path)] == typed[str(path)]
    rows[str(path)] = typed[str(path)]
owner = replace_assignment(owner, 'SOURCE_HASHES', rows)
owner = replace_assignment(owner, 'RUNNER', str(D/'native_diagnostic_runner.py'))
owner = replace_assignment(owner, 'SELF', str(D/'native_diagnostic_container_owner.py'))
roots = ast.literal_eval(assignment(owner, 'EXTRA_READONLY').value)
added_roots = [str(D.parent), str(RESOURCE)]
for path in added_roots:
    if path not in roots:
        roots.append(path)
owner = replace_assignment(owner, 'EXTRA_READONLY', roots)
old_function = function(owner, 'bound_manifest')
new_function = function((OLD/'native_diagnostic_container_owner.py').read_text(), 'bound_manifest')
new_function = new_function.replace(str(OLD/'native_diagnostic.py'), str(D/'native_diagnostic.py')).replace(str(OLD/'case_evaluator.py'), str(HOOK/'case_evaluator.py'))
owner = owner.replace(old_function, new_function, 1)
(D/'native_diagnostic_container_owner.py').write_text(owner)
# Every ownership/acquisition/normal-cleanup method remains AST-identical.
def bodies(source, excluded=()):
    return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(source).body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name not in excluded}
assert bodies(owner_before, ('bound_manifest',)) == bodies(owner, ('bound_manifest',))
original_runner = ast.parse(runner_before)
for node in original_runner.body:
    if isinstance(node, ast.FunctionDef) and node.name != 'run':
        assert function(runner_before, node.name) == function(runner, node.name)
assert function(runner_before, 'run') == function(runner, 'run').replace('\n    _bind_m05(diagnostic, manifest, manifest_path)', '', 1)
for name, before in [('native_diagnostic_container_owner.py', owner_before), ('native_diagnostic_runner.py', runner_before)]:
    (D/(name+'.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(True), (D/name).read_text().splitlines(True), fromfile='current-reviewed/'+name, tofile='M05-hook-successor/'+name)))
manifest = D.parent/'actual-stage-1/manifest.json'
assert sha(manifest) == '8c03e5570b98a99db009f74f6dea9bf27ad9f046abeeea44d66ec561cbe708d7'
cohort = {'scope': __doc__, 'status': 'PRIVATE_COHERENT_M05_HOOK_READY_PENDING_ORDINARY_FIXTURES_AND_ROOT_RELEASE', 'runtime_sources': {str(D/name): {'sha256': sha(D/name), 'bytes': (D/name).stat().st_size} for name in ('native_diagnostic_container_owner.py', 'native_diagnostic_runner.py', 'native_diagnostic.py', 'native_diagnostic_backend.py', 'qmp_capture.py')}, 'typed_hook_source_entries': typed, 'historical_source_rows_reused_without_rehash': historical, 'historical_count': len(historical), 'source_map_count': len(rows), 'added_readonly_roots': added_roots, 'ownership_normalcleanup_other_function_AST_identical': True, 'actual_manifest': {'path': str(manifest), 'sha256': sha(manifest)}, 'required_root_manifest_publication': '/home/holden/mckernel-work/scratch/nm05p5a1/m.json', 'runtime_release': None, 'actual227_acceptance': None, 'first_restoration_native_result': None, 'first_restoration_physical_acceptance': None}
(D/'EXACT-M05-RUNTIME-COHORT.json').write_text(json.dumps(cohort, indent=2)+'\n')
for q in D.iterdir():
    if q.is_file():
        (E/q.name).write_bytes(q.read_bytes())
print(json.dumps({'runtime_sources': cohort['runtime_sources'], 'source_map_count': len(rows), 'historical_count': len(historical)}))
