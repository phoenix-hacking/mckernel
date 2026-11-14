// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// PRIVATE UNWIRED. Actual constructor/fork/scheduler/exit/terminal participants.
use core::ptr::{addr_of_mut,null_mut};
use crate::abi::{CInt,CULong,Process,Thread};
use super::descriptors::Locked;
use super::process_targets;
use super::maps::Plan;
use super::monitors::MonitorRead;
const EINVAL:CInt=22;const ENOMEM:CInt=12;

/// The real initialized Thread is still private; setup may fail BEFORE its
/// original visibility and before any Linux child process is requested.
pub(crate) unsafe fn prepare_created_thread(thread:*mut Thread,flags:CULong)->Result<(),CInt>{
    if thread.is_null()||unsafe{(*thread).proc.is_null()}{return Err(-EINVAL);}
    let target=unsafe{process_targets::ensure((*thread).proc,flags)}?;
    let mut r=unsafe{Locked::take()};unsafe{super::maps::bind_thread_locked(thread,target.key(),&mut r)}
}

/// Existing fork constructor invokes this before returning its unpublished
/// Thread to do_fork and BEFORE the genuine Linux fork. The logical monitor
/// snapshot linearizes under R here together with genuine pending descriptor
/// copies; the later host-success path NEVER recopies an unowned raw pointer.
pub(crate) unsafe fn prepare_cloned_thread(parent:*mut Thread,child:*mut Thread,flags:CULong)->Result<(),CInt>{
    if parent.is_null()||child.is_null()||unsafe{(*parent).proc.is_null()||(*child).proc.is_null()}{return Err(-EINVAL);}
    let parent_target=unsafe{process_targets::ensure((*parent).proc,flags)}?;
    let child_target=unsafe{process_targets::ensure((*child).proc,flags)}?;
    let shared=unsafe{(*parent).proc==(*child).proc};
    let counters=unsafe{crate::x86_perfctr::ihk_mc_perf_get_num_counters()};
    loop{
        let count={let mut r=unsafe{Locked::take()};let read=unsafe{parent_target.pin_locked(&mut r)}?;
            match read{
                MonitorRead::None=>0,
                MonitorRead::Unmanaged(_)=>return Err(-EINVAL),
                MonitorRead::Managed(pin)=>{let n=if shared||pin.inherit_enabled(){let group=unsafe{pin.selected_group().read_locked(&mut r)};let n=group.event_count();unsafe{group.finish_locked(&mut r);}n}else{0};unsafe{pin.release_locked(&mut r);}n}
            }};
        let mut plan=unsafe{Plan::allocate(count,flags)}?;
        let mut r=unsafe{Locked::take()};
        let current=match unsafe{parent_target.pin_locked(&mut r)}{Ok(pin)=>pin,Err(error)=>{drop(r);return Err(error);}};
        let outcome=match current{
            MonitorRead::None=>unsafe{super::maps::bind_thread_locked(child,child_target.key(),&mut r)},
            MonitorRead::Unmanaged(_)=>Err(-EINVAL),
            MonitorRead::Managed(pin)=>{
                let result=(|| -> Result<(),CInt> { if shared||pin.inherit_enabled(){
                    let mut group=unsafe{pin.selected_group().read_locked(&mut r)};
                    let prepared=unsafe{plan.new_thread_monitor_locked(child,child_target.key(),&mut group,pin.selected_group().key(),counters,&mut r)};
                    unsafe{group.finish_locked(&mut r);}
                    if let Err(error)=prepared{Err(error)}else{
                        let validation=unsafe{plan.validate_locked(&mut r)};
                        if let Err(error)=validation{Err(error)}else{
                            if !shared{
                                // Three stable real objects; the child slot is
                                // Process-owned, even with NO copied perf fd.
                                let parent_ptr=unsafe{parent_target.target_locked(&mut r)}? as *mut super::monitors::Target;
                                let child_ptr=unsafe{child_target.target_locked(&mut r)}? as *mut super::monitors::Target;
                                let slot=unsafe{child_target.inherited_slot_locked(&mut r)}? as *mut super::monitors::MonitorSlot;
                                unsafe{super::monitors::inherit_locked(&*parent_ptr,&mut *child_ptr,&mut *slot,&mut r)}?;
                            }
                            unsafe{super::maps::bind_thread_locked(child,child_target.key(),&mut r)}?;
                            unsafe{plan.commit_locked(&mut r);}Ok(())
                        }
                    }
                }else{unsafe{super::maps::bind_thread_locked(child,child_target.key(),&mut r)}} })();
                unsafe{pin.release_locked(&mut r);}result
            }
        };
        drop(r);
        match outcome{Ok(())=>return Ok(()),Err(error) if error == -ENOMEM=>{drop(plan);continue;},Err(error)=>return Err(error)}
    }
}

