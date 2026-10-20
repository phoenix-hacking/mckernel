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
    fork_control_guest::child_credits::offload_tests::transport(request,cpu)
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
    use core::ffi::c_void;use crate::fork_control_guest::Carrier;
    static FREES:AtomicUsize=AtomicUsize::new(0);
    pub unsafe fn kmalloc(bytes:i32,_:i32)->*mut c_void{
        assert_eq!(bytes as usize,core::mem::size_of::<Carrier>());
        alloc(Layout::new::<Carrier>()).cast()
    }
    pub unsafe fn kfree(pointer:*mut c_void){
        FREES.fetch_add(1,Ordering::SeqCst);dealloc(pointer.cast(),Layout::new::<Carrier>());
    }
    pub fn frees()->usize{FREES.load(Ordering::SeqCst)}
}
