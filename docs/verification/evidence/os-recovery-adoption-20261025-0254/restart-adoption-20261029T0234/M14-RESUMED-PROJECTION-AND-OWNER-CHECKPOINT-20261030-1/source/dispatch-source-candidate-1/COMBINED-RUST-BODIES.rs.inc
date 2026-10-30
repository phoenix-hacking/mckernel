// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Complete PROFILE_ENABLE + Rust-offload, non-ToFu entry. Unselected caller HOLD.
#[cfg(f03_do_syscall_supported_candidate)]
mod f03_do_syscall_supported_v1 {
    use core::mem::{align_of, offset_of, size_of, MaybeUninit};
    use core::ptr::{addr_of, addr_of_mut, read_volatile, write_volatile};
    use core::sync::atomic::{compiler_fence, AtomicU64, Ordering};

    use crate::abi::{
        CInt, CLong, CULong, CpuLocalVar, IhkOsCpuMonitor, Process, SyscallRequest,
        SyscallResponse, Thread,
    };
    use crate::debug::Ddebug;

    use super::{
        ihk_mc_get_processor_id, send_syscall, syscall_offload_counted_result,
        syscall_offload_prepare_result, syscall_offload_wait_reply, syscall_owner_log_budget,
        syscall_preempt_disable_needed_result, syscall_profile_event_needed_result,
        syscall_proxy_dead_result,
    };

    unsafe extern "C" {
        static f03_do_syscall_constants_v1: [CULong; 5];
        static mut f03_do_syscall_debug_v1: [Ddebug; 6];
        fn kprintf(format: *const i8, ...) -> CInt;
    }

    // Reuse the existing Rust offload logger's linearized PID/count state. It
    // matches the old serial 64-message budget and avoids the original shared
    // C static ints' unsynchronized accesses. This is a correctness extension,
    // not a claim of cross-CPU C data-race parity or ordered console delivery.
    static RETURN_LOG_STATE: AtomicU64 = AtomicU64::new((u32::MAX as u64) << 32);

    macro_rules! debug {
        ($index:expr, $format:expr $(, $value:expr)* $(,)?) => {{
            // SAFETY: Original static lexical records and exact scalar varargs.
            unsafe {
                if read_volatile(addr_of!(f03_do_syscall_debug_v1[$index].line_flags)) >> 24 != 0 {
                    kprintf($format.as_ptr().cast() $(, $value)*);
                }
            }
        }};
    }

