/// Retire the selected C entry while reusing its exact existing Rust core.
/// The original selected entry discarded the core result. In particular, a
/// null context retains the existing core's -EINVAL/no-log behavior; no new
/// frame or freeze/null policy is introduced. Context/log pointers do not escape.
#[no_mangle]
pub unsafe extern "C" fn ihk_mc_print_user_context(uctx: *mut X86UserContext) {
    unsafe {
        let _ = x86_print_user_context_body_result(
            uctx,
            Some(x86_context_line_log_bridge),
        );
    }
}
