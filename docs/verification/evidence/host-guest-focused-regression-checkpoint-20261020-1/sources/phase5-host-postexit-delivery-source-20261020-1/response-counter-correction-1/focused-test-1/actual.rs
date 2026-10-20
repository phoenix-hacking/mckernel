#![allow(dead_code,private_interfaces,unused_imports)]
// UNRUN fixture. Actual production protocol bodies; explicit host adapters.
extern crate self as kernel;
use std::{cell::UnsafeCell,ffi::c_void,sync::{Arc,atomic::{AtomicBool,AtomicUsize,Ordering}},ptr,mem::ManuallyDrop};
type Result<T=()> = std::result::Result<T,i32>;
const EINVAL:i32=-22;const EACCES:i32=-13;const EBUSY:i32=-16;const ENOENT:i32=-2;const EIO:i32=-5;
fn errno(n:i32)->i32{n} trait ToErrno{fn to_errno(self)->i32;}impl ToErrno for i32{fn to_errno(self)->i32{self}}
pub mod prelude {
 pub const GFP_KERNEL:u32=0;pub struct Vec<T>(std::vec::Vec<T>);
 pub trait VecExt<T>:Sized{fn with_capacity(c:usize,f:u32)->std::result::Result<Self,()>;fn push(&mut self,v:T,f:u32)->std::result::Result<(),()>;}
 impl<T> VecExt<T> for Vec<T>{fn with_capacity(c:usize,_:u32)->std::result::Result<Self,()>{Ok(Self(std::vec::Vec::with_capacity(c)))}fn push(&mut self,v:T,_:u32)->std::result::Result<(),()>{self.0.push(v);Ok(())}}
 impl<T> std::ops::Deref for Vec<T>{type Target=std::vec::Vec<T>;fn deref(&self)->&Self::Target{&self.0}}
 impl<T> std::ops::DerefMut for Vec<T>{fn deref_mut(&mut self)->&mut Self::Target{&mut self.0}}
}
#[path="/home/holden/mckernel-work/host-preparation/phase5-host-postexit-delivery-source-20261020-1/response-counter-correction-1/focused-test-1/application_rpc.rs"]mod application_rpc;
#[path="/home/holden/mckernel-work/host-preparation/phase5-host-postexit-delivery-source-20261020-1/response-counter-correction-1/focused-test-1/application.rs"]mod application_abi;
mod application_syscall;mod smp_application_syscall;
use application_rpc::Token;use application_syscall::{Request,ResponseMemory};
use smp_application_syscall::{Mailbox,ForkResponse};
#[repr(C,align(8))]struct Words(UnsafeCell<[u64;5]>);
struct Shared{words:Words,frame:UnsafeCell<[u8;128]>,release:AtomicUsize,capsule_release:AtomicUsize,callbacks:AtomicUsize,fail_read:AtomicBool,callback_status:std::sync::atomic::AtomicI32}
impl Shared{fn new()->Arc<Self>{Arc::new(Self{words:Words(UnsafeCell::new([0,0,2,0,0])),frame:UnsafeCell::new([0;128]),release:AtomicUsize::new(0),capsule_release:AtomicUsize::new(0),callbacks:AtomicUsize::new(0),fail_read:AtomicBool::new(false),callback_status:std::sync::atomic::AtomicI32::new(0)})}}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]struct Span{physical:u64,end:u64}#[derive(Clone,Copy,Debug,Eq,PartialEq)]struct Tag{span:Span}
struct Memory{physical:u64,shared:Arc<Shared>,payload:Option<(Tag,usize,bool)>}
type SyscallRequest=Request;type SyscallResponse=Memory;
unsafe impl ResponseMemory for Memory{fn physical(&self)->u64{self.physical}fn address(&mut self)->*mut u8{self.shared.words.0.get().cast()}unsafe fn release(self){self.shared.release.fetch_add(1,Ordering::SeqCst);}}
impl Memory{
 fn prepare_payload(&mut self,p:u64,n:usize,w:bool)->Result{if self.shared.fail_read.load(Ordering::Acquire){return Err(EIO)}if n!=128{return Err(EINVAL)}self.payload=Some((Tag{span:Span{physical:p,end:p+128}},self.shared.frame.get() as usize,w));Ok(())}
 fn pager_copy(&mut self,offset:usize,b:&mut[u8],to_guest:bool)->Result{if offset!=0||b.len()!=128{return Err(EINVAL)}if to_guest{unsafe{ptr::copy_nonoverlapping(b.as_ptr(),self.shared.frame.get().cast(),128)}}else{unsafe{ptr::copy_nonoverlapping(self.shared.frame.get().cast(),b.as_mut_ptr(),128)}}Ok(())}
    fn read_current_fork_carrier(&mut self,request:&SyscallRequest)->Result<[u8;128]> {
        let args=request.arguments();
        if request.number()!=56||args[5]!=0x313030434b46434d{return Err(EACCES);}
        if self.payload.is_none(){self.prepare_payload(args[4],128,true)?;}
        let(tag,address,writable)=self.payload.ok_or(EIO)?;
        if !writable||tag.span.physical!=args[4]
            ||tag.span.end.checked_sub(tag.span.physical)!=Some(128){return Err(EACCES);}
        // The same exclusive response-owned span permits both initial reads
        // and the eventual first receipt write; ordinary pager rights remain
        // unchanged. No peer byte is written before the original RET is bound.
        let mut bytes=[0;128];
        for(i,b)in bytes.iter_mut().enumerate(){*b=unsafe {ptr::read_volatile((address as *const u8).add(i))};}
        Ok(bytes)
    }
    pub(crate) fn current_fork_control_frame(&mut self,request:&SyscallRequest)->Result<[u8;128]> {
        let a=request.arguments();
        if request.number()!=56||!matches!(a[0],2|3)||a[5]!=0x313030434b46434d{return Err(EACCES);}
        self.read_current_fork_carrier(request)
    }
    pub(crate) fn write_fork_control_frame(&mut self,bytes:&mut[u8;128])->Result {
        self.pager_copy(0,bytes,true)
    }
}
struct Mutex<T>(std::sync::Mutex<T>);impl<T> Mutex<T>{fn new(t:T)->Self{Self(std::sync::Mutex::new(t))}fn lock(&self)->std::sync::MutexGuard<'_,T>{self.0.lock().unwrap()}}
#[derive(Clone,Copy)]struct OsOwner;impl OsOwner{fn slot(self)->u32{1}fn generation(self)->u64{3}}
// Explicit outer environment adapters; actual full InheritedRoot and ingress
// metadata declarations below, with actual move-only ForkResponse storage.
struct ChildTaskMm{pid:i32,mm:u64}impl ChildTaskMm{fn tgid(&self)->i32{self.pid}fn identity(&self)->u64{self.mm}}
struct Procfs;impl Procfs{fn close(&self){}}
mod provider{
 use super::*;
struct InheritedRoot {root:u64,start:u64,end:u64,uid:u32,gid:u32,control_cpu:i32,nonce:u64}
enum ForkResponseLocation {Ticket,Mailbox,MailboxQuarantined}
pub(crate) struct PreparedForkIngress {
    remote: core::mem::ManuallyDrop<Arc<Remote>>,
    child_task: core::mem::ManuallyDrop<ChildTaskMm>,
    response: core::mem::ManuallyDrop<super::smp_application_syscall::ForkResponse<SyscallResponse>>,
    parent: Token,
    child: Token,
    finished: bool,
    response_location:ForkResponseLocation,
    sealed:AtomicBool,
    carrier_nonce:u64,
    first_return_written:bool,
    first_return_committed:bool,
    first_return_published:bool,
    lease:core::mem::ManuallyDrop<Option<BackendForkLeaseV4>>,
    host_revoke:Option<current_fork_control::OwnedRevoke>,
}
struct BackendForkLeaseV4 {owner:*mut core::ffi::c_void,release:super::application_abi::ForkLeaseReleaseV4}
impl Drop for BackendForkLeaseV4 {fn drop(&mut self){unsafe {(self.release)(self.owner)};}}
 struct Entry{token:Token,closed:bool,needs_cleanup:bool,quarantined:bool,fork_ingress:Option<PreparedForkIngress>,inherited_root:Option<InheritedRoot>,syscalls:Mailbox<Memory>,procfs:Option<Procfs>,parent_slot_pins:u32}
 impl Entry{fn key(&self)->Token{self.token}}
 struct Changed;
 impl Changed{fn notify_all(&self){}fn wait(&self,slots:&mut std::sync::MutexGuard<'_,std::vec::Vec<Option<Entry>>>){
  // Explicit test transport scheduler only: execute the ACTUAL mailbox and
  // Response publisher. No fake returned()/ACK flag or response substitution.
  let mut progress=false;for e in slots.iter_mut().flatten(){progress|=e.syscalls.publish(0,|_|Ok(())).unwrap();}assert!(progress,"fixture publication made no progress");
 }}
 struct Remote{owner:OsOwner,slots:Mutex<std::vec::Vec<Option<Entry>>>,changed:Changed}
 #[path="/home/holden/mckernel-work/host-preparation/phase5-host-postexit-delivery-source-20261020-1/response-counter-correction-1/focused-test-1/current_fork_control.rs"] mod current_fork_control;
 use current_fork_control::ControlPhase;
 struct Setup{remote:Arc<Remote>,parent:Token,child:Token,w:u64,s:u64,request:Request,shared:Arc<Shared>}
 fn req(selector:u64,response:u64)->Request{
  let mut p=[0;128];p[8..12].copy_from_slice(&4i32.to_le_bytes());p[32..36].copy_from_slice(&100i32.to_le_bytes());p[48..52].copy_from_slice(&101i32.to_le_bytes());p[56..64].copy_from_slice(&1u64.to_le_bytes());p[64..72].copy_from_slice(&56u64.to_le_bytes());
  for(i,a)in[selector,if selector==2{123}else if selector==3{2}else{0},0x8000,0x9000,0x5000,0x313030434b46434d].iter().enumerate(){p[72+i*8..80+i*8].copy_from_slice(&a.to_le_bytes());}p[120..128].copy_from_slice(&response.to_le_bytes());Request::decode(&p,1).unwrap()
 }
 fn admit(m:&mut Mailbox<Memory>,r:Request,shared:Arc<Shared>){m.admit(r,|r|Ok(Memory{physical:r.response(),shared,payload:None})).unwrap();}
 fn setup()->Setup{
  let parent=Token::allocate().unwrap();let child=Token::allocate().unwrap();let mut m=Mailbox::new().unwrap();
  let ow=m.open_worker(201).unwrap();let original=req(0,0xa000);admit(&mut m,original.clone(),Shared::new());let(os,_)=m.reserve(ow).unwrap().unwrap();m.copied(ow,os,true).unwrap();let ticket=m.park_fork_response(ow,os,&original).unwrap();
  let shared=Shared::new();let request=req(2,0xb000);let w=m.open_worker(202).unwrap();admit(&mut m,request.clone(),shared.clone());let(s,_)=m.reserve(w).unwrap().unwrap();
  let entry=|token,syscalls|Entry{token,closed:false,needs_cleanup:false,quarantined:false,fork_ingress:None,inherited_root:None,syscalls,procfs:None,parent_slot_pins:1};
  let remote=Arc::new(Remote{owner:OsOwner,slots:Mutex::new(vec![Some(entry(parent,m)),Some(entry(child,Mailbox::new().unwrap()))]),changed:Changed});
  let owner=PreparedForkIngress{remote:ManuallyDrop::new(remote.clone()),child_task:ManuallyDrop::new(ChildTaskMm{pid:123,mm:0x6000}),response:ManuallyDrop::new(ticket),parent,child,finished:false,response_location:ForkResponseLocation::Ticket,sealed:AtomicBool::new(true),carrier_nonce:99,first_return_written:true,first_return_committed:true,first_return_published:true,lease:ManuallyDrop::new(None),host_revoke:None};
  {let mut slots=remote.slots.lock();slots[1].as_mut().unwrap().fork_ingress=Some(owner);slots[1].as_mut().unwrap().inherited_root=Some(InheritedRoot{root:0x9000,start:0,end:0x8000,uid:0,gid:0,control_cpu:0,nonce:99});}
  let f=Setup{remote,parent,child,w,s,request,shared};valid_frame(&f);f
 }
 fn valid_frame(f:&Setup){let slots=f.remote.slots.lock();let o=slots[1].as_ref().unwrap().fork_ingress.as_ref().unwrap();let(ow,os)=o.response.route();let mut b=[0;128];b[..8].copy_from_slice(b"MCFKW001");b[8..12].copy_from_slice(&[1,0,40,0]);b[12..16].copy_from_slice(&128u32.to_le_bytes());b[16..20].copy_from_slice(&1u32.to_le_bytes());b[24..32].copy_from_slice(&1u64.to_le_bytes());b[32..40].copy_from_slice(&123u64.to_le_bytes());b[40..44].copy_from_slice(&1u32.to_le_bytes());b[44..48].copy_from_slice(&123i32.to_le_bytes());for(at,v)in[(48,3),(56,f.parent.wire()),(64,ow),(72,os),(80,f.child.wire()),(88,0x6000),(96,0x9000),(104,0),(112,0x8000),(120,99)]{b[at..at+8].copy_from_slice(&v.to_le_bytes());}unsafe{*f.shared.frame.get()=b;}}
 unsafe extern "C" fn revoke(owner:*mut c_void,_:*const application_abi::ForkRevokeClaimV1)->i32{let s=unsafe{&*owner.cast::<Shared>()};s.callbacks.fetch_add(1,Ordering::SeqCst);s.callback_status.load(Ordering::Acquire)}
 unsafe extern "C" fn accept(owner:*mut c_void)->i32{let s=unsafe{&*owner.cast::<Shared>()};s.callbacks.fetch_add(1,Ordering::SeqCst);0}
 unsafe extern "C" fn release(owner:*mut c_void){let s=unsafe{&*owner.cast::<Shared>()};s.capsule_release.fetch_add(1,Ordering::SeqCst);}
 fn call(f:&Setup)->application_abi::ForkControlCallV1{application_abi::ForkControlCallV1{version:1,bytes:std::mem::size_of::<application_abi::ForkControlCallV1>()as u32,child:ptr::null_mut(),worker:f.w,delivery:f.s,owner:Arc::as_ptr(&f.shared)as *mut c_void,revoke:Some(revoke),accept:Some(accept),release:Some(release)}}
 fn invoke(f:&Setup,c:&mut application_abi::ForkControlCallV1)->Result{unsafe{f.remote.fork_control_current(f.parent,f.child,c)}}
 fn unchanged(f:&Setup,c:&application_abi::ForkControlCallV1){assert_eq!(c.owner,Arc::as_ptr(&f.shared)as *mut c_void);assert_eq!(c.revoke.map(|f|f as usize),Some(revoke as usize));assert_eq!(c.accept.map(|f|f as usize),Some(accept as usize));assert_eq!(c.release.map(|f|f as usize),Some(release as usize));assert_eq!(f.shared.callbacks.load(Ordering::Acquire),0);assert_eq!(f.shared.release.load(Ordering::Acquire),0);assert_eq!(f.shared.capsule_release.load(Ordering::Acquire),0);assert_eq!(unsafe{*f.shared.words.0.get()},[0,0,2,0,0]);}

