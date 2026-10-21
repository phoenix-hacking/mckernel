/// Complete gettid-pool request used by the CLONE_VM thread path.
///
/// # Safety
/// `request` must point to the caller's DMA-aligned, writable SyscallRequest
/// storage for this entire synchronous call. The callbacks must match their C
/// ABI and retain the existing do_syscall ownership/lifetime contract. `tids`
/// is translated even for zero count or a null pointer, as in the C fallback.
#[no_mangle]
pub unsafe extern "C" fn syscall_settid_body_result(
    request: *mut SyscallRequest,
    nr_tids: CInt,
    tids: *mut CInt,
    gettid_nr: CInt,
    virt_to_phys_fn: SyscallVirtToPhysFn,
    get_cpu_fn: SyscallGetCpuFn,
    syscall_fn: SyscallRequestCallFn,
    log_fn: unsafe extern "C" fn(CInt),
) -> CInt {
    // Zero every byte, including any representation padding, before fields.
    core::ptr::write_bytes(request.cast::<u8>(), 0, size_of::<SyscallRequest>());
    write(addr_of_mut!((*request).number), gettid_nr as CULong);
    write(addr_of_mut!((*request).args[4]), nr_tids as CULong);
    let tids_pa = virt_to_phys_fn(tids.cast::<c_void>());
    write(addr_of_mut!((*request).args[5]), tids_pa);
    let cpu = get_cpu_fn();
    // C assigns long do_syscall's return to int before checking its sign.
    let ret = syscall_fn(request, cpu) as CInt;
    if ret < 0 {
        log_fn(ret);
    }
    ret
}

