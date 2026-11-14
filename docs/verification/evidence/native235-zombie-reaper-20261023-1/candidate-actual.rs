#![allow(dead_code,non_snake_case,non_camel_case_types,non_upper_case_globals,private_interfaces,dropping_copy_types)]
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

use std::sync::Arc; use core::sync::atomic::{AtomicU64,Ordering};
#[path="/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/modules/application_rpc.rs"] mod application_rpc;
#[path="/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/modules/application_syscall.rs"] mod application_syscall;
#[path="/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/modules/smp_application_syscall.rs"] mod smp_application_syscall;
#[path="/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/modules/exec_transfer_checked.rs"] mod exec_transfer_checked;
#[path="/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/modules/exec_delivery.rs"] mod exec_delivery;
#[path="/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/modules/application_image.rs"] mod application_image;
use application_syscall as syscall;use smp_application_syscall as mailbox;
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

thread_local! { static WORKER:std::cell::Cell<u64>=const{std::cell::Cell::new(0)}; static BACKEND:std::cell::RefCell<Option<(mailbox::Mailbox<TestMemory>,Arc<TestRam>)>>=const{std::cell::RefCell::new(None)}; static CLEANUPS:std::cell::Cell<usize>=const{std::cell::Cell::new(0)}; static CLOSES:std::cell::Cell<usize>=const{std::cell::Cell::new(0)}; }
fn setup_backend(){
 let mut p=[0u8;128]; p[8..12].copy_from_slice(&4i32.to_le_bytes());p[32..36].copy_from_slice(&260i32.to_le_bytes());p[48..52].copy_from_slice(&260i32.to_le_bytes());p[56..64].copy_from_slice(&1u64.to_le_bytes());p[64..72].copy_from_slice(&231u64.to_le_bytes());p[120..128].copy_from_slice(&0x800000u64.to_le_bytes());
 let request=syscall::Request::decode(&p,4).unwrap();let mut q=mailbox::Mailbox::new().unwrap();let w=q.open_worker(260).unwrap();WORKER.with(|n|n.set(w));let ram=TestRam::new(request.response(),2);q.admit(request,|_|ram.claim()).unwrap();let(s,_)=q.reserve(w).unwrap().unwrap();q.copied(w,s,true).unwrap();BACKEND.with(|b|*b.borrow_mut()=Some((q,ram)));CLEANUPS.with(|n|n.set(0));CLOSES.with(|n|n.set(0));
}


