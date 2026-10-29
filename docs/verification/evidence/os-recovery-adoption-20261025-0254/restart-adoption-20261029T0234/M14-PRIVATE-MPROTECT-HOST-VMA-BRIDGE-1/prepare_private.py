"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private full-prefix callback reuse; no compiler/runtime or new VM implementation.
"""
from pathlib import Path
import json,hashlib,difflib
ROOT=Path('/home/holden/mckernel');D=Path(__file__).resolve().parent
FILES=['kernel/syscall.c','kernel/rust/syscall_policy.rs','kernel/CMakeLists.txt'];pre={f:(ROOT/f).read_text()for f in FILES};post=dict(pre)
old='''static int mprotect_set_host_vma_bridge(unsigned long start, size_t len,
\t\tint prot, int holding_lock)
{
\treturn set_host_vma(start, len, prot, holding_lock);
}
'''
new='''#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)
extern int mprotect_set_host_vma_bridge(unsigned long start, size_t len, int prot, int holding_lock);
#else
static int mprotect_set_host_vma_bridge(unsigned long start, size_t len, int prot, int holding_lock) { return set_host_vma(start, len, prot, holding_lock); }
#endif
'''
assert pre['kernel/syscall.c'].count(old)==1 and old.count('\n')==new.count('\n');post['kernel/syscall.c']=pre['kernel/syscall.c'].replace(old,new)
leaf='''//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Full reachable set_host_vma prefix, then the existing qualified Rust body.

use crate::abi::{CInt, CULong, SizeT, X86UserContext};
use crate::x86_cpu_helpers::{
    ihk_mc_syscall_set_arg0, ihk_mc_syscall_set_arg1, ihk_mc_syscall_set_arg2,
};
use super::{get_this_cpu_local_var, set_host_vma_body_result};
use core::mem::{offset_of, size_of, MaybeUninit};

type SetArgFn = unsafe extern "C" fn(*mut X86UserContext, CULong);
type HostVmaFn = unsafe extern "C" fn(CULong, SizeT, CInt, CInt) -> CInt;
const _: SetArgFn = ihk_mc_syscall_set_arg0;
const _: SetArgFn = ihk_mc_syscall_set_arg1;
const _: SetArgFn = ihk_mc_syscall_set_arg2;
const _: HostVmaFn = set_host_vma_body_result;
const _: HostVmaFn = mprotect_set_host_vma_bridge;
const _: () = {
    assert!(size_of::<X86UserContext>() == 224);
    assert!(offset_of!(X86UserContext, gpr) == 56);
    assert!(size_of::<CULong>() == 8 && size_of::<SizeT>() == 8);
    assert!(size_of::<CInt>() == 4);
};

/// Preserve the original callback's complete reachable prefix and return.
///
/// # Safety
/// The existing CPU-local pointer remains valid/readable for its current slot;
/// the original body's current/thread/VM and borrowed lock/endpoint prerequisites
/// are unchanged. The unused current-thread value may be null as before. No new
/// lifetime, ownership, locking or null/errno policy is introduced here.
#[no_mangle]
pub(super) unsafe extern "C" fn mprotect_set_host_vma_bridge(
    start: CULong, len: SizeT, prot: CInt, holding_lock: CInt,
) -> CInt {
    // Private scratch only. X86UserContext and its nested register structs contain
    // only u64/u8 fields, so zero is valid. Initializing these otherwise unused
    // local bytes prevents references to uninitialized fields in existing setters.
    // The scratch pointer never escapes those setters; no context is read back.
    let mut ctx = MaybeUninit::<X86UserContext>::zeroed();
    // SAFETY: Exactly the original reachable current-slot read before setters.
    let _thread = unsafe { (*get_this_cpu_local_var()).current };
    // SAFETY: Naturally aligned, live, zero-initialized private224B scratch; each
    // unchanged setter performs its original volatile register write in order.
    // C size_t/unsigned long are64-bit here. C int prot converts to unsigned long
    // modulo2^64; Rust's direct signed-i32→u64 cast has that exact defined value.
    unsafe {
        ihk_mc_syscall_set_arg0(ctx.as_mut_ptr(), start);
        ihk_mc_syscall_set_arg1(ctx.as_mut_ptr(), len as CULong);
        ihk_mc_syscall_set_arg2(ctx.as_mut_ptr(), prot as CULong);
    }
    set_host_vma_body_result(start, len, prot, holding_lock)
}
'''
f='kernel/rust/syscall_mprotect_host_vma.rs';post[f]=leaf
module='''
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[cfg(all(f03_leaf_callbacks_candidate, target_arch = "x86_64"))]
#[path = "syscall_mprotect_host_vma.rs"]
mod syscall_mprotect_host_vma;
''';assert pre['kernel/rust/syscall_policy.rs'].endswith('\n');post['kernel/rust/syscall_policy.rs']=pre['kernel/rust/syscall_policy.rs']+module
anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_policy.rs"\n';assert pre['kernel/CMakeLists.txt'].count(anchor)==1;post['kernel/CMakeLists.txt']=pre['kernel/CMakeLists.txt'].replace(anchor,anchor+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_mprotect_host_vma.rs"\n')
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
for kind,data in [('preimage',pre),('postimage',post)]:
 for n,s in data.items():
  p=D/kind/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
patch=''
for n in [f]+FILES:patch+=''.join(difflib.unified_diff(pre.get(n,'').splitlines(True),post[n].splitlines(True),fromfile='a/'+n if n in pre else '/dev/null',tofile='b/'+n))
(D/'MPROTECT-HOST-VMA.PRIVATE-NOT-APPLIED.patch').write_text(patch)
(D/'FILEMAP.SOURCE-ONLY.json').write_text(json.dumps(dict(preimages={n:ref(D/'preimage'/n)for n in pre},postimages={n:ref(D/'postimage'/n)for n in post},reused_sources={n:ref(ROOT/n)for n in ['kernel/rust/abi.rs','kernel/rust/x86_cpu_helpers.rs','arch/x86_64/kernel/include/ihk/context.h']},runtime_authority=None),indent=2)+'\n');print('private full-prefix source generated')
