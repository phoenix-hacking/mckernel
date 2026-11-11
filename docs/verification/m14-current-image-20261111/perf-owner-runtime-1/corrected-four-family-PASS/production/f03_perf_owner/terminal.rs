// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Private perf terminal route. Selection and genuine image proof remain separate.
use core::ffi::c_void;
use core::mem::{align_of, forget, size_of, MaybeUninit};
use core::ptr::{addr_of, read_volatile};
use crate::abi::{CInt, CLong, CULong, Process, SyscallRequest, Thread};
use super::descriptors::{self, CloseToken, HostState, HostUnissued};
use super::process_targets;

const NR_CLOSE: CULong = 3;

/// The original live terminal frame owns both objects. A Process address stored
/// in registry metadata is NOT permission to use some other current host route.
unsafe fn same_current_owner(thread: *mut Thread, process: *mut Process) -> bool {
    let cpu = unsafe { crate::cls::get_this_cpu_local_var() };
    if cpu.is_null() || thread.is_null() || process.is_null() { return false; }
    if unsafe { addr_of!((*cpu).current).read() } != thread { return false; }
    unsafe { addr_of!((*thread).proc).read() == process }
}

/// Match the existing volatile nohost protocol; never manufacture a Linux
/// close acknowledgement from a skipped/expired current executor route.
unsafe fn host_route_available(process: *mut Process) -> bool {
    unsafe { read_volatile(addr_of!((*process).nohost)) == 0 }
}

/// Consume the genuine unlink ownership with its accepted tracked free origin.
/// An unexpected internal retirement failure retains this exact metadata pin;
/// neither a numeric-FD retry nor a free/acknowledgement is invented for it.
unsafe fn retire(token: CloseToken) -> bool {
    let process = token.process();
    let descriptor = token.descriptor();
    match unsafe { descriptors::retire_unlinked(
        process, descriptor, super::super::syscall_mckfd_free_bridge,
    ) } {
        Ok(true) => { drop(token); true },
        _ => { forget(token); false },
    }
}

