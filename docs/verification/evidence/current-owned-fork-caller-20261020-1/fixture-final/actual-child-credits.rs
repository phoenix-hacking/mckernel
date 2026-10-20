#![allow(dead_code)]
use std::sync::atomic::{AtomicUsize,Ordering};
mod abi;
mod process_helpers;
mod fork_control_registry;
mod fork_control_guest;
mod x86_cpu_helpers;
static OFFLOAD_CALLS:AtomicUsize=AtomicUsize::new(0);
static DESTRUCTORS:AtomicUsize=AtomicUsize::new(0);
fn unexpected_destructor(){DESTRUCTORS.fetch_add(1,Ordering::SeqCst);panic!("no last parent reference/destructor authorized");}
#[no_mangle]
unsafe extern "C" fn do_syscall(request: *mut abi::SyscallRequest,cpu:abi::CInt)->abi::CLong{
    OFFLOAD_CALLS.fetch_add(1,Ordering::SeqCst);
    fork_control_guest::child_credits::caller_tests::transport(request,cpu)
}
mod cls{
    use std::sync::atomic::{AtomicPtr,Ordering};use crate::abi::CpuLocalVar;
    static CURRENT:AtomicPtr<CpuLocalVar>=AtomicPtr::new(core::ptr::null_mut());
    pub unsafe fn set(pointer:*mut CpuLocalVar){CURRENT.store(pointer,Ordering::SeqCst);}
    pub unsafe fn get_this_cpu_local_var()->*mut CpuLocalVar{CURRENT.load(Ordering::SeqCst)}
}
mod x86_memory_helpers{
    pub unsafe fn virt_to_phys(pointer:*mut core::ffi::c_void)->u64{pointer as u64}
}
mod mem_helpers{
    use std::alloc::{alloc,dealloc,Layout};use std::sync::atomic::{AtomicUsize,Ordering};
    use std::sync::Mutex;
    use core::ffi::c_void;use crate::{abi::SyscallRequest,fork_control_guest::Carrier};
    static FREES:AtomicUsize=AtomicUsize::new(0);
    static FAIL_NEXT:AtomicUsize=AtomicUsize::new(0);
    static LIVE:Mutex<Vec<(usize,usize)>>=Mutex::new(Vec::new());
    pub unsafe fn kmalloc(bytes:i32,_:i32)->*mut c_void{
        let bytes = bytes as usize;
        assert!(bytes == core::mem::size_of::<Carrier>() || bytes == core::mem::size_of::<SyscallRequest>());
        if FAIL_NEXT.compare_exchange(bytes,0,Ordering::SeqCst,Ordering::SeqCst).is_ok() { return core::ptr::null_mut(); }
        let pointer = alloc(Layout::from_size_align(bytes,8).unwrap()).cast::<c_void>();
        if !pointer.is_null() { LIVE.lock().unwrap().push((pointer as usize,bytes)); }
        pointer
    }
    pub unsafe fn kfree(pointer:*mut c_void){
        let mut live = LIVE.lock().unwrap();
        let index = live.iter().position(|(p,_)| *p == pointer as usize).expect("only owned allocation freed");
        let (_,bytes) = live.remove(index);
        FREES.fetch_add(1,Ordering::SeqCst);
        dealloc(pointer.cast(),Layout::from_size_align(bytes,8).unwrap());
    }
    pub fn fail_next(bytes:usize){FAIL_NEXT.store(bytes,Ordering::SeqCst)}
    pub fn frees()->usize{FREES.load(Ordering::SeqCst)}
    pub fn live_request_slots()->usize{
        LIVE.lock().unwrap().iter().filter(|(_,bytes)| *bytes == core::mem::size_of::<SyscallRequest>()).count()
    }
}

use crate::abi::CInt;
const CLONE_PARENT: CInt = 0x00008000;
#[no_mangle]
pub extern "C" fn clone_host_parent_flags_result(clone_flags: CInt, ppid_parent_pid: CInt) -> CInt {
    if (clone_flags & CLONE_PARENT) != 0 && ppid_parent_pid != 1 {
        clone_flags
    } else {
        0
    }
}
