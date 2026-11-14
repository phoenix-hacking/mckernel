#![allow(dead_code)]
use core::ffi::{c_int,c_long,c_ulong,c_void};
use std::{cell::RefCell,collections::BTreeSet};
const SYS_CLONE:c_long=56;const EINVAL:i32=22;const EOPNOTSUPP:i32=95;const ENOMEM:i32=12;const EAGAIN:i32=11;const EINTR:i32=4;
const PRIVATE_FORK_CARRIER_MARKER_V1:u64=0x313030434b46434d;
const MCEXEC_UP_RET_SYSCALL:c_ulong=0x30a02904;static RET_PERROR_TAG:&[u8]=b"ret\0";
#[repr(C)]
pub struct McexecSyscallRequest {
    rtid: c_int,
    ttid: c_int,
    valid: c_ulong,
    number: c_ulong,
    args: [c_ulong; 6],
}
#[repr(C)]
pub struct McexecSyscallWaitDesc {
    cpu: c_ulong,
    sr: McexecSyscallRequest,
    pid: c_int,
}
#[repr(C)]
struct SyscallRetDesc {
    cpu: c_long,
    ret: c_long,
    src: c_ulong,
    dest: c_ulong,
    size: c_ulong,
}
#[repr(C)]
pub struct ForkSync {
    status: i32,
    success: i32,
}
#[repr(C)]
pub struct ForkSyncContainer {
    pid: i32,
    next: *mut ForkSyncContainer,
    fs: *mut ForkSync,
}
static mut MCEXEC_FORK_SYNC_TOP:*mut ForkSyncContainer=core::ptr::null_mut();