 // Two actual reservations belong to different real Worker tokens. Retaining
 // both Requests or an ingress owner cannot delegate either delivery to the other.
 #[test]fn foreign_reserved_worker_cannot_borrow_owned_control_delivery(){
  let f=setup();let other_shared=Shared::new();let other_request=req(2,0xc000);
  let(other_worker,other_serial)={
   let mut slots=f.remote.slots.lock();let m=&mut slots[0].as_mut().unwrap().syscalls;
   let w=m.open_worker(203).unwrap();admit(m,other_request.clone(),other_shared.clone());
   let(s,_)=m.reserve(w).unwrap().unwrap();(w,s)
  };
  assert_ne!(other_worker,f.w);assert_ne!(other_serial,f.s);
  for(w,s)in[(other_worker,f.s),(f.w,other_serial)]{
   let mut c=call(&f);c.worker=w;c.delivery=s;
   assert_eq!(invoke(&f,&mut c),Err(EBUSY));unchanged(&f,&c);
   let slots=f.remote.slots.lock();let p=slots[0].as_ref().unwrap();let ch=slots[1].as_ref().unwrap();
   p.syscalls.fixture_call(f.w,f.s,&f.request,false);
   p.syscalls.fixture_call(other_worker,other_serial,&other_request,false);
   assert!(ch.fork_ingress.as_ref().unwrap().host_revoke.is_none());
   assert_eq!(ch.parent_slot_pins,1);assert_eq!(p.parent_slot_pins,1);
   assert_eq!(other_shared.callbacks.load(Ordering::Acquire),0);
   assert_eq!(other_shared.release.load(Ordering::Acquire),0);
   assert_eq!(unsafe{*other_shared.words.0.get()},[0,0,2,0,0]);
  }
  // A refusal must leave the original worker's real delivery usable. This is
  // actual Response publication through the existing test transport adapter;
  // it does not create delegated execution or a destructor ACK.
  let mut own=call(&f);assert_eq!(invoke(&f,&mut own),Ok(()));
  assert!(own.owner.is_null());assert!(own.revoke.is_none()&&own.accept.is_none()&&own.release.is_none());
  assert_eq!(f.shared.callbacks.load(Ordering::Acquire),1);
  // Actual Completion::publish releases its consumed ResponseMemory once.
  // The separate capsule remains retained; no destructor ACK has run.
  assert_eq!(f.shared.release.load(Ordering::Acquire),1);
  assert_eq!(f.shared.capsule_release.load(Ordering::Acquire),0);
  let slots=f.remote.slots.lock();
  slots[0].as_ref().unwrap().syscalls.fixture_call(other_worker,other_serial,&other_request,false);
  assert_eq!(slots[1].as_ref().unwrap().fork_ingress.as_ref().unwrap().host_revoke.as_ref().unwrap().fixture_phase(),ControlPhase::Revoked);
 }
}
