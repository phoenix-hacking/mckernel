// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[cfg(all(f03_perf_entry_candidate, enable_perf))]
mod perf_entry {
    use core::mem::{align_of, offset_of, size_of, MaybeUninit};
    use core::ptr::{addr_of, read_volatile};

    use crate::abi::{CInt, CLong, CULong, SizeT, SyscallRequest, X86UserContext};
    use crate::x86_cpu_helpers as cpu;

    use super::{PerfAttrFreqFn, PerfCounterAllocFn, PerfOpenAllocEventFn, PerfOpenSyscallFn, SyscallCopyFromUserFn, SyscallMckfdIntFn, SyscallMckfdLockFn, SyscallMckfdLongFn, SyscallMckfdUnlockFn, SyscallPolicyAllocFn};

    mod attr {
        // Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
        // Complete selected runtime layout from genuine lib/include/mc_perf_event.h.
        // __GENKSYMS__ is a distinct Linux metadata projection and is not this runtime ABI.
        use crate::abi::{CInt, CULong};
        
        #[repr(C)]
        #[derive(Clone, Copy)]
        pub union PerfSample {
            pub sample_period: CULong,
            pub sample_freq: CULong,
        }
        
        #[repr(C)]
        #[derive(Clone, Copy)]
        pub union PerfWakeup {
            pub wakeup_events: u32,
            pub wakeup_watermark: u32,
        }
        
        #[repr(C)]
        #[derive(Clone, Copy)]
        pub union PerfConfigOne {
            pub bp_addr: CULong,
            pub config1: CULong,
        }
        
        #[repr(C)]
        #[derive(Clone, Copy)]
        pub union PerfConfigTwo {
            pub bp_len: CULong,
            pub config2: CULong,
        }
        
        #[repr(C)]
        pub struct PerfEventAttr {
            pub type_: u32,
            pub size: u32,
            pub config: CULong,
            pub sampling: PerfSample,
            pub sample_type: CULong,
            pub read_format: CULong,
            // The genuine C unsigned-long bitfield allocation unit. Every one of its
            // 64 source-declared bits is independently checked against C object bytes.
            pub flags: CULong,
            pub wakeup: PerfWakeup,
            pub bp_type: u32,
            pub config_one: PerfConfigOne,
            pub config_two: PerfConfigTwo,
            pub branch_sample_type: CULong,
            pub sample_regs_user: CULong,
            pub sample_stack_user: u32,
            pub reserved_two: u32,
            pub sample_regs_intr: CULong,
        }
        
        impl PerfEventAttr {
            // Ten preceding one-bit members in the actual selected header; this is
            // qualified by the genuine C .freq=1 image, not an assumed Linux ABI.
            pub const FREQUENCY_SHIFT: u32 = 10;
        
            pub fn frequency(&self) -> CInt {
                ((self.flags >> Self::FREQUENCY_SHIFT) & 1) as CInt
            }
        }
    }
    use attr::PerfEventAttr;

    #[repr(C)]
    struct Layout {
        raw_type: CULong,
        hardware_type: CULong,
        hw_cache_type: CULong,
        unsupported_read_format_mask: CULong,
        sample_period_sign_bit: CULong,
        perf_event_open_nr: CInt,
        mckfd_size: SizeT,
        mckfd_alloc_flags: CULong,
        event_pid_offset: SizeT,
        event_counter_id_offset: SizeT,
        proc_mckfd_offset: SizeT,
        mckfd_next_offset: SizeT,
        mckfd_fd_offset: SizeT,
        mckfd_data_offset: SizeT,
        event_group_leader_offset: SizeT,
        event_sibling_list_offset: SizeT,
        event_group_entry_offset: SizeT,
        event_nr_siblings_offset: SizeT,
        event_pmc_status_offset: SizeT,
        thread_pmc_alloc_map_offset: SizeT,
        proc_mckfd_lock_offset: SizeT,
        mckfd_sig_no_offset: SizeT,
        mckfd_read_cb_offset: SizeT,
        mckfd_ioctl_cb_offset: SizeT,
        mckfd_mmap_cb_offset: SizeT,
        mckfd_close_cb_offset: SizeT,
        mckfd_fcntl_cb_offset: SizeT,
    }

