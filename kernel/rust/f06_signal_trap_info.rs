// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Define the notification bytes before do_signal's traced default-SIGTRAP notify.
use core::mem::{offset_of, size_of};
use core::ptr::{addr_of_mut, write_volatile};

use crate::abi::{CInt, SigInfo, SigInfoChild};

const SIGCHLD: CInt = 17;
const CLD_TRAPPED: CInt = 4;

// The selected native x86 ABI uses the same 128-byte siginfo payload as C.
const _: () = {
    assert!(size_of::<SigInfo>() == 128);
    assert!(offset_of!(SigInfo, sifields) == 16);
    assert!(offset_of!(SigInfoChild, si_pid) == 0);
    assert!(offset_of!(SigInfoChild, si_status) == 8);
};

/// Initialize the same SIGCHLD/CLD_TRAPPED notification as ptrace_report_signal.
///
/// The default SIGTRAP branch previously forwarded uninitialized stack bytes to
/// do_kill. Both its main-thread and report-process notifications now receive a
/// fully initialized siginfo, with the stopped TID and actual exit status. This
/// helper owns no pending node, process reference, lock, wakeup or scheduling.
///
/// # Safety
/// `info` covers writable, aligned SigInfo storage exclusively owned by the
/// caller during initialization. It may initially contain uninitialized bytes.
/// The caller snapshots tid/status from its live stopped thread. The helper
/// neither reads prior storage nor retains a pointer past this synchronous call.
#[no_mangle]
pub unsafe extern "C" fn arch_do_signal_trap_info_bridge(
    info: *mut SigInfo,
    tid: CInt,
    status: CInt,
) {
    // Initialize every byte, including the inactive union/padding, without ever
    // materializing a Rust value or reference from the uninitialized storage.
    for byte in 0..size_of::<SigInfo>() {
        unsafe { write_volatile(info.cast::<u8>().add(byte), 0) };
    }
    unsafe {
        addr_of_mut!((*info).si_signo).write(SIGCHLD);
        addr_of_mut!((*info).si_code).write(CLD_TRAPPED);
        let child = addr_of_mut!((*info).sifields.sigchld).cast::<SigInfoChild>();
        addr_of_mut!((*child).si_pid).write(tid);
        addr_of_mut!((*child).si_status).write(status);
    }
}
