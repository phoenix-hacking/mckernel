// Exact unchanged production definitions below; imports only adapt namespace.
use core::{ffi::c_void, mem::offset_of, ptr::{addr_of_mut, null_mut, write}};
use crate::abi::{CInt, CLong, CULong, SizeT, SyscallRequest, Thread, ProcessVm};
use crate::cls::get_this_cpu_local_var;
use crate::x86_local::ihk_mc_get_processor_id;
use crate::production_memory_provider::syscall_policy_do_syscall3_bridge;

const EINVAL: CInt = 22;
const PROT_READ: CInt = 0x01;
const PROT_WRITE: CInt = 0x02;
const PROT_EXEC: CInt = 0x04;
type SyscallRequestCallFn = unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong;
type SyscallDoSyscall3Fn = unsafe extern "C" fn(CInt, CULong, CULong, CULong) -> CLong;
type DoMunmapVoidFn = unsafe extern "C" fn();
type DoMunmapRemoveRangeFn = unsafe extern "C" fn(*mut c_void, CULong, CULong, *mut CInt) -> CInt;
type DoMunmapClearHostFn = unsafe extern "C" fn(CULong, SizeT, CInt) -> CLong;
type DoMunmapLogFn = unsafe extern "C" fn(CULong, SizeT, CInt);
type ClearHostPteLogFn = unsafe extern "C" fn(CLong);
type MprotectSetHostVmaFn = unsafe extern "C" fn(CULong, SizeT, CInt, CInt) -> CInt;

#[inline(always)]
unsafe fn field_ptr<T>(base: *mut u8, offset: SizeT) -> *mut T {
    base.add(offset).cast::<T>()
}

unsafe fn current_thread_ptr() -> *mut Thread {
    let cpu = get_this_cpu_local_var();
    if cpu.is_null() {
        null_mut()
    } else {
        (*cpu).current
    }
}

#[no_mangle]
pub unsafe extern "C" fn syscall_generic_forwarding_body_result(
    request: *mut SyscallRequest,
    n: CInt,
    arg0: CULong,
    arg1: CULong,
    arg2: CULong,
    arg3: CULong,
    arg4: CULong,
    arg5: CULong,
    cpu: CInt,
    do_syscall_fn: Option<SyscallRequestCallFn>,
) -> CLong {
    let Some(do_syscall_fn) = do_syscall_fn else {
        return -(EINVAL as CLong);
    };
    if request.is_null() {
        return -(EINVAL as CLong);
    }

    write(addr_of_mut!((*request).number), n as CULong);
    write(addr_of_mut!((*request).args[0]), arg0);
    write(addr_of_mut!((*request).args[1]), arg1);
    write(addr_of_mut!((*request).args[2]), arg2);
    write(addr_of_mut!((*request).args[3]), arg3);
    write(addr_of_mut!((*request).args[4]), arg4);
    write(addr_of_mut!((*request).args[5]), arg5);

    do_syscall_fn(request, cpu)
}

