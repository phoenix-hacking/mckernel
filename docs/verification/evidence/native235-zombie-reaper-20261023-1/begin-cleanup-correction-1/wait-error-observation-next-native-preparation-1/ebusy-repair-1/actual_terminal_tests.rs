#![allow(dead_code,non_camel_case_types,non_snake_case,unused_variables,unused_mut)]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Actual entire Mirror revoke bodies plus actual selector admission prefix.
use std::{sync::{Arc,Mutex,atomic::{AtomicBool,AtomicI32,Ordering}},ptr::{self,NonNull},ffi::c_void};
type Result<T=()> = std::result::Result<T,i32>;
const EBUSY:i32=-16;const EACCES:i32=-13;const EINVAL:i32=-22;const ENOENT:i32=-2;
mod application_abi {
 #[derive(Clone,Copy)]pub struct Identity{pub child_mm:u64,pub start:u64,pub length:u64,pub generation:u64,pub root:u64,pub parent:u64,pub child:u64,pub worker:u64,pub delivery:u64,pub nonce:u64,pub child_pid:i32}
 pub struct ForkRevokeClaimV1{pub identity:Identity,pub carrier:u64}
}
mod vm {
use super::*;
#[derive(Default)]struct Stats{locked:bool,locks:usize,unlocks:usize,finds:usize,zaps:usize,puts:usize,recheck_to:Option<i32>,foreign_on_lock:bool,foreign:*const AtomicBool,nodes:Vec<Box<bindings::vm_area_struct>>}
thread_local!{static STATE:std::cell::RefCell<Stats>=std::cell::RefCell::new(Stats::default());}
mod bindings {
 use super::*;
 pub struct Counter{pub counter:i32}pub struct MmAnon{pub mm_users:Counter}pub struct mm_struct{pub __bindgen_anon_1:MmAnon}
 pub struct Bounds{pub vm_start:u64,pub vm_end:u64}pub struct VmaAnon{pub __bindgen_anon_1:Bounds}pub struct Flags{pub __vm_flags:u64}
 pub struct vm_area_struct{pub __bindgen_anon_1:VmaAnon,pub vm_mm:*mut mm_struct,pub vm_ops:*const Ops,pub __bindgen_anon_2:Flags,pub vm_file:*mut c_void,pub owner:*const VmaOwner}
 pub const VM_PFNMAP:u32=0x400;
 pub unsafe fn find_vma(mm:*mut mm_struct,address:u64)->*mut vm_area_struct{STATE.with(|s|{let mut s=s.borrow_mut();assert!(s.locked);s.finds+=1;s.nodes.iter_mut().find(|v|v.vm_mm==mm&&v.__bindgen_anon_1.__bindgen_anon_1.vm_end>address).map_or(ptr::null_mut(),|v|&mut**v)})}
 pub unsafe fn zap_vma_ptes(_v:*mut vm_area_struct,_start:u64,_length:u64){STATE.with(|s|{let mut s=s.borrow_mut();assert!(s.locked);s.zaps+=1;});}
}
unsafe fn mckernel_inherited_mmap_write_lock(mm:*mut c_void){STATE.with(|s|{let mut s=s.borrow_mut();assert!(!s.locked);s.locked=true;s.locks+=1;if let Some(value)=s.recheck_to.take(){unsafe{AtomicI32::from_ptr(ptr::addr_of_mut!((*mm.cast::<bindings::mm_struct>()).__bindgen_anon_1.mm_users.counter))}.store(value,Ordering::Release);}if s.foreign_on_lock{assert!(!s.foreign.is_null());unsafe{&*s.foreign}.store(true,Ordering::Release);}});}
unsafe fn mckernel_inherited_mmap_write_unlock(_mm:*mut c_void){STATE.with(|s|{let mut s=s.borrow_mut();assert!(s.locked);s.locked=false;s.unlocks+=1;});}
unsafe fn mckernel_inherited_vma_start_write(_v:*mut c_void){STATE.with(|s|assert!(s.borrow().locked));}
struct CurrentMm(NonNull<bindings::mm_struct>);
impl Drop for CurrentMm{fn drop(&mut self){STATE.with(|s|{let mut s=s.borrow_mut();assert!(!s.locked,"mmput under mmap lock");s.puts+=1;});unsafe{AtomicI32::from_ptr(ptr::addr_of_mut!((*self.0.as_ptr()).__bindgen_anon_1.mm_users.counter))}.fetch_sub(1,Ordering::Release);}}
struct InheritedWrite<'a>(&'a CurrentMm);impl Drop for InheritedWrite<'_>{fn drop(&mut self){unsafe{mckernel_inherited_mmap_write_unlock(self.0.0.as_ptr().cast())};}}
struct MmIdentity(NonNull<bindings::mm_struct>);struct Mirror{mm:MmIdentity,start:u64,end:u64,admission:AtomicBool,foreign_alias_seen:AtomicBool}
struct Ops;struct OpsWrap(Ops);static VM_OPERATIONS:OpsWrap=OpsWrap(Ops);
struct VmaOwner{mirror:Arc<Mirror>}
unsafe fn vma_owner(v:*mut bindings::vm_area_struct)->Result<&'static VmaOwner>{let o=unsafe{(*v).owner};if o.is_null(){Err(EACCES)}else{Ok(unsafe{&*o})}}
impl Mirror {
pub(super) fn revoke_fork_aliases(self:&Arc<Self>,claim:&super::application_abi::ForkRevokeClaimV1)->Result {
        let identity=claim.identity;
        if identity.child_mm!=self.mm.0.as_ptr() as u64||identity.start!=self.start
            ||identity.start.checked_add(identity.length)!=Some(self.end)||identity.generation==0
            ||identity.root==0||identity.root%4096!=0||identity.parent==0||identity.child==0
            ||identity.parent==identity.child||identity.worker==0||identity.delivery==0
            ||identity.nonce==0||identity.child_pid<=0||claim.carrier==0||claim.carrier%8!=0{return Err(EACCES);}
        // Monotonic closure. No PID disappearance or scalar return proves MM
        // retirement. The structural pin permits guarded mmget or the terminal proof below.
        self.admission.store(false,Ordering::Release);
        let users=unsafe {AtomicI32::from_ptr(ptr::addr_of_mut!(
            (*self.mm.0.as_ptr()).__bindgen_anon_1.mm_users.counter))};
        if let Err(previous)=users.fetch_update(Ordering::Acquire,Ordering::Relaxed,|n|
            if n>0{n.checked_add(1)}else{None}) {
            if previous!=0{return Err(EBUSY);}
            // The Arc's structural MM pin spans this distinct terminal proof.
            // Zero users alone is insufficient: Linux must have removed every
            // VMA under this exact MM's write lock. Never acquire CurrentMm,
            // call mmput, dereference a VMA, or zap on this zero-users path.
            unsafe {mckernel_inherited_mmap_write_lock(self.mm.0.as_ptr().cast())};
            let empty=users.load(Ordering::Acquire)==0
                &&!self.foreign_alias_seen.load(Ordering::Acquire)
                &&unsafe {bindings::find_vma(self.mm.0.as_ptr(),0).is_null()};
            unsafe {mckernel_inherited_mmap_write_unlock(self.mm.0.as_ptr().cast())};
            return if empty{Ok(())}else{Err(EBUSY)};
        }
        let mm=CurrentMm(self.mm.0);
        unsafe {mckernel_inherited_mmap_write_lock(mm.0.as_ptr().cast())};
        let guard=InheritedWrite(&mm);
        let result=(||->Result {
            if self.foreign_alias_seen.load(Ordering::Acquire){return Err(EBUSY);}
            // Include split/moved aliases throughout this MM. Preflight all,
            // exclude per-VMA readers, then zap (including Linux TLB finish).
            for pass in 0..3 {
                let mut address=0;
                loop {
                    let vma=unsafe {bindings::find_vma(mm.0.as_ptr(),address)};
                    if vma.is_null(){break;}
                    let(first,last)=unsafe {((*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start,
                        (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_end)};
                    if first<address||last<=first||last%4096!=0
                        ||unsafe {(*vma).vm_mm}!=mm.0.as_ptr(){return Err(EBUSY);}
                    if unsafe {(*vma).vm_ops}==&VM_OPERATIONS.0 {
                        let owner=unsafe {vma_owner(vma)}.map_err(|_|EBUSY)?;
                        if ptr::eq(&*owner.mirror,&**self) {
                            if first%4096!=0||unsafe {(*vma).vm_file.is_null()}
                                ||unsafe {(*vma).__bindgen_anon_2.__vm_flags}&bindings::VM_PFNMAP as u64==0{return Err(EBUSY);}
                            if pass==1{unsafe {mckernel_inherited_vma_start_write(vma.cast())};}
                            if pass==2{unsafe {bindings::zap_vma_ptes(vma,first,last-first)};}
                        }
                    }
                    address=last;
                }
            }
            Ok(())
        })();
        drop(guard);drop(mm);result
    }
pub(super) fn baseline_revoke_fork_aliases(self:&Arc<Self>,claim:&super::application_abi::ForkRevokeClaimV1)->Result {
        let identity=claim.identity;
        if identity.child_mm!=self.mm.0.as_ptr() as u64||identity.start!=self.start
            ||identity.start.checked_add(identity.length)!=Some(self.end)||identity.generation==0
            ||identity.root==0||identity.root%4096!=0||identity.parent==0||identity.child==0
            ||identity.parent==identity.child||identity.worker==0||identity.delivery==0
            ||identity.nonce==0||identity.child_pid<=0||claim.carrier==0||claim.carrier%8!=0{return Err(EACCES);}
        // Monotonic closure. No PID disappearance or scalar return proves MM
        // retirement. The structural pin only permits this guarded mmget.
        self.admission.store(false,Ordering::Release);
        let users=unsafe {AtomicI32::from_ptr(ptr::addr_of_mut!(
            (*self.mm.0.as_ptr()).__bindgen_anon_1.mm_users.counter))};
        users.fetch_update(Ordering::Acquire,Ordering::Relaxed,|n|
            if n>0{n.checked_add(1)}else{None}).map_err(|_|EBUSY)?;
        let mm=CurrentMm(self.mm.0);
        unsafe {mckernel_inherited_mmap_write_lock(mm.0.as_ptr().cast())};
        let guard=InheritedWrite(&mm);
        let result=(||->Result {
            if self.foreign_alias_seen.load(Ordering::Acquire){return Err(EBUSY);}
            // Include split/moved aliases throughout this MM. Preflight all,
            // exclude per-VMA readers, then zap (including Linux TLB finish).
            for pass in 0..3 {
                let mut address=0;
                loop {
                    let vma=unsafe {bindings::find_vma(mm.0.as_ptr(),address)};
                    if vma.is_null(){break;}
                    let(first,last)=unsafe {((*vma).__bindgen_anon_1.__bindgen_anon_1.vm_start,
                        (*vma).__bindgen_anon_1.__bindgen_anon_1.vm_end)};
                    if first<address||last<=first||last%4096!=0
                        ||unsafe {(*vma).vm_mm}!=mm.0.as_ptr(){return Err(EBUSY);}
                    if unsafe {(*vma).vm_ops}==&VM_OPERATIONS.0 {
                        let owner=unsafe {vma_owner(vma)}.map_err(|_|EBUSY)?;
                        if ptr::eq(&*owner.mirror,&**self) {
                            if first%4096!=0||unsafe {(*vma).vm_file.is_null()}
                                ||unsafe {(*vma).__bindgen_anon_2.__vm_flags}&bindings::VM_PFNMAP as u64==0{return Err(EBUSY);}
                            if pass==1{unsafe {mckernel_inherited_vma_start_write(vma.cast())};}
                            if pass==2{unsafe {bindings::zap_vma_ptes(vma,first,last-first)};}
                        }
                    }
                    address=last;
                }
            }
            Ok(())
        })();
        drop(guard);drop(mm);result
    }
}
fn fixture(users:i32)->(Box<bindings::mm_struct>,Arc<Mirror>,application_abi::ForkRevokeClaimV1){STATE.with(|s|*s.borrow_mut()=Stats::default());let mut mm=Box::new(bindings::mm_struct{__bindgen_anon_1:bindings::MmAnon{mm_users:bindings::Counter{counter:users}}});let mirror=Arc::new(Mirror{mm:MmIdentity(NonNull::from(&mut*mm)),start:4096,end:8192,admission:AtomicBool::new(true),foreign_alias_seen:AtomicBool::new(false)});let claim=application_abi::ForkRevokeClaimV1{identity:application_abi::Identity{child_mm:&*mm as*const _ as u64,start:4096,length:4096,generation:1,root:8192,parent:1,child:2,worker:3,delivery:4,nonce:5,child_pid:258},carrier:4096};(mm,mirror,claim)}
fn add_vma(mm:&mut bindings::mm_struct,mirror:Option<Arc<Mirror>>)->Option<Box<VmaOwner>>{let owner=mirror.map(|mirror|Box::new(VmaOwner{mirror}));let ptr=owner.as_ref().map_or(ptr::null(),|v|&**v as*const VmaOwner);STATE.with(|s|s.borrow_mut().nodes.push(Box::new(bindings::vm_area_struct{__bindgen_anon_1:bindings::VmaAnon{__bindgen_anon_1:bindings::Bounds{vm_start:4096,vm_end:8192}},vm_mm:mm,vm_ops:&VM_OPERATIONS.0,__bindgen_anon_2:bindings::Flags{__vm_flags:bindings::VM_PFNMAP as u64},vm_file:std::ptr::dangling_mut::<u8>().cast(),owner:ptr})));owner}
#[test]fn baseline_refuses_terminal_empty_mm_candidate_proves_empty(){let(mut mm,m,c)=fixture(0);assert_eq!(m.baseline_revoke_fork_aliases(&c),Err(EBUSY));assert_eq!(m.revoke_fork_aliases(&c),Ok(()));STATE.with(|s|{let s=s.borrow();assert_eq!((s.locks,s.unlocks,s.finds,s.zaps,s.puts),(1,1,1,0,0));assert!(!s.locked);});assert_eq!(mm.__bindgen_anon_1.mm_users.counter,0);assert!(!m.admission.load(Ordering::Acquire));}
#[test]fn terminal_any_vma_retains_without_zap_or_mmput(){let(mut mm,m,c)=fixture(0);let _owner=add_vma(&mut mm,None);assert_eq!(m.revoke_fork_aliases(&c),Err(EBUSY));STATE.with(|s|{let s=s.borrow();assert_eq!((s.locks,s.unlocks,s.finds,s.zaps,s.puts),(1,1,1,0,0));});}
#[test]fn terminal_sticky_foreign_flag_checked_under_write_lock(){let(_mm,m,c)=fixture(0);STATE.with(|s|{let mut s=s.borrow_mut();s.foreign_on_lock=true;s.foreign=&m.foreign_alias_seen;});assert_eq!(m.revoke_fork_aliases(&c),Err(EBUSY));assert!(m.foreign_alias_seen.load(Ordering::Acquire));STATE.with(|s|{let s=s.borrow();assert_eq!((s.locks,s.unlocks,s.finds,s.zaps,s.puts),(1,1,0,0,0));});}
#[test]fn terminal_users_rechecked_after_lock_without_claiming_external_reference(){let(mm,m,c)=fixture(0);STATE.with(|s|s.borrow_mut().recheck_to=Some(1));assert_eq!(m.revoke_fork_aliases(&c),Err(EBUSY));assert_eq!(mm.__bindgen_anon_1.mm_users.counter,1);STATE.with(|s|{let s=s.borrow();assert_eq!((s.locks,s.unlocks,s.finds,s.zaps,s.puts),(1,1,0,0,0));});}
#[test]fn negative_and_overflow_users_refuse_without_lock_or_mmput(){for users in [-1,i32::MAX]{let(mm,m,c)=fixture(users);assert_eq!(m.revoke_fork_aliases(&c),Err(EBUSY));assert_eq!(mm.__bindgen_anon_1.mm_users.counter,users);STATE.with(|s|{let s=s.borrow();assert_eq!((s.locks,s.unlocks,s.finds,s.zaps,s.puts),(0,0,0,0,0));});}}
#[test]fn live_mm_revoke_path_balances_real_acquisition_after_unlock(){let(mut mm,m,c)=fixture(1);let _owner=add_vma(&mut mm,Some(m.clone()));assert_eq!(m.revoke_fork_aliases(&c),Ok(()));assert_eq!(mm.__bindgen_anon_1.mm_users.counter,1);STATE.with(|s|{let s=s.borrow();assert_eq!((s.locks,s.unlocks,s.zaps,s.puts),(1,1,1,1));assert!(!s.locked);});}
#[test]fn live_foreign_alias_refuses_and_balances_mmput(){let(mm,m,c)=fixture(1);m.foreign_alias_seen.store(true,Ordering::Release);assert_eq!(m.revoke_fork_aliases(&c),Err(EBUSY));assert_eq!(mm.__bindgen_anon_1.mm_users.counter,1);STATE.with(|s|{let s=s.borrow();assert_eq!((s.locks,s.unlocks,s.zaps,s.puts),(1,1,0,1));});}
#[test]fn forged_claim_fails_before_admission_or_lock(){let(_mm,m,mut c)=fixture(0);c.identity.child_mm+=8;assert_eq!(m.revoke_fork_aliases(&c),Err(EACCES));assert!(m.admission.load(Ordering::Acquire));STATE.with(|s|assert_eq!(s.borrow().locks,0));}
}

mod control {
use super::*;
#[derive(Clone,Copy,Debug,Eq,PartialEq)]struct Token(u64);
type ForkControlCallV1=Call;
struct Call{worker:u64,delivery:u64}struct Image;
struct Ingress{parent:Token,child:Token,sealed:AtomicBool,first_return_published:bool}
struct Entry{token:Token,closed:bool,needs_cleanup:bool,quarantined:bool,fork_ingress:Option<Ingress>,inherited_root:Option<Image>,pins:usize,credits:usize}
impl Entry{fn key(&self)->Token{self.token}}
struct Lock<T>(Mutex<T>);impl<T> Lock<T>{fn lock(&self)->std::sync::MutexGuard<'_,T>{self.0.lock().unwrap()}}
struct Remote{slots:Lock<Vec<Option<Entry>>>}
impl Remote {
pub(crate) unsafe fn candidate_admission(&self,parent:Token,child:Token,call:&mut ForkControlCallV1)->Result {
        if parent==child||call.worker==0||call.delivery==0{return Err(EINVAL);}
        let worker=call.worker;let serial=call.delivery;
        {
            let mut slots=self.slots.lock();
            let p=slots.iter().position(|e|e.as_ref().is_some_and(|e|e.key()==parent)).ok_or(ENOENT)?;
            let c=slots.iter().position(|e|e.as_ref().is_some_and(|e|e.key()==child)).ok_or(ENOENT)?;
            if p==c{return Err(EINVAL);}
            let pe=slots[p].as_ref().unwrap();let ce=slots[c].as_ref().unwrap();
            // Child terminal intent closes ordinary admissions but must not block
            // this exact retained selector2/3 revoke and destructor-ACK route.
            if pe.closed||pe.needs_cleanup||pe.quarantined||ce.closed||ce.quarantined{return Err(EBUSY);}
            let owner=ce.fork_ingress.as_ref().ok_or(EACCES)?;let image=ce.inherited_root.as_ref().ok_or(EACCES)?;
            if owner.parent!=parent||owner.child!=child||!owner.sealed.load(Ordering::Acquire)
                ||!owner.first_return_published{return Err(EACCES);}
            Ok(())
        }
    }
pub(crate) unsafe fn baseline_admission(&self,parent:Token,child:Token,call:&mut ForkControlCallV1)->Result {
        if parent==child||call.worker==0||call.delivery==0{return Err(EINVAL);}
        let worker=call.worker;let serial=call.delivery;
        {
            let mut slots=self.slots.lock();
            let p=slots.iter().position(|e|e.as_ref().is_some_and(|e|e.key()==parent)).ok_or(ENOENT)?;
            let c=slots.iter().position(|e|e.as_ref().is_some_and(|e|e.key()==child)).ok_or(ENOENT)?;
            if p==c{return Err(EINVAL);}
            let pe=slots[p].as_ref().unwrap();let ce=slots[c].as_ref().unwrap();
            if pe.closed||pe.needs_cleanup||pe.quarantined||ce.closed||ce.needs_cleanup||ce.quarantined{return Err(EBUSY);}
            let owner=ce.fork_ingress.as_ref().ok_or(EACCES)?;let image=ce.inherited_root.as_ref().ok_or(EACCES)?;
            if owner.parent!=parent||owner.child!=child||!owner.sealed.load(Ordering::Acquire)
                ||!owner.first_return_published{return Err(EACCES);}
            Ok(())
        }
    }
}
fn fixture()->(Remote,Call){let rows=vec![Some(Entry{token:Token(1),closed:false,needs_cleanup:false,quarantined:false,fork_ingress:None,inherited_root:None,pins:1,credits:1}),Some(Entry{token:Token(2),closed:false,needs_cleanup:true,quarantined:false,fork_ingress:Some(Ingress{parent:Token(1),child:Token(2),sealed:AtomicBool::new(true),first_return_published:true}),inherited_root:Some(Image),pins:1,credits:1})];(Remote{slots:Lock(Mutex::new(rows))},Call{worker:3,delivery:4})}
#[test]fn baseline_post_begin_refusal_candidate_terminal_route_admits_without_release(){let(r,mut c)=fixture();assert_eq!(unsafe{r.baseline_admission(Token(1),Token(2),&mut c)},Err(EBUSY));assert_eq!(unsafe{r.candidate_admission(Token(1),Token(2),&mut c)},Ok(()));let s=r.slots.lock();assert!(s[1].as_ref().unwrap().needs_cleanup);for row in s.iter().flatten(){assert_eq!((row.pins,row.credits),(1,1));}}
#[test]fn parent_cleanup_closed_and_either_quarantine_still_refuse(){for (index,field)in[(0,0),(0,1),(0,2),(1,1),(1,2)]{let(r,mut c)=fixture();{let mut s=r.slots.lock();let e=s[index].as_mut().unwrap();match field{0=>e.needs_cleanup=true,1=>e.closed=true,_=>e.quarantined=true}}assert_eq!(unsafe{r.candidate_admission(Token(1),Token(2),&mut c)},Err(EBUSY));}}
#[test]fn unpublished_unsealed_and_mismatched_pair_refuse(){for field in 0..4{let(r,mut c)=fixture();{let mut s=r.slots.lock();let owner=s[1].as_mut().unwrap().fork_ingress.as_mut().unwrap();match field{0=>owner.first_return_published=false,1=>owner.sealed.store(false,Ordering::Release),2=>owner.parent=Token(9),_=>owner.child=Token(9)}}assert_eq!(unsafe{r.candidate_admission(Token(1),Token(2),&mut c)},Err(EACCES));}}
#[test]fn stale_missing_and_invalid_call_do_not_admit(){let(r,mut c)=fixture();assert_eq!(unsafe{r.candidate_admission(Token(1),Token(9),&mut c)},Err(ENOENT));assert_eq!(unsafe{r.candidate_admission(Token(1),Token(1),&mut c)},Err(EINVAL));c.delivery=0;assert_eq!(unsafe{r.candidate_admission(Token(1),Token(2),&mut c)},Err(EINVAL));}
}
