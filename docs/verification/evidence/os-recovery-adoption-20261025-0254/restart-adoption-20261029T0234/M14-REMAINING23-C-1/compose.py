from pathlib import Path
import difflib
here=Path(__file__).resolve().parent
family=here.parent/'M14-TERMINATION-FAMILY-COMPOSITION-1'/'postimage'/'kernel'
nine=here.parent/'M14-PRIVATE-NINE-LEAF-BATCH-1'/'postimage'/'kernel'
kfree=here.parent/'M14-UPGRADED-F03-PTRACE-KFREE-1'/'Rust-owned-metadata-correction-1'/'postimage'/'kernel'
out=here/'postimage'/'kernel';src=(family/'syscall.c').read_text(); baseline=(nine/'syscall.c').read_text();k=(kfree/'syscall.c').read_text()
old='''static void
ptrace_detach_kfree_bridge(void *ptr)
{
\tkfree_tracked(ptr, __FILE__, __LINE__);
}
'''
a=baseline.index(old); suffix='\n#ifndef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nstatic void\nptrace_detach_clear_single_step_bridge';b=k.index('#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__) && defined(MCKERNEL_RUST_F03_PTRACE_KFREE_PROFILE_119)\n',a);c=k.index(suffix,b)
replacement=k[b:c];assert src.count(old)==1
src=src.replace(old,replacement)
kill='''static long
ptrace_detach_do_kill_bridge(void *current_thread, int pid, int tid,
\t\tint sig, const void *info, int ptracecont)
{
\treturn do_kill((struct thread *)current_thread, pid, tid, sig,
\t\t\t(struct siginfo *)info, ptracecont);
}
'''
interrupt='''void
interrupt_syscall(struct thread *thread, int sig)
{
\tihk_mc_user_context_t ctx;
\tlong lerror;

\tdkprintf("interrupt_syscall pid=%d tid=%d sig=%d\\n", thread->proc->pid,
\t         thread->tid, sig);
\tihk_mc_syscall_set_arg0(&ctx, thread->proc->pid);
\tihk_mc_syscall_set_arg1(&ctx, thread->tid);
\tihk_mc_syscall_set_arg2(&ctx, sig);

\tlerror = syscall_generic_forwarding(__NR_kill, &ctx);
\tif (lerror) {
\t\tkprintf("interrupt_syscall failed. %ld\\n", lerror);
\t}
\treturn;
}
'''
dispatch='#if defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_DISPATCH_CONTEXT)\n'
def wrap(old, guard, proto, on, off):
 n=old.count('\n')
 return (guard+proto+'\n#else\n'+dispatch+'#line '+str(on-3)+'\n#else\n#line '+str(off-1)+'\n#endif\n'+old+'#endif\n'+dispatch+'#line '+str(on+n-3)+'\n#else\n#line '+str(off+n-1)+'\n#endif\n')
assert src.count(kill)==1 and src.count(interrupt)==1
src=src.replace(kill,wrap(kill,'#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)\n','extern long ptrace_detach_do_kill_bridge(void *current_thread, int pid, int tid, int sig, const void *info, int ptracecont);',4690,4697))
src=src.replace(interrupt,wrap(interrupt,'#if defined(MCKERNEL_RUST_F03_INTERRUPT_ARITY3_DEFINED) && defined(MCKERNEL_RUST_F03_INTERRUPT_ORIGIN_PROFILE_119) && defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_SYSCALL_OFFLOAD) && defined(__x86_64__)\n','extern void interrupt_syscall(struct thread *thread, int sig);',5656,5663))
(out/'syscall.c').write_text(src)
policy=(family/'rust/syscall_policy.rs').read_text()
for cfg,file in [('all(f03_ptrace_kfree_profile_119, f03_leaf_callbacks_candidate, target_arch = "x86_64")','syscall_ptrace_detach_kfree.rs'),('all(f03_leaf_callbacks_candidate, target_arch = "x86_64")','syscall_ptrace_detach_kill.rs'),('all(f03_interrupt_arity3_defined_candidate, f03_interrupt_origin_profile_119, target_arch = "x86_64")','syscall_interrupt_arity3.rs')]:
 policy+='\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg('+cfg+')]\n#[path = "'+file+'"]\nmod '+file[:-3]+';\n'
