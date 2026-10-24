// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// F06 private fragment: public process-VM read/write entry and provider adapters.
// Reuse the exact existing Rust algorithm and existing lifetime/locking owners.
static F06_PROCESS_VM_RW_OFFSETS: ArchProcessVmRwOffsets = ArchProcessVmRwOffsets {
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
unsafe extern "C" fn f06_process_vm_rw_read_lock(vm: *mut c_void) {
    unsafe {
        crate::lock_helpers::ihk_rwspinlock_read_lock_noirq(
            addr_of_mut!((*vm.cast::<ProcessVm>()).memory_range_lock).cast(),
        );
    }
}
unsafe extern "C" fn f06_process_vm_rw_read_unlock(vm: *mut c_void) {
    unsafe {
        crate::lock_helpers::ihk_rwspinlock_read_unlock_noirq(
            addr_of_mut!((*vm.cast::<ProcessVm>()).memory_range_lock).cast(),
        );
    }
}
unsafe extern "C" fn f06_process_vm_rw_lookup(vm: *mut c_void, start: CULong, end: CULong) -> *mut VmRange {
    unsafe { crate::process_helpers::lookup_process_memory_range(vm.cast(), start, end) }
}
unsafe extern "C" fn f06_process_vm_rw_find(pid: CInt, node: *mut c_void) -> *mut Process {
    unsafe { crate::process_helpers::find_process(pid, node.cast()) }
}
unsafe extern "C" fn f06_process_vm_rw_process_unlock(proc: *mut c_void, node: *mut c_void) {
    unsafe { crate::process_helpers::process_unlock(proc.cast(), node.cast()) }
}
unsafe extern "C" fn f06_process_vm_rw_update_lock(proc: *mut c_void, node: *mut c_void) {
    unsafe {
        crate::lock_helpers::__mcs_rwlock_reader_lock_noirq(
            addr_of_mut!((*proc.cast::<Process>()).update_lock).cast(), node,
        );
    }
}
unsafe extern "C" fn f06_process_vm_rw_update_unlock(proc: *mut c_void, node: *mut c_void) {
    unsafe {
        crate::lock_helpers::__mcs_rwlock_reader_unlock_noirq(
            addr_of_mut!((*proc.cast::<Process>()).update_lock).cast(), node,
        );
    }
}
unsafe extern "C" fn f06_process_vm_rw_hold(vm: *mut c_void) {
    unsafe { crate::process_helpers::hold_process_vm(vm.cast()) }
}
unsafe extern "C" fn f06_process_vm_rw_release(vm: *mut c_void) {
    unsafe { crate::process_helpers::release_process_vm(vm.cast()) }
}
unsafe extern "C" fn f06_process_vm_rw_vtop(
    pt: *mut c_void, virt: CULong, phys: *mut CULong, page_size: *mut CULong,
) -> CInt {
    unsafe { crate::x86_memory_helpers::ihk_mc_pt_virt_to_phys_size(pt, virt as *const c_void, phys, page_size) }
}
unsafe extern "C" fn f06_process_vm_rw_fault(vm: *mut c_void, addr: CULong, reason: CULong) -> CInt {
    unsafe { crate::process_helpers::page_fault_process_vm(vm.cast(), addr as *mut c_void, reason) }
}
unsafe extern "C" fn f06_process_vm_rw_phys(phys: CULong) -> *mut c_void {
    unsafe { crate::x86_memory_helpers::phys_to_virt(phys) }
}
unsafe extern "C" fn f06_process_vm_rw_copy(dst: *mut c_void, src: *const c_void, bytes: SizeT) {
    // Both selected Rust memcpy/fast_memcpy providers already share this exact
    // volatile byte-copy body. Keep its forward copy and zero-byte semantics.
    unsafe { let _ = crate::string::__inline_memcpy(dst, src, bytes); }
}

#[used]
#[link_section = "__verbose"]
static mut F06_PROCESS_VM_IOV_LOCAL_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(file!(), "\0").as_ptr().cast(), func: b"arch_process_vm_rw_log_bridge\0".as_ptr().cast(),
    fmt: core::ptr::null(), line_flags: line!() & 0x00ff_ffff,
};
#[used]
#[link_section = "__verbose"]
static mut F06_PROCESS_VM_IOV_REMOTE_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(file!(), "\0").as_ptr().cast(), func: b"arch_process_vm_rw_log_bridge\0".as_ptr().cast(),
    fmt: core::ptr::null(), line_flags: line!() & 0x00ff_ffff,
};
#[used]
#[link_section = "__verbose"]
static mut F06_PROCESS_VM_FOUND_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(file!(), "\0").as_ptr().cast(), func: b"arch_process_vm_rw_log_bridge\0".as_ptr().cast(),
    fmt: core::ptr::null(), line_flags: line!() & 0x00ff_ffff,
};
#[used]
#[link_section = "__verbose"]
static mut F06_PROCESS_VM_COPY_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(file!(), "\0").as_ptr().cast(), func: b"arch_process_vm_rw_log_bridge\0".as_ptr().cast(),
    fmt: core::ptr::null(), line_flags: line!() & 0x00ff_ffff,
};
unsafe extern "C" fn f06_process_vm_rw_log(record: *const ArchProcessVmRwLogRecord) {
    unsafe {
        // The reused producer initializes only the active event's fields.
        // Read exactly those fields; never form/read a whole initialized record.
        match read_volatile(addr_of!((*record).event)) {
            1 => if read_volatile(addr_of!(F06_PROCESS_VM_IOV_LOCAL_DEBUG.line_flags)) >> 24 != 0 {
                kprintf(b"local_iov[%d].iov_base: 0x%lx, len: %lu\n\0".as_ptr().cast(),
                    read_volatile(addr_of!((*record).x)), read_volatile(addr_of!((*record).a)), read_volatile(addr_of!((*record).b)));
            },
            2 => if read_volatile(addr_of!(F06_PROCESS_VM_IOV_REMOTE_DEBUG.line_flags)) >> 24 != 0 {
                kprintf(b"remote_iov[%d].iov_base: 0x%lx, len: %lu\n\0".as_ptr().cast(),
                    read_volatile(addr_of!((*record).x)), read_volatile(addr_of!((*record).a)), read_volatile(addr_of!((*record).b)));
            },
            3 => if read_volatile(addr_of!(F06_PROCESS_VM_FOUND_DEBUG.line_flags)) >> 24 != 0 {
                let operation = if read_volatile(addr_of!((*record).y)) == PROCESS_VM_READ {
                    b"PROCESS_VM_READ\0".as_ptr().cast::<i8>()
                } else { b"PROCESS_VM_WRITE\0".as_ptr().cast::<i8>() };
                kprintf(b"pid %d found, doing %s: liovcnt: %d, riovcnt: %d \n\0".as_ptr().cast(),
                    read_volatile(addr_of!((*record).x)), operation,
                    read_volatile(addr_of!((*record).a)) as CInt, read_volatile(addr_of!((*record).b)) as CInt);
            },
            4 => if read_volatile(addr_of!(F06_PROCESS_VM_COPY_DEBUG.line_flags)) >> 24 != 0 {
                let direction = if read_volatile(addr_of!((*record).z)) == PROCESS_VM_READ {
                    b"<-\0".as_ptr().cast::<i8>()
                } else { b"->\0".as_ptr().cast::<i8>() };
                kprintf(b"local_iov[%d]: 0x%lx %s remote_iov[%d]: 0x%lx, %lu copied, psize: %lu, rpage_left: %lu\n\0".as_ptr().cast(),
                    read_volatile(addr_of!((*record).x)), read_volatile(addr_of!((*record).a)), direction,
                    read_volatile(addr_of!((*record).y)), read_volatile(addr_of!((*record).b)), read_volatile(addr_of!((*record).c)),
                    read_volatile(addr_of!((*record).d)), read_volatile(addr_of!((*record).e)));
            },
            _ => {},
        }
    }
}

