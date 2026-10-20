// SPDX-License-Identifier: GPL-2.0
//! The actual current selector2/3 consumer. All MM/foreign callbacks run after
//! releasing Remote::slots; uncertain work keeps the same owned capsule.
use super::*;
use super::super::application_abi::{ForkControlCallV1,ForkControlIdentityV1,ForkRevokeClaimV1};

#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(super) enum ControlPhase {Idle,Revoking,Revoked,AckPending,AckPublished,Retained}
/// No implicit foreign Drop: an error after transfer retains the capsule.
pub(super) struct OwnedRevoke {
    owner:*mut core::ffi::c_void,
    revoke:super::super::application_abi::ForkRevokeV1,
    accept:super::super::application_abi::ForkAcceptV1,
    release:super::super::application_abi::ForkLeaseReleaseV4,
    phase:ControlPhase,epoch:u64,worker:u64,delivery:u64,response:u64,
}
unsafe impl Send for OwnedRevoke {}
unsafe impl Sync for OwnedRevoke {}
impl OwnedRevoke {
    fn take(call:&mut ForkControlCallV1)->Result<Self> {
        let(revoke,accept,release)=(call.revoke.ok_or(EINVAL)?,call.accept.ok_or(EINVAL)?,call.release.ok_or(EINVAL)?);
        if call.owner.is_null(){return Err(EINVAL);}
        let owner=call.owner;call.owner=core::ptr::null_mut();call.revoke=None;call.accept=None;call.release=None;
        Ok(Self{owner,revoke,accept,release,phase:ControlPhase::Idle,epoch:0,worker:0,delivery:0,response:0})
    }
    unsafe fn release_after_ack(self){debug_assert_eq!(self.phase,ControlPhase::AckPublished);unsafe {(self.release)(self.owner)};}
}
fn identity(owner:&PreparedForkIngress,image:&InheritedRoot,slot:u32,generation:u64)->ForkControlIdentityV1 {
    let(worker,delivery)=owner.response.route();
    ForkControlIdentityV1{slot,child_pid:owner.child_task.tgid(),generation,parent:owner.parent.wire(),worker,
        delivery,child:owner.child.wire(),child_mm:owner.child_task.identity(),root:image.root,start:image.start,
        length:image.end-image.start,nonce:owner.carrier_nonce}
}
fn packed_identity(frame:&mut[u8;128],key:&ForkControlIdentityV1){
    frame[40..44].copy_from_slice(&key.slot.to_le_bytes());frame[44..48].copy_from_slice(&key.child_pid.to_le_bytes());
    for(at,value)in[(48,key.generation),(56,key.parent),(64,key.worker),(72,key.delivery),(80,key.child),
        (88,key.child_mm),(96,key.root),(104,key.start),(112,key.length),(120,key.nonce)]{
        frame[at..at+8].copy_from_slice(&value.to_le_bytes());
    }
}
fn matches_identity(frame:&[u8;128],key:&ForkControlIdentityV1)->bool{
    let mut expected=[0;128];packed_identity(&mut expected,key);frame[40..]==expected[40..]
}
fn word(frame:&[u8;128],at:usize)->u64{u64::from_le_bytes(frame[at..at+8].try_into().unwrap())}
fn control_frame(magic:&[u8;8],key:&ForkControlIdentityV1,epoch:u64,worker:u64,delivery:u64,response:u64)->[u8;128]{
    let mut frame=[0;128];frame[..8].copy_from_slice(magic);
    for(at,value)in[(8,epoch),(16,worker),(24,delivery),(32,response)]{frame[at..at+8].copy_from_slice(&value.to_le_bytes());}
    packed_identity(&mut frame,key);frame
}
impl Remote {
    pub(crate) unsafe fn fork_control_current(&self,parent:Token,child:Token,call:&mut ForkControlCallV1)->Result {
        if parent==child||call.worker==0||call.delivery==0{return Err(EINVAL);}
        let worker=call.worker;let serial=call.delivery;
        let(mut slots,request,key,claim,selector,capsule)={
            let mut slots=self.slots.lock();
            let p=slots.iter().position(|e|e.as_ref().is_some_and(|e|e.key()==parent)).ok_or(ENOENT)?;
            let c=slots.iter().position(|e|e.as_ref().is_some_and(|e|e.key()==child)).ok_or(ENOENT)?;
            if p==c{return Err(EINVAL);}
            let pe=slots[p].as_ref().unwrap();let ce=slots[c].as_ref().unwrap();
            if pe.closed||pe.needs_cleanup||pe.quarantined||ce.closed||ce.needs_cleanup||ce.quarantined{return Err(EBUSY);}
            let owner=ce.fork_ingress.as_ref().ok_or(EACCES)?;let image=ce.inherited_root.as_ref().ok_or(EACCES)?;
            if owner.parent!=parent||owner.child!=child||!owner.sealed.load(Ordering::Acquire)
                ||!owner.first_return_published{return Err(EACCES);}
            let key=identity(owner,image,self.owner.slot(),self.owner.generation());
            let original=owner.response.request().clone();let carrier=original.arguments()[4];let cpu=original.cpu();
            // Reservation is matched to this exact owned parent and actual
            // worker. No current user pointer or claimed MM creates authority.
            let request=slots[p].as_mut().unwrap().syscalls.begin_kernel(worker,serial).map_err(errno)?;
            let args=request.arguments();let selector=args[0];
            // This closure has no foreign callback or write/publication. All
            // errors precede OwnedRevoke::take (which itself fails only before
            // transfer), or selector3's phase transition. Keep this exact slots
            // guard throughout admission, validation and any rollback.
            let capsule=(||->Result<_>{
                if request.number()!=56||request.cpu()!=cpu||request.requester()!=original.requester()
                    ||request.target()!=0||args[2]!=key.length||args[3]!=key.root||args[4]!=carrier
                    ||args[5]!=0x313030434b46434d||!matches!(selector,2|3)
                    ||(selector==2&&args[1]!=key.child_pid as u64)||(selector==3&&args[1]!=2){return Err(EACCES);}
                let frame=slots[p].as_mut().unwrap().syscalls.with_kernel_memory(worker,serial,|r,m|
                    m.current_fork_control_frame(r).map_err(|e|e.to_errno())).map_err(errno)?;
                if !matches_identity(&frame,&key){return Err(EACCES);}
                let owner=slots[c].as_mut().unwrap().fork_ingress.as_mut().unwrap();
                if selector==2 {
                    if owner.host_revoke.is_some()||frame[..8]!=*b"MCFKW001"||frame[8..12]!=[1,0,40,0]
                        ||frame[12..16]!=128u32.to_le_bytes()||frame[16..20]!=1u32.to_le_bytes()
                        ||frame[20..24]!=[0;4]||word(&frame,24)!=1||word(&frame,32)!=key.child_pid as u64{return Err(EACCES);}
                    let mut host=OwnedRevoke::take(call)?;host.phase=ControlPhase::Revoking;
                    let capsule=(host.owner,host.revoke,host.accept);owner.host_revoke=Some(host);Ok(capsule)
                }else{
                    if !call.owner.is_null()||call.revoke.is_some()||call.accept.is_some()||call.release.is_some(){return Err(EINVAL);}
                    let host=owner.host_revoke.as_mut().ok_or(EACCES)?;
                    if host.phase!=ControlPhase::Revoked||frame[..8]!=*b"MCFKD001"||word(&frame,8)!=host.epoch
                        ||word(&frame,16)!=host.worker||word(&frame,24)!=host.delivery||word(&frame,32)!=host.response{return Err(EACCES);}
                    host.phase=ControlPhase::AckPending;Ok((host.owner,host.revoke,host.accept))
                }
            })();
            let capsule=match capsule {
                Ok(capsule)=>capsule,
                Err(error)=>{
                    slots[p].as_mut().unwrap().syscalls
                        .rollback_fork_kernel_admission(worker,serial,&request).map_err(errno)?;
                    return Err(error);
                }
            };
            let claim=ForkRevokeClaimV1{identity:key,carrier};
            (slots,request,key,claim,selector,capsule)
        };
        // Exact provider owner and child pins exclude movement/removal; only
        // this monotonic transaction may invoke the transferred capsule.
        drop(slots);
        let status=if selector==2 {unsafe {(capsule.1)(capsule.0,&claim)}}else{unsafe {(capsule.2)(capsule.0)}};
        slots=self.slots.lock();
        let c=slots.iter().position(|e|e.as_ref().is_some_and(|e|e.key()==child)).ok_or(ENOENT)?;
        let p=slots.iter().position(|e|e.as_ref().is_some_and(|e|e.key()==parent)).ok_or(ENOENT)?;
        let owner=slots[c].as_mut().unwrap().fork_ingress.as_mut().ok_or(EACCES)?;
        let host=owner.host_revoke.as_mut().ok_or(EACCES)?;
        if status!=0 {host.phase=ControlPhase::Retained;return Err(errno(if status<0&&status>= -4095{status}else{-71}));}
        if selector==2 {
            if host.phase!=ControlPhase::Revoking{return Err(EACCES);}
            host.phase=ControlPhase::Revoked;host.epoch=serial;host.worker=worker;host.delivery=serial;host.response=request.response();
        }else if host.phase!=ControlPhase::AckPending{return Err(EACCES);}
        let mut frame=control_frame(if selector==2{b"MCFKR001"}else{b"MCFKA001"},&key,host.epoch,worker,serial,request.response());
        slots[p].as_mut().unwrap().syscalls.finish_fork_kernel_retained(worker,serial,|_,memory|{
            memory.write_fork_control_frame(&mut frame).map_err(|e|e.to_errno())?;Ok(0)
        }).map_err(errno)?;
        self.changed.notify_all();
        // Once committed the continuing publisher owns the same real Response.
        // Interrupts cannot turn uncertain publication into a release permit.
        loop {
            let pe=slots[p].as_ref().ok_or(ENOENT)?;
            if pe.quarantined{return Err(errno(-71));}
            if pe.syscalls.returned(worker,serial).map_err(errno)?{break;}
            self.changed.wait(&mut slots);
        }
        if selector==2{return Ok(());}
        let ce=slots[c].as_mut().ok_or(ENOENT)?;
        let mut owner=ce.fork_ingress.take().ok_or(EACCES)?;
        owner.host_revoke.as_mut().unwrap().phase=ControlPhase::AckPublished;
        ce.inherited_root=None;ce.closed=true;
        if let Some(procfs)=&ce.procfs{procfs.close();}
        // Guest destruction is already authenticated; closing worker admission
        // is not its evidence. Any cancellation uncertainty retains the owner.
        if let Err(error)=ce.syscalls.close(){ce.quarantined=true;ce.fork_ingress=Some(owner);return Err(errno(error));}
        ce.parent_slot_pins-=1;
        slots[p].as_mut().unwrap().parent_slot_pins-=1;owner.finished=true;
        drop(slots);self.changed.notify_all();
        // All foreign/task/MM/lease destruction is after provider, publication
        // and Linux MM locks, and after the actual final ACK status publication.
        let host=owner.host_revoke.take().unwrap();unsafe {host.release_after_ack()};
        unsafe {
            core::mem::ManuallyDrop::drop(&mut owner.lease);
            core::mem::ManuallyDrop::drop(&mut owner.child_task);
            core::mem::ManuallyDrop::drop(&mut owner.response);
            core::mem::ManuallyDrop::drop(&mut owner.remote);
        }
        Ok(())
    }
}

impl OwnedRevoke { pub(super) fn fixture_phase(&self)->ControlPhase {self.phase} }