    /// Execute the existing Rust offload transaction and original caller accounting.
    ///
    /// # Safety
    /// The current CPU, monitor, thread/process and selected IKC channel remain
    /// live for the entire offload, including nested service/scheduling callbacks.
    /// request is aligned and its number and all six argument scalars are
    /// initialized before entry. The existing prepare helper assigns rtid and
    /// ttid, and the existing sender assigns valid before copying/publishing.
    /// No pointer ownership is created or foreign whole-object reference made.
    /// The host's release/completion contract makes the final response readable.
    /// This precondition excludes the separately held partial exec requests; no
    /// guessed field initialization or host acknowledgement is supplied here.
    #[export_name = "do_syscall"]
    pub unsafe extern "C" fn f03_do_syscall_supported_v1(
        request: *mut SyscallRequest, cpu: CInt,
    ) -> CLong {
        // SAFETY: These are exactly the caller-owned current objects. Raw field
        // operations never create a fully initialized response reference.
        unsafe {
            let local = crate::cls::get_this_cpu_local_var();
            let thread = read_volatile(addr_of!((*local).current));
            let monitor = read_volatile(addr_of!((*local).monitor));
            let process = read_volatile(addr_of!((*thread).proc));
            let pid = if process.is_null() { -1 } else { (*process).pid };
            let started = if read_volatile(addr_of!((*thread).profile)) != 0 {
                crate::x86_cpu_helpers::rdtsc()
            } else {
                0
            };
            let exit_group = f03_do_syscall_constants_v1[0] as CInt;
            let setaffinity = f03_do_syscall_constants_v1[1] as CInt;
            let spinning = f03_do_syscall_constants_v1[2];
            let offload_monitor = f03_do_syscall_constants_v1[3] as CInt;
            let profile_max = f03_do_syscall_constants_v1[4] as CInt;
            let number = read_volatile(addr_of!((*request).number)) as CInt;

            debug!(0, b"SC(%d)[%3d] sending syscall\n\0", ihk_mc_get_processor_id(), number);
            let old_monitor_status = read_volatile(addr_of!((*monitor).status));
            write_volatile(addr_of_mut!((*monitor).status), offload_monitor);
            // C barrier() orders compiler accesses; no new hardware fence.
            compiler_fence(Ordering::SeqCst);
            if syscall_offload_counted_result(number, exit_group) != 0 {
                let count = addr_of_mut!((*thread).in_syscall_offload);
                write_volatile(count, read_volatile(count).wrapping_add(1));
            }

            let mut response = MaybeUninit::<SyscallResponse>::uninit();
            let response_ptr = response.as_mut_ptr();
            let current = read_volatile(addr_of!((*crate::cls::get_this_cpu_local_var()).current));
            let use_requester = syscall_offload_prepare_result(
                request, response_ptr, read_volatile(addr_of!((*current).tid)), number,
                read_volatile(addr_of!((*request).args[0])), setaffinity, spinning,
            );
            if use_requester < 0 {
                // Preserve the original early return before monitor/count unwind.
                return use_requester as CLong;
            }
            if use_requester != 0 {
                debug!(1, b"%s: uti, ttid=%d\n\0", c"do_syscall".as_ptr(), (*request).ttid);
            }
            send_syscall(request, cpu, response_ptr);
            if syscall_preempt_disable_needed_result((*request).rtid) != 0 {
                crate::cls::preempt_disable();
            }
            debug!(2, b"%s: syscall num: %d waiting for Linux.. \n\0",
                c"do_syscall".as_ptr(), number);
            syscall_offload_wait_reply(request, response_ptr, cpu, thread);
            if syscall_preempt_disable_needed_result((*request).rtid) != 0 {
                crate::cls::preempt_enable();
            }
            // Only the completed ret field is read. Other response fields can
            // remain uninitialized unless the genuine protocol wrote them.
            let result = read_volatile(addr_of!((*response_ptr).ret));
            debug!(3, b"%s: syscall num: %d got host reply: %d \n\0",
                c"do_syscall".as_ptr(), number, result as CInt);
            if syscall_owner_log_budget(&RETURN_LOG_STATE, pid) {
                kprintf(
                    concat!(
                        "mcexec_v10: offload_return cpu=%d pid=%d tid=%d nr=%d ",
                        "ret=0x%lx ret_signed=%ld\n\0",
                    ).as_ptr().cast(),
                    cpu, pid, read_volatile(addr_of!((*thread).tid)), number,
                    result as CULong, result,
                );
            }
            if syscall_offload_counted_result(number, exit_group) != 0 {
                let count = addr_of_mut!((*thread).in_syscall_offload);
                write_volatile(count, read_volatile(count).wrapping_sub(1));
            }
            if syscall_proxy_dead_result(result) != 0 {
                debug!(4, b"%s: proxy PID %d is dead, terminate()\n\0",
                    c"do_syscall".as_ptr(), (*process).pid);
                write_volatile(addr_of_mut!((*process).nohost), 1);
            }
            if syscall_profile_event_needed_result(number, profile_max) != 0 {
                let event = crate::profile::profile_syscall2offload(number);
                crate::profile::profile_event_add(
                    event, crate::x86_cpu_helpers::rdtsc().wrapping_sub(started),
                );
            } else {
                debug!(5, b"%s: offload syscall > %d ?? : %d\n\0",
                    c"do_syscall".as_ptr(), profile_max, number);
            }
            write_volatile(addr_of_mut!((*monitor).status), old_monitor_status);
            let counter = addr_of_mut!((*monitor).counter);
            write_volatile(counter, read_volatile(counter).wrapping_add(1));
            result
        }
    }

