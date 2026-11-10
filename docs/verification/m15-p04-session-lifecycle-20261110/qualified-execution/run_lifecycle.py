#!/usr/bin/python3
"""Frozen ABI-first single-condition baseline/candidate lifecycle qualification."""
import hashlib
import json
import os
from pathlib import Path
import resource
import shutil
import sys
import time

BASE = Path(__file__).resolve().parent
SOURCE = Path('/home/holden/mckernel-work/m15-original-integration-20261110T0708Z/p04-lifecycle-source-max-1')
RUSTC = '/home/holden/mckernel-work/scratch-readonly-20261105/native-exact-rust-nightly-1.95.0-20260218-1/rustup/toolchains/nightly-2026-02-18-x86_64-unknown-linux-gnu/bin/rustc'


def main():
    if sys.argv[1:] != ['--execute']:
        raise RuntimeError('Root-reviewed exact --execute invocation required')
    out = BASE / 'output'
    out.mkdir(exist_ok=False)
    started = time.monotonic()
    owner = None
    results = []
    state = {'phase': 'frozen-bindings', 'argv': None, 'label': None, 'variant': None}
    env = {'PATH': '/usr/bin:/bin', 'LANG': 'C', 'LC_ALL': 'C',
           'CMAKE_BUILD_PARALLEL_LEVEL': '1', 'MAKEFLAGS': '-j1', 'OMP_NUM_THREADS': '1'}

    def bounded(limit):
        left = 150 - (time.monotonic() - started)
        if left <= 0:
            raise TimeoutError('150-second work envelope exhausted')
        return min(limit, left)

    def checked(argv, child_env, limit, label):
        state.update(phase=label, argv=list(argv), label=label)
        previous = len(owner.records)
        completed = owner.run(argv, child_env, BASE, bounded(limit), label)
        if len(owner.records) != previous + 1:
            raise RuntimeError(label + ': exactly one ownership receipt required')
        record = owner.records[-1]
        required = {'label': label, 'status': completed.returncode,
                    'leader_parent_joined': True, 'whole_descendants_joined': True,
                    'streams_closed': True, 'error': None, 'timed_out': False,
                    'leader_group_signalled': False, 'adopted_reaps': [],
                    'adopted_kills': [], 'remaining_direct_children': []}
        bad = [key for key, value in required.items() if key not in record or record[key] != value]
        if type(record.get('leader')) is not int or record['leader'] <= 0:
            bad.append('leader')
        birth = record.get('leader_birth')
        if not isinstance(birth, str) or not birth.isdigit() or int(birth) <= 0:
            bad.append('leader_birth')
        if type(record.get('status')) is not int or type(completed.returncode) is not int:
            bad.append('status_type')
        if completed.args != argv:
            bad.append('returned_argv')
        if bad or completed.returncode != 0:
            raise RuntimeError(label + ': unexpected command/ownership failure: ' + ','.join(bad))
        return completed

    try:
        bindings = json.loads((BASE / 'INPUTS.json').read_text())
        for row in bindings['runtime_files']:
            path = Path(row['path'])
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
                raise RuntimeError('frozen lifecycle input mismatch: ' + str(path))
        abi_binding = json.loads((SOURCE / 'ABI-BINDINGS.SOURCE-ONLY.json').read_text())
        for row in abi_binding['headers']:
            path = Path(row['path'])
            if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
                raise RuntimeError('changed actual ABI header: ' + str(path))
        for variant in ('baseline', 'candidate'):
            d = out / variant
            d.mkdir()
            for name in ('prefix', 'tools', 'control'):
                (d / name).mkdir()
            for tool, original in [('crash', 'controlled_crash_peer.py'), ('uname', 'uname_stub.py')]:
                shutil.copyfile(BASE / 'fixtures' / original, d / 'tools' / tool)
                (d / 'tools' / tool).chmod(0o755)
            (d / 'input').write_bytes(b'synthetic input gate only; not a real vmcore\n')
        sys.path.insert(0, str(BASE))
        from owned_process import Owner
        owner = Owner(out)
        witness = out / 'linux-child-abi-witness'
        checked(['/usr/bin/cc', '-std=c11', '-Wall', '-Wextra', '-Werror',
                 str(BASE / 'fixtures/linux_child_abi_witness.c'), '-o', str(witness)],
                env, 30, 'abi-compile')
        abi_result = checked([str(witness)], env, 5, 'abi-values')
        values = json.loads(abi_result.stdout)
        for key, expected in {'siginfo_bytes': 128, 'siginfo_alignment': 8,
                              'idtype_unsigned32': True, 'pidfd_open': 434,
                              'pidfd_send_signal': 424, 'P_PIDFD': 3,
                              'process_control_calls': 0}.items():
            if values.get(key) != expected:
                raise RuntimeError('actual C ABI witness value mismatch: ' + key)
        (out / 'abi-values.json').write_bytes(abi_result.stdout)
        for variant, relative in [('baseline', 'preimage'), ('candidate', 'source')]:
            state['variant'] = variant
            d = out / variant
            compiler_env = dict(env, VMCORE_INSTALLDIR=str(d / 'prefix'), VMCORE_ARCH='x86_64',
                                VMCORE_CRASH=str(d / 'tools/crash'), VMCORE_PROMPT_TIMEOUT_MS='1000')
            compile_argv = [RUSTC, '--edition=2021', '-C', 'opt-level=2', '-C', 'debuginfo=1',
                            str(SOURCE / relative / 'executer/user/rust/vmcore2mckdump.rs'),
                            '-o', str(out / ('vmcore-' + variant))]
            (d / 'compile-command.json').write_text(json.dumps({'argv': compile_argv,
                    'environment': compiler_env}, indent=2) + '\n')
            checked(compile_argv, compiler_env, 60, variant + '-compile')
            checked(['/usr/bin/python3', '-I', '-B', str(BASE / 'run_case.py'), variant],
                    env, 16, variant + '-controlled-case')
            state['phase'] = variant + '-receipt'
            case = json.loads((d / 'RESULT.json').read_text())
            expected = ('FAIL_EXPECTED_BASELINE_PUBLISHED_WITH_LIVE_DESCENDANT' if variant == 'baseline'
                        else 'PASS_CANDIDATE_NO_OUTER_RESCUE_OR_ADOPTED_CHILD')
            if (case['status'] != expected or case['error'] is not None or case['cleanup_errors']
                    or not case['wrapper_parent_joined'] or case['remaining_direct_children']
                    or not case['subreaper_restored'] or not case['streams_closed']):
                raise RuntimeError(variant + ': controlled lifecycle receipt failed')
            if variant == 'baseline':
                if (len(case['signals']) != 1 or case['signals'][0]['role'] != 'descendant'
                        or len(case['adopted_waits']) != 1
                        or not case['adopted_waits'][0]['positive_adopted_wait']):
                    raise RuntimeError('baseline exact one-pidfd-rescue/positive-wait receipt missing')
            elif case['signals'] or case['adopted_waits']:
                raise RuntimeError('candidate required outer rescue/reap')
            results.append({'variant': variant, 'status': expected,
                            'receipt': str(d / 'RESULT.json')})
        if len(owner.records) != 6:
            raise RuntimeError('exactly six bounded command receipts required')
        summary = {'status': 'PASS_BASELINE_DEFECT_REPRODUCED_AND_CANDIDATE_CONTROLLED_SCOPE',
                   'one_condition_variants': results, 'owner_records': len(owner.records),
                   'ABI_witness_passed_before_runtime': True,
                   'cumulative_children_maxrss_kib': resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                   'elapsed_seconds': time.monotonic() - started, 'real_converter_or_dump': False,
                   'production_acceptance': False, 'original_acceptance_delta': 0}
        (out / 'RESULT.json').write_text(json.dumps(summary, indent=2) + '\n')
        print(json.dumps(summary))
        return 0
    except BaseException as primary:
        try:
            partial = {'status': 'FAIL_UNEXPECTED_OR_UNKNOWN', 'active': state,
                       'error': type(primary).__name__ + ': ' + str(primary),
                       'completed_variants': results,
                       'ownership_path': str(out / 'ownership.json'),
                       'owner_records': len(owner.records) if owner is not None else 0,
                       'elapsed_seconds': time.monotonic() - started,
                       'real_converter_or_dump': False, 'production_acceptance': False}
            (out / 'RESULT.json').write_text(json.dumps(partial, indent=2) + '\n')
        except BaseException as receipt_error:
            try:
                sys.stderr.write('Partial receipt failed: ' + str(receipt_error) + '\n')
            except BaseException:
                pass
        raise


if __name__ == '__main__':
    sys.exit(main())
