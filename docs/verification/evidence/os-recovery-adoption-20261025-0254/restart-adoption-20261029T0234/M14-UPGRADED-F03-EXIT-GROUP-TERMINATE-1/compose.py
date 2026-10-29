from pathlib import Path
import difflib
here=Path(__file__).resolve().parent
base=here.parent/'M14-PRIVATE-NINE-LEAF-BATCH-1'/'postimage'/'kernel'
out=here/'postimage'/'kernel'
s=(base/'syscall.c').read_text()
old='''void
exit_group_terminate_bridge(int status, int group)
{
\tterminate(status, group);
}
'''
new='''#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)
extern void exit_group_terminate_bridge(int status, int group);
#else
#if defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)
#line 5678
#else
#line 5687
#endif
void
exit_group_terminate_bridge(int status, int group)
{
\tterminate(status, group);
}
#endif
#if defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)
#line 5683
#else
#line 5692
#endif
'''
assert s.count(old)==1
(out/'syscall.c').write_text(s.replace(old,new))
p=(base/'rust/syscall_policy.rs').read_text()
(out/'rust/syscall_policy.rs').write_text(p+'''\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(f03_leaf_callbacks_candidate, target_arch = "x86_64"))]\n#[path = "syscall_exit_group_terminate.rs"]\nmod syscall_exit_group_terminate;\n''')
c=(base/'CMakeLists.txt').read_text()
anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_mprotect_host_vma.rs"\n'
assert c.count(anchor)==1
(out/'CMakeLists.txt').write_text(c.replace(anchor,anchor+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_exit_group_terminate.rs"\n'))
(out/'rust/syscall_exit_group_terminate.rs').write_text('''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use core::ffi::c_int;

// Same existing C provider used by the scoped Rust exit helpers. This is a
// declaration only; it does not replace or claim the terminate implementation.
unsafe extern "C" {
    fn terminate(status: c_int, group: c_int);
}

/// Forward the exit-group callback to its existing termination provider.
///
/// # Safety
/// The caller must meet the same execution-context and lifetime requirements
/// as the original C callback and the existing terminate provider.
#[no_mangle]
pub unsafe extern "C" fn exit_group_terminate_bridge(status: c_int, group: c_int) {
    // SAFETY: The original callback forwards these exact C int arguments once
    // to the existing void provider and does not assume it cannot return.
    unsafe { terminate(status, group) };
}
''')
patch=[]
for name in ['syscall.c','CMakeLists.txt','rust/syscall_policy.rs','rust/syscall_exit_group_terminate.rs']:
 a,b=base/name,out/name
 patch+=difflib.unified_diff(a.read_text().splitlines(keepends=True) if a.exists() else [],b.read_text().splitlines(keepends=True),fromfile='a/kernel/'+name if a.exists() else '/dev/null',tofile='b/kernel/'+name)
(here/'EXIT-GROUP-TERMINATE.PRIVATE-NOT-APPLIED.patch').write_text(''.join(patch))