    #[no_mangle]
    #[used]
    pub static f03_do_syscall_Rust_ABI_v1: [CULong; 29] = [
        size_of::<SyscallRequest>() as CULong,
        align_of::<SyscallRequest>() as CULong,
        offset_of!(SyscallRequest, rtid) as CULong,
        offset_of!(SyscallRequest, ttid) as CULong,
        offset_of!(SyscallRequest, valid) as CULong,
        offset_of!(SyscallRequest, number) as CULong,
        offset_of!(SyscallRequest, args) as CULong,
        size_of::<SyscallResponse>() as CULong,
        align_of::<SyscallResponse>() as CULong,
        offset_of!(SyscallResponse, status) as CULong,
        offset_of!(SyscallResponse, req_thread_status) as CULong,
        offset_of!(SyscallResponse, ret) as CULong,
        offset_of!(SyscallResponse, pde_data) as CULong,
        size_of::<IhkOsCpuMonitor>() as CULong,
        align_of::<IhkOsCpuMonitor>() as CULong,
        offset_of!(IhkOsCpuMonitor, status) as CULong,
        offset_of!(IhkOsCpuMonitor, counter) as CULong,
        size_of::<CpuLocalVar>() as CULong,
        align_of::<CpuLocalVar>() as CULong,
        offset_of!(CpuLocalVar, current) as CULong,
        offset_of!(CpuLocalVar, monitor) as CULong,
        size_of::<Thread>() as CULong,
        align_of::<Thread>() as CULong,
        offset_of!(Thread, tid) as CULong,
        offset_of!(Thread, proc) as CULong,
        offset_of!(Thread, profile) as CULong,
        offset_of!(Thread, in_syscall_offload) as CULong,
        offset_of!(Process, pid) as CULong,
        offset_of!(Process, nohost) as CULong,
    ];
}

// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Root accepted args5=0 as a separate intended-wire correction; both cfgs are required.
#[cfg(all(f03_util_thread_whole_candidate, f03_util_thread_arg5_zero_candidate))]
mod f03_util_thread_whole_v1 {
    use core::ffi::c_void;
    use core::mem::{align_of, offset_of, size_of, MaybeUninit};
    use core::ptr::{addr_of, addr_of_mut, copy_nonoverlapping, null_mut, read_volatile};
    use core::ptr::write_volatile;
    use crate::abi::{
        CInt, CLong, CULong, SizeT, SyscallRequest, Thread, UtiAttr, UtiCtx, UtiCtxRefill,
    };
    use super::{field_ptr, kprintf, save_uctx, syscall_proxy_dead_result, ENOMEM};

    #[repr(C)]
    struct Kattr {
        parent_cpuid: CLong,
        attr: UtiAttr,
    }

    #[repr(C)]
    struct Layout {
        context_size: SizeT,
        info_size: SizeT,
        context: SizeT,
        refill_tid: SizeT,
        info_thread_va: SizeT,
        info_response_pa: SizeT,
        info_channel_pa: SizeT,
        info_tid: SizeT,
        info_cpu: SizeT,
        info_status_pa: SizeT,
        info_sleep_lock_pa: SizeT,
        info_sleep_pa: SizeT,
        info_vm_pa: SizeT,
        info_futex_q_pa: SizeT,
        info_idle_halt: SizeT,
        info_futex_queue_pa: SizeT,
    }

    #[repr(C)]
    struct Origins {
        file: *const i8,
        context_alloc: CInt,
        info_alloc: CInt,
        context_free: CInt,
        info_free: CInt,
        context_out: CInt,
        info_out: CInt,
    }

