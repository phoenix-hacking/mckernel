#[repr(C)]
pub struct PageallocTrackAddrEntry {
    addr: *mut c_void,
    runcount: CInt,
    list: AbiListHead,
    entry: *mut PageallocTrackEntry,
    hash: AbiListHead,
    npages: CInt,
}
