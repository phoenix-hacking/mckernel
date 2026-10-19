"""Expert-prescribed last-only assertion correction; no earlier checks replayed."""
from pathlib import Path
import ast
import copy
import hashlib
import json

F = Path(__file__).resolve().parent
OLD = Path('/home/holden/mckernel-work/host-preparation/future-four-callback-compiler-preparation-20261019-1/terminal-preparation-1/failure-preparation-1')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def functions(text):
    return {node.name: node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef)}

def main():
    statuses = [('affected-failure-run-1/status.json', '207998d7b5156ed8d48f3550337c4b5aa8a3b0bcd9cf93ea35d3e870f6790f5d', 8), ('affected-failure-run-2/status.json', '64c3da90623090a713d345a426b2a7bf2f12e7cf09397998cec56222a84a6c8d', 15)]
    for name, digest, _ in statuses:
        path = F / name
        assert sha(path) == digest
        status = json.loads(path.read_bytes())
        assert status['returncode'] == 1 and status['direct_child_joined'] and status['process_group_absent']
    for name in ('candidate-source-pins.json', 'candidate-source-pins-correction.json'):
        pins = json.loads((F / name).read_bytes())
        for row in pins.values():
            assert sha(Path(row['path'])) == row['sha256']
    old_text = (OLD / 'cleanup_failed.py').read_text()
    new_text = (F / 'cleanup_failed.py').read_text()
    old, new = functions(old_text), functions(new_text)
    assert set(old) == set(new) and len(old) == 46
    changes = {
        'configure': ('native-rust-future-four-callback-image-guard-20261019-3a34ecb79f00dcc881c0bd58773ca772', 'native-rust-four-callback-affinity-image-guard-bc32500028be40a09ce651f20ade82d4', 2),
        'prepare_release': ('/root/next_live_process_rust_batch', '/root/clone_thread_affinity_rust_repair', 1),
    }
    normalized = copy.deepcopy(new)
    for name, (before, after, count) in changes.items():
        actual = [node for node in ast.walk(new[name]) if isinstance(node, ast.Constant) and node.value == after]
        obsolete = [node for node in ast.walk(new[name]) if isinstance(node, ast.Constant) and node.value == before]
        assert len(actual) == count and not obsolete
        old_values = [node for node in ast.walk(old[name]) if isinstance(node, ast.Constant) and node.value == before]
        assert len(old_values) == count
        replaced = 0
        for node in ast.walk(normalized[name]):
            if isinstance(node, ast.Constant) and node.value == after:
                node.value = before
                replaced += 1
        assert replaced == count
    assert {name: ast.dump(node, include_attributes=False) for name, node in old.items()} == {name: ast.dump(node, include_attributes=False) for name, node in normalized.items()}
    assignments = {node.targets[0].id: node.value for node in ast.parse(new_text).body if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)}
    assert ast.literal_eval(assignments['PUBLISHED_SCRIPT']) == 'docs/verification/evidence/new205-failed-terminal-20261019-1/cleanup_failed.py'
    result = dict(status='PASS_ACTUAL_FAILURE_CALLERS_AND_EXACT_LITERAL_DELTA_ONLY', old_function_count=46, unchanged_function_count=44, exact_guard_literal_replacements=2, exact_author_literal_replacements=1, reused_prior_checks=sum(row[2] for row in statuses), final_checks=3, cumulative_checks=26, prior_failures=[dict(path=str(F / name), sha256=digest) for name, digest, _ in statuses], root=False, docker=False, copied_logs=False, observed_five=False, full_configure_executed=False, cleanup_authorized=False, physical_release=False, application_acceptance=False)
    with (F / 'fixture-result.json').open('x') as stream:
        json.dump(result, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print('PASS_ACTUAL_FAILURE_CALLERS_AND_EXACT_LITERAL_DELTA_ONLY cumulative=26 last=3 reused=23')

if __name__ == '__main__':
    main()
