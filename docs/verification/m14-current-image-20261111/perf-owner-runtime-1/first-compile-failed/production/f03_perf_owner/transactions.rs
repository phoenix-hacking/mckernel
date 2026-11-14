// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// PRIVATE UNWIRED. Full genuine open transaction; no alternate host backend.
use core::ffi::c_void;
use core::mem::{size_of,align_of,offset_of,MaybeUninit};
use core::ptr::{addr_of_mut,null_mut,write_bytes};
use crate::abi::{CInt,CLong,CULong,SizeT,Process,Thread,Mckfd,SyscallRequest};
use super::super::{PerfOpenAllocEventFn,PerfCounterAllocFn,PerfOpenSyscallFn,SyscallPolicyAllocFn,
    SyscallMckfdLongFn,SyscallMckfdIntFn,SyscallMckfdLockFn,SyscallMckfdUnlockFn};
use super::super::f03_sync_child_layout_v2::FullMcPerfEvent as Event;
use super::events::{EventPin,DescriptorEvent,EventOrigins};
use super::groups::EventLayout;
use super::descriptors::{self,Locked,Prepared};
use super::maps::Plan;
const EINVAL:CInt=22;const ENOMEM:CInt=12;const EBADF:CInt=9;
#[derive(Clone,Copy)]
pub(crate) struct Open {
    pub(crate) request:*mut SyscallRequest,
    pub(crate) thread:*mut c_void,
    pub(crate) proc:*mut c_void,
    pub(crate) attr:*mut c_void,
    pub(crate) pid:CInt,
    pub(crate) group_fd:CInt,
    pub(crate) perf_event_open_nr:CInt,
    pub(crate) cpu:CInt,
    pub(crate) mckfd_size:SizeT,
    pub(crate) mckfd_alloc_flags:CULong,
    pub(crate) event_pid_offset:SizeT,
    pub(crate) event_counter_id_offset:SizeT,
    pub(crate) proc_mckfd_offset:SizeT,
    pub(crate) mckfd_next_offset:SizeT,
    pub(crate) mckfd_fd_offset:SizeT,
    pub(crate) mckfd_data_offset:SizeT,
    pub(crate) event_group_leader_offset:SizeT,
    pub(crate) event_sibling_list_offset:SizeT,
    pub(crate) event_group_entry_offset:SizeT,
    pub(crate) event_nr_siblings_offset:SizeT,
    pub(crate) event_pmc_status_offset:SizeT,
    pub(crate) thread_pmc_alloc_map_offset:SizeT,
    pub(crate) proc_mckfd_lock_offset:SizeT,
    pub(crate) mckfd_sig_no_offset:SizeT,
    pub(crate) mckfd_read_cb_offset:SizeT,
    pub(crate) mckfd_ioctl_cb_offset:SizeT,
    pub(crate) mckfd_mmap_cb_offset:SizeT,
    pub(crate) mckfd_close_cb_offset:SizeT,
    pub(crate) mckfd_fcntl_cb_offset:SizeT,
    pub(crate) event_alloc_fn:Option<PerfOpenAllocEventFn>,
    pub(crate) counter_alloc_fn:Option<PerfCounterAllocFn>,
    pub(crate) syscall_fn:Option<PerfOpenSyscallFn>,
    pub(crate) mckfd_alloc_fn:Option<SyscallPolicyAllocFn>,
    pub(crate) read_fn:Option<SyscallMckfdLongFn>,
    pub(crate) ioctl_fn:Option<SyscallMckfdIntFn>,
    pub(crate) mmap_fn:Option<SyscallMckfdLongFn>,
    pub(crate) close_fn:Option<SyscallMckfdIntFn>,
    pub(crate) fcntl_fn:Option<SyscallMckfdIntFn>,
    pub(crate) lock_fn:Option<SyscallMckfdLockFn>,
    pub(crate) unlock_fn:Option<SyscallMckfdUnlockFn>,
}

