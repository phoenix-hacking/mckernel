#[path="/home/holden/mckernel-work/host-preparation/evening-next-process-rust-batch2-20261019-1/original/kernel/rust/abi.rs"] mod abi;
use core::ffi::c_void;use core::mem::{offset_of,size_of,MaybeUninit};
use abi::{CInt,CULong,CpuLocalVar,ResourceSet,Process,Mckfd};
#[repr(C,align(64))] struct McsRwlockNodeIrqsave {irqsave:CULong}

extern "C" {
}

const _: () = {
    #[cfg(not(enable_tofu))]
    assert!(offset_of!(CpuLocalVar, resource_set) == 7912);
    #[cfg(enable_tofu)]
    assert!(offset_of!(CpuLocalVar, resource_set) == 24368);
    assert!(offset_of!(ResourceSet, pid1) == 320);
    assert!(offset_of!(Process, children_list) == 288);
    assert!(offset_of!(Process, children_lock) == 320);
    assert!(size_of::<McsRwlockNodeIrqsave>() == 64);
};

/// Read the current CPU's existing resource-set binding. The CPU-local pointer
/// returned by the existing ABI remains valid for this synchronous read. The
/// caller retains CPU affinity and owns the resource-set lifetime; this callback
/// neither obtains a reference nor interprets a possibly null resource-set value.
#[no_mangle]
pub unsafe extern "C" fn process_current_resource_set_bridge() -> *mut c_void {
    unsafe { (*get_this_cpu_local_var()).resource_set.cast() }
}