mod process {
// Explicit std ownership/locking/allocation and IHK-auth adapters. No Linux ABI,
// MM, actual provider Request authentication or native process-exit proof.
use std::{ptr,pin::Pin,sync::{Arc,Mutex as StdMutex,OnceLock,atomic::{AtomicBool,AtomicI32,AtomicU64,Ordering}},ffi::c_void};
use std::ptr::NonNull;
#[derive(Clone,Copy,Debug,PartialEq,Eq)] struct Error(i32);
impl Error {fn to_errno(self)->i32 {self.0}}
type Result<T=()> = std::result::Result<T,Error>;
const EINVAL:Error=Error(-22);const EACCES:Error=Error(-13);const EBUSY:Error=Error(-16);
const EIO:Error=Error(-5);const ENOENT:Error=Error(-2);const GFP_KERNEL:()=();
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
 pub const CLEANUP:u32=4;pub const WORKER_CLOSE:u32=5;
 pub struct ForkControlCallV1{pub version:u32,pub bytes:u32,pub child:*mut c_void,pub worker:u64,pub delivery:u64,pub owner:*mut c_void,pub revoke:Option<unsafe extern "C" fn(*mut c_void,*const ForkRevokeClaimV1)->i32>,pub accept:Option<unsafe extern "C" fn(*mut c_void)->i32>,pub release:Option<unsafe extern "C" fn(*mut c_void)>}
}
pub(crate) mod mcctrl_vm {pub struct DeferredModule;impl DeferredModule{pub fn acquire()->super::Result<Self>{Ok(Self)}}}
#[derive(Clone)] struct ProcessId{pid:i32,token:u64}
impl ProcessId{fn number(&self)->Result<i32>{Ok(self.pid)}fn same(&self,other:&Self)->bool{self.token==other.token}fn thread_alive(&self)->bool{self.pid!=260}}
struct Mirror;
impl Mirror{fn revoke_fork_aliases(&self,_:&application_abi::ForkRevokeClaimV1)->Result{Ok(())}}
struct HostWorker{handle:u64,identity:ProcessId,delivery:AtomicU64}
struct Registration {context:NonNull<c_void>,slot:u32,generation:u64,pid:i32,armed:AtomicBool,cleanup_requested:AtomicBool,workers:Mutex<Vec<Arc<HostWorker>>>,mapping:Mutex<Option<Arc<Mirror>>>,control_children:Pin<std::boxed::Box<Mutex<Vec<current_fork_host::ForkChildRoute>>>>,fork_parent:Pin<std::boxed::Box<Mutex<Option<Arc<Registration>>>>>,_pid:ProcessId}
unsafe impl Send for Registration{}unsafe impl Sync for Registration{}
impl Registration {fn new(pid:i32,token:u64)->Arc<Self>{Arc::new(Self{context:NonNull::new(token as *mut c_void).unwrap(),slot:1,generation:7,pid,armed:AtomicBool::new(true),cleanup_requested:AtomicBool::new(false),workers:Mutex::new(Vec::new()),mapping:Mutex::new(Some(Arc::new(Mirror))),control_children:std::boxed::Box::pin(Mutex::new(Vec::new())),fork_parent:std::boxed::Box::pin(Mutex::new(None)),_pid:ProcessId{pid,token}})}}
struct Process{slot:u32,generation:u64,pid:ProcessId,registration:Mutex<Option<Arc<Registration>>>,executable:Mutex<Option<()>>}
struct Entry{process:Arc<Process>,files:usize}
fn table()->&'static Mutex<std::vec::Vec<Entry>>{static T:OnceLock<Mutex<std::vec::Vec<Entry>>>=OnceLock::new();T.get_or_init(||Mutex::new(std::vec::Vec::new()))}
struct Pending{owner:usize,revoke:unsafe extern "C" fn(*mut c_void,*const application_abi::ForkRevokeClaimV1)->i32,accept:unsafe extern "C" fn(*mut c_void)->i32,release:unsafe extern "C" fn(*mut c_void)}
static MODE:AtomicI32=AtomicI32::new(0);
fn pending()->&'static Mutex<Option<Pending>>{static P:OnceLock<Mutex<Option<Pending>>>=OnceLock::new();P.get_or_init(||Mutex::new(None))}
// Mode0: documented no-effect refusal. Mode1: uncertain partial transfer.
// Mode2: authenticated adapter success; Mode3 refuses source Request identity.
unsafe fn ihk_os_application_fork_control_current_v1(parent:*mut c_void,child:*mut c_void,call:*mut application_abi::ForkControlCallV1)->i32 {
 let call=unsafe{&mut*call};let mode=MODE.load(Ordering::SeqCst);
 if mode==0{return -5;}if mode==1{call.owner=ptr::null_mut();return -5;}
 if mode==3||parent as usize!=100||child as usize!=200||call.delivery!=91||call.worker==0{return -13;}
 if !call.owner.is_null(){*pending().lock()=Some(Pending{owner:call.owner as usize,revoke:call.revoke.unwrap(),accept:call.accept.unwrap(),release:call.release.unwrap()});call.owner=ptr::null_mut();call.revoke=None;call.accept=None;call.release=None;0}
 else {let Some(p)=pending().lock().take()else{return -13};let claim=application_abi::ForkRevokeClaimV1{identity:application_abi::Identity{slot:1,generation:7,child_pid:20}};let r=unsafe{(p.revoke)(p.owner as *mut c_void,&claim)};if r!=0{return r;}let r=unsafe{(p.accept)(p.owner as *mut c_void)};unsafe{(p.release)(p.owner as *mut c_void)};r}
}
#[path="/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/modules/current_fork_host.rs"] mod current_fork_host;


