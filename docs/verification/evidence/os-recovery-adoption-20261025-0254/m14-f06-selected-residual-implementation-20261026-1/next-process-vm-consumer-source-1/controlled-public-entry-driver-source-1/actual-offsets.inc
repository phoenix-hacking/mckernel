#[used]
#[export_name = "arch_process_vm_rw_kernel_offsets"]
pub static F06_PROCESS_VM_RW_OFFSETS: ArchProcessVmRwOffsets = ArchProcessVmRwOffsets {
    thread_proc_offset: offset_of!(Thread, proc) as SizeT,
    thread_vm_offset: offset_of!(Thread, vm) as SizeT,
    proc_vm_offset: offset_of!(Process, vm) as SizeT,
    proc_status_offset: offset_of!(Process, status) as SizeT,
    proc_ruid_offset: offset_of!(Process, ruid) as SizeT,
    proc_euid_offset: offset_of!(Process, euid) as SizeT,
    proc_suid_offset: offset_of!(Process, suid) as SizeT,
    proc_rgid_offset: offset_of!(Process, rgid) as SizeT,
    proc_egid_offset: offset_of!(Process, egid) as SizeT,
    proc_sgid_offset: offset_of!(Process, sgid) as SizeT,
    process_vm_address_space_offset: offset_of!(ProcessVm, address_space) as SizeT,
    address_space_page_table_offset: offset_of!(crate::abi::AddressSpace, page_table) as SizeT,
    vm_range_flag_offset: offset_of!(VmRange, flag) as SizeT,
};

