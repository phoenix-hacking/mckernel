"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure retained-file/AST consumer checks. Never import or call a runtime producer.
"""
from pathlib import Path
import ast
import hashlib
import json

HERE = Path(__file__).resolve().parent


def reference(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def checked(row):
    assert type(row) is dict and set(row) == {'path', 'bytes', 'sha256'}
    assert reference(row['path']) == row, row['path']
    return Path(row['path'])


def literals(path):
    found = {}
    for node in ast.parse(Path(path).read_bytes()).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try:
                found[node.targets[0].id] = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                pass
    return found


def main():
    subject_map = json.loads((HERE/'SUBJECT-MAP.SOURCE-ONLY.json').read_bytes())
    subjects = subject_map['subjects']
    for row in subjects.values():
        checked(row)
    static = json.loads(checked(subjects['static']).read_bytes())
    bridge = literals(checked(subjects['consumer:root_once_startup_entry.py']))
    capture = literals(checked(subjects['consumer:capture_fresh_startup_resource.py']))
    current = literals(checked(subjects['observer']))
    assert static['nonce'] == bridge['NONCE'] == '6b4696fd4f4ebe3b8bcae3cd3406bd37'
    assert bridge['STATIC_SHA'] == subjects['static']['sha256']
    assert capture['OBSERVER_REF'] == static['current_observer_source'] == subjects['observer']
    assert current['CURRENT']['ledger'] == subjects['root61']
    assert current['PINS']['current60_source'] == subjects['current60_source']
    pins = json.loads(checked(subjects['current60_pins']).read_bytes())
    assert pins['common'] == subjects['recursive_common']
    assert pins['common_dependencies'] == subjects['recursive_common_dependencies']
    deps = json.loads(checked(pins['common_dependencies']).read_bytes())
    assert deps['account_window_guard_configuration'] == subjects['recursive_guard_configuration']
    assert deps['physical_history_configuration'] == subjects['recursive_physical_configuration']
    acceptance = json.loads(checked(subjects['independent_retained_stage_acceptance']).read_bytes())
    assert acceptance['decision'] == 'PASS_INDEPENDENT_ACTUAL_ORIGINAL227_RETAINED_STAGE_ARCHIVE_FULLMAP'
    assert acceptance['actual_source_manifest'] == static['offline_manifest']
    assert acceptance['actual_scratch_manifest'] == static['manifest']
    assert acceptance['actual_kernel']['sha256'] == static['expected_new_image_sha256']
    assert acceptance['actual_profile']['positive_wait4_join'] is True
    assert acceptance['actual_profile']['returncode'] == 0
    for key in ['actual_full_readback_result', 'actual_once_claim', 'actual_child_started',
                'actual_child_join', 'actual_stdout', 'actual_stderr']:
        checked(acceptance[key])
    assert subject_map['runtime_authority'] is None
    assert subject_map['matching_CURRENT116_native_acceptance'] is False
    for path in HERE.glob('*.TEMPLATE.NOT-AUTHORITY.json'):
        raw = json.loads(path.read_bytes())
        assert raw.get('runtime_authority') is None
    # Explicitly prove the old recursive runtime binding is a blocker, not new authority.
    old_guard = literals(checked(subjects['historical_shared_guard']))
    assert old_guard['THREAD'] == '01a18111-26a7-7ef2-bbd6-e33d1c8dc803'
    assert old_guard['THREAD'] != subject_map['actual_parent_identity']['thread_id']
    assert subject_map['effective_cutoff_ceilings'][1] < static['fixed_cutoffs'][1]
    # A bad byte reference must be rejected without importing the referenced source.
    bad = dict(subjects['observer'], sha256='0'*64)
    try:
        checked(bad)
    except AssertionError:
        pass
    else:
        raise AssertionError('tampered source reference was accepted')
    print(json.dumps(dict(decision='PASS_RETAINED_SUBJECT_AND_CONSUMER_SHAPES_SOURCE_ONLY',
                         source_subjects=len(subjects), groups=6, runtime_authority=None,
                         runtime_imports=0, guard_calls=0, observations=0, nonce_calls=0,
                         producer_runs=0, readback_replays=0, native_calls=0)))


if __name__ == '__main__':
    main()
