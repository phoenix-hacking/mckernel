// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Source-only witness using the actual module's existing ABI aliases. No model
// struct, new runtime provider, architecture constant or execution queue.
#[no_mangle]
pub static M14_RUST_WAKEUP_TYPE_ABI: [usize; 22] = [
    core::mem::size_of::<CInt>(), core::mem::align_of::<CInt>(),
    core::mem::size_of::<CUInt>(), core::mem::align_of::<CUInt>(),
    core::mem::size_of::<CULong>(), core::mem::align_of::<CULong>(),
    core::mem::size_of::<*mut i8>(), core::mem::align_of::<*mut i8>(),
    core::mem::size_of::<unsafe extern "C" fn(CInt, CUInt)>(),
    core::mem::align_of::<unsafe extern "C" fn(CInt, CUInt)>(),
    core::mem::size_of::<unsafe extern "C" fn(CInt) -> CUInt>(),
    core::mem::size_of::<unsafe extern "C" fn()>(),
    core::mem::size_of::<unsafe extern "C" fn(CUInt, CUInt)>(),
    core::mem::size_of::<*const unsafe extern "C" fn(CInt, CUInt)>(),
    core::mem::size_of::<*const unsafe extern "C" fn(CInt) -> CUInt>(),
    core::mem::size_of::<*const unsafe extern "C" fn()>(),
    core::mem::size_of::<*const *mut i8>(),
    core::mem::size_of::<*const CInt>(),
    core::mem::size_of::<[CUInt; 5]>(), core::mem::align_of::<[CUInt; 5]>(),
    core::mem::size_of::<CInt>(), core::mem::align_of::<CInt>(),
];
