// M14-F03 source-only: retire the live move-pages public C entry and five
// private C adapters. Reuse the existing unchanged Rust request/ownership body.
// C diagnostic formatting and the architecture SMP migration handler remain debt.
extern "C" {
    #[link_name = "move_pages_log_bridge"]
    fn f03_move_pages_log(event: CInt, value: CULong, error: CInt);
    #[link_name = "move_pages_smp_handler"]
    fn f03_move_pages_smp_handler(cpu: CInt, nr_cpus: CInt, arg: *mut c_void) -> CInt;
}

unsafe extern "C" fn f03_move_pages_verify(vm: *mut ProcessVm, addr: CULong, bytes: SizeT) -> CInt {
    crate::x86_memory_helpers::verify_process_vm(vm, addr as *const c_void, bytes)
}

unsafe extern "C" fn f03_move_pages_table_lock(lock: *mut c_void) {
    crate::spinlock_helpers::__ihk_mc_spinlock_lock_noirq(lock.cast());
}

unsafe extern "C" fn f03_move_pages_table_unlock(lock: *mut c_void) {
    crate::spinlock_helpers::__ihk_mc_spinlock_unlock_noirq(lock.cast());
}

unsafe extern "C" fn f03_move_pages_smp_call(
    cpus: *mut c_void, handler: Option<MovePagesSmpHandlerFn>, arg: *mut c_void,
) -> CInt {
    crate::ap::smp_call_func(cpus.cast::<CpuSet>(), handler, arg)
}

#[no_mangle]
pub unsafe extern "C" fn sys_move_pages(_n: CInt, ctx: *mut X86UserContext) -> CLong {
    // Keep the six original selected Rust getter calls, casts and null-context
    // behavior. Current thread/VM remain live as required by the original entry.
    let pid = crate::x86_cpu_helpers::ihk_mc_syscall_arg0(ctx) as CInt;
    let count = crate::x86_cpu_helpers::ihk_mc_syscall_arg1(ctx);
    let user_virt_addr = crate::x86_cpu_helpers::ihk_mc_syscall_arg2(ctx);
    let user_nodes = crate::x86_cpu_helpers::ihk_mc_syscall_arg3(ctx);
    let user_status = crate::x86_cpu_helpers::ihk_mc_syscall_arg4(ctx);
    let flags = crate::x86_cpu_helpers::ihk_mc_syscall_arg5(ctx) as CInt;
    let vm = (*current_thread_ptr()).vm;
    // Retain three current-CPU samples and evaluate both owner arguments before
    // the helper; this entry does not schedule between the stable-owner samples.
    let proc = (*current_thread_ptr()).proc;
    let cpu_set = addr_of_mut!((*current_thread_ptr()).cpu_set);
    move_pages_body_result(
        pid, count, user_virt_addr, user_nodes, user_status, flags,
        vm, addr_of_mut!((*vm).page_table_lock).cast::<c_void>(),
        cpu_set.cast::<c_void>(), proc.cast::<c_void>(), IHK_MC_AP_NOWAIT,
        size_of::<*mut c_void>(), size_of::<CInt>(), size_of::<CULong>(), size_of::<CULong>(),
        Some(f03_move_pages_verify), Some(syscall_copy_from_user_bridge),
        Some(syscall_copy_to_user_bridge), Some(syscall_alloc_bridge),
        Some(syscall_mckfd_free_bridge), Some(ihk_mc_get_nr_numa_nodes),
        Some(f03_move_pages_table_lock), Some(f03_move_pages_table_unlock),
        Some(f03_move_pages_smp_call), Some(f03_move_pages_smp_handler),
        Some(crate::x86_cpu_helpers::rdtsc), Some(f03_move_pages_log),
    )
}
