
#[cfg(test)]
pub(crate) mod control_adapter {
    use super::*;
    use crate::abi::{SyscallRequest,SyscallResponse};
    use std::sync::atomic::{AtomicI32,Ordering};
    pub(crate) static MODE:AtomicI32=AtomicI32::new(0);
    pub(crate) unsafe fn transport(request:*mut SyscallRequest,cpu:i32)->i64 {
        assert_eq!((*request).args[0],2);
        let mut handles=[Handle::EMPTY;registry::CAPACITY];registry::snapshot_handles(&mut handles);
        let handle=handles.into_iter().find(|h|h.epoch!=0 && registry::visit(*h,|p|
            i32::from(p.as_ref().control.request==request as usize))==1).expect("actual owned control request");
        assert_eq!(registry::visit(handle,|p|{
            let c=p.as_ref();let slot=c.control.owned_request.as_ref().expect("control storage owned before offload");
            assert_eq!(slot.request.as_ptr(),request);assert_ne!(request as usize,c.request);
            assert_eq!((*request).args,c.control.args);assert_eq!(c.control.state,super::super::PENDING);
            assert!(c.owned_credits.is_some());assert!(c.owned_request.is_some());0
        }),0);
        let mode=MODE.load(Ordering::SeqCst);
        if mode==1{return -5;}if mode==2{return 0;}
        let thread=(*crate::cls::get_this_cpu_local_var()).current;
        (*request).rtid=(*thread).tid;(*request).ttid=0;(*request).valid=0;
        let mut response:SyscallResponse=core::mem::zeroed();
        response.ret=0;response.stid=31;response.status=1;
        let physical=&mut response as *mut _ as u64;
        assert_eq!(registry::visit(handle,|mut p|{
            let c=p.as_mut();let frame=&mut c.bytes;let id=c.identity;
            frame.fill(0);frame[..8].copy_from_slice(b"MCFKR001");
            for(at,value)in[(8,2),(16,18),(24,19),(32,physical),(48,id.generation),
                (56,id.parent),(64,id.worker),(72,id.delivery),(80,id.child),(88,id.child_mm),
                (96,id.root),(104,id.start),(112,id.length),(120,id.nonce)]{
                super::super::put(frame,at,value);
            }
            frame[40..44].copy_from_slice(&id.slot.to_le_bytes());
            frame[44..48].copy_from_slice(&id.child_pid.to_le_bytes());
            if mode==4{super::super::put(frame,64,id.worker+1);}0
        }),0);
        super::super::observe_fork_control_reply(request,&mut response,cpu,thread);0
    }
}
