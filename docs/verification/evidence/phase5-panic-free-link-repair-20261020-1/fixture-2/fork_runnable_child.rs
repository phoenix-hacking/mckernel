//! Existing nr56/selector1 host-child start, followed by the existing guest
//! scheduler lifecycle. No revoke/destruction permit is inferred from RET0.
use super::*;

pub(super) struct StartPending {
    owned_request:Option<ControlRequestSlot>,request:usize,thread:usize,cpu:i32,
    args:[u64;6],state:u32,error:i32,response:u64,stid:i32,
}
impl StartPending {
    pub(super) const ZERO:Self=Self{owned_request:None,request:0,thread:0,cpu:-1,
        args:[0;6],state:IDLE,error:0,response:0,stid:0};
    pub(super) fn completed(&self)->bool{
        self.state==OBSERVED&&self.response!=0&&self.stid>0&&self.owned_request.is_some()
    }
    pub(super) unsafe fn free_after_ack(&mut self){
        // The terminal consumer validates completed() before destruction.
        if let Some(slot)=self.owned_request.take(){slot.free_completed();}
    }
}

#[derive(Clone,Copy)]
pub(super) struct RunOptions{pub(super) flags:i32,pub(super) parent_cpu:i32,pub(super) child_tid:u64}

/// Support ordinary fork and the exact retained native libc-fork producer.
/// Refuse other flags rather than silently omit their ABI effects.
/// This does not silently omit ptrace, CLONE_PARENT/PARENT_SETTID/SETTLS or
/// remote-spawn semantics.
pub(super) unsafe fn admit(parent:*mut Thread,child:*mut Thread,options:RunOptions)->i32 {
    let flags=options.flags;
    if parent.is_null()||child.is_null()||options.parent_cpu<0
        ||(flags!=17&&!(flags==0x01200011&&cfg!(native_linux_irq_work_v6_12))){return EINVAL;}
    let local=crate::cls::get_this_cpu_local_var();
    if local.is_null()||(*local).current!=parent||(*parent).proc.is_null()
        ||(*child).uctx.is_null()||(*parent).ptrace!=0||(*parent).mod_clone!=0
        ||!(*parent).mod_clone_arg.is_null()||!(*(*parent).proc).monitoring_event.is_null()
    {return EACCES;}
    0
}

pub(super) unsafe fn observe_start(c:&mut Carrier,context:&ReplyContext)->i32 {
    if c.host_start.state!=PENDING||c.host_start.request!=context.request as usize
        ||c.host_start.thread!=context.thread as usize{return 0;}
    let request=&*context.request;let response=&*context.response;
    let physical=crate::x86_memory_helpers::virt_to_phys(context.response.cast::<c_void>())as u64;
    let end=physical.checked_add(size_of::<SyscallResponse>()as u64);
    let carrier_end=c.physical.checked_add(128);
    let disjoint=match (end,carrier_end){
        (Some(end),Some(carrier_end))=>!(physical<carrier_end&&c.physical<end),
        _=>false,
    };
    let frame=snapshot(c);
    let valid=c.phase==FIRST_POSITIVE&&c.error==0&&c.parent==context.thread as usize
        &&request.number==NR_CLONE&&request.args==c.host_start.args&&request.args[0]==1
        &&request.args[1]==c.identity.child_pid as u64&&request.args[4]==c.physical
        &&request.args[5]==MARKER&&request.rtid==(*context.thread).tid&&request.rtid>0
        &&request.ttid==0&&request.valid==0&&context.cpu==c.host_start.cpu&&context.cpu>=0
        &&physical!=0&&physical%8==0&&response.stid>0
        &&crate::x86_cpu_helpers::smp_load_acquire_ulong(addr_of!(response.status))==1
        &&disjoint
        &&crate::x86_memory_helpers::virt_to_phys(addr_of_mut!(c.bytes).cast::<c_void>())as u64==c.physical
        &&frame[..8]==*b"MCFKW001"&&word(&frame,24)==1
        &&word(&frame,32)==c.identity.child_pid as u64&&key(&frame)==c.identity
        &&carrier_geometry(c,&c.identity);
    let error=if !valid{EACCES}else if response.ret!=0{transport_error(response.ret)}else{0};
    if error!=0{c.host_start.error=error;c.host_start.state=RETAINED;c.error=error;c.phase=RETAINED;return error;}
    c.host_start.response=physical;c.host_start.stid=response.stid;c.host_start.state=OBSERVED;1
}

struct StartGuard{handle:Handle,armed:bool}
impl Drop for StartGuard {
    fn drop(&mut self){if !self.armed{return;}
        unsafe{let _=registry::visit(self.handle,|pointer|{let c=&mut*pointer.as_ptr();
            if c.host_start.state==PENDING{c.host_start.state=RETAINED;c.host_start.error=EIO;c.phase=RETAINED;}0});}
        let _=registry::retain(self.handle);
    }
}

