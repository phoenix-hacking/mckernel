// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod remaining_process_profile_providers {
    use core::ffi::c_void;
    use core::mem::{align_of, offset_of, size_of};

    use crate::abi::CInt;
    #[cfg(enable_profile)]
    use crate::abi::{Process, Thread};
    use crate::ap::IhkMcCpuInfo;

    use super::EINVAL;

    unsafe extern "C" {
        #[link_name = "ihk_mc_get_cpu_info"]
        fn current_cpu_info() -> *mut IhkMcCpuInfo;
    }

    const _: () = {
        assert!(size_of::<IhkMcCpuInfo>() == 40);
        assert!(align_of::<IhkMcCpuInfo>() == 8);
        assert!(offset_of!(IhkMcCpuInfo, ncpus) == 0);
    };

    /// Return the existing CPU-info count, or the original absent-info error.
    ///
    /// # Safety
    /// The platform getter supplies either null or a live, initialized CPU-info
    /// object whose count remains readable through this synchronous call. No
    /// ownership or reference changes occur; the original signed count is kept.
    #[no_mangle]
    pub unsafe extern "C" fn process_default_ncpus_bridge() -> CInt {
        // SAFETY: The getter and its existing initialized-object contract supply
        // the same nullable40-byte C-layout object as the original C provider.
        unsafe {
            let info = current_cpu_info();
            if info.is_null() {
                -EINVAL
            } else {
                (*info).ncpus
            }
        }
    }

    /// Accumulate a released thread's events before its existing deallocation.
    ///
    /// # Safety
    /// With profiling selected, the existing release owner preserves thread and
    /// process/event lifetimes until accumulation finishes, then grants the same
    /// one-time event deallocation. The existing providers retain their null
    /// handling and locks. Without profiling, both pointers remain unused.
    #[no_mangle]
    pub unsafe extern "C" fn process_release_thread_profile_bridge(
        thread: *mut c_void,
        proc: *mut c_void,
    ) {
        #[cfg(enable_profile)]
        // SAFETY: The original release callback owns this sequencing. Existing
        // providers borrow the same objects, then free the same event allocation;
        // no extra reset, free, reference, lock or event traversal is introduced.
        unsafe {
            crate::profile::profile_accumulate_events(
                thread.cast::<Thread>(),
                proc.cast::<Process>(),
            );
            crate::profile::profile_dealloc_thread_events(thread.cast::<Thread>());
        }
        #[cfg(not(enable_profile))]
        let _ = (thread, proc);
    }

    /// Print the released process's selected profile before its event teardown.
    ///
    /// # Safety
    /// With profiling selected, `proc_arg` is the original live process under its
    /// final-release owner. Profile state stays readable through the synchronous
    /// print/accumulation callback and the owner permits the existing one-time
    /// deallocation afterward. Without profiling, the pointer is not accessed.
    #[no_mangle]
    pub unsafe extern "C" fn process_release_profile_bridge(proc_arg: *mut c_void) {
        #[cfg(enable_profile)]
        // SAFETY: The caller retains the same process/event lifetimes and release
        // exclusivity as C. Existing Rust providers own all statistics, locking,
        // printing and deallocation, preserving their order and return handling.
        unsafe {
            let proc = proc_arg.cast::<Process>();
            if (*proc).profile != 0 {
                if (*proc).nr_processes != 0 {
                    let _ = crate::profile::profile_accumulate_and_print_job_events(proc);
                } else {
                    crate::profile::profile_print_proc_stats(proc);
                }
            }
            crate::profile::profile_dealloc_proc_events(proc);
        }
        #[cfg(not(enable_profile))]
        let _ = proc_arg;
    }

    const _: unsafe extern "C" fn() -> CInt = process_default_ncpus_bridge;
    const _: unsafe extern "C" fn(*mut c_void, *mut c_void) =
        process_release_thread_profile_bridge;
    const _: unsafe extern "C" fn(*mut c_void) = process_release_profile_bridge;
}
