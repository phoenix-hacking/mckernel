#!/usr/bin/env python3
"""Functional OS source preparation only; no security testing or compilation."""

import difflib
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
REPO = Path('/home/holden/mckernel')


def binding(path):
    data = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(data).hexdigest(),
            'bytes': len(data)}


def main():
    cpath = REPO / 'kernel/process.c'
    rpath = REPO / 'kernel/rust/process_helpers.rs'
    c = cpath.read_text()
    rust = rpath.read_text()
    start = c.index('void\ndebug_log(unsigned long arg)\n{')
    end = c.index('\nvoid process_access_ok_log_bridge', start)
    original = c[start:end]
    if '\n}\n' != original[-3:]:
        raise RuntimeError('exact debug_log body terminator changed')
    if 'pub unsafe extern "C" fn debug_log(' in rust:
        raise RuntimeError('debug_log already ported; do not duplicate slice')
    replacement = ('#ifdef MCKERNEL_RUST_PROCESS_HELPERS\n'
                   'void debug_log(unsigned long arg);\n'
                   '#else\n' + original + '#endif\n')
    body = ROOT / 'fixture/debug_log.ACTUAL-RUST.inc'
    (ROOT / 'fixture/original_debug_log.ACTUAL-C.inc').write_text(original)
    outputs = {
        'kernel/process.c': c[:start] + replacement + c[end:],
        'kernel/rust/process_helpers.rs': rust + '\n' + body.read_text(),
    }
    for name, text in outputs.items():
        target = ROOT / 'candidate' / name
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise RuntimeError('retain prior candidate; use a fresh attempt')
        target.write_text(text)
        before = c if name.endswith('.c') else rust
        diff = ''.join(difflib.unified_diff(
            before.splitlines(True), text.splitlines(True),
            fromfile='a/' + name, tofile='b/' + name))
        (ROOT / 'patch' / (Path(name).name + '.DEBUG-LOG.diff')).write_text(diff)
    manifest = {
        'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
        'status': 'DEBUG_LOG_FOUR_HASH_TRAVERSALS_SOURCE_ONLY',
        'owner': '/root/m14_process',
        'base': {'C': binding(cpath), 'Rust': binding(rpath)},
        'postimages': {name: binding(ROOT / 'candidate' / name) for name in outputs},
        'original': binding(ROOT / 'fixture/original_debug_log.ACTUAL-C.inc'),
        'new_Rust': binding(body),
        'providers': {name: binding(REPO / name) for name in [
            'kernel/rust/abi.rs', 'kernel/rust/lock_helpers.rs',
            'kernel/include/process.h']},
        'preserved': [
            'Existing FP/process fixes and all current COW/anonymous/install-finish bodies',
            'Original case 1/2 reader lock per bucket and original case 3/4 unlocked traversal',
            'Bucket/list/printf order, exact five format strings, pid1 process omission',
            'Existing typed ABI and Rust __mcs_rwlock_reader_lock/unlock providers',
            'Unknown code produces no output or lock operations',
        ],
        'ownership': 'No allocation/free/refcount change or list mutation; borrowed diagnostic views only. Unlocked cases preserve original caller-stable lifetime requirement.',
        'next_executable_check': 'After root physical acceptance and ordinary compiler grant: actual C-reference/Rust parity of empty/multi-bucket/multi-entry/pid1/unknown-code cases with exact output and lock trace; full compute crate and selected/default plus fallback process consumer compile/link.',
        'downstream_unlock': 'Retires the remaining live debug_log traversal body into Rust; reduces process.c runtime debt while retaining full current-candidate/native proof open.',
        'compiler_jobs': 0,
        'actual_tests': 0,
        'CPU_reservations': 0,
        'new_executable_queues': 0,
        'canonical_mutations': 0,
        'all_prior_failures_retained': True,
        'fullcrate_default_native_credit': False,
    }
    (ROOT / 'SOURCE-NEXT-BODY.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
