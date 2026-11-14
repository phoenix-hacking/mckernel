#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source-only paired IRQ-saving writer boundary candidate.
"""
import difflib, hashlib, json, re
from pathlib import Path
D=Path(__file__).resolve().parent
A=D.parent
F=A/'M14-PRIVATE-NINE-LEAF-BATCH-1/preimage'
ROOT=Path('/home/holden/mckernel')
def ref(p):
 b=p.read_bytes(); return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def tokens(s): return re.findall(r'[A-Za-z_][A-Za-z_0-9]*|\d+|[^\s]',s)
leaf='''//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Paired IRQ-saving MCS writer callbacks use the existing lock provider.
use core::ffi::c_void;
use core::mem::{align_of, size_of};
use crate::abi::CULong;
use crate::lock_helpers::{self, McsRwlockLock, McsRwlockNodeIrqsave};

const _: () = {
    assert!(size_of::<CULong>() == 8);
    assert!(size_of::<McsRwlockLock>() == 64 && align_of::<McsRwlockLock>() == 64);
    assert!(size_of::<McsRwlockNodeIrqsave>() == 64 && align_of::<McsRwlockNodeIrqsave>() == 64);
};

/// Acquire the caller's IRQ-saving writer lock and save flags in its node.
///
/// # Safety
/// The caller provides the original live, 64-byte-aligned lock and exclusive,
/// writable IRQ-save node, follows existing lock ordering and IRQ context, and
/// retains both objects until the matching release completes.
#[no_mangle]
pub unsafe extern "C" fn ptrace_wakeup_update_lock_bridge(lock_addr: CULong, node: *mut c_void) {
    // SAFETY: The selected x86 lock and IRQ-save node have the provider's C
    // representation; raw casts preserve their addresses and caller ownership.
    unsafe { lock_helpers::__mcs_rwlock_writer_lock(lock_addr as *mut McsRwlockLock, node.cast::<McsRwlockNodeIrqsave>()) };
}

/// Release the matching writer acquisition and restore its saved IRQ flags.
///
/// # Safety
/// The caller owns the matching acquisition and provides the same live lock
/// and node without concurrent node reuse until this release has completed.
#[no_mangle]
pub unsafe extern "C" fn ptrace_wakeup_update_unlock_bridge(lock_addr: CULong, node: *mut c_void) {
    // SAFETY: The original lock and saved node are passed to the paired provider;
    // it performs the release and restores the original saved interrupt state.
    unsafe { lock_helpers::__mcs_rwlock_writer_unlock(lock_addr as *mut McsRwlockLock, node.cast::<McsRwlockNodeIrqsave>()) };
}

type WriterCallback = unsafe extern "C" fn(CULong, *mut c_void);
const _: WriterCallback = ptrace_wakeup_update_lock_bridge;
const _: WriterCallback = ptrace_wakeup_update_unlock_bridge;
'''
files=['kernel/syscall.c','kernel/rust/lib.rs','kernel/CMakeLists.txt']
before={name:(F/name).read_text() for name in files}
after=dict(before)
for action in ('lock','unlock'):
 name='ptrace_wakeup_update_'+action+'_bridge'
 old=f'''static void\n{name}(unsigned long lock_addr, void *node)\n{{\n\tmcs_rwlock_writer_{action}((struct mcs_rwlock_lock *)lock_addr,\n\t\t\t(struct mcs_rwlock_node_irqsave *)node);\n}}'''
 new=f'''#if defined(MCKERNEL_RUST_F03_WAKEUP_WRITER_PAIR)
extern void {name}(unsigned long lock_addr, void *node);
#else
static void {name}(unsigned long lock_addr, void *node) {{ mcs_rwlock_writer_{action}((struct mcs_rwlock_lock *)lock_addr, (struct mcs_rwlock_node_irqsave *)node); }}

#endif'''
 assert after['kernel/syscall.c'].count(old)==1 and old.count('\n')==new.count('\n')
 assert tokens(old)==tokens(new.split('#else\n')[1].split('\n\n#endif')[0])
 after['kernel/syscall.c']=after['kernel/syscall.c'].replace(old,new)
assert len(before['kernel/syscall.c'].splitlines()) == len(after['kernel/syscall.c'].splitlines())
directives=lambda s:[(i,line) for i,line in enumerate(s.splitlines(),1) if re.match(r'^\s*#\s*(?:line\b|\d)',line)]
assert directives(before['kernel/syscall.c'])==directives(after['kernel/syscall.c'])
after['kernel/rust/lib.rs'] += '\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(f03_wakeup_writer_pair_candidate, target_arch = "x86_64"))]\nmod f03_wakeup_writer_pair;\n'
cm=after['kernel/CMakeLists.txt']
anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/lock_helpers.rs"\n'
assert cm.count(anchor)==1
cm=cm.replace(anchor,anchor+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_wakeup_writer_pair.rs"\n')
anchor='\t\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n'
assert cm.count(anchor)==1
cm=cm.replace(anchor,anchor+'\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_wakeup_writer_pair_candidate")\n')
anchor='COMPILE_DEFINITIONS "MCKERNEL_RUST_F03_PERF_ATTR_CALLBACKS;'
assert cm.count(anchor)==1
cm=cm.replace(anchor,'COMPILE_DEFINITIONS "MCKERNEL_RUST_F03_WAKEUP_WRITER_PAIR;MCKERNEL_RUST_F03_PERF_ATTR_CALLBACKS;')
after['kernel/CMakeLists.txt']=cm
after['kernel/rust/f03_wakeup_writer_pair.rs']=leaf
header=(ROOT/'arch/x86_64/kernel/include/arch-lock.h').read_text()
assert '#define SPINLOCK_IN_MCS_RWLOCK' in header
for action in ('lock','unlock'):
 assert f'#define mcs_rwlock_writer_{action} __mcs_rwlock_writer_{action}' in header
provider=(ROOT/'kernel/rust/lock_helpers.rs').read_text()
for clause in ['pub struct McsRwlockNodeIrqsave', 'pub struct McsRwlockLock', 'assert!(offset_of!(McsRwlockNodeIrqsave, irqsave) == 0)', 'assert!(offset_of!(McsRwlockLock, slock) == 0)', '(*node).irqsave = spinlock_helpers::__ihk_mc_spinlock_lock(&mut (*lock).slock);', 'spinlock_helpers::__ihk_mc_spinlock_unlock(&mut (*lock).slock, (*node).irqsave);']:
 assert clause in provider
for action in ('lock','unlock'):
 assert leaf.count(f'lock_helpers::__mcs_rwlock_writer_{action}(')==1
 assert f'ptrace_wakeup_update_{action}_bridge,' in before['kernel/syscall.c']
assert '_noirq(' not in leaf
rust_policy=(F/'kernel/rust/syscall_policy.rs').read_text()
assert 'type PtraceRwlockFn = unsafe extern "C" fn(CULong, *mut c_void);' in rust_policy
assert 'struct mcs_rwlock_node_irqsave lock;' in before['kernel/syscall.c']
lock_call=rust_policy.index('unsafe { lock_update(update_lock, lock_node) };')
unlock_call=rust_policy.index('unsafe { unlock_update(update_lock, lock_node) };', lock_call)
assert lock_call < unlock_call
assert 'unsafe { lock_update(update_lock, lock_node) };' not in rust_policy[lock_call+1:unlock_call]
patch=''; rows=[]
for name,text in after.items():
 dest=D/'postimage'/name; dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(text)
 if name in before:
  pre=D/'preimage'/name;pre.parent.mkdir(parents=True,exist_ok=True);pre.write_text(before[name])
 patch+=''.join(difflib.unified_diff(before.get(name,'').splitlines(True),text.splitlines(True),fromfile='a/'+name if name in before else '/dev/null',tofile='b/'+name))
 rows.append({'path':name,'preimage':ref(D/'preimage'/name) if name in before else None,'postimage':ref(dest)})
p=D/'WAKEUP-WRITER-PAIR.PRIVATE-NOT-APPLIED.patch';p.write_text(patch)
result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.', 'status':'PASS_PRIVATE_PAIRED_WRITER_SOURCE_ONLY', 'symbols':['ptrace_wakeup_update_lock_bridge','ptrace_wakeup_update_unlock_bridge'], 'patch':ref(p), 'files':rows, 'c_header':ref(ROOT/'arch/x86_64/kernel/include/arch-lock.h'), 'rust_provider':ref(ROOT/'kernel/rust/lock_helpers.rs'), 'caller':ref(F/'kernel/syscall.c'), 'checks':['paired C fallback tokens unchanged; source line and #line origins unchanged','selected matched linux-6.12 x86_64 non-UBSAN C and Rust cfg, fallback elsewhere','callback C and Rust scalar/raw-pointer signatures identical with typed function assertions','existing IRQsave provider selected for both callbacks exactly once; never noirq','header spinlock representation and provider node/lock ABI assertions; caller retains same stack irqsave node', 'no caller, signal state, logger or existing clone-noirq body changed'], 'limits':'Source only; no compiler/link/concurrency/native execution, no C-retirement or authority claim.'}
(D/'SOURCE-CHECKS.json').write_text(json.dumps(result,indent=2)+'\n')
print(result['status'])