impl Registration{fn invoke(&self,command:u32,bytes:&mut[u8])->Result {assert_eq!(command,application_abi::WORKER_CLOSE);crate::BACKEND.with(|b|b.borrow_mut().as_mut().unwrap().0.close_worker(u64::from_le_bytes(bytes[..8].try_into().unwrap())).map_err(Error))}}

macro_rules! pr_info { ($($args:tt)*)=>{{let _=format_args!($($args)*);}} }
unsafe fn ihk_os_application_invoke_v1(_: *mut c_void,command:u32,_:*mut u8,_:usize)->i64 {assert_eq!(command,application_abi::CLEANUP);crate::CLEANUPS.with(|n|n.set(n.get()+1));crate::BACKEND.with(|b|b.borrow_mut().as_mut().unwrap().0.close().unwrap());-110}
unsafe fn ihk_os_application_close_v1(_: *mut c_void){crate::CLOSES.with(|n|n.set(n.get()+1));}

impl Registration{fn request_cleanup(&self) {
        if self.armed.load(Ordering::Acquire)
            && !self.cleanup_requested.swap(true, Ordering::AcqRel)
        {
            // SAFETY: The process's PID and this connection remain owned until
            // cleanup finishes. The continuing service owns any request whose
            // acknowledgement arrives after the bounded waiter has departed.
            let status = unsafe {
                ihk_os_application_invoke_v1(
                    self.context.as_ptr(),
                    super::application_abi::CLEANUP,
                    ptr::null_mut(),
                    0,
                )
            };
            pr_info!(
                "application_process=release os={} generation={} pid={} cleanup_errno={}\n",
                self.slot,
                self.generation,
                self.pid,
                status
            );
        }
    }}
impl Registration{fn reap_workers(&self) -> Result {
        let mut workers = self.workers.lock();
        let mut index = 0;
        while index < workers.len() {
            if !workers[index].identity.thread_alive() {
                let mut bytes = [0; 16];
                bytes[..8].copy_from_slice(&workers[index].handle.to_le_bytes());
                match self.invoke(super::application_abi::WORKER_CLOSE, &mut bytes) {
                    Ok(()) => {
                        let removed = workers.swap_remove(index);
                        drop(workers);
                        pr_info!("application_worker=retired os={} generation={} pid={} tid={} handle={} delivered={}\n",
                            self.slot, self.generation, self.pid, removed.identity.number()?, removed.handle,
                            removed.delivery.load(Ordering::Acquire));
                        // Referenced PID/MM destruction is outside publication.
                        drop(removed);
                        workers = self.workers.lock();
                        index = 0;
                        continue;
                    }
                    Err(error) if error == EBUSY => {}
                    Err(error) => return Err(error),
                }
            }
            index += 1;
        }
        Ok(())
    }}
impl Drop for Registration {
    fn drop(&mut self) {
        self.request_cleanup();
        // SAFETY: Return exactly the successful connection after invocation.
        // A failed/racing publication remains unarmed and cancels only its own
        // reserved descriptor; it cannot clean up the winning registration.
        unsafe { ihk_os_application_close_v1(self.context.as_ptr()) };
    }
}
impl Process{fn detach_owners(&self) {
        let registration = self.registration.lock().take();
        let executable = self.executable.lock().take();
        // Reaper snapshots retain only Process identity. Real VMAs and active
        // invocations still own independent Registration references.
        drop(executable);
        if let Some(owner) = &registration {
            // No process/table/MM lock spans backend cancellation or waiting.
            // Keep the connection live even when its fork pair suppresses Drop.
            owner.request_cleanup();
        }
        drop(registration);
    }}
struct Binding(Arc<Process>);
impl Drop for Binding {
    fn drop(&mut self) {
        let removed = {
            let mut entries = table().lock();
            let index = entries
                .iter()
                .position(|entry| Arc::ptr_eq(&entry.process, &self.0))
                .expect("native process binding lost its registry entry");
            assert!(entries[index].files != 0);
            entries[index].files -= 1;
            if entries[index].files == 0 {
                Some(entries.swap_remove(index))
            } else {
                None
            }
        };
        if removed.is_some() {
            // A reaper snapshot can retain Process beyond close. Explicitly
            // detach its owners here, after releasing the global table lock.
            self.0.detach_owners();
        }
        drop(removed);
    }
}