#[no_mangle]
pub unsafe extern "C" fn do_munmap_body_result(
    vm: *mut c_void,
    proc: *mut c_void,
    addr: CULong,
    len: SizeT,
    holding_memory_range_lock: CInt,
    proc_straight_va_offset: SizeT,
    proc_straight_len_offset: SizeT,
    begin_fn: Option<DoMunmapVoidFn>,
    remove_range_fn: Option<DoMunmapRemoveRangeFn>,
    clear_host_pte_fn: Option<DoMunmapClearHostFn>,
    set_host_vma_fn: Option<MprotectSetHostVmaFn>,
    finish_fn: Option<DoMunmapVoidFn>,
    log_fn: Option<DoMunmapLogFn>,
) -> CInt {
    if let Some(begin) = begin_fn {
        begin();
    }

    let mut ro_freed = 0;
    let mut error = if let Some(remove_range) = remove_range_fn {
        remove_range(vm, addr, addr.wrapping_add(len as CULong), &mut ro_freed)
    } else {
        -EINVAL
    };

    let straight_va = *field_ptr::<CULong>(proc.cast::<u8>(), proc_straight_va_offset);
    let straight_len = *field_ptr::<SizeT>(proc.cast::<u8>(), proc_straight_len_offset);
    if straight_va == 0
        || addr < straight_va
        || addr.wrapping_add(len as CULong) > straight_va.wrapping_add(straight_len as CULong)
    {
        if error != 0 || ro_freed == 0 {
            if let Some(clear_host_pte) = clear_host_pte_fn {
                let clear_error = clear_host_pte(addr, len, holding_memory_range_lock);
                if error == 0 {
                    error = clear_error as CInt;
                }
            }
        } else {
            error = if let Some(set_host_vma) = set_host_vma_fn {
                set_host_vma(
                    addr,
                    len,
                    PROT_READ | PROT_WRITE | PROT_EXEC,
                    holding_memory_range_lock,
                )
            } else {
                -EINVAL
            };
        }
    }

    if let Some(finish) = finish_fn {
        finish();
    }
    if let Some(log) = log_fn {
        log(addr, len, error);
    }
    error
}

#[no_mangle]
pub unsafe extern "C" fn clear_host_pte_body_result(
    vm: *mut c_void,
    addr: CULong,
    len: SizeT,
    holding_memory_range_lock: CInt,
    vm_lock_taken_offset: SizeT,
    cpu: CInt,
    syscall_nr: CInt,
    forward_fn: Option<SyscallDoSyscall3Fn>,
    log_fn: Option<ClearHostPteLogFn>,
) -> CLong {
    if holding_memory_range_lock != 0 {
        *field_ptr::<CInt>(vm.cast::<u8>(), vm_lock_taken_offset) = cpu;
    }

    let lerror = if let Some(forward) = forward_fn {
        forward(syscall_nr, addr, len as CULong, 0)
    } else {
        (-EINVAL) as CLong
    };

    if holding_memory_range_lock != 0 {
        *field_ptr::<CInt>(vm.cast::<u8>(), vm_lock_taken_offset) = -1;
    }
    if lerror != 0 {
        if let Some(log) = log_fn {
            log(lerror);
        }
    }
    lerror
}

