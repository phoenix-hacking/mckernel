//! Seven changed ptrace callback lifecycle cases; explicit HOST-only lower effects.
#![feature(c_variadic)]
#![allow(dead_code, unused_imports)]

use core::{ffi::c_void, mem::{align_of, offset_of, size_of, MaybeUninit}, ptr::{addr_of_mut, read_volatile, write}};
use std::{alloc::{alloc_zeroed, dealloc, handle_alloc_error, Layout}, ffi::CStr,
          sync::{LazyLock, Mutex}};
#[path="source/production_abi.rs"] mod abi;
#[path="source/production_policy.rs"] mod syscall_policy;
#[path="source/production_process_state.rs"] mod process_helpers;
#[path="source/production_lock_types.rs"] mod lock_helpers;
#[path="source/production_spinlock_type.rs"] mod spinlock_helpers;
#[path="source/production_debug_type.rs"] mod debug;
#[path="source/production_adapters.rs"] mod f03_ptrace_adapters;
use abi::{CInt, CLong, CULong, CpuLocalVar, Process, SigInfo, SigPending, Thread};

const SAVED_IRQ: u64 = 0xabc0_1234_ffff_0202;
const TARGET: i32 = 42;
const TRACER: i32 = 500;
const ORIGINAL_C_FILE: &str = "/src/kernel/syscall.c";

struct Slot<T>(*mut T);
impl<T> Slot<T> {
    fn new() -> Self {
        let layout=Layout::new::<T>();
        let p=unsafe { alloc_zeroed(layout).cast::<T>() };
        if p.is_null() { handle_alloc_error(layout); }
        Self(p)
    }
    fn into_raw(self) -> *mut T { let p=self.0; core::mem::forget(self); p }
}
impl<T> Drop for Slot<T> {
    fn drop(&mut self) { unsafe { dealloc(self.0.cast(),Layout::new::<T>()) }; }
}

#[derive(Clone,Default)]
struct Model {
    cpu:usize, current:usize, child:usize, child_proc:usize,
    exists:bool, borrowed:bool, irq_held:bool, active_node:usize, active_lock:usize,
    expected_saved:i32, expected_ptrace:i32, kill_result:i64,
    events:Vec<String>, infos:Vec<String>, kills:Vec<[i64;4]>, prints:Vec<[i64;2]>,
    origins:Vec<String>, owned_pending:Vec<usize>,
    finds:usize, unlocks:usize, current_lookups:usize, locks:usize, irq_unlocks:usize,
    frees:usize, wakes:usize, steps:usize,
}
static MODEL: LazyLock<Mutex<Model>>=LazyLock::new(||Mutex::new(Model::default()));
fn with<R>(f:impl FnOnce(&mut Model)->R)->R { f(&mut MODEL.lock().unwrap()) }
fn event(s:&mut Model, name:&str) { s.events.push(name.into()); }
fn hex(bytes:&[u8])->String { bytes.iter().map(|b|format!("{:02x}",b)).collect() }

