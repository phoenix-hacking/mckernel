// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Exact Root named legacy clone first-phase slot contract; no ID/valid or other
// argument ownership is transferred. A caller must not have published the request.
#[cfg(f03_clone_request_defined_candidate)]
#[no_mangle]
pub unsafe extern "C" fn f03_clone_request_define_unused45(request: *mut crate::abi::SyscallRequest) {
    // SAFETY: Original local request is naturally aligned, alive, exclusively
    // owned and not yet sent. Raw field addresses do not form a reference to
    // the partially initialized whole struct.
    unsafe {
        core::ptr::addr_of_mut!((*request).args[4]).write(0);
        core::ptr::addr_of_mut!((*request).args[5]).write(0);
    }
}
