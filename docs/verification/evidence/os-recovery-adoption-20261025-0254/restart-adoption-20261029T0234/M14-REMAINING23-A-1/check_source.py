#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only structural checks, never native execution or acceptance.
"""
from pathlib import Path
import hashlib
p=Path(__file__).resolve().parent;r=p.parent
before=(r/'M14-LARGE-MMAP-FORK-REUSE-1/do_mmap/width-corrected.PRIVATE.rs.inc').read_text()
mmap=(p/'do_mmap.reservation.PROPOSED.rs.inc').read_text()
assert before.count('f03_mmap_constants_v1[PF_POPULATE] as CInt')==0
assert mmap.count('f03_mmap_constants_v1[PF_POPULATE] as CInt')==0
block=mmap[mmap.index('let xpmem = unsafe'):mmap.index('// Population uses only scalar')]
order=['let reservation = unsafe { f03_mmap_range_reserve_write_v1',
       'ihk_rwspinlock_write_unlock_noirq', 'f03_mmap_xpmem_update_reserved_v1',
       'if error != 0', 'f03_mmap_range_release_v1']
pos=0
for term in order:pos=block.index(term,pos)+len(term)
assert 'xpmem_update_process_page_table(\n' not in block
assert 'Process, ProcessVm, ShmidDs' in mmap
helper=(p/'fork-enqueue-tid-snapshot.PRIVATE.rs.inc').read_text()
deps=(p/'fork-dependencies.PRIVATE.rs.inc').read_text()
assert deps.count(helper)==1
assert '#[cfg(f03_do_fork_owned_candidate)]' in deps
assert '(*new).tid' not in helper[helper.index('runq_add_thread(new, cpuid)'):]
exec_prev=(r/'M14-EXEC-FORK-CONTRACT-CORRECTIONS-1/do_execveat.long-format.PRIVATE.rs.inc').read_text()
whole=(p/'do_execveat.whole.PRIVATE.rs.inc').read_text()
assert whole==exec_prev.replace('#[export_name = "f03_do_execveat_whole_v1"]','#[export_name = "do_execveat"]')
assert 'MaybeUninit::<SyscallRequest>::uninit()' in whole
assert 'f03_execveat_phase1_request_init_v1' in whole and 'f03_execveat_phase2_request_init_v1' in whole
bridge=(p/'syscall_execveat_bridge.PRIVATE.rs.inc').read_text()
assert '#[link_name = "do_execveat"]' in bridge
assert '#[export_name = "syscall_execveat_bridge"]' in bridge
# #line affects the following physical line, including intervening directives.
# Helpers: #else, the inactive #line, and #endif precede the declaration.
# Fallback: only #endif precedes the declaration after its active #line.
assert 7528 + 3 == 7531
assert 7537 + 1 == 7538
for baseline,post in [('M14-PRIVATE-NINE-LEAF-BATCH-1/preimage/kernel/syscall.c','syscall.bridge-on-frozen119.PRIVATE.c'),('M14-CONVERSION-FIRST-COMPOSITION-1/postimage/kernel/syscall.c','syscall.bridge-on-first20.PRIVATE.c'),('M14-CONVERSION-FIRST-LARGE-COMPOSITION-2/postimage/kernel/syscall.c','syscall.bridge-on-large2.PRIVATE.c')]:
 before=(r/baseline).read_text();after=(p/post).read_text()
 old='static int do_execveat(ihk_mc_user_context_t *ctx, int dirfd,'
 replacement='''#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_EXECVEAT_BRIDGE)
int
#else
static int
#endif
#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
#line 7528
#else
#line 7537
#endif
do_execveat(ihk_mc_user_context_t *ctx, int dirfd,'''
 assert before.count(old)==1 and after.count(replacement)==1
 # Reverse projection checks all original C including disabled bodies and metadata.
 after=after.replace(replacement,old)
 start=after.index('#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\n#ifdef MCKERNEL_RUST_F03_EXECVEAT_BRIDGE')
 stop=after.index('#line 7705',start)
 original_start=before.index('#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nint\nsyscall_execveat_bridge')
 original_stop=before.index('#line 7705',original_start)
 after=after[:start]+before[original_start:original_stop]+after[stop:]
 assert after==before
for f in ['do_mmap.reservation.PROPOSED.rs.inc','fork-dependencies.PRIVATE.rs.inc',
'do_fork.whole.PRIVATE.rs.inc','do_execveat.whole.PRIVATE.rs.inc',
'syscall_execveat_bridge.PRIVATE.rs.inc','bridge-selection-first20.patch']:
 print(f,hashlib.sha256((p/f).read_bytes()).hexdigest())
print('PASS static source identity, selector reverse projection, reservation order and retained candidate checks; no compile or execution')
