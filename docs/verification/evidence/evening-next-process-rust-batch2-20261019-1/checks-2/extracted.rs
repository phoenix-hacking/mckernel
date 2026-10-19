#![no_std]
#[path="/home/holden/mckernel-work/host-preparation/evening-next-process-rust-batch2-20261019-1/original/kernel/rust/abi.rs"] mod abi;
use core::ffi::c_void;use core::mem::{offset_of,size_of,MaybeUninit};
use abi::{CInt,CULong,CpuLocalVar,ResourceSet,Process,Mckfd};
#[repr(C,align(64))] struct McsRwlockNodeIrqsave {irqsave:CULong}
unsafe extern "C" {fn get_this_cpu_local_var()->*mut CpuLocalVar;fn process_mcs_reader_lock_bridge(l:CULong,n:*mut c_void);fn process_mcs_reader_unlock_bridge(l:CULong,n:*mut c_void); }

extern "C" {
    fn hugefileobj_cleanup();
    #[cfg(enable_tofu)]
    fn tof_utofu_finalize();
}

const _: () = {
    #[cfg(not(enable_tofu))]
    assert!(offset_of!(CpuLocalVar, resource_set) == 7912);
    #[cfg(enable_tofu)]
    assert!(offset_of!(CpuLocalVar, resource_set) == 24368);
    assert!(offset_of!(ResourceSet, pid1) == 320);
    assert!(offset_of!(Process, children_list) == 288);
    assert!(offset_of!(Process, children_lock) == 320);
    assert!(size_of::<McsRwlockNodeIrqsave>() == 64);
};

/// Read the current CPU's existing resource-set binding. The CPU-local pointer
/// returned by the existing ABI remains valid for this synchronous read. The
/// caller retains CPU affinity and owns the resource-set lifetime; this callback
/// neither obtains a reference nor interprets a possibly null resource-set value.
#[no_mangle]
pub unsafe extern "C" fn process_current_resource_set_bridge() -> *mut c_void {
    unsafe { (*get_this_cpu_local_var()).resource_set.cast() }
}

/// Perform existing last-child cleanup under pid1's children reader lock.
/// The resource set, pid1 process, initialized child-list head and lock storage
/// remain live, and pid1 stays stable throughout synchronous callbacks. The
/// cleanup callees retain their existing concurrency/ownership contracts. The
/// list-empty test is exactly head.next == head; no list mutation/free is added.
#[no_mangle]
pub unsafe extern "C" fn process_release_final_cleanup_bridge(resource_set_arg: *mut c_void) {
    let rset = resource_set_arg.cast::<ResourceSet>();
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    unsafe {
        process_mcs_reader_lock_bridge(
            core::ptr::addr_of_mut!((*(*rset).pid1).children_lock) as CULong,
            lock.as_mut_ptr().cast(),
        );
        let head = core::ptr::addr_of_mut!((*(*rset).pid1).children_list);
        if (*head).next == head {
            #[cfg(enable_tofu)]
            tof_utofu_finalize();
            hugefileobj_cleanup();
        }
        process_mcs_reader_unlock_bridge(
            core::ptr::addr_of_mut!((*(*rset).pid1).children_lock) as CULong,
            lock.as_mut_ptr().cast(),
        );
    }
}