pub(crate) unsafe fn inherit_monitor_after_host_clone(_parent:*mut Process,child:*mut Process){
    // Managed inheritance and all fallible mapping work already occurred at
    // the genuine constructor snapshot, before host fork. Only actual positive
    // host clone result activates the independent Linux child fd-table route.
    unsafe{super::fork_copy::finish_child_host_route(child,true);}
}
pub(super) unsafe fn clear_current_monitor(process:*mut Process){
    let Some(handle)=(unsafe{process_targets::existing(process)}).expect("current Process metadata")else{return;};
    let mut r=unsafe{Locked::take()};
    unsafe{handle.target_locked(&mut r).expect("live current Process").clear_locked(&mut r);}
    unsafe{addr_of_mut!((*process).perf_status).write(super::super::f03_perf_counter_control_v1::f03_perf_event_layout_v1.pp_none);}
    unsafe{super::maps::reconcile_monitors_locked(|key,group,r|process_targets::current_group_locked(key,group,r),&mut r);}
}

/// Capture the genuine current association AND its complete group/maps in the
/// SAME R exclusion before a clear can release those real map ownership edges.
/// Void scheduler/exit callers allocate nothing and introduce no new ENOMEM.
pub(crate) unsafe fn sync_monitor(process:*mut Process,thread:*mut Thread){
    let mut r=unsafe{Locked::take()};
    let read=match unsafe{process_targets::pin_under_lock(process,&mut r)}{Ok(read)=>read,Err(_)=>return};
    match read{
        MonitorRead::None=>{},
        MonitorRead::Unmanaged(_)=>panic!("unregistered perf monitor in managed profile"),
        MonitorRead::Managed(pin)=>{let _=unsafe{super::hardware::sync_locked(&pin,thread,r)};drop(pin);}
    }
}
pub(crate) unsafe fn switch_monitor(thread:*mut Thread,reset_state:CInt,count_state:CInt){
    if thread.is_null(){return;}let process=unsafe{(*thread).proc};
    let mut r=unsafe{Locked::take()};
    let read=match unsafe{process_targets::pin_under_lock(process,&mut r)}{Ok(read)=>read,Err(_)=>return};
    match read{
        MonitorRead::None=>{},
        MonitorRead::Unmanaged(_)=>panic!("unregistered perf monitor in managed profile"),
        MonitorRead::Managed(pin)=>{
            let status=unsafe{(*process).perf_status};
            if status==count_state{unsafe{pin.release_locked(&mut r);}return;}
            // All original steps consume ONE coherent member epoch and ONE
            // complete actual lease set captured under this already-held R.
            // Monitor clear/replacement plus late append cannot widen a later
            // step to include a member that was never mapped for this Thread.
            match unsafe { super::hardware::switch_sequence_locked(&pin,thread,r,status==reset_state) } {
                Ok(_ignored_original_backend_status) => {},
                Err(_capture_error) => panic!("managed scheduler monitor was not prebound"),
            }
        }
    }
}
