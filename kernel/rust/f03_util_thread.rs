//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
//! Complete ordinary-profile UTI orchestration over the existing real providers.

use core::mem::{align_of, offset_of, size_of, MaybeUninit};
use core::ptr::{addr_of, addr_of_mut, copy_nonoverlapping, null_mut, read_volatile};

use crate::abi::{CInt, CLong, CULong, SyscallRequest, UtiAttr, UtiCtx, UtiInfo, UtiKattr};
use crate::debug::Ddebug;
use crate::uti_data_providers::{f03_uti_info_data_initialize_v1, EXISTING_DATA_PROVIDERS};

#[cfg(any(not(target_arch = "x86_64"), not(native_linux_irq_work_v6_12),
          not(enable_profile), not(enable_perf), not(enable_rusage), enable_tofu,
          enable_fugaku_hacks, dcfa_kmod, not(f03_do_syscall_outer_candidate),
          not(f03_do_exit_supported_candidate), not(f03_terminate_candidate)))]
compile_error!("util_thread requires the paired ordinary dispatch/exit/terminate profile");

const ENOMEM: CInt = 12;
const IHK_MC_AP_NOWAIT: CULong = 2;
const SYS_SCHED_SETAFFINITY: CULong = 203;
const UTI_STATE_PROLOGUE: CInt = 1;
const UTI_STATE_RUNNING_IN_LINUX: CInt = 2;
const UTI_STATE_EPILOGUE: CInt = 3;
const EXIT_GROUP: CLong = 0x1_0000_0000;

// Reuse the existing paired C source/debug identity. These are the original
// logical syscall.c origins, including the reviewed initializer's #line reset.
const SOURCE_FILE: &[u8] = concat!(env!("MCKERNEL_DO_SYSCALL_C_FILE"), "\0").as_bytes();
const FUNCTION: *const i8 = b"util_thread\0".as_ptr().cast();
const INITIAL_DEBUG_FLAGS: u32 = match env!("MCKERNEL_DO_SYSCALL_DDEBUG_FLAGS").as_bytes() {
    b"0" => 0,
    b"1" => 1,
    _ => panic!("util_thread debug flags must match the paired C definition"),
};

const fn debug_record(line: u32) -> Ddebug {
    Ddebug {
        file: SOURCE_FILE.as_ptr().cast(),
        func: FUNCTION,
        fmt: core::ptr::null(),
        line_flags: line | (INITIAL_DEBUG_FLAGS << 24),
    }
}

#[used]
#[link_section = "__verbose"]
static mut UTIL_THREAD_DEBUG: [Ddebug; 4] = [
    debug_record(28361),
    debug_record(28369),
    debug_record(28379),
    debug_record(28384),
];

unsafe extern "C" {
    // Existing unique storage; registration and descriptor lifetime stay owned
    // by the original caller/host protocol. This declaration defines no storage.
    static mut uti_desc: CULong;
}

unsafe fn debug_enabled(index: usize) -> bool {
    // SAFETY: Same live mutable ddebug record and volatile flag read as dkprintf.
    unsafe { read_volatile(addr_of!(UTIL_THREAD_DEBUG[index].line_flags)) >> 24 != 0 }
}

unsafe fn release_partial(context: *mut UtiCtx, info: *mut UtiInfo) {
    // SAFETY: The original out label always calls both tracked frees, including
    // NULL. These pointers are either still-owned allocations or both NULL after
    // the earlier normal frees. No automatic destructor changes this order.
    unsafe {
        (EXISTING_DATA_PROVIDERS.free_tracked)(
            context.cast(), SOURCE_FILE.as_ptr().cast_mut().cast(), 28397,
        );
        (EXISTING_DATA_PROVIDERS.free_tracked)(
            info.cast(), SOURCE_FILE.as_ptr().cast_mut().cast(), 28398,
        );
    }
}