struct PGuard{lock:*mut c_void,flags:CLong,unlock:SyscallMckfdUnlockFn}
impl Drop for PGuard{fn drop(&mut self){unsafe{(self.unlock)(self.lock,self.flags)};}}
unsafe fn lock_process(c:&Open)->PGuard{
    let lock=unsafe{addr_of_mut!((*c.proc.cast::<Process>()).mckfd_lock)}.cast();
    let flags=unsafe{c.lock_fn.unwrap()(lock)};PGuard{lock,flags,unlock:c.unlock_fn.unwrap()}
}
fn layout()->EventLayout{EventLayout{size:size_of::<Event>(),align:align_of::<Event>(),
    group_leader:offset_of!(Event,group_leader),sibling_list:offset_of!(Event,sibling_list),
    group_entry:offset_of!(Event,group_entry),nr_siblings:offset_of!(Event,nr_siblings),
    pmc_status:offset_of!(Event,pmc_status),counter_id:offset_of!(Event,counter_id),
    attr_flags:offset_of!(Event,attr)+offset_of!(crate::f03_perf_attr_callbacks::PerfEventAttr,flags)}}
fn validate(c:&Open)->Result<(),CLong>{
    let valid=!c.request.is_null()&&!c.thread.is_null()&&!c.proc.is_null()&&!c.attr.is_null()
        && c.mckfd_size==size_of::<Mckfd>()
        && c.event_pid_offset==offset_of!(Event,pid)&&c.event_counter_id_offset==offset_of!(Event,counter_id)
        && c.proc_mckfd_offset==offset_of!(Process,mckfd)&&c.proc_mckfd_lock_offset==offset_of!(Process,mckfd_lock)
        && c.thread_pmc_alloc_map_offset==offset_of!(Thread,pmc_alloc_map)
        && c.mckfd_next_offset==offset_of!(Mckfd,next)&&c.mckfd_fd_offset==offset_of!(Mckfd,fd)
        && c.mckfd_data_offset==offset_of!(Mckfd,data)&&c.mckfd_sig_no_offset==offset_of!(Mckfd,padding)
        && c.mckfd_read_cb_offset==offset_of!(Mckfd,read_cb)&&c.mckfd_ioctl_cb_offset==offset_of!(Mckfd,ioctl_cb)
        && c.mckfd_mmap_cb_offset==offset_of!(Mckfd,mmap_cb)&&c.mckfd_close_cb_offset==offset_of!(Mckfd,close_cb)
        && c.mckfd_fcntl_cb_offset==offset_of!(Mckfd,fcntl_cb)
        && c.event_group_leader_offset==offset_of!(Event,group_leader)
        && c.event_sibling_list_offset==offset_of!(Event,sibling_list)&&c.event_group_entry_offset==offset_of!(Event,group_entry)
        && c.event_nr_siblings_offset==offset_of!(Event,nr_siblings)&&c.event_pmc_status_offset==offset_of!(Event,pmc_status)
        && c.event_alloc_fn.is_some()&&c.counter_alloc_fn.is_some()&&c.syscall_fn.is_some()&&c.mckfd_alloc_fn.is_some()
        && c.read_fn.is_some()&&c.ioctl_fn.is_some()&&c.mmap_fn.is_some()&&c.close_fn.is_some()&&c.fcntl_fn.is_some()
        && c.lock_fn.is_some()&&c.unlock_fn.is_some();
    if valid{Ok(())}else{Err(-EINVAL as CLong)}
}

/// Genuine complete initialized carrier; actual do_syscall overwrites the route
/// from the still-current invoking Thread. This is NEVER called by idle drain.
unsafe fn host(c:&Open,number:CInt,arg0:CULong)->CLong{
    unsafe{write_bytes(c.request,0,1);(*c.request).number=number as CULong;(*c.request).args[0]=arg0;}
    let cpu=unsafe{crate::x86_local::ihk_mc_get_processor_id()};
    unsafe{c.syscall_fn.unwrap()(c.request,cpu)}
}
struct Transaction{configuration:Open,prepared:Option<Prepared>,plan:Plan,host_fd:Option<CLong>,descriptor:*mut Mckfd}
impl Drop for Transaction{fn drop(&mut self){
    if let Some(fd)=self.host_fd.take(){
        // The exact opening Thread is still inside this syscall. No request or
        // Process reference is handed to a background/idle or foreign executor.
        let result=unsafe{host(&self.configuration,3,fd as CULong)};
        if let Some(prepared)=self.prepared.as_mut(){unsafe{prepared.host_rollback_result(result);}}
    }
    if !self.descriptor.is_null(){unsafe{super::super::syscall_mckfd_free_bridge(self.descriptor.cast());}self.descriptor=null_mut();}
    // Remaining fields drop AFTER the real close disposition. Plan consumes
    // only its exact reservation tokens; Prepared queues actual abort origins.
}}

