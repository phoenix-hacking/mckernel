from pathlib import Path
import sys,json,hashlib
sys.path.insert(0,'/home/holden/mckernel')
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item
Q=Path(__file__).resolve().parent;S=(Q/'mcexec_helpers.rs').read_text();B=(Q/'base-mcexec_helpers.rs').read_text()
def item(n):return balanced_item(S,n)
old=balanced_item(B,'pub unsafe extern "C" fn act_clone_start(')
new=item('pub unsafe extern "C" fn act_clone_start(')
insert='    if unsafe { act_private_fork_control(w, fd, cpu) } { return 0; }\n'
assert new.count(insert)==1 and new.replace(insert,'',1)==old
for name in ['pub unsafe extern "C" fn act_clone_complete(','pub unsafe extern "C" fn do_syscall_return(','pub unsafe extern "C" fn mcexec_fork_sync_complete_result(','pub unsafe extern "C" fn mcexec_fork_sync_remove_node_result(']:assert item(name)==balanced_item(B,name)
pre=r'''#![allow(dead_code)]
use core::ffi::{c_int,c_long,c_ulong,c_void};
use std::{cell::RefCell,collections::BTreeSet};
const SYS_CLONE:c_long=56;const EINVAL:i32=22;const EOPNOTSUPP:i32=95;const ENOMEM:i32=12;const EAGAIN:i32=11;const EINTR:i32=4;
const PRIVATE_FORK_CARRIER_MARKER_V1:u64=0x313030434b46434d;
const MCEXEC_UP_RET_SYSCALL:c_ulong=0x30a02904;static RET_PERROR_TAG:&[u8]=b"ret\0";
'''
for n in ['pub struct McexecSyscallRequest {','pub struct McexecSyscallWaitDesc {','struct SyscallRetDesc {','pub struct ForkSync {','pub struct ForkSyncContainer {']:pre+='#[repr(C)]\n'+item(n)+'\n'
pre+='static mut MCEXEC_FORK_SYNC_TOP:*mut ForkSyncContainer=core::ptr::null_mut();\n'
adapters=r'''
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
'''
actual=''
for n in ['pub unsafe extern "C" fn do_syscall_return(','unsafe fn act_private_fork_control(','pub unsafe extern "C" fn act_clone_start(','pub unsafe extern "C" fn act_clone_complete(','pub unsafe extern "C" fn mcexec_fork_sync_complete_result(','pub unsafe extern "C" fn mcexec_fork_sync_remove_node_result(']:actual+=item(n)+'\n'
tests=r'''
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
'''
(Q/'actual-control-dispatch.rs').write_text(pre+adapters+actual+tests)
rows=[]
for p in [Q/'base-mcexec_helpers.rs',Q/'mcexec_helpers.rs',Q/'actual-control-dispatch.rs',Q/'prepare_control_fixture.py']:
 rows.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
(Q/'fixture-inputs.json').write_text(json.dumps({'rows':rows,'exact_actual_bodies':['act_clone_start','act_clone_complete','act_private_fork_control','do_syscall_return','mcexec_fork_sync_complete_result','mcexec_fork_sync_remove_node_result'],'normal_body_after_guard_byte_identical':True,'new_tests':4,'adapters':['Linux allocator/mmap/sem/fork/waitpid and errno','ioctl capture/perror','C fork-sync global/lock boundary'],'no_linux_fork_executed':True,'native_authority':False,'success_means':'Recognized control delivered as actual RET descriptor refusal with no allocation/fork, not successful revoke/ACK.'},indent=2)+'\n');print('sources',len(rows),'new_tests',4)
