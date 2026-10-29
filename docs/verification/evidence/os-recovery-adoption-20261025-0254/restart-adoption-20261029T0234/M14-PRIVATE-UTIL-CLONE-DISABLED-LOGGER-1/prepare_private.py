"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source-only construction; no compiler/process/guard/native operations.
"""
from pathlib import Path
import hashlib,json,difflib,re,ast
ROOT=Path('/home/holden/mckernel');D=Path(__file__).resolve().parent
FILES=['kernel/syscall.c','kernel/rust/syscall_policy.rs','kernel/CMakeLists.txt']
pre={f:(ROOT/f).read_text()for f in FILES}
old='''void
syscall_util_indicate_clone_disabled_bridge(void)
{
\tkprintf("%s: error: --enable-uti mcexec option not specified\\n",
\t\t\t"sys_util_indicate_clone");
}
'''
assert pre['kernel/syscall.c'].count(old)==1
assert '\n#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\n'+old in pre['kernel/syscall.c']
replacement='extern void syscall_util_indicate_clone_disabled_bridge(void);\n'+'\n'*(old.count('\n')-1)
post=dict(pre);post['kernel/syscall.c']=pre['kernel/syscall.c'].replace(old,replacement)
leaf='''//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Private source-only successor for the existing constant disabled-UTI logger.

use super::kprintf;

/// Existing no-argument void callback; one unchanged diagnostic per invocation.
#[no_mangle]
pub(super) extern "C" fn syscall_util_indicate_clone_disabled_bridge() {
    // SAFETY: both pointers refer to immutable static NUL-terminated C strings.
    // The format consumes exactly one %s; its sole variadic argument is the
    // matching const-char pointer. Neither storage can expire during kprintf.
    // The existing synchronous logger retains its CPU-prefix/output behavior.
    unsafe {
        kprintf(
            c"%s: error: --enable-uti mcexec option not specified\\n".as_ptr().cast(),
            c"sys_util_indicate_clone".as_ptr().cast::<i8>(),
        );
    }
}
'''
newfile='kernel/rust/syscall_util_clone_disabled_logger.rs';post[newfile]=leaf
anchor='use core::ffi::c_void;\n';assert pre['kernel/rust/syscall_policy.rs'].startswith(anchor)
module='\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[path = "syscall_util_clone_disabled_logger.rs"]\nmod syscall_util_clone_disabled_logger;\n'
post['kernel/rust/syscall_policy.rs']=anchor+module+pre['kernel/rust/syscall_policy.rs'][len(anchor):]
a='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_policy.rs"\n';assert pre['kernel/CMakeLists.txt'].count(a)==1
post['kernel/CMakeLists.txt']=pre['kernel/CMakeLists.txt'].replace(a,a+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_util_clone_disabled_logger.rs"\n')
for kind,data in [('preimage',pre),('postimage',post)]:
 for f,s in data.items():
  p=D/kind/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
patch=''
for f in [newfile]+FILES:patch+=''.join(difflib.unified_diff(pre.get(f,'').splitlines(True),post[f].splitlines(True),fromfile='a/'+f if f in pre else '/dev/null',tofile='b/'+f))
(D/'UTIL-CLONE-DISABLED.PRIVATE-NOT-APPLIED.patch').write_text(patch)
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
(D/'FILEMAP.SOURCE-ONLY.json').write_text(json.dumps(dict(preimages={f:ref(D/'preimage'/f)for f in pre},postimages={f:ref(D/'postimage'/f)for f in post}),indent=2)+'\n')
print('private source generated')
