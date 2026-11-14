const UTI_SZ_SYSCALL_STACK: usize = 16;
const UTI_SYSCALL_PROFILE_SLOTS: usize = 512;
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
