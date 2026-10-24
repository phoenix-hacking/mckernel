// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Defined do_execveat end-label ownership slice; not the full exec lifecycle.
/// # Safety
/// Non-null envp_flat/argv_flat are the distinct owned kmalloc allocations from
/// the original flatten calls; descriptor owns exactly four kernel pages. Each
/// handle is consumed exactly once in the original envp/argv/descriptor order.
/// `file` is the original static NUL-terminated C source string, and the three
/// source-line values identify the byte-bound C preimage tracking sites. No
/// handle may be accessed after return; original C locals remain unused/dangling.
#[no_mangle]
pub unsafe extern "C" fn f03_execveat_release_temporaries_v1(
    envp_flat: *mut c_void,
    argv_flat: *mut c_void,
    descriptor: *mut c_void,
    file: *const i8,
    envp_line: CInt,
    argv_line: CInt,
    descriptor_line: CInt,
) {
    if !envp_flat.is_null() {
        crate::mem_helpers::kfree_tracked(envp_flat, file.cast_mut(), envp_line);
    }
    if !argv_flat.is_null() {
        crate::mem_helpers::kfree_tracked(argv_flat, file.cast_mut(), argv_line);
    }
    crate::mem_helpers::_ihk_mc_free_pages(descriptor, 4, 0, file.cast_mut(), descriptor_line);
}
