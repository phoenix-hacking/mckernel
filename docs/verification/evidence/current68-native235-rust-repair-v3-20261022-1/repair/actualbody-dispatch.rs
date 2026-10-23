#![allow(dead_code,non_upper_case_globals)]
use std::ffi::c_void;use std::sync::atomic::{AtomicI32,Ordering};
#[derive(Clone,Copy)]struct Error(i32);impl Error{fn to_errno(&self)->i32{self.0}}
const EINVAL:Error=Error(-22);type Result<T>=std::result::Result<T,Error>;
mod abi{pub const MCEXEC_UP_CLOSE_EXEC: u32 = 0x30a0_2913;
pub const MCEXEC_UP_CREATE_PPD: u32 = 0x30a0_290e;
pub const MCEXEC_UP_GET_CPU: u32 = 0x30a0_2907;
pub const MCEXEC_UP_GET_CREDV: u32 = 0x30a0_290b;
pub const MCEXEC_UP_GET_NUM_POOL_THREADS: u32 = 0x30a0_2926;
pub const MCEXEC_UP_OPEN_EXEC: u32 = 0x30a0_2912;
pub const MCEXEC_UP_PREPARE_IMAGE: u32 = 0x30a0_2900;
pub const MCEXEC_UP_RELEASE_USER_SPACE: u32 = 0x30a0_2928;
pub const MCEXEC_UP_RET_SYSCALL: u32 = 0x30a0_2904;
pub const MCEXEC_UP_START_IMAGE: u32 = 0x30a0_2902;
pub const MCEXEC_UP_STRNCPY_FROM_USER: u32 = 0x30a0_2908;
pub const MCEXEC_UP_TRANSFER: u32 = 0x30a0_2901;
pub const MCEXEC_UP_WAIT_SYSCALL: u32 = 0x30a0_2903;}
mod service_abi{pub fn topology_query(c:u32)->bool{c==super::abi::MCEXEC_UP_GET_CPU}}
mod mcctrl_exec{use super::*;pub fn credentials(_:usize)->Result<isize>{Ok(0)}pub fn copy_string(_:usize,_:bool)->Result<isize>{Ok(0)}}
struct FileContext{slot:u32,generation:u64,pool:AtomicI32,calls:AtomicI32}
impl FileContext{fn pool_thread_limit(&self)->Result<isize>{self.calls.fetch_add(1,Ordering::SeqCst);let v=self.pool.load(Ordering::SeqCst);if v<0{Err(Error(v))}else{Ok(v as isize)}}
fn open_executable(&self,_:usize)->Result<isize>{Ok(0)}
fn close_executable(&self)->Result<isize>{Ok(0)}
fn create_process(&self,_:usize,_:bool)->Result<isize>{Ok(0)}
fn prepare_image(&self,_:usize,_:bool)->Result<isize>{Ok(0)}
fn start_image(&self,_:usize,_:bool)->Result<isize>{Ok(0)}
fn transfer_image(&self,_:usize,_:bool)->Result<isize>{Ok(0)}
fn wait_syscall(&self,_:usize,_:bool)->Result<isize>{Ok(0)}
fn return_syscall(&self,_:usize,_:bool)->Result<isize>{Ok(0)}
fn clear_user_space(&self,_:usize,_:bool)->Result<isize>{Ok(0)}
}
unsafe fn ihk_os_topology_query_v1(_:u32,_:u64,_:u32)->i64{0}
unsafe extern "C" fn ioctl(context: *mut c_void, command: u32, argument: u64, compat: u32) -> i64 {
    if compat > 1 || (compat == 1 && argument > u32::MAX as u64) {
        return EINVAL.to_errno() as i64;
    }
    // SAFETY: Successful open supplied this object and its interior locks,
    // live until final close and shared safely by concurrent ioctl borrows.
    let context = unsafe { &*context.cast::<FileContext>() };
    let operation = match command {
        abi::MCEXEC_UP_GET_NUM_POOL_THREADS => Some(context.pool_thread_limit()),
        abi::MCEXEC_UP_GET_CREDV => Some(mcctrl_exec::credentials(argument as usize)),
        abi::MCEXEC_UP_STRNCPY_FROM_USER => {
            Some(mcctrl_exec::copy_string(argument as usize, compat == 1))
        }
        abi::MCEXEC_UP_OPEN_EXEC => Some(context.open_executable(argument as usize)),
        abi::MCEXEC_UP_CLOSE_EXEC => Some(context.close_executable()),
        abi::MCEXEC_UP_CREATE_PPD => Some(context.create_process(argument as usize, compat == 1)),
        abi::MCEXEC_UP_PREPARE_IMAGE => Some(context.prepare_image(argument as usize, compat == 1)),
        abi::MCEXEC_UP_START_IMAGE => Some(context.start_image(argument as usize, compat == 1)),
        abi::MCEXEC_UP_TRANSFER => Some(context.transfer_image(argument as usize, compat == 1)),
        abi::MCEXEC_UP_WAIT_SYSCALL => Some(context.wait_syscall(argument as usize, compat == 1)),
        abi::MCEXEC_UP_RET_SYSCALL => Some(context.return_syscall(argument as usize, compat == 1)),
        abi::MCEXEC_UP_RELEASE_USER_SPACE => {
            Some(context.clear_user_space(argument as usize, compat == 1))
        }
        _ => None,
    };
    if let Some(result) = operation {
        return result.map_or_else(|error| error.to_errno() as i64, |value| value as i64);
    }
    if !service_abi::topology_query(command) {
        return EINVAL.to_errno() as i64;
    }
    // SAFETY: The dependency owns the checked scalar query for our lifetime.
    let value = unsafe { ihk_os_topology_query_v1(context.slot, context.generation, command) };
    // Adapt the existing mcctrl_control_get_cpu_body_result check. GET_NODES
    // returns the retained boot node count, matching its existing Rust helper.
    if command == abi::MCEXEC_UP_GET_CPU && value == 0 {
        EINVAL.to_errno() as i64
    } else {
        value
    }
}
fn context(v:i32)->FileContext{FileContext{slot:0,generation:1,pool:AtomicI32::new(v),calls:AtomicI32::new(0)}}
fn call(c:&FileContext,arg:u64,compat:u32)->i64{unsafe{ioctl(c as *const _ as *mut c_void,abi::MCEXEC_UP_GET_NUM_POOL_THREADS,arg,compat)}}
#[test]fn actual_dispatch_preserves_predicate_and_error(){for value in [0,1,-5]{let c=context(value);assert_eq!(call(&c,0,0),value as i64);assert_eq!(c.calls.load(Ordering::SeqCst),1);}}
#[test]fn actual_dispatch_compat_gates_precede_handler(){let c=context(1);assert_eq!(call(&c,0,2),-22);assert_eq!(call(&c,1u64<<32,1),-22);assert_eq!(c.calls.load(Ordering::SeqCst),0);assert_eq!(call(&c,u32::MAX as u64,1),1);}
#[test]fn unknown_command_still_errors(){let c=context(1);assert_eq!(unsafe{ioctl(&c as *const _ as *mut c_void,0xff,0,0)},-22);assert_eq!(c.calls.load(Ordering::SeqCst),0);}
