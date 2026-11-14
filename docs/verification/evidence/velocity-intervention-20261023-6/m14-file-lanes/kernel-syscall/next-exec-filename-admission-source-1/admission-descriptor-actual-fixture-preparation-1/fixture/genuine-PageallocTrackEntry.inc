#[repr(C)]
pub struct PageallocTrackEntry {
    file: *mut i8,
    line: CInt,
    alloc_count: IhkAtomic,
    hash: AbiListHead,
    addr_list: AbiListHead,
    addr_list_lock: IhkSpinlock,
}
