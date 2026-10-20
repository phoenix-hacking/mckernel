#![allow(dead_code,static_mut_refs)]
// Whole production queue/manycore functions and actual ABI/list definitions.
// Only platform IRQ, logging, notification and address translation are adapters.
#[path="abi.rs"] mod abi;
#[path="list_helpers.rs"] mod list_helpers;
#[path="../source/kernel/rust/ikc_queue.rs"] mod ikc_queue;
#[path="../source/kernel/rust/ikc_manycore.rs"] mod ikc_manycore;
use core::{cell::UnsafeCell,ffi::c_void,ptr};
use std::sync::atomic::{AtomicUsize,AtomicBool,Ordering};
static IRQ_SAVE:AtomicUsize=AtomicUsize::new(0);
static IRQ_RESTORE:AtomicUsize=AtomicUsize::new(0);
static IRQ_FLAGS:AtomicUsize=AtomicUsize::new(0);
static NOTIFY:AtomicUsize=AtomicUsize::new(0);
static RELEASE_ON_FULL:AtomicBool=AtomicBool::new(false);
static RELEASE_QUEUE:AtomicUsize=AtomicUsize::new(0);
static FULL_LOGS:AtomicUsize=AtomicUsize::new(0);
#[no_mangle] extern "C" fn cpu_disable_interrupt_save()->u64{IRQ_SAVE.fetch_add(1,Ordering::SeqCst);0x202}
#[no_mangle] extern "C" fn cpu_restore_interrupt(flags:u64){IRQ_FLAGS.store(flags as usize,Ordering::SeqCst);IRQ_RESTORE.fetch_add(1,Ordering::SeqCst);}
#[no_mangle] extern "C" fn ihk_ikc_send_interrupt(_:*mut ikc_queue::IhkIkcChannelDesc)->i32{NOTIFY.fetch_add(1,Ordering::SeqCst);0}
#[no_mangle] extern "C" fn virt_to_phys(p:*mut c_void)->u64{p as u64}
core::arch::global_asm!(".text",".globl kprintf",".type kprintf,@function","kprintf:","jmp fixture_log",".size kprintf,.-kprintf");
#[no_mangle] unsafe extern "C" fn fixture_log(format:*const i8)->i32{
 let format=std::ffi::CStr::from_ptr(format).to_bytes();
 if format.windows(7).any(|s|s==b"is full"){
  FULL_LOGS.fetch_add(1,Ordering::SeqCst);
  if RELEASE_ON_FULL.swap(false,Ordering::SeqCst){
   let q=RELEASE_QUEUE.load(Ordering::SeqCst)as *mut ikc_queue::IhkIkcQueueHead;
   let mut old=[0u64;8];assert_eq!(ikc_queue::ihk_ikc_read_queue(q,old.as_mut_ptr().cast(),0),0);
  }
 }
 0
}
#[repr(C,align(64))] struct Storage([u8;576]);
fn storage()->Storage{Storage([0xa5;576])}
unsafe fn queue(s:&mut Storage,count:i32)->*mut ikc_queue::IhkIkcQueueHead{
 let q=s.0.as_mut_ptr().cast();assert_eq!(ikc_queue::ihk_ikc_init_queue(q,1,0,64+count*64,64),0);q
}
unsafe fn channel(q:*mut ikc_queue::IhkIkcQueueHead)->ikc_queue::IhkIkcChannelDesc{
 let mut c:ikc_queue::IhkIkcChannelDesc=core::mem::zeroed();c.flag=ikc_queue::IKC_FLAG_ENABLED;c.send.queue=q;c
}
fn reset(){IRQ_SAVE.store(0,Ordering::SeqCst);IRQ_RESTORE.store(0,Ordering::SeqCst);IRQ_FLAGS.store(0,Ordering::SeqCst);NOTIFY.store(0,Ordering::SeqCst);FULL_LOGS.store(0,Ordering::SeqCst);RELEASE_ON_FULL.store(false,Ordering::SeqCst);}
fn irq_once(){assert_eq!(IRQ_SAVE.load(Ordering::SeqCst),1);assert_eq!(IRQ_RESTORE.load(Ordering::SeqCst),1);assert_eq!(IRQ_FLAGS.load(Ordering::SeqCst),0x202);}
#[test]fn affected_invalid_geometry_keeps_reservation_and_packet(){unsafe{
 for geometry in 0..5{
  let mut s=storage();let q=queue(&mut s,4);match geometry{0=>(*q).pktsize=0,1=>(*q).pktsize=9,2=>(*q).queue_size-=1,3=>(*q).pktcount=0,_=>{(*q).pktcount=1;(*q).queue_size=64}}
  let before=s.0;let mut packet=[7u64;8];assert_eq!(ikc_queue::ihk_ikc_write_queue(q,packet.as_mut_ptr().cast(),0),-22);assert_eq!(s.0,before);
 }
 // This malformed size can be constructed by the existing exported initializer:
 // producer rejects it rather than publishing a silently truncated memcpyl.
 let mut s=storage();let q=s.0.as_mut_ptr().cast();assert_eq!(ikc_queue::ihk_ikc_init_queue(q,1,0,100,9),0);let before=s.0;let mut packet=[7u64;8];assert_eq!(ikc_queue::ihk_ikc_write_queue(q,packet.as_mut_ptr().cast(),0),-22);assert_eq!(s.0,before);
}}
#[test]fn affected_fatal_send_restores_irq_without_notification(){unsafe{
 for bad in 0..3{
  reset();let mut s=storage();let q=queue(&mut s,4);let mut c=channel(q);match bad{0=>(*q).pktsize=9,1=>c.send.queue=ptr::null_mut(),_=>c.flag=0};let before=s.0;let mut packet=[8u64;8];assert_eq!(ikc_manycore::ihk_ikc_send(&mut c,packet.as_mut_ptr().cast(),0),-22);irq_once();assert_eq!(NOTIFY.load(Ordering::SeqCst),0);assert_eq!(s.0,before);
 }
 reset();let mut packet=[8u64;8];assert_eq!(ikc_manycore::ihk_ikc_send(ptr::null_mut(),packet.as_mut_ptr().cast(),0),-22);assert_eq!(IRQ_SAVE.load(Ordering::SeqCst),0);assert_eq!(IRQ_RESTORE.load(Ordering::SeqCst),0);
}}
#[test]fn affected_full_retry_then_success_and_no_notify(){unsafe{
 reset();let mut s=storage();let q=queue(&mut s,2);let mut old=[1u64;8];assert_eq!(ikc_queue::ihk_ikc_write_queue(q,old.as_mut_ptr().cast(),0),0);let counters=((*q).read_off,(*q).write_off,(*q).max_read_off);assert_eq!(ikc_queue::ihk_ikc_write_queue(q,old.as_mut_ptr().cast(),0),-16);assert_eq!(((*q).read_off,(*q).write_off,(*q).max_read_off),counters);
 RELEASE_QUEUE.store(q as usize,Ordering::SeqCst);RELEASE_ON_FULL.store(true,Ordering::SeqCst);let mut c=channel(q);let mut packet=[2u64;8];assert_eq!(ikc_manycore::ihk_ikc_send(&mut c,packet.as_mut_ptr().cast(),0),0);irq_once();assert_eq!(FULL_LOGS.load(Ordering::SeqCst),2);assert_eq!(NOTIFY.load(Ordering::SeqCst),1);let mut received=[0u64;8];assert_eq!(ikc_queue::ihk_ikc_read_queue(q,received.as_mut_ptr().cast(),0),0);assert_eq!(received,packet);
 reset();assert_eq!(ikc_manycore::ihk_ikc_send(&mut c,packet.as_mut_ptr().cast(),ikc_queue::IKC_NO_NOTIFY),0);irq_once();assert_eq!(NOTIFY.load(Ordering::SeqCst),0);
}}
#[test]fn affected_candidate_slot_wrap_and_complete_copy(){unsafe{
 let mut s=storage();let q=queue(&mut s,3);(*q).read_off=u64::MAX;(*q).write_off=u64::MAX;(*q).max_read_off=u64::MAX;let mut packet=[0x12345678abcdef01u64;8];assert_eq!(ikc_queue::ihk_ikc_write_queue(q,packet.as_mut_ptr().cast(),0),0);assert_eq!((*q).write_off,0);assert_eq!((*q).max_read_off,0);let mut received=[0u64;8];assert_eq!(ikc_queue::ihk_ikc_read_queue(q,received.as_mut_ptr().cast(),0),0);assert_eq!(received,packet);assert_eq!((*q).read_off,0);
}}
#[cfg(native_linux_irq_work_v6_12)]
#[test]fn affected_concurrent_writers_recompute_candidate_after_cas(){
 struct Shared(UnsafeCell<Storage>);unsafe impl Send for Shared{}unsafe impl Sync for Shared{}
 let shared=std::sync::Arc::new(Shared(UnsafeCell::new(storage())));unsafe{queue(&mut*shared.0.get(),8);}
 let barrier=std::sync::Arc::new(std::sync::Barrier::new(3));let mut jobs=Vec::new();
 for writer in 0..2u64{let(shared,barrier)=(shared.clone(),barrier.clone());jobs.push(std::thread::spawn(move||{barrier.wait();let q=shared.0.get().cast::<ikc_queue::IhkIkcQueueHead>();for sequence in 0..128u64{let mut packet=[writer,sequence,3,4,5,6,7,8];loop{let rc=unsafe{ikc_queue::ihk_ikc_write_queue(q,packet.as_mut_ptr().cast(),0)};if rc==0{break;}assert_eq!(rc,-16);std::thread::yield_now();}}}));}
 barrier.wait();let q=shared.0.get().cast::<ikc_queue::IhkIkcQueueHead>();let mut seen=std::collections::HashSet::new();while seen.len()!=256{let mut received=[0u64;8];let rc=unsafe{ikc_queue::ihk_ikc_read_queue(q,received.as_mut_ptr().cast(),0)};if rc==0{assert!(received[0]<2&&received[1]<128);assert_eq!(&received[2..],&[3,4,5,6,7,8]);assert!(seen.insert((received[0],received[1])));}else{assert!(rc==-1||rc==-16);std::thread::yield_now();}}
 for job in jobs{job.join().unwrap();}unsafe{assert_eq!((*q).read_off,256);assert_eq!((*q).max_read_off,256);assert_eq!((*q).write_off,256);}
}