    unsafe extern "C" {
        static f03_util_thread_layout_v1: Layout;
        static f03_util_thread_constants_v1: [CULong; 5];
        static f03_util_thread_origins_v1: Origins;
        static f03_util_thread_descriptor_slot_v1: *const CULong;
        static mut f03_util_thread_debug_v1: [crate::debug::Ddebug; 4];
        static mut idle_halt: CInt;
        #[link_name = "do_syscall"]
        fn existing_do_syscall(request: *mut SyscallRequest, cpu: CInt) -> CLong;
        #[link_name = "terminate"]
        fn existing_terminate(rc: CInt, sig: CInt);
        // Existing public adapter is needed because do_exit remains C-static.
        #[link_name = "exit_do_exit_bridge"]
        fn existing_do_exit(code: CInt);
        #[link_name = "util_show_syscall_profile"]
        fn existing_profile() -> CInt;
    }

    unsafe fn physical(address: *mut c_void) -> CULong {
        // SAFETY: Same live original mapping/boot objects; no pin is synthesized.
        unsafe { crate::x86_memory_helpers::virt_to_phys(address) }
    }

    unsafe fn release(pointer: *mut c_void, line: CInt) {
        // SAFETY: The selected original edge owns this allocation or NULL.
        let file = unsafe { f03_util_thread_origins_v1.file.cast_mut() };
        unsafe { crate::mem_helpers::kfree_tracked(pointer, file, line) };
    }

    unsafe fn debug_record(index: usize, thread: *mut Thread, rc: CLong) {
        // SAFETY: Actual aligned C records preserve the original macro flag gate.
        unsafe {
            let record = addr_of!(f03_util_thread_debug_v1).cast::<crate::debug::Ddebug>();
            if read_volatile(addr_of!((*record.add(index)).line_flags)) >> 24 == 0 {
                return;
            }
            match index {
                0 => {
                    kprintf(c"%s: returned from do_syscall,tid=%d,rc=%lx\n".as_ptr().cast(),
                        c"util_thread".as_ptr(), read_volatile(addr_of!((*thread).tid)),
                        rc as CULong);
                }
                1 => {
                    kprintf(c"%s: mcexec worker tid=%d\n".as_ptr().cast(),
                        c"util_thread".as_ptr(),
                        read_volatile(addr_of!((*thread).uti_refill_tid)));
                }
                2 => {
                    kprintf(c"%s: exit_group, tid=%d,rc=%lx\n".as_ptr().cast(),
                        c"util_thread".as_ptr(), read_volatile(addr_of!((*thread).tid)),
                        rc as CULong);
                }
                3 => {
                    let process = read_volatile(addr_of!((*thread).proc));
                    kprintf(c"%s: exit or killed by signal, pid=%d,tid=%d,rc=%lx\n"
                        .as_ptr().cast(), c"util_thread".as_ptr(),
                        read_volatile(addr_of!((*process).pid)),
                        read_volatile(addr_of!((*thread).tid)), rc as CULong);
                }
                _ => {}
            }
        }
    }

