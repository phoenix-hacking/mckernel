// SPDX-License-Identifier: GPL-2.0
// Focused actual-source failed-invalidation ownership regression.
// Uses the existing allocation-only shim and test ResponseMemory. Linux MM
// invalidation itself is not executed. A later exact successful completion is
// an API check; the current mcctrl WAIT loop does not automatically retry it.
#![allow(dead_code)]
#[path = "../../../host-kernel/native-rust/application_rpc.rs"] mod application_rpc;
#[path = "../../../host-kernel/native-rust/application_syscall.rs"] mod syscall;
use syscall as application_syscall;
#[path = "../../../host-kernel/native-rust/smp_application_syscall.rs"] mod mailbox;
#[path = "../../../host-kernel/native-rust/application_pager.rs"] mod pager;
use core::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use syscall::Request;
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

#[repr(C, align(8))]
struct Buffer([u8; 64]);

impl Buffer {
    fn new(state: u64) -> Self {
        let mut buffer = Self([0xa5; 64]);
        buffer.0[8..16].fill(0);
        buffer.0[16..24].copy_from_slice(&state.to_le_bytes());
        buffer
    }
}


struct TestRam {
    bytes: core::cell::UnsafeCell<Buffer>,
    physical: u64,
    claimed: core::sync::atomic::AtomicBool,
    releases: core::sync::atomic::AtomicUsize,
}
// SAFETY: The exclusive TestMemory claim serializes host writes. Concurrent
// peer operations use only aligned atomics; full snapshots follow joined work.
unsafe impl Sync for TestRam {}
impl TestRam {
    fn new(physical: u64, state: u64) -> Arc<Self> {
        Arc::new(Self {
            bytes: core::cell::UnsafeCell::new(Buffer::new(state)),
            physical,
            claimed: core::sync::atomic::AtomicBool::new(false),
            releases: core::sync::atomic::AtomicUsize::new(0),
        })
    }
    fn claim(self: &Arc<Self>) -> Result<TestMemory, i32> {
        self.claimed
            .compare_exchange(false, true, Ordering::AcqRel, Ordering::Acquire)
            .map_err(|_| -16)?;
        Ok(TestMemory {
            ram: self.clone(),
            released: false,
        })
    }
    fn snapshot(&self) -> [u8; 64] {
        unsafe { (*self.bytes.get()).0 }
    }
    fn status(&self) -> u64 {
        unsafe { AtomicU64::from_ptr(self.bytes.get().cast::<u8>().add(8).cast()) }
            .load(Ordering::Acquire)
    }
}
struct TestMemory {
    ram: Arc<TestRam>,
    released: bool,
}
// SAFETY: Construction checks the exclusive claim. Arc owns the aligned RAM;
// unfinished destruction deliberately retains it as a quarantined test owner.
unsafe impl syscall::ResponseMemory for TestMemory {
    fn physical(&self) -> u64 {
        self.ram.physical
    }
    fn address(&mut self) -> *mut u8 {
        self.ram.bytes.get().cast()
    }
    unsafe fn release(mut self) {
        assert!(self.ram.claimed.swap(false, Ordering::AcqRel));
        self.ram.releases.fetch_add(1, Ordering::AcqRel);
        self.released = true;
    }
}
impl Drop for TestMemory {
    fn drop(&mut self) {
        if !self.released {
            // The synthetic peer supplied no retirement proof. Keep its RAM,
            // matching the native started owner's quarantine contract.
            std::mem::forget(self.ram.clone());
        }
    }
}

fn admit(queue: &mut mailbox::Mailbox<TestMemory>, request: Request, state: u64) -> Arc<TestRam> {
    let memory = TestRam::new(request.response(), state);
    assert_eq!(queue.admit(request, |_| memory.claim()), Ok(true));
    memory
}


fn invalidation_request(start: u64, length: u64) -> Request {
 let mut packet=[0u8;128];
 packet[8..12].copy_from_slice(&4i32.to_le_bytes());
 packet[24..28].copy_from_slice(&1i32.to_le_bytes());
 packet[32..36].copy_from_slice(&321i32.to_le_bytes());
 packet[48..52].copy_from_slice(&700i32.to_le_bytes());
 packet[56..64].copy_from_slice(&1u64.to_le_bytes());
 packet[64..72].copy_from_slice(&11u64.to_le_bytes());
 packet[72..80].copy_from_slice(&start.to_le_bytes());
 packet[80..88].copy_from_slice(&length.to_le_bytes());
 packet[120..128].copy_from_slice(&0x800000u64.to_le_bytes());
 let request=Request::decode(&packet,4).unwrap();
 assert_eq!(request.invalidation_range(),Ok((start,start+length)));
 request
}
fn reserved() -> (mailbox::Mailbox<TestMemory>,u64,u64,i32,Arc<TestRam>) {
 let mut queue=mailbox::Mailbox::new().unwrap();let worker=queue.open_worker(900).unwrap();
 let request=invalidation_request(0x400000,4096);let cpu=request.cpu();let ram=admit(&mut queue,request,2);
 let (serial,_)=queue.reserve(worker).unwrap().unwrap();queue.begin_invalidation(worker,serial).unwrap();
 (queue,worker,serial,cpu,ram)
}
fn held(queue:&mailbox::Mailbox<TestMemory>,ram:&TestRam) {
 assert_eq!(ram.status(),0);assert!(ram.claimed.load(Ordering::Acquire));assert_eq!(ram.releases.load(Ordering::Acquire),0);assert!(!queue.drained());
}


