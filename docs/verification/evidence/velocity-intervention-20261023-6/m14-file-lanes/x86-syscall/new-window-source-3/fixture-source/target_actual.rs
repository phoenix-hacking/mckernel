// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![allow(dead_code,unused_imports)]
mod abi;
mod string;
mod list_helpers;
mod process_helpers {
    use crate::abi::{CInt,Thread};
    const HASH_SIZE:CInt=73;
    include!("thread_hash.ACTUAL.rs");
    unsafe extern "C" {pub fn hold_thread(thread:*mut Thread)->CInt;}
}
mod lock_helpers {
    use core::ffi::c_void;
    use crate::abi::McsRwlockLock;
    unsafe extern "C" {
        pub fn __mcs_rwlock_reader_lock_noirq(lock:*mut McsRwlockLock,node:*mut c_void);
        pub fn __mcs_rwlock_reader_unlock_noirq(lock:*mut McsRwlockLock,node:*mut c_void);
    }
}
use abi::CInt;
const ESRCH:CInt=3;
const EINVAL:CInt=22;
const PS_EXITED:CInt=0x10;
const PS_ZOMBIE:CInt=8;
const SIGKILL:CInt=9;
unsafe extern "C" {fn kprintf(format:*const i8,...)->CInt;}
include!("do_kill_thread_target.FRAGMENT.rs");
include!("do_kill_prepare_info.FRAGMENT.rs");
#[no_mangle]
pub extern "C" fn fixture_target_abi(i:usize)->usize {
    use core::mem::{size_of,align_of,offset_of};
    use abi::{Thread,ThreadHash,Process,SigInfo,AbiListHead};
    let values=[size_of::<Thread>(),align_of::<Thread>(),size_of::<Process>(),align_of::<Process>(),
        size_of::<ThreadHash>(),offset_of!(ThreadHash,list),offset_of!(ThreadHash,lock),
        size_of::<abi::McsRwlockLock>(),offset_of!(Thread,hash_list),offset_of!(Thread,tid),
        offset_of!(Thread,proc),offset_of!(Thread,status),offset_of!(Thread,sigpendinglock),
        offset_of!(Thread,sigpending),offset_of!(Process,pid),offset_of!(Process,status),
        offset_of!(Process,update_lock),offset_of!(Process,threads_lock),size_of::<SigInfo>(),
        align_of::<SigInfo>(),offset_of!(SigInfo,si_signo),offset_of!(SigInfo,si_code),
        size_of::<AbiListHead>(),abi::PROCESS_HASH_SIZE,0x80];values[i]
}
