// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// PRIVATE UNWIRED genuine selected callback/close flow. No metadata kind guesses.
use core::ffi::c_void;
use core::mem::MaybeUninit;
use core::ptr::{addr_of_mut,null_mut};
use crate::abi::{CInt,CLong,CULong,Mckfd,Process,Thread,X86UserContext};
use super::descriptors::{self,Locked,HostState};
use super::events::EventPin;
use super::maps::{Plan,CallScope};
use super::monitors::{MonitorRead,InstallMode,Installed};
use super::super::f03_sync_child_layout_v2::FullMcPerfEvent as Event;
use super::super::{SyscallForwardContextFn,SyscallMckfdFreeFn};
const EINVAL:CInt=22;const EBADF:CInt=9;const ENOMEM:CInt=12;
const NOWAIT:CULong=2;
unsafe fn current()->(*mut Thread,*mut Process){let cpu=unsafe{crate::cls::get_this_cpu_local_var()};let thread=unsafe{(*cpu).current};(thread,unsafe{(*thread).proc})}
unsafe fn callback(sfd:*mut Mckfd)->Result<(super::DescriptorPin,EventPin,*mut Thread),CInt>{
    let (thread,process)=unsafe{current()};let pin=unsafe{descriptors::pin_callback(sfd)}?;
    if pin.process()!=process{return Err(-EBADF);}let event=pin.event()?;Ok((pin,event,thread))
}

/// Allocate only real transient mapping nodes before the final R window. The
/// returned lock is transferred to hardware's *_locked entry, so snapshot and
/// Operation leases are acquired BEFORE any association/map can be retired.
unsafe fn prepare_call(event:&EventPin,thread:*mut Thread)->Result<(Plan,CallScope,Locked),CInt>{
    let counters=unsafe{crate::x86_perfctr::ihk_mc_perf_get_num_counters()};
    loop{
        let capacity={let mut r=unsafe{Locked::take()};let read=unsafe{event.selected_group().read_locked(&mut r)};let n=read.event_count();unsafe{read.finish_locked(&mut r);}n};
        let mut plan=unsafe{Plan::allocate(capacity,NOWAIT)}?;
        let mut r=unsafe{Locked::take()};let mut read=unsafe{event.selected_group().read_locked(&mut r)};
        let outcome=unsafe{plan.call_group_locked(thread,&mut read,event.selected_group().key(),counters,&mut r)};
        unsafe{read.finish_locked(&mut r);}
        if let Err(error)=outcome{drop(r);drop(plan);if error == -ENOMEM{continue;}return Err(error);}
        if let Err(error)=unsafe{plan.validate_locked(&mut r)}{drop(r);drop(plan);return Err(error);}
        let scope=CallScope::new(&plan);unsafe{plan.commit_locked(&mut r);}
        return Ok((plan,scope,r));
    }
}

unsafe fn prepare_one_call(event:&EventPin,thread:*mut Thread)->Result<(Plan,CallScope,Locked),CInt>{
    let mut plan=unsafe{Plan::allocate(1,NOWAIT)}?;let counters=unsafe{crate::x86_perfctr::ihk_mc_perf_get_num_counters()};
    let mut r=unsafe{Locked::take()};
    if let Err(error)=unsafe{plan.call_one_locked(thread,event.key(),event.selected_group().key(),counters,&mut r)}{drop(r);return Err(error);}
    let scope=CallScope::new(&plan);unsafe{plan.commit_locked(&mut r);}Ok((plan,scope,r))
}

unsafe fn read_size_valid(event:&EventPin,count:CULong,format:CULong,r:&mut Locked)->bool{
    if format&8==0{return count>=core::mem::size_of::<CULong>() as CULong;}
    let snapshot=unsafe{event.selected_group().read_locked(r)};
    let words=snapshot.event_count().checked_add(1);
    unsafe{snapshot.finish_locked(r);}
    words.and_then(|n|n.checked_mul(core::mem::size_of::<CULong>())).map_or(false,|bytes|count>=bytes as CULong)
}

pub(crate) unsafe fn read(sfd:*mut Mckfd,ctx:*mut X86UserContext)->CLong{
    let (_pin,event,thread)=match unsafe{callback(sfd)}{Ok(v)=>v,Err(error)=>return error as CLong};
    let buf=unsafe{crate::x86_cpu_helpers::ihk_mc_syscall_arg1(ctx)};
    let count=unsafe{crate::x86_cpu_helpers::ihk_mc_syscall_arg2(ctx)};
    let format=unsafe{(*event.raw_event().cast::<Event>()).attr.read_format};
    // Original entry checks precede allocation/hardware/usercopy. Validate again
    // against the SAME final R snapshot passed into the full group reader.
    {let mut r=unsafe{Locked::take()};if !unsafe{read_size_valid(&event,count,format,&mut r)}{return -EINVAL as CLong;}}
    let (_plan,_scope,mut r)=match if format&8!=0{unsafe{prepare_call(&event,thread)}}else{unsafe{prepare_one_call(&event,thread)}}{Ok(v)=>v,Err(error)=>return error as CLong};
    if !unsafe{read_size_valid(&event,count,format,&mut r)}{drop(r);return -EINVAL as CLong;}
    // Hardware read captures under the SAME metadata exclusion, then releases
    // R/S before each genuine usercopy; no mutable C sibling traversal.
    unsafe{super::hardware::read_locked(&event,thread,buf,count,format,r)}
}

