// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// The target is the existing C body or, when later selected, the whole Rust body.
#[cfg(f03_execveat_bridge_candidate)]
mod f03_execveat_bridge_candidate_v1 {
    use core::ffi::c_void;
    use crate::abi::{CInt, X86UserContext};
    unsafe extern "C" {
        #[link_name = "do_execveat"]
        fn target(ctx: *mut X86UserContext, dirfd: CInt, filename: *const i8,
            argv: *mut *mut i8, envp: *mut *mut i8, flags: CInt) -> CInt;
    }
    /// # Safety
    /// Original exec caller owns the context, filename and user argv/env vector
    /// lifetimes. The actual target retains its initialization, descriptor,
    /// offload/ACK, VM, preemption and switch contracts. No pointer is dereferenced
    /// here and no new owner, ACK, error path or additional context copy is added.
    #[export_name = "syscall_execveat_bridge"]
    pub unsafe extern "C" fn bridge(ctx: *mut c_void, dirfd: CInt,
        filename: *const c_void, argv: *mut *mut c_void,
        envp: *mut *mut c_void, flags: CInt) -> CInt {
        target(ctx.cast::<X86UserContext>(), dirfd, filename.cast::<i8>(),
            argv.cast::<*mut i8>(), envp.cast::<*mut i8>(), flags)
    }
    const _: unsafe extern "C" fn(*mut c_void, CInt, *const c_void,
        *mut *mut c_void, *mut *mut c_void, CInt) -> CInt = bridge;
}