struct Frame {
    cpu:Slot<CpuLocalVar>, current:Slot<Thread>, child:Slot<Thread>,
    tracer_proc:Slot<Process>, child_proc:Slot<Process>,
}
impl Frame {
    fn new(exists:bool,initial_ptrace:i32,expected_ptrace:i32,kill_result:i64)->Self {
        let f=Self { cpu:Slot::new(),current:Slot::new(),child:Slot::new(),
                     tracer_proc:Slot::new(),child_proc:Slot::new() };
        unsafe {
            write(addr_of_mut!((*f.cpu.0).current),f.current.0);
            write(addr_of_mut!((*f.current.0).proc),f.tracer_proc.0);
            write(addr_of_mut!((*f.child.0).proc),f.child_proc.0);
            write(addr_of_mut!((*f.tracer_proc.0).pid),TRACER);
            write(addr_of_mut!((*f.child_proc.0).pid),TARGET);
            write(addr_of_mut!((*f.child.0).ptrace_saved_uctx_valid),7);
            write(addr_of_mut!((*f.child.0).ptrace),initial_ptrace);
        }
        with(|s|*s=Model { cpu:f.cpu.0 as usize,current:f.current.0 as usize,
            child:f.child.0 as usize,child_proc:f.child_proc.0 as usize,exists,
            expected_saved:0,expected_ptrace,kill_result,..Model::default() });
        f
    }
    fn pending(&self,send:bool,seed:u8,attach:bool)->*mut SigPending {
        let p=Slot::<SigPending>::new().into_raw();
        let bytes:Vec<u8>=(0..128).map(|i|(i as u8).wrapping_mul(7).wrapping_add(seed)).collect();
        unsafe {
            core::ptr::copy_nonoverlapping(bytes.as_ptr(),addr_of_mut!((*p).info).cast::<u8>(),128);
            if attach {
                if send { write(addr_of_mut!((*self.child.0).ptrace_sendsig),p.cast()); }
                else { write(addr_of_mut!((*self.child.0).ptrace_recvsig),p.cast()); }
            }
        }
        with(|s|s.owned_pending.push(p as usize)); p
    }
    fn observe(&self,id:&str,result:i64)->String {
        let s=with(|s|s.clone());
        let (saved,ptrace,send,recv)=unsafe { ((*self.child.0).ptrace_saved_uctx_valid,
            (*self.child.0).ptrace,!(*self.child.0).ptrace_sendsig.is_null(),
            !(*self.child.0).ptrace_recvsig.is_null()) };
        assert!(!s.irq_held && s.active_node==0 && s.active_lock==0);
        assert_eq!(s.locks,s.irq_unlocks);
        format!("{{\"id\":{:?},\"return\":{},\"events\":{:?},\"current_lookups\":{},\"finds\":{},\"thread_unlocks\":{},\"saved_after\":{},\"ptrace_after\":{},\"frees\":{},\"wakes\":{},\"steps\":{},\"irq_pairs\":{},\"irq_restored\":true,\"borrow_released\":{},\"send_retained\":{},\"recv_retained\":{},\"kill_args\":{:?},\"kill_info128\":{:?},\"prints\":{:?},\"free_origins\":{:?}}}",
            id,result,s.events,s.current_lookups,s.finds,s.unlocks,saved,ptrace,s.frees,
            s.wakes,s.steps,s.locks,!s.borrowed,send,recv,s.kills,s.infos,s.prints,s.origins)
    }
}
impl Drop for Frame {
    fn drop(&mut self) {
        let pending=with(|s|core::mem::take(&mut s.owned_pending));
        for p in pending { unsafe { dealloc((p as *mut SigPending).cast(),Layout::new::<SigPending>()) }; }
    }
}