/// Reuse the exact validated process-VM read/write orchestration and its owners.
/// Current-thread, VM and process pointers are borrowed under the original call
/// contract. Both distinct stack lock nodes remain live until the body returns.
/// Existing callbacks alone own locks/remote-VM hold/release and fault/copy order;
/// this entry introduces no retained reference, rollback, retry or error policy.
#[no_mangle]
pub unsafe extern "C" fn do_process_vm_read_writev(
    pid: CInt, local_iov: *const c_void, liovcnt: CULong,
    remote_iov: *const c_void, riovcnt: CULong, flags: CULong, op: CInt,
) -> CInt {
    unsafe {
        let mut find_lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
        let mut update_lock = MaybeUninit::<McsRwlockNode>::uninit();
        let current = read_volatile(addr_of!((*crate::cls::get_this_cpu_local_var()).current));
        arch_process_vm_read_writev_body_result(
            pid, local_iov.cast::<Iovec>(), liovcnt, remote_iov.cast::<Iovec>(), riovcnt, flags, op,
            current.cast(), find_lock.as_mut_ptr().cast(), update_lock.as_mut_ptr().cast(),
            &F06_PROCESS_VM_RW_OFFSETS,
            Some(f06_process_vm_rw_read_lock), Some(f06_process_vm_rw_read_unlock),
            Some(f06_process_vm_rw_lookup), Some(f06_process_vm_rw_find), Some(f06_process_vm_rw_process_unlock),
            Some(f06_process_vm_rw_update_lock), Some(f06_process_vm_rw_update_unlock),
            Some(f06_process_vm_rw_hold), Some(f06_process_vm_rw_release), Some(f06_process_vm_rw_vtop),
            Some(f06_process_vm_rw_fault), Some(f06_process_vm_rw_phys), Some(f06_process_vm_rw_copy),
            Some(f06_process_vm_rw_log),
        )
    }
}