/// Preserve the original complete util_thread state/request/exit transaction.
///
/// # Safety
/// The original current CPU, Thread, Process, CLS, VM, futex/global and registered
/// descriptor contracts must hold. A nonnull `argument` is a readable kernel
/// UtiAttr for the synchronous call, not an unchecked user pointer. The original
/// peer must keep every borrowed address live, initialize the consumed refill TID
/// and finish its borrows before the genuine do_syscall return allows these same
/// frees. This port does not establish that external completion/ACK/drain fact.
/// Existing exit/terminate providers retain their current-stack, IRQ, lock and
/// process-lifetime requirements; their void ABI may return. No whole-object Rust
/// reference spans an offload, formatter, context switch or release.
#[no_mangle]
pub unsafe extern "C" fn util_thread(argument: *mut UtiAttr) -> CInt {
    // SAFETY: Preserve the original initial current-thread lookup and plain state
    // store under the caller's existing current-thread exclusion.
    let local = unsafe { (EXISTING_DATA_PROVIDERS.current_cpu_local)() };
    let thread = unsafe { addr_of!((*local).current).read() };
    unsafe { addr_of_mut!((*thread).uti_state).write(UTI_STATE_PROLOGUE) };

    // SAFETY: Exact original allocator flags, size, filename and logical origin.
    // A successful allocation is not treated as an initialized UtiCtx value.
    let context = unsafe {
        (EXISTING_DATA_PROVIDERS.allocate_tracked)(
            size_of::<UtiCtx>() as CInt, IHK_MC_AP_NOWAIT,
            SOURCE_FILE.as_ptr().cast_mut().cast(), 28314,
        ).cast::<UtiCtx>()
    };
    if context.is_null() {
        unsafe { release_partial(context, null_mut()) };
        return -ENOMEM;
    }
    // SAFETY: Preserve address translation before the actual save_uctx provider;
    // no context byte or host-owned refill field is read here.
    let physical_context = unsafe {
        (EXISTING_DATA_PROVIDERS.virtual_to_physical)(context.cast())
    };
    unsafe {
        (EXISTING_DATA_PROVIDERS.save_user_context)(context.cast(), null_mut())
    };

    // SAFETY: Same second allocation. Failure releases the first allocation and
    // the NULL second pointer through the original common out-label sequence.
    let info = unsafe {
        (EXISTING_DATA_PROVIDERS.allocate_tracked)(
            size_of::<UtiInfo>() as CInt, IHK_MC_AP_NOWAIT,
            SOURCE_FILE.as_ptr().cast_mut().cast(), 28323,
        ).cast::<UtiInfo>()
    };
    if info.is_null() {
        unsafe { release_partial(context, info) };
        return -ENOMEM;
    }
    // SAFETY: Reuse the reviewed twelve-field initializer byte-for-byte. Nine
    // host-owned pointer slots and padding remain untouched; no initialized
    // whole UtiInfo reference/value is formed.
    unsafe { f03_uti_info_data_initialize_v1(info, thread) };

    let mut request_slot = MaybeUninit::<SyscallRequest>::uninit();
    let request = request_slot.as_mut_ptr();
    let mut attribute_slot = MaybeUninit::<UtiKattr>::uninit();
    let attribute = attribute_slot.as_mut_ptr();
    // SAFETY: Write only the original caller-owned request fields. The genuine
    // do_syscall provider initializes its transport header before consumption.
    // All six argument slots are defined; args[5] retains the accepted zero fix.
    unsafe {
        addr_of_mut!((*request).number).write(SYS_SCHED_SETAFFINITY);
        addr_of_mut!((*request).args[0]).write(0);
        addr_of_mut!((*request).args[1]).write(physical_context);
        addr_of_mut!((*request).args[2]).write(0);
    }
    if !argument.is_null() {
        // SAFETY: Same memcpy of the readable kernel attribute to disjoint local
        // storage, then signed int-to-long parent CPU promotion. The stack slot
        // stays live until the synchronous provider has completed its borrows.
        unsafe {
            copy_nonoverlapping(
                argument.cast::<u8>(), addr_of_mut!((*attribute).attr).cast(),
                size_of::<UtiAttr>(),
            );
            addr_of_mut!((*attribute).parent_cpuid)
                .write(addr_of!((*thread).parent_cpuid).read() as CLong);
            let physical_attribute =
                (EXISTING_DATA_PROVIDERS.virtual_to_physical)(attribute.cast());
            addr_of_mut!((*request).args[2]).write(physical_attribute);
        }
    }
    unsafe {
        addr_of_mut!((*request).args[3]).write(info as CULong);
        addr_of_mut!((*request).args[4]).write(addr_of!(uti_desc).read());
        addr_of_mut!((*thread).uti_state).write(UTI_STATE_RUNNING_IN_LINUX);
        addr_of_mut!((*request).args[5]).write(0);
    }
    // SAFETY: Both heap allocations and both local request/attribute slots stay
    // live through the actual selected Rust offload transaction. No callback,
    // substitute return, early free, timeout or completion state is introduced.
    let result = unsafe {
        crate::syscall_offload_entry::do_syscall(
            request, (EXISTING_DATA_PROVIDERS.processor_id)(),
        )
    };
    if unsafe { debug_enabled(0) } {
        unsafe {
            crate::debug::kprintf(
                b"%s: returned from do_syscall,tid=%d,rc=%lx\n\0".as_ptr().cast(),
                FUNCTION, addr_of!((*thread).tid).read(), result,
            );
        }
    }
    unsafe { addr_of_mut!((*thread).uti_state).write(UTI_STATE_EPILOGUE) };
    // SAFETY: Original profile call precedes refill consumption and both frees;
    // the registered descriptor's lifetime is still an original prerequisite.
    let _ = unsafe { crate::syscall_policy::util_show_syscall_profile() };
    // SAFETY: The original peer-completion contract must initialize this field
    // and end its borrows before return. Read it before freeing context; do not
    // assume initialization or final ACK from the pointer/return value alone.
    let refill_tid = unsafe { addr_of!((*context).refill.uti_refill_tid).read() };
    unsafe { addr_of_mut!((*thread).uti_refill_tid).write(refill_tid) };
    if unsafe { debug_enabled(1) } {
        unsafe {
            crate::debug::kprintf(
                b"%s: mcexec worker tid=%d\n\0".as_ptr().cast(),
                FUNCTION, addr_of!((*thread).uti_refill_tid).read(),
            );
        }
    }
    // SAFETY: Same normal frees and origins, before any exit/terminate callback.
    // No Thread/Process reference is retained across either possible release.
    unsafe {
        (EXISTING_DATA_PROVIDERS.free_tracked)(
            context.cast(), SOURCE_FILE.as_ptr().cast_mut().cast(), 28371,
        );
        (EXISTING_DATA_PROVIDERS.free_tracked)(
            info.cast(), SOURCE_FILE.as_ptr().cast_mut().cast(), 28374,
        );
    }
    if result >= 0 {
        if result & EXIT_GROUP != 0 {
            if unsafe { debug_enabled(2) } {
                unsafe {
                    crate::debug::kprintf(
                        b"%s: exit_group, tid=%d,rc=%lx\n\0".as_ptr().cast(),
                        FUNCTION, addr_of!((*thread).tid).read(), result,
                    );
                }
            }
            let process = unsafe { addr_of!((*thread).proc).read() };
            unsafe {
                addr_of_mut!((*process).nohost).write(1);
                crate::f03_terminate::terminate(
                    ((result >> 8) & 255) as CInt, (result & 255) as CInt,
                );
            }
        } else {
            if unsafe { debug_enabled(3) } {
                unsafe {
                    let process = addr_of!((*thread).proc).read();
                    crate::debug::kprintf(
                        b"%s: exit or killed by signal, pid=%d,tid=%d,rc=%lx\n\0"
                            .as_ptr().cast(),
                        FUNCTION, addr_of!((*process).pid).read(),
                        addr_of!((*thread).tid).read(), result,
                    );
                }
            }
            // SAFETY: Same C-long to C-int conversion at the real exit ABI.
            unsafe { crate::syscall_policy::f03_do_exit_supported_v2(result as CInt) };
        }
    } else if crate::syscall_policy::syscall_proxy_dead_result(result) != 0 {
        unsafe {
            let process = addr_of!((*thread).proc).read();
            crate::debug::kprintf(
                b"%s: release_handler,pid=%d,tid=%d,rc=%lx\n\0".as_ptr().cast(),
                FUNCTION, addr_of!((*process).pid).read(),
                addr_of!((*thread).tid).read(), result,
            );
            // Reload the field after the formatter, as the original C does.
            let process = addr_of!((*thread).proc).read();
            addr_of_mut!((*process).nohost).write(1);
            crate::syscall_policy::f03_do_exit_supported_v2(result as CInt);
        }
    } else {
        unsafe {
            crate::debug::kprintf(
                b"%s: ERROR: do_syscall() failed (%ld)\n\0".as_ptr().cast(),
                FUNCTION, result,
            );
        }
    }
    // SAFETY: Original context/info locals were NULL after their normal frees.
    // Preserve both NULL frees if a void exit provider unexpectedly returns;
    // never touch Thread/Process/context/info after that provider can release it.
    unsafe { release_partial(null_mut(), null_mut()) };
    result as CInt
}

// The public int(pointer) body and both reused void endpoints retain their real
// ABI. Existing Rust callers perform the original signed int-to-long promotion.
const _: unsafe extern "C" fn(*mut UtiAttr) -> CInt = util_thread;
const _: unsafe extern "C" fn(CInt) = crate::syscall_policy::f03_do_exit_supported_v2;
const _: unsafe extern "C" fn(CInt, CInt) = crate::f03_terminate::terminate;
const _: () = {
    assert!(size_of::<CInt>() == 4 && size_of::<CLong>() == 8);
    assert!(size_of::<SyscallRequest>() == 72 && align_of::<SyscallRequest>() == 8);
    assert!(offset_of!(SyscallRequest, args) == 24);
    assert!(size_of::<UtiCtx>() == 4096 && size_of::<UtiInfo>() == 160);
    assert!(size_of::<UtiAttr>() == 136 && size_of::<UtiKattr>() == 144);
};