unsafe fn submit_start(handle:Handle)->i32 {
    let local=crate::cls::get_this_cpu_local_var();if local.is_null(){return EACCES;}
    let parent=(*local).current;if parent.is_null(){return EACCES;}let cpu=(*parent).cpu_id;
    let slot=match ControlRequestSlot::allocate(){Ok(slot)=>slot,Err(error)=>return error};
    let request=slot.request;let mut slot=Some(slot);
    let prepared=registry::visit(handle,|pointer|{let c=&mut*pointer.as_ptr();
        if c.handle!=handle||c.phase!=FIRST_POSITIVE||c.error!=0||c.parent!=parent as usize
            ||c.host_start.state!=IDLE||!carrier_geometry(c,&c.identity){return EACCES;}
        (*request.as_ptr()).args=[1,c.identity.child_pid as u64,c.length,c.root,c.physical,MARKER];
        c.host_start=StartPending{owned_request:slot.take(),request:request.as_ptr()as usize,
            thread:parent as usize,cpu,args:(*request.as_ptr()).args,state:PENDING,
            error:0,response:0,stid:0};0
    });
    if prepared!=0{if let Some(slot)=slot{slot.free_private();}return prepared;}
    let mut guard=StartGuard{handle,armed:true};
    // Registry owns the exact request before the synchronous transport. The
    // actual outer wait must observe this same Response, not a scalar replay.
    let actual=do_syscall(request.as_ptr(),cpu);
    let result=registry::visit(handle,|pointer|{let c=&mut*pointer.as_ptr();
        if actual!=0{return transport_error(actual);}
        if c.phase!=FIRST_POSITIVE||c.error!=0||c.host_start.state!=OBSERVED
            ||c.host_start.request!=request.as_ptr()as usize||c.host_start.thread!=parent as usize
            ||c.host_start.cpu!=cpu||c.host_start.response==0||c.host_start.stid<=0
            ||c.host_start.owned_request.as_ref().is_none_or(|slot|slot.request!=request)
        {return if c.host_start.error!=0{c.host_start.error}else{EIO};}
        c.phase=HOST_STARTED;0
    });
    if result==0{guard.armed=false;}result
}

/// The returned PID is produced only after the actual selector1 response and
/// real runqueue insertion. A separate retained Thread pin prevents exit/wait
/// from invalidating the registry's storage. It is deliberately not released
/// by phase4's pre-publication destructor/ACK route.
pub(super) unsafe fn start_and_publish(handle:Handle,options:RunOptions)->i32 {
    let started=submit_start(handle);if started!=0{return started;}
    let mut permit=None;let mut pid=0;
    let prepared=registry::visit(handle,|pointer|{let c=&mut*pointer.as_ptr();
        if c.phase!=HOST_STARTED||c.error!=0||c.host_start.state!=OBSERVED{return EACCES;}
        let admitted=admit(c.parent as *mut Thread,c.child as *mut Thread,options);
        if admitted!=0{return admitted;}
        let Some(credits)=c.owned_credits.as_mut()else{return EACCES;};
        let bound=registry::bind_runtime_exit(handle,c.child);
        if bound!=0{return bound;}
        match credits.prepare_runtime(){Ok(owner)=>{permit=Some(owner);pid=c.identity.child_pid;c.runtime_committed=true;c.phase=RUNTIME_PUBLISHING;0},Err(error)=>error}
    });
    if prepared!=0{return prepared;}
    // No registry/publication/MM lock is held across lifecycle callbacks.
    let Some(permit)=permit else{
        let _=registry::visit(handle,|pointer|{let c=&mut*pointer.as_ptr();c.phase=RETAINED;c.error=EIO;0});
        let _=registry::retain(handle);return EIO;
    };
    let published=permit.publish(pid,options.parent_cpu,options.flags,options.child_tid);
    let _=registry::visit(handle,|pointer|{let c=&mut*pointer.as_ptr();
        if published==0{c.runtime_publish_completed=true;if c.phase==RUNTIME_PUBLISHING{c.phase=RUNTIME_PUBLISHED;}}
        else{c.phase=RETAINED;c.error=published;}0});
    if published==0{let _=process_fork_runtime_drain_current_v1();pid}else{published}
}

