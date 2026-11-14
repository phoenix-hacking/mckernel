// Production methods and Slot destruction execute with std synchronization.
// PeerStopped is a scoped test adapter; production proof construction is covered
// by native_shutdown_epoch_source tests. No hardware or Linux removal occurs.
#![allow(dead_code)]
pub(crate) mod sysfs_remote {
    // Frozen test boundary: a live non-clone borrow; no unscoped generation token
    // is accepted by the helper under test.
    pub(crate) struct PeerStopped<'a>{owner:&'a u64}
    impl PeerStopped<'_>{pub(crate) fn matches_owner(&self,owner:u64)->bool{*self.owner==owner}}
    pub(crate) fn scoped(owner:&u64,run:impl FnOnce(&PeerStopped<'_>)){run(&PeerStopped{owner})}
}
mod fixture {
use crate::sysfs_remote;
use std::{ffi::CStr, sync::{Arc, atomic::{AtomicBool, AtomicU64, Ordering}}};
trait KernelCStr {fn as_bytes_with_nul(&self)->&[u8];}
impl KernelCStr for CStr {fn as_bytes_with_nul(&self)->&[u8]{self.to_bytes_with_nul()}}
type Result<T = ()> = std::result::Result<T, i32>;
const EBUSY:i32=-16;const EINVAL:i32=-22;const ENODEV:i32=-19;const EAGAIN:i32=-11;
const GFP_KERNEL:()=();const REQUEST_BYTES:usize=808;const CHAIN_PAGES:usize=1024;const PA_NULL:u64=u64::MAX;
struct Mutex<T>(std::sync::Mutex<T>);
impl<T> Mutex<T> {fn new(v:T)->Self {Self(std::sync::Mutex::new(v))}fn lock(&self)->std::sync::MutexGuard<'_,T>{self.0.lock().unwrap()}}
#[derive(Debug,PartialEq,Eq)]struct Vec<T>(std::vec::Vec<T>);
impl<T> Vec<T> {fn with_capacity(n:usize,_flags:())->Result<Self>{Ok(Self(std::vec::Vec::with_capacity(n)))}}
impl<T> From<std::vec::Vec<T>> for Vec<T>{fn from(v:std::vec::Vec<T>)->Self{Self(v)}}
impl<T> std::ops::Deref for Vec<T>{type Target=std::vec::Vec<T>;fn deref(&self)->&Self::Target{&self.0}}
impl<T> std::ops::DerefMut for Vec<T>{fn deref_mut(&mut self)->&mut Self::Target{&mut self.0}}
#[derive(Clone,Copy,Debug,PartialEq,Eq)]struct Span(u64);
#[derive(Clone,Copy,Debug,PartialEq,Eq)]struct Tagged{span:Span,serial:u64}
// PRODUCTION_LEDGER
struct Memory{owner:u64,direct_map:u64,ledger:Mutex<Ledger>}
impl Memory{// PRODUCTION_MEMORY_CHECK
}
struct Registry{entries:Mutex<Vec<Option<Arc<()>>>>}
impl Registry{// PRODUCTION_PAGER_CHECK
}

static ALLOC_HOOK:std::sync::Mutex<Option<Arc<std::sync::Barrier>>>=std::sync::Mutex::new(None);
struct BootPages;
impl BootPages{fn allocate(_n:usize,_direct_map:u64)->Result<Self>{
    let hook=ALLOC_HOOK.lock().unwrap().take();
    if let Some(hook)=hook{hook.wait();hook.wait();}Ok(Self)
}}
#[derive(Clone,Copy,PartialEq,Eq)]struct Token(u64);
impl Token{fn allocate()->Result<Self>{static NEXT:AtomicU64=AtomicU64::new(1);Ok(Self(NEXT.fetch_add(1,Ordering::Relaxed)))}}
fn errno(value:i32)->i32{value}
fn bytes(n:usize)->Result<Vec<u8>>{Ok(vec![0;n].into())}
struct ProcfsRegion;
struct Exchange{pending:bool}
impl Exchange{fn result(&self)->Option<()>{if self.pending{None}else{Some(())}}fn queued(&self)->bool{false}}
#[derive(Clone,Copy)]enum Operation{Snapshot,Direct,Release}
// PRODUCTION_CONTEXT
// PRODUCTION_SLOT
// PRODUCTION_SLOT_DROP
mod procfs {
    use super::*;
    pub(super) struct Remote{pub(super) memory:Arc<Memory>,pub(super) active:AtomicBool,pub(super) slots:Mutex<Vec<Option<Slot>>>}
    pub(super) struct Session{remote:Arc<Remote>,key:Token,direct:bool}
    impl Remote{
        // PRODUCTION_REMOTE_CHECK
        // PRODUCTION_REMOTE_OPEN
    }
    struct Published{owner:Arc<()>}
    struct Service{processes:Vec<Published>}
    impl Service{// PRODUCTION_SERVICE_CHECK
    }
    fn context()->Arc<Context>{Arc::new(Context{key:Token(44),pid:1,cpu:0,live:AtomicBool::new(true)})}
    fn remote()->Arc<Remote>{Arc::new(Remote{memory:memory(),active:AtomicBool::new(true),slots:Mutex::new(vec![None,None].into())})}
    fn path()->&'static CStr{c"status"}
    #[test]fn empty_procfs_closes_and_all_future_opens_fail(){
        let r=remote();sysfs_remote::scoped(&7,|p|assert_eq!(r.close_if_quiescent(p),Ok(())));
        assert!(!r.active.load(Ordering::Acquire));assert!(matches!(r.open(&context(),path(),false),Err(ENODEV)));
        assert!(r.slots.lock().iter().all(Option::is_none));
    }
    #[test]fn any_slot_including_closed_quarantined_pending_remains_owned(){
        for mode in 0..4{
            let r=remote();let context=context();let owner=Arc::downgrade(&context);
            let session=r.open(&context,path(),false).unwrap();
            let key=session.key;
            {let mut slots=r.slots.lock();let slot=slots[0].as_mut().unwrap();
             if mode==1{slot.closed=true;}if mode==2{slot.quarantined=true;}
             if mode==3{slot.exchange=Some(Exchange{pending:true});}}
            let count=Arc::strong_count(&context);
            sysfs_remote::scoped(&7,|p|assert_eq!(r.close_if_quiescent(p),Err(EBUSY)));
            assert!(!r.active.load(Ordering::Acquire));assert_eq!(Arc::strong_count(&context),count);
            let slots=r.slots.lock();let slot=slots[0].as_ref().unwrap();assert!(slot.key==key);
            assert_eq!(slot.closed,mode==1);assert_eq!(slot.quarantined,mode==2);
            assert_eq!(slot.exchange.is_some(),mode==3);assert!(owner.upgrade().is_some());
        }
    }
    #[test]fn invalid_proof_preserves_admission_and_retained_slots(){
        for busy in [false,true]{let r=remote();let _session=busy.then(||r.open(&context(),path(),false).unwrap());
            sysfs_remote::scoped(&8,|p|assert_eq!(r.close_if_quiescent(p),Err(EINVAL)));
            assert!(r.active.load(Ordering::Acquire));assert_eq!(r.slots.lock().iter().filter(|s|s.is_some()).count(),usize::from(busy));}
    }
    #[test]fn open_that_passed_early_check_cannot_publish_after_close(){
        let r=remote();let barrier=Arc::new(std::sync::Barrier::new(2));
        *ALLOC_HOOK.lock().unwrap()=Some(barrier.clone());let other=r.clone();
        let opening=std::thread::spawn(move||other.open(&context(),path(),false));
        barrier.wait();sysfs_remote::scoped(&7,|p|assert_eq!(r.close_if_quiescent(p),Ok(())));
        barrier.wait();assert!(matches!(opening.join().unwrap(),Err(ENODEV)));
        assert!(r.slots.lock().iter().all(Option::is_none));
    }
    #[test]fn published_process_negative_preserves_owner(){
        let owner=Arc::new(());let mut s=Service{processes:vec![Published{owner:owner.clone()}].into()};
        assert_eq!(s.shutdown_quiescent(),Err(EBUSY));assert_eq!(Arc::strong_count(&owner),2);assert_eq!(s.processes.len(),1);
        s.processes.clear();assert_eq!(s.shutdown_quiescent(),Ok(()));
    }
}
fn memory()->Arc<Memory>{Arc::new(Memory{owner:7,direct_map:0,ledger:Mutex::new(Ledger{
 fixed:vec![Span(100)].into(),requests:vec![None,None].into(),responses:vec![None,None].into(),payloads:vec![None,None].into(),
 snoops:vec![].into(),procfs:vec![].into(),zeroing:vec![].into(),serial:99})})}
