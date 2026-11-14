#[no_mangle]
pub unsafe extern "C" fn ihk_mc_syscall_set_arg2(uctx: *mut X86UserContext, value: CULong) {
    unsafe { x86_syscall_write(uctx, 2, value) }
}
