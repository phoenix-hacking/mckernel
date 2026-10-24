#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_arg0(uctx: *const X86UserContext) -> CULong {
    unsafe { x86_syscall_read(uctx, 0) }
}