    #[repr(C)]
    struct Providers {
        copy_from_fn: Option<SyscallCopyFromUserFn>,
        attr_freq_fn: Option<PerfAttrFreqFn>,
        event_alloc_fn: Option<PerfOpenAllocEventFn>,
        counter_alloc_fn: Option<PerfCounterAllocFn>,
        syscall_fn: Option<PerfOpenSyscallFn>,
        mckfd_alloc_fn: Option<SyscallPolicyAllocFn>,
        read_fn: Option<SyscallMckfdLongFn>,
        ioctl_fn: Option<SyscallMckfdIntFn>,
        mmap_fn: Option<SyscallMckfdLongFn>,
        close_fn: Option<SyscallMckfdIntFn>,
        fcntl_fn: Option<SyscallMckfdIntFn>,
        lock_fn: Option<SyscallMckfdLockFn>,
        unlock_fn: Option<SyscallMckfdUnlockFn>,
    }

    unsafe extern "C" {
        static f03_perf_entry_layout_v1: Layout;
        static f03_perf_entry_ops_v1: Providers;
    }

    const _: () = {
        assert!(size_of::<PerfEventAttr>() == size_of::<crate::x86_perfctr::PerfEventAttrOpaque>());
        assert!(align_of::<PerfEventAttr>() == align_of::<crate::x86_perfctr::PerfEventAttrOpaque>());
    };

    /// Own the genuine perf entry scratch objects and forward to its Rust body.
    ///
    /// # Safety
    /// Original pinned CPU/current-thread/process and readable user-context
    /// contracts apply. The existing providers retain all allocator, perf group,
    /// descriptor locking, Linux delegation and mmap/writer lifetime obligations.
    /// copy_from_user success initializes all attribute bytes; no uninitialized
    /// scratch byte is read by this entry. Request/attribute pointers cannot
    /// escape this synchronous helper transaction. Genuine C/Rust ABI probes must
    /// qualify both complete attribute layout and selected empty IHK_DMA_ALIGN.
    #[no_mangle]
    pub unsafe extern "C" fn sys_perf_event_open(
        _number: CInt, context: *mut X86UserContext,
    ) -> CLong {
        let mut request = MaybeUninit::<SyscallRequest>::uninit();
        let mut attribute = MaybeUninit::<PerfEventAttr>::uninit();
        // SAFETY: Same CPU ownership and live current-thread/process as C entry.
        let thread = unsafe { read_volatile(addr_of!((*super::get_this_cpu_local_var()).current)) };
        // SAFETY: The current thread retains its original process lifetime.
        let process = unsafe { read_volatile(addr_of!((*thread).proc)) };
        // SAFETY: Original live context; preserve each source-width conversion.
        let (user_attr, pid, validation_cpu, group_fd, flags) = unsafe {
            (cpu::ihk_mc_syscall_arg0(context), cpu::ihk_mc_syscall_arg1(context) as CInt,
             cpu::ihk_mc_syscall_arg2(context) as CInt, cpu::ihk_mc_syscall_arg3(context) as CInt,
             cpu::ihk_mc_syscall_arg4(context))
        };
        // SAFETY: Actual immutable header-derived metadata and original providers.
        let layout = unsafe { &*addr_of!(f03_perf_entry_layout_v1) };
        let providers = unsafe { &*addr_of!(f03_perf_entry_ops_v1) };
        // SAFETY: Stack scratch is correctly aligned and remains live through the
        // unchanged synchronous body; providers retain every original obligation.
        unsafe {
            super::perf_event_open_entry_body_result(
                request.as_mut_ptr(),
                thread.cast(),
                process.cast(),
                attribute.as_mut_ptr().cast(),
                user_attr,
                size_of::<PerfEventAttr>() as SizeT,
                offset_of!(PerfEventAttr, type_) as SizeT,
                offset_of!(PerfEventAttr, read_format) as SizeT,
                offset_of!(PerfEventAttr, sampling) as SizeT,
                pid,
                validation_cpu,
                group_fd,
                flags,
                super::ihk_mc_get_processor_id(),
                layout.raw_type,
                layout.hardware_type,
                layout.hw_cache_type,
                layout.unsupported_read_format_mask,
                layout.sample_period_sign_bit,
                layout.perf_event_open_nr,
                layout.mckfd_size,
                layout.mckfd_alloc_flags,
                layout.event_pid_offset,
                layout.event_counter_id_offset,
                layout.proc_mckfd_offset,
                layout.mckfd_next_offset,
                layout.mckfd_fd_offset,
                layout.mckfd_data_offset,
                layout.event_group_leader_offset,
                layout.event_sibling_list_offset,
                layout.event_group_entry_offset,
                layout.event_nr_siblings_offset,
                layout.event_pmc_status_offset,
                layout.thread_pmc_alloc_map_offset,
                layout.proc_mckfd_lock_offset,
                layout.mckfd_sig_no_offset,
                layout.mckfd_read_cb_offset,
                layout.mckfd_ioctl_cb_offset,
                layout.mckfd_mmap_cb_offset,
                layout.mckfd_close_cb_offset,
                layout.mckfd_fcntl_cb_offset,
                providers.copy_from_fn,
                providers.attr_freq_fn,
                providers.event_alloc_fn,
                providers.counter_alloc_fn,
                providers.syscall_fn,
                providers.mckfd_alloc_fn,
                providers.read_fn,
                providers.ioctl_fn,
                providers.mmap_fn,
                providers.close_fn,
                providers.fcntl_fn,
                providers.lock_fn,
                providers.unlock_fn,
            )
        }
    }

