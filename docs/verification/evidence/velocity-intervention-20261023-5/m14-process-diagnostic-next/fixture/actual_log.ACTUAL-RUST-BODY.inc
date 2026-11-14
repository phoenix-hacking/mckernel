/// Preserve the actual process.c log event and variadic ABI. Unknown events
/// do nothing; disabled success logging does not evaluate range fields. The
/// caller retains live ranges through the existing synchronous logger call.
#[no_mangle]
pub unsafe extern "C" fn vm_range_insert_log_bridge(
    event: CInt,
    vm: *mut c_void,
    newrange: *mut VmRange,
    range: *mut VmRange,
) {
    if event == PROCESS_VM_RANGE_INSERT_LOG_OVERLAP {
        let _ = kprintf(
            b"vm_range_insert(%p,%lx-%lx %x): overlap %lx-%lx %lx\n\0".as_ptr().cast(),
            vm,
            (*newrange).start,
            (*newrange).end,
            (*newrange).flag,
            (*range).start,
            (*range).end,
            (*range).flag,
        );
    } else if event == PROCESS_VM_RANGE_INSERT_LOG_SUCCESS {
        let flags = core::ptr::read_volatile(
            core::ptr::addr_of!(process_vm_range_insert_debug.line_flags),
        ) >> 24;
        if flags != 0 {
            let _ = kprintf(
                b"vm_range_insert: %p,%p: %lx-%lx %x\n\0".as_ptr().cast(),
                vm,
                newrange,
                (*newrange).start,
                (*newrange).end,
                (*newrange).flag,
            );
        }
    }
}
