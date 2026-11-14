// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Append-only private candidate; canonical syscall_policy.rs is coordinator-owned.
mod f06_do_kill_wakeup_candidate {
    use core::mem::{size_of, MaybeUninit};
    use core::ptr::{addr_of, addr_of_mut, read_volatile};

    use crate::abi::{CInt, CULong, Process, SigInfo, SigInfoChild, Thread};

    use super::{CLD_CONTINUED, PS_INTERRUPTIBLE, PS_RUNNING, PS_STOPPED, PS_TRACED,
        SIGNAL_STOP_CONTINUED, SIGCHLD, SIGCONT, SIGKILL};

    unsafe extern "C" {
        #[link_name = "do_kill"]
        fn notify_parent(
            thread: *mut Thread, pid: CInt, tid: CInt, sig: CInt,
            info: *mut SigInfo, ptracecont: CInt,
        ) -> CULong;
        fn ihk_mc_get_vector(vector_type: CInt) -> CInt;
        fn ihk_mc_interrupt_cpu(cpu: CInt, vector: CInt) -> CInt;
    }

    #[used]
    #[link_section = "__verbose"]
    static mut IPI_DEBUG: crate::debug::Ddebug = crate::debug::Ddebug {
        file: concat!(file!(), "\0").as_ptr().cast(),
        func: b"do_kill\0".as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: line!() & 0x00ff_ffff,
    };

    /// Complete existing do_kill tail after pending writer unlock and IRQ restore.
    /// Returns the enqueue result unchanged; consumes exactly one target reference.
    ///
    /// # Safety
    /// `target` is nonnull with the reference acquired by original target selection.
    /// It and its process/main-thread/parent relations remain valid under the
    /// existing signal-delivery lifetime contract through synchronous notification
    /// and scheduler/IPI calls. `target_proc` is the original borrowed snapshot.
    /// No list or process lock is held by this tail. `caller` may be null and is
    /// compared only, never dereferenced. The caller has already restored IRQs.
    #[no_mangle]
    pub unsafe extern "C" fn arch_do_kill_wakeup_result(
        caller: *mut Thread, target: *mut Thread, target_proc: *mut Process,
        sig: CInt, ptracecont: CInt, mask: CULong, mut doint: CInt, rc: CInt,
    ) -> CInt {
        if sig == SIGCONT || ptracecont == 1 {
            // SAFETY: target owns the caller's held reference. Preserve scheduler
            // result test exactly: only zero means the stopped state was resumed.
            if unsafe { crate::sched_helpers::sched_wakeup_thread(target, PS_STOPPED) } == 0 {
                let mut storage = MaybeUninit::<SigInfo>::uninit();
                // SAFETY: stack storage is writable and suitably aligned for its
                // full extent. Zeroing every byte initializes the repr(C) siginfo
                // including padding before any public do_kill consumer sees it.
                unsafe {
                    (*(*(*target).proc).main_thread).signal_flags = SIGNAL_STOP_CONTINUED;
                    (*(*target).proc).status = PS_RUNNING;
                    crate::string::__inline_memset(
                        storage.as_mut_ptr().cast(), 0, size_of::<SigInfo>(),
                    );
                }
                // SAFETY: every byte of this plain ABI value was initialized.
                let mut info = unsafe { storage.assume_init() };
                info.si_signo = SIGCHLD;
                info.si_code = CLD_CONTINUED;
                let child = addr_of_mut!(info.sifields.sigchld).cast::<SigInfoChild>();
                // SAFETY: child points into live writable SigInfo union storage;
                // the chosen payload is exactly the original SIGCHLD arm. The
                // notification borrows info synchronously and does not retain it.
                unsafe {
                    (*child).si_pid = (*(*target).proc).pid;
                    (*child).si_status = 0x0000ffff;
                    let _ = notify_parent(
                        target, (*(*(*target).proc).parent).pid, -1, SIGCHLD, &mut info, 0,
                    );
                    // Re-read target->proc after the externally visible effect.
                    (*(*target).proc).status = PS_RUNNING;
                    if caller != target {
                        let cpu = (*target).cpu_id;
                        let vector = ihk_mc_get_vector(1); // actual IHK_GV_IKC
                        let _ = ihk_mc_interrupt_cpu(cpu, vector);
                    }
                }
                doint = 0;
            }
        }
        // SAFETY: held target reference remains live until the final release;
        // reads retain original unsynchronized signal/status observation semantics.
        if doint != 0 && mask & unsafe { (*target).sigmask.__val[0] } == 0 {
            let status = unsafe { (*target).status };
            if caller != target {
                // SAFETY: static debug metadata is retained; read its flag without
                // making a Rust reference to the mutable descriptor.
                if unsafe { read_volatile(addr_of!(IPI_DEBUG.line_flags)) } >> 24 != 0 {
                    // SAFETY: exact diagnostic format and ABI integer arguments;
                    // target_proc is the original live selected-process snapshot.
                    unsafe {
                        super::kprintf(
                            b"do_kill,ipi,pid=%d,cpu_id=%d\n\0".as_ptr().cast(),
                            (*target_proc).pid, (*target).cpu_id,
                        );
                    }
                }
                // SAFETY: retain original CPU/vector endpoint and ignored result.
                unsafe {
                    let cpu = (*target).cpu_id;
                    let vector = ihk_mc_get_vector(1);
                    let _ = ihk_mc_interrupt_cpu(cpu, vector);
                }
            }
            if status != PS_RUNNING {
                let states = if sig == SIGKILL {
                    PS_TRACED | PS_STOPPED | PS_INTERRUPTIBLE
                } else {
                    PS_INTERRUPTIBLE
                };
                // SAFETY: use status captured BEFORE IPI, as original C; the
                // scheduler owns synchronization and no new lock spans this call.
                let _ = unsafe { crate::sched_helpers::sched_wakeup_thread(target, states) };
            }
        }
        // SAFETY: consume exactly the caller's held target reference after all
        // target/process accesses. No target pointer is accessed after release.
        unsafe { crate::process_helpers::release_thread(target) };
        rc
    }
}
