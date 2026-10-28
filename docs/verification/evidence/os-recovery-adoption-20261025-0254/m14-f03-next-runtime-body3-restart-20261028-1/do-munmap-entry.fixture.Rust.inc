// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
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

    #[no_mangle]
    pub static F03_DO_MUNMAP_ABI:[CULong;27]=[
        core::mem::size_of::<crate::abi::Thread>() as _,core::mem::align_of::<crate::abi::Thread>() as _,
        core::mem::size_of::<crate::abi::ProcessVm>() as _,core::mem::align_of::<crate::abi::ProcessVm>() as _,
        core::mem::size_of::<Process>() as _,core::mem::align_of::<Process>() as _,
        core::mem::size_of::<crate::abi::CpuLocalVar>() as _,core::mem::align_of::<crate::abi::CpuLocalVar>() as _,
        offset_of!(crate::abi::CpuLocalVar,current) as _,offset_of!(crate::abi::Thread,vm) as _,
        offset_of!(crate::abi::Thread,proc) as _,offset_of!(Process,straight_va) as _,offset_of!(Process,straight_len) as _,
        core::mem::size_of::<DoMunmapBinding>() as _,core::mem::align_of::<DoMunmapBinding>() as _,
        offset_of!(DoMunmapBinding,begin) as _,offset_of!(DoMunmapBinding,remove_range) as _,
        offset_of!(DoMunmapBinding,clear_host) as _,offset_of!(DoMunmapBinding,set_host) as _,
        offset_of!(DoMunmapBinding,finish) as _,offset_of!(DoMunmapBinding,log) as _,
        core::mem::size_of::<CInt>() as _,core::mem::size_of::<crate::abi::CLong>() as _,
        core::mem::size_of::<SizeT>() as _,core::mem::size_of::<DoMunmapClearHostFn>() as _,
        core::mem::size_of::<DoMunmapRemoveRangeFn>() as _,(super::PROT_READ|super::PROT_WRITE|super::PROT_EXEC) as _,
    ];
}
