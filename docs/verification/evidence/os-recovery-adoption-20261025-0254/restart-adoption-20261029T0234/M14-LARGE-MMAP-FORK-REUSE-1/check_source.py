#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only source comparisons; not a compiler, execution grant, or acceptance test.
"""
from pathlib import Path
import hashlib

here = Path(__file__).resolve().parent
base = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall')
frozen = (here.parent / 'M14-PRIVATE-NINE-LEAF-BATCH-1/preimage/kernel/syscall.c').read_bytes()
for name, directory in [('mmap', 'next-do-mmap-whole-orchestration-source-1'), ('fork', 'next-do-fork-whole-owned-orchestration-source-1')]:
    original = (base / directory / f'do_{name}.ACTUAL-ORIGINAL-FULL-C.inc').read_bytes()
    assert frozen.count(original) == 1, f'frozen {name} body mismatch or duplicate'
    print(f'frozen do_{name} exact once: {hashlib.sha256(original).hexdigest()}')
old = (base/'next-do-mmap-whole-orchestration-source-1/do_mmap_whole.PRIVATE-FRAGMENT.rs.inc').read_text()
mmap = (here/'do_mmap/width-corrected.PRIVATE.rs.inc').read_text()
assert old.count('f03_mmap_constants_v1[PF_POPULATE] as CInt') == 2
assert mmap == old.replace('f03_mmap_constants_v1[PF_POPULATE] as CInt', 'f03_mmap_constants_v1[PF_POPULATE]')
policy = (base/'next-do-mmap-whole-orchestration-source-1/current81-compile-qualification-preparation-1/bounded-fault-width-correction-1/source/kernel/rust/syscall_policy.rs').read_text()
assert mmap.split('\n',1)[1] in policy
fork=(here/'do_fork/do_fork_whole_owned.PRIVATE.rs.inc').read_bytes()
assert fork == (base/'next-do-fork-whole-owned-orchestration-source-1/do_fork_whole_owned.PRIVATE-FRAGMENT.rs.inc').read_bytes()
helper=(here/'do_fork/enqueue-tid-snapshot.PRIVATE.rs.inc').read_text()
snapshot=helper.index('let child_tid = unsafe { addr_of!((*new).tid).read() };')
enqueue=helper.index('crate::sched_helpers::runq_add_thread(new, cpuid)')
schedule=helper.index('schedule()')
assert snapshot < enqueue < schedule
assert '(*new).tid' not in helper[enqueue:]
assert helper.count('child_tid') == 2
for path in [here/'do_mmap/width-corrected.PRIVATE.rs.inc', here/'do_fork/do_fork_whole_owned.PRIVATE.rs.inc', here/'do_fork/enqueue-tid-snapshot.PRIVATE.rs.inc']:
 print(f'{path.relative_to(here)} sha256 {hashlib.sha256(path.read_bytes()).hexdigest()}')
print('PASS source comparisons and enqueue snapshot ordering; no runtime evidence')