    /// Preserve both allocations, remote argument ownership and final cleanup.
    ///
    /// # Safety
    /// arg is NULL or the original readable disjoint UtiAttr span. Current thread,
    /// VM/channel/futex objects and physical mappings survive the synchronous
    /// offload transaction. Its host/context-completion and final-stack contracts
    /// remain explicit HOLDs. Neither scalar return nor a thread ref is a new ACK.
    /// Root accepted only args5=0; host completion and lifetime proofs remain held.
    #[export_name = "util_thread"]
    pub unsafe extern "C" fn f03_util_thread_whole_v1(arg: *mut UtiAttr) -> CInt {
        let mut context: *mut c_void = null_mut();
        let mut info: *mut c_void = null_mut();
        let mut request = MaybeUninit::<SyscallRequest>::uninit();
        let mut attribute = MaybeUninit::<Kattr>::uninit();
        // SAFETY: Raw current pointers and exact C layout data; no foreign whole
        // object reference or initialized MaybeUninit value is constructed.
        unsafe {
            let layout = addr_of!(f03_util_thread_layout_v1);
            let origins = addr_of!(f03_util_thread_origins_v1);
            let constants = addr_of!(f03_util_thread_constants_v1).cast::<CULong>();
            let local = crate::cls::get_this_cpu_local_var();
            let thread = read_volatile(addr_of!((*local).current));
            write_volatile(addr_of_mut!((*thread).uti_state), *constants.add(2) as CInt);
            let rc = 'allocate: {
                context = crate::mem_helpers::kmalloc_tracked(
                    (*layout).context_size as CInt, *constants, (*origins).file.cast_mut(),
                    (*origins).context_alloc,
                );
                if context.is_null() {
                    break 'allocate -(ENOMEM as CLong);
                }
                let remote_context = physical(context);
                // Actual Rust provider initializes cond at offset0 before later
                // ctx[0..4]/uti_refill_tid reads; its real saved-context bridge applies.
                save_uctx(context.cast::<u8>().add((*layout).context).cast(), null_mut());
                info = crate::mem_helpers::kmalloc_tracked(
                    (*layout).info_size as CInt, *constants, (*origins).file.cast_mut(),
                    (*origins).info_alloc,
                );
                if info.is_null() {
                    break 'allocate -(ENOMEM as CLong);
                }
                let bytes = info.cast::<u8>();
                let current = crate::cls::get_this_cpu_local_var();
                write_volatile(field_ptr::<CULong>(bytes, (*layout).info_thread_va),
                    read_volatile(addr_of!((*current).current)) as CULong);
                let current = crate::cls::get_this_cpu_local_var();
                write_volatile(field_ptr::<CULong>(bytes, (*layout).info_response_pa),
                    physical(read_volatile(addr_of!((*current).uti_futex_resp)).cast()));
                let current = crate::cls::get_this_cpu_local_var();
                write_volatile(field_ptr::<CULong>(bytes, (*layout).info_channel_pa),
                    physical(read_volatile(addr_of!((*current).ikc2linux)).cast()));
                write_volatile(field_ptr::<CInt>(bytes, (*layout).info_tid),
                    read_volatile(addr_of!((*thread).tid)));
                write_volatile(field_ptr::<CInt>(bytes, (*layout).info_cpu),
                    crate::x86_local::ihk_mc_get_processor_id());
                write_volatile(field_ptr::<CULong>(bytes, (*layout).info_status_pa),
                    physical(addr_of_mut!((*thread).status).cast()));
                write_volatile(field_ptr::<CULong>(bytes, (*layout).info_sleep_lock_pa),
                    physical(addr_of_mut!((*thread).spin_sleep_lock).cast()));
                write_volatile(field_ptr::<CULong>(bytes, (*layout).info_sleep_pa),
                    physical(addr_of_mut!((*thread).spin_sleep).cast()));
                write_volatile(field_ptr::<CULong>(bytes, (*layout).info_vm_pa),
                    physical(read_volatile(addr_of!((*thread).vm)).cast()));
                write_volatile(field_ptr::<CULong>(bytes, (*layout).info_futex_q_pa),
                    physical(addr_of_mut!((*thread).futex_q).cast()));
                write_volatile(field_ptr::<CInt>(bytes, (*layout).info_idle_halt),
                    read_volatile(addr_of!(idle_halt)));
                write_volatile(field_ptr::<CULong>(bytes, (*layout).info_futex_queue_pa),
                    physical(crate::futex::get_futex_queues().cast()));

                let request = request.as_mut_ptr();
                write_volatile(addr_of_mut!((*request).number), *constants.add(1));
                write_volatile(addr_of_mut!((*request).args[0]), 0);
                write_volatile(addr_of_mut!((*request).args[1]), remote_context);
                write_volatile(addr_of_mut!((*request).args[2]), 0);
                if !arg.is_null() {
                    let attribute = attribute.as_mut_ptr();
                    copy_nonoverlapping(arg.cast::<u8>(),
                        addr_of_mut!((*attribute).attr).cast(), size_of::<UtiAttr>());
                    write_volatile(addr_of_mut!((*attribute).parent_cpuid),
                        read_volatile(addr_of!((*thread).parent_cpuid)) as CLong);
                    write_volatile(addr_of_mut!((*request).args[2]), physical(attribute.cast()));
                }
                write_volatile(addr_of_mut!((*request).args[3]), info as CULong);
                let slot = read_volatile(addr_of!(f03_util_thread_descriptor_slot_v1));
                write_volatile(addr_of_mut!((*request).args[4]), read_volatile(slot));
                write_volatile(addr_of_mut!((*thread).uti_state), *constants.add(3) as CInt);
                // Separate Root-accepted correction: the actual selected host ignores
                // arg5, but the transport copies all6. Never reset IDs/valid here.
                write_volatile(addr_of_mut!((*request).args[5]), 0);
                let rc = existing_do_syscall(request, crate::x86_local::ihk_mc_get_processor_id());
                debug_record(0, thread, rc);
                write_volatile(addr_of_mut!((*thread).uti_state), *constants.add(4) as CInt);
                let _ = existing_profile();
                write_volatile(addr_of_mut!((*thread).uti_refill_tid),
                    read_volatile(field_ptr::<CInt>(context.cast(), (*layout).refill_tid)));
                debug_record(1, thread, rc);
                release(context, (*origins).context_free);
                context = null_mut();
                release(info, (*origins).info_free);
                info = null_mut();
                if rc >= 0 {
                    if rc & 0x1_0000_0000 != 0 {
                        debug_record(2, thread, rc);
                        let process = read_volatile(addr_of!((*thread).proc));
                        write_volatile(addr_of_mut!((*process).nohost), 1);
                        existing_terminate(((rc >> 8) & 255) as CInt, (rc & 255) as CInt);
                    } else {
                        debug_record(3, thread, rc);
                        existing_do_exit(rc as CInt);
                    }
                } else if syscall_proxy_dead_result(rc) != 0 {
                    let process = read_volatile(addr_of!((*thread).proc));
                    kprintf(c"%s: release_handler,pid=%d,tid=%d,rc=%lx\n".as_ptr().cast(),
                        c"util_thread".as_ptr(), read_volatile(addr_of!((*process).pid)),
                        read_volatile(addr_of!((*thread).tid)), rc as CULong);
                    let process = read_volatile(addr_of!((*thread).proc));
                    write_volatile(addr_of_mut!((*process).nohost), 1);
                    existing_do_exit(rc as CInt);
                } else {
                    kprintf(c"%s: ERROR: do_syscall() failed (%ld)\n".as_ptr().cast(),
                        c"util_thread".as_ptr(), rc);
                }
                break 'allocate rc;
            };
            // Preserve the original out label even after a nominally nonreturning
            // terminate/do_exit returns: only NULL remains on the success path.
            release(context, (*origins).context_out);
            release(info, (*origins).info_out);
            rc as CInt
        }
    }

    #[no_mangle]
    #[used]
    pub static f03_util_thread_Rust_ABI_v1: [CULong; 23] = [
        size_of::<Layout>() as CULong, align_of::<Layout>() as CULong,
        size_of::<Origins>() as CULong, align_of::<Origins>() as CULong,
        size_of::<Kattr>() as CULong, align_of::<Kattr>() as CULong,
        offset_of!(Kattr, parent_cpuid) as CULong, offset_of!(Kattr, attr) as CULong,
        size_of::<UtiAttr>() as CULong, align_of::<UtiAttr>() as CULong,
        size_of::<SyscallRequest>() as CULong, align_of::<SyscallRequest>() as CULong,
        size_of::<CInt>() as CULong, size_of::<CLong>() as CULong,
        size_of::<CULong>() as CULong, offset_of!(super::TransUctx, cond) as CULong,
        size_of::<CULong>() as CULong,
        size_of::<UtiCtx>() as CULong, align_of::<UtiCtx>() as CULong,
        offset_of!(UtiCtx, ctx) as CULong,
        (offset_of!(UtiCtx, refill) + offset_of!(UtiCtxRefill, uti_refill_tid)) as CULong,
        size_of::<UtiCtxRefill>() as CULong, align_of::<UtiCtxRefill>() as CULong,
    ];
}

#[cfg(all(f03_request_constructors_candidate, target_arch = "x86_64"))]
#[path = "f03_request_constructors.rs"]
mod f03_request_constructors;