/// Perform existing last-child cleanup under pid1's children reader lock.
/// The resource set, pid1 process, initialized child-list head and lock storage
/// remain live, and pid1 stays stable throughout synchronous callbacks. The
/// cleanup callees retain their existing concurrency/ownership contracts. The
/// list-empty test is exactly head.next == head; no list mutation/free is added.
#[no_mangle]
pub unsafe extern "C" fn process_release_final_cleanup_bridge(resource_set_arg: *mut c_void) {
    let rset = resource_set_arg.cast::<ResourceSet>();
    let mut lock = MaybeUninit::<McsRwlockNodeIrqsave>::uninit();
    unsafe {
        process_mcs_reader_lock_bridge(
            core::ptr::addr_of_mut!((*(*rset).pid1).children_lock) as CULong,
            lock.as_mut_ptr().cast(),
        );
        let head = core::ptr::addr_of_mut!((*(*rset).pid1).children_list);
        if (*head).next == head {
            #[cfg(enable_tofu)]
            tof_utofu_finalize();
            hugefileobj_cleanup();
        }
        process_mcs_reader_unlock_bridge(
            core::ptr::addr_of_mut!((*(*rset).pid1).children_lock) as CULong,
            lock.as_mut_ptr().cast(),
        );
    }
}
use abi::AbiListHead;
use std::ptr::{addr_of_mut,null_mut};
#[derive(Clone,Debug,PartialEq,Eq)]
struct Event { kind:u8, next:usize, prev:usize }
struct Context {
 head:*mut AbiListHead,child:*mut AbiListHead,lock:usize,node:usize,
 mode:usize,locked:bool,events:Vec<Event>,
}
static mut CURRENT:*mut Context=null_mut();
static mut CPU:*mut CpuLocalVar=null_mut();
static mut GET_CALLS:usize=0;
unsafe fn event(c:&mut Context,kind:u8) {
 c.events.push(Event{kind,next:(*c.head).next as usize,prev:(*c.head).prev as usize});
}
#[no_mangle]
unsafe extern "C" fn get_this_cpu_local_var()->*mut CpuLocalVar {
 GET_CALLS+=1;CPU
}
#[no_mangle]
unsafe extern "C" fn process_mcs_reader_lock_bridge(lock:CULong,node:*mut c_void) {
 let c=&mut *CURRENT;assert!(!c.locked);assert_eq!(lock as usize,c.lock);
 assert_eq!(node as usize%64,0);c.node=node as usize;c.locked=true;event(c,b'L');
 if c.mode==1 {(*c.head).next=if (*c.head).next==c.head {c.child}else{c.head};}
}
#[no_mangle]
unsafe extern "C" fn process_mcs_reader_unlock_bridge(lock:CULong,node:*mut c_void) {
 let c=&mut *CURRENT;assert!(c.locked);assert_eq!(lock as usize,c.lock);assert_eq!(node as usize,c.node);
 event(c,b'U');c.locked=false;
}
#[no_mangle]
unsafe extern "C" fn hugefileobj_cleanup() {
 let c=&mut *CURRENT;assert!(c.locked);event(c,b'H');if c.mode==2 {(*c.head).next=c.child;}
}
#[cfg(enable_tofu)]
#[no_mangle]
unsafe extern "C" fn tof_utofu_finalize() {
 let c=&mut *CURRENT;assert!(c.locked);event(c,b'T');if c.mode==2 {(*c.head).next=c.child;}
}
unsafe extern "C" {
 fn c_process_current_resource_set_bridge()->*mut c_void;
 fn c_process_release_final_cleanup_bridge(rset:*mut c_void);
}
fn main(){unsafe{
 let mut count=0;
 let mut rsets:[Box<ResourceSet>;2]=[Box::new(std::mem::zeroed()),Box::new(std::mem::zeroed())];
 let mut cpus:[Box<CpuLocalVar>;2]=[Box::new(std::mem::zeroed()),Box::new(std::mem::zeroed())];
 for cpu in 0..2 {for binding in 0..3 {for _repeat in 0..3 {
  let value=if binding==0 {null_mut()}else{&mut *rsets[binding-1] as *mut ResourceSet};
  CPU=&mut *cpus[cpu];(*CPU).resource_set=value;
  let other=(cpu+1)%2;cpus[other].resource_set=if binding==0 {&mut *rsets[1]}else{null_mut()};
  let other_before=cpus[other].resource_set;
  for rust in [false,true] {
   GET_CALLS=0;
   let got=if rust {process_current_resource_set_bridge()}else{c_process_current_resource_set_bridge()};
   assert_eq!(got,value.cast());assert_eq!(GET_CALLS,1);assert_eq!((*CPU).resource_set,value);assert_eq!(cpus[other].resource_set,other_before);
  }
  count+=1;
 }}}
 for shape in 0..5 {for mode in 0..3 {for pid in [0,73,i32::MAX] {
  let mut proc:Box<Process>=Box::new(std::mem::zeroed());
  let mut rset:Box<ResourceSet>=Box::new(std::mem::zeroed());
  let mut child1:Box<AbiListHead>=Box::new(std::mem::zeroed());
  let mut child2:Box<AbiListHead>=Box::new(std::mem::zeroed());
  let head=addr_of_mut!(proc.children_list);let child=&mut *child1 as *mut AbiListHead;let tail=&mut *child2 as *mut AbiListHead;
  let mut c=Context{head,child,lock:addr_of_mut!(proc.children_lock) as usize,node:0,mode,locked:false,events:vec![]};CURRENT=&mut c;
  let mut traces=Vec::new();
  for rust in [false,true] {
   c.events.clear();c.locked=false;c.node=0;proc.pid=pid;rset.pid1=&mut *proc;
   child1.next=if shape==4 {tail}else{head};child1.prev=head;child2.next=head;child2.prev=child;
   (*head).next=match shape {0|3=>head,2=>null_mut(),_=>child};
   (*head).prev=match shape {0=>head,4=>tail,_=>child};
   let before_next=(*head).next;let before_prev=(*head).prev;
   let child_before=(child1.next,child1.prev,child2.next,child2.prev);
   // Independently predict the entire observer trace before calling either body.
   let mut expect=vec![Event{kind:b'L',next:before_next as usize,prev:before_prev as usize}];
   let mut next=if mode==1 {if before_next==head {child}else{head}}else{before_next};
   if next==head {
    if cfg!(enable_tofu) {expect.push(Event{kind:b'T',next:next as usize,prev:before_prev as usize});if mode==2 {next=child;}}
    expect.push(Event{kind:b'H',next:next as usize,prev:before_prev as usize});if mode==2 {next=child;}
   }
   expect.push(Event{kind:b'U',next:next as usize,prev:before_prev as usize});
   if rust {process_release_final_cleanup_bridge((&mut *rset as *mut ResourceSet).cast())}else{c_process_release_final_cleanup_bridge((&mut *rset as *mut ResourceSet).cast())}
   assert_eq!(c.events,expect,"independent oracle shape={shape} mode={mode}");assert!(!c.locked);
   assert_eq!((*head).next,next);assert_eq!((*head).prev,before_prev);
   assert_eq!((child1.next,child1.prev,child2.next,child2.prev),child_before);
   assert_eq!(rset.pid1,&mut *proc as *mut Process);assert_eq!(proc.pid,pid);assert_eq!(proc.children_lock.slock.head_tail,0);
   traces.push(c.events.clone());
  }
  assert_eq!(traces[0],traces[1]);count+=1;
 }}}
 CURRENT=null_mut();CPU=null_mut();assert_eq!(count,63);
 println!("PASS 63 scenarios/126 C+Rust calls; resource binding/null identity and reader-lock/empty-test/cleanup ordering; TOFU={}",cfg!(enable_tofu));
}}
