// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// F06 source-only next slice: complete global VDSO mapping orchestration.
// Root removes the old extern declaration of vdso_map_global_pages before merge.
// Existing ArchVdso/state bridge, Rust memory/CPU providers and Ddebug ABI reused.
extern "C" {
    #[link_name = "pvti"]
    static mut ARCH_VDSO_GLOBAL_PVTI: *mut c_void;
    #[link_name = "pvti_npages"]
    static mut ARCH_VDSO_GLOBAL_PVTI_NPAGES: CInt;
}

type ArchVdsoGlobalSetupFn = unsafe extern "C" fn() -> CInt;
type ArchVdsoGlobalPhysFn = unsafe extern "C" fn(*mut c_void) -> CULong;
type ArchVdsoGlobalMapFn =
    unsafe extern "C" fn(*mut c_void, *mut c_void, CULong, CULong) -> CInt;
type ArchVdsoGlobalLogFn = unsafe extern "C" fn(CInt, CInt);

const VDSO_GLOBAL_LOG_ENTER: CInt = 0;
const VDSO_GLOBAL_LOG_VVAR_FAILED: CInt = 1;
const VDSO_GLOBAL_LOG_HPET_FAILED: CInt = 2;
const VDSO_GLOBAL_LOG_SETUP_FAILED: CInt = 3;
const VDSO_GLOBAL_LOG_PVTI_FAILED: CInt = 4;
const VDSO_GLOBAL_LOG_EXIT: CInt = 5;

#[used]
#[link_section = "__verbose"]
static mut VDSO_GLOBAL_ENTER_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(file!(), "\0").as_ptr().cast(),
    func: b"vdso_map_global_pages\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: line!() & 0x00ff_ffff,
};
#[used]
#[link_section = "__verbose"]
static mut VDSO_GLOBAL_EXIT_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(file!(), "\0").as_ptr().cast(),
    func: b"vdso_map_global_pages\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: line!() & 0x00ff_ffff,
};

unsafe extern "C" fn arch_vdso_global_log(event: CInt, error: CInt) {
    unsafe {
        match event {
            VDSO_GLOBAL_LOG_ENTER => {
                if read_volatile(addr_of!(VDSO_GLOBAL_ENTER_DEBUG.line_flags)) >> 24 != 0 {
                    kprintf(b"vdso_map_global_pages()\n\0".as_ptr().cast());
                }
            }
            VDSO_GLOBAL_LOG_VVAR_FAILED => {
                kprintf(b"vdso_map_global_pages: mapping vvar failed. %d\n\0".as_ptr().cast(), error);
            }
            VDSO_GLOBAL_LOG_HPET_FAILED => {
                kprintf(b"vdso_map_global_pages: mapping hpet failed. %d\n\0".as_ptr().cast(), error);
            }
            VDSO_GLOBAL_LOG_SETUP_FAILED => {
                kprintf(b"vdso_map_global_pages: arch_setup_pvclock failed. %d\n\0".as_ptr().cast(), error);
            }
            VDSO_GLOBAL_LOG_PVTI_FAILED => {
                kprintf(b"vdso_map_global_pages: mapping pvti failed. %d\n\0".as_ptr().cast(), error);
            }
            VDSO_GLOBAL_LOG_EXIT => {
                if read_volatile(addr_of!(VDSO_GLOBAL_EXIT_DEBUG.line_flags)) >> 24 != 0 {
                    kprintf(b"vdso_map_global_pages(): %d\n\0".as_ptr().cast(), error);
                }
            }
            _ => {}
        }
    }
}

