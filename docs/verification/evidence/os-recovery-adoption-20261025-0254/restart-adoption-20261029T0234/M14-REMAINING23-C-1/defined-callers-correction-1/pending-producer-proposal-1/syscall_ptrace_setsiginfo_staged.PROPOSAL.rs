// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Unselected producer proposal. It intentionally changes failed fresh-sendsig
// publication. Root must approve that contract and the real lock/lifetime model.
use core::ffi::c_void;
use core::mem::{offset_of, size_of, MaybeUninit};
use core::ptr::{addr_of, addr_of_mut, copy_nonoverlapping};
use crate::abi::{CInt, CLong, CULong, SigInfo, SigPending};
use super::{
    f03_ptrace_io_find, f03_ptrace_io_unlock, ptrace_io_recvsig, ptrace_io_sendsig,
    ptrace_io_status, ptrace_setsiginfo_store_result, ptrace_setsiginfo_target_result,
    syscall_alloc_bridge, syscall_copy_from_user_bridge, F03_PTRACE_IO_OFFSETS,
    EFAULT, ENOMEM, ESRCH, IHK_MC_AP_NOWAIT, PTRACE_SIGINFO_ALLOC_SENDSIG,
    PTRACE_SIGINFO_STORE_RECVSIG, PTRACE_SIGINFO_STORE_SENDSIG,
};

/// Proposed selected producer: a new sendsig is initialized before publishing.
///
/// # Safety
/// The original tracee/find/unlock and ptrace exclusion contracts apply. The
/// allocator and tracked free are the qualified matching pair, and a staged
/// allocation stays privately owned until published. The offsets and typed ABI
/// must match the selected C layout. No concurrent writer may replace sendsig
/// during this original transaction unless a separately reviewed lock protocol
/// handles that conflict. On failed copy, Root must accept retaining no new slot.
pub unsafe fn f03_ptrace_setsiginfo_staged_v2(pid: CInt, data: *mut SigInfo) -> CLong {
    let mut scratch = MaybeUninit::<SigInfo>::uninit();
    let offsets = addr_of!(F03_PTRACE_IO_OFFSETS);
    // SAFETY: This repeats the actual selected find and original raw offset reads.
    let child = unsafe { f03_ptrace_io_find(0, pid) };
    if child == 0 {
        return -(ESRCH as CLong);
    }
    let status = unsafe { ptrace_io_status(child, offsets) };
    let sendsig = unsafe { ptrace_io_sendsig(child, offsets) };
    let recvsig = unsafe { ptrace_io_recvsig(child, offsets) };
    let target = ptrace_setsiginfo_target_result(status, (sendsig != 0) as CInt, (recvsig != 0) as CInt);
    let mut rc = target as CLong;
    let mut staged: *mut SigPending = core::ptr::null_mut();
    if target >= 0 {
        rc = 0;
        if (target & PTRACE_SIGINFO_ALLOC_SENDSIG) != 0 {
            // SAFETY: Genuine syscall allocator owns the same size/flags domain.
            staged = unsafe { syscall_alloc_bridge(size_of::<SigPending>(), IHK_MC_AP_NOWAIT).cast() };
            if staged.is_null() {
                rc = -(ENOMEM as CLong);
            }
        }
        if rc == 0 && (target & PTRACE_SIGINFO_STORE_SENDSIG) != 0 {
            // SAFETY: Raw aligned scratch has sizeof(SigInfo) writable bytes;
            // the existing provider owns the user pointer and reports full copy.
            let copy_rc = unsafe { syscall_copy_from_user_bridge(scratch.as_mut_ptr().cast(), data as CULong, size_of::<SigInfo>()) };
            if copy_rc != 0 {
                rc = -(EFAULT as CLong);
            } else if !staged.is_null() {
                // SAFETY: Full successful usercopy initialized scratch. Write the
                // entire payload into private tracked storage BEFORE slot publish.
                unsafe {
                    copy_nonoverlapping(scratch.as_ptr().cast::<u8>(), addr_of_mut!((*staged).info).cast::<u8>(), size_of::<SigInfo>());
                    rc = ptrace_setsiginfo_store_result(
                        child, (*offsets).thread_ptrace_sendsig_offset as CULong,
                        (*offsets).thread_ptrace_recvsig_offset as CULong,
                        offset_of!(SigPending, info) as CULong, PTRACE_SIGINFO_ALLOC_SENDSIG,
                        staged as CULong, core::ptr::null(), 0,
                    ) as CLong;
                }
                if rc == 0 {
                    staged = core::ptr::null_mut(); // ownership transferred to slot
                }
            } else {
                // SAFETY: Existing slot is retained by original tracee contract.
                rc = unsafe {
                    ptrace_setsiginfo_store_result(
                        child, (*offsets).thread_ptrace_sendsig_offset as CULong,
                        (*offsets).thread_ptrace_recvsig_offset as CULong,
                        offset_of!(SigPending, info) as CULong, PTRACE_SIGINFO_STORE_SENDSIG,
                        0, scratch.as_ptr().cast::<u8>(), size_of::<SigInfo>(),
                    ) as CLong
                };
            }
        }
        if rc == 0 && (target & PTRACE_SIGINFO_STORE_RECVSIG) != 0 {
            // Preserve the original second usercopy and its separate failure edge.
            let copy_rc = unsafe { syscall_copy_from_user_bridge(scratch.as_mut_ptr().cast(), data as CULong, size_of::<SigInfo>()) };
            if copy_rc != 0 {
                rc = -(EFAULT as CLong);
            } else {
                rc = unsafe {
                    ptrace_setsiginfo_store_result(
                        child, (*offsets).thread_ptrace_sendsig_offset as CULong,
                        (*offsets).thread_ptrace_recvsig_offset as CULong,
                        offset_of!(SigPending, info) as CULong, PTRACE_SIGINFO_STORE_RECVSIG,
                        0, scratch.as_ptr().cast::<u8>(), size_of::<SigInfo>(),
                    ) as CLong
                };
            }
        }
    }
    if !staged.is_null() {
        // SAFETY: No slot owns this tracked allocation on error. This is a new
        // cleanup edge; its Rust source/line provenance is intentionally new.
        unsafe {
            crate::mem_helpers::kfree_tracked(staged.cast::<c_void>(),
                concat!(file!(), "\0").as_ptr().cast_mut().cast(), line!() as CInt);
        }
    }
    unsafe { f03_ptrace_io_unlock(child) };
    rc
}
