from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,'/home/holden/mckernel')
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item
Q=Path(__file__).resolve().parent;S=(Q/'smp_application.rs').read_text();BASE=(Q/'base-smp_application.rs').read_text()
def item(n):return balanced_item(S,n)
rpc=Path('/home/holden/mckernel/host-kernel/native-rust/application_rpc.rs');(Q/'application_rpc.rs').write_bytes(rpc.read_bytes())
owner=Path('/home/holden/mckernel/host-kernel/native-rust/smp_resource.rs').read_text()
os_token=balanced_item(owner,'pub(crate) struct OsToken {')
getters=balanced_item(owner,'pub(crate) const fn slot(self)')+balanced_item(owner,'pub(crate) const fn generation(self)')
pre=r'''#![allow(dead_code)]
use std::sync::{Arc,atomic::{AtomicBool,AtomicI32,AtomicUsize,Ordering}};
use std::marker::PhantomData;
type Error=i32;type Result<T=()>=std::result::Result<T,i32>;
const EIO:i32=-5;const ENODEV:i32=-19;const EACCES:i32=-13;const ENOENT:i32=-2;const EBUSY:i32=-16;const EINVAL:i32=-22;const EAGAIN:i32=-11;const EINTR:i32=-4;
mod kernel{pub mod error{pub fn to_result(v:i32)->std::result::Result<i32,i32>{if v<0{Err(v)}else{Ok(v)}}}}
macro_rules! pr_info{($($v:tt)*)=>{()}}
struct Mutex<T>(std::sync::Mutex<T>);impl<T> Mutex<T>{fn new(v:T)->Self{Self(std::sync::Mutex::new(v))}fn lock(&self)->std::sync::MutexGuard<'_,T>{self.0.lock().unwrap()}}
#[derive(Default)]struct CondVar;impl CondVar{fn notify_all(&self){}}
mod bindings{use super::*;pub static SLEEPS:AtomicUsize=AtomicUsize::new(0);pub unsafe fn msleep(_:u32){SLEEPS.fetch_add(1,Ordering::SeqCst);}pub unsafe fn ktime_get_seconds()->i64{0}}
struct SyscallResponse;
// Existing actual-body boundary: syscall/procfs/prepared-image services are
// adapters. The exact current Exchange, Entry, counter and close/removal bodies
// below are compiled unchanged. No service/guest/kernel-runtime proof is claimed.
struct Mailbox<T>{drained:bool,closed:bool,_kind:PhantomData<T>}
impl<T> Mailbox<T>{fn new()->Result<Self>{Ok(Self{drained:true,closed:false,_kind:PhantomData})}fn drained(&self)->bool{self.drained}fn close(&mut self)->Result{self.closed=true;Ok(())}}
struct ProcfsProcess;impl ProcfsProcess{fn close(&self){}fn drained(&self)->bool{true}fn threads_retired(&self)->bool{true}}
struct Input{cpu:i32,pid:i32}struct Preparation{exchange:Exchange,input:Input,thread:u64}
impl Preparation{fn result(&self)->Option<i32>{self.exchange.result()}fn finish(&mut self,_:&mut impl FnMut(u64,usize)->Result)->Result{Ok(())}}
'''
pre+='#[path="'+str(Q/'application_rpc.rs')+'"] mod application_rpc;\nuse application_rpc::{Exchange,Token};\n#[derive(Clone,Copy,Debug,Eq,PartialEq)]\n'+os_token+'\nimpl OsToken{'+getters+'}\n'
# Select actual current bodies, preserving their visibility/module nesting.
actual='mod actual{use super::*;\n'+item('struct Entry {')+'\n'+item('impl Entry {')+'\n'+item('pub(crate) struct ParentSlotPin {')+'\n'+item('impl ParentSlotPin {')+'\n'
actual+='pub(crate) struct Remote{owner:OsToken,slots:Mutex<Vec<Option<Entry>>>,changed:CondVar,transport_error:AtomicI32,shutdown_closed:AtomicBool}\nimpl Remote{'
for n in ['pub(crate) fn pin_parent_slot(','pub(crate) fn reserve(','fn transport_health(','pub(crate) fn reply(','fn close_inner(','pub(crate) fn close(&self, token: Token)','pub(crate) fn cleanup(']:actual+=item(n)+'\n'
actual+='}\n'
tests=r'''
fn owner(generation:u64)->OsToken{OsToken{slot:0,generation}}
fn remote()->Arc<Remote>{Arc::new(Remote{owner:owner(2),slots:Mutex::new((0..4).map(|_|None).collect()),changed:CondVar,transport_error:AtomicI32::new(0),shutdown_closed:AtomicBool::new(false)})}
fn count(r:&Remote,t:Token)->usize{r.slots.lock().iter().flatten().find(|e|e.key()==t).unwrap().parent_slot_pins}
fn packet(r:&Remote,t:Token)->[u8;128]{let mut slots=r.slots.lock();let e=slots.iter_mut().flatten().find(|e|e.key()==t).unwrap();let mut p=e.cleanup.outgoing().unwrap();e.cleanup.published().unwrap();p[8..12].copy_from_slice(&application_rpc::CLEANUP_REPLY.to_le_bytes());p}
fn queue(r:&Remote,t:Token){let mut slots=r.slots.lock();let e=slots.iter_mut().flatten().find(|e|e.key()==t).unwrap();e.request_cleanup().unwrap();}
#[test]fn current_pin_exact_identity_admission_overflow_and_no_effects(){
 let r=remote();let t=r.reserve(101).unwrap();let before=Arc::strong_count(&r);
 assert!(matches!(r.pin_parent_slot(owner(3),t),Err(EACCES)));
 assert!(matches!(r.pin_parent_slot(OsToken{slot:1,generation:2},t),Err(EACCES)));
 assert!(matches!(r.pin_parent_slot(owner(2),Token::allocate().unwrap()),Err(ENOENT)));
 assert_eq!(count(&r,t),0);assert_eq!(Arc::strong_count(&r),before);
 r.slots.lock()[0].as_mut().unwrap().owner_slot=1;assert!(matches!(r.pin_parent_slot(owner(2),t),Err(EACCES)));assert_eq!(count(&r,t),0);r.slots.lock()[0].as_mut().unwrap().owner_slot=0;
 r.slots.lock()[0].as_mut().unwrap().parent_slot_pins=usize::MAX;
 assert!(matches!(r.pin_parent_slot(owner(2),t),Err(-75)));assert_eq!(count(&r,t),usize::MAX);assert_eq!(Arc::strong_count(&r),before);
 for kind in 0..5{let r=remote();let t=r.reserve(100+kind).unwrap();match kind{0=>r.transport_error.store(-5,Ordering::Release),1=>r.shutdown_closed.store(true,Ordering::Release),2=>r.slots.lock()[0].as_mut().unwrap().closed=true,3=>r.slots.lock()[0].as_mut().unwrap().needs_cleanup=true,_=>r.slots.lock()[0].as_mut().unwrap().quarantined=true};assert!(r.pin_parent_slot(owner(2),t).is_err());assert_eq!(count(&r,t),0);assert_eq!(Arc::strong_count(&r),1);}
}
#[test]fn current_actual_close_reserved_removal_is_blocked_only_by_owned_slot_pin(){
 let r=remote();let t=r.reserve(101).unwrap();r.close(t);assert!(r.slots.lock().iter().all(Option::is_none));
 let r=remote();let t=r.reserve(102).unwrap();let pin=r.pin_parent_slot(owner(2),t).unwrap();assert!(pin.matches(&r,owner(2),t));assert!(!pin.matches(&r,owner(3),t));assert!(!pin.matches(&remote(),owner(2),t));assert_eq!(count(&r,t),1);
 {let slots=r.slots.lock();drop(pin);assert_eq!(slots[0].as_ref().unwrap().parent_slot_pins,1);}
 r.close(t);let slots=r.slots.lock();let e=slots[0].as_ref().unwrap();assert!(e.closed&&e.needs_cleanup);assert_eq!(e.parent_slot_pins,1);assert!(!e.release_ready());drop(slots);assert!(matches!(r.pin_parent_slot(owner(2),t),Err(EBUSY)));
 let weak=Arc::downgrade(&r);drop(r);let retained=weak.upgrade().expect("discarded pin released Remote storage");assert_eq!(retained.slots.lock()[0].as_ref().unwrap().parent_slot_pins,1);assert_eq!(Arc::strong_count(&retained),2);
}
#[test]fn current_actual_reply_and_final_cleanup_keep_pinned_slot_and_reap_unpinned_slot(){
 let r=remote();let t=r.reserve(101).unwrap();queue(&r,t);let p=packet(&r,t);assert_eq!(r.reply(&p,|_,_|Ok(())),Ok(()));assert!(r.slots.lock()[0].as_ref().unwrap().release_ready());assert_eq!(r.cleanup(t),Ok(()));assert!(r.slots.lock().iter().all(Option::is_none));
 let r=remote();let t=r.reserve(102).unwrap();let pin=r.pin_parent_slot(owner(2),t).unwrap();queue(&r,t);r.slots.lock()[0].as_mut().unwrap().closed=true;r.slots.lock()[0].as_mut().unwrap().cleanup.abandon();let p=packet(&r,t);assert_eq!(r.reply(&p,|_,_|Ok(())),Ok(()));assert_eq!(count(&r,t),1);assert!(!r.slots.lock()[0].as_ref().unwrap().release_ready());let before=bindings::SLEEPS.load(Ordering::SeqCst);assert_eq!(r.cleanup(t),Err(-110));assert_eq!(bindings::SLEEPS.load(Ordering::SeqCst)-before,500);assert_eq!(count(&r,t),1);drop(pin);
}
'''
actual+=tests+'\n}\n'
(Q/'actual-current-parent-pin.rs').write_text(pre+item('fn errno(')+'\n'+actual)
# Every production pin/close/removal body is exact; scaffolding declarations are
# explicit adapters and are not claimed as Linux task/MM/refcount authority.
rows=[]
for p in [Q/'base-smp_application.rs',Q/'smp_application.rs',Q/'application_rpc.rs',Q/'actual-current-parent-pin.rs',Q/'prepare_current_fixture.py']:
 rows.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
(Q/'fixture-inputs.json').write_text(json.dumps({'rows':rows,'actual_methods':['Entry::release_ready','Entry::request_cleanup','Remote::pin_parent_slot','Remote::reserve','Remote::reply','Remote::close_inner','Remote::close','Remote::cleanup','Remote::transport_health'],'services_adapted':['syscall mailbox drain/close','procfs rundown','prepared-image finish','clock/msleep','Rust allocation/Arc/mutex/error representation'],'actual_exchange':'current application_rpc.rs','new_tests':3,'native_authority':False},indent=2)+'\n');print('sources',len(rows),'new_tests',3)
