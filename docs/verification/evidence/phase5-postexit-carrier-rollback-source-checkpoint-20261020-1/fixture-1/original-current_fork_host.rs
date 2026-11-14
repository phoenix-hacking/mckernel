// SPDX-License-Identifier: GPL-2.0
//! Paired current connections and the actual owned Linux MM revoke capsule.
use super::*;
use super::super::application_abi::{ForkControlCallV1,ForkRevokeClaimV1,ForkPreparedV3,ForkGeometryV3};
// A zero carrier is private pending state, never a lookup key. The row is
// minted only by the authenticated v4 adoption callback before any MM effect.
pub(super) struct ForkChildRoute {
    carrier:u64,child:Arc<Registration>,geometry:ForkGeometryV3,
    child_mm:u64,response:u64,nonce:u64,
}
impl ForkChildRoute {
    fn matches(&self,child:&Arc<Registration>,proof:&ForkPreparedV3)->bool {
        Arc::ptr_eq(&self.child,child)&&self.geometry==proof.geometry
            &&self.child.pid==proof.child_pid&&self.child_mm==proof.child_mm
            &&self.response==proof.response&&self.nonce==proof.nonce
    }
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
        children.push(ForkChildRoute{carrier:0,child:self.clone(),geometry:proof.geometry,
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
    fn bind_fork_carrier(&self,child:&Arc<Self>,carrier:u64)->Result {
        let mut children=self.control_children.lock();
        if carrier==0||children.iter().any(|row|row.carrier==carrier){return Err(EBUSY);}
        let row=children.iter_mut().find(|row|Arc::ptr_eq(&row.child,child)&&row.carrier==0).ok_or(EACCES)?;
        row.carrier=carrier;Ok(())
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
        let mut original=ptr::null_mut();
        if selector==2 {
            let mirror=child.mapping.lock().clone().ok_or(EACCES)?;
            let module=super::super::mcctrl_vm::DeferredModule::acquire()?;
            let owner=Box::new(HostRevoke{child:child.clone(),mirror,revoked:AtomicBool::new(false),_module:module},GFP_KERNEL)?;
            original=Box::into_raw(owner).cast();call.owner=original;
            call.revoke=Some(revoke);call.accept=Some(accept);call.release=Some(release);
            // Bind only this authenticated adoption's existing owned row.
            // Failure/uncertain provider publication keeps the pair and key.
            if let Err(error)=self.bind_fork_carrier(&child,carrier){unsafe {release(original)};return Err(error);}
        }
        let status=unsafe {ihk_os_application_fork_control_current_v1(self.context.as_ptr(),child.context.as_ptr(),&mut call)};
        if !original.is_null()&&call.owner==original&&call.revoke.map(|f|f as usize)==Some(revoke as usize)
            &&call.accept.map(|f|f as usize)==Some(accept as usize)&&call.release.map(|f|f as usize)==Some(release as usize){
            // No transfer/effect occurred. Balance the actual original box.
            unsafe {release(original)};
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

#[cfg(test)] mod original_witness {
 use super::*;
 #[test] fn original_intact_negative_capsule_poisoned_corrected_retry(){
  table().lock().clear();MODE.store(0,Ordering::SeqCst);let p=Registration::new(10,100);let c=Registration::new(20,200);
  let proof=ForkPreparedV3{geometry:ForkGeometryV3{root:4096,start:8192,length:12288},child_pid:20,reserved:0,child_mm:400,response:500,nonce:600};c.reserve_fork_pair(&p,&proof).unwrap();
  let mut bytes=[0;96];for(at,v)in[(8,91u64),(48,2),(56,20),(64,12288),(72,4096),(80,800)]{bytes[at..at+8].copy_from_slice(&v.to_le_bytes())}
  assert_eq!(p.fork_control_current(&HostWorker{handle:1},&bytes),Err(errno(-5)));assert_eq!(p.control_children.lock()[0].carrier,800);
  MODE.store(2,Ordering::SeqCst);assert_eq!(p.fork_control_current(&HostWorker{handle:1},&bytes),Err(EBUSY));assert_eq!(p.control_children.lock()[0].carrier,800);
  println!("ORIGINAL: intact negative capsule return left carrier 800; corrected actual caller refused EBUSY before provider");
 }
}