#[test]fn actual_reaper_close_retains_worker_until_actual_publication(){
 crate::setup_backend();let r=Registration::new(257,100);let handle=crate::WORKER.with(|n|n.get());r.workers.lock().push(Arc::new(HostWorker{handle,identity:ProcessId{pid:260,token:200},delivery:AtomicU64::new(97)}),GFP_KERNEL).unwrap();r.reap_workers().unwrap();assert_eq!(r.workers.lock().len(),1);
 crate::BACKEND.with(|b|{let mut b=b.borrow_mut();let(q,ram)=b.as_mut().unwrap();assert!(!q.drained());assert_eq!(ram.status(),0);assert_eq!(q.publish(0,|_|Err(-11)),Err(-11));assert!(ram.claimed.load(Ordering::Acquire));assert_eq!(q.publish(0,|_|Ok(())),Ok(true));assert_eq!(ram.status(),1);assert!(q.drained());});r.reap_workers().unwrap();assert_eq!(r.workers.lock().len(),0);
}

fn fixture_pair()->(Arc<Registration>,Arc<Registration>,Arc<Process>){
 let p=Registration::new(257,100);let c=Registration::new(260,200);let proof=application_abi::ForkPreparedV3{geometry:application_abi::ForkGeometryV3{root:4096,start:8192,length:4096},child_pid:260,reserved:0,child_mm:300,response:0x800000,nonce:9};c.reserve_fork_pair(&p,&proof).unwrap();
 let process=Arc::new(Process{slot:1,generation:7,pid:c._pid.clone(),registration:Mutex::new(Some(c.clone())),executable:Mutex::new(Some(()))});table().lock().push(Entry{process:process.clone(),files:1});(p,c,process)
}
#[test]fn last_binding_close_reaches_retained_child_and_real_publication(){
 crate::setup_backend();let(p,c,process)=fixture_pair();let weak=Arc::downgrade(&c);drop(c);drop(Binding(process.clone()));assert!(table().lock().is_empty());assert!(process.registration.lock().is_none());assert!(weak.upgrade().is_some());assert_eq!(p.control_children.lock().len(),1);assert!(weak.upgrade().unwrap().armed.load(Ordering::Acquire));crate::CLOSES.with(|n|assert_eq!(n.get(),0));
 crate::CLEANUPS.with(|n|assert_eq!(n.get(),1));
 crate::BACKEND.with(|b|{let mut b=b.borrow_mut();let(q,ram)=b.as_mut().unwrap();assert!(!q.drained());assert_eq!(ram.status(),0);assert!(ram.claimed.load(Ordering::Acquire));assert_eq!(ram.releases.load(Ordering::Acquire),0);assert_eq!(q.publish(0,|_|Err(-11)),Err(-11));assert_eq!(ram.status(),0);assert!(!q.drained());assert!(ram.claimed.load(Ordering::Acquire));assert_eq!(q.publish(0,|_|Ok(())),Ok(true));assert!(q.drained());assert_eq!(ram.status(),1);assert_eq!(ram.releases.load(Ordering::Acquire),1);});
 process.detach_owners();crate::CLEANUPS.with(|n|assert_eq!(n.get(),1));assert!(weak.upgrade().is_some());assert_eq!(p.control_children.lock().len(),1);
 // Explicit test teardown after checks; this is not a production release path.
 let child=weak.upgrade().unwrap();drop(p.control_children.lock().swap_remove(0));child.fork_parent.lock().take();drop(child);drop(p);drop(process);
}
#[test]fn duplicate_cleanup_is_once_and_unarmed_is_untouched(){crate::setup_backend();let p=Registration::new(257,100);p.request_cleanup();p.request_cleanup();let q=Registration::new(260,200);q.armed.store(false,Ordering::Release);drop(q);crate::CLEANUPS.with(|n|assert_eq!(n.get(),1));drop(p);crate::CLEANUPS.with(|n|assert_eq!(n.get(),1));}

}
use process::{application_abi,mcctrl_vm};