/// Called only by the real wait-zombie body after its actual host wait4 result,
/// with the parent's children lock held. This metadata CAS removes the normal
/// wait obligation once; no release callback runs under the registry lock.
#[derive(Clone,Copy)]
pub(crate) enum WaitReap {Ordinary,Retained(i32),Prepared(Handle)}
pub(crate) unsafe fn prepare_wait_reap(thread:*mut Thread,parent:*mut crate::abi::Process,
    child:*mut crate::abi::Process,pid:i32,options:i32,actual:i32)->WaitReap {
    if pid<=0||thread.is_null()||parent.is_null()||child.is_null()
        ||crate::syscall_policy::wait_reap_needed_result(options)==0{return WaitReap::Ordinary;}
    let local=crate::cls::get_this_cpu_local_var();
    if local.is_null()||(*local).current!=thread||(*thread).proc!=parent{return WaitReap::Ordinary;}
    let mut handles=[Handle::EMPTY;registry::CAPACITY];registry::snapshot_handles(&mut handles);
    for handle in handles{if handle.epoch==0{continue;}
        let mut matched=false;
        let found=registry::visit(handle,|pointer|{let c=&mut*pointer.as_ptr();
            if !c.runtime_committed
                ||c.identity.child_pid!=pid||c.host_start.state!=OBSERVED{return 0;}
            let Some(credits)=c.owned_credits.as_ref()else{return 0;};
            // The additional Thread pin keeps these exact allocations live.
            // Do not inspect/mutate the graph while publish() may own it.
            if !credits.runtime_processes_match(parent,child)
                ||(*child).pid!=pid||(*child).status!=8{return 0;}
            matched=true;
            if c.error!=0{return c.error;}
            if !matches!(c.phase,RUNTIME_PUBLISHING|RUNTIME_PUBLISHED){return EBUSY;}
            if actual!=pid{let error=if actual<0{actual}else{EIO};c.phase=RETAINED;c.error=error;return error;}
            c.phase=WAIT_REAP_PENDING;1
        });
        if found==1{return WaitReap::Prepared(handle);}
        // A busy ownership visitor cannot authorize falling through to the
        // generic destructive reap. Refuse without consuming any wait edge.
        if found<0&&(matched||found==EBUSY){return WaitReap::Retained(found);}
    }
    WaitReap::Ordinary
}

pub(crate) unsafe fn finish_wait_reap(handle:Handle,error:i32){
    let _=registry::visit(handle,|pointer|{let c=&mut*pointer.as_ptr();
        if c.phase!=WAIT_REAP_PENDING{return EACCES;}
        if error==0{c.runtime_wait_reaped=true;c.phase=WAIT_REAPED;}else{c.phase=RETAINED;c.error=error;}0});
    // The caller has released the actual parent/children/hash locks. If the
    // scheduler event is later, the next real syscall entry retries in the
    // original parent context. Neither wait nor its return implies quiescence.
    let _=process_fork_runtime_drain_current_v1();
}

pub(super) unsafe fn runtime_retirement_ready(c:&Carrier)->bool{
    let local=crate::cls::get_this_cpu_local_var();
    if local.is_null()||(*local).current as usize!=c.parent{return false;}
    let parent=(*local).current;
    if parent.is_null()||(*parent).proc.is_null()
        ||(*parent).status&(8|16)!=0||(*(*parent).proc).status&(8|16)!=0
        ||crate::x86_cpu_helpers::cpu_interrupt_disabled()!=0{return false;}
    c.runtime_committed&&c.runtime_publish_completed&&c.runtime_wait_reaped&&c.error==0&&c.host_start.completed()
        &&registry::runtime_exit_observed(c.handle,c.child)==Ok(true)
        &&carrier_geometry(c,&c.identity)
}

/// Called at a real current-parent syscall entry, and after the unlocked
/// successful wait commit. One bounded pass, no scheduler-context offload,
/// no spinning on busy visitors, and no change to the original syscall result.
#[no_mangle]
pub(crate) unsafe extern "C" fn process_fork_runtime_drain_current_v1()->i32{
    let local=crate::cls::get_this_cpu_local_var();if local.is_null(){return EACCES;}
    let parent=(*local).current;
    // Real process.h defines PS_ZOMBIE=8, PS_EXITED=16. The original storage
    // pin is not permission to run a transaction after either exit frontier.
    if parent.is_null()||(*parent).proc.is_null()
        ||(*parent).status&(8|16)!=0||(*(*parent).proc).status&(8|16)!=0
        ||crate::x86_cpu_helpers::cpu_interrupt_disabled()!=0{return EACCES;}
    let _active=match registry::claim_parent_drain(parent as usize){Ok(active)=>active,Err(error)=>return error};
    let mut handles=[Handle::EMPTY;registry::CAPACITY];registry::snapshot_handles(&mut handles);
    let mut completed=0;
    for handle in handles{if handle.epoch==0{continue;}
        let ready=registry::visit(handle,|pointer|{let c=&*pointer.as_ptr();
            if c.parent==parent as usize&&c.phase==WAIT_REAPED&&c.control.state==IDLE
                &&runtime_retirement_ready(c){1}else{0}});
        if ready!=1{continue;}
        let mut observed=ControlObservation::ZERO;
        if submit_control_current(handle,&mut observed,true)!=0{continue;}
        if destroy_and_ack_current(handle)==0{completed+=1;}
    }
    completed
}

#[cfg(test)]pub(crate) unsafe fn fixture_publication_pending(mut c:core::ptr::NonNull<super::Carrier>){c.as_mut().runtime_publish_completed=false;}
