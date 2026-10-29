"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One private existing-provider forwarding callback; no VM implementation change.
"""
from pathlib import Path
import json,hashlib,difflib
ROOT=Path('/home/holden/mckernel');D=Path(__file__).resolve().parent
FILES=['kernel/syscall.c','kernel/rust/syscall_policy.rs','kernel/CMakeLists.txt'];pre={f:(ROOT/f).read_text()for f in FILES};post=dict(pre)
old='''static long
do_munmap_clear_host_bridge(unsigned long addr, size_t len, int holding_lock)
{
\treturn clear_host_pte(addr, len, holding_lock);
}
'''
new='''#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)
extern long do_munmap_clear_host_bridge(unsigned long addr, size_t len, int holding_lock);
#else
static long do_munmap_clear_host_bridge(unsigned long addr, size_t len, int holding_lock) { return clear_host_pte(addr, len, holding_lock); }
#endif
'''
assert pre['kernel/syscall.c'].count(old)==1 and old.count('\n')==new.count('\n');post['kernel/syscall.c']=pre['kernel/syscall.c'].replace(old,new)
leaf='''//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Existing do_munmap callback forwarding to the qualified Rust clear_host_pte.

use crate::abi::{CInt, CLong, CULong, SizeT};
use super::f03_clear_host_pte_entry_v1::clear_host_pte;

type ClearHostFn = unsafe extern "C" fn(CULong, SizeT, CInt) -> CLong;
const _: ClearHostFn = clear_host_pte;
const _: ClearHostFn = do_munmap_clear_host_bridge;
const _: () = {
    assert!(core::mem::size_of::<CULong>() == 8);
    assert!(core::mem::size_of::<SizeT>() == 8);
    assert!(core::mem::size_of::<CInt>() == 4);
    assert!(core::mem::size_of::<CLong>() == 8);
};

/// Retain the original scalar callback ABI and exact signed long return.
///
/// # Safety
/// The caller retains all existing clear_host_pte current CPU/thread/VM lifetime,
/// original memory-range-lock state and synchronous forwarding prerequisites.
/// The qualified Rust provider owns the existing request/endpoint/flag/logging
/// protocol; this callback adds no access, validation, lock, retry or cleanup.
#[no_mangle]
pub(super) unsafe extern "C" fn do_munmap_clear_host_bridge(
    addr: CULong, len: SizeT, holding_lock: CInt,
) -> CLong {
    // SAFETY: Unchanged exact original provider and argument order. No casts,
    // normalization or null/errno policy is introduced by this forwarding leaf.
    unsafe { clear_host_pte(addr, len, holding_lock) }
}
'''
newfile='kernel/rust/syscall_munmap_clear_host_forward.rs';post[newfile]=leaf
assert pre['kernel/rust/syscall_policy.rs'].endswith('\n');module='''
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[cfg(all(f03_leaf_callbacks_candidate, target_arch = "x86_64"))]
#[path = "syscall_munmap_clear_host_forward.rs"]
mod syscall_munmap_clear_host_forward;
''';post['kernel/rust/syscall_policy.rs']=pre['kernel/rust/syscall_policy.rs']+module
anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_policy.rs"\n';assert pre['kernel/CMakeLists.txt'].count(anchor)==1;post['kernel/CMakeLists.txt']=pre['kernel/CMakeLists.txt'].replace(anchor,anchor+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_munmap_clear_host_forward.rs"\n')
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
for kind,data in [('preimage',pre),('postimage',post)]:
 for f,s in data.items():
  p=D/kind/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
patch=''
for f in [newfile]+FILES:patch+=''.join(difflib.unified_diff(pre.get(f,'').splitlines(True),post[f].splitlines(True),fromfile='a/'+f if f in pre else '/dev/null',tofile='b/'+f))
(D/'MUNMAP-CLEAR-HOST.PRIVATE-NOT-APPLIED.patch').write_text(patch)
(D/'FILEMAP.SOURCE-ONLY.json').write_text(json.dumps(dict(preimages={f:ref(D/'preimage'/f)for f in pre},postimages={f:ref(D/'postimage'/f)for f in post},reused_provider_module='syscall_policy::f03_clear_host_pte_entry_v1::clear_host_pte',ABI_source=ref(ROOT/'kernel/rust/abi.rs')),indent=2)+'\n');print('private forwarding source generated')
