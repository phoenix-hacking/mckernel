#![no_std]

use core::ffi::{c_int, c_long, c_ulong};
use core::ptr;
use core::sync::atomic::{AtomicI32, Ordering};

const SYS_GETTID: c_long = 186;
const SYS_IOCTL: c_long = 16;
const SYS_BRK: c_long = 12;
const SYS_MMAP: c_long = 9;
const SYS_MUNMAP: c_long = 11;
const SYS_MPROTECT: c_long = 10;
const SYS_MREMAP: c_long = 25;
const SYS_EXIT: c_long = 60;
const SYS_EXIT_GROUP: c_long = 231;
const SYS_CLONE: c_long = 56;
const SYS_FORK: c_long = 57;
const SYS_VFORK: c_long = 58;
const SYS_EXECVE: c_long = 59;
const SYS_FUTEX: c_long = 202;

const EINVAL: c_long = 22;
const ENOMEM: c_long = 12;
const ENOSYS: c_long = 38;

const MCEXEC_UP_SYSCALL_THREAD: c_long = 0x30a02924;
const MCEXEC_UP_TERMINATE_THREAD: c_long = 0x30a02925;
const UTI_SZ_SYSCALL_STACK: usize = 16;
const UTI_SYSCALL_PROFILE_SLOTS: usize = 512;
const UTI_DESC_SYSCALL: c_long = 733;
const UTI_DESC_QUERY_SYSCALL: c_long = 888;

type HookFn = unsafe extern "C" fn(
    syscall_number: c_long,
    arg0: c_long,
    arg1: c_long,
    arg2: c_long,
    arg3: c_long,
    arg4: c_long,
    arg5: c_long,
    result: *mut c_long,
) -> c_int;

#[repr(C)]
struct SyscallStruct {
    number: c_int,
    args: [c_ulong; 6],
    ret: c_ulong,
    uti_info: c_ulong,
}

#[repr(C)]
struct UtiDesc {
    lctx: [u8; 4096],
    rctx: [u8; 4096],
    mck_tid: c_int,
    key: c_ulong,
    pid: c_int,
    tid: c_int,
    uti_info: c_ulong,
    fd: c_int,
    syscall_stack: [SyscallStruct; UTI_SZ_SYSCALL_STACK],
    syscall_stack_top: c_int,
    syscalls: [c_long; UTI_SYSCALL_PROFILE_SLOTS],
    syscalls2: [c_long; UTI_SYSCALL_PROFILE_SLOTS],
    start_syscall_intercept: c_int,
}

#[repr(C)]
struct TerminateThreadDesc {
    pid: c_int,
    tid: c_int,
    code: c_long,
    tsk: c_ulong,
}

static mut UTI_DESC: UtiDesc = UtiDesc {
    lctx: [0; 4096],
    rctx: [0; 4096],
    mck_tid: 0,
    key: 0,
    pid: 0,
    tid: 0,
    uti_info: 0,
    fd: 0,
    syscall_stack: [const {
        SyscallStruct {
            number: 0,
            args: [0; 6],
            ret: 0,
            uti_info: 0,
        }
    }; UTI_SZ_SYSCALL_STACK],
    syscall_stack_top: 0,
    syscalls: [0; UTI_SYSCALL_PROFILE_SLOTS],
    syscalls2: [0; UTI_SYSCALL_PROFILE_SLOTS],
    start_syscall_intercept: 0,
};

unsafe extern "C" {
    static mut intercept_hook_point: Option<HookFn>;

    fn uti_syscall0(syscall_number: c_long) -> c_long;
    fn uti_syscall1(syscall_number: c_long, arg0: c_long) -> c_long;
    fn uti_syscall3(syscall_number: c_long, arg0: c_long, arg1: c_long, arg2: c_long) -> c_long;
}

unsafe fn bump_counter(counters: *mut c_long, syscall_number: c_long) {
    if syscall_number >= 0 && syscall_number < UTI_SYSCALL_PROFILE_SLOTS as c_long {
        let counter = unsafe { counters.add(syscall_number as usize) };
        unsafe {
            counter.write(counter.read().wrapping_add(1));
        }
    }
}

unsafe fn store_result(result: *mut c_long, value: c_long) {
    unsafe {
        result.write(value);
    }
}

unsafe fn current_thread_is_mckernel(desc: *mut UtiDesc) -> bool {
    let tid = unsafe { uti_syscall0(SYS_GETTID) as c_int };

    tid == unsafe { (*desc).mck_tid }
}

