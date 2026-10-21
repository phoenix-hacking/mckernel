// SPDX-License-Identifier: GPL-2.0
//! Actual native zeroing/ledger/mapping bodies with controlled Linux providers.
#![allow(dead_code)]
extern crate self as kernel;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Error(i32);
pub type Result<T = ()> = std::result::Result<T, Error>;
pub const EINVAL: Error = Error(-22);
pub const EBUSY: Error = Error(-16);
pub const EIO: Error = Error(-5);
pub const ENOMEM: Error = Error(-12);
pub const EACCES: Error = Error(-13);
pub const EAGAIN: Error = Error(-11);
impl Error {fn to_errno(self)->i32{self.0}}
fn errno(code: i32) -> Error {
    Error(code)
}
thread_local! {
    static ALLOC_LEFT: std::cell::Cell<isize> = const { std::cell::Cell::new(-1) };
    static SLEEP_HOOK: std::cell::RefCell<Option<Box<dyn FnOnce()>>> = const { std::cell::RefCell::new(None) };
}
pub mod prelude {
    pub trait VecExt<T>{}
    impl<T> VecExt<T> for Vec<T>{}
    pub use crate::{Error, Result, EAGAIN, EBUSY, EINVAL, EIO, ENOMEM, EACCES};
    pub const GFP_KERNEL: u32 = 0;
    pub struct Vec<T>(pub std::vec::Vec<T>);
    impl<T> Vec<T> {
        pub fn new() -> Self {
            Self(std::vec::Vec::new())
        }
        pub fn as_slice(&self) -> &[T] {
            self.0.as_slice()
        }
        pub fn with_capacity(n: usize, _: u32) -> Result<Self> {
            Ok(Self(std::vec::Vec::with_capacity(n)))
        }
        pub fn push(&mut self, value: T, _: u32) -> Result {
            crate::ALLOC_LEFT.with(|left| {
                let count = left.get();
                if count == 0 {
                    return Err(ENOMEM);
                }
                if count > 0 {
                    left.set(count - 1);
                }
                self.0.try_reserve(1).map_err(|_| ENOMEM)?;
                self.0.push(value);
                Ok(())
            })
        }
        pub fn swap_remove(&mut self, index: usize) -> T {
            self.0.swap_remove(index)
        }
        pub fn remove(&mut self, index: usize) -> T {
            self.0.remove(index)
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
    impl<'a, T> IntoIterator for &'a Vec<T> {
        type Item = &'a T;
        type IntoIter = core::slice::Iter<'a, T>;
        fn into_iter(self) -> Self::IntoIter {
            self.0.iter()
        }
    }
}
pub mod sync {
    pub struct Mutex<T>(pub std::sync::Mutex<T>);
    impl<T> Mutex<T> {
        pub fn new(value: T) -> Self {
            Self(std::sync::Mutex::new(value))
        }
        pub fn lock(&self) -> std::sync::MutexGuard<'_, T> {
            self.0.lock().unwrap()
        }
    }
}
pub mod bindings {
    pub unsafe fn msleep(_: u32) {
        let hook = crate::SLEEP_HOOK.with(|slot| slot.borrow_mut().take());
        if let Some(hook) = hook {
            hook();
        }
        std::thread::yield_now();
    }
}

#[path="application_rpc.rs"]mod application_rpc;
#[path="application_syscall.rs"]mod application_syscall;
#[path="application_image.rs"]mod application_image;
#[path="application_pager.rs"]mod application_pager;
#[path="exec_transfer_checked.rs"]mod exec_transfer_checked;
#[path="exec_delivery.rs"]mod exec_delivery;
#[path="smp_application_syscall.rs"]mod smp_application_syscall;
mod memory {
use super::*;use core::{ptr,sync::atomic::{AtomicU32,AtomicU64,Ordering}};
use kernel::{prelude::*,sync::Mutex};use std::sync::Arc;
use crate::application_syscall::{Request as SyscallRequest,ResponseMemory,RESPONSE_BYTES};
use crate::exec_transfer_checked::{ResponseOwnedExecClaims,Section,Step,ExecKey};
#[derive(Clone,Copy)]struct OsToken;impl OsToken{fn slot(self)->u32{2}fn generation(self)->u64{3}}
struct Memory{owner:OsToken,storage:Box<[u64]>,ledger:Mutex<Ledger>}
impl Memory{fn address(&self,p:u64,n:usize)->Result<u64>{if p<0x100000||p.checked_add(n as u64).is_none_or(|e|e>0x140000){return Err(EINVAL);}Ok(self.storage.as_ptr() as u64+p-0x100000)}
    pub(super) fn syscall(self: &Arc<Self>, request: &SyscallRequest) -> Result<SyscallResponse> {
        let physical = request.response();
        if physical % 8 != 0 {
            return Err(EINVAL);
        }
        let address = self.address(physical, RESPONSE_BYTES)?;
        let span = Span::new(physical, RESPONSE_BYTES)?;
        let mut ledger = self.ledger.lock();
        if ledger.conflicts(span, true) {
            return Err(EBUSY);
        }
        let slot = ledger
            .responses
            .iter()
            .position(Option::is_none)
            .ok_or(EAGAIN)?;
        // SAFETY: The checked exact-generation RAM is aligned and disjoint
        // from every active service access. The guest owns only atomic state.
        let status = unsafe { AtomicU64::from_ptr((address as *mut u8).add(8).cast()) };
        // SAFETY: The same retained, response-sized mapping covers the
        // eight-byte-aligned state word at offset 16. The held ledger claim
        // excludes host aliases, while the guest accesses this shared word
        // atomically; this creates no Rust reference to guest memory.
        let state = unsafe { AtomicU64::from_ptr((address as *mut u8).add(16).cast()) };
        if status.load(Ordering::Acquire) != 0 || !matches!(state.load(Ordering::Acquire), 0 | 2) {
            return Err(errno(-71));
        }
        let tag = ledger.tag(span)?;
        ledger.responses[slot] = Some(tag);
        Ok(SyscallResponse {
            memory: self.clone(),
            address,
            tag,
            slot,
            payload: None,
            exec_group: None,
        })
    }
    pub(super) fn shutdown_quiescent(&self) -> Result {
        let ledger = self.ledger.lock();
        if ledger.requests.iter().any(Option::is_some)
            || ledger.responses.iter().any(Option::is_some)
            || ledger.payloads.iter().any(Option::is_some)
            || ledger.exec_payloads.iter().any(Option::is_some)
            || !ledger.snoops.is_empty()
            || !ledger.procfs.is_empty()
            || !ledger.zeroing.is_empty()
        {
            return Err(EBUSY);
        }
        Ok(())
    }
}
include!("actual-ledger-response-bodies.rs");

fn request()->SyscallRequest{let mut b=[0;128];b[8..12].copy_from_slice(&4i32.to_le_bytes());b[32..36].copy_from_slice(&700i32.to_le_bytes());b[48..52].copy_from_slice(&900i32.to_le_bytes());b[56..64].copy_from_slice(&1u64.to_le_bytes());b[64..72].copy_from_slice(&59u64.to_le_bytes());for(at,n)in[(72,2u64),(80,0x102000),(88,832),(120,0x101000)]{b[at..at+8].copy_from_slice(&n.to_le_bytes());}SyscallRequest::decode(&b,1).unwrap()}
fn memory()->Arc<Memory>{ALLOC_LEFT.with(|v|v.set(-1));let mut responses=Vec::new();let mut payloads=Vec::new();let mut exec_payloads=Vec::new();for _ in 0..2{responses.push(None,0).unwrap();payloads.push(None,0).unwrap();exec_payloads.push(None,0).unwrap();}Arc::new(Memory{owner:OsToken,storage:vec![0;0x40000/8].into_boxed_slice(),ledger:Mutex::new(Ledger{fixed:Vec::new(),requests:Vec::new(),responses,payloads,exec_payloads,snoops:Vec::new(),procfs:Vec::new(),zeroing:Vec::new(),serial:0})})}
fn response(m:&Arc<Memory>)->(SyscallRequest,SyscallResponse,ExecKey){let r=request();let mut response=m.syscall(&r).unwrap();let key=ExecKey{os_slot:2,os_generation:3,application:4,worker:5,delivery:6,response_serial:response.tag.serial,response_physical:r.response()};response.prepare_exec_descriptor(&r,key).unwrap();(r,response,key)}
fn sections()->[Section;2]{[Section{physical:0x110000,pages:2},Section{physical:0x120000,pages:1}]}

fn install_descriptor(m:&Arc<Memory>)->std::vec::Vec<u8>{let mut b=vec![0;832];for(at,n)in[(0,0xcafecafe44332211u64),(776,0x400000),(784,4096),(792,0x110000),(800,1)]{b[at..at+8].copy_from_slice(&n.to_le_bytes());}b[8..12].copy_from_slice(&1i32.to_le_bytes());b[816..820].copy_from_slice(&5i32.to_le_bytes());unsafe{ptr::copy_nonoverlapping(b.as_ptr(),m.address(0x102000,832).unwrap() as *mut u8,832);}b}
fn queue(m:&Arc<Memory>,r:SyscallRequest)->(crate::smp_application_syscall::Mailbox<SyscallResponse>,u64,u64){let mut q=crate::smp_application_syscall::Mailbox::new().unwrap();let w=q.open_worker(900).unwrap();q.admit(r,|r|m.syscall(r).map_err(|e|e.to_errno())).unwrap();let(s,_) =q.reserve(w).unwrap().unwrap();q.copied(w,s,true).unwrap();(q,w,s)}
fn transfer(q:&mut crate::smp_application_syscall::Mailbox<SyscallResponse>,w:u64,s:u64,step:Step,b:&mut[u8])->core::result::Result<(),i32>{q.transfer_exec(w,s,step,b,|r,m|m.prepare_exec_delivery(r,4,w,s),|r,m,key,step,b|m.copy_exec_delivery(r,key,step,b))}
#[test]fn actual_mailbox_abort_retry_immutable_snapshot_page_cursor_and_success_ret(){
 let m=memory();let expected=install_descriptor(&m);let r=request();let(mut q,w,s)=queue(&m,r.clone());let read=Step{physical:0x102000,bytes:832,direction:1};let mut b=vec![0;832];
 assert_eq!(q.return_value(w,s,0,0,|_|Ok(())),Err(-22));transfer(&mut q,w,s,read,&mut b).unwrap();assert_eq!(b,expected);
 assert_eq!(q.return_value(w,s,0,0,|_|Ok(())),Err(-16));assert!(transfer(&mut q,w,s,read,&mut b).is_err());
 q.exec_usercopy_done(w,s,false).unwrap();assert_eq!(q.return_value(w,s,0,0,|_|Ok(())),Err(-22));
 // Controlled peer mutation proves retry uses retained original immutable copy.
 unsafe{ptr::write_volatile(m.address(0x102000,1).unwrap() as *mut u8,0);}
 b.fill(0);transfer(&mut q,w,s,read,&mut b).unwrap();assert_eq!(b,expected);q.exec_usercopy_done(w,s,true).unwrap();
 assert_eq!(q.return_value(w,s,0,0,|_|Ok(())),Err(-22));assert!(q.exec_usercopy_done(w,s,true).is_err());
 let page=Step{physical:0x110000,bytes:4096,direction:0};transfer(&mut q,w,s,page,&mut[0x5a;4096]).unwrap();assert!(transfer(&mut q,w,s,page,&mut[0;4096]).is_err());
 q.return_value(w,s,0,0,|_|Ok(())).unwrap();q.publish(0,|_|Ok(())).unwrap();assert_eq!(m.shutdown_quiescent(),Ok(()));
}
#[test]fn actual_mailbox_close_defers_original_response_until_abort_then_queue_publication(){
 let m=memory();install_descriptor(&m);let r=request();unsafe{AtomicU64::from_ptr((m.address(r.response(),40).unwrap() as *mut u8).add(16).cast()).store(2,Ordering::Release);}
 let(mut q,w,s)=queue(&m,r);transfer(&mut q,w,s,Step{physical:0x102000,bytes:832,direction:1},&mut[0;832]).unwrap();
 assert_eq!(q.close_worker(w),Err(-16));assert!(!q.publish(0,|_|panic!("pending UserSlice cannot publish cancellation")).unwrap());assert_eq!(m.shutdown_quiescent(),Err(EBUSY));
 assert!(q.exec_usercopy_done(w+1,s,false).is_err());assert!(q.exec_usercopy_done(w,s+1,false).is_err());q.exec_usercopy_done(w,s,false).unwrap();
 for _ in 0..3{assert_eq!(q.publish(0,|_|Err(-11)),Err(-11));assert!(m.ledger.lock().exec_payloads[0].is_some());}
 q.publish(0,|_|Ok(())).unwrap();assert_eq!(m.shutdown_quiescent(),Ok(()));q.close_worker(w).unwrap();
}
#[test]fn actual_mailbox_phase1_ret_zero_requires_completed_exact_upload(){
 let m=memory();let mut descriptor=install_descriptor(&m);descriptor[792..800].fill(0);let old=request();let mut packet=[0;128];packet[8..12].copy_from_slice(&4i32.to_le_bytes());packet[32..36].copy_from_slice(&700i32.to_le_bytes());packet[48..52].copy_from_slice(&900i32.to_le_bytes());packet[56..64].copy_from_slice(&1u64.to_le_bytes());packet[64..72].copy_from_slice(&59u64.to_le_bytes());for(at,n)in[(72,1u64),(96,0x102000),(120,old.response())]{packet[at..at+8].copy_from_slice(&n.to_le_bytes());}let r=SyscallRequest::decode(&packet,1).unwrap();let(mut q,w,s)=queue(&m,r);
 assert_eq!(q.return_value(w,s,0,0,|_|Ok(())),Err(-22));let step=Step{physical:0x102000,bytes:832,direction:0};
 assert!(transfer(&mut q,w,s,Step{direction:1,..step},&mut descriptor).is_err());assert_eq!(q.return_value(w,s,0,0,|_|Ok(())),Err(-22));
 transfer(&mut q,w,s,step,&mut descriptor).unwrap();assert!(transfer(&mut q,w,s,step,&mut descriptor).is_err());q.return_value(w,s,0,0,|_|Ok(())).unwrap();q.publish(0,|_|Ok(())).unwrap();assert_eq!(m.shutdown_quiescent(),Ok(()));
}
#[test]fn actual_mailbox_all_bss_still_requires_usercopy_commit_and_exact_route(){
 let m=memory();let mut descriptor=install_descriptor(&m);descriptor[800..808].fill(0);unsafe{ptr::copy_nonoverlapping(descriptor.as_ptr(),m.address(0x102000,832).unwrap() as *mut u8,832);}
 let(mut q,w,s)=queue(&m,request());transfer(&mut q,w,s,Step{physical:0x102000,bytes:832,direction:1},&mut[0;832]).unwrap();assert_eq!(q.return_value(w,s,0,0,|_|Ok(())),Err(-16));q.exec_usercopy_done(w,s,true).unwrap();q.return_value(w,s,0,0,|_|Ok(())).unwrap();q.publish(0,|_|Ok(())).unwrap();assert_eq!(m.shutdown_quiescent(),Ok(()));
}
#[test]fn actual_mailbox_pending_descriptor_refuses_negative_ret_until_exact_abort(){
 let m=memory();install_descriptor(&m);let r=request();let(mut q,w,s)=queue(&m,r.clone());
 transfer(&mut q,w,s,Step{physical:0x102000,bytes:832,direction:1},&mut[0;832]).unwrap();
 // The frontend's failed DONE call can return while this exact read remains
 // pending. A later negative RET must not copy, consume, or publish Response.
 assert_eq!(q.return_value(w,s,0,-14,|_|panic!("pending failure RET cannot copy")),Err(-16));
 assert!(!q.publish(0,|_|panic!("pending failure RET cannot publish")).unwrap());
 {let ledger=m.ledger.lock();assert!(ledger.responses[0].is_some());assert!(ledger.payloads[0].is_some());assert!(ledger.exec_payloads[0].is_some());}
 assert_eq!(m.shutdown_quiescent(),Err(EBUSY));
 assert!(q.exec_usercopy_done(w+1,s,false).is_err());assert!(q.exec_usercopy_done(w,s+1,false).is_err());
 assert_eq!(q.return_value(w,s,0,-14,|_|panic!("stale abort cannot release")),Err(-16));
 q.exec_usercopy_done(w,s,false).unwrap();q.return_value(w,s,0,-14,|_|Ok(())).unwrap();
 assert!(m.ledger.lock().exec_payloads[0].is_some());q.publish(0,|_|Ok(())).unwrap();
 assert_eq!(m.shutdown_quiescent(),Ok(()));
 let address=m.address(r.response(),40).unwrap();assert_eq!(unsafe{ptr::read_volatile((address as *const u8).add(24).cast::<i64>())},-14);
}

}