#[no_mangle]
pub extern "C" fn set_host_vma_body_result(
    _addr: CULong,
    _len: SizeT,
    _prot: CInt,
    _holding_memory_range_lock: CInt,
) -> CInt {
    #[cfg(native_linux_irq_work_v6_12)]
    unsafe {
        let thread = current_thread_ptr();
        if thread.is_null() || (*thread).vm.is_null() {
            return -EINVAL;
        }
        // Keep the mirror VMA's original protection and invalidate cached PFNs.
        // Subsequent host faults must consult the new guest PTE permissions.
        // The existing bridge publishes the held-range-lock flag while the
        // offload runs, then restores it before the caller unlocks that range.
        return clear_host_pte_body_result(
            (*thread).vm.cast::<c_void>(),
            _addr,
            _len,
            _holding_memory_range_lock,
            offset_of!(ProcessVm, is_memory_range_lock_taken),
            ihk_mc_get_processor_id(),
            11,
            Some(syscall_policy_do_syscall3_bridge),
            None,
        ) as CInt;
    }
    #[cfg(not(native_linux_irq_work_v6_12))]
    {
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn syscall_get_processor_id_bridge() -> CInt {
    // SAFETY: The original architecture entry is called under the same CPU context;
    // no MSR access, local-data read or fallback behavior is reimplemented here.
    unsafe { crate::x86_local::ihk_mc_get_processor_id() }
}

mod f03_clear_host_pte_entry_v1 {
    use core::mem::offset_of;
    use crate::abi::{CInt, CLong, CULong, ProcessVm, SizeT};
    use super::{clear_host_pte_body_result, syscall_get_processor_id_bridge,
                ClearHostPteLogFn, SyscallDoSyscall3Fn};

    #[repr(C)]
    struct ClearHostBinding {
        munmap_nr: CInt,
        forward: Option<SyscallDoSyscall3Fn>,
        log: Option<ClearHostPteLogFn>,
    }
    unsafe extern "C" {
        static f03_clear_host_pte_binding_v1: ClearHostBinding;
    }

    /// Preserve the existing host-PTE request and borrowed VM lock-state protocol.
    ///
    /// # Safety
    /// The current CPU/thread/VM remain live throughout the original synchronous
    /// forwarding operation. The caller retains the original range-lock ownership
    /// when `holding_lock` is nonzero. No range is acquired, released or remapped
    /// by this wrapper; the genuine existing forwarding provider retains its own
    /// complete context/request and endpoint contracts, including existing holds.
    #[no_mangle]
    pub unsafe extern "C" fn clear_host_pte(
        addr: CULong, len: SizeT, holding_lock: CInt,
    ) -> CLong {
        // SAFETY: Same original CPU-local/thread lookup and borrowed VM.
        let cpu = unsafe { crate::cls::get_this_cpu_local_var() };
        let thread = unsafe { (*cpu).current };
        let vm = unsafe { (*thread).vm };
        let processor = unsafe { syscall_get_processor_id_bridge() };
        // SAFETY: Immutable header-derived syscall number and genuine existing
        // providers. The exact complete Rust body publishes CPU before forward,
        // restores -1 before logging, and returns the original signed result.
        unsafe {
            let binding = &f03_clear_host_pte_binding_v1;
            clear_host_pte_body_result(
                vm.cast(), addr, len, holding_lock,
                offset_of!(ProcessVm, is_memory_range_lock_taken),
                processor, binding.munmap_nr, binding.forward, binding.log,
            )
        }
    }
}

mod f03_do_munmap_entry_v1 {
    use core::{ffi::c_void, mem::offset_of};
    use crate::abi::{CInt, CULong, Process, SizeT};
    use super::{do_munmap_body_result, DoMunmapVoidFn, DoMunmapRemoveRangeFn,
                DoMunmapClearHostFn, MprotectSetHostVmaFn, DoMunmapLogFn};

    #[repr(C)]
    struct DoMunmapBinding {
        begin: Option<DoMunmapVoidFn>,
        remove_range: Option<DoMunmapRemoveRangeFn>,
        clear_host: Option<DoMunmapClearHostFn>,
        set_host: Option<MprotectSetHostVmaFn>,
        finish: Option<DoMunmapVoidFn>,
        log: Option<DoMunmapLogFn>,
    }
    unsafe extern "C" {
        static f03_do_munmap_binding_v1: DoMunmapBinding;
    }

    /// Enter the existing unmap body with the original borrowed process and VM.
    ///
    /// # Safety
    /// The current CPU/thread/process/VM and immutable provider binding remain
    /// live throughout this synchronous operation. Callers retain the original
    /// range-lock contract indicated by `holding_lock`; this entry acquires no
    /// additional lock and preserves the existing begin/remove/host/finish/log
    /// lifetime and error precedence in `do_munmap_body_result`.
    #[no_mangle]
    pub unsafe extern "C" fn do_munmap(
        addr: *mut c_void, len: SizeT, holding_lock: CInt,
    ) -> CInt {
        // SAFETY: Identical original CPU-local lookup and live borrowed fields.
        let cpu = unsafe { crate::cls::get_this_cpu_local_var() };
        let thread = unsafe { (*cpu).current };
        let vm = unsafe { (*thread).vm };
        let proc = unsafe { (*thread).proc };
        // SAFETY: The repr(C) fields match the genuine C provider typedefs.
        // Real Rust Process offsets replace the corresponding C offsetof values.
        unsafe {
            let binding = &f03_do_munmap_binding_v1;
            do_munmap_body_result(
                vm.cast(), proc.cast(), addr as CULong, len, holding_lock,
                offset_of!(Process, straight_va), offset_of!(Process, straight_len),
                binding.begin, binding.remove_range, binding.clear_host,
                binding.set_host, binding.finish, binding.log,
            )
        }
    }
}
