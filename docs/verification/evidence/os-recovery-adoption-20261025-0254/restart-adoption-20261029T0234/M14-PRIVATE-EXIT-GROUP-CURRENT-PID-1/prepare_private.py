"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source-only getter candidate; no compiler or runtime operations.
"""
from pathlib import Path
import hashlib,json,difflib
ROOT=Path('/home/holden/mckernel');D=Path(__file__).resolve().parent
files=['kernel/syscall.c','kernel/rust/syscall_policy.rs','kernel/CMakeLists.txt'];pre={f:(ROOT/f).read_text()for f in files};post=dict(pre)
old='''int
exit_group_current_pid_bridge(void)
{
\tstruct thread *thread = get_this_cpu_local_var()->current;

\treturn thread->proc->pid;
}
'''
assert pre['kernel/syscall.c'].count(old)==1
new='''#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)
extern int exit_group_current_pid_bridge(void);
#else
int exit_group_current_pid_bridge(void) { struct thread *thread = get_this_cpu_local_var()->current; return thread->proc->pid; }


#endif
'''
assert old.count('\n')==new.count('\n');post['kernel/syscall.c']=pre['kernel/syscall.c'].replace(old,new)
leaf='''//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Existing raw current-process PID callback; private source-only successor.

use super::{current_thread_ptr, CInt};
use crate::abi::{Process, Thread};
use core::mem::{offset_of, size_of};

// Reuse the exact existing abi.rs/process_helpers.rs assertions, not a new layout.
const _: () = {
    assert!(size_of::<CInt>() == 4);
    assert!(offset_of!(Thread, proc) == 4304);
    assert!(offset_of!(Process, pid) == 456);
};

/// Same no-argument C int callback as the original raw C getter.
///
/// # Safety
/// Existing syscall-entry invariant: the local current thread and its proc are
/// live, non-null, correctly aligned and readable for this callback. Reuse the
/// existing accessor and scheduler/preemption/lifetime context. This getter does
/// not schedule, acquire ownership, add null handling, or extend either lifetime.
#[no_mangle]
pub(super) unsafe extern "C" fn exit_group_current_pid_bridge() -> CInt {
    // SAFETY: the unchanged caller's raw current/proc invariant above is exactly
    // the original C getter's precondition. No Rust reference is constructed.
    unsafe { (*(*current_thread_ptr()).proc).pid }
}
'''
name='kernel/rust/syscall_exit_group_current_pid.rs';post[name]=leaf
anchor='use core::ffi::c_void;\n';assert pre['kernel/rust/syscall_policy.rs'].startswith(anchor)
module='\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(f03_leaf_callbacks_candidate, target_arch = "x86_64"))]\n#[path = "syscall_exit_group_current_pid.rs"]\nmod syscall_exit_group_current_pid;\n';post['kernel/rust/syscall_policy.rs']=anchor+module+pre['kernel/rust/syscall_policy.rs'][len(anchor):]
anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_policy.rs"\n';assert pre['kernel/CMakeLists.txt'].count(anchor)==1;post['kernel/CMakeLists.txt']=pre['kernel/CMakeLists.txt'].replace(anchor,anchor+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_exit_group_current_pid.rs"\n')
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
for kind,data in [('preimage',pre),('postimage',post)]:
 for f,s in data.items():
  p=D/kind/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
patch=''
for f in [name]+files:patch+=''.join(difflib.unified_diff(pre.get(f,'').splitlines(True),post[f].splitlines(True),fromfile='a/'+f if f in pre else '/dev/null',tofile='b/'+f))
(D/'CURRENT-PID.PRIVATE-NOT-APPLIED.patch').write_text(patch)
(D/'FILEMAP.SOURCE-ONLY.json').write_text(json.dumps(dict(preimages={f:ref(D/'preimage'/f)for f in pre},postimages={f:ref(D/'postimage'/f)for f in post},layout_source=ref(ROOT/'kernel/rust/abi.rs'),existing_accessor_source=ref(ROOT/'kernel/rust/syscall_policy.rs')),indent=2)+'\n');print('private getter generated')
