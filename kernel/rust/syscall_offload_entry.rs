// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! The real delegated-syscall outer entry. The existing Rust transport and reply
//! state machine retain their implementation and all nested/fork-control work.

#[cfg(not(all(target_arch = "x86_64", native_linux_irq_work_v6_12, enable_profile)))]
compile_error!("do_syscall outer requires its paired x86_64/linux-6.12/PROFILE profile");

use core::mem::{align_of, offset_of, size_of, MaybeUninit};
use core::ptr::{addr_of, addr_of_mut, read, read_volatile, write, write_volatile};
use core::sync::atomic::AtomicU64;

use crate::abi::{CInt, CLong, CULong, Process, SyscallRequest, SyscallResponse, Thread};
use crate::debug::Ddebug;
use crate::syscall_policy;

const SYS_EXIT_GROUP: CInt = 231;
const SYS_SCHED_SETAFFINITY: CInt = 203;
const REQUEST_THREAD_SPINNING: CULong = 0;
const MONITOR_KERNEL_OFFLOAD: CInt = 5;
#[cfg(enable_profile)]
const PROFILE_SYSCALL_MAX: CInt = 2000;
#[cfg(enable_tofu)]
const SYS_IOCTL: CInt = 16;
#[cfg(enable_tofu)]
const SYS_OPENAT: CInt = 257;
#[cfg(enable_tofu)]
const MAX_FD_PDE: CInt = 1024;

// The C source asserts its actual __FILE__ and DDEBUG_DEFAULT against these
// same build inputs. Original logical C line identities are retained by the
// paired C guard's #line directives; no Rust file!()/line!() substitution.
const SOURCE_FILE: &[u8] = concat!(env!("MCKERNEL_DO_SYSCALL_C_FILE"), "\0").as_bytes();
const INITIAL_DEBUG_FLAGS: u32 = match env!("MCKERNEL_DO_SYSCALL_DDEBUG_FLAGS").as_bytes() {
    b"0" => 0,
    b"1" => 1,
    _ => panic!("do_syscall DDEBUG flags must match the C definition"),
};
const FUNCTION_NAME: &[u8] = b"do_syscall\0";
const _: () = assert!(SOURCE_FILE.len() > 1);

const fn debug_record(line: u32) -> Ddebug {
    Ddebug {
        file: SOURCE_FILE.as_ptr().cast(),
        func: FUNCTION_NAME.as_ptr().cast(),
        fmt: core::ptr::null(),
        line_flags: (line & 0x00ff_ffff) | (INITIAL_DEBUG_FLAGS << 24),
    }
}

#[used]
#[link_section = "__verbose"]
static mut SEND_DEBUG: Ddebug = debug_record(4149);
#[used]
#[link_section = "__verbose"]
static mut REQUESTER_DEBUG: Ddebug = debug_record(4183);
#[used]
#[link_section = "__verbose"]
static mut WAIT_DEBUG: Ddebug = debug_record(4191);
#[used]
#[link_section = "__verbose"]
static mut REPLY_DEBUG: Ddebug = debug_record(4363);
#[cfg(enable_tofu)]
#[used]
#[link_section = "__verbose"]
static mut TOFU_DEBUG: Ddebug = debug_record(4392);
#[used]
#[link_section = "__verbose"]
static mut PROXY_DEBUG: Ddebug = debug_record(4410);
#[cfg(enable_profile)]
#[used]
#[link_section = "__verbose"]
static mut PROFILE_DEBUG: Ddebug = debug_record(4422);

// Same sequential initial PID=-1/count=0, reset-on-PID-change and budget64 as
// the C counters. The existing real helper serializes only this diagnostic
// budget; no request, reply, thread or process state is published by it.
static RETURN_LOG_STATE: AtomicU64 = AtomicU64::new((u32::MAX as u64) << 32);

#[inline(always)]
unsafe fn debug_enabled(record: *const Ddebug) -> bool {
    // The genuine dkprintf macro tests any nonzero flags, not only bit zero.
    unsafe { read_volatile(addr_of!((*record).line_flags)) >> 24 != 0 }
}

// These are the genuinely new field accesses of the outer port. The paired C
// selection asserts the same offsets under the actual generated configuration.
const _: () = {
    assert!(size_of::<SyscallRequest>() == 72 && align_of::<SyscallRequest>() == 8);
    assert!(size_of::<SyscallResponse>() == 48 && align_of::<SyscallResponse>() == 8);
    assert!(offset_of!(Thread, in_syscall_offload) == 4792);
    assert!(offset_of!(Thread, profile) == 4796);
    assert!(offset_of!(Process, nohost) == 500);
};