unsafe fn enable(pin:&super::DescriptorPin,event:&EventPin,thread:*mut Thread,target:*mut Process,remote:bool)->CLong{
    let handle=match unsafe{super::process_targets::ensure(target,NOWAIT)}{Ok(handle)=>handle,Err(error)=>return error as CLong};
    if remote{
        let mut r=unsafe{Locked::take()};
        match unsafe{handle.pin_locked(&mut r)}{
            Ok(MonitorRead::Managed(existing))=>{unsafe{existing.release_locked(&mut r);}return 0;},
            Ok(MonitorRead::Unmanaged(_))=>return 0,
            Ok(MonitorRead::None)=>{},Err(error)=>return error as CLong,
        }
    }
    let counters=unsafe{crate::x86_perfctr::ihk_mc_perf_get_num_counters()};
    loop{
        let capacity={let mut r=unsafe{Locked::take()};let read=unsafe{event.selected_group().read_locked(&mut r)};
            let n=read.event_count().checked_mul(unsafe{Plan::thread_count_locked(Some(handle.key()),&mut r)}).ok_or(-EINVAL);
            unsafe{read.finish_locked(&mut r);}match n{Ok(n)=>n,Err(error)=>return error as CLong}};
        let mut plan=match unsafe{Plan::allocate(capacity,NOWAIT)}{Ok(plan)=>plan,Err(error)=>return error as CLong};
        let mut r=unsafe{Locked::take()};
        if !unsafe{handle.live_for_open_locked(&mut r)}{drop(r);return -EBADF as CLong;}
        let mut read=unsafe{event.selected_group().read_locked(&mut r)};
        let result=unsafe{plan.monitor_locked(handle.key(),&mut read,event.selected_group().key(),counters,&mut r)};
        unsafe{read.finish_locked(&mut r);}
        if let Err(error)=result{drop(r);drop(plan);if error == -ENOMEM{continue;}return error as CLong;}
        if let Err(error)=unsafe{plan.validate_locked(&mut r)}{drop(r);return error as CLong;}
        let slot=unsafe{pin.monitor_slot_locked(&mut r)};
        let mode=if remote{InstallMode::Remote{pp_reset:1}}else{InstallMode::Current};
        let installed={let target=match unsafe{handle.target_locked(&mut r)}{Ok(target)=>target,Err(error)=>{drop(r);return error as CLong;}};
            unsafe{(*slot).install_locked(target,handle.key(),event,mode,&mut r)}};
        match installed{
            Err(error)=>{drop(r);return error as CLong;},
            Ok(Installed::AlreadyPopulated)=>{drop(r);return 0;},
            Ok(Installed::Published)=>unsafe{plan.commit_locked(&mut r);},
        }
        if remote{drop(r);return 0;}
        let _=unsafe{super::hardware::start_locked(event,thread,r)};return 0;
    }
}

pub(crate) unsafe fn ioctl(sfd:*mut Mckfd,ctx:*mut X86UserContext)->CInt{
    let (pin,event,thread)=match unsafe{callback(sfd)}{Ok(v)=>v,Err(error)=>return error};
    let command=unsafe{crate::x86_cpu_helpers::ihk_mc_syscall_arg1(ctx)} as u32;
    let pid=unsafe{(*event.raw_event().cast::<Event>()).pid};
    if command==0x2400{
        if pid==0{return unsafe{enable(&pin,&event,thread,(*thread).proc,false)} as CInt;}
        if pid>0{
            let mut node=MaybeUninit::<crate::lock_helpers::McsRwlockNodeIrqsave>::uninit();
            let result=unsafe{super::target_process::with_remote_target(pid,node.as_mut_ptr().cast(),
                super::super::f03_process_cleanup_find,super::super::f03_process_cleanup_unlock,
                |target|unsafe{enable(&pin,&event,thread,target,true)})};
            return match result{Ok(result)=>result as CInt,Err(error)=>error};
        }return 0;
    }
    if command==0x2401{
        if pid==0{
            let (_plan,_scope,r)=match unsafe{prepare_call(&event,thread)}{Ok(v)=>v,Err(error)=>return error};
            let _=unsafe{super::hardware::stop_locked(&event,thread,r)};
            unsafe{super::lifecycle::clear_current_monitor((*thread).proc);}
        }return 0;
    }
    if command==0x2403{
        let (_plan,_scope,r)=match unsafe{prepare_call(&event,thread)}{Ok(v)=>v,Err(error)=>return error};
        let _=unsafe{super::hardware::reset_locked(&event,thread,r)};return 0;
    }
    if command==0x2402{return if event.inherit_enabled(){-EINVAL}else{0};}
    -1
}

