// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
/// # Safety
/// vm and its memory_range_lock/range tree retain the original current-thread
/// ownership contract. The range pointer is used only under the same reader lock;
/// no reference or range ownership escapes. filename is converted to address only.
#[no_mangle]
pub unsafe extern "C" fn f03_execveat_filename_admission_v1(
    vm: *mut ProcessVm, filename: *const c_void,
) -> CInt {
    let lock = addr_of_mut!((*vm).memory_range_lock)
        .cast::<crate::lock_helpers::IhkRwSpinlock>();
    crate::lock_helpers::ihk_rwspinlock_read_lock_noirq(lock);
    let start = filename as CULong;
    let range = crate::process_helpers::lookup_process_memory_range(
        vm, start, start.wrapping_add(1),
    );
    if range.is_null() || ((*range).flag & 0x0001_0000) == 0 {
        crate::lock_helpers::ihk_rwspinlock_read_unlock_noirq(lock);
        kprintf(c"execve(): ERROR: filename is bad address\n".as_ptr().cast());
        return -EFAULT;
    }
    crate::lock_helpers::ihk_rwspinlock_read_unlock_noirq(lock);
    0
}
