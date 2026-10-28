// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
mod f03_util_profile_v1 {
    use core::ptr;
    use crate::abi::{CInt as c_int, CLong as c_long, CULong as c_ulong};

    // Exact existing project Rust ABI declarations, reused without field edits.
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

    /// Print the original two ordered syscall-counter tables.
    ///
    /// # Safety
    /// The original caller supplies a live, aligned, initialized UtiDesc at the
    /// captured uti_desc address for the entire call. It retains the existing
    /// foreign-memory synchronization/lifetime contract. No borrowed whole
    /// descriptor reference is formed and no descriptor byte is written.
    #[no_mangle]
    pub unsafe extern "C" fn util_show_syscall_profile() -> c_int {
        // SAFETY: Same one-time global descriptor capture before the first log.
        let desc = unsafe { super::uti_desc as *const UtiDesc };
        unsafe {
            super::kprintf(b"Syscall stats for offloaded thread:\n\0".as_ptr().cast());
            for i in 0..UTI_SYSCALL_PROFILE_SLOTS {
                let slot = ptr::addr_of!((*desc).syscalls).cast::<c_long>().add(i);
                if ptr::read(slot) != 0 {
                    super::kprintf(b"nr=%d #called=%ld\n\0".as_ptr().cast(), i as c_int, ptr::read(slot));
                }
            }
            super::kprintf(b"Syscall stats for other threads:\n\0".as_ptr().cast());
            for i in 0..UTI_SYSCALL_PROFILE_SLOTS {
                let slot = ptr::addr_of!((*desc).syscalls2).cast::<c_long>().add(i);
                if ptr::read(slot) != 0 {
                    super::kprintf(b"nr=%d #called=%ld\n\0".as_ptr().cast(), i as c_int, ptr::read(slot));
                }
            }
        }
        0
    }

    #[no_mangle]
    pub static F03_UTIL_PROFILE_ABI:[c_ulong;26]=[
        core::mem::size_of::<SyscallStruct>() as _,core::mem::align_of::<SyscallStruct>() as _,
        core::mem::offset_of!(SyscallStruct,number) as _,core::mem::offset_of!(SyscallStruct,args) as _,
        core::mem::offset_of!(SyscallStruct,ret) as _,core::mem::offset_of!(SyscallStruct,uti_info) as _,
        core::mem::size_of::<UtiDesc>() as _,core::mem::align_of::<UtiDesc>() as _,
        core::mem::offset_of!(UtiDesc,lctx) as _,core::mem::offset_of!(UtiDesc,rctx) as _,
        core::mem::offset_of!(UtiDesc,mck_tid) as _,core::mem::offset_of!(UtiDesc,key) as _,
        core::mem::offset_of!(UtiDesc,pid) as _,core::mem::offset_of!(UtiDesc,tid) as _,
        core::mem::offset_of!(UtiDesc,uti_info) as _,core::mem::offset_of!(UtiDesc,fd) as _,
        core::mem::offset_of!(UtiDesc,syscall_stack) as _,core::mem::offset_of!(UtiDesc,syscall_stack_top) as _,
        core::mem::offset_of!(UtiDesc,syscalls) as _,core::mem::offset_of!(UtiDesc,syscalls2) as _,
        core::mem::offset_of!(UtiDesc,start_syscall_intercept) as _,UTI_SZ_SYSCALL_STACK as _,
        UTI_SYSCALL_PROFILE_SLOTS as _,core::mem::size_of::<c_int>() as _,
        core::mem::size_of::<c_long>() as _,core::mem::size_of::<c_ulong>() as _,
    ];
}
