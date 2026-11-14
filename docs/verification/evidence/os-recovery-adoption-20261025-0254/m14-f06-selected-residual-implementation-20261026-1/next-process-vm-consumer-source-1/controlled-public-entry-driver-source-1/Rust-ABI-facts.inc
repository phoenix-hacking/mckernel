// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Future fixture adapter only; include after actual body+new fragment in its module.
#[no_mangle]
pub extern "C" fn f06_process_vm_rw_Rust_ABI_fact(i: usize) -> usize {
    let o = &F06_PROCESS_VM_RW_OFFSETS;
    let facts = [
        size_of::<Thread>(), size_of::<Process>(), size_of::<ProcessVm>(),
        size_of::<crate::abi::AddressSpace>(), size_of::<Iovec>(),
        size_of::<McsRwlockNodeIrqsave>(), align_of::<McsRwlockNodeIrqsave>(),
        size_of::<McsRwlockNode>(), align_of::<McsRwlockNode>(),
        o.thread_proc_offset, o.thread_vm_offset, o.proc_vm_offset,
        o.proc_status_offset, o.proc_ruid_offset, o.proc_euid_offset, o.proc_suid_offset,
        o.proc_rgid_offset, o.proc_egid_offset, o.proc_sgid_offset,
        o.process_vm_address_space_offset, o.address_space_page_table_offset,
        o.vm_range_flag_offset,
    ];
    facts.get(i).copied().unwrap_or(usize::MAX)
}
