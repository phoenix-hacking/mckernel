// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#[cfg(enable_perf)]
mod f03_perf_mmap_entry_v1 {
    use crate::abi::{CInt, CLong, CULong, Mckfd, SizeT, X86UserContext};
    use super::{perf_mmap_body_result, PerfDoMmapFn};

    // Actual C headers supply constants and offsets; no duplicated perf-page ABI.
    #[repr(C)]
    struct MmapBinding {
        map_anonymous: CInt,
        prot_write: CInt,
        data_head: SizeT,
        capabilities: SizeT,
        cap_user_rdpmc: CULong,
        do_mmap: Option<PerfDoMmapFn>,
    }

    unsafe extern "C" {
        static f03_perf_mmap_binding_v1: MmapBinding;
    }

    /// Invoke the existing complete Rust mapping transaction with the original ABI.
    ///
    /// # Safety
    /// `ctx` is the genuine live syscall context. The existing mmap provider owns
    /// allocation, synchronization and mapping lifetime. A nonnegative result must
    /// name the writable mapping covering both actual perf-page metadata fields,
    /// exactly as required by the original callback. `sfd` remains unused.
    #[no_mangle]
    pub unsafe extern "C" fn f03_perf_mmap_v1(
        _sfd: *mut Mckfd,
        ctx: *mut X86UserContext,
    ) -> CLong {
        // SAFETY: Read the same six actual registers in their original order.
        let addr = unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_arg0(ctx) };
        let len = unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_arg1(ctx) } as SizeT;
        let prot = unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_arg2(ctx) } as CInt;
        let flags = unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_arg3(ctx) } as CInt;
        let fd = unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_arg4(ctx) } as CInt;
        let off = unsafe { crate::x86_cpu_helpers::ihk_mc_syscall_arg5(ctx) } as CLong;
        // SAFETY: Immutable, cfg-matched header/provider data; existing Rust body
        // retains negative errors without metadata access and owns success writes.
        unsafe {
            let binding = &f03_perf_mmap_binding_v1;
            perf_mmap_body_result(
                addr, len, prot, flags, fd, off,
                binding.map_anonymous, binding.prot_write,
                binding.data_head, binding.capabilities,
                binding.cap_user_rdpmc, binding.do_mmap,
            )
        }
    }

    #[no_mangle]
    pub static F03_PERF_MMAP_ABI:[CULong;18]=[
        core::mem::size_of::<X86UserContext>() as _,core::mem::align_of::<X86UserContext>() as _,
        core::mem::offset_of!(X86UserContext,gpr.rdi) as _,core::mem::offset_of!(X86UserContext,gpr.rsi) as _,
        core::mem::offset_of!(X86UserContext,gpr.rdx) as _,core::mem::offset_of!(X86UserContext,gpr.r10) as _,
        core::mem::offset_of!(X86UserContext,gpr.r8) as _,core::mem::offset_of!(X86UserContext,gpr.r9) as _,
        core::mem::size_of::<MmapBinding>() as _,core::mem::align_of::<MmapBinding>() as _,
        core::mem::offset_of!(MmapBinding,map_anonymous) as _,core::mem::offset_of!(MmapBinding,prot_write) as _,
        core::mem::offset_of!(MmapBinding,data_head) as _,core::mem::offset_of!(MmapBinding,capabilities) as _,
        core::mem::offset_of!(MmapBinding,cap_user_rdpmc) as _,core::mem::offset_of!(MmapBinding,do_mmap) as _,
        core::mem::size_of::<PerfDoMmapFn>() as _,
        core::mem::size_of::<unsafe extern "C" fn(*mut Mckfd,*mut X86UserContext)->CLong>() as _,
    ];
}