// Explicit HOST controls: logical borrowed lookup and saved-IRQ effects only.
unsafe fn host_find(pid:CInt,tid:CInt)->*mut Thread {
    with(|s| {
        assert_eq!((pid,tid),(TARGET,TARGET)); assert!(!s.borrowed);
        s.finds+=1;event(s,"find");
        if s.exists { s.borrowed=true;s.child as *mut Thread } else { core::ptr::null_mut() }
    })
}
unsafe fn host_thread_unlock(thread:*mut Thread) {
    with(|s| { assert_eq!(thread as usize,s.child);assert!(s.borrowed && !s.irq_held);
        s.borrowed=false;s.unlocks+=1;event(s,"thread_unlock"); });
}
fn host_writer_lock(lock:usize,node:usize) {
    with(|s|unsafe {
        assert!(s.borrowed && !s.irq_held && s.active_node==0);
        assert_eq!(lock,addr_of_mut!((*(s.child_proc as *mut Process)).update_lock) as usize);
        assert_eq!(lock%64,0);assert_eq!(node%64,0);assert_ne!(node,0);
        assert_eq!((*(s.child as *mut Thread)).ptrace_saved_uctx_valid,s.expected_saved);
        // Do not read any node byte here: acquisition initializes saved IRQ below.
        s.irq_held=true;s.active_node=node;s.active_lock=lock;s.locks+=1;event(s,"lock");
    });
}
fn host_writer_unlock(lock:usize,node:usize,saved:u64) {
    with(|s|unsafe {
        assert!(s.borrowed && s.irq_held);assert_eq!((lock,node),(s.active_lock,s.active_node));
        assert_eq!(saved,SAVED_IRQ);
        assert_eq!((*(s.child as *mut Thread)).ptrace,s.expected_ptrace);
        s.irq_held=false;s.active_lock=0;s.active_node=0;s.irq_unlocks+=1;event(s,"unlock_irq");
    });
}
mod cls {
    pub unsafe extern "C" fn get_this_cpu_local_var()->*mut crate::abi::CpuLocalVar {
        crate::with(|s| {s.current_lookups+=1;crate::event(s,"current");s.cpu as *mut crate::abi::CpuLocalVar})
    }
}
mod mem_helpers {
    pub unsafe extern "C" fn kfree_tracked(p:*mut core::ffi::c_void,file:*mut i8,line:i32) {
        crate::with(|s|unsafe {
            assert!(s.borrowed && !s.irq_held);assert!(!p.is_null());
            assert_eq!(std::ffi::CStr::from_ptr(file).to_str().unwrap(),crate::ORIGINAL_C_FILE);
            assert_eq!(line,4657);
            let slot=s.owned_pending.iter().position(|v|*v==p as usize).expect("once-only owned pending free");
            let child=s.child as *mut crate::abi::Thread;
            assert_ne!((*child).ptrace_sendsig.cast::<core::ffi::c_void>(),p);
            assert_ne!((*child).ptrace_recvsig.cast::<core::ffi::c_void>(),p);
            s.owned_pending.remove(slot);s.frees+=1;crate::event(s,"free");
            s.origins.push(format!("{}:{}",crate::ORIGINAL_C_FILE,line));
            // Poison all128 bytes and actually release this test allocation. A
            // later delivery must use the body's prior stack copy, never p.
            core::ptr::write_bytes(core::ptr::addr_of_mut!((*(p as *mut crate::abi::SigPending)).info).cast::<u8>(),0xa5,128);
            std::alloc::dealloc(p.cast(),std::alloc::Layout::new::<crate::abi::SigPending>());
        });
    }
}
#[no_mangle]
pub unsafe extern "C" fn do_kill(thread:*mut Thread,pid:CInt,tid:CInt,sig:CInt,info:*mut SigInfo,cont:CInt)->CULong {
    with(|s| {
        assert_eq!(thread as usize,s.current);assert_eq!((pid,tid),(TARGET,-1));
        assert!(s.borrowed && !s.irq_held && !info.is_null());
        assert_eq!(unsafe{(*(s.child as *mut Thread)).ptrace_saved_uctx_valid},s.expected_saved);
        s.kills.push([pid as i64,tid as i64,sig as i64,cont as i64]);
        s.infos.push(hex(unsafe {core::slice::from_raw_parts(info.cast::<u8>(),128)}));
        event(s,"kill");s.kill_result as CULong
    })
}
#[no_mangle]
pub unsafe extern "C" fn sched_wakeup_thread(thread:*mut Thread,states:CInt)->CInt {
    with(|s| {assert_eq!(thread as usize,s.child);assert_eq!(states,0x60);
        assert!(s.borrowed && !s.irq_held);s.wakes+=1;event(s,"wake");}); -44
}
#[no_mangle]
pub unsafe extern "C" fn set_single_step(thread:*mut Thread) {
    with(|s|unsafe {assert_eq!(thread as usize,s.child);assert!(s.borrowed && !s.irq_held);
        assert_eq!((*thread).ptrace_saved_uctx_valid,0);s.steps+=1;event(s,"step");});
}
#[no_mangle]
pub unsafe extern "C" fn kprintf(fmt:*const i8,mut args:...)->CInt {
    assert_eq!(unsafe{CStr::from_ptr(fmt)}.to_bytes(),b"ptrace_wakeup_sig,pid=%d,data=%08x\n");
    let pid=unsafe{args.arg::<i32>()};let bits=unsafe{args.arg::<u32>()};
    with(|s|{s.prints.push([pid as i64,bits as i64]);event(s,"log");});0
}