#[test]
fn failed_mm_error_retains_response_and_allows_exact_success_retry() {
 let (mut queue,worker,serial,cpu,ram)=reserved();
 let outcome=queue.finish_invalidation(worker,serial,-14);
 let published=queue.publish(cpu,|_|Ok(()));
 assert_eq!((outcome,published,ram.status(),ram.releases.load(Ordering::Acquire),ram.claimed.load(Ordering::Acquire)),(Err(-14),Ok(false),0,0,true),"failed MM invalidation must retain exact response owner");
 assert_eq!(queue.close_worker(worker),Err(-16));held(&queue,&ram);
 assert_eq!(queue.finish_invalidation(worker,serial,0),Ok(-512));
 queue.publish(cpu,|_|Ok(())).unwrap();assert_eq!(ram.releases.load(Ordering::Acquire),1);
}
#[test]
fn every_valid_negative_mm_errno_retains_until_proven_success() {
 for value in [-1,-14,-22,-18,-4095] {
  let (mut queue,worker,serial,cpu,ram)=reserved();
  assert_eq!(queue.finish_invalidation(worker,serial,value),Err(value as i32));
  assert_eq!(queue.publish(cpu,|_|panic!("failed clear response publication")),Ok(false));held(&queue,&ram);
  assert!(queue.open_worker(900).is_err());assert_eq!(queue.reserve(worker),Err(-16));
  assert_eq!(queue.finish_invalidation(worker,serial,0),Ok(0));queue.publish(cpu,|_|Ok(())).unwrap();
  assert_eq!(ram.status(),1);assert_eq!(ram.releases.load(Ordering::Acquire),1);assert!(!ram.claimed.load(Ordering::Acquire));
 }
}
#[test]
fn close_and_worker_cancellation_cannot_release_failed_clear() {
 for process_close in [false,true] {
  let (mut queue,worker,serial,cpu,ram)=reserved();
  if process_close {queue.close().unwrap();}else{assert_eq!(queue.close_worker(worker),Err(-16));}
  assert_eq!(queue.finish_invalidation(worker,serial,-22),Err(-22));
  assert_eq!(queue.publish(cpu,|_|panic!("cancellation before clear")),Ok(false));held(&queue,&ram);
  assert_eq!(queue.close_worker(worker),Err(-16));
  assert_eq!(queue.finish_invalidation(worker,serial,0),Ok(-512));queue.publish(cpu,|_|Ok(())).unwrap();
  assert_eq!(i64::from_le_bytes(ram.snapshot()[24..32].try_into().unwrap()),-512);
  queue.close_worker(worker).unwrap();assert!(queue.drained());assert_eq!(ram.releases.load(Ordering::Acquire),1);
 }
}
#[test]
fn wrong_worker_serial_and_invalid_result_preserve_valid_retry() {
 let (mut queue,worker,serial,cpu,ram)=reserved();let wrong=queue.open_worker(901).unwrap();
 for value in [0,-14] {assert_eq!(queue.finish_invalidation(wrong,serial,value),Err(-16));assert_eq!(queue.finish_invalidation(worker,serial+1,value),Err(-2));held(&queue,&ram);}
 for value in [1,i64::MAX,-4096,i64::MIN] {assert_eq!(queue.finish_invalidation(worker,serial,value),Err(-22));held(&queue,&ram);}
 assert!(!queue.quarantined());assert_eq!(queue.finish_invalidation(worker,serial,0),Ok(0));queue.publish(cpu,|_|Ok(())).unwrap();assert_eq!(ram.releases.load(Ordering::Acquire),1);
}
#[test]
fn repeated_error_and_finish_never_duplicate_completion_or_release() {
 let (mut queue,worker,serial,cpu,ram)=reserved();
 for _ in 0..3 {assert_eq!(queue.finish_invalidation(worker,serial,-18),Err(-18));assert_eq!(queue.publish(cpu,|_|panic!("unexpected error completion")),Ok(false));held(&queue,&ram);}
 assert_eq!(queue.finish_invalidation(worker,serial,0),Ok(0));assert_eq!(queue.finish_invalidation(worker,serial,0),Err(-16));
 queue.publish(cpu,|_|Ok(())).unwrap();assert_eq!(queue.finish_invalidation(worker,serial,0),Err(-2));assert_eq!(queue.publish(cpu,|_|panic!("duplicate completion")),Ok(false));assert_eq!(ram.releases.load(Ordering::Acquire),1);
}
#[test]
fn normal_success_keeps_publication_retry_and_exact_one_release() {
 let (mut queue,worker,serial,cpu,ram)=reserved();assert_eq!(queue.finish_invalidation(worker,serial,0),Ok(0));
 for _ in 0..3 {assert_eq!(queue.publish(cpu,|_|Err(-11)),Err(-11));held(&queue,&ram);}
 queue.publish(cpu,|_|Ok(())).unwrap();assert_eq!(ram.status(),1);assert_eq!(ram.releases.load(Ordering::Acquire),1);assert_eq!(queue.returned(worker,serial),Ok(true));assert!(queue.drained());
}
