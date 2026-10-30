// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Actual-crate frontend only: no production exports or selector authority.
use core::mem::{align_of, offset_of, size_of, MaybeUninit};
use core::ptr::{addr_of, addr_of_mut, read_volatile, write_volatile};
use core::sync::atomic::{compiler_fence, AtomicU64, Ordering};

use crate::abi::{
    CInt, CLong, CULong, CpuLocalVar, IhkOsCpuMonitor, Process, SyscallRequest,
    SyscallResponse, Thread,
};
use crate::debug::Ddebug;

use super::{
    ihk_mc_get_processor_id, send_syscall, syscall_offload_counted_result,
    syscall_offload_prepare_result, syscall_offload_wait_reply, syscall_owner_log_budget,
    syscall_preempt_disable_needed_result, syscall_profile_event_needed_result,
    syscall_proxy_dead_result,
};

unsafe extern "C" {
    static f03_do_syscall_constants_v1: [CULong; 5];
    static mut f03_do_syscall_debug_v1: [Ddebug; 6];
    fn kprintf(format: *const i8, ...) -> CInt;
}

// Reuse the existing Rust offload logger's linearized PID/count state. It
// matches the old serial 64-message budget and avoids the original shared
// C static ints' unsynchronized accesses. This is a correctness extension,
// not a claim of cross-CPU C data-race parity or ordered console delivery.
static RETURN_LOG_STATE: AtomicU64 = AtomicU64::new((u32::MAX as u64) << 32);

macro_rules! debug {
    ($index:expr, $format:expr $(, $value:expr)* $(,)?) => {{
        // SAFETY: Original static lexical records and exact scalar varargs.
        unsafe {
            if read_volatile(addr_of!(f03_do_syscall_debug_v1[$index].line_flags)) >> 24 != 0 {
                kprintf($format.as_ptr().cast() $(, $value)*);
            }
        }
    }};
}

/// Execute the existing Rust offload transaction and original caller accounting.
///
/// # Safety
/// The current CPU, monitor, thread/process and selected IKC channel remain
/// live for the entire offload, including nested service/scheduling callbacks.
/// request is aligned and its number and all six argument scalars are
/// initialized before entry. The existing prepare helper assigns rtid and
/// ttid, and the existing sender assigns valid before copying/publishing.
/// No pointer ownership is created or foreign whole-object reference made.
/// The host's release/completion contract makes the final response readable.
/// This precondition excludes the separately held partial exec requests; no
/// guessed field initialization or host acknowledgement is supplied here.
pub unsafe extern "C" fn f03_do_syscall_supported_v1(
    request: *mut SyscallRequest, cpu: CInt,
) -> CLong {
    // SAFETY: These are exactly the caller-owned current objects. Raw field
    // operations never create a fully initialized response reference.
    unsafe {
        let local = crate::cls::get_this_cpu_local_var();
        let thread = read_volatile(addr_of!((*local).current));
        let monitor = read_volatile(addr_of!((*local).monitor));
        let process = read_volatile(addr_of!((*thread).proc));
        let pid = if process.is_null() { -1 } else { (*process).pid };
        let started = if read_volatile(addr_of!((*thread).profile)) != 0 {
            crate::x86_cpu_helpers::rdtsc()
        } else {
            0
        };
        let exit_group = f03_do_syscall_constants_v1[0] as CInt;
        let setaffinity = f03_do_syscall_constants_v1[1] as CInt;
        let spinning = f03_do_syscall_constants_v1[2];
        let offload_monitor = f03_do_syscall_constants_v1[3] as CInt;
        let profile_max = f03_do_syscall_constants_v1[4] as CInt;
        let number = read_volatile(addr_of!((*request).number)) as CInt;

        debug!(0, b"SC(%d)[%3d] sending syscall\n\0", ihk_mc_get_processor_id(), number);
        let old_monitor_status = read_volatile(addr_of!((*monitor).status));
        write_volatile(addr_of_mut!((*monitor).status), offload_monitor);
        // C barrier() orders compiler accesses; no new hardware fence.
        compiler_fence(Ordering::SeqCst);
        if syscall_offload_counted_result(number, exit_group) != 0 {
            let count = addr_of_mut!((*thread).in_syscall_offload);
            write_volatile(count, read_volatile(count).wrapping_add(1));
        }

        let mut response = MaybeUninit::<SyscallResponse>::uninit();
        let response_ptr = response.as_mut_ptr();
        let current = read_volatile(addr_of!((*crate::cls::get_this_cpu_local_var()).current));
        let use_requester = syscall_offload_prepare_result(
            request, response_ptr, read_volatile(addr_of!((*current).tid)), number,
            read_volatile(addr_of!((*request).args[0])), setaffinity, spinning,
        );
        if use_requester < 0 {
            // No send or host access occurred. Roll back this entry's local
            // accounting while preserving the exact preparation error result.
            if syscall_offload_counted_result(number, exit_group) != 0 {
                let count = addr_of_mut!((*thread).in_syscall_offload);
                write_volatile(count, read_volatile(count).wrapping_sub(1));
            }
            write_volatile(addr_of_mut!((*monitor).status), old_monitor_status);
            return use_requester as CLong;
        }
        if use_requester != 0 {
            debug!(1, b"%s: uti, ttid=%d\n\0", c"do_syscall".as_ptr(), (*request).ttid);
        }
        send_syscall(request, cpu, response_ptr);
        if syscall_preempt_disable_needed_result((*request).rtid) != 0 {
            crate::cls::preempt_disable();
        }
        debug!(2, b"%s: syscall num: %d waiting for Linux.. \n\0",
            c"do_syscall".as_ptr(), number);
        syscall_offload_wait_reply(request, response_ptr, cpu, thread);
        if syscall_preempt_disable_needed_result((*request).rtid) != 0 {
            crate::cls::preempt_enable();
        }
        // Only the completed ret field is read. Other response fields can
        // remain uninitialized unless the genuine protocol wrote them.
        let result = read_volatile(addr_of!((*response_ptr).ret));
        debug!(3, b"%s: syscall num: %d got host reply: %d \n\0",
            c"do_syscall".as_ptr(), number, result as CInt);
        if syscall_owner_log_budget(&RETURN_LOG_STATE, pid) {
            kprintf(
                concat!(
                    "mcexec_v10: offload_return cpu=%d pid=%d tid=%d nr=%d ",
                    "ret=0x%lx ret_signed=%ld\n\0",
                ).as_ptr().cast(),
                cpu, pid, read_volatile(addr_of!((*thread).tid)), number,
                result as CULong, result,
            );
        }
        if syscall_offload_counted_result(number, exit_group) != 0 {
            let count = addr_of_mut!((*thread).in_syscall_offload);
            write_volatile(count, read_volatile(count).wrapping_sub(1));
        }
        if syscall_proxy_dead_result(result) != 0 {
            debug!(4, b"%s: proxy PID %d is dead, terminate()\n\0",
                c"do_syscall".as_ptr(), (*process).pid);
            write_volatile(addr_of_mut!((*process).nohost), 1);
        }
        if syscall_profile_event_needed_result(number, profile_max) != 0 {
            let event = crate::profile::profile_syscall2offload(number);
            crate::profile::profile_event_add(
                event, crate::x86_cpu_helpers::rdtsc().wrapping_sub(started),
            );
        } else {
            debug!(5, b"%s: offload syscall > %d ?? : %d\n\0",
                c"do_syscall".as_ptr(), profile_max, number);
        }
        write_volatile(addr_of_mut!((*monitor).status), old_monitor_status);
        let counter = addr_of_mut!((*monitor).counter);
        write_volatile(counter, read_volatile(counter).wrapping_add(1));
        result
    }
}