#[derive(Default)]struct State{events:Vec<&'static str>,returns:Vec<(i32,i64,i64)>,live_fs:BTreeSet<usize>,live_nodes:BTreeSet<usize>,forks:usize,alloc_fs_fail:bool,alloc_node_fail:bool,fork_pid:i32,errno:i32,fs_status:i32,child_return:i64,sem_results:Vec<i32>,wait_pid:i32,ioctl_result:i32}
thread_local!{static STATE:RefCell<State>=RefCell::new(State::default());}
fn event(e:&'static str){STATE.with(|s|s.borrow_mut().events.push(e));}
fn reset(){assert!(unsafe{MCEXEC_FORK_SYNC_TOP}.is_null());STATE.with(|s|{assert!(s.borrow().live_fs.is_empty()&&s.borrow().live_nodes.is_empty());*s.borrow_mut()=State{fork_pid:33,errno:12,child_return:37,..State::default()};});}
unsafe fn ioctl(fd:c_int,command:c_ulong,address:c_ulong)->c_int{assert_eq!(command,MCEXEC_UP_RET_SYSCALL);let d=unsafe{&*(address as*const SyscallRetDesc)};assert_eq!((d.src,d.dest,d.size),(0,0,0));STATE.with(|s|{let mut s=s.borrow_mut();s.events.push("ioctl");s.returns.push((fd,d.cpu,d.ret));s.ioctl_result})}
unsafe fn perror(tag:*const u8){assert_eq!(unsafe{std::ffi::CStr::from_ptr(tag.cast())}.to_bytes(),b"ret");event("perror");}
unsafe fn __errno_location()->*mut c_int{STATE.with(|s|core::ptr::addr_of_mut!(s.borrow_mut().errno))}
unsafe fn mcexec_clone_alloc_fork_sync_bridge()->*mut c_void{event("alloc_fs");let(fail,status)=STATE.with(|s|{let s=s.borrow();(s.alloc_fs_fail,s.fs_status)});if fail{return core::ptr::null_mut();}let p=Box::into_raw(Box::new(ForkSync{status,success:0}));STATE.with(|s|assert!(s.borrow_mut().live_fs.insert(p as usize)));p.cast()}
unsafe fn mcexec_clone_alloc_container_bridge()->*mut c_void{event("alloc_node");if STATE.with(|s|s.borrow().alloc_node_fail){return core::ptr::null_mut();}let p=Box::into_raw(Box::new(ForkSyncContainer{pid:0,next:core::ptr::null_mut(),fs:core::ptr::null_mut()}));STATE.with(|s|assert!(s.borrow_mut().live_nodes.insert(p as usize)));p.cast()}
unsafe fn mcexec_fork_sync_lock_bridge(){event("lock");}unsafe fn mcexec_fork_sync_unlock_bridge(){event("unlock");}
unsafe fn mcexec_fork_sync_munmap_bridge(p:*mut c_void){event("unmap");STATE.with(|s|assert!(s.borrow_mut().live_fs.remove(&(p as usize))));unsafe{drop(Box::from_raw(p.cast::<ForkSync>()))};}
unsafe fn mcexec_fork_sync_free_bridge(p:*mut c_void){event("free");STATE.with(|s|assert!(s.borrow_mut().live_nodes.remove(&(p as usize))));unsafe{drop(Box::from_raw(p.cast::<ForkSyncContainer>()))};}
unsafe fn mcexec_clone_fork_bridge()->c_int{STATE.with(|s|{let mut s=s.borrow_mut();s.events.push("fork");s.forks+=1;s.fork_pid})}
unsafe fn mcexec_clone_fork_failed_bridge(){event("fork_failed");}
unsafe fn mcexec_clone_child_bridge(_:*const McexecSyscallWaitDesc,_:*mut c_void)->c_long{event("child");STATE.with(|s|s.borrow().child_return)}
unsafe fn mcexec_clone_sem_trywait_bridge(_:*mut c_void)->c_int{event("sem_wait");STATE.with(|s|{let mut s=s.borrow_mut();if s.sem_results.is_empty(){0}else{s.sem_results.remove(0)}})}
unsafe fn mcexec_clone_waitpid_nohang_bridge(_:c_int)->c_int{event("waitpid");STATE.with(|s|s.borrow().wait_pid)}
unsafe fn mcexec_clone_sched_yield_bridge(){event("yield");}
unsafe fn mcexec_clone_child_after_fork_failed_bridge(){event("child_failed");}
unsafe fn mcexec_clone_sem_destroy_bridge(_:*mut c_void){event("sem_destroy");}
pub unsafe extern "C" fn do_syscall_return(
    fd: c_int,
    cpu: c_int,
    ret: c_long,
    _n: c_int,
    src: c_ulong,
    dest: c_ulong,
    sz: c_ulong,
) {
    let desc = SyscallRetDesc {
        cpu: cpu as c_long,
        ret,
        src,
        dest,
        size: sz,
    };

    if unsafe {
        ioctl(
            fd,
            MCEXEC_UP_RET_SYSCALL,
            &desc as *const SyscallRetDesc as c_ulong,
        )
    } != 0
    {
        unsafe { perror(RET_PERROR_TAG.as_ptr()) };
    }
}
unsafe fn act_private_fork_control(
    w: *const McexecSyscallWaitDesc, fd: c_int, cpu: c_int,
) -> bool {
    let request = unsafe { &(*w).sr };
    let selector = request.args[0];
    if selector != 2 && selector != 3 { return false; }
    let route_matches = request.number == SYS_CLONE as c_ulong && cpu >= 0
        && unsafe { (*w).cpu } == cpu as c_ulong
        && request.args[5] as u64 == PRIVATE_FORK_CARRIER_MARKER_V1;
    // Selector3 has an existing guest final-ACK shape (stage2). Selector2 has
    // no authenticated revoke protocol yet; no new wire phase is inferred.
    let known_shape = selector != 3 || request.args[1] == 2;
    let result = if route_matches && known_shape { -EOPNOTSUPP } else { -EINVAL };
    unsafe { do_syscall_return(fd, cpu, result as c_long, 0, 0, 0, 0) };
    true
}
pub unsafe extern "C" fn act_clone_start(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
    main_loop_ret: *mut c_long,
) -> c_int {
    if unsafe { act_private_fork_control(w, fd, cpu) } { return 0; }
    let mut rc: c_long = -1;
    let fs = unsafe { mcexec_clone_alloc_fork_sync_bridge() as *mut ForkSync };

    if fs.is_null() {
        unsafe { do_syscall_return(fd, cpu, rc, 0, 0, 0, 0) };
        return 0;
    }

    let fsc = unsafe { mcexec_clone_alloc_container_bridge() as *mut ForkSyncContainer };
    if fsc.is_null() {
        unsafe {
            mcexec_clone_sem_destroy_bridge(fs as *mut c_void);
            mcexec_fork_sync_munmap_bridge(fs as *mut c_void);
            do_syscall_return(fd, cpu, rc, 0, 0, 0, 0);
        }
        return 0;
    }

    unsafe {
        mcexec_fork_sync_lock_bridge();
        (*fsc).next = MCEXEC_FORK_SYNC_TOP;
        MCEXEC_FORK_SYNC_TOP = fsc;
        mcexec_fork_sync_unlock_bridge();
        (*fsc).fs = fs;
    }

    let pid = unsafe { mcexec_clone_fork_bridge() };
    unsafe {
        (*fsc).pid = pid;
    }

    if pid == -1 {
        let errno = unsafe { *__errno_location() };
        unsafe { mcexec_clone_fork_failed_bridge() };
        rc = -(errno as c_long);
    } else if pid == 0 {
        let child_ret = unsafe { mcexec_clone_child_bridge(w, fs as *mut c_void) };
        if !main_loop_ret.is_null() {
            unsafe {
                *main_loop_ret = child_ret;
            }
        }
        return 1;
    } else {
        loop {
            let wait_rc = unsafe { mcexec_clone_sem_trywait_bridge(fs as *mut c_void) };
            if wait_rc != -1 {
                break;
            }

            let errno = unsafe { *__errno_location() };
            if errno != EAGAIN && errno != EINTR {
                break;
            }

            let wrc = unsafe { mcexec_clone_waitpid_nohang_bridge(pid) };
            if wrc == pid {
                unsafe {
                    (*fs).status = -ENOMEM;
                }
                break;
            }
            unsafe { mcexec_clone_sched_yield_bridge() };
        }

        let status = unsafe { (*fs).status };
        if status != 0 {
            unsafe { mcexec_clone_child_after_fork_failed_bridge() };
            rc = status as c_long;
        } else {
            rc = pid as c_long;
        }
    }

    unsafe {
        mcexec_clone_sem_destroy_bridge(fs as *mut c_void);
        if rc < 0 {
            mcexec_fork_sync_munmap_bridge(fs as *mut c_void);
            mcexec_fork_sync_lock_bridge();
            if mcexec_fork_sync_remove_node_result(
                core::ptr::addr_of_mut!(MCEXEC_FORK_SYNC_TOP),
                fsc,
            ) > 0
            {
                mcexec_fork_sync_free_bridge(fsc as *mut c_void);
            }
            mcexec_fork_sync_unlock_bridge();
        }
        do_syscall_return(fd, cpu, rc, 0, 0, 0, 0);
    }

    0
}
pub unsafe extern "C" fn act_clone_complete(
    w: *const McexecSyscallWaitDesc,
    fd: c_int,
    cpu: c_int,
) {
    let pid = unsafe { (*w).sr.args[1] as c_int };
    let mut fs: *mut ForkSync = core::ptr::null_mut();
    let mut node: *mut ForkSyncContainer = core::ptr::null_mut();

    unsafe {
        mcexec_fork_sync_lock_bridge();
        if mcexec_fork_sync_complete_result(
            core::ptr::addr_of_mut!(MCEXEC_FORK_SYNC_TOP),
            pid,
            &mut fs,
            &mut node,
        ) > 0
        {
            if !fs.is_null() {
                mcexec_fork_sync_munmap_bridge(fs as *mut c_void);
            }
            if !node.is_null() {
                mcexec_fork_sync_free_bridge(node as *mut c_void);
            }
        }
        mcexec_fork_sync_unlock_bridge();
        do_syscall_return(fd, cpu, 0, 0, 0, 0, 0);
    }
}
pub unsafe extern "C" fn mcexec_fork_sync_complete_result(
    top: *mut *mut ForkSyncContainer,
    pid: i32,
    fs_out: *mut *mut ForkSync,
    node_out: *mut *mut ForkSyncContainer,
) -> i32 {
    if top.is_null() || fs_out.is_null() || node_out.is_null() {
        return -EINVAL;
    }

    unsafe {
        *fs_out = core::ptr::null_mut();
        *node_out = core::ptr::null_mut();
    }

    let mut prev: *mut ForkSyncContainer = core::ptr::null_mut();
    let mut current = unsafe { *top };
    while !current.is_null() {
        let next = unsafe { (*current).next };
        if unsafe { (*current).pid } == pid {
            if prev.is_null() {
                unsafe {
                    *top = next;
                }
            } else {
                unsafe {
                    (*prev).next = next;
                }
            }

            let fs = unsafe { (*current).fs };
            if !fs.is_null() {
                unsafe {
                    (*fs).success = 1;
                }
            }
            unsafe {
                *fs_out = fs;
                *node_out = current;
            }
            return 1;
        }
        prev = current;
        current = next;
    }

    0
}
pub unsafe extern "C" fn mcexec_fork_sync_remove_node_result(
    top: *mut *mut ForkSyncContainer,
    target: *mut ForkSyncContainer,
) -> i32 {
    if top.is_null() || target.is_null() {
        return 0;
    }

    let mut prev: *mut ForkSyncContainer = core::ptr::null_mut();
    let mut current = unsafe { *top };
    while !current.is_null() {
        let next = unsafe { (*current).next };
        if current == target {
            if prev.is_null() {
                unsafe {
                    *top = next;
                }
            } else {
                unsafe {
                    (*prev).next = next;
                }
            }
            return 1;
        }
        prev = current;
        current = next;
    }

    0
}

fn request(selector:u64,stage:u64)->McexecSyscallWaitDesc{McexecSyscallWaitDesc{cpu:1,sr:McexecSyscallRequest{rtid:101,ttid:0,valid:1,number:56,args:[selector,stage,0x8000,0x9000,0xa000,PRIVATE_FORK_CARRIER_MARKER_V1]},pid:101}}
fn run_start(w:&McexecSyscallWaitDesc,cpu:i32)->(i32,i64){let mut main=99;let rc=unsafe{act_clone_start(w,7,cpu,&mut main)};(rc,main)}
fn no_fork_refusal(expected:i64){STATE.with(|s|{let s=s.borrow();assert_eq!(s.forks,0);assert!(s.live_fs.is_empty()&&s.live_nodes.is_empty());assert_eq!(s.events,vec!["ioctl"]);assert_eq!(s.returns.len(),1);assert_eq!(s.returns[0].2,expected);});assert!(unsafe{MCEXEC_FORK_SYNC_TOP}.is_null());}
fn complete(pid:i32){let w=request(1,pid as u64);unsafe{act_clone_complete(&w,7,1)};assert!(unsafe{MCEXEC_FORK_SYNC_TOP}.is_null());STATE.with(|s|assert!(s.borrow().live_fs.is_empty()&&s.borrow().live_nodes.is_empty()));}
#[test]fn actual_control_selectors_refuse_unavailable_backend_without_alloc_or_linux_fork(){for selector in [2,3]{reset();let w=request(selector,2);let before=w.sr.args;assert_eq!(run_start(&w,1),(0,99));assert_eq!(w.sr.args,before);no_fork_refusal(-95);}}
#[test]fn actual_malformed_private_routes_never_enter_normal_clone_or_claim_phase(){for kind in 0..5{reset();let mut w=request(3,2);let mut cpu=1;match kind{0=>w.sr.args[5]^=1,1=>w.sr.number=57,2=>cpu=2,3=>cpu=-1,_=>w.sr.args[1]=1};assert_eq!(run_start(&w,cpu),(0,99));no_fork_refusal(-22);}reset();let mut w=request(2,0);w.sr.args[5]=0;assert_eq!(run_start(&w,1),(0,99));no_fork_refusal(-22);}
#[test]fn actual_normal_parent_child_failure_and_selector1_completion_are_preserved(){
 for flag in [0,0x8011]{reset();let mut w=request(flag,0);w.sr.args[5]=0;assert_eq!(run_start(&w,1),(0,99));STATE.with(|s|{let s=s.borrow();assert_eq!(s.forks,1);assert_eq!(s.returns,vec![(7,1,33)]);assert_eq!((s.live_fs.len(),s.live_nodes.len()),(1,1));});complete(33);}
 reset();STATE.with(|s|s.borrow_mut().fork_pid=0);let w=request(0,0);assert_eq!(run_start(&w,1),(1,37));STATE.with(|s|{let s=s.borrow();assert_eq!(s.forks,1);assert!(s.returns.is_empty());assert!(s.events.contains(&"child"));});complete(0);
 reset();STATE.with(|s|s.borrow_mut().fork_pid=-1);let w=request(0,0);assert_eq!(run_start(&w,1),(0,99));STATE.with(|s|{let s=s.borrow();assert_eq!(s.forks,1);assert_eq!(s.returns,vec![(7,1,-12)]);assert!(s.live_fs.is_empty()&&s.live_nodes.is_empty());assert_eq!(s.events,vec!["alloc_fs","alloc_node","lock","unlock","fork","fork_failed","sem_destroy","unmap","lock","free","unlock","ioctl"]);});assert!(unsafe{MCEXEC_FORK_SYNC_TOP}.is_null());
 reset();STATE.with(|s|{let mut s=s.borrow_mut();s.errno=11;s.sem_results=vec![-1];s.wait_pid=33;});assert_eq!(run_start(&request(0,0),1),(0,99));STATE.with(|s|{let s=s.borrow();assert_eq!(s.returns,vec![(7,1,-12)]);assert!(s.events.contains(&"waitpid")&&s.events.contains(&"child_failed"));assert!(s.live_fs.is_empty()&&s.live_nodes.is_empty());});
}
#[test]fn actual_allocation_errors_and_failed_control_return_do_not_fall_back_to_fork(){
 for kind in 0..2{reset();STATE.with(|s|{let mut s=s.borrow_mut();if kind==0{s.alloc_fs_fail=true}else{s.alloc_node_fail=true}});assert_eq!(run_start(&request(0,0),1),(0,99));STATE.with(|s|{let s=s.borrow();assert_eq!(s.returns,vec![(7,1,-1)]);assert_eq!(s.forks,0);assert!(s.live_fs.is_empty()&&s.live_nodes.is_empty());});}
 reset();STATE.with(|s|s.borrow_mut().ioctl_result=-1);assert_eq!(run_start(&request(3,2),1),(0,99));STATE.with(|s|{let s=s.borrow();assert_eq!(s.forks,0);assert!(s.live_fs.is_empty()&&s.live_nodes.is_empty());assert_eq!(s.events,vec!["ioctl","perror"]);assert_eq!(s.returns,vec![(7,1,-95)]);});
}