/// Preserve the original partial-map ownership: stop at the first setup/map
/// error, leave successful prior mappings in place, and never free/rollback.
/// vdso and both global slots must remain live under the original boot/setup
/// exclusion. Callback effects on later state/slots are observed in order.
#[no_mangle]
pub unsafe extern "C" fn vdso_map_global_pages_body_result(
    vdso: *mut ArchVdso,
    pvti_slot: *mut *mut c_void,
    pvti_npages_slot: *mut CInt,
    setup_fn: ArchVdsoGlobalSetupFn,
    phys_fn: ArchVdsoGlobalPhysFn,
    map_fn: ArchVdsoGlobalMapFn,
    log_fn: ArchVdsoGlobalLogFn,
) -> CInt {
    unsafe {
        log_fn(VDSO_GLOBAL_LOG_ENTER, 0);
        let ordinary_attr = PTATTR_ACTIVE | PTATTR_USER | PTATTR_NO_EXECUTE;
        if !read_volatile(addr_of!((*vdso).vvar_virt)).is_null()
            && read_volatile(addr_of!((*vdso).vvar_is_global)) != 0
        {
            let error = map_fn(
                null_mut(),
                read_volatile(addr_of!((*vdso).vvar_virt)),
                read_volatile(addr_of!((*vdso).vvar_phys)) as CULong,
                ordinary_attr,
            );
            if error != 0 {
                log_fn(VDSO_GLOBAL_LOG_VVAR_FAILED, error);
                log_fn(VDSO_GLOBAL_LOG_EXIT, error);
                return error;
            }
        }
        if !read_volatile(addr_of!((*vdso).hpet_virt)).is_null()
            && read_volatile(addr_of!((*vdso).hpet_is_global)) != 0
        {
            let error = map_fn(
                null_mut(),
                read_volatile(addr_of!((*vdso).hpet_virt)),
                read_volatile(addr_of!((*vdso).hpet_phys)) as CULong,
                ordinary_attr | PTATTR_UNCACHABLE,
            );
            if error != 0 {
                log_fn(VDSO_GLOBAL_LOG_HPET_FAILED, error);
                log_fn(VDSO_GLOBAL_LOG_EXIT, error);
                return error;
            }
        }
        if !read_volatile(addr_of!((*vdso).pvti_virt)).is_null()
            && read_volatile(addr_of!((*vdso).pvti_is_global)) != 0
        {
            let error = setup_fn();
            if error != 0 {
                log_fn(VDSO_GLOBAL_LOG_SETUP_FAILED, error);
                log_fn(VDSO_GLOBAL_LOG_EXIT, error);
                return error;
            }
            // PAGE_SIZE is C 1UL<<PAGE_SHIFT. Match its unsigned 64-bit
            // displacement and the old destination-minus/source-plus order.
            let mut i: CInt = 0;
            while i < read_volatile(pvti_npages_slot) {
                let displacement = (i as CULong).wrapping_mul(PAGE_SIZE) as usize;
                let virt = read_volatile(addr_of!((*vdso).pvti_virt))
                    .cast::<u8>().wrapping_sub(displacement).cast::<c_void>();
                let source = read_volatile(pvti_slot)
                    .cast::<u8>().wrapping_add(displacement).cast::<c_void>();
                let phys = phys_fn(source);
                let error = map_fn(null_mut(), virt, phys, ordinary_attr);
                if error != 0 {
                    log_fn(VDSO_GLOBAL_LOG_PVTI_FAILED, error);
                    log_fn(VDSO_GLOBAL_LOG_EXIT, error);
                    return error;
                }
                i += 1;
            }
        }
        log_fn(VDSO_GLOBAL_LOG_EXIT, 0);
        0
    }
}

