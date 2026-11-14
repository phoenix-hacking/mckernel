"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only source checks. No compiler, runtime, controller, host or native calls.
"""
from pathlib import Path
import hashlib,json,re
D=Path(__file__).resolve().parent;ROOT=Path('/home/holden/mckernel');p=(D/'PTRACE-CLONE-NOIRQ.PRIVATE-NOT-APPLIED.patch').read_text();leaf=(D/'PRIVATE-LEAF.rs').read_text();inputs=json.loads((D/'SOURCE-INPUTS.json').read_text())
for name,row in inputs.items():
 b=(ROOT/name).read_bytes();assert len(b)==row['bytes'] and hashlib.sha256(b).hexdigest()==row['sha256'],name
syscall=(ROOT/'kernel/syscall.c').read_text();policy=(ROOT/'kernel/rust/syscall_policy.rs').read_text();locks=(ROOT/'kernel/rust/lock_helpers.rs').read_text();spin=(ROOT/'kernel/rust/spinlock_helpers.rs').read_text();header=(ROOT/'arch/x86_64/kernel/include/arch-lock.h').read_text();cmake=(ROOT/'kernel/CMakeLists.txt').read_text()
assert 'typedef void (*ptrace_rwlock_fn_t)(unsigned long lock_addr, void *node);' in syscall
for op in ('lock','unlock'):
 assert len(re.findall(r'extern "C" fn ptrace_report_clone_noirq_'+op+r'_bridge\(',leaf))==1
 assert leaf.count('lock_helpers::__mcs_rwlock_writer_'+op+'_noirq(lock_addr as *mut McsRwlockLock, node);')==1
 assert '__mcs_rwlock_writer_'+op+'_noirq' in locks
assert leaf.count('#[no_mangle]')==2 and leaf.count('node: *mut c_void')==2 and 'cpu_disable_interrupt' not in leaf and 'cpu_restore_interrupt' not in leaf
assert 'type CULong = u64;' in (ROOT/'kernel/rust/abi.rs').read_text()
for op in ('lock','unlock'):
 match=re.search(r'pub unsafe extern "C" fn __mcs_rwlock_writer_'+op+r'_noirq\((.*?)\) \{(.*?)\n\}',locks,re.S);assert match and '_node: *mut core::ffi::c_void' in match[1] and 'spinlock_helpers::__ihk_mc_spinlock_'+op+'_noirq(&mut (*lock).slock);' in match[2]
assert 'SPINLOCK_IN_MCS_RWLOCK' in header and 'struct mcs_rwlock_node *next;' in header
assert 'preempt_disable();' in spin and 'preempt_enable();' in spin and 'Ordering::SeqCst' in spin
parent=syscall[syscall.index('static int ptrace_report_clone(struct thread *thread'):syscall.index('static int ptrace_report_clone(struct thread *thread')+6200]
assert 'struct mcs_rwlock_node lock;' in parent and 'struct mcs_rwlock_node updatelock;' in parent
assert 'get_this_cpu_local_var()->current, &offsets, &lock, &updatelock,\n\t\t\tptrace_report_clone_noirq_lock_bridge,\n\t\t\tptrace_report_clone_noirq_unlock_bridge,' in parent
body=policy[policy.index('pub unsafe extern "C" fn ptrace_report_clone_body_result('):];body=body[:body.index('\n#[no_mangle]',30)]
calls=re.findall(r'^\s*(lock|unlock)\((update_lock|new_update_lock), (lock_node|new_lock_node)\);',body,re.M)
assert calls==[('lock','update_lock','lock_node'),('unlock','update_lock','lock_node'),('lock','new_update_lock','new_lock_node'),('unlock','new_update_lock','new_lock_node')]
assert 'if (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)' in cmake and 'if (MCKERNEL_HOST_IRQ_ABI STREQUAL "linux-6.12")' in cmake
assert p.count('+\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_ptrace_clone_noirq_candidate")')==1
assert '+#if defined(MCKERNEL_RUST_F03_PTRACE_CLONE_NOIRQ)' in p and '+#line 7274\n' in p
# The next original blank line consumes 7274 and static logger begins at 7275;
# its three unchanged dkprintf lines remain 7279, 7283 and 7288.
logger=syscall[syscall.index('static void\nptrace_report_clone_log_bridge'):];logger=logger[:logger.index('\n#endif')]
lines=logger.splitlines();assert [7275+i for i,s in enumerate(lines) if 'dkprintf(' in s]==[7279,7283,7288]
assert 'ptrace_report_clone_body_result(' not in p and 'syscall_policy.rs' not in p
print('PASS source snapshots, exact ABI/delegation, paired caller nodes and lock sequence, x86 selection, original logger line projection, untouched parent body')
