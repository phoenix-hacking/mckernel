// SPDX-License-Identifier: GPL-2.0
//! Paired current connections and the actual owned Linux MM revoke capsule.
use super::*;
use super::super::application_abi::{ForkControlCallV1,ForkRevokeClaimV1};
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
    pub(super) fn fork_control_current(&self,worker:&HostWorker,bytes:&[u8;96])->Result {
        let word=|at|u64::from_le_bytes(bytes[at..at+8].try_into().unwrap());
        let selector=word(48);let serial=word(8);let carrier=word(80);
        if carrier==0||carrier%8!=0||carrier.checked_add(128).is_none(){return Err(EINVAL);}
        let child=if selector==2 {
            let pid=i32::try_from(word(56)).map_err(|_|EINVAL)?;
            if pid<=0{return Err(EINVAL);}
            // This lookup acquires a real owner only. The paired IHK/provider
            // route below must still authenticate its exact backend child.
            let process={let table=table().lock();table.iter().find(|entry|
                entry.process.slot==self.slot&&entry.process.generation==self.generation
                &&entry.process.pid.number().ok()==Some(pid)).map(|entry|entry.process.clone()).ok_or(ENOENT)?};
            let child=process.registration.lock().clone().ok_or(ENOENT)?;
            child
        }else if selector==3 {self.control_children.lock().iter().find(|(key,_)|*key==carrier)
            .map(|(_,child)|child.clone()).ok_or(EACCES)?}
        else{return Err(EINVAL);};
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
            // Reserve before any provider effect. The already allocated Vec
            // never grows beyond its 64-entry capacity. Holding a child Arc
            // grants no revoke/ACK right: paired IHK/provider auth follows.
            let reserved=(||->Result {
                let mut children=self.control_children.lock();
                if children.len()>=64||children.iter().any(|(key,_)|*key==carrier){return Err(EBUSY);}
                children.push((carrier,child.clone()),GFP_KERNEL)?;Ok(())
            })();
            if let Err(error)=reserved{unsafe {release(original)};return Err(error);}
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
                let index=children.iter().position(|(key,owner)|*key==carrier&&Arc::ptr_eq(owner,&child)).ok_or(EACCES)?;
                children.swap_remove(index)};
            drop(previous);
        }
        Ok(())
    }
}