/// Drain managed host descriptors BEFORE the real exit-group/nohost transition.
///
/// # Safety
/// The real current Thread and its Process remain positively owned by the
/// original terminal caller. It has released all hash/P/R/S/update/runqueue/IRQ
/// locks and may use the existing process-context wait/offload path. Nonlast
/// Thread exit does not call this routine. Process construction, ordinary close
/// and open/rollback use the same Process transaction gate; their frames cannot
/// outlive this terminal gate unnoticed. Idle/VM-under-P never calls this entry.
pub(crate) unsafe fn terminal_current_process() {
    let cpu = unsafe { crate::cls::get_this_cpu_local_var() };
    if cpu.is_null() { return; }
    let thread = unsafe { addr_of!((*cpu).current).read() };
    if thread.is_null() { return; }
    let process = unsafe { addr_of!((*thread).proc).read() };
    if process.is_null() { return; }

    // Perf open/fork construction registered this identity before visibility.
    // An unrelated never-managed Process needs no terminal allocation or route.
    let handle = match unsafe { process_targets::existing(process) } {
        Ok(Some(handle)) => handle,
        Ok(None) => return,
        Err(error) => {
            unsafe { descriptors::mark_owned_host_unresolved(process, HostUnissued::GateFailure(error)) };
            return;
        },
    };
    // Closing excludes future open/ordinary-close transactions. Waiting here
    // is outside all original caller and registry locks. Keep the handle alive
    // until this guard is dropped, so its real waitqueue storage cannot move.
    let _terminal = match unsafe { handle.terminal() } {
        Ok(guard) => guard,
        Err(error) => {
            unsafe { descriptors::mark_owned_host_unresolved(process, HostUnissued::GateFailure(error)) };
            return;
        },
    };
    if !unsafe { same_current_owner(thread, process) } {
        unsafe { descriptors::mark_owned_host_unresolved(process, HostUnissued::WrongCurrentOwner) };
        return;
    }
    if !unsafe { host_route_available(process) } {
        unsafe { descriptors::mark_owned_host_unresolved(process, HostUnissued::NoHostFlag) };
        return;
    }

    loop {
        // This exact helper owns the P lookup and R semantic-kind check, takes
        // one unique LIVE+Owned close token, unlinks and releases P/R BEFORE
        // returning. PendingChildRoute is never a child fd-table permission.
        let token = match unsafe { descriptors::take_terminal_owned(process) } {
            Ok(Some(token)) => token,
            Ok(None) => break,
            Err(error) => {
                unsafe { descriptors::mark_owned_host_unresolved(process, HostUnissued::GateFailure(error)) };
                break;
            },
        };
        {
            // Existing forwards finish on this descriptor G; no new forward
            // can pass Closing. The token pins storage through wait and call.
            let gated = unsafe { token.gate().close() };
            match gated {
                Err(error) => unsafe { token.mark_host_unissued(HostUnissued::GateFailure(error)) },
                Ok(_forward) => {
                    if token.process() != process || !unsafe { same_current_owner(thread, process) } {
                        unsafe { token.mark_host_unissued(HostUnissued::WrongCurrentOwner) };
                    } else if !unsafe { host_route_available(process) } {
                        unsafe { token.mark_host_unissued(HostUnissued::NoHostFlag) };
                    } else if matches!(token.host_state(), HostState::Owned) {
                        let fd = token.host_fd();
                        // The actual successful open/inherit path bounds this
                        // value to a nonnegative CInt before publication.
                        if CInt::try_from(fd).map_or(true, |value| value < 0) {
                            unsafe { token.mark_host_unissued(HostUnissued::InterruptedOwnerRoute) };
                        } else {
                            let mut request = MaybeUninit::<SyscallRequest>::zeroed();
                            let request_ptr = request.as_mut_ptr();
                            unsafe {
                                (*request_ptr).number = NR_CLOSE;
                                (*request_ptr).args[0] = fd as CULong;
                            }
                            let cpu = unsafe { crate::x86_local::ihk_mc_get_processor_id() };
                            let result = unsafe { super::super::do_syscall(request_ptr, cpu) };
                            // Preserve every genuine nonzero signed result.
                            // A zero after the route disappeared is NOT a close
                            // ACK merely because an offload endpoint returned0.
                            if result != 0 || (unsafe { same_current_owner(thread, process) }
                                && unsafe { host_route_available(process) }) {
                                unsafe { token.record_host_result(result) };
                            } else {
                                unsafe { token.mark_host_unissued(HostUnissued::InterruptedOwnerRoute) };
                            }
                        }
                    }
                },
            }
        } // descriptor G is released BEFORE actual unlink-retirement callbacks.
        if !unsafe { retire(token) } {
            unsafe { descriptors::mark_owned_host_unresolved(process, HostUnissued::InterruptedOwnerRoute) };
            return;
        }
        // A nohost/context change cannot cause another numeric-FD call. The
        // remaining actual owned entries retain explicit unissued disposition.
        if !unsafe { same_current_owner(thread, process) } {
            unsafe { descriptors::mark_owned_host_unresolved(process, HostUnissued::WrongCurrentOwner) };
            return;
        }
        if !unsafe { host_route_available(process) } {
            unsafe { descriptors::mark_owned_host_unresolved(process, HostUnissued::NoHostFlag) };
            return;
        }
    }
}

// Exact current production C ABIs and the complete initialized real carrier.
const _: unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong = super::super::do_syscall;
const _: unsafe extern "C" fn(*mut c_void) = super::super::syscall_mckfd_free_bridge;
const _: () = {
    assert!(size_of::<SyscallRequest>() == 72 && align_of::<SyscallRequest>() == 8);
    assert!(size_of::<CInt>() == 4 && size_of::<CLong>() == 8 && size_of::<CULong>() == 8);
};