#[used]
pub static f03_do_syscall_Rust_ABI_v1: [CULong; 29] = [
    size_of::<SyscallRequest>() as CULong,
    align_of::<SyscallRequest>() as CULong,
    offset_of!(SyscallRequest, rtid) as CULong,
    offset_of!(SyscallRequest, ttid) as CULong,
    offset_of!(SyscallRequest, valid) as CULong,
    offset_of!(SyscallRequest, number) as CULong,
    offset_of!(SyscallRequest, args) as CULong,
    size_of::<SyscallResponse>() as CULong,
    align_of::<SyscallResponse>() as CULong,
    offset_of!(SyscallResponse, status) as CULong,
    offset_of!(SyscallResponse, req_thread_status) as CULong,
    offset_of!(SyscallResponse, ret) as CULong,
    offset_of!(SyscallResponse, pde_data) as CULong,
    size_of::<IhkOsCpuMonitor>() as CULong,
    align_of::<IhkOsCpuMonitor>() as CULong,
    offset_of!(IhkOsCpuMonitor, status) as CULong,
    offset_of!(IhkOsCpuMonitor, counter) as CULong,
    size_of::<CpuLocalVar>() as CULong,
    align_of::<CpuLocalVar>() as CULong,
    offset_of!(CpuLocalVar, current) as CULong,
    offset_of!(CpuLocalVar, monitor) as CULong,
    size_of::<Thread>() as CULong,
    align_of::<Thread>() as CULong,
    offset_of!(Thread, tid) as CULong,
    offset_of!(Thread, proc) as CULong,
    offset_of!(Thread, profile) as CULong,
    offset_of!(Thread, in_syscall_offload) as CULong,
    offset_of!(Process, pid) as CULong,
    offset_of!(Process, nohost) as CULong,
];

// Exact actual-crate prototypes, checked by the affected frontend.
const _: unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong = f03_do_syscall_supported_v1;
const _: unsafe extern "C" fn(*mut SyscallRequest, CInt, *mut SyscallResponse) = send_syscall;
const _: unsafe extern "C" fn(*mut SyscallRequest, *mut SyscallResponse, CInt, CInt, CULong, CInt, CULong) -> CInt = syscall_offload_prepare_result;
const _: unsafe extern "C" fn(*mut SyscallRequest, *mut SyscallResponse, CInt, *mut Thread) = syscall_offload_wait_reply;
const _: unsafe extern "C" fn() -> *mut CpuLocalVar = crate::cls::get_this_cpu_local_var;
