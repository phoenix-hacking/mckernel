#![no_std]
#[path="actual-abi-excerpts.rs"] mod abi;
#[path="actual-storage-module.rs"] mod actual_storage;
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Proposed HOST-only companion, outside production source. Link the actual
// process_global_storage provider extracted/bound by the existing data5 producer.
unsafe extern "C" {
    static mut idle_halt: crate::abi::CInt;
    static mut allow_oversubscribe: crate::abi::CInt;
    static mut time_sharing: crate::abi::CInt;
}
unsafe fn f02_control_pointer(slot: u32) -> *mut crate::abi::CInt {
    match slot {
        0 => core::ptr::addr_of_mut!(idle_halt),
        1 => core::ptr::addr_of_mut!(allow_oversubscribe),
        2 => core::ptr::addr_of_mut!(time_sharing),
        _ => core::ptr::null_mut(),
    }
}
#[no_mangle]
pub unsafe extern "C" fn f02_read_control(slot: u32) -> crate::abi::CInt {
    unsafe { core::ptr::read(f02_control_pointer(slot)) }
}
#[no_mangle]
pub unsafe extern "C" fn f02_write_control(slot: u32, value: crate::abi::CInt) {
    unsafe { core::ptr::write(f02_control_pointer(slot), value) };
}
#[no_mangle]
pub unsafe extern "C" fn f02_control_address(slot: u32) -> *mut core::ffi::c_void {
    unsafe { f02_control_pointer(slot).cast() }
}