#[no_mangle]
pub unsafe extern "C" fn vdso_map_global_pages() -> CInt {
    // Reuse the existing state-provider contract already used by the selected
    // Rust arch_setup_vdso caller. It returns addresses of stable C data only.
    let (vdso, _, _) = match unsafe { arch_vdso_state() } {
        Ok(state) => state,
        Err(error) => return error,
    };
    unsafe {
        vdso_map_global_pages_body_result(
            vdso,
            addr_of_mut!(ARCH_VDSO_GLOBAL_PVTI),
            addr_of_mut!(ARCH_VDSO_GLOBAL_PVTI_NPAGES),
            crate::x86_cpu_helpers::arch_setup_pvclock,
            crate::x86_memory_helpers::virt_to_phys,
            crate::x86_memory_helpers::ihk_mc_pt_set_page,
            arch_vdso_global_log,
        )
    }
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// F06 private fragment: retire the existing ptrace_report_signal C entry and
// its seven private adapters. Keep the accepted Rust signal algorithm intact.
unsafe extern "C" {
    #[link_name = "do_kill"]
    fn f06_ptrace_report_signal_do_kill(
        thread: *mut Thread, pid: CInt, tid: CInt, sig: CInt,
        info: *mut SigInfo, ptracecont: CInt,
    ) -> CULong;
}

static F06_PTRACE_REPORT_SIGNAL_OFFSETS: PtraceReportSignalOffsets = PtraceReportSignalOffsets {
    thread_proc_offset: offset_of!(Thread, proc) as SizeT,
    thread_tid_offset: offset_of!(Thread, tid) as SizeT,
    thread_status_offset: offset_of!(Thread, status) as SizeT,
    thread_exit_status_offset: offset_of!(Thread, exit_status) as SizeT,
    thread_signal_flags_offset: offset_of!(Thread, signal_flags) as SizeT,
    thread_ptrace_offset: offset_of!(Thread, ptrace) as SizeT,
    thread_ptrace_debugreg_offset: offset_of!(Thread, ptrace_debugreg) as SizeT,
    thread_report_proc_offset: offset_of!(Thread, report_proc) as SizeT,
    proc_pid_offset: offset_of!(Process, pid) as SizeT,
    proc_parent_offset: offset_of!(Process, parent) as SizeT,
    proc_main_thread_offset: offset_of!(Process, main_thread) as SizeT,
    proc_status_offset: offset_of!(Process, status) as SizeT,
    proc_update_lock_offset: offset_of!(Process, update_lock) as SizeT,
    proc_waitpid_q_offset: offset_of!(Process, waitpid_q) as SizeT,
};

unsafe extern "C" fn f06_ptrace_report_signal_lock(lock: *mut c_void, node: *mut c_void) {
    unsafe { crate::lock_helpers::__mcs_rwlock_writer_lock(lock.cast(), node.cast()) }
}
unsafe extern "C" fn f06_ptrace_report_signal_unlock(lock: *mut c_void, node: *mut c_void) {
    unsafe { crate::lock_helpers::__mcs_rwlock_writer_unlock(lock.cast(), node.cast()) }
}
unsafe extern "C" fn f06_ptrace_report_signal_save(debugreg: *mut c_void) {
    unsafe { crate::x86_cpu_helpers::save_debugreg(debugreg.cast::<CULong>()) }
}
unsafe extern "C" fn f06_ptrace_report_signal_wake(waitq: *mut c_void) {
    // RuntimeWaitq and C waitq_t are the already selected waitq ABI.
    unsafe { crate::waitq::waitq_wakeup(waitq.cast::<RuntimeWaitq>()) }
}
unsafe extern "C" fn f06_ptrace_report_signal_kill(
    thread: *mut c_void, pid: CInt, tid: CInt, sig: CInt,
    info: *const SigInfo, ptracecont: CInt,
) -> CLong {
    // The old C adapter implicitly converted do_kill's unsigned long to long.
    // Keep its exact bits; the signal body deliberately ignores the return.
    unsafe {
        f06_ptrace_report_signal_do_kill(
            thread.cast::<Thread>(), pid, tid, sig, info.cast_mut(), ptracecont,
        ) as CLong
    }
}

#[used]
#[link_section = "__verbose"]
static mut F06_PTRACE_SIGNAL_ENTER_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(file!(), "\0").as_ptr().cast(),
    func: b"arch_ptrace_signal_log_bridge\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: line!() & 0x00ff_ffff,
};
#[used]
#[link_section = "__verbose"]
static mut F06_PTRACE_SIGNAL_SLEEP_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(file!(), "\0").as_ptr().cast(),
    func: b"arch_ptrace_signal_log_bridge\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: line!() & 0x00ff_ffff,
};
#[used]
#[link_section = "__verbose"]
static mut F06_PTRACE_SIGNAL_WAKE_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
    file: concat!(file!(), "\0").as_ptr().cast(),
    func: b"arch_ptrace_signal_log_bridge\0".as_ptr().cast(),
    fmt: core::ptr::null(),
    line_flags: line!() & 0x00ff_ffff,
};
unsafe extern "C" fn f06_ptrace_report_signal_log(event: CInt, value: CInt, result: CInt) {
    unsafe {
        match event {
            PTRACE_REPORT_SIGNAL_LOG_ENTER => {
                if read_volatile(addr_of!(F06_PTRACE_SIGNAL_ENTER_DEBUG.line_flags)) >> 24 != 0 {
                    kprintf(b"ptrace_report_signal, tid=%d, pid=%d\n\0".as_ptr().cast(), value, result);
                }
            }
            PTRACE_REPORT_SIGNAL_LOG_SLEEPING => {
                if read_volatile(addr_of!(F06_PTRACE_SIGNAL_SLEEP_DEBUG.line_flags)) >> 24 != 0 {
                    kprintf(b"ptrace_report_signal,sleeping\n\0".as_ptr().cast());
                }
            }
            PTRACE_REPORT_SIGNAL_LOG_WAKE => {
                if read_volatile(addr_of!(F06_PTRACE_SIGNAL_WAKE_DEBUG.line_flags)) >> 24 != 0 {
                    kprintf(b"ptrace_report_signal,wake up\n\0".as_ptr().cast());
                }
            }
            _ => {}
        }
    }
}

/// Preserve the existing synchronous ptrace notification and stack-node lifetime.
/// The live current CPU/thread and reported thread/process are borrowed only;
/// this entry neither acquires nor releases their owner references. The reused
/// body restores the update lock/IRQ state before main-parent wake and schedule.
/// The lock node stays live through every callback, including scheduler return.
#[no_mangle]
pub unsafe extern "C" fn ptrace_report_signal(thread: *mut Thread, sig: CInt) {
    unsafe {
        let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
        let current = read_volatile(addr_of!((*crate::cls::get_this_cpu_local_var()).current));
        // Existing C public entry is void and intentionally ignores body status.
        let _ = ptrace_report_signal_body_result(
            thread.cast(), sig, current.cast(), &F06_PTRACE_REPORT_SIGNAL_OFFSETS,
            lock.as_mut_ptr().cast(),
            Some(f06_ptrace_report_signal_lock), Some(f06_ptrace_report_signal_unlock),
            Some(f06_ptrace_report_signal_save), Some(f06_ptrace_report_signal_wake),
            Some(f06_ptrace_report_signal_kill), Some(schedule),
            Some(f06_ptrace_report_signal_log),
        );
    }
}
