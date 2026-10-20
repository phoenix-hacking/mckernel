// SPDX-License-Identifier: GPL-2.0
//! Paired current connections and the actual owned Linux MM revoke capsule.
use super::*;
use super::super::application_abi::{ForkControlCallV1,ForkRevokeClaimV1,ForkPreparedV3,ForkGeometryV3};
// A zero carrier is private pending state, never a lookup key. The row is
// minted only by the authenticated v4 adoption callback before any MM effect.
pub(super) struct ForkChildRoute {
    carrier:u64,carrier_capsule:usize,child:Arc<Registration>,geometry:ForkGeometryV3,
    child_mm:u64,response:u64,nonce:u64,
}
impl ForkChildRoute {
    fn matches(&self,child:&Arc<Registration>,proof:&ForkPreparedV3)->bool {
        Arc::ptr_eq(&self.child,child)&&self.geometry==proof.geometry
            &&self.child.pid==proof.child_pid&&self.child_mm==proof.child_mm
            &&self.response==proof.response&&self.nonce==proof.nonce
    }
}
// A move-only witness for the exact row reserved by this synchronous call.
// The capsule allocation stays live until either transfer or private rollback;
// its address distinguishes this attempt, never supplies delivery authority.
struct ForkCarrierBinding {
    parent:usize,child:Arc<Registration>,carrier:u64,capsule:usize,response:u64,nonce:u64,
}
struct HostRevoke {
    child:Arc<Registration>,mirror:Arc<Mirror>,revoked:AtomicBool,
    // Last: Registration/Mirror Drop and connection close retain module code.
    _module:super::super::mcctrl_vm::DeferredModule,
}
unsafe extern "C" fn revoke(owner:*mut c_void,claim:*const ForkRevokeClaimV1)->i32 {
    let result=(||->Result {
        if owner.is_null()||claim.is_null(){return Err(EINVAL);}
        let owner=unsafe {&*owner.cast::<HostRevoke>()};let claim=unsafe {&*claim};let key=&claim.identity;
        if key.slot!=owner.child.slot||key.generation!=owner.child.generation||key.child_pid!=owner.child.pid
            ||owner.revoked.load(Ordering::Acquire){return Err(EACCES);}
        owner.mirror.revoke_fork_aliases(claim)?;
        owner.revoked.store(true,Ordering::Release);Ok(())
    })();result.map_or_else(|e|e.to_errno(),|()|0)
}
unsafe extern "C" fn accept(owner:*mut c_void)->i32 {
    if owner.is_null(){return EINVAL.to_errno();}
    let owner=unsafe {&*owner.cast::<HostRevoke>()};
    if !owner.revoked.load(Ordering::Acquire){return EACCES.to_errno();}
    // Invoked only after the provider authenticates the real destructor ACK.
    // No cleanup command may target guest objects that are already destroyed.
    owner.child.armed.store(false,Ordering::Release);0
}
unsafe extern "C" fn release(owner:*mut c_void){unsafe {drop(Box::from_raw(owner.cast::<HostRevoke>()))};}
impl Registration {
    pub(super) fn reserve_fork_pair(self:&Arc<Self>,parent:&Arc<Self>,proof:&ForkPreparedV3)->Result {
        if self.slot!=parent.slot||self.generation==0||self.generation!=parent.generation
            ||self.context==parent.context||self.pid!=proof.child_pid||proof.reserved!=0
            ||proof.child_mm==0||proof.response==0||proof.nonce==0{return Err(EACCES);}
        // Fixed lock order. Both caller Arcs remain live; no final Drop under locks.
        let mut children=parent.control_children.lock();let mut paired=self.fork_parent.lock();
        if paired.is_some()||children.len()>=64||children.iter().any(|row|
            Arc::ptr_eq(&row.child,self)||row.child.pid==self.pid){return Err(EBUSY);}
        // Capacity was allocated before IHK open. This push cannot grow it.
        children.push(ForkChildRoute{carrier:0,carrier_capsule:0,child:self.clone(),geometry:proof.geometry,
            child_mm:proof.child_mm,response:proof.response,nonce:proof.nonce},GFP_KERNEL)?;
        *paired=Some(parent.clone());Ok(())
    }
    pub(super) fn cancel_private_fork_pair(self:&Arc<Self>,parent:&Arc<Self>,proof:&ForkPreparedV3)->Result {
        let previous={
            let mut children=parent.control_children.lock();let mut paired=self.fork_parent.lock();
            if !paired.as_ref().map_or(false,|owner|Arc::ptr_eq(owner,parent)){return Err(EACCES);}
            let index=children.iter().position(|row|row.carrier==0&&row.matches(self,proof)).ok_or(EACCES)?;
            let row=children.swap_remove(index);let pin=paired.take();(row,pin)
        };
        drop(previous);Ok(())
    }
    fn select_fork_child(&self,selector:u64,carrier:u64,pid:i32,length:u64,root:u64)->Result<Arc<Self>> {
        let children=self.control_children.lock();
        let mut matching=children.iter().filter(|row|if selector==2 {
            row.child.pid==pid&&row.geometry.length==length&&row.geometry.root==root
        }else{selector==3&&row.carrier==carrier&&carrier!=0});
        let row=matching.next().ok_or(EACCES)?;
        if matching.next().is_some(){return Err(EACCES);}
        Ok(row.child.clone())
    }
    fn bind_fork_carrier(&self,child:&Arc<Self>,carrier:u64,capsule:usize)->Result<ForkCarrierBinding> {
        let mut children=self.control_children.lock();
        if carrier==0||capsule==0||children.iter().any(|row|row.carrier==carrier){return Err(EBUSY);}
        let row=children.iter_mut().find(|row|Arc::ptr_eq(&row.child,child)
            &&row.carrier==0&&row.carrier_capsule==0).ok_or(EACCES)?;
        row.carrier=carrier;row.carrier_capsule=capsule;
        Ok(ForkCarrierBinding{parent:self as *const Self as usize,child:child.clone(),carrier,
            capsule,response:row.response,nonce:row.nonce})
    }
    // ONLY the synchronous caller's intact negative return may consume this
    // witness. OwnedRevoke::take clears all four capsule fields before effects;
    // it never returns/restores them, including on callback/publication errors.
    // No Drop rollback: transferred, partial and unknown returns retain the row.
    fn cancel_untransferred_fork_carrier(&self,binding:ForkCarrierBinding)->Result {
        if binding.parent!=self as *const Self as usize{return Err(EACCES);}
        let mut children=self.control_children.lock();
        let row=children.iter_mut().find(|row|Arc::ptr_eq(&row.child,&binding.child)
            &&row.carrier==binding.carrier&&row.carrier_capsule==binding.capsule
            &&row.response==binding.response&&row.nonce==binding.nonce).ok_or(EACCES)?;
        row.carrier=0;row.carrier_capsule=0;Ok(())
    }
    pub(super) fn fork_control_current(&self,worker:&HostWorker,bytes:&[u8;96])->Result {
        let word=|at|u64::from_le_bytes(bytes[at..at+8].try_into().unwrap());
        let selector=word(48);let serial=word(8);let carrier=word(80);
        if carrier==0||carrier%8!=0||carrier.checked_add(128).is_none(){return Err(EINVAL);}
        if selector!=2&&selector!=3{return Err(EINVAL);}
        let pid=if selector==2 {i32::try_from(word(56)).map_err(|_|EINVAL)?}else{0};
        if selector==2&&pid<=0{return Err(EINVAL);}
        let child=self.select_fork_child(selector,carrier,pid,word(64),word(72))?;
        // A table entry is a consistency check, never an alternate owner source.
        // A detached file/PID may have no entry, but cannot substitute a reused PID.
        if selector==2 {
            let process={let entries=table().lock();entries.iter().find(|entry|
                entry.process.slot==self.slot&&entry.process.generation==self.generation
                &&entry.process.pid.number().ok()==Some(pid)).map(|entry|entry.process.clone())};
            if let Some(process)=process {
                if !process.pid.same(&child._pid){return Err(EACCES);}
                let published=process.registration.lock();
                if let Some(owner)=published.as_ref(){if !Arc::ptr_eq(owner,&child){return Err(EACCES);}}
            }
        }
        {let paired=child.fork_parent.lock();
            if !paired.as_ref().map_or(false,|parent|core::ptr::eq(&**parent,self)){return Err(EACCES);}}
        if child.slot!=self.slot||child.generation!=self.generation||child.context==self.context{return Err(EACCES);}
        let mut call=ForkControlCallV1{version:1,bytes:core::mem::size_of::<ForkControlCallV1>() as u32,
            child:ptr::null_mut(),worker:worker.handle,delivery:serial,owner:ptr::null_mut(),
            revoke:None,accept:None,release:None};
        let mut original=ptr::null_mut();let mut binding=None;
        if selector==2 {
            let mirror=child.mapping.lock().clone().ok_or(EACCES)?;
            let module=super::super::mcctrl_vm::DeferredModule::acquire()?;
            let owner=Box::new(HostRevoke{child:child.clone(),mirror,revoked:AtomicBool::new(false),_module:module},GFP_KERNEL)?;
            original=Box::into_raw(owner).cast();call.owner=original;
            call.revoke=Some(revoke);call.accept=Some(accept);call.release=Some(release);
            // Bind only this authenticated adoption's existing owned row.
            // Failure/uncertain provider publication keeps the pair and key.
            match self.bind_fork_carrier(&child,carrier,original as usize){
                Ok(owned)=>binding=Some(owned),Err(error)=>{unsafe {release(original)};return Err(error);}
            }
        }
        let status=unsafe {ihk_os_application_fork_control_current_v1(self.context.as_ptr(),child.context.as_ptr(),&mut call)};
        if !original.is_null()&&call.owner==original&&call.revoke.map(|f|f as usize)==Some(revoke as usize)
            &&call.accept.map(|f|f as usize)==Some(accept as usize)&&call.release.map(|f|f as usize)==Some(release as usize){
            // The complete original capsule stayed caller-owned throughout
            // this synchronous negative return. No provider may retain an
            // untransferred capsule: the current consumer takes it before any
            // revoke/accept/publication effect. Release only outside row locks.
            // Success with an untouched capsule is inconsistent; retain its key.
            if status<0&&call.version==1&&call.bytes==core::mem::size_of::<ForkControlCallV1>() as u32
                &&call.child.is_null()&&call.worker==worker.handle&&call.delivery==serial {
                let cancelled=match binding.take(){Some(owned)=>self.cancel_untransferred_fork_carrier(owned),None=>Err(EACCES)};
                unsafe {release(original)};cancelled?;
            }else{unsafe {release(original)};return Err(errno(-71));}
        }else if !call.owner.is_null()||call.revoke.is_some()||call.accept.is_some()||call.release.is_some(){
            // Unknown transfer is deliberately retained, never reconstructed.
            return Err(errno(-71));
        }
        kernel::error::to_result(status)?;
        if selector==3 {
            let previous={let mut children=self.control_children.lock();
                let index=children.iter().position(|row|row.carrier==carrier&&Arc::ptr_eq(&row.child,&child)).ok_or(EACCES)?;
                children.swap_remove(index)};
            drop(previous);
        }
        Ok(())
    }
}