(out/'rust/syscall_policy.rs').write_text(policy)
cm=(family/'CMakeLists.txt').read_text();anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_mprotect_host_vma.rs"\n';assert cm.count(anchor)==1
addition=''.join('\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/'+f+'"\n' for f in ['syscall_ptrace_detach_kfree.rs','syscall_ptrace_detach_kill.rs','syscall_interrupt_arity3.rs'])
(out/'CMakeLists.txt').write_text(cm.replace(anchor,anchor+addition))
(out/'rust/syscall_ptrace_detach_kfree.rs').write_text((kfree/'rust/syscall_ptrace_detach_kfree.rs').read_text())
(out/'rust/syscall_ptrace_detach_kill.rs').write_text('''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use crate::abi::{CInt, CLong, SigInfo};
use core::ffi::c_void;

/// Forward the original callback to the existing do_kill provider.
///
/// # Safety
/// Caller retains the current thread and, when non-null, info for the duration
/// of the existing provider call, following the original C callback contract.
#[no_mangle]
pub unsafe extern "C" fn ptrace_detach_do_kill_bridge(
    current_thread: *mut c_void, pid: CInt, tid: CInt, sig: CInt,
    info: *const c_void, ptracecont: CInt,
) -> CLong {
    // SAFETY: Existing adapter uses the original unsigned C provider and
    // bit-preserving long conversion; raw pointers and arguments are unchanged.
    unsafe { super::f06_ptrace_report_signal_kill(
        current_thread, pid, tid, sig, info.cast::<SigInfo>(), ptracecont,
    ) }
}
''')
(out/'rust/syscall_interrupt_arity3.rs').write_text('''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Contract candidate only: kill's unused arguments 3-5 are zero. This proposed
// defined-input policy does not change UTI decisions or request ID/valid logic.
use core::mem::MaybeUninit;
use core::ptr::{addr_of, addr_of_mut, write_volatile};
use crate::abi::{CInt, CULong, Thread, X86UserContext};
use crate::debug::Ddebug;

const SOURCE_FILE: &[u8] = b"/src/kernel/syscall.c\\0";
#[cfg(f03_interrupt_origin_dispatch)]
const DEBUG_LINE: u32 = 5662;
#[cfg(not(f03_interrupt_origin_dispatch))]
const DEBUG_LINE: u32 = 5669;
#[used]
#[no_mangle]
#[link_section = "__verbose"]
static mut f03_interrupt_syscall_debug_v1: [Ddebug; 1] = [Ddebug {
    file: SOURCE_FILE.as_ptr().cast(), func: b"interrupt_syscall\\0".as_ptr().cast(),
    fmt: core::ptr::null(), line_flags: DEBUG_LINE,
}];

/// Invoke the original three-argument kill forwarding route on a defined context.
///
/// # Safety
/// `thread` and its process are live for all field reads and forwarding, as in
/// the original entry. Current execution and forwarding retain their original
/// locks and lifetime; this does not acquire a reference or alter UTI state.
#[export_name = "interrupt_syscall"]
pub unsafe extern "C" fn f03_interrupt_arity3_v1(thread: *mut Thread, sig: CInt) {
    // Only the six argument fields are initialized; never create a reference
    // to an incompletely initialized context or initialize unrelated UTI state.
    let mut ctx = MaybeUninit::<X86UserContext>::uninit();
    let ctx_ptr = ctx.as_mut_ptr();
    unsafe {
        if core::ptr::read_volatile(addr_of!(f03_interrupt_syscall_debug_v1[0].line_flags)) >> 24 != 0 {
            super::kprintf(c"interrupt_syscall pid=%d tid=%d sig=%d\\n".as_ptr(),
                (*(*thread).proc).pid, (*thread).tid, sig);
        }
        // SAFETY: These six distinct integer fields match the x86 syscall
        // selectors; raw field writes avoid references to uninitialized storage.
        write_volatile(addr_of_mut!((*ctx_ptr).gpr.rdi), (*(*thread).proc).pid as CULong);
        write_volatile(addr_of_mut!((*ctx_ptr).gpr.rsi), (*thread).tid as CULong);
        write_volatile(addr_of_mut!((*ctx_ptr).gpr.rdx), sig as CULong);
        write_volatile(addr_of_mut!((*ctx_ptr).gpr.r10), 0);
        write_volatile(addr_of_mut!((*ctx_ptr).gpr.r8), 0);
        write_volatile(addr_of_mut!((*ctx_ptr).gpr.r9), 0);
        let error = super::syscall_generic_forwarding(62, ctx_ptr);
        if error != 0 {
            super::kprintf(c"interrupt_syscall failed. %ld\\n".as_ptr(), error);
        }
    }
}
''')
for f in ['syscall_terminate_whole.rs','syscall_terminate_mcexec_whole.rs','syscall_terminate_host_whole.rs']:
 (out/'rust'/f).write_text((family/'rust'/f).read_text())
patch=[]
for name in ['syscall.c','CMakeLists.txt','rust/syscall_policy.rs','rust/syscall_ptrace_detach_kfree.rs','rust/syscall_ptrace_detach_kill.rs','rust/syscall_interrupt_arity3.rs']:
 a,b=family/name,out/name
 patch+=difflib.unified_diff(a.read_text().splitlines(keepends=True) if a.exists() else [],b.read_text().splitlines(keepends=True),fromfile='a/kernel/'+name if a.exists() else '/dev/null',tofile='b/kernel/'+name)
(here/'QUEUE-C.PRIVATE-NOT-APPLIED.patch').write_text(''.join(patch))
