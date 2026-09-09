#!/usr/bin/env python3
"""Capture and check exact futex/time/clone-copy bodies in the pinned container.

Usage: python3 -B /workspace/scripts/tests/run_ultra_futex_clone.py native|compat ATTEMPT
No guest, module load, installation or source mutation occurs in this helper.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys

assert os.getuid() == 1000 and os.sched_getaffinity(0) == {2, 3, 4, 5}
profile, attempt = sys.argv[1:]
assert profile in ('native', 'compat')
assert re.fullmatch(r'[1-9][0-9]*', attempt)
repo = Path('/workspace')
linux = Path('/work/native-source/linux-6.12.0-211.44.1.el10_2')
out = Path('/work/ultra-futex-clone-protocol-20260909-' + profile + '-' + attempt)
out.mkdir()
record = dict(status='RUNNING', profile=profile, started_utc=datetime.now(timezone.utc).isoformat(),
              commands=[], inputs=[], extracted_bodies=[], actual_guest_pass=False,
              scope='Exact pinned Linux time vectors, native checked timeout adapter, exact scheduler/futex countdown bodies with controlled clocks, exact native C clone store blocks and real Rust target-VM copy sequencing with controlled page providers. Instruction faults, real COW and actual applications remain guest obligations.')


def identity(path):
    value = path.read_bytes()
    return dict(path=str(path), size=len(value), sha256=hashlib.sha256(value).hexdigest())


def capture(path, relative):
    target = out / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(path, target)
    record['inputs'].append(dict(original=identity(path), captured=identity(target)))
    return target


def body(path, pattern, name):
    data = path.read_text()
    match = re.search(pattern, data, re.M)
    assert match, (str(path), name)
    start = match.start()
    end = data.index('{', start) + 1
    depth = 1
    while depth:
        depth += (data[end] == '{') - (data[end] == '}')
        end += 1
    value = data[start:end]
    record['extracted_bodies'].append(dict(source=str(path), name=name,
        start_byte=len(data[:start].encode()), end_byte=len(data[:end].encode()),
        sha256=hashlib.sha256(value.encode()).hexdigest()))
    return value + '\n'


def definitions(path, pattern):
    return '\n'.join(re.findall(pattern, path.read_text(), re.M)) + '\n'


def run(label, command, timeout=120):
    print('RUN', label, flush=True)
    (out / 'phase').write_text(label + '\n')
    with (out / (label + '.log')).open('wb') as log:
        result = subprocess.run(command, cwd=str(out), stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
    record['commands'].append(dict(label=label, command=command, timeout_seconds=timeout, exit_code=result.returncode))
    assert result.returncode == 0, (label, result.returncode, (out / (label + '.log')).read_text()[-10000:])


try:
    capture(Path(__file__), 'helper.py')
    record['source_parent'] = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], universal_newlines=True).strip()
    names = ['kernel/rust/native_futex.rs', 'kernel/rust/abi.rs', 'kernel/rust/syscall_policy.rs',
             'kernel/rust/futex.rs', 'kernel/rust/sched_helpers.rs', 'kernel/rust/x86_memory_helpers.rs',
             'kernel/syscall.c', 'kernel/rust/lib.rs', 'kernel/CMakeLists.txt',
             'scripts/tests/fixtures/ultra-futex-clone.rs', 'scripts/tests/fixtures/ultra-futex-linux-reference.c',
             'scripts/tests/fixtures/ultra-clone-store.c', 'kernel/rust/tests/run_equivalence.sh']
    for name in names:
        capture(repo / name, 'original-inputs/' + name)
    for name in ['kernel/futex/syscalls.c', 'include/linux/time64.h', 'include/linux/ktime.h',
                 'kernel/time/hrtimer.c', 'kernel/futex/waitwake.c', 'kernel/sched/core.c', 'kernel/fork.c']:
        capture(linux / name, 'linux-reference/' + name)
    for name in ['native_futex.rs', 'abi.rs']:
        shutil.copyfile(out / 'original-inputs/kernel/rust' / name, out / name)
    for name in ['ultra-futex-clone.rs', 'ultra-futex-linux-reference.c', 'ultra-clone-store.c']:
        shutil.copyfile(out / 'original-inputs/scripts/tests/fixtures' / name, out / name)

    time64 = out / 'linux-reference/include/linux/time64.h'
    ktime = out / 'linux-reference/include/linux/ktime.h'
    hrtimer = out / 'linux-reference/kernel/time/hrtimer.c'
    futex = out / 'linux-reference/kernel/futex/syscalls.c'
    reference = body(time64, r'^static inline bool timespec64_valid\(', 'timespec64_valid')
    reference += body(ktime, r'^static inline ktime_t ktime_set\(', 'ktime_set')
    reference += body(ktime, r'^static inline ktime_t timespec64_to_ktime\(', 'timespec64_to_ktime')
    reference += body(hrtimer, r'^ktime_t ktime_add_safe\(', 'ktime_add_safe')
    reference += body(futex, r'^static __always_inline int\nfutex_init_timeout\(', 'futex_init_timeout')
    (out / 'linux-time-bodies.h').write_text(reference)
    vectors = []
    for op in [0, 9]:
        for sec in [-1, 0, 1, 9223372035, 9223372036, (1 << 63) - 1]:
            for nsec in [-1, 0, 1, 999999999, 1000000000]:
                for now_sec, now_nsec in [(0, 0), (1, 0), (10, 999999999), (9223372035, 999999999)]:
                    vectors.append(struct.pack('<5q', op, sec, nsec, now_sec, now_nsec))
    (out / 'vectors.bin').write_bytes(b''.join(vectors))
    record['linux_vectors'] = len(vectors)

    sched = out / 'original-inputs/kernel/rust/sched_helpers.rs'
    timer = definitions(sched, r'^type (?:Timer\w+|FutexWait\w+)\s*=[^;]+;')
    timer += definitions(sched, r'^const (?:EINVAL|EINTR|ETIMEDOUT|ERESTARTSYS|PS_RUNNING|FUTEX_WAIT_POST_\w+|FUTEX_WAIT_LOG_\w+):[^;]+;')
    timer += '#[repr(C)]\n' + body(sched, r'^pub struct TimerRuntimeOffsets \{', 'TimerRuntimeOffsets')
    for name in ['timer_spin_sleep_remaining_result', 'timer_runq_should_schedule_result',
                 'timer_after_spin_remaining_result', 'timer_schedule_timeout_body_result',
                 'futex_wait_prepare_q_result', 'futex_wake_bitset_valid_result',
                 'futex_wait_post_action_result', 'futex_wait_body_result', 'read_cint_field']:
        timer += body(sched, r'^(?:pub )?(?:unsafe )?(?:extern "C" )?fn ' + name + r'\(', name)
    (out / 'timer-bodies.rs').write_text(timer)

    policy = out / 'original-inputs/kernel/rust/syscall_policy.rs'
    selected = definitions(policy, r'^type Futex\w+\s*=[^;]+;')
    selected += definitions(policy, r'^const (?:EINVAL|EFAULT|FUTEX_\w+|DO_FUTEX_LOG_\w+):[^;]+;')
    selected += '#[repr(C)]\n' + body(policy, r'^pub struct FutexLogRecord \{', 'FutexLogRecord')
    for name in ['futex_decode_flags_result', 'futex_requeue_val2_result', 'do_futex_log', 'do_futex_body_result']:
        selected += body(policy, r'^(?:pub )?(?:unsafe )?(?:extern "C" )?fn ' + name + r'\(', name)
    (out / 'policy-bodies.rs').write_text(selected)

    memory = out / 'original-inputs/kernel/rust/x86_memory_helpers.rs'
    copies = definitions(memory, r'^type X86User\w+\s*=[^;]+;')
    copies += definitions(memory, r'^const (?:EINVAL|EFAULT|PTATTR_ACTIVE|PTL1_SHIFT|PTL1_SIZE|PAGE_MASK|PF_PATCH|X86_USER_COPY_\w+):[^;]+;')
    for name in ['x86_user_copy_bytes', 'x86_user_range_valid', 'x86_verify_process_vm_result',
                 'x86_process_vm_copy_impl', 'x86_process_vm_copy_result']:
        copies += body(memory, r'^(?:pub )?(?:unsafe )?(?:extern "C" )?fn ' + name + r'\(', name)
    (out / 'copy-bodies.rs').write_text(copies)

    c = out / 'original-inputs/kernel/syscall.c'
    conditions = ''
    for kind in ['parent', 'child']:
        name = 'clone_' + kind + '_tid_store_needed_result'
        conditions += body(c, r'^SYSCALL_POLICY_HELPER_SCOPE int\n' + name + r'\(', name)
        (out / ('clone-' + kind + '-store.h')).write_text(body(c, r'^\tif \(' + name + r'\(clone_flags\)\) \{', name + ' actual call block'))
    (out / 'clone-store-conditions.h').write_text(conditions)
    record['provider_substitutions'] = ['Pinned Linux initial-namespace clock returns fixed vectors.',
        'Exact scheduler body receives controlled rdtsc/scheduler/locks; exact futex retry body resolves its native ticks_now provider to the same deterministic clock.',
        'Exact Rust VM-copy body receives guarded discontiguous page providers; this proves sequencing/full-span preflight, not real hardware COW or instruction recovery.',
        'Exact native C child/parent store blocks call controlled checked-copy providers; no synthetic successful clone is counted as a running application.']
    run('diff-check', ['git', '-C', str(repo), 'diff', '--check'])
    rustc = '/opt/mckernel/cargo/bin/rustc' if profile == 'compat' else 'rustc'
    run('rust-version', [rustc, '--version'])
    run('c-version', ['cc', '--version'])
    run('linux-reference-build', ['cc', '-std=gnu11', '-O2', '-g', '-Wall', '-Wextra', '-Werror', '-MD', '-MF', 'linux-reference.d', 'ultra-futex-linux-reference.c', '-o', 'linux-reference-test'])
    run('linux-reference', [str(out / 'linux-reference-test'), str(out / 'vectors.bin')])
    run('clone-store-build', ['cc', '-std=gnu11', '-O2', '-g', '-Wall', '-Wextra', '-Werror', '-MD', '-MF', 'clone-store.d', 'ultra-clone-store.c', '-o', 'clone-store'])
    run('clone-store', [str(out / 'clone-store')])
    run('rust-build', [rustc, '--edition', '2021', '--cfg', 'native_linux_irq_work_v6_12', '-D', 'warnings', '--test', 'ultra-futex-clone.rs', '-o', 'futex-clone-tests'])
    run('rust-tests', [str(out / 'futex-clone-tests'), '--nocapture'])
    record['compiler_dependencies'] = []
    for name in ['linux-reference.d', 'clone-store.d']:
        for word in (out / name).read_text().replace('\\\n', ' ').split()[1:]:
            path = Path(word)
            if not path.is_absolute(): path = out / path
            if path.is_file(): record['compiler_dependencies'].append(identity(path))
    record['test_summary'] = [line for line in (out / 'rust-tests.log').read_text().splitlines() if line.startswith('test result:')]
    for row in record['inputs']:
        assert identity(Path(row['captured']['path'])) == row['captured']
        assert identity(Path(row['original']['path'])) == row['original']
    record['status'] = 'PASS'
except BaseException as error:
    record.update(status='FAIL', error=str(error))
    raise
finally:
    record['finished_utc'] = datetime.now(timezone.utc).isoformat()
    record['outputs'] = [identity(path) for path in sorted(out.iterdir()) if path.is_file() and path.name not in ('record.json', 'phase')]
    (out / 'record.json').write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
    print(record['status'], out, flush=True)
