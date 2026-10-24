// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// F06: complete public x86 ptrace syscall-event entry and its synchronous adapter.
// Insert adjacent to arch_ptrace_syscall_event_body_result. No shared ABI edit.
extern "C" {
    #[link_name = "ptrace_syscall_event"]
    fn arch_ptrace_public_syscall_event(thread: *mut Thread);
}

unsafe extern "C" fn arch_ptrace_syscall_event_notify(thread: *mut c_void, _unused: CInt) {
    unsafe { arch_ptrace_public_syscall_event(thread.cast::<Thread>()) };
}

#[no_mangle]
pub unsafe extern "C" fn arch_ptrace_syscall_event(
    thread: *mut Thread,
    ctx: *mut X86UserContext,
    setret: CLong,
) -> CLong {
    // The existing body checks ctx before dereferencing it, stores before the
    // callback, and rereads RAX after the callback. Thread is forwarded as-is.
    unsafe {
        arch_ptrace_syscall_event_body_result(
            thread.cast::<c_void>(),
            ctx.cast::<c_void>(),
            setret,
            offset_of!(X86UserContext, gpr) + offset_of!(crate::abi::X86BasicRegs, rax),
            Some(arch_ptrace_syscall_event_notify),
        )
    }
}
