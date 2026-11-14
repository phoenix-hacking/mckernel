#![no_std]
#[path="abi.ACTUAL.rs"] mod abi;
mod debug {
#[repr(C)]
pub struct Ddebug {
    pub file: *const i8,
    pub func: *const i8,
    pub fmt: *const i8,
    pub line_flags: u32,
}
}
use core::ffi::c_void;
use abi::{CInt,VmRange};
const PROCESS_VM_RANGE_INSERT_LOG_OVERLAP:CInt=1;
const PROCESS_VM_RANGE_INSERT_LOG_SUCCESS:CInt=2;
unsafe extern "C" {
    fn kprintf(format:*const i8,...)->CInt;
    static mut process_vm_range_insert_debug:debug::Ddebug;
}
/// Preserve the actual process.c log event and variadic ABI. Unknown events
/// do nothing; disabled success logging does not evaluate range fields. The
/// caller retains live ranges through the existing synchronous logger call.
#[no_mangle]
pub unsafe extern "C" fn fixture_rust_vm_range_insert_log_bridge(
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

#[no_mangle]
pub unsafe extern "C" fn fixture_log_layout(out:*mut usize) {
    let values=[core::mem::size_of::<VmRange>(),core::mem::offset_of!(VmRange,start),
        core::mem::offset_of!(VmRange,end),core::mem::offset_of!(VmRange,flag),
        core::mem::size_of::<debug::Ddebug>(),core::mem::align_of::<debug::Ddebug>(),
        core::mem::offset_of!(debug::Ddebug,line_flags),core::mem::size_of::<CInt>()];
    core::ptr::copy_nonoverlapping(values.as_ptr(),out,values.len());
}