#[cfg(test)] mod rollback_tests {
 use super::*;
 fn proof(c:&Arc<Registration>)->ForkPreparedV3{ForkPreparedV3{geometry:ForkGeometryV3{root:4096,start:8192,length:12288},child_pid:c.pid,reserved:0,child_mm:400,response:500,nonce:600}}
 fn bytes(selector:u64,pid:u64,carrier:u64)->[u8;96]{let mut b=[0;96];for(at,v)in[(8,91u64),(48,selector),(56,pid),(64,12288),(72,4096),(80,carrier)]{b[at..at+8].copy_from_slice(&v.to_le_bytes())}b}
 fn pair()->(Arc<Registration>,Arc<Registration>){table().lock().clear();MODE.store(0,Ordering::SeqCst);MODULE_RELEASES.store(0,Ordering::SeqCst);let p=Registration::new(10,100);let c=Registration::new(20,200);c.reserve_fork_pair(&p,&proof(&c)).unwrap();(p,c)}
 fn call(p:&Registration,selector:u64)->Result{p.fork_control_current(&HostWorker{handle:1},&bytes(selector,if selector==2{20}else{0},800))}
 #[test] fn rollback_negative_no_transfer_allows_actual_retry_and_ack(){
  let(p,c)=pair();assert_eq!(call(&p,2),Err(errno(-5)));assert_eq!(MODULE_RELEASES.load(Ordering::SeqCst),1);
  {let rows=p.control_children.lock();assert_eq!(rows.len(),1);assert_eq!(rows[0].carrier,0);assert_eq!(rows[0].carrier_capsule,0);}
  assert!(c.fork_parent.lock().is_some());MODE.store(2,Ordering::SeqCst);assert_eq!(call(&p,2),Ok(()));assert_eq!(call(&p,3),Ok(()));assert!(p.control_children.lock().is_empty());assert!(!c.armed.load(Ordering::Acquire));assert_eq!(MODULE_RELEASES.load(Ordering::SeqCst),2);
 }
 #[test] fn rollback_bad_request_identity_returns_key_before_corrected_delivery(){
  let(p,_c)=pair();MODE.store(3,Ordering::SeqCst);assert_eq!(call(&p,2),Err(EACCES));assert_eq!(p.control_children.lock()[0].carrier,0);
  MODE.store(2,Ordering::SeqCst);assert_eq!(call(&p,2),Ok(()));assert_eq!(call(&p,3),Ok(()));
 }
 #[test] fn rollback_partial_and_transferred_errors_never_return_key(){
  for mode in [1,4,5]{let(p,c)=pair();MODE.store(mode,Ordering::SeqCst);assert!(call(&p,2).is_err());assert_eq!(p.control_children.lock()[0].carrier,800);assert_ne!(p.control_children.lock()[0].carrier_capsule,0);assert!(c.fork_parent.lock().is_some());assert_eq!(MODULE_RELEASES.load(Ordering::SeqCst),0);MODE.store(2,Ordering::SeqCst);assert_eq!(call(&p,2),Err(EBUSY));assert_eq!(p.control_children.lock()[0].carrier,800);
   // A fully transferred error is retained by the adapter. Test teardown alone
   // releases its module; this is not a production ACK/release claim.
   if mode==5{let held=pending().lock().take().unwrap();unsafe{(held.release)(held.owner as *mut c_void)};}
  }
 }
 #[test] fn rollback_inconsistent_success_or_mutated_call_retains_key(){
  for mode in [6,7]{let(p,c)=pair();MODE.store(mode,Ordering::SeqCst);assert_eq!(call(&p,2),Err(errno(-71)));assert_eq!(p.control_children.lock()[0].carrier,800);assert!(c.fork_parent.lock().is_some());assert_eq!(MODULE_RELEASES.load(Ordering::SeqCst),1);}
 }
 #[test] fn rollback_exact_attempt_parent_child_epoch_capsule_refusals(){
  for changed in 0..6{let(p,c)=pair();let mut witness=p.bind_fork_carrier(&c,800,1234).unwrap();match changed{0=>witness.parent+=1,1=>witness.child=Registration::new(20,201),2=>witness.carrier+=8,3=>witness.capsule+=1,4=>witness.response+=1,_=>witness.nonce+=1};assert_eq!(p.cancel_untransferred_fork_carrier(witness),Err(EACCES));let rows=p.control_children.lock();assert_eq!(rows[0].carrier,800);assert_eq!(rows[0].carrier_capsule,1234);}
 }
 #[test] fn rollback_stale_attempt_cannot_cancel_rebound_identical_carrier(){
  let(p,c)=pair();let first=p.bind_fork_carrier(&c,800,1234).unwrap();
  // Preserve stale metadata in this private test to model an ABA/refusal probe;
  // production witnesses are move-only and cannot be duplicated by callers.
  let stale=ForkCarrierBinding{parent:first.parent,child:c.clone(),carrier:first.carrier,capsule:first.capsule,response:first.response,nonce:first.nonce};
  p.cancel_untransferred_fork_carrier(first).unwrap();let second=p.bind_fork_carrier(&c,800,1235).unwrap();assert_eq!(p.cancel_untransferred_fork_carrier(stale),Err(EACCES));assert_eq!(p.control_children.lock()[0].carrier_capsule,1235);p.cancel_untransferred_fork_carrier(second).unwrap();assert_eq!(p.control_children.lock()[0].carrier,0);
 }
 #[test] fn rollback_concurrent_duplicate_refuses_then_original_retry_succeeds(){
  let(p,c)=pair();let arrived=Arc::new(std::sync::Barrier::new(2));let resume=Arc::new(std::sync::Barrier::new(2));*blocked().lock()=Some((arrived.clone(),resume.clone()));MODE.store(8,Ordering::SeqCst);
  let owner=p.clone();let job=std::thread::spawn(move||call(&owner,2));arrived.wait();MODE.store(0,Ordering::SeqCst);assert_eq!(call(&p,2),Err(EBUSY));assert_eq!(call(&p,3),Err(errno(-5)));assert_eq!(p.control_children.lock()[0].carrier,800);resume.wait();assert_eq!(job.join().unwrap(),Err(errno(-5)));assert_eq!(p.control_children.lock()[0].carrier,0);*blocked().lock()=None;
  MODE.store(2,Ordering::SeqCst);assert_eq!(call(&p,2),Ok(()));assert_eq!(call(&p,3),Ok(()));assert!(!c.armed.load(Ordering::Acquire));
 }
 #[test] fn rollback_zero_capsule_and_other_live_carrier_never_overwrite(){
  let(p,c)=pair();assert!(p.bind_fork_carrier(&c,800,0).is_err());assert_eq!(p.control_children.lock()[0].carrier,0);let held=p.bind_fork_carrier(&c,800,1234).unwrap();let d=Registration::new(21,201);d.reserve_fork_pair(&p,&proof(&d)).unwrap();assert!(p.bind_fork_carrier(&d,800,1235).is_err());assert_eq!(p.control_children.lock()[1].carrier,0);p.cancel_untransferred_fork_carrier(held).unwrap();assert_eq!(p.control_children.lock()[0].carrier,0);
 }
}
