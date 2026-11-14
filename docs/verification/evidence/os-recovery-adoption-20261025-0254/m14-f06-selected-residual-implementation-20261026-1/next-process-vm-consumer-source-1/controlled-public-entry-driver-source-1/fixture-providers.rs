// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// HOST fixture boundary declarations only. Production adapters remain unchanged.
mod cls {
    extern "C" {
        #[link_name = "fixture_cpu"]
        pub fn get_this_cpu_local_var() -> *mut crate::abi::CpuLocalVar;
    }
}

mod lock_helpers {
    use core::ffi::c_void;
    use crate::abi::CULong;

    // Exact production node definition; no executable lock implementation copied.
    #[repr(C, align(64))]
    pub struct McsRwlockNodeIrqsave {
        irqsave: CULong,
    }

    extern "C" {
        #[link_name = "fixture_range_lock"]
        pub fn ihk_rwspinlock_read_lock_noirq(lock: *mut c_void);
        #[link_name = "fixture_range_unlock"]
        pub fn ihk_rwspinlock_read_unlock_noirq(lock: *mut c_void);
        #[link_name = "fixture_update_lock"]
        pub fn __mcs_rwlock_reader_lock_noirq(lock: *mut c_void, node: *mut c_void);
        #[link_name = "fixture_update_unlock"]
        pub fn __mcs_rwlock_reader_unlock_noirq(lock: *mut c_void, node: *mut c_void);
    }
}

mod process_helpers {
    use core::ffi::c_void;
    use crate::abi::{CInt, CULong, Process, ProcessVm, VmRange};
    use crate::lock_helpers::McsRwlockNodeIrqsave;

    extern "C" {
        #[link_name = "fixture_lookup"]
        pub fn lookup_process_memory_range(vm: *mut ProcessVm, start: CULong,
                                           end: CULong) -> *mut VmRange;
        #[link_name = "fixture_find"]
        pub fn find_process(pid: CInt, node: *mut McsRwlockNodeIrqsave) -> *mut Process;
        #[link_name = "fixture_process_unlock"]
        pub fn process_unlock(proc: *mut Process, node: *mut McsRwlockNodeIrqsave);
        #[link_name = "fixture_hold"]
        pub fn hold_process_vm(vm: *mut ProcessVm);
        #[link_name = "fixture_release"]
        pub fn release_process_vm(vm: *mut ProcessVm);
        #[link_name = "fixture_fault"]
        pub fn page_fault_process_vm(vm: *mut ProcessVm, addr: *mut c_void,
                                     reason: CULong) -> CInt;
    }
}

mod x86_memory_helpers {
    use core::ffi::c_void;
    use crate::abi::{CInt, CULong};

    extern "C" {
        #[link_name = "fixture_vtop"]
        pub fn ihk_mc_pt_virt_to_phys_size(pt: *mut c_void, virt: *const c_void,
                                          phys: *mut CULong, size: *mut CULong) -> CInt;
        #[link_name = "fixture_phys"]
        pub fn phys_to_virt(phys: CULong) -> *mut c_void;
    }
}

mod string {
    use core::ffi::c_void;
    use crate::abi::SizeT;

    extern "C" {
        #[link_name = "fixture_copy"]
        pub fn __inline_memcpy(dst: *mut c_void, src: *const c_void,
                               bytes: SizeT) -> *mut c_void;
    }
}
