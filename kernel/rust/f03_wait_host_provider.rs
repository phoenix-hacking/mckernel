// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Required ordinary-profile host wait4 provider, independent of broad adapters.

#[cfg(not(all(target_arch = "x86_64", native_linux_irq_work_v6_12, enable_profile, f03_do_syscall_outer_candidate)))]
compile_error!("wait host provider requires the real supported do_syscall owner");
#[cfg(f03_forward_adapters_candidate)]
compile_error!("narrow wait host provider must not duplicate broad adapters");

use core::mem::{align_of, offset_of, size_of};
use core::ptr::addr_of_mut;
use crate::abi::{CInt, CLong, CULong, SyscallRequest};

const SYS_WAIT4: CULong = 61;
type WaitHostFn = unsafe extern "C" fn(CInt, CInt) -> CInt;
const _: WaitHostFn = wait_host_wait4_bridge;
const _: unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong =
    crate::syscall_offload_entry::do_syscall;
const _: unsafe extern "C" fn() -> CInt = crate::x86_local::ihk_mc_get_processor_id;
const _: () = {
    assert!(size_of::<CInt>() == 4 && align_of::<CInt>() == 4);
    assert!(size_of::<CLong>() == 8 && size_of::<CULong>() == 8);
    assert!(size_of::<SyscallRequest>() == 72 && align_of::<SyscallRequest>() == 8);
    assert!(offset_of!(SyscallRequest, rtid) == 0);
    assert!(offset_of!(SyscallRequest, ttid) == 4);
    assert!(offset_of!(SyscallRequest, valid) == 8);
    assert!(offset_of!(SyscallRequest, number) == 16);
    assert!(offset_of!(SyscallRequest, args) == 24);
};

/// Preserve the original wait callback and its synchronous request lifetime.
///
/// The selected outer overwrites rtid/ttid before sending, send_syscall resets
/// valid then publishes its packet copy. The selected nr61 launcher consumes
/// args0/args2 via waitid; args1/args3..5 are not status/rusage destinations.
/// Define those carrier bytes before the real full72B copy/publication instead
/// of propagating the C entry's unspecified stack bytes. This is not a reply,
/// ACK, new completion or a change to the caller's reap/lock/IRQ decisions.
///
/// # Safety
/// The existing wait transaction owns the live current Thread/Process, CPU and
/// initialized IKC channel across this real offload. No new reference or async
/// ownership is acquired; no Rust reference escapes the synchronous call.
#[no_mangle]
pub unsafe extern "C" fn wait_host_wait4_bridge(pid: CInt, options: CInt) -> CInt {
    let mut request = SyscallRequest {
        rtid: 0,
        ttid: 0,
        valid: 0,
        number: SYS_WAIT4,
        args: [pid as CULong, 0, options as CULong, 0, 0, 0],
    };
    let cpu = unsafe { crate::x86_local::ihk_mc_get_processor_id() };
    // The original C callback returns int, narrowing the actual long result.
    unsafe { crate::syscall_offload_entry::do_syscall(addr_of_mut!(request), cpu) as CInt }
}
