"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only source/data reconciliation and pure operation checks. No live guard.
"""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

E = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
P = E / 'bfd-default-control-routing-restart-20261028-1'
OLD = E / 'm15-bfd-default-next-integration-source-20261028-1/new-window-producer-cohort-source-1/latest-root61-consumer-successor-source-1'
HERE = Path(__file__).resolve().parent
OP = E / 'restart-adoption-20261028T1911/BFD-FINAL-INTEGRATION-1/EXPLICIT-BFD-OPERATION-SUCCESSOR.json'
CAPS = [1793253600.0, 1035704.5689393478, 1051042.6959879305]

def ref(path):
    raw = Path(path).read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def read(path):
    return json.loads(Path(path).read_bytes())

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def exact(reference):
    assert ref(reference['path']) == reference, reference['path']

assert ref(P / 'SOURCE-READY.json')['sha256'] == 'b01f04bf20e206be83fbce4b8856736d84c5e3e32524bbb6d226a706bbea2577'
ready = read(P / 'SOURCE-READY.json')
for item in ready['files']:
    exact(item)
for key in ['source_delta', 'minimal_diff', 'initial_failure', 'routing_test_source', 'handoff', 'ordered_commands']:
    exact(ready[key])
for item in ready['root_templates']:
    exact(item)
for check in ready['checks']:
    exact(check['evidence'])
    assert check['returncode'] == 0
delta = read(P / 'SOURCE-DELTA.json')
for item in delta['files']:
    exact(item['source'])
    exact(item['successor'])
    assert item['identical_bytes'] == (Path(item['source']['path']).read_bytes() == Path(item['successor']['path']).read_bytes())

reused = []
for relative, expected_hash in [
    ('bfd-default-restart-independent-review-20261028-1/REVIEW.json', '81402e04bca91db4d46756abd3258361af23177f630c47daf2f549a67ffcc750'),
    ('bfd-default-restart-independent-review-20261028-1/OBSERVER-SCHEMA-REVIEW.json', 'dc7a674761057f62e22bf2c9a3084fdc62d9cb51e0c3921246c42ac34d2ca418'),
    ('bfd-default-restart-independent-review-20261028-1/RESTART-GUARD-REVIEW-1/REVIEW.json', '2ecc7b073f38beee54271c3266edd8c430f69983e323dba4baa694e87c9cf694')]:
    r = ref(E / relative)
    assert r['sha256'] == expected_hash
    reused.append(r)

base_guard = (E / 'restart-operation-guard-source-20261028-1/operation_window_guard.py').read_text()
assert base_guard.replace('E = HERE.parent\n', 'E = Path(' + repr(str(E)) + ')\n') == (P / 'cohort/operation_window_guard.py').read_text()
old_profile = read(OLD / 'root-adopted-dispatch-1/PROFILE.SOURCE-ONLY.json')
new_profile = read(P / 'cohort/PROFILE.SOURCE-ONLY.json')
assert new_profile['fixed_three_clock_cutoffs'] == CAPS
old_profile['fixed_three_clock_cutoffs'] = CAPS
assert old_profile == new_profile
old_contract = read(OLD / 'root-adopted-dispatch-1/CONTRACT.json')
new_contract = read(P / 'cohort/CONTRACT.json')
old_contract['limits'] = CAPS
old_contract['all_controls_minimum_binding'] = new_contract['all_controls_minimum_binding']
assert old_contract == new_contract
exact(new_contract['all_controls_minimum_binding'])
old_runtime = (OLD / 'root-adopted-dispatch-1/runtime_guard.py').read_text()
assert old_runtime.replace('51cd8b9510d8b6ea01e434d68d7932c506e84a099b88291733c4afe576ca620d',
                           '9eefd1469edc42a837d0fa4238475af5d07a1ecca631e9dba987a99cefafdb38') == (P / 'cohort/runtime_guard.py').read_text()
old_common = (OLD / 'actual-entry-coupling-source-1/handoff_common.py').read_text()
assert old_common.replace('1035705.5689454618,1051043.6959931096',
                          '1035704.5689393478,1051042.6959879305') == (P / 'entry/handoff_common.py').read_text()
old_top = (OLD / 'actual-entry-coupling-source-1/observe_bfd_current61.py').read_text()
assert old_top.replace(str(OLD / 'actual-entry-coupling-source-1/observe_bfd_current60_history.py'),
                       str(P / 'entry/observe_bfd_current60_history.py')) == (P / 'entry/observe_bfd_current61.py').read_text()
schema = read(P / 'entry/OBSERVER-SCHEMA.BFD.SOURCE-ONLY.json')
old_schema = read(OLD / 'actual-entry-coupling-source-1/OBSERVER-SCHEMA.BFD.SOURCE-ONLY.json')
assert schema['observer'] == ref(P / 'entry/observe_bfd_current61.py')
old_schema['observer'] = schema['observer']
assert schema == old_schema and len(schema) == 6

runtime = load('review_only_BFD_runtime', P / 'cohort/runtime_guard.py')
shared = load('review_only_BFD_operation_source', P / 'cohort/operation_window_guard.py')
subjects = runtime.subjects()
assert len(subjects) == 12
assert {key for key in subjects if key.startswith('consumer:')} == {
    'consumer:build_only_worker.py', 'consumer:hold_and_run_build_only.py',
    'consumer:operation_window_guard.py', 'consumer:run_build_only.py', 'consumer:runtime_guard.py'}
for item in subjects.values():
    exact(item)
assert ref(OP)['sha256'] == '110ef6f3599a72f93a792a87f6cd7222126768780b6ec6f57bc9bf9db4b6a91f'
successor = read(OP)
assert successor['subjects'] == subjects
assert successor['operation_cutoffs'] == CAPS and successor['runtime_authority'] is None
assert successor['source_owners'] == ['/root', '/root/bfd_route', '/root/restart_guard']
assert successor['minimum_cumulative_spent'] == '22812.3311'
assert successor['actual_control_receipt'] == new_contract['all_controls_minimum_binding']
assert successor['same_window_restart'] == shared.THREAD
exact(successor['guardian']['source'])
review = dict(schema='mckernel.independent-operation-window-review.v1',
              decision='PASS_EXPLICIT_OPERATION_WINDOW_SUCCESSOR', independent=True,
              reviewer='/root/consumer_review', operation='bfd-current-default-two-tools',
              successor=successor, scope=__doc__.splitlines()[0], runtime_authority=None,
              successor_reference=ref(OP), source_ready=ref(P / 'SOURCE-READY.json'),
              source_boundary='Only this exact twelve-subject BFD cohort and additive routing; no live clearance, execution/resource/nonce release or default/native/file acceptance.')
# Deliberately synthetic earlier clocks exercise only the pure checker. They are
# not a measurement or a freshness claim. No guard()/account-state call occurs.
clocks = [1793250000.0, 1030000.0, 1040000.0]
assert shared.validate_operation(successor, review, runtime.OPERATION, subjects, clocks) == tuple(CAPS)
negatives = []
def reject(name, mutate):
    changed = copy.deepcopy(successor)
    mutate(changed)
    changed_review = copy.deepcopy(review)
    changed_review['successor'] = changed
    try:
        shared.validate_operation(changed, changed_review, runtime.OPERATION, subjects, clocks)
    except ValueError as error:
        negatives.append(dict(name=name, result='REJECTED', reason=str(error)))
    else:
        raise AssertionError(name)
reject('looser-BOOT', lambda s: s['operation_cutoffs'].__setitem__(2, CAPS[2] + 1))
reject('old-guardian-reference', lambda s: s['guardian'].__setitem__('source', dict(path='/retired/guardian.py', bytes=1, sha256='0'*64)))
reject('rollback-floor', lambda s: s.__setitem__('minimum_cumulative_spent', '22812.3310'))
reject('changed-source-subject', lambda s: s['subjects']['BFD_contract'].__setitem__('sha256', '0'*64))
reject('reviewer-is-source-owner', lambda s: s['source_owners'].append('/root/consumer_review'))
result = dict(status='PASS_EXACT_SOURCE_ROUTING_AND_ACTUAL_OPERATION_PURE_CHECKS',
              source_ready=ref(P / 'SOURCE-READY.json'), minimal_diff=ref(P / 'MINIMAL-CHANGED-BYTES.diff'),
              source_delta_records=len(delta['files']), reused_reviews=reused,
              operation_reference=ref(OP), operation_subjects=subjects,
              unchanged_producer_commands=new_profile['exact_commands'],
              prior_pure_tests=sum(check['tests'] for check in ready['checks']),
              independent_positive_operation_controls=1, independent_negative_operation_controls=negatives,
              live_guard_calls=0, live_account_calls=0, resource_calls=0, compiler_Docker_native_calls=0,
              new_producer_runs=0, new_native_cases=0, files_closed=0, runtime_authority=None)
(HERE / 'CHECKS.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
(HERE / 'BFD-ACTUAL-OPERATION-WINDOW-REVIEW.json').write_text(json.dumps(review, indent=2, sort_keys=True) + '\n')
schema_review = dict(independent=True, reviewer='/root/consumer_review', implementation_ownership=False,
                    decision='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING',
                    required_decision='PASS_EXACT_OBSERVER_SCHEMA_SOURCE_BINDING',
                    reviewed_observer_schema=ref(P / 'entry/OBSERVER-SCHEMA.BFD.SOURCE-ONLY.json'),
                    runtime_authority=None, scope=__doc__.splitlines()[0],
                    findings=['Only observer reference changes from independently accepted dc7a6747 schema; six fields preserved.',
                              'Current61 source changes only authenticated private current60 source path; typed functions are byte-identical.'])
(HERE / 'OBSERVER-SCHEMA-REVIEW.json').write_text(json.dumps(schema_review, indent=2, sort_keys=True) + '\n')
print(json.dumps(dict(status=result['status'], subjects=len(subjects), source_delta_records=len(delta['files']),
                      independent_negatives=len(negatives), operation_review=ref(HERE / 'BFD-ACTUAL-OPERATION-WINDOW-REVIEW.json'),
                      schema_review=ref(HERE / 'OBSERVER-SCHEMA-REVIEW.json')), sort_keys=True))
