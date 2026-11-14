"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Data/source materialization adapted from the selected immutable cohort preparer.
No product import, fixture, namespace publication, root command or execution release.
"""
import ast
import copy
import difflib
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent
B = Path('/home/holden/mckernel-work/host-preparation/p12-long-first-round-progress-expert-20261023-1/runtime-sdk8-snapshot-equality-successor-1')
A = D.parent/'qmp-capacity-fix/candidate/scripts/application-tests'
S = D/'source'
CHANGED = ('qmp_capture.py', 'native_diagnostic_backend.py', 'native_diagnostic_runner.py',
           'native_diagnostic.py', 'native_diagnostic_container_owner.py', 'long_transport.py')


def ref(path):
    path = Path(path); raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def emit(name, value):
    (D/name).write_text(json.dumps(value, sort_keys=True, indent=2)+'\n')


def literal(source, name):
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
    return ast.literal_eval(node.value)


def replace(source, name, value):
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == name for t in n.targets))
    return source.replace(ast.get_source_segment(source, node), name+' = '+repr(value), 1)


def functions(source):
    return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(source).body
            if isinstance(n, (ast.FunctionDef, ast.ClassDef))}


S.mkdir(exist_ok=True)
cohort_base = json.loads((B/'COHORT-BINDINGS.json').read_text())
namespace = json.loads((D/'ROOT-NAMESPACE.PENDING.json').read_text())
# Root alone supplies and observes these actual names/identities. Pending None
# values are intentionally not replaced by a prior live nonce or host parent.
for name, pin in cohort_base.items():
    source = A/name if name in CHANGED else B/'source'/name
    (S/name).write_bytes(source.read_bytes())

# The controller embeds owner PATH, never owner HASH: no owner/controller cycle.
controller_old = (B/'capture_root_LONG.NOT-RELEASED.py').read_text()
controller = controller_old
bindings = dict(OWNER_PATH=str(S/'native_diagnostic_container_owner.py'),
                RELEASE_PATH=namespace['release_path'], HOST_PARENT=namespace['host_parent'],
                NONCE=namespace['nonce'], MANIFEST_PATH=namespace['manifest_path'],
                MANIFEST_SHA=namespace['manifest_sha256'])
for key, value in bindings.items():
    controller = replace(controller, key, value)
assert functions(controller) == functions(controller_old)
(D/'capture_root_LONG.NOT-RELEASED.py').write_text(controller)

# Transport binds controller HASH and owner PATH; owner HASH remains external.
told = (S/'long_transport.py').read_text()
host = literal(told, 'HOST_OUTPUT')
host.update(parent=namespace['host_parent'], retention_parent=namespace['host_retention_parent'])
external = literal(told, 'EXTERNAL_CAPTURE_BINDING')
external.update(controller_path=str(D/'capture_root_LONG.NOT-RELEASED.py'),
                controller_sha256=ref(D/'capture_root_LONG.NOT-RELEASED.py')['sha256'],
                request_path=str(D/'CAPTURE-REQUEST.json'),
                capture_directory=str(D/'actual-capture-1'),
                command_source_path=str(S/'native_diagnostic_container_owner.py'))
transport = replace(replace(told, 'HOST_OUTPUT', host), 'EXTERNAL_CAPTURE_BINDING', external)
assert functions(transport) == functions(told)
(S/'long_transport.py').write_text(transport)

# Preserve every nonselected provider/history pin. Replace only the nine active
# predecessor cohort pins; owner never hashes itself or the external cohort map.
owner_old = (S/'native_diagnostic_container_owner.py').read_text()
hashes_old = literal(owner_old, 'SOURCE_HASHES')
preserved = {k: v for k, v in hashes_old.items() if not k.startswith(str(B/'source')+'/')}
hashes = dict(preserved)
for path in sorted(S.iterdir()):
    if path.name != 'native_diagnostic_container_owner.py':
        hashes[str(path)] = ref(path)['sha256']
roots = [str(S) if x == str(B/'source') else x for x in literal(owner_old, 'EXTRA_READONLY')]
owner = replace(replace(replace(replace(owner_old, 'SELF', str(S/'native_diagnostic_container_owner.py')),
                'RUNNER', str(S/'native_diagnostic_runner.py')), 'SOURCE_HASHES', hashes), 'EXTRA_READONLY', roots)
old_diagnostic = str(B/'source/native_diagnostic.py')
owner = owner.replace('    source = '+repr(old_diagnostic),
                      '    source = '+repr(str(S/'native_diagnostic.py')), 1)
before, after = functions(owner_old), functions(owner)
assert [k for k in before if before[k] != after[k]] == ['bound_manifest']
assert before['bound_manifest'].replace(old_diagnostic, 'LOCAL_DIAGNOSTIC') == after['bound_manifest'].replace(str(S/'native_diagnostic.py'), 'LOCAL_DIAGNOSTIC')
assert str(S/'native_diagnostic_container_owner.py') not in hashes
assert all(hashes[k] == v for k, v in preserved.items())
(S/'native_diagnostic_container_owner.py').write_text(owner)
cohort = {p.name: ref(p) for p in sorted(S.iterdir()) if p.is_file()}
assert len(cohort) == 10 and len(hashes) == len(hashes_old) == 287
emit('COHORT-BINDINGS.json', cohort)

request = json.loads((B/'CAPTURE-REQUEST.json').read_text())
argv = request['argv']
for key, value in {'--attempt-parent': namespace['host_parent'], '--nonce': namespace['nonce'],
                   '--manifest': namespace['manifest_path'], '--manifest-sha256': namespace['manifest_sha256'],
                   '--long-profile-release': namespace['release_path'], '--long-profile-release-sha256': None}.items():
    argv[argv.index(key)+1] = value
argv[argv.index(str(B/'source/native_diagnostic_container_owner.py'))] = str(S/'native_diagnostic_container_owner.py')
argv[argv.index('--owner-sha256')+1] = cohort['native_diagnostic_container_owner.py']['sha256']
request.update(command_source=cohort['native_diagnostic_container_owner.py'],
               capture_directory=str(D/'actual-capture-1'),
               wrapper_sha256=ref(D/'capture_root_LONG.NOT-RELEASED.py')['sha256'],
               long_profile_release=dict(path=namespace['release_path'], sha256=None),
               status='UNRELEASED_ROOT_LATE_NAMESPACE_RELEASE_NULL_NO_RUNTIME_AUTHORITY')
emit('PROSPECTIVE-REQUEST-MODEL.NOT-EXECUTABLE.json', request)
emit('CAPTURE-REQUEST.PROTOTYPE.NOT-EXECUTABLE.json', request)
test = copy.deepcopy(request)
test['long_profile_release']['sha256'] = '0'*64
test['argv'][-1] = '0'*64
test['status'] = 'TESTONLY_ROOT_LATE_NAMESPACE_STILL_REQUIRED_NO_RUNTIME_AUTHORITY'
emit('TESTONLY-CORRECTED-REQUEST.json', test)

# Interpret only DATA constants/profile expression; no module/product function
# is imported or executed. The original preparer used the same AST literal step.
profile = copy.deepcopy(json.loads((B/'LONG-RELEASE.PROTOTYPE.ACTUAL-STAGE.NOT-EXECUTABLE.json').read_text())['profile'])
profile.update(host_output=host, qmp_raw_bytes=32*2**20, qmp_ordinary_capture_bytes=128*2**20,
               qmp_recovery_bytes=2*2**20, qmp_recovery_capture_bytes=8*2**20,
               qmp_record_limit=1048576, qmp_recovery_records=4096, qmp_bytes=136*2**20,
               qmp_capture_seconds=10, qmp_readback_seconds=10,
               shared_capture_bytes=640*2**20, logical_growth_bytes=4224*2**20)
release = json.loads((B/'LONG-RELEASE.PROTOTYPE.ACTUAL-STAGE.NOT-EXECUTABLE.json').read_text())
release.update(attempt_parent=namespace['host_parent'], nonce=namespace['nonce'],
               manifest=dict(path=namespace['manifest_path'], sha256=namespace['manifest_sha256']),
               profile=profile, source_sha256={k: cohort[k]['sha256'] for k in release['source_sha256']},
               author=None, boot_id=None, expires_unix=None, independent_review=None)
emit('LONG-RELEASE.PROTOTYPE.NOT-EXECUTABLE.json', release)
emit('LONG-PROFILE.PREPARED.json', profile)

required = set(json.loads((B/'PRECISE-SDK6-CONSUMED-PATHS.json').read_text())['required_paths'])
required = {str(S/Path(x).name) if x.startswith(str(B/'source')+'/') else x for x in required}
required.update(hashes)
if namespace['manifest_path'] is not None:
    required.add(namespace['manifest_path'])
emit('PRECISE-SDK6-CONSUMED-PATHS.json', dict(scope=__doc__, required_paths=sorted(required),
     preserved_nonlocal_provider_history_pins=len(preserved), source_hash_rows=len(hashes),
     runtime_manifest_publication=namespace['manifest_path']))
emit('SOURCE-TO-REQUEST-BINDING-MATRIX.json', dict(scope=__doc__, status='COHERENT_SOURCE_DATA_ROOT_LATE_PARAMETERS_NULL',
     source_hash_rows=len(hashes), readonly_roots=len(roots), historical147unchanged=True,
     preserved_nonlocal_provider_history_pins=len(preserved), selected_runtime_pins=9,
     controller=ref(D/'capture_root_LONG.NOT-RELEASED.py'), controller_functions_AST_identical=True,
     active_module_paths=dict(owner=cohort['native_diagnostic_container_owner.py']['path'],
       runner=cohort['native_diagnostic_runner.py']['path'], diagnostic=str(S/'native_diagnostic.py'),
       backend=str(S/'native_diagnostic_backend.py'), qmp=str(S/'qmp_capture.py')),
     owner_self_hash_cycle=False, runtime_release=None, native_acceptance=False))

# Keep the selected 18-guard fixture and exact consumer. Only rebind its OLD
# historical path and add active runtime module identity assertions to the same
# existing full-manifest check, retaining the original eighteen check count.
fixture = (B/'fixture_actual_controller_guards.py').read_text()
fixture = fixture.replace("OLD=D.parent/'failure-dfbb-docker-start-1/runtime-successor-1'",
    "OLD=Path("+repr(str(B.parent/'failure-dfbb-docker-start-1/runtime-successor-1'))+")", 1)
anchor = "assert m['pair_long_session']==g.PROFILE and len(o.SOURCE_HASHES)==matrix['source_hash_rows']"
addition = '''
# Fresh imports of the actual successor consumer, not only hash-table scanning.
runtime_runner=load(S/'native_diagnostic_runner.py','successor_actual_runner')
runtime_diagnostic,runtime_backend=runtime_runner._runtime()
runtime_paths=dict(diagnostic=runtime_diagnostic.run_diagnostic.__code__.co_filename,
                  backend=runtime_backend.QmpBackend.negotiate.__code__.co_filename,
                  qmp_init=runtime_backend.QmpSession.__init__.__code__.co_filename,
                  qmp_retain=runtime_backend.QmpSession._retain.__code__.co_filename)
assert runtime_paths==dict(diagnostic=str(S/'native_diagnostic.py'),backend=str(S/'native_diagnostic_backend.py'),
                           qmp_init=str(S/'qmp_capture.py'),qmp_retain=str(S/'qmp_capture.py'))
assert g.TRANSPORT==json.loads((D/'LONG-PROFILE.PREPARED.json').read_bytes())
'''
assert anchor in fixture
fixture = fixture.replace(anchor, anchor+addition, 1)
fixture = fixture.replace("checks.append(dict(name='actual_full_bound_manifest_current_and_controller_transport_owner_request_matrix',status='PASS',readonly_roots=len(o.EXTRA_READONLY)))",
    "checks.append(dict(name='actual_full_bound_manifest_current_and_controller_transport_owner_request_matrix',status='PASS',readonly_roots=len(o.EXTRA_READONLY),active_runtime_module_paths=runtime_paths))", 1)
(D/'fixture_actual_controller_guards.py').write_text(fixture)
consumer = (B/'controller_pre_effect_consumer.py').read_text().replace(
    ref(B/'capture_root_LONG.NOT-RELEASED.py')['sha256'], ref(D/'capture_root_LONG.NOT-RELEASED.py')['sha256'])
(D/'controller_pre_effect_consumer.py').write_text(consumer)
driver = (B/'run_actual_guard_fixture_owned.py').read_bytes()
(D/'run_actual_guard_fixture_owned.py').write_bytes(driver)
emit('NEXT-ACTUAL-FIXTURE-ARGV.NOT-RELEASED.json', dict(scope=__doc__,
     status='PREPARED_REQUIRES_ROOT_LATE_NAMESPACE_REFREEZE_AND_FRESH_ORDINARY_GRANT',
     argv=['/home/holden/anaconda3/bin/python3', '-I', '-B', str(D/'run_actual_guard_fixture_owned.py')],
     profile=dict(cpu=[6], AS=2*2**30, CPU=60, wall=90, grace=6, FSIZE=32*2**20, NOFILE=256, core=0),
     source=ref(D/'run_actual_guard_fixture_owned.py'), guard=ref(D/'fixture_actual_controller_guards.py'),
     root_grant=None, actual_fixture=None, full_root_environment_proof=False))
emit('MATERIALIZATION-RESULT.json', dict(scope=__doc__, status='SOURCE_DATA_ONLY_ROOT_LATE_NAMESPACE_NULL',
     reused_preparer=ref(B/'prepare_runtime_snapshot_equality_successor.py'),
     adapted_preparer=ref(Path(__file__)), selected_base_cohort=ref(B/'COHORT-BINDINGS.json'),
     accepted_capacity_source=ref(D.parent/'qmp-capacity-fix/SOURCE-READY.json'),
     cohort_count=10, source_hash_count=287, preserved_nonlocal_count=len(preserved),
     source_hash_owner_excluded=True, controller_transport_owner_order=True,
     namespace=namespace, profile=profile, fixture_executed=False, runtime=False,
     provider_authority_unchanged=ref(S/'CURRENT68-SDK8-AUTHORITY-LINKS.json')))
print(json.dumps(dict(cohort_count=10, selected_runtime_pins=9,
      preserved_nonlocal_pins=len(preserved), runtime=False, fixture=False), sort_keys=True))
