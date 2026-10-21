// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![allow(dead_code)]
#[path="application_rpc.rs"] mod application_rpc;
#[path="application_syscall.rs"] mod application_syscall;
#[path="smp_application_syscall.rs"] mod mailbox;
extern crate self as kernel;
pub mod prelude {
    pub const GFP_KERNEL: u32 = 0;
    pub struct AllocError;
    pub struct Vec<T>(std::vec::Vec<T>);
    pub trait VecExt<T>: Sized {
        fn with_capacity(n: usize, flags: u32) -> Result<Self, AllocError>;
        fn push(&mut self, value: T, flags: u32) -> Result<(), AllocError>;
    }
    impl<T> VecExt<T> for Vec<T> {
        fn with_capacity(n: usize, _flags: u32) -> Result<Self, AllocError> {
            let mut value = std::vec::Vec::new();
            value.try_reserve(n).map_err(|_| AllocError)?;
            Ok(Self(value))
        }
        fn push(&mut self, value: T, _flags: u32) -> Result<(), AllocError> {
            self.0.try_reserve(1).map_err(|_| AllocError)?;
            self.0.push(value);
            Ok(())
        }
    }
    impl<T> core::ops::Deref for Vec<T> {
        type Target = [T];
        fn deref(&self) -> &[T] {
            &self.0
        }
    }
    impl<T> core::ops::DerefMut for Vec<T> {
        fn deref_mut(&mut self) -> &mut [T] {
            &mut self.0
        }
    }
}

use application_syscall::{Request, ResponseMemory};
#[repr(C,align(8))] struct Storage([u8;40]);
struct Memory { physical:u64, storage:Box<Storage> }
unsafe impl ResponseMemory for Memory {
 fn physical(&self)->u64{self.physical}
 fn address(&mut self)->*mut u8{self.storage.0.as_mut_ptr()}
 unsafe fn release(self){}
}
fn request(number:u64,args:[u64;6])->Request {
 let mut b=[0u8;128]; b[8..12].copy_from_slice(&4i32.to_le_bytes());
 b[32..36].copy_from_slice(&700i32.to_le_bytes());b[48..52].copy_from_slice(&900i32.to_le_bytes());
 b[56..64].copy_from_slice(&1u64.to_le_bytes());b[64..72].copy_from_slice(&number.to_le_bytes());
 for(i,a)in args.iter().enumerate(){b[72+i*8..80+i*8].copy_from_slice(&a.to_le_bytes());}
 b[120..128].copy_from_slice(&0x200000u64.to_le_bytes());Request::decode(&b,1).unwrap()
}
fn delivered(r:Request)->(mailbox::Mailbox<Memory>,u64,u64) {
 let mut q=mailbox::Mailbox::new().unwrap();let w=q.open_worker(900).unwrap();
 q.admit(r,|r|Ok(Memory{physical:r.response(),storage:Box::new(Storage([0;40]))})).unwrap();
 let(s,_) =q.reserve(w).unwrap().unwrap();q.copied(w,s,true).unwrap();(q,w,s)
}
#[test] fn actual_phase1_and_phase2_reject_before_payload_callback(){
 for(phase,args,physical,length,direction)in [
 (1,[1,u64::MAX-99,0x400000,0x300000,0,0],0x300000,832,0),
 (2,[2,0x300000,832,0,0,0],0x300000,832,1)] {
  let r=request(59,args);assert_eq!(r.tid_buffer(),Err(-22));let(mut q,w,s)=delivered(r);
  assert_eq!(q.transfer_tids(w,s,physical,&mut vec![0;length],direction,
    |_,_,_|panic!("exec phase{phase} must not reach existing TID memory writer")),Err(-22));
 }
}
#[test] fn actual_tid_geometry_direction_delivery_and_single_transfer_stay_strict(){
 let r=request(186,[0,0,0,0,2,0x300000]);assert_eq!(r.tid_buffer(),Ok((0x300000,8)));
 let(mut q,w,s)=delivered(r);let mut b=[0;8];
 for(handle,serial,physical,length,direction)in[(w+1,s,0x300000,8,0),(w,s+1,0x300000,8,0),(w,s,0x300004,8,0),(w,s,0x300000,7,0),(w,s,0x300000,8,1)]{
  assert!(q.transfer_tids(handle,serial,physical,&mut b[..length],direction,|_,_,_|panic!("invalid TID transfer")).is_err());
 }
 assert_eq!(q.transfer_tids(w,s,0x300000,&mut b,0,|_,_,_|Ok(())),Ok(()));
 assert_eq!(q.transfer_tids(w,s,0x300000,&mut b,0,|_,_,_|panic!("second transfer")),Err(-16));
}
