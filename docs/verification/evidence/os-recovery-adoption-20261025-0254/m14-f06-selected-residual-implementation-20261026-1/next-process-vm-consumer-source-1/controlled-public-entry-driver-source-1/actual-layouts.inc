#[repr(C)]
pub struct ArchProcessVmRwOffsets {
    thread_proc_offset: SizeT,
    thread_vm_offset: SizeT,
    proc_vm_offset: SizeT,
    proc_status_offset: SizeT,
    proc_ruid_offset: SizeT,
    proc_euid_offset: SizeT,
    proc_suid_offset: SizeT,
    proc_rgid_offset: SizeT,
    proc_egid_offset: SizeT,
    proc_sgid_offset: SizeT,
    process_vm_address_space_offset: SizeT,
    address_space_page_table_offset: SizeT,
    vm_range_flag_offset: SizeT,
}

#[repr(C)]
pub struct ArchProcessVmRwLogRecord {
    event: CInt,
    x: CInt,
    y: CInt,
    z: CInt,
    a: CULong,
    b: CULong,
    c: CULong,
    d: CULong,
    e: CULong,
}

