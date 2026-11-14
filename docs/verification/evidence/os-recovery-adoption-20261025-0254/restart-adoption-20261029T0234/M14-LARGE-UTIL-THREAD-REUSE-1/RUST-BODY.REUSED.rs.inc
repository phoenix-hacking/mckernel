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