/// Own the complete supported delegated-syscall outer orchestration.
///
/// # Safety
/// The original C entry's context is required: request is live, writable and
/// naturally aligned; number/consumed arguments are initialized; cpu selects a
/// live IKC channel; the current Thread, Process, monitor and scheduler graph
/// remain live throughout synchronous send/wait/nested work. The Linux proxy
/// must obey the actual response publication protocol. No exclusive Rust
/// reference spans transport, a callback or a context switch. This entry adds
/// no process reference, native admission, timeout, cancellation or free.
#[no_mangle]
pub unsafe extern "C" fn do_syscall(request: *mut SyscallRequest, cpu: CInt) -> CLong {
    // Define unused response bytes too: existing selected control code may
    // create a typed view after completion. Zero is IN_PROGRESS, never a fake
    // completion. The real producer must still publish the actual reply.
    let mut response_slot = MaybeUninit::<SyscallResponse>::zeroed();
    let response = response_slot.as_mut_ptr();
    let thread = unsafe { (*crate::cls::get_this_cpu_local_var()).current };
    let monitor = unsafe { (*crate::cls::get_this_cpu_local_var()).monitor };
    let pid = unsafe {
        if thread.is_null() || (*thread).proc.is_null() {
            -1
        } else {
            (*(*thread).proc).pid
        }
    };
    #[cfg(enable_profile)]
    let started = unsafe {
        if read(addr_of!((*thread).profile)) != 0 {
            crate::x86_cpu_helpers::rdtsc()
        } else {
            0
        }
    };

    unsafe {
        if debug_enabled(addr_of!(SEND_DEBUG)) {
            crate::debug::kprintf(
                b"SC(%d)[%3d] sending syscall\n\0".as_ptr().cast(),
                crate::x86_local::ihk_mc_get_processor_id(),
                read(addr_of!((*request).number)) as CInt,
            );
        }
    }
    let saved_monitor_status = unsafe { read_volatile(addr_of!((*monitor).status)) };
    unsafe { write_volatile(addr_of_mut!((*monitor).status), MONITOR_KERNEL_OFFLOAD) };
    // Same compiler memory clobber as C barrier(); deliberately no nomem or
    // readonly option and no newly introduced hardware fence.
    unsafe { core::arch::asm!("", options(nostack, preserves_flags)) };

    unsafe {
        if syscall_policy::syscall_offload_counted_result(
            read(addr_of!((*request).number)) as CInt, SYS_EXIT_GROUP,
        ) != 0 {
            let count = addr_of_mut!((*thread).in_syscall_offload);
            write(count, read(count).wrapping_add(1));
        }
    }

    let use_requester_tid = unsafe {
        syscall_policy::syscall_offload_prepare_result(
            request, response,
            (*(*crate::cls::get_this_cpu_local_var()).current).tid,
            read(addr_of!((*request).number)) as CInt,
            read(addr_of!((*request).args[0])),
            SYS_SCHED_SETAFFINITY, REQUEST_THREAD_SPINNING,
        )
    };
    if use_requester_tid < 0 {
        // Keep the original early-return point; this is not a newly invented
        // recovery or cleanup policy for invalid original caller arguments.
        return use_requester_tid as CLong;
    }
    unsafe {
        if use_requester_tid != 0 && debug_enabled(addr_of!(REQUESTER_DEBUG)) {
            crate::debug::kprintf(
                b"%s: uti, ttid=%d\n\0".as_ptr().cast(),
                FUNCTION_NAME.as_ptr().cast::<i8>(), read(addr_of!((*request).ttid)),
            );
        }
        syscall_policy::send_syscall(request, cpu, response);
        if syscall_policy::syscall_preempt_disable_needed_result(read(addr_of!((*request).rtid))) != 0 {
            crate::cls::preempt_disable();
        }
        if debug_enabled(addr_of!(WAIT_DEBUG)) {
            crate::debug::kprintf(
                b"%s: syscall num: %d waiting for Linux.. \n\0".as_ptr().cast(),
                FUNCTION_NAME.as_ptr().cast::<i8>(), read(addr_of!((*request).number)) as CInt,
            );
        }
        // Actual Rust state machine: IRQ/waitq/runqueue scheduling, nested
        // services and genuine outer fork-control observation stay unchanged.
        syscall_policy::syscall_offload_wait_reply(request, response, cpu, thread);
        if syscall_policy::syscall_preempt_disable_needed_result(read(addr_of!((*request).rtid))) != 0 {
            crate::cls::preempt_enable();
        }
        if debug_enabled(addr_of!(REPLY_DEBUG)) {
            crate::debug::kprintf(
                b"%s: syscall num: %d got host reply: %d \n\0".as_ptr().cast(),
                FUNCTION_NAME.as_ptr().cast::<i8>(),
                read(addr_of!((*request).number)) as CInt,
                read_volatile(addr_of!((*response).ret)) as CInt,
            );
        }
    }

    // The real wait acquired this exact completed response before returning.
    let rc = unsafe { read_volatile(addr_of!((*response).ret)) };
    if syscall_policy::syscall_owner_log_budget(&RETURN_LOG_STATE, pid) {
        unsafe {
            crate::debug::kprintf(
                b"mcexec_v10: offload_return cpu=%d pid=%d tid=%d nr=%d ret=0x%lx ret_signed=%ld\n\0"
                    .as_ptr().cast(),
                cpu, pid, if thread.is_null() { -1 } else { (*thread).tid },
                read(addr_of!((*request).number)) as CInt, rc as CULong, rc,
            );
        }
    }

    #[cfg(enable_tofu)]
    unsafe {
        if syscall_policy::syscall_tofu_post_reply_candidate_result(
            read(addr_of!((*request).number)) as CInt, rc, SYS_IOCTL, SYS_OPENAT,
        ) != 0 {
            // Preserve the original full-width ioctl comparison followed by
            // C-int narrowing, path selection and short-circuit evaluation.
            let is_ioctl = read(addr_of!((*request).number)) == SYS_IOCTL as CULong;
            let fd = if is_ioctl { read(addr_of!((*request).args[0])) as CInt } else { rc as CInt };
            let proc = read(addr_of!((*thread).proc));
            let path = if is_ioctl {
                read(addr_of!((*proc).fd_path).cast::<*mut i8>().offset(fd as isize))
            } else {
                read(addr_of!((*thread).fd_path_in_open))
            };
            let current = (*crate::cls::get_this_cpu_local_var()).current;
            if (*(*current).proc).enable_tofu != 0
                && !read_volatile(addr_of!((*response).pde_data)).is_null()
                && fd < MAX_FD_PDE
                && read(addr_of!((*proc).fd_pde_data).cast::<*mut core::ffi::c_void>().offset(fd as isize)).is_null()
                && crate::string::strncmp(path, b"/proc/tofu/dev/\0".as_ptr().cast(), 15) == 0
            {
                // Original valid TOFU-fd/path and process lifetime contracts
                // remain required; no new unsupported-request filter is added.
                let lock = addr_of_mut!((*proc).mckfd_lock).cast::<crate::spinlock_helpers::IhkSpinlock>();
                let irqstate = crate::spinlock_helpers::__ihk_mc_spinlock_lock(lock);
                write(
                    addr_of_mut!((*proc).fd_pde_data).cast::<*mut core::ffi::c_void>().offset(fd as isize),
                    read_volatile(addr_of!((*response).pde_data)),
                );
                crate::spinlock_helpers::__ihk_mc_spinlock_unlock(lock, irqstate);
                if debug_enabled(addr_of!(TOFU_DEBUG)) {
                    crate::debug::kprintf(
                        b"%s: PID: %d, ioctl fd: %d, filename: %s, pde_data: 0x%lx\n\0".as_ptr().cast(),
                        FUNCTION_NAME.as_ptr().cast::<i8>(), (*proc).pid, fd, path,
                        read_volatile(addr_of!((*response).pde_data)) as CULong,
                    );
                }
            }
        }
    }

    unsafe {
        if syscall_policy::syscall_offload_counted_result(
            read(addr_of!((*request).number)) as CInt, SYS_EXIT_GROUP,
        ) != 0 {
            let count = addr_of_mut!((*thread).in_syscall_offload);
            write(count, read(count).wrapping_sub(1));
        }
        if syscall_policy::syscall_proxy_dead_result(rc) != 0 {
            if debug_enabled(addr_of!(PROXY_DEBUG)) {
                crate::debug::kprintf(
                    b"%s: proxy PID %d is dead, terminate()\n\0".as_ptr().cast(),
                    FUNCTION_NAME.as_ptr().cast::<i8>(), (*(*thread).proc).pid,
                );
            }
            write(addr_of_mut!((*(*thread).proc).nohost), 1);
        }
    }
    #[cfg(enable_profile)]
    unsafe {
        if syscall_policy::syscall_profile_event_needed_result(
            read(addr_of!((*request).number)) as CInt, PROFILE_SYSCALL_MAX,
        ) != 0 {
            let event = crate::profile::profile_syscall2offload(read(addr_of!((*request).number)) as CInt);
            crate::profile::profile_event_add(event, crate::x86_cpu_helpers::rdtsc().wrapping_sub(started));
        } else if debug_enabled(addr_of!(PROFILE_DEBUG)) {
            crate::debug::kprintf(
                b"%s: offload syscall > %d ?? : %d\n\0".as_ptr().cast(),
                FUNCTION_NAME.as_ptr().cast::<i8>(), PROFILE_SYSCALL_MAX,
                read(addr_of!((*request).number)) as CInt,
            );
        }
    }
    unsafe {
        write_volatile(addr_of_mut!((*monitor).status), saved_monitor_status);
        let counter = addr_of_mut!((*monitor).counter);
        write_volatile(counter, read_volatile(counter).wrapping_add(1));
    }
    rc
}

const _: unsafe extern "C" fn(*mut SyscallRequest, CInt) -> CLong = do_syscall;
