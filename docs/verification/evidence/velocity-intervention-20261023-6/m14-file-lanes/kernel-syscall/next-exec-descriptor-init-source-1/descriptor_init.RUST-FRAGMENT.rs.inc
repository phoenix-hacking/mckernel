// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
/// # Safety
/// file is the original static C source string; source_line identifies the bound
/// allocation origin. error points to the live C local, written only on failure.
/// Genuine tracked allocator owns initialization; on success the caller receives
/// exactly four owned kernel pages, all zeroed before return. No context/request
/// fields are touched and no ownership escapes on allocation failure.
#[no_mangle]
pub unsafe extern "C" fn f03_execveat_allocate_descriptor_v1(
    file: *const i8, source_line: CInt, error: *mut CInt,
) -> *mut c_void {
    let descriptor = crate::mem_helpers::_ihk_mc_alloc_aligned_pages_node(
        4, 0, 0x000002, -1, 0, CULong::MAX, file.cast_mut(), source_line,
    );
    if descriptor.is_null() {
        kprintf(c"execve(): ERROR: allocating program descriptor\n".as_ptr().cast());
        core::ptr::write(error, -ENOMEM);
        return descriptor;
    }
    crate::string::memset(descriptor, 0, 4 * 4096);
    descriptor
}
