pub unsafe extern "C" fn process_add_range_mark_xpmem_bridge(range: *mut VmRange) {
        // SAFETY: Original caller owns this live flag publication; the same
        // actual u32 memobj field is modified without creating shared references.
        unsafe { (*(*range).memobj.cast::<Memobj>()).flags |= MF_XPMEM };
    }

pub extern "C" fn shmobj_initial_flags_result() -> CInt {
    MF_SHM
}

pub extern "C" fn shmobj_indexed_flags_result(flags: CInt) -> CInt {
    flags | MF_SHMDT_OK | MF_IS_REMOVABLE
}

pub extern "C" fn mmap_is_shared(flags: CInt) -> CInt {
    if (flags & MAP_SHARED) != 0 {
        1
    } else {
        0
    }
}