/// Shared ordinary close entry. An unregistered descriptor returns None and
/// remains with the original nonperf helper, never an inferred perf callback.
pub(crate) unsafe fn close_if_managed(
    thread:*mut c_void,fd:CInt,number:CInt,ctx:*mut c_void,
    forward:SyscallForwardContextFn,free:Option<SyscallMckfdFreeFn>,
)->Result<Option<CLong>,CInt>{
    let thread=thread.cast::<Thread>();if thread.is_null(){return Err(-EINVAL);}
    let (actual_thread,_)=unsafe{current()};if actual_thread!=thread{return Err(-EINVAL);}
    let process=unsafe{(*thread).proc};
    let p=unsafe{addr_of_mut!((*process).mckfd_lock)}.cast::<c_void>();
    let first={let flags=unsafe{super::super::syscall_mckfd_lock_bridge(p)};
        let mut row=unsafe{(*process).mckfd.cast::<Mckfd>()};while !row.is_null()&&unsafe{(*row).fd!=fd}{row=unsafe{(*row).next};}
        let result=if row.is_null(){Ok(None)}else{unsafe{descriptors::pin_managed_locked(process,row)}};
        unsafe{super::super::syscall_mckfd_unlock_bridge(p,flags);}result?};
    let Some(pin)=first else{return Ok(None);};let free=free.ok_or(-EINVAL)?;
    // Actual shared close entry ALREADY owns the same Process transaction gate
    // before either P window. This also prevents a new managed publication from
    // changing an opaque/missing initial lookup into a legacy unpinned close.
    // Never recursively acquire this gate here.
    let token={let flags=unsafe{super::super::syscall_mckfd_lock_bridge(p)};
        let mut link=unsafe{addr_of_mut!((*process).mckfd)}.cast::<*mut Mckfd>();
        while !unsafe{*link}.is_null()&&unsafe{(**link).fd!=fd}{link=unsafe{addr_of_mut!((**link).next)};}
        let result=if unsafe{*link}!=pin.descriptor(){Err(-EBADF)}else{
            match unsafe{descriptors::mark_close_under_p(process,pin.descriptor())}{
                Ok(Some(token))=>{unsafe{*link=(*pin.descriptor()).next;(*pin.descriptor()).next=null_mut();}Ok(token)},
                Ok(None)=>Err(-EINVAL),Err(error)=>Err(error),
            }};
        unsafe{super::super::syscall_mckfd_unlock_bridge(p,flags);}result?};
    let _close=unsafe{token.gate().close()}?;
    if !matches!(token.host_state(),HostState::Owned){
        unsafe{token.mark_host_unissued(descriptors::HostUnissued::WrongCurrentOwner);}
        let _=unsafe{descriptors::retire_unlinked(process,token.descriptor(),free)}?;
        return Ok(Some(-EBADF as CLong));
    }
    let (_,actual)=unsafe{current()};
    if actual!=process{
        unsafe{token.mark_host_unissued(descriptors::HostUnissued::WrongCurrentOwner);}
        let _=unsafe{descriptors::retire_unlinked(process,token.descriptor(),free)}?;
        return Ok(Some(-EBADF as CLong));
    }
    // Original complete user context and original syscall number/caller route.
    // No background numeric close or partial/fabricated syscall context.
    let result=unsafe{forward(number,ctx)};
    unsafe{token.record_host_result(result);}
    let _=unsafe{descriptors::retire_unlinked(process,token.descriptor(),free)}?;
    Ok(Some(result))
}

pub(crate) unsafe fn fcntl(sfd:*mut Mckfd,ctx:*mut X86UserContext)->CInt{
    let (pin,_event,_thread)=match unsafe{callback(sfd)}{Ok(value)=>value,Err(error)=>return error};
    let command=unsafe{crate::x86_cpu_helpers::ihk_mc_syscall_arg1(ctx)} as CInt;
    let argument=unsafe{crate::x86_cpu_helpers::ihk_mc_syscall_arg2(ctx)} as CLong;
    if command==10{ // genuine existing F_SETSIG constant, C entry metadata joins it
        let lock=unsafe{addr_of_mut!((*pin.process()).mckfd_lock)}.cast();
        let flags=unsafe{super::super::syscall_mckfd_lock_bridge(lock)};
        unsafe{(*sfd).padding=argument as CInt;super::super::syscall_mckfd_unlock_bridge(lock,flags);}
    }
    let data=unsafe{&super::super::f03_perf_descriptor_entries_v1::f03_perf_descriptor_layout_v1};
    match data.forward{Some(forward)=>(unsafe{forward(data.fcntl_nr,ctx.cast())}) as CInt,None=>-EINVAL}
}