#[test]fn memory_requires_each_transient_empty_including_quarantined_tags(){
    let tag=Tagged{span:Span(200),serial:88};
    for field in 0..6{let m=memory();{
        let mut l=m.ledger.lock();match field{0=>l.requests[1]=Some(tag),1=>l.responses[1]=Some(tag),2=>l.payloads[1]=Some(tag),3=>l.snoops.push(tag),4=>l.procfs.push(tag),_=>l.zeroing.push(tag)}}
        assert_eq!(m.shutdown_quiescent(),Err(EBUSY));let l=m.ledger.lock();
        assert_eq!(l.fixed.as_slice(),&[Span(100)]);assert_eq!(l.serial,99);
        let retained=match field{0=>l.requests[1],1=>l.responses[1],2=>l.payloads[1],3=>l.snoops.first().copied(),4=>l.procfs.first().copied(),_=>l.zeroing.first().copied()};assert_eq!(retained,Some(tag));
    }
    let m=memory();assert_eq!(m.shutdown_quiescent(),Ok(()));assert_eq!(m.ledger.lock().fixed.as_slice(),&[Span(100)]);
}
#[test]fn pager_busy_preserves_exact_file_owner(){
    let file=Arc::new(());let r=Registry{entries:Mutex::new(vec![None,Some(file.clone())].into())};
    assert_eq!(r.shutdown_quiescent(),Err(EBUSY));assert_eq!(Arc::strong_count(&file),2);
    assert!(Arc::ptr_eq(r.entries.lock()[1].as_ref().unwrap(),&file));
    r.entries.lock()[1]=None;assert_eq!(r.shutdown_quiescent(),Ok(()));
}

}
