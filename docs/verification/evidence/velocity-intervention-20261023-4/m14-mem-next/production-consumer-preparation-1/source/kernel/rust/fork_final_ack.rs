//! Real post-revoke destructor and final selector3 producer. Every uncertain
//! path keeps constructor/CPU/parent/request owners; no Drop infers an ACK.
use super::*;

pub(super) unsafe fn destroy_and_ack_current(handle:Handle)->i32 {
    // This request allocation precedes every destructive guest effect.
    let slot=match ControlRequestSlot::allocate(){Ok(slot)=>slot,Err(error)=>return error};
    let request=slot.request;let mut slot=Some(slot);let mut permit=None;let mut runtime_permit=None;
    let mut runtime=false;let mut cpu=-1;let mut parent=0;
    let prepared=registry::visit(handle,|pointer|{
        let c=&mut*pointer.as_ptr();
        let cls=crate::cls::get_this_cpu_local_var();
        if cls.is_null()||(*cls).current as usize!=c.parent||c.phase!=HOST_REVOKED
            ||c.control.state!=OBSERVED||c.retired_control.is_some(){return EACCES;}
        let current=snapshot(c);
        match control_receipt(c,&current,c.revoke.response){
            Ok(observation)if observation.epoch==c.revoke.epoch&&observation.worker==c.revoke.worker
                &&observation.delivery==c.revoke.delivery=>{},_=>return EACCES,
        }
        runtime=c.runtime_committed;
        if runtime&&!runnable::runtime_retirement_ready(c){return EACCES;}
        let Some(credits)=c.owned_credits.as_mut()else{return EACCES;};
        if runtime{
            runtime_permit=match credits.prepare_runtime_retirement(){Ok(permit)=>Some(permit),Err(error)=>return error};
        }else{
            permit=match credits.prepare_revoked_destruction(){Ok(permit)=>Some(permit),Err(error)=>return error};
        }
        cpu=c.control.cpu;parent=c.parent;c.phase=DESTRUCTING;0
    });
    if prepared!=0 {if let Some(slot)=slot{slot.free_private();}return prepared;}
    // No registry lock or Carrier reference survives a destructive callback.
    let destroyed=if runtime{
        match runtime_permit.take(){Some(permit)=>Some(permit.destroy()),None=>None}
    }else{
        match permit.take(){Some(permit)=>Some(permit.destroy()),None=>None}
    };
    let Some(destroyed)=destroyed else{
        if let Some(slot)=slot{slot.free_private();}
        let _=registry::visit(handle,|pointer|{let c=&mut*pointer.as_ptr();c.phase=RETAINED;c.error=EIO;0});
        let _=registry::retain(handle);return EIO;
    };
    let rebound=registry::visit(handle,|pointer|{
        let c=&mut*pointer.as_ptr();
        if c.phase!=DESTRUCTING{return EACCES;}
        let Some(credits)=c.owned_credits.as_ref()else{return EACCES;};
        if destroyed.is_err(){c.phase=RETAINED;c.error=EBUSY;return EBUSY;}
        if !credits.retirement_complete(runtime){c.phase=RETAINED;return EBUSY;}
        if runtime&&!runnable::runtime_retirement_ready(c){c.phase=RETAINED;c.error=EACCES;return EACCES;}
        // The saved real revoke receipt binds nonce, original request/root,
        // opaque epoch and delivery. Only the checked graph can reach here.
        c.bytes[..8].copy_from_slice(b"MCFKD001");
        (*request.as_ptr()).args=[3,2,c.length,c.root,c.physical,MARKER];
        c.retired_control=c.control.owned_request.take();
        c.control=ControlPending{owned_request:slot.take(),request:request.as_ptr() as usize,
            thread:parent,cpu,args:(*request.as_ptr()).args,state:PENDING,error:0,
            observation:ControlObservation::ZERO};
        c.phase=GUEST_DESTROYED;0
    });
    if rebound!=0 {
        if let Some(slot)=slot{slot.free_private();}
        let _=registry::retain(handle);return rebound;
    }
    let mut guard=SubmitGuard{handle,armed:true};
    let actual=do_syscall(request.as_ptr(),cpu);
    let mut expected=None;
    let observed=registry::visit(handle,|pointer|{
        let c=&mut*pointer.as_ptr();
        if actual!=0{return transport_error(actual);}
        if c.phase!=FINAL_ACK||c.control.state!=OBSERVED||c.control.request!=request.as_ptr() as usize
            ||c.control.thread!=parent||c.control.cpu!=cpu
            ||c.control.owned_request.as_ref().is_none_or(|slot|slot.request!=request)
            ||c.owned_credits.as_ref().is_none_or(|credits|!credits.retirement_complete(runtime))
            ||(runtime&&!c.host_start.completed()){return EACCES;}
        expected=Some(pointer);0
    });
    if observed!=0{return observed;}
    let Some(expected)=expected else{let _=registry::retain(handle);return EIO;};
    let mut pointer=match registry::detach_terminal(handle,expected){
        Ok(pointer)=>pointer,Err(error)=>return error,
    };
    // No new observer can obtain a Carrier borrow; all three real calls have
    // acquired their actual completed Responses. Destruction is outside locks.
    let c=pointer.as_mut();let Some(credits)=c.owned_credits.take()else{
        // Detach already removed discovery. Keep this allocation and every
        // request; missing credits grant no destructor/free/positive return.
        c.phase=RETAINED;c.error=EIO;guard.armed=false;return EIO;
    };
    let released=if runtime{credits.release_runtime_after_ack()}else{credits.release_after_ack()};
    if let Err(credits)=released{c.owned_credits=Some(credits);guard.armed=false;return EBUSY;}
    if runtime{c.host_start.free_after_ack();}
    if let Some(slot)=c.owned_request.take(){slot.free_completed();}
    if let Some(slot)=c.retired_control.take(){slot.free_completed();}
    if let Some(slot)=c.control.owned_request.take(){slot.free_completed();}
    guard.armed=false;crate::mem_helpers::kfree(pointer.as_ptr().cast());0
}
