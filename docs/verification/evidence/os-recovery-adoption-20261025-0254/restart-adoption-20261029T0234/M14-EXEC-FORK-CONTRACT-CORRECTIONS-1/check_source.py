#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source checks only: no compiler, native runtime, or acceptance.
"""
from pathlib import Path
import hashlib
import re
p=Path(__file__).resolve().parent
root=p.parent
base=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall')
old=(root/'M14-LARGE-EXECVEAT-REUSE-1/do_execveat.PRIVATE.rs.inc').read_text()
new=(p/'do_execveat.long-format.PRIVATE.rs.inc').read_text()
changes=[('execve(): ERROR: host failed to load elf header, errno: %d', 'execve(): ERROR: host failed to load elf header, errno: %ld'),('execve(): ERROR: preparing ranges, args, envs, stack, ret: %d','execve(): ERROR: preparing ranges, args, envs, stack, ret: %ld')]
for before,after in changes:
 assert old.count(before)==1
 old=old.replace(before,after)
assert new==old
old_policy=(base/'next-do-fork-whole-owned-orchestration-source-1/syscall_policy.PRIVATE-WHOLE-MMAP-AND-FORK.rs').read_text()
old_helper=(base/'next-clone-report-enqueue-source-1/clone_report_enqueue.RUST-FRAGMENT.rs.inc').read_text()
helper=(p/'fork-enqueue-tid-snapshot.PRIVATE.rs.inc').read_text()
new_policy=(p/'syscall_policy.PRIVATE-MAP-FORK-TID.rs').read_text()
assert old_policy.count(old_helper)==1 and new_policy==old_policy.replace(old_helper,helper)
# The complete legacy C body is exactly the one frozen in CURRENT119.
old_c=(base/'next-do-fork-whole-owned-orchestration-source-1/do_fork.ACTUAL-ORIGINAL-FULL-C.inc').read_bytes()
frozen=(root/'M14-PRIVATE-NINE-LEAF-BATCH-1/preimage/kernel/syscall.c').read_bytes()
assert frozen.count(old_c)==1
body=helper[helper.index('pub unsafe extern "C" fn f03_clone_finish_report_enqueue_v1('):]
assert body.index('process_thread_report_attach_result') < body.index('hold_thread(new)') < body.index('let child_tid') < body.index('runq_add_thread(new, cpuid)') < body.index('schedule()') < body.index('    child_tid')
after=body[body.index('runq_add_thread(new, cpuid)')+len('runq_add_thread(new, cpuid)'):]
assert re.search(r'\bnew\b',after) is None
assert not re.search(r'\(\*new\)|addr_of!\(\(\*new\)',after)
whole = new_policy[new_policy.index('mod f03_fork_whole_owned_v1 {'):]
assert whole.count('return f03_clone_finish_report_enqueue_v1(') == 1
assert 'return f03_clone_finish_report_enqueue_v1(\n                    new, old_process, flags, term_signal, cpu, ptrace_event,\n                ) as CLong as CULong;' in whole
arity=(p/'exec-request-arity.PROPOSED.rs.inc').read_text()
assert 'args: [1, dirfd as CLong as CULong, filename as CULong,' in arity
assert 'descriptor_pa, flags as CLong as CULong, seed.unused_arg5]' in arity
phase2=arity[arity.index('pub unsafe extern "C" fn f03_execveat_phase2_declared_v1'):]
for field in ('number','args[0]','args[1]','args[2]'):
 assert f'(*request).{field}' in phase2
for field in ('args[3]','args[4]','args[5]','rtid','ttid','valid'):
 assert f'(*request).{field}' not in phase2
for f in ['do_execveat.long-format.PRIVATE.rs.inc','exec-request-arity.PROPOSED.rs.inc',
          'exec-request-arity.PROPOSED.h.inc','fork-enqueue-tid-snapshot.PRIVATE.rs.inc',
          'syscall_policy.PRIVATE-MAP-FORK-TID.rs']:
 print(f,hashlib.sha256((p/f).read_bytes()).hexdigest())
print('PASS exact candidate deltas, original C provenance, enqueue ordering and declared request fields; source only')
