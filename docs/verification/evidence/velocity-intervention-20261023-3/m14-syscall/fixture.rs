#![allow(dead_code)]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
use std::cell::RefCell;
use std::ffi::c_void;
use std::mem::{offset_of, size_of};
use std::ptr::{addr_of_mut, copy_nonoverlapping, null_mut};
#[path="snapshot/kernel/rust/abi.rs"] mod abi;
use abi::{CInt, CLong, CULong, SizeT, Thread, Process, Mckfd, SigSet, X86UserContext, CpuLocalVar};
const EINVAL:CInt=22;
const ENOMEM:CInt=12;
const EFAULT:CInt=14;
const SFD_NONBLOCK:CInt=0o4000;
const SFD_CLOEXEC:CInt=0o2000000;
const IHK_MC_AP_NOWAIT:CULong=2;
const SYS_SIGNALFD4:CInt=289;
type SyscallCopyFromUserFn=unsafe extern "C" fn(*mut u8,CULong,SizeT)->CLong;
type SyscallSignalfdCreateFn=unsafe extern "C" fn(CInt,CInt)->CLong;
type SyscallSignalfdPublishFn=unsafe extern "C" fn(*mut c_void,CInt,*const CULong,CInt)->CLong;
include!("signalfd_publish.rs");
include!("existing_consumer.rs.inc");
#[repr(C)] struct RefProcess { lock:u32, head:*mut Mckfd }
#[repr(C)] struct RefThread { proc:*mut RefProcess }
extern "C" {
    fn original_c_signalfd_publish_bridge(thread:*mut c_void,fd:CInt,mask:*const CULong,create:CInt)->CLong;
}
#[derive(Default)] struct State {
    lock:*mut c_void, headp:*mut *mut Mckfd, alloc:*mut Mckfd,
    fail_alloc:bool, copy_rc:CLong, host_rc:CLong, host_flags:CInt,
    cpu:*mut CpuLocalVar, depth:i32, events:Vec<&'static str>,
    reload:bool,
}
thread_local! { static STATE:RefCell<State>=RefCell::new(State::default()); }
unsafe extern "C" fn get_this_cpu_local_var()->*mut CpuLocalVar {STATE.with(|s|s.borrow().cpu)}
unsafe extern "C" fn syscall_copy_from_user_bridge(dst:*mut u8,src:CULong,n:SizeT)->CLong {
    STATE.with(|s| {let mut s=s.borrow_mut();s.events.push("copy");assert_eq!(n,8);
        if s.copy_rc==0 {copy_nonoverlapping(src as *const u8,dst,n)} s.copy_rc})
}
unsafe extern "C" fn syscall_signalfd_create_bridge(n:CInt,flags:CInt)->CLong {
    STATE.with(|s| {let mut s=s.borrow_mut();s.events.push("host");assert_eq!(n,289);
        assert_eq!(flags,s.host_flags);s.host_rc})
}
unsafe extern "C" fn syscall_alloc_bridge(n:SizeT,f:CULong)->*mut c_void {
    STATE.with(|s| {let mut s=s.borrow_mut();s.events.push("alloc");
        assert_eq!((n,f),(size_of::<Mckfd>(),2));assert_eq!(s.depth,0);
        if s.fail_alloc {null_mut()} else {s.alloc.cast()}})
}
#[no_mangle] unsafe extern "C" fn fixture_c_alloc(n:CInt,f:CULong,_file:*const u8,_line:CInt)->*mut c_void {
    syscall_alloc_bridge(n as SizeT,f)
}
#[no_mangle] unsafe extern "C" fn fixture_lock(lock:*mut c_void)->CLong {
    STATE.with(|s| {let mut s=s.borrow_mut();s.events.push("lock");assert_eq!(lock,s.lock);
        assert_eq!(s.depth,0);s.depth=1;0x1234_5678_8765_4321u64 as i64})
}
#[no_mangle] unsafe extern "C" fn fixture_unlock(lock:*mut c_void,irq:CLong) {
    STATE.with(|s| {let mut s=s.borrow_mut();s.events.push("unlock");assert_eq!(lock,s.lock);
        assert_eq!(irq,0x1234_5678_8765_4321u64 as i64);assert_eq!(s.depth,1);
        if s.reload {(**s.headp).fd=77;} s.depth=0;})
}
unsafe extern "C" fn syscall_mckfd_lock_bridge(lock:*mut c_void)->CLong {fixture_lock(lock)}
unsafe extern "C" fn syscall_mckfd_unlock_bridge(lock:*mut c_void,irq:CLong) {fixture_unlock(lock,irq)}
unsafe fn zero_box<T>()->Box<T> {
    Box::from_raw(std::alloc::alloc_zeroed(std::alloc::Layout::new::<T>()).cast())
}
unsafe fn bytes<T>(p:*const T)->Vec<u8> {
    std::slice::from_raw_parts(p.cast::<u8>(),size_of::<T>()).to_vec()
}
#[derive(Clone,Copy)] struct Case {
    name:&'static str, empty:bool, fd:i32, create:i32, mask:u64,
    fail:bool, consumer:bool, copy_rc:i64, host_rc:i64, flags:i32, sigsize:usize,
    null_mask:bool, null_ctx:bool, null_thread:bool, reload:bool,
    expected:i64, order:&'static [&'static str],
}
impl Case {fn direct(name:&'static str,fd:i32,create:i32,mask:u64,expected:i64,order:&'static [&'static str])->Self {
    Self{name,empty:false,fd,create,mask,fail:false,consumer:false,copy_rc:0,host_rc:55,flags:0,sigsize:8,
        null_mask:false,null_ctx:false,null_thread:false,reload:false,expected,order}
}}
#[derive(Debug,PartialEq)] struct Outcome {rc:i64,head:i32,next:Vec<i32>,nodes:Vec<Vec<u8>>,events:Vec<&'static str>}
unsafe fn run(c:Case,rust:bool)->Outcome {
    let mut thread=zero_box::<Thread>(); let mut proc=zero_box::<Process>(); let mut cpu=zero_box::<CpuLocalVar>();
    let mut rp=RefProcess{lock:0,head:null_mut()};let mut rt=RefThread{proc:&mut rp};
    let mut nodes:Vec<Box<Mckfd>>=(0..4).map(|_|zero_box::<Mckfd>()).collect();
    let ptrs:Vec<*mut Mckfd>=nodes.iter_mut().map(|n|&mut **n as *mut Mckfd).collect();
    for (i,n) in nodes.iter_mut().enumerate() {
        std::ptr::write_bytes((&mut **n as *mut Mckfd).cast::<u8>(),0x7a,size_of::<Mckfd>());
        n.fd=[10,20,10,99][i];n.data=[0x1111,0x2222,0x3333,0x4444][i];
        n.next=if i<2 {ptrs[i+1]} else {null_mut()};
    }
    std::ptr::write_bytes(ptrs[3].cast::<u8>(),0xa5,size_of::<Mckfd>());
    let head=if c.empty {null_mut()} else {ptrs[0]};
    thread.proc=&mut *proc;proc.mckfd=head.cast();rp.head=head;
    let threadp=if rust {(&mut *thread as *mut Thread).cast::<c_void>()}else{(&mut rt as *mut RefThread).cast()};
    let (lock,headp)=if rust {(addr_of_mut!(proc.mckfd_lock).cast(),addr_of_mut!(proc.mckfd).cast::<*mut Mckfd>())}
        else {(addr_of_mut!(rp.lock).cast(),addr_of_mut!(rp.head))};
    cpu.current=if c.null_thread {null_mut()} else {threadp.cast::<Thread>()};
    let proc_before=bytes(&*proc);let thread_before=bytes(&*thread);
    STATE.with(|s|*s.borrow_mut()=State{lock,headp,alloc:ptrs[3],fail_alloc:c.fail,copy_rc:c.copy_rc,
        host_rc:c.host_rc,host_flags:c.flags,cpu:&mut *cpu,reload:c.reload,..State::default()});
    let mut ctx=zero_box::<X86UserContext>();
    ctx.gpr.rdi=c.fd as u64;ctx.gpr.rsi=if c.null_mask {0}else{&c.mask as *const u64 as u64};
    ctx.gpr.rdx=c.sigsize as u64;ctx.gpr.r10=c.flags as u64;
    let rc=if c.consumer {
        if rust {sys_signalfd4(289,if c.null_ctx {null_mut()}else{&mut *ctx})}
        else if c.null_ctx {-14}
        else {signalfd4_body_result(c.fd,ctx.gpr.rsi,c.sigsize,8,c.flags,
            if c.null_thread {null_mut()}else{threadp},289,Some(syscall_copy_from_user_bridge),
            Some(syscall_signalfd_create_bridge),Some(original_c_signalfd_publish_bridge))}
    } else if rust {syscall_signalfd_publish_bridge(threadp,c.fd,&c.mask,c.create)}
        else {original_c_signalfd_publish_bridge(threadp,c.fd,&c.mask,c.create)};
    let events=STATE.with(|s| {let s=s.borrow();assert_eq!(s.depth,0);s.events.clone()});
    assert_eq!(rc,c.expected,"{} expected result",c.name);assert_eq!(events,c.order,"{} expected order",c.name);
    // A mutation outside the process head field would be a separate behavior change.
    let mut after=bytes(&*proc);let head_offset=offset_of!(Process,mckfd);
    after[head_offset..head_offset+8].copy_from_slice(&proc_before[head_offset..head_offset+8]);
    assert_eq!(after,proc_before);assert_eq!(bytes(&*thread),thread_before);
    let index=|p:*mut Mckfd| if p.is_null(){-1}else{ptrs.iter().position(|q|*q==p).expect("owned node") as i32};
    let head=index(*headp);
    let mut next=Vec::new();let mut memory=Vec::new();
    for (i,p) in ptrs.iter().enumerate() {
        // Unused allocation storage intentionally contains poison, not a valid next pointer.
        next.push(if i==3 && (!events.contains(&"alloc")||c.fail){-2}else{index((**p).next)});
        let mut b=bytes(*p);b[..8].fill(0);memory.push(b);
    }
    Outcome{rc,head,next,nodes:memory,events}
}
fn main() {unsafe {
    // Existing ABI module is compiled unchanged; fixture C layout is separately bounded below.
    assert_eq!((size_of::<Mckfd>(),offset_of!(Mckfd,fd),offset_of!(Mckfd,data)),(80,8,16));
    let mut cases=vec![
        Case::direct("create-prepends",55,1,0x8000_0000_0000_0001,55,&["alloc","lock","unlock"]),
        Case::direct("create-noncanonical-true",55,-7,0,55,&["alloc","lock","unlock"]),
        Case::direct("update-head-first-duplicate",10,0,u64::MAX,10,&["lock","unlock"]),
        Case::direct("update-interior",20,0,0,20,&["lock","unlock"]),
        Case::direct("missing",30,0,123,-22,&["lock","unlock"]),
        Case::direct("negative-fd-existing-search",-1,0,123,-22,&["lock","unlock"]),
    ];
    let mut c=Case::direct("create-empty",55,1,31,55,&["alloc","lock","unlock"]);c.empty=true;cases.push(c);
    let mut c=Case::direct("update-empty",10,0,31,-22,&["lock","unlock"]);c.empty=true;cases.push(c);
    let mut c=Case::direct("alloc-failure",55,1,31,-12,&["alloc"]);c.fail=true;cases.push(c);
    let mut c=Case::direct("reload-after-unlock",55,1,31,77,&["alloc","lock","unlock"]);c.reload=true;cases.push(c);
    let base=Case{consumer:true,fd:-1,expected:55,order:&["copy","host","alloc","lock","unlock"],
        ..Case::direct("consumer-create",-1,0,u64::MAX,55,&[])};
    cases.push(base);
    cases.push(Case{name:"consumer-update",fd:20,expected:20,order:&["copy","lock","unlock"],..base});
    cases.push(Case{name:"consumer-update-missing",fd:40,expected:-22,order:&["copy","lock","unlock"],..base});
    cases.push(Case{name:"consumer-host-failure",host_rc:-38,expected:-38,order:&["copy","host"],..base});
    cases.push(Case{name:"consumer-alloc-failure-after-host",fail:true,expected:-12,order:&["copy","host","alloc"],..base});
    cases.push(Case{name:"consumer-flags-both",flags:SFD_CLOEXEC|SFD_NONBLOCK,..base});
    cases.push(Case{name:"consumer-size-before-copy",sigsize:16,expected:-22,order:&[],..base});
    cases.push(Case{name:"consumer-copy-error",copy_rc:-5,expected:-14,order:&["copy"],..base});
    cases.push(Case{name:"consumer-copy-positive-error",copy_rc:1,expected:-14,order:&["copy"],..base});
    cases.push(Case{name:"consumer-null-mask",null_mask:true,expected:-14,order:&[],..base});
    cases.push(Case{name:"consumer-invalid-flags",flags:1,expected:-22,order:&["copy"],..base});
    cases.push(Case{name:"consumer-null-context",null_ctx:true,expected:-14,order:&[],..base});
    cases.push(Case{name:"consumer-null-thread",null_thread:true,expected:-22,order:&["copy"],..base});
    for c in cases.iter().copied() {
        let reference=run(c,false);let candidate=run(c,true);
        assert_eq!(reference,candidate,"{} unchanged C versus Rust",c.name);
        // Independent create/update invariants supplement the C equivalence oracle.
        if candidate.events.contains(&"alloc")&&!c.fail&&candidate.rc>=0 {
            assert_eq!(candidate.head,3);assert_eq!(candidate.next[3],if c.empty{-1}else{0});
            let mut expected=vec![0u8;80];expected[8..12].copy_from_slice(&(candidate.rc as i32).to_ne_bytes());
            expected[16..24].copy_from_slice(&c.mask.to_ne_bytes());assert_eq!(candidate.nodes[3],expected);
        }
        println!("PASS {} rc={} events={:?}",c.name,candidate.rc,candidate.events);
    }
    println!("PASS {} focused vectors; actual selected Rust sys_signalfd4 executed for consumer rows",cases.len());
}}
