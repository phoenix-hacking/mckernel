#![allow(dead_code,unused_imports)]
#[path="/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1/f06-debug-constants-align32-host-1/src/kernel/rust/abi.rs"] mod abi;
use core::ffi::c_void;use core::mem::{size_of,MaybeUninit};use core::ptr::{write,write_volatile};use abi::{CInt,CULong,IkcScdPacket};
const EINVAL:CInt=22;type SyscallIkcSendFn=unsafe extern "C" fn(*mut c_void,*mut c_void,CInt)->CInt;
static mut PACKET:[u8;128]=[0;128]; static mut CPU:i32=-1; static mut CHANNEL:usize=0;static mut OPT:i32=-1;static mut RET:i32=0;static mut CALLS:i32=0;
mod cls { use core::ffi::c_void; #[repr(C)] pub struct FakeCpu {pub ikc2linux:*mut c_void} static mut CPU0:FakeCpu=FakeCpu{ikc2linux:0x1234usize as *mut c_void};pub unsafe fn get_cpu_local_var(n:i32)->*mut FakeCpu{crate::CPU=n; core::ptr::addr_of_mut!(CPU0)} }
mod ikc_manycore {use core::ffi::c_void;pub unsafe fn ihk_ikc_send(c:*mut c_void,p:*mut c_void,o:i32)->i32 {crate::CHANNEL=c as usize;crate::OPT=o;crate::CALLS+=1;core::ptr::copy_nonoverlapping(p.cast::<u8>(),core::ptr::addr_of_mut!(crate::PACKET).cast::<u8>(),128);crate::RET}}
include!("actual_bodies.rs");
fn main(){assert_eq!(size_of::<IkcScdPacket>(),128);assert_eq!(unsafe{syscall_eventfd_packet_prepare_result(core::ptr::null_mut(),1,2)},-22);assert_eq!(unsafe{syscall_eventfd_send_result(core::ptr::null_mut(),1,2,None)},-22);for val in [0, -7, i32::MAX] {for ret in [0,-11,5] {unsafe {RET=ret;CPU=-1;CALLS=0;CHANNEL=0;OPT=-1;eventfd(val);print!("{} {} {} {} {} {} ",val,ret,CPU,CHANNEL,OPT,CALLS);for x in PACKET {print!("{:02x}",x)}println!();}}}}
