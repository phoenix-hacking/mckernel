#![allow(dead_code,non_snake_case)]
mod process {
// Explicit std ownership/locking/allocation and IHK-auth adapters. No Linux ABI,
// MM, actual provider Request authentication or native process-exit proof.
use std::{ptr,pin::Pin,sync::{Arc,Mutex as StdMutex,OnceLock,atomic::{AtomicBool,AtomicI32,Ordering}},ffi::c_void};
use std::ptr::NonNull;
#[derive(Clone,Copy,Debug,PartialEq,Eq)] struct Error(i32);
impl Error {fn to_errno(self)->i32 {self.0}}
type Result<T=()> = std::result::Result<T,Error>;
const EINVAL:Error=Error(-22);const EACCES:Error=Error(-13);const EBUSY:Error=Error(-16);
const ENOENT:Error=Error(-2);const GFP_KERNEL:()=();
fn errno(v:i32)->Error {Error(v)}
mod kernel {pub mod error {pub fn to_result(v:i32)->super::super::Result {if v<0 {Err(super::super::Error(v))}else{Ok(())}}}}
struct Mutex<T>(StdMutex<T>);
impl<T> Mutex<T>{fn new(v:T)->Self{Self(StdMutex::new(v))}fn lock(&self)->std::sync::MutexGuard<'_,T>{self.0.lock().unwrap()}}
struct Vec<T>(std::vec::Vec<T>);
impl<T> Vec<T>{fn new()->Self{Self(std::vec::Vec::with_capacity(64))}fn push(&mut self,v:T,_:())->Result{assert!(self.0.len()<self.0.capacity(),"unexpected allocation");self.0.push(v);Ok(())}fn swap_remove(&mut self,i:usize)->T{self.0.swap_remove(i)}}
impl<T> std::ops::Deref for Vec<T>{type Target=[T];fn deref(&self)->&[T]{&self.0}}
impl<T> std::ops::DerefMut for Vec<T>{fn deref_mut(&mut self)->&mut[T]{&mut self.0}}
mod Box {pub fn new<T>(v:T,_:())->super::Result<std::boxed::Box<T>>{Ok(std::boxed::Box::new(v))}pub fn into_raw<T>(v:std::boxed::Box<T>)->*mut T{std::boxed::Box::into_raw(v)}pub unsafe fn from_raw<T>(p:*mut T)->std::boxed::Box<T>{unsafe{std::boxed::Box::from_raw(p)}}}
pub(crate) mod application_abi {
 use super::*;
 #[derive(Clone,Copy,PartialEq,Eq)] pub struct ForkGeometryV3{pub root:u64,pub start:u64,pub length:u64}
 pub struct ForkPreparedV3{pub geometry:ForkGeometryV3,pub child_pid:i32,pub reserved:u32,pub child_mm:u64,pub response:u64,pub nonce:u64}
 pub struct Identity{pub slot:u32,pub generation:u64,pub child_pid:i32}
 pub struct ForkRevokeClaimV1{pub identity:Identity}
 pub struct ForkControlCallV1{pub version:u32,pub bytes:u32,pub child:*mut c_void,pub worker:u64,pub delivery:u64,pub owner:*mut c_void,pub revoke:Option<unsafe extern "C" fn(*mut c_void,*const ForkRevokeClaimV1)->i32>,pub accept:Option<unsafe extern "C" fn(*mut c_void)->i32>,pub release:Option<unsafe extern "C" fn(*mut c_void)>}
}
pub(crate) mod mcctrl_vm {pub struct DeferredModule;impl DeferredModule{pub fn acquire()->super::Result<Self>{Ok(Self)}}impl Drop for DeferredModule {fn drop(&mut self){super::MODULE_RELEASES.fetch_add(1,super::Ordering::SeqCst);}}}
#[derive(Clone)] struct ProcessId{pid:i32,token:u64}
impl ProcessId{fn number(&self)->Result<i32>{Ok(self.pid)}fn same(&self,other:&Self)->bool{self.token==other.token}}
struct Mirror;
impl Mirror{fn revoke_fork_aliases(&self,_:&application_abi::ForkRevokeClaimV1)->Result{Ok(())}}
struct HostWorker{handle:u64}
struct Registration {context:NonNull<c_void>,slot:u32,generation:u64,pid:i32,armed:AtomicBool,mapping:Mutex<Option<Arc<Mirror>>>,control_children:Pin<std::boxed::Box<Mutex<Vec<current_fork_host::ForkChildRoute>>>>,fork_parent:Pin<std::boxed::Box<Mutex<Option<Arc<Registration>>>>>,_pid:ProcessId}
unsafe impl Send for Registration{}unsafe impl Sync for Registration{}
impl Registration {fn new(pid:i32,token:u64)->Arc<Self>{Arc::new(Self{context:NonNull::new(token as *mut c_void).unwrap(),slot:1,generation:7,pid,armed:AtomicBool::new(true),mapping:Mutex::new(Some(Arc::new(Mirror))),control_children:std::boxed::Box::pin(Mutex::new(Vec::new())),fork_parent:std::boxed::Box::pin(Mutex::new(None)),_pid:ProcessId{pid,token}})}}
struct Process{slot:u32,generation:u64,pid:ProcessId,registration:Mutex<Option<Arc<Registration>>>}
struct Entry{process:Arc<Process>}
fn table()->&'static Mutex<std::vec::Vec<Entry>>{static T:OnceLock<Mutex<std::vec::Vec<Entry>>>=OnceLock::new();T.get_or_init(||Mutex::new(std::vec::Vec::new()))}
struct Pending{owner:usize,revoke:unsafe extern "C" fn(*mut c_void,*const application_abi::ForkRevokeClaimV1)->i32,accept:unsafe extern "C" fn(*mut c_void)->i32,release:unsafe extern "C" fn(*mut c_void)}
static MODE:AtomicI32=AtomicI32::new(0);
static MODULE_RELEASES:AtomicI32=AtomicI32::new(0);
fn blocked()->&'static Mutex<Option<(Arc<std::sync::Barrier>,Arc<std::sync::Barrier>)>>{static B:OnceLock<Mutex<Option<(Arc<std::sync::Barrier>,Arc<std::sync::Barrier>)>>>=OnceLock::new();B.get_or_init(||Mutex::new(None))}
fn pending()->&'static Mutex<Option<Pending>>{static P:OnceLock<Mutex<Option<Pending>>>=OnceLock::new();P.get_or_init(||Mutex::new(None))}
// Mode0: documented no-effect refusal. Mode1: uncertain partial transfer.
// Mode2: authenticated adapter success; Mode3 refuses source Request identity.
unsafe fn ihk_os_application_fork_control_current_v1(parent:*mut c_void,child:*mut c_void,call:*mut application_abi::ForkControlCallV1)->i32 {
 let call=unsafe{&mut*call};let mode=MODE.load(Ordering::SeqCst);
 if mode==0{return -5;}if mode==1{call.owner=ptr::null_mut();return -5;}
 if mode==4{call.owner=ptr::null_mut();call.revoke=None;call.accept=None;call.release=None;return -5;}
 if mode==6{return 0;}
 if mode==7{call.delivery+=1;return -5;}
 if mode==8{let(a,b)=blocked().lock().as_ref().unwrap().clone();a.wait();b.wait();return -5;}
 if mode==3||parent as usize!=100||child as usize!=200||call.delivery!=91||call.worker==0{return -13;}
 if !call.owner.is_null(){*pending().lock()=Some(Pending{owner:call.owner as usize,revoke:call.revoke.unwrap(),accept:call.accept.unwrap(),release:call.release.unwrap()});call.owner=ptr::null_mut();call.revoke=None;call.accept=None;call.release=None;if mode==5{-5}else{0}}
 else {let Some(p)=pending().lock().take()else{return -13};let claim=application_abi::ForkRevokeClaimV1{identity:application_abi::Identity{slot:1,generation:7,child_pid:20}};let r=unsafe{(p.revoke)(p.owner as *mut c_void,&claim)};if r!=0{return r;}let r=unsafe{(p.accept)(p.owner as *mut c_void)};unsafe{(p.release)(p.owner as *mut c_void)};r}
}
#[path="/home/holden/mckernel-work/host-preparation/phase5-postexit-real-delivery-source-next-20261020-1/fixture-1/original-current_fork_host.rs"] mod current_fork_host;

}
use process::{application_abi,mcctrl_vm};
