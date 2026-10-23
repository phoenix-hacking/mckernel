/// Own the selected process.c insertion entry in Rust. The caller holds the
/// existing VM range exclusion and supplies a live ProcessVm, exactly as for
/// the former C wrapper; the helper retains all tree mutation and error order.
#[no_mangle]
pub unsafe extern "C" fn vm_range_insert(
    vm: *mut ProcessVm,
    newrange: *mut VmRange,
) -> CInt {
    process_vm_range_insert_result(
        (&raw mut (*vm).vm_range_tree).cast::<RbRoot>(),
        newrange,
        vm.cast(),
        Some(vm_range_insert_log_bridge),
        Some(vm_range_insert_dump_bridge),
    )
}