    // Fixture-only typed geometry, appended outside the unchanged entry body.
    #[no_mangle]
    pub static f03_perf_entry_fixture_Rust_ABI: [usize; 56] = [
        size_of::<Layout>(),
        align_of::<Layout>(),
        offset_of!(Layout,raw_type),
        offset_of!(Layout,hardware_type),
        offset_of!(Layout,hw_cache_type),
        offset_of!(Layout,unsupported_read_format_mask),
        offset_of!(Layout,sample_period_sign_bit),
        offset_of!(Layout,perf_event_open_nr),
        offset_of!(Layout,mckfd_size),
        offset_of!(Layout,mckfd_alloc_flags),
        offset_of!(Layout,event_pid_offset),
        offset_of!(Layout,event_counter_id_offset),
        offset_of!(Layout,proc_mckfd_offset),
        offset_of!(Layout,mckfd_next_offset),
        offset_of!(Layout,mckfd_fd_offset),
        offset_of!(Layout,mckfd_data_offset),
        offset_of!(Layout,event_group_leader_offset),
        offset_of!(Layout,event_sibling_list_offset),
        offset_of!(Layout,event_group_entry_offset),
        offset_of!(Layout,event_nr_siblings_offset),
        offset_of!(Layout,event_pmc_status_offset),
        offset_of!(Layout,thread_pmc_alloc_map_offset),
        offset_of!(Layout,proc_mckfd_lock_offset),
        offset_of!(Layout,mckfd_sig_no_offset),
        offset_of!(Layout,mckfd_read_cb_offset),
        offset_of!(Layout,mckfd_ioctl_cb_offset),
        offset_of!(Layout,mckfd_mmap_cb_offset),
        offset_of!(Layout,mckfd_close_cb_offset),
        offset_of!(Layout,mckfd_fcntl_cb_offset),
        size_of::<Providers>(),
        align_of::<Providers>(),
        offset_of!(Providers,copy_from_fn),
        offset_of!(Providers,attr_freq_fn),
        offset_of!(Providers,event_alloc_fn),
        offset_of!(Providers,counter_alloc_fn),
        offset_of!(Providers,syscall_fn),
        offset_of!(Providers,mckfd_alloc_fn),
        offset_of!(Providers,read_fn),
        offset_of!(Providers,ioctl_fn),
        offset_of!(Providers,mmap_fn),
        offset_of!(Providers,close_fn),
        offset_of!(Providers,fcntl_fn),
        offset_of!(Providers,lock_fn),
        offset_of!(Providers,unlock_fn),
        size_of::<PerfEventAttr>(),
        align_of::<PerfEventAttr>(),
        size_of::<SyscallRequest>(),
        align_of::<SyscallRequest>(),
        size_of::<crate::abi::CpuLocalVar>(),
        align_of::<crate::abi::CpuLocalVar>(),
        offset_of!(crate::abi::CpuLocalVar,current),
        size_of::<crate::abi::Thread>(),
        align_of::<crate::abi::Thread>(),
        offset_of!(crate::abi::Thread,proc),
        size_of::<crate::abi::Process>(),
        align_of::<crate::abi::Process>(),
    ];
}