pub(crate) unsafe fn open_from_body(c:Open)->CLong{
    let result=unsafe{open(c)};
    // This ordinary syscall return is a real safe point, with no P/R/S/hash/G
    // held. UNKNOWN host cleanup records remain retained, never retried here.
    unsafe{super::drain_safe_point();}
    match result{Ok(fd)=>fd,Err(error)=>error}
}
unsafe fn open(c:Open)->Result<CLong,CLong>{
    validate(&c)?;
    let cpu=unsafe{crate::cls::get_this_cpu_local_var()};
    if cpu.is_null()||unsafe{(*cpu).current.cast::<c_void>()!=c.thread||(*c.thread.cast::<Thread>()).proc.cast::<c_void>()!=c.proc}{return Err(-EINVAL as CLong);}
    let process=unsafe{super::process_targets::ensure(c.proc.cast(),c.mckfd_alloc_flags)}.map_err(|e|e as CLong)?;
    let _opening=unsafe{process.opening()}.map_err(|e|e as CLong)?;
    let mut raw=null_mut();let status=unsafe{c.event_alloc_fn.unwrap()(&mut raw,c.attr)};
    if status!=0{return Err(status as CLong);}
    let event=unsafe{EventPin::allocate(raw,layout(),c.mckfd_alloc_flags,EventOrigins{
        abort:super::super::perf_event_alloc_free_bridge,close:super::super::syscall_mckfd_free_bridge})}.map_err(|e|e as CLong)?;
    unsafe{(*raw.cast::<Event>()).pid=c.pid;}
    let mut plan=unsafe{Plan::allocate(1,c.mckfd_alloc_flags)}.map_err(|e|e as CLong)?;
    let counters=unsafe{crate::x86_perfctr::ihk_mc_perf_get_num_counters()};
    let counter={let mut r=unsafe{Locked::take()};
        unsafe{plan.origin_locked(c.thread.cast(),&event,counters,&mut r)}.map_err(|e|e as CLong)?;
        unsafe{plan.origin_index_locked(&mut r)}.ok_or(-EINVAL as CLong)?};
    // No published borrower exists. The genuine C mirror keeps its ORIGINAL
    // creation index; all later hardware access uses actual executing-Thread maps.
    unsafe{(*raw.cast::<Event>()).counter_id=counter;(*raw.cast::<Event>()).pmc_status=1u64<<counter;}
    let chosen=if c.group_fd == -1{None}else{
        let result={let _p=unsafe{lock_process(&c)};
            let mut row=unsafe{(*c.proc.cast::<Process>()).mckfd.cast::<Mckfd>()};
            while !row.is_null()&&unsafe{(*row).fd!=c.group_fd}{row=unsafe{(*row).next};}
            if row.is_null(){Err(-EINVAL)}else{
                match unsafe{descriptors::pin_managed_locked(c.proc.cast(),row)}.map_err(|error|error as CLong)?{Some(pin)=>Ok(pin),None=>Err(-EINVAL)}
            }};
        Some(result.map_err(|e|e as CLong)?)
    };
    let leader=match chosen.as_ref(){None=>None,Some(pin)=>Some(pin.event().map_err(|e|e as CLong)?)};
    let mut member=match leader.as_ref(){None=>None,Some(pin)=>Some(unsafe{pin.own_group().prepare_member(&event,c.mckfd_alloc_flags)}.map_err(|e|e as CLong)?)};
    let descriptor_event=DescriptorEvent::from_pin(event.try_clone().map_err(|e|e as CLong)?).map_err(|e|e as CLong)?;
    let prepared=unsafe{Prepared::allocate(c.proc.cast(),null_mut(),descriptor_event,c.mckfd_alloc_flags)}.map_err(|e|e as CLong)?;
    let mut transaction=Transaction{configuration:c,prepared:Some(prepared),plan,host_fd:None,descriptor:null_mut()};
    let fd=unsafe{host(&c,c.perf_event_open_nr,0)};
    if fd<0{return Err(fd);}
    transaction.host_fd=Some(fd);
    unsafe{transaction.prepared.as_mut().unwrap().host_opened(fd)}.map_err(|e|e as CLong)?;
    let fd_int=CInt::try_from(fd).map_err(|_|-EINVAL as CLong)?;
    // ORIGINAL ordering: host error precedes this actual Mckfd allocation.
    let descriptor=unsafe{c.mckfd_alloc_fn.unwrap()(c.mckfd_size,c.mckfd_alloc_flags)}.cast::<Mckfd>();
    if descriptor.is_null(){return Err(-ENOMEM as CLong);}
    transaction.descriptor=descriptor;
    unsafe{
        write_bytes(descriptor,0,1);(*descriptor).fd=fd_int;(*descriptor).padding=-1;(*descriptor).data=raw as CLong;
        (*descriptor).read_cb=c.read_fn.map_or(core::ptr::null_mut(),|f|f as *const () as *mut c_void);
        (*descriptor).ioctl_cb=c.ioctl_fn.map_or(core::ptr::null_mut(),|f|f as *const () as *mut c_void);
        (*descriptor).mmap_cb=c.mmap_fn.map_or(core::ptr::null_mut(),|f|f as *const () as *mut c_void);
        (*descriptor).close_cb=c.close_fn.map_or(core::ptr::null_mut(),|f|f as *const () as *mut c_void);
        (*descriptor).fcntl_cb=c.fcntl_fn.map_or(core::ptr::null_mut(),|f|f as *const () as *mut c_void);
        // Full80 bytes initialized, including original previously-unwritten opt
        // and dup callback slots. They are not a hidden kind/tag/refcount.
        transaction.prepared.as_mut().unwrap().bind_unpublished_descriptor(descriptor).map_err(|error|error as CLong)?;
    }
    // Allocate enough stable map nodes OUTSIDE P/R after real host success;
    // no host work is replayed if concurrent Thread setup increases capacity.
    loop{
        let needed=if leader.is_some(){let mut r=unsafe{Locked::take()};unsafe{Plan::thread_count_locked(None,&mut r)}}else{0};
        transaction.plan.grow(needed,c.mckfd_alloc_flags).map_err(|e|e as CLong)?;
        let outcome={let _p=unsafe{lock_process(&c)};let mut r=unsafe{Locked::take()};
            if !unsafe{process.live_for_open_locked(&mut r)}{Err((-EBADF,false))}else if chosen.as_ref().map_or(false,|pin|!unsafe{pin.live_locked(&mut r)}){Err((-EINVAL,false))}else{
                let prepared_maps=match leader.as_ref(){None=>Ok(()),Some(pin)=>unsafe{transaction.plan.group_append_locked(pin.own_group().key(),&event,counters,&mut r)}};
                if let Err(error)=prepared_maps{Err((error,error == -ENOMEM))}else if let Err(error)=unsafe{transaction.plan.validate_locked(&mut r)}{Err((error,false))}else{
                    let prepared=transaction.prepared.take().unwrap();
                    match unsafe{prepared.publish(member.take(),&mut r,|r|transaction.plan.commit_locked(r))}{
                        Ok(())=>Ok(()),Err((error,prepared,returned_member))=>{transaction.prepared=Some(prepared);member=returned_member;Err((error,false))}
                    }
                }
            }
        };
        match outcome{Ok(())=>break,Err((_error,true))=>continue,Err((error,false))=>return Err(error as CLong)}
    }
    transaction.host_fd=None;transaction.descriptor=null_mut();Ok(fd)
}