unsafe fn forward_remote_syscall(
    desc: *mut UtiDesc,
    syscall_number: c_long,
    args: [c_long; 6],
    result: *mut c_long,
) -> c_int {
    let top = ptr::addr_of_mut!((*desc).syscall_stack_top);

    if unsafe { top.read() } == -1 {
        unsafe {
            store_result(result, -ENOMEM);
        }
        return 0;
    }

    let current_top = unsafe { top.read() };
    if !(0..UTI_SZ_SYSCALL_STACK as c_int).contains(&current_top) {
        unsafe {
            store_result(result, -EINVAL);
        }
        return 0;
    }

    let stack_top = unsafe { AtomicI32::from_ptr(top).fetch_sub(1, Ordering::SeqCst) };
    let entry = unsafe { (*desc).syscall_stack.as_mut_ptr().add(stack_top as usize) };

    unsafe {
        (*entry).number = syscall_number as c_int;
        (*entry).args[0] = args[0] as c_ulong;
        (*entry).args[1] = args[1] as c_ulong;
        (*entry).args[2] = args[2] as c_ulong;
        (*entry).args[3] = args[3] as c_ulong;
        (*entry).args[4] = args[4] as c_ulong;
        (*entry).args[5] = args[5] as c_ulong;
        (*entry).uti_info = (*desc).uti_info;
        (*entry).ret = (-EINVAL) as c_ulong;
    }

    let ret = unsafe {
        uti_syscall3(
            SYS_IOCTL,
            (*desc).fd as c_long,
            MCEXEC_UP_SYSCALL_THREAD,
            entry as c_long,
        )
    };
    unsafe {
        store_result(result, if ret < 0 { ret } else { (*entry).ret as c_long });
        AtomicI32::from_ptr(top).fetch_add(1, Ordering::SeqCst);
    }

    0
}

unsafe fn request_remote_thread_exit(desc: *mut UtiDesc, code: c_long) -> c_int {
    let mut term_desc = TerminateThreadDesc {
        pid: unsafe { (*desc).pid },
        tid: unsafe { (*desc).tid },
        code,
        tsk: unsafe { (*desc).key },
    };

    unsafe {
        uti_syscall3(
            SYS_IOCTL,
            (*desc).fd as c_long,
            MCEXEC_UP_TERMINATE_THREAD,
            ptr::addr_of_mut!(term_desc) as c_long,
        );
    }
    1
}

unsafe extern "C" fn hook(
    syscall_number: c_long,
    arg0: c_long,
    arg1: c_long,
    arg2: c_long,
    arg3: c_long,
    arg4: c_long,
    arg5: c_long,
    result: *mut c_long,
) -> c_int {
    let desc = ptr::addr_of_mut!(UTI_DESC);

    if unsafe { (*desc).start_syscall_intercept } == 0 {
        return 1;
    }

    if !unsafe { current_thread_is_mckernel(desc) } {
        unsafe {
            bump_counter((*desc).syscalls2.as_mut_ptr(), syscall_number);
        }
        return 1;
    }

    unsafe {
        bump_counter((*desc).syscalls.as_mut_ptr(), syscall_number);
    }

    match syscall_number {
        SYS_GETTID => unsafe {
            store_result(result, (*desc).mck_tid as c_long);
            0
        },
        SYS_FUTEX | SYS_BRK | SYS_MMAP | SYS_MUNMAP | SYS_MPROTECT | SYS_MREMAP => unsafe {
            forward_remote_syscall(
                desc,
                syscall_number,
                [arg0, arg1, arg2, arg3, arg4, arg5],
                result,
            )
        },
        SYS_EXIT_GROUP => unsafe {
            request_remote_thread_exit(desc, 0x1_0000_0000 | ((arg0 & 255) << 8))
        },
        SYS_EXIT => unsafe { request_remote_thread_exit(desc, (arg0 & 255) << 8) },
        SYS_CLONE | SYS_FORK | SYS_VFORK | SYS_EXECVE => unsafe {
            store_result(result, -ENOSYS);
            0
        },
        UTI_DESC_QUERY_SYSCALL => unsafe {
            store_result(result, desc as c_long);
            0
        },
        _ => 1,
    }
}

unsafe extern "C" fn init() {
    let desc = ptr::addr_of_mut!(UTI_DESC);

    unsafe {
        intercept_hook_point = Some(hook);
        (*desc).syscall_stack_top = UTI_SZ_SYSCALL_STACK as c_int - 1;
        uti_syscall1(UTI_DESC_SYSCALL, desc as c_long);
    }
}

unsafe extern "C" fn fini() {}

#[used]
#[link_section = ".init_array"]
static INIT_ARRAY: unsafe extern "C" fn() = init;

#[used]
#[link_section = ".fini_array"]
static FINI_ARRAY: unsafe extern "C" fn() = fini;
