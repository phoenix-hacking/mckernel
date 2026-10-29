from pathlib import Path
import difflib
here=Path(__file__).resolve().parent
base=here.parent.parent/'M14-PRIVATE-NINE-LEAF-BATCH-1'/'postimage'/'kernel'
out=here/'postimage'/'kernel'
s=(base/'syscall.c').read_text()
old='''static void
ptrace_detach_kfree_bridge(void *ptr)
{
\tkfree_tracked(ptr, __FILE__, __LINE__);
}
'''
new='''#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__) && defined(MCKERNEL_RUST_F03_PTRACE_KFREE_PROFILE_119)
extern void ptrace_detach_kfree_bridge(void *ptr);
#else
#if defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)
#line 4651
#else
#line 4660
#endif
static void
ptrace_detach_kfree_bridge(void *ptr)
{
\tkfree_tracked(ptr, __FILE__, __LINE__);
}
#endif
#if defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)
#line 4656
#else
#line 4665
#endif
'''
assert s.count(old)==1
(out/'syscall.c').write_text(s.replace(old,new))
policy=(base/'rust/syscall_policy.rs').read_text()
(out/'rust/syscall_policy.rs').write_text(policy+'''\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(f03_leaf_callbacks_candidate, f03_ptrace_kfree_profile_119, target_arch = "x86_64"))]\n#[path = "syscall_ptrace_detach_kfree.rs"]\nmod syscall_ptrace_detach_kfree;\n''')
cmake=(base/'CMakeLists.txt').read_text()
anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_mprotect_host_vma.rs"\n'
assert cmake.count(anchor)==1
(out/'CMakeLists.txt').write_text(cmake.replace(anchor,anchor+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_ptrace_detach_kfree.rs"\n'))
(out/'rust/syscall_ptrace_detach_kfree.rs').write_text('''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use core::ffi::{c_int, c_void};

// These constants are valid only under the independently bound PROFILE_119
// source path and logical-line profile described in the private handoff.
const SOURCE_FILE: &[u8] = b"/src/kernel/syscall.c\\0";
#[cfg(f03_ptrace_kfree_dispatch_origin)]
const SOURCE_LINE: c_int = 4657;
#[cfg(not(f03_ptrace_kfree_dispatch_origin))]
const SOURCE_LINE: c_int = 4664;

/// Preserve the original tracked-free callback and its selected C origin.
///
/// # Safety
/// `ptr` must be null or an owned live tracked allocation admissible to the
/// original callback, and ownership must be transferred exactly once.
#[no_mangle]
pub unsafe extern "C" fn ptrace_detach_kfree_bridge(ptr: *mut c_void) {
    // SAFETY: The caller supplies the original pointer domain, and the source
    // profile binds these Rust-owned C-string bytes and line to the original
    // translation unit. The allocator handles null and tracking as before.
    unsafe {
        crate::mem_helpers::kfree_tracked(
            ptr, SOURCE_FILE.as_ptr().cast_mut().cast(), SOURCE_LINE,
        );
    }
}
''')
patch=[]
for name in ['syscall.c','CMakeLists.txt','rust/syscall_policy.rs','rust/syscall_ptrace_detach_kfree.rs']:
 a,b=base/name,out/name
 patch+=difflib.unified_diff(a.read_text().splitlines(keepends=True) if a.exists() else [],b.read_text().splitlines(keepends=True),fromfile='a/kernel/'+name if a.exists() else '/dev/null',tofile='b/kernel/'+name)
(here/'RUST-METADATA.PRIVATE-NOT-APPLIED.patch').write_text(''.join(patch))
