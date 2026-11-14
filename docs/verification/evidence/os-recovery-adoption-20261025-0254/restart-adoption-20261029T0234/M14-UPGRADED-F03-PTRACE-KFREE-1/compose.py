from pathlib import Path
import difflib

here = Path(__file__).resolve().parent
base = here.parent / 'M14-PRIVATE-NINE-LEAF-BATCH-1' / 'postimage' / 'kernel'
out = here / 'postimage' / 'kernel'
source = (base / 'syscall.c').read_text()
old = '''static void
ptrace_detach_kfree_bridge(void *ptr)
{
\tkfree_tracked(ptr, __FILE__, __LINE__);
}
'''
# The selected TU's prior conditional #line has two different offsets. Each
# directive accounts for skipped preprocessor lines before its next C token.
new = '''#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)
#if defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)
#line 4654
#else
#line 4663
#endif
const char f03_ptrace_detach_kfree_file_v1[] = __FILE__; const int f03_ptrace_detach_kfree_line_v1 = __LINE__;
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
assert source.count(old) == 1
(out / 'syscall.c').write_text(source.replace(old, new))
policy=(base / 'rust/syscall_policy.rs').read_text()
policy += '''\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(f03_leaf_callbacks_candidate, target_arch = "x86_64"))]\n#[path = "syscall_ptrace_detach_kfree.rs"]\nmod syscall_ptrace_detach_kfree;\n'''
(out / 'rust/syscall_policy.rs').write_text(policy)
cmake=(base / 'CMakeLists.txt').read_text()
anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_mprotect_host_vma.rs"\n'
assert cmake.count(anchor)==1
(out/'CMakeLists.txt').write_text(cmake.replace(anchor,anchor+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_ptrace_detach_kfree.rs"\n'))
leaf='''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use core::ffi::{c_char, c_int, c_void};
use core::ptr::addr_of;

unsafe extern "C" {
    static f03_ptrace_detach_kfree_file_v1: c_char;
    static f03_ptrace_detach_kfree_line_v1: c_int;
}

/// Forward the original callback's ownership and tracking provenance unchanged.
///
/// # Safety
/// `ptr` must be null or the same live tracked allocation accepted by the
/// original callback; ownership transfers to the allocator exactly once.
#[no_mangle]
pub unsafe extern "C" fn ptrace_detach_kfree_bridge(ptr: *mut c_void) {
    // SAFETY: The caller supplies the original tracked-free domain. These C
    // objects have static lifetime and capture the selected C file and line;
    // the tracked allocator owns the subsequent null/valid-pointer handling.
    unsafe {
        crate::mem_helpers::kfree_tracked(
            ptr,
            addr_of!(f03_ptrace_detach_kfree_file_v1).cast_mut(),
            f03_ptrace_detach_kfree_line_v1,
        );
    }
}
'''
(out/'rust/syscall_ptrace_detach_kfree.rs').write_text(leaf)
patch=[]
for name in ['syscall.c','CMakeLists.txt','rust/syscall_policy.rs','rust/syscall_ptrace_detach_kfree.rs']:
    a=base/name
    b=out/name
    oldlines=a.read_text().splitlines(keepends=True) if a.exists() else []
    patch += difflib.unified_diff(oldlines,b.read_text().splitlines(keepends=True),fromfile='a/kernel/'+name if a.exists() else '/dev/null',tofile='b/kernel/'+name)
(here/'PTRACE-KFREE.PRIVATE-NOT-APPLIED.patch').write_text(''.join(patch))