unsafe fn debug_flags(flags:u8) {
    let p=unsafe{syscall_policy::entry::host_descriptor()};
    assert_eq!(unsafe{CStr::from_ptr((*p).file)}.to_str().unwrap(),ORIGINAL_C_FILE);
    assert_eq!(unsafe{CStr::from_ptr((*p).func)}.to_bytes(),b"ptrace_wakeup_log_bridge");
    assert!(unsafe{(*p).fmt.is_null()});assert_eq!(unsafe{(*p).line_flags}&0x00ff_ffff,24429);
    unsafe{write(addr_of_mut!((*p).line_flags),24429|((flags as u32)<<24))};
}
fn run_entry(id:&str,request:i64,data:i64,exists:bool,initial:i32,expected:i32,
             result:i64,send:bool,recv:bool)->String {
    let f=Frame::new(exists,initial,expected,result);
    if send {f.pending(true,3,true);}
    if recv {f.pending(false,11,true);}
    unsafe{debug_flags(0x80)};
    let rc=unsafe{syscall_policy::entry::ptrace_wakeup_sig(TARGET,request,data)};
    assert!(!with(|s|s.borrowed));f.observe(id,rc as i64)
}
fn main() {
    assert_eq!(size_of::<SigInfo>(),128);assert_eq!(offset_of!(SigPending,info),24);
    assert_eq!(unsafe{(*syscall_policy::entry::host_descriptor()).line_flags},24429);
    let mut groups:Vec<(&str,Vec<String>)>=Vec::new();
    // Case1: the six non-entry exports, exact debug gate/origin and public ABI.
    let f=Frame::new(true,0x280,0x280,i64::MIN+3);
    with(|s|{s.borrowed=true;s.expected_saved=7;});
    unsafe {
        debug_flags(0);syscall_policy::entry::ptrace_wakeup_log_bridge(4,-7,i32::MIN+1);
        debug_flags(0x80);syscall_policy::entry::ptrace_wakeup_log_bridge(3,-7,i32::MIN+1);
        syscall_policy::entry::ptrace_wakeup_log_bridge(4,-7,i32::MIN+1);
        let lock=addr_of_mut!((*f.child_proc.0).update_lock) as u64;
        let mut node=MaybeUninit::<lock_helpers::McsRwlockNodeIrqsave>::uninit();
        syscall_policy::entry::ptrace_wakeup_update_lock_bridge(lock,node.as_mut_ptr().cast());
        syscall_policy::entry::ptrace_wakeup_update_unlock_bridge(lock,node.as_mut_ptr().cast());
        let pending=f.pending(true,3,false);
        syscall_policy::entry::ptrace_detach_kfree_bridge(pending.cast());
        let info=Slot::<SigInfo>::new();
        core::ptr::write_bytes(info.0.cast::<u8>(),0x11,128);
        let rc=f03_ptrace_adapters::ptrace_detach_do_kill_bridge(f.current.0.cast(),TARGET,-1,10,info.0.cast::<c_void>().cast_const(),1);
        assert_eq!(rc,i64::MIN+3);
        let unit:()=f03_ptrace_adapters::ptrace_detach_wakeup_bridge(f.child.0.cast(),0x60);
        assert_eq!(unit,());groups.push(("direct-provider-ABI-debug-origin",vec![f.observe("direct",rc)]));
    }
    drop(f);
    groups.push(("lookup-and-data-errors",vec![
        run_entry("miss",7,0,false,0x280,0x80,0,false,false),
        run_entry("negative-data",7,-1,true,0x280,0x80,0,false,false),
        run_entry("above-NSIG",7,65,true,0x280,0x80,0,false,false)]));
    groups.push(("KILL-success-error",vec![
        run_entry("kill-success",8,0,true,0x280,0x80,0,false,false),
        run_entry("kill-error",8,0,true,0x280,0x80,-77,false,false)]));
    groups.push(("CONT-no-signal-SIGSTOP",vec![
        run_entry("cont-zero",7,0,true,0x280,0x80,0,false,false),
        run_entry("cont-SIGSTOP",7,19,true,0x280,0x80,0,false,false)]));
    groups.push(("SINGLESTEP-user-signal",vec![
        run_entry("single-user",9,10,true,0x280,0x80,0,true,true)]));
    groups.push(("SYSCALL-user-error",vec![
        run_entry("syscall-user-error",24,12,true,0x80,0x280,-91,true,true)]));
    groups.push(("CONT-pending-copy128-free-error",vec![
        run_entry("cont-sendsig",7,10,true,0x280,0x80,0,true,true),
        run_entry("cont-recvsig-error",7,10,true,0x280,0x80,-5,false,true)]));
    assert_eq!(groups.len(),7);
    let cases=groups.iter().map(|(id,rows)|format!("{{\"id\":{:?},\"vectors\":[{}]}}",id,rows.join(","))).collect::<Vec<_>>().join(",");
    println!("{{\"status\":\"PASS\",\"scope\":\"changed-ptrace-callback-composition-with-explicit-HOST-lower-controls\",\"case_count\":{},\"kernel_runtime\":false,\"native_execution\":false,\"actual_provider_binding\":false,\"layout\":{{\"ops_size\":{},\"ops_slots\":{},\"wakeup_offset\":{},\"irq_node_size\":{},\"irq_node_alignment\":{},\"siginfo_size\":{},\"pending_info_offset\":{}}},\"cases\":[{}]}}",
        groups.len(),size_of::<syscall_policy::PtraceSyscallOps>(),size_of::<syscall_policy::PtraceSyscallOps>()/8,
        syscall_policy::entry::host_wakeup_slot_offset(),size_of::<lock_helpers::McsRwlockNodeIrqsave>(),
        align_of::<lock_helpers::McsRwlockNodeIrqsave>(),size_of::<SigInfo>(),offset_of!(SigPending,info),cases);
}
