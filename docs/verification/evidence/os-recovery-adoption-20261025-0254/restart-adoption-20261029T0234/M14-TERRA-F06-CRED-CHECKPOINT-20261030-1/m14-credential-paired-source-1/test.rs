use core::{ffi::c_void, mem::{offset_of,MaybeUninit}, ptr::{null_mut,write}};
use std::sync::atomic::{AtomicI64, AtomicUsize, Ordering};
type CInt=i32; type CLong=i64; type CULong=u64; type SizeT=usize;
const EFAULT:CInt=14; const EINVAL:CInt=22;
#[repr(C)] struct SyscallRequest { number:u64, args:[u64;6], other:[u64;2] }
type SyscallRequestCallFn=unsafe extern "C" fn(*mut SyscallRequest,CInt)->CLong;
type SyscallVirtToPhysFn=unsafe extern "C" fn(*mut c_void)->CULong;
type SyscallGetcredFn=unsafe extern "C" fn(*mut CInt)->*mut CInt;
type SyscallGetCpuFn=unsafe extern "C" fn()->CInt;
include!("actual-bodies.rs");
#[repr(C)] #[derive(Debug,PartialEq)] struct Proc { r:i32,e:i32,s:i32,fs:i32 }
#[repr(C)] struct Thread { proc:*mut Proc }
static RETURN:AtomicI64=AtomicI64::new(0); static CALLS:AtomicUsize=AtomicUsize::new(0);
unsafe extern "C" fn phys(p:*mut c_void)->u64 { p as u64 }
unsafe extern "C" fn cpu()->i32 { 3 }
unsafe extern "C" fn request(p:*mut SyscallRequest, cpu:i32)->i64 {
 assert_eq!(cpu,3);assert_eq!((*p).number,122);assert_eq!((*p).args[1],1);CALLS.fetch_add(1,Ordering::SeqCst);
 let ret=RETURN.load(Ordering::SeqCst);
 if ret==0 { let buf=(*p).args[0] as *mut i32; for i in 0..8 { buf.add(i).write(10+i as i32); } }
 ret
}
unsafe extern "C" fn getcred(buf:*mut i32)->*mut i32 { getcred_body_result(buf,0,122,Some(phys),Some(cpu),Some(request)) }
fn run(status:i64,idx:usize)->(i32,Proc,usize) {
 RETURN.store(status,Ordering::SeqCst);CALLS.store(0,Ordering::SeqCst);
 let mut scratch=[-1i32;16];let mut p=Proc{r:1,e:2,s:3,fs:4};let mut t=Thread{proc:&mut p};
 let rc=unsafe{syscall_refresh_cred_fields_body_result((&mut t as *mut Thread).cast(),scratch.as_mut_ptr(),offset_of!(Thread,proc),offset_of!(Proc,r),offset_of!(Proc,e),offset_of!(Proc,s),offset_of!(Proc,fs),idx,idx+1,idx+2,idx+3,Some(getcred))};
 (rc,p,CALLS.load(Ordering::SeqCst))
}
#[test] fn successful_uid_values_propagate() { assert_eq!(run(0,0),(0,Proc{r:10,e:11,s:12,fs:13},1)); }
#[test] fn successful_gid_values_propagate() { assert_eq!(run(0,4),(0,Proc{r:14,e:15,s:16,fs:17},1)); }
#[test] fn error_leaves_prior_fields_untouched() { assert_eq!(run(-5,0),(-14,Proc{r:1,e:2,s:3,fs:4},1)); }
#[test] fn positive_nonzero_also_leaves_fields_untouched() { assert_eq!(run(1,4),(-14,Proc{r:1,e:2,s:3,fs:4},1)); }
