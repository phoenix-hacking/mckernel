"""Functional OS only; no security testing. Pure source/data validation only.

This program never calls admission, reads clocks/account/resources, compiles,
starts a workload, or grants execution.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

D = Path(__file__).resolve().parent


def reference(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())


def check_nulls(value, key=''):
    if value is None:
        assert key in {'Root_grant', 'Root_actual_boundary', 'new227_test_receipts'}, key
    elif isinstance(value, dict):
        for name, child in value.items():
            check_nulls(child, name)
    elif isinstance(value, list):
        for child in value:
            check_nulls(child, key)


def main():
    profile = json.loads((D / 'BOUND-RECIPE.NOT-GRANTED.json').read_bytes())
    source = json.loads((D / 'SOURCE-INPUTS.NOT-GRANTED.json').read_bytes())
    runner = source['runner']
    assert reference(runner['path']) == runner
    assert runner['sha256'] == '6e98a1fbcbce2e822a815a05516287e7122cbd8e06d43277134b27b70cf3ad34'
    spec = importlib.util.spec_from_file_location('retained_source_validation_only', runner['path'])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.validate_profile(profile)
    module.verify(profile['inputs'] + [leaf['plan'] for leaf in profile['leaves']])
    check_nulls(profile)
    check_nulls(source)
    assert len(profile['commands']) == 3
    assert len(profile['expected_test_names']) == len(set(profile['expected_test_names'])) == 26
    old = json.loads(Path(source['retained_profile']['path']).read_bytes())
    assert profile['expected_test_names'] == old['expected_test_names']
    assert profile['resources'] == old['resources'] and profile['fixed_cutoffs'] == old['fixed_cutoffs']
    case = json.loads(Path(profile['caseprofile']['path']).read_bytes())
    review = json.loads(Path(source['source_review']['path']).read_bytes())
    assert review['decision'].startswith('PASS') and source['source_ready']['sha256'] in json.dumps(review)
    assert case['case_id'] == 'P-M01-02-child-SIGTERM-and-exec-recovery-227B'
    assert case['argv'] == ['/bin/mcexec', '-t', '1', '0', '/apps/app']
    assert case['env'] == {'PATH': '/usr/bin:/bin', 'COKERNEL_PATH': '/apps'}
    assert case['cwd'] == '/case/work'
    assert case['startup_boot_argv'] == ['/bin/native-boot', 'hidos', 'allow_oversubscribe']
    assert case['payload_timeout_ms'] == 10000 and case['post_reap_retirement_ms'] == 5000
    assert case['stdout_limit_bytes'] == case['stderr_limit_bytes'] == 1024
    assert case['original_payload']['sha256'] == '6abb5e9046444c64d72139f85fcae9e4796eff7ceb5cc2dd1e5b1a47ef3695a5'
    expected = Path(source['expected_stdout_input']['path']).read_bytes()
    assert len(expected) == 227 and expected == bytes.fromhex(case['oracle']['stdout_hex'])
    assert case['oracle']['stderr_hex'] == '' and case['oracle']['exit_code'] == 0
    assert len(profile['source_inputs']) == len(profile['qualified_generic_source_inputs']) == 8
    for current, prior in zip(profile['source_inputs'], profile['qualified_generic_source_inputs']):
        assert Path(current['path']).name == Path(prior['path']).name
        assert Path(current['path']).read_bytes() == Path(prior['path']).read_bytes()
    output = D / 'future-output-1'
    for command in profile['commands']:
        assert command['cwd'] == source['source_root']
    for command in profile['commands'][:2]:
        assert command['argv'][:2] == ['/usr/bin/env', 'TMPDIR=' + str(output)]
        assert source['compiler']['path'] in command['argv']
    assert profile['commands'][1]['argv'][2] == 'STARTUP_FAKEEXEC_PATH=' + str(output / 'process227-fakeexec')
    assert profile['commands'][2]['argv'] == [str(output / 'process227-tests'), '--test-threads=1']
    assert profile['new227_HOST_status'] == 'UNRUN'
    assert profile['production_recompiled'] is profile['readelf_replayed'] is False
    assert profile['reused_actual_collector_artifact']['sha256'] == 'ab3e775e6a9df8d36bbbb974ddafbb26493c24f1aaf49487f5fc27c5583bed6c'
    assert not output.exists() and not Path(profile['capture_root']).exists()
    print(json.dumps(dict(decision='PASS_SOURCE_DATA_THREE_COMMAND227_PROFILE_ONLY', commands=3,
                          prepared_controls=26, byteexact_generic_modules=8,
                          production_compile_replayed=False, compiler_runtime_guard_queries=0)))


if __name__ == '__main__':
    main()
