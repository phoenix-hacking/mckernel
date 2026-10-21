//! Exact extracted adoption method differential test. Linux/SDK effects below
//! are explicit deterministic adapters, not production ownership/ABI proof.
#![allow(dead_code, unused_assignments)]
use std::{cell::RefCell, ffi::c_void, ptr::{self,NonNull}, sync::{Arc,Mutex as StdMutex,atomic::{AtomicBool,Ordering}}};
#[derive(Clone,Copy,Debug,PartialEq,Eq)] struct Error(i32);
impl Error {fn to_errno(self)->i32{self.0}}
const EINVAL:Error=Error(-22);const EACCES:Error=Error(-13);const EBUSY:Error=Error(-16);
type Result<T=()>=std::result::Result<T,Error>;
fn errno(n:i32)->Error{Error(n)}
mod kernel {pub mod error {pub fn to_result(n:i32)->super::super::Result {if n<0{Err(super::super::Error(n))}else{Ok(())}}}}
macro_rules! pr_err {($($arg:tt)*)=>{STATE.with(|s|s.borrow_mut().logs.push(format!($($arg)*)))}}
#[derive(Clone,Copy,Debug,PartialEq,Eq)] enum Mode {Valid,ProcessErr,CurrentErr,WrongCurrent,PendingBusy,AlreadyRegistered,MirrorErr,ParentSlot,ParentGeneration,ParentCurrent,ChildErr,IhkErr(i32),MissingCalled,MissingPublished}
struct State {mode:Mode,trace:Vec<String>,logs:Vec<String>,reservation_drops:usize,ihk_calls:usize,callbacks:usize}
thread_local! {static STATE:RefCell<State>=RefCell::new(State{mode:Mode::Valid,trace:vec![],logs:vec![],reservation_drops:0,ihk_calls:0,callbacks:0});}
fn mode()->Mode{STATE.with(|s|s.borrow().mode)}
fn event(s:&str){STATE.with(|v|v.borrow_mut().trace.push(s.into()));}
struct Mutex<T>(StdMutex<T>);
impl<T> Mutex<T>{fn new(v:T)->Self{Self(StdMutex::new(v))}fn lock(&self)->std::sync::MutexGuard<'_,T>{self.0.lock().unwrap()}}
struct ProcessId(i32);
impl ProcessId {fn current()->Result<Self>{event("current");if mode()==Mode::CurrentErr{Err(Error(-3))}else{Ok(Self(if mode()==Mode::WrongCurrent{302}else{301}))}}fn same(&self,p:&Self)->bool{self.0==p.0}}
struct Process {pid:ProcessId,registration:Mutex<Option<Arc<Registration>>>,registration_pending:AtomicBool}
struct Registration {pid:i32,slot:u32,generation:u64,_pid:ProcessId,context:NonNull<c_void>}
impl Registration {fn new(pid:i32,slot:u32,generation:u64)->Arc<Self>{event(&format!("registration-new:{pid}"));Arc::new(Self{pid,slot,generation,_pid:ProcessId(pid),context:NonNull::new(pid as usize as *mut c_void).unwrap()})}fn acquire(slot:u32,generation:u64,current:ProcessId)->Result<Arc<Self>>{event("child-acquire");if mode()==Mode::ChildErr{Err(EINVAL)}else{Ok(Self::new(current.0,slot,generation))}}}
impl Drop for Registration {fn drop(&mut self){event(&format!("registration-drop:{}",self.pid));}}
struct RegistrationReservation<'a>(&'a Process);
impl Drop for RegistrationReservation<'_>{fn drop(&mut self){self.0.registration_pending.store(false,Ordering::Release);STATE.with(|s|s.borrow_mut().reservation_drops+=1);event("reservation-drop");}}
struct Mirror;
impl Mirror {fn inherited_registration(start:u64,end:u64)->Result<(Arc<Self>,Arc<Registration>)>{event(&format!("inherited:{start}:{end}"));if mode()==Mode::MirrorErr{return Err(EINVAL);}Ok((Arc::new(Self),Registration::new(if mode()==Mode::ParentCurrent{301}else{256},if mode()==Mode::ParentSlot{8}else{0},if mode()==Mode::ParentGeneration{2}else{1})))}}
impl Drop for Mirror {fn drop(&mut self){event("mirror-drop");}}
mod application_abi {#[derive(Clone,Copy)] pub struct ForkGeometryV3{pub root:u64,pub start:u64,pub length:u64}}
struct CurrentForkAdoptAttempt<'a>{process:&'a Arc<Process>,parent:&'a Arc<Registration>,child:&'a Arc<Registration>,mirror:&'a Arc<Mirror>,geometry:application_abi::ForkGeometryV3,called:bool,published:bool}
unsafe extern "C" fn current_fork_adopted_v4(context:*mut c_void,_descriptor:*const ())->i32{event("callback");STATE.with(|s|s.borrow_mut().callbacks+=1);let a=&mut*context.cast::<CurrentForkAdoptAttempt<'_>>();a.called=true;a.published=mode()!=Mode::MissingPublished;0}
unsafe fn ihk_os_application_adopt_current_v4(parent:*mut c_void,child:*mut c_void,geometry:*const application_abi::ForkGeometryV3,consumer:Option<unsafe extern "C" fn(*mut c_void,*const ())->i32>,context:*mut c_void)->i32{
    let g=&*geometry;event(&format!("ihk:{parent:p}:{child:p}:{}:{}:{}",g.root,g.start,g.length));STATE.with(|s|s.borrow_mut().ihk_calls+=1);
    if let Mode::IhkErr(n)=mode(){return n;}if mode()!=Mode::MissingCalled{consumer.unwrap()(context,ptr::null());}0
}
mod pre {use super::*;pub(super) struct Context{pub(super) slot:u32,pub(super) generation:u64,pub(super) process:Arc<Process>}
impl Context {fn process(&self)->Result<Arc<Process>>{event("process");if mode()==Mode::ProcessErr{Err(EINVAL)}else{Ok(self.process.clone())}}
    fn adopt_current_fork_v4(&self,descriptor:&[u8;24],compat:bool)->Result<isize> {
        let word=|at|u64::from_le_bytes(descriptor[at..at+8].try_into().unwrap());
        let (start,length,root)=if compat{let integer=|at|u32::from_le_bytes(descriptor[at..at+4].try_into().unwrap()) as u64;
            (integer(0),integer(4),integer(8))}else{(word(0),word(8),word(16))};
        let end=start.checked_add(length).ok_or(EINVAL)?;
        if root==0||root%4096!=0||start%4096!=0||length==0||length%4096!=0{return Err(EINVAL);}
        let process=self.process()?;let current=ProcessId::current()?;
        if !process.pid.same(&current){return Err(EACCES);}
        process.registration_pending.compare_exchange(false,true,Ordering::AcqRel,Ordering::Acquire).map_err(|_|EBUSY)?;
        let _reservation=RegistrationReservation(&process);
        if process.registration.lock().is_some(){return Err(EINVAL);}
        let (mirror,parent)=Mirror::inherited_registration(start,end)?;
        if parent.slot!=self.slot||parent.generation!=self.generation||self.generation==0||parent._pid.same(&current){return Err(EACCES);}
        let child=Registration::acquire(self.slot,self.generation,current)?;
        let geometry=super::application_abi::ForkGeometryV3{root,start,length};
        let mut attempt=CurrentForkAdoptAttempt{process:&process,parent:&parent,child:&child,mirror:&mirror,geometry,called:false,published:false};
        let status=unsafe {ihk_os_application_adopt_current_v4(parent.context.as_ptr(),child.context.as_ptr(),
            &geometry,Some(current_fork_adopted_v4),ptr::from_mut(&mut attempt).cast())};
        kernel::error::to_result(status)?;
        if !attempt.called||!attempt.published{return Err(errno(-71));}Ok(0)
    }

}
pub(super) fn execute(context:&Context,descriptor:&[u8;24],compat:bool)->Result<isize>{context.adopt_current_fork_v4(descriptor,compat)}
}
mod post {use super::*;pub(super) struct Context{pub(super) slot:u32,pub(super) generation:u64,pub(super) process:Arc<Process>}
impl Context {fn process(&self)->Result<Arc<Process>>{event("process");if mode()==Mode::ProcessErr{Err(EINVAL)}else{Ok(self.process.clone())}}
    fn adopt_current_fork_v4(&self,descriptor:&[u8;24],compat:bool)->Result<isize> {
        let word=|at|u64::from_le_bytes(descriptor[at..at+8].try_into().unwrap());
        let (start,length,root)=if compat{let integer=|at|u32::from_le_bytes(descriptor[at..at+4].try_into().unwrap()) as u64;
            (integer(0),integer(4),integer(8))}else{(word(0),word(8),word(16))};
        // Observation only: each stage precedes the existing fallible effect.
        // Unknown child_pid remains zero until the real child owner exists.
        let mut stage="geometry";let mut child_pid=0;
        let result=(||->Result<isize>{
            let end=start.checked_add(length).ok_or(EINVAL)?;
            if root==0||root%4096!=0||start%4096!=0||length==0||length%4096!=0{return Err(EINVAL);}
            stage="process";let process=self.process()?;
            stage="current-identity";let current=ProcessId::current()?;
            if !process.pid.same(&current){return Err(EACCES);}
            stage="pending-reservation";
            process.registration_pending.compare_exchange(false,true,Ordering::AcqRel,Ordering::Acquire).map_err(|_|EBUSY)?;
            let _reservation=RegistrationReservation(&process);
            stage="existing-registration";
            if process.registration.lock().is_some(){return Err(EINVAL);}
            stage="inherited-registration";let (mirror,parent)=Mirror::inherited_registration(start,end)?;
            stage="parent-identity";
            if parent.slot!=self.slot||parent.generation!=self.generation||self.generation==0||parent._pid.same(&current){return Err(EACCES);}
            stage="child-acquire";let child=Registration::acquire(self.slot,self.generation,current)?;
            child_pid=child.pid;
            let geometry=super::application_abi::ForkGeometryV3{root,start,length};
            let mut attempt=CurrentForkAdoptAttempt{process:&process,parent:&parent,child:&child,mirror:&mirror,geometry,called:false,published:false};
            stage="ihk-adopt";
            let status=unsafe {ihk_os_application_adopt_current_v4(parent.context.as_ptr(),child.context.as_ptr(),
                &geometry,Some(current_fork_adopted_v4),ptr::from_mut(&mut attempt).cast())};
            kernel::error::to_result(status)?;
            stage="callback-publication";
            if !attempt.called||!attempt.published{return Err(errno(-71));}Ok(0)
        })();
        if let Err(error)=&result {
            pr_err!("application_fork_adoption=failed os={} generation={} stage={} errno={} compat={} start={} length={} root={} child_pid={}\n",
                self.slot,self.generation,stage,error.to_errno(),compat,start,length,root,child_pid);
        }
        result
    }

}
pub(super) fn execute(context:&Context,descriptor:&[u8;24],compat:bool)->Result<isize>{context.adopt_current_fork_v4(descriptor,compat)}
}
#[derive(Debug,PartialEq,Eq)]struct Observation{result:Result<isize>,trace:Vec<String>,drops:usize,ihk:usize,callbacks:usize,pending:bool}
fn process(m:Mode)->Arc<Process>{Arc::new(Process{pid:ProcessId(301),registration:Mutex::new(if m==Mode::AlreadyRegistered{Some(Registration::new(999,0,1))}else{None}),registration_pending:AtomicBool::new(m==Mode::PendingBusy)})}
fn run(m:Mode,bytes:&[u8;24],compat:bool,diagnostic:bool)->(Observation,Vec<String>){
    STATE.with(|s|*s.borrow_mut()=State{mode:m,trace:vec![],logs:vec![],reservation_drops:0,ihk_calls:0,callbacks:0});
    let process=process(m);let (result,pending)=if diagnostic{let c=post::Context{slot:0,generation:1,process};let r=post::execute(&c,bytes,compat);(r,c.process.registration_pending.load(Ordering::Acquire))}else{let c=pre::Context{slot:0,generation:1,process};let r=pre::execute(&c,bytes,compat);(r,c.process.registration_pending.load(Ordering::Acquire))};
    STATE.with(|s|{let s=s.borrow();(Observation{result,trace:s.trace.clone(),drops:s.reservation_drops,ihk:s.ihk_calls,callbacks:s.callbacks,pending},s.logs.clone())})
}
mod candidate {use super::*;pub(super) struct Context{pub(super) slot:u32,pub(super) generation:u64,pub(super) process:Arc<Process>}
impl Context {fn process(&self)->Result<Arc<Process>>{event("process");if mode()==Mode::ProcessErr{Err(EINVAL)}else{Ok(self.process.clone())}}
    fn adopt_current_fork_v4(&self,descriptor:&[u8;24],compat:bool)->Result<isize> {
        let word=|at|u64::from_le_bytes(descriptor[at..at+8].try_into().unwrap());
        let (start,length,root)=if compat{let integer=|at|u32::from_le_bytes(descriptor[at..at+4].try_into().unwrap()) as u64;
            (integer(4),integer(8),integer(0))}else{(word(8),word(16),word(0))};
        // Observation only: each stage precedes the existing fallible effect.
        // Unknown child_pid remains zero until the real child owner exists.
        let mut stage="geometry";let mut child_pid=0;
        let result=(||->Result<isize>{
            let end=start.checked_add(length).ok_or(EINVAL)?;
            if root==0||root%4096!=0||start%4096!=0||length==0||length%4096!=0{return Err(EINVAL);}
            stage="process";let process=self.process()?;
            stage="current-identity";let current=ProcessId::current()?;
            if !process.pid.same(&current){return Err(EACCES);}
            stage="pending-reservation";
            process.registration_pending.compare_exchange(false,true,Ordering::AcqRel,Ordering::Acquire).map_err(|_|EBUSY)?;
            let _reservation=RegistrationReservation(&process);
            stage="existing-registration";
            if process.registration.lock().is_some(){return Err(EINVAL);}
            stage="inherited-registration";let (mirror,parent)=Mirror::inherited_registration(start,end)?;
            stage="parent-identity";
            if parent.slot!=self.slot||parent.generation!=self.generation||self.generation==0||parent._pid.same(&current){return Err(EACCES);}
            stage="child-acquire";let child=Registration::acquire(self.slot,self.generation,current)?;
            child_pid=child.pid;
            let geometry=super::application_abi::ForkGeometryV3{root,start,length};
            let mut attempt=CurrentForkAdoptAttempt{process:&process,parent:&parent,child:&child,mirror:&mirror,geometry,called:false,published:false};
            stage="ihk-adopt";
            let status=unsafe {ihk_os_application_adopt_current_v4(parent.context.as_ptr(),child.context.as_ptr(),
                &geometry,Some(current_fork_adopted_v4),ptr::from_mut(&mut attempt).cast())};
            kernel::error::to_result(status)?;
            stage="callback-publication";
            if !attempt.called||!attempt.published{return Err(errno(-71));}Ok(0)
        })();
        if let Err(error)=&result {
            pr_err!("application_fork_adoption=failed os={} generation={} stage={} errno={} compat={} start={} length={} root={} child_pid={}\n",
                self.slot,self.generation,stage,error.to_errno(),compat,start,length,root,child_pid);
        }
        result
    }

}
pub(super) fn execute(context:&Context,descriptor:&[u8;24],compat:bool)->Result<isize>{context.adopt_current_fork_v4(descriptor,compat)}
}

extern "C" { fn fixture_capture_descriptor(start:u64,length:u64,root:u64,output:*mut u8)->i32; }
fn c_descriptor(start:u64,length:u64,root:u64)->[u8;24] {let mut d=[0;24];assert_eq!(unsafe{fixture_capture_descriptor(start,length,root,d.as_mut_ptr())},0);d}
fn run_candidate(bytes:&[u8;24],compat:bool,m:Mode)->(Result<isize>,Vec<String>,Vec<String>) {
 STATE.with(|s|*s.borrow_mut()=State{mode:m,trace:vec![],logs:vec![],reservation_drops:0,ihk_calls:0,callbacks:0});
 let c=candidate::Context{slot:0,generation:1,process:process(m)};
 let result=candidate::execute(&c,bytes,compat);
 STATE.with(|s|{let s=s.borrow();(result,s.trace.clone(),s.logs.clone())})
}
#[test]fn actual_c_producer_and_current_rust_consumer_permute_distinct_fixture_fields(){
 let d=c_descriptor(0x4000,0x8000,0x1000);
 assert_eq!(d,[0x1000u64.to_le_bytes(),0x4000u64.to_le_bytes(),0x8000u64.to_le_bytes()].concat().as_slice());
 let(observation,logs)=run(Mode::IhkErr(-22),&d,false,true);
 assert_eq!(observation.result,Err(EINVAL));
 assert!(observation.trace.iter().any(|s|s.ends_with(":32768:4096:16384")),"current decoder must retain wrong root/start/length as observation");
 assert!(logs[0].contains("stage=ihk-adopt errno=-22 compat=false start=4096 length=16384 root=32768"));
 println!("C fixture root=4096/start=16384/length=32768; current Rust root=32768/start=4096/length=16384");
}
#[test]fn private_decoder_order_candidate_preserves_c_fields_and_error_stage(){
 let d=c_descriptor(0x4000,0x8000,0x1000);
 let(result,trace,logs)=run_candidate(&d,false,Mode::Valid);assert_eq!(result,Ok(0));assert!(logs.is_empty());assert!(trace.iter().any(|s|s.ends_with(":4096:16384:32768")));
 for (start,length,root) in [(0x4000,0x8000,0),(0x4001,0x8000,0x1000),(0x4000,0,0x1000),(0x4000,0x8001,0x1000),(0x4000,0x8000,0x1001),(u64::MAX-4095,4096,4096)] {
  let d=c_descriptor(start,length,root);let(result,trace,logs)=run_candidate(&d,false,Mode::Valid);
  assert_eq!(result,Err(EINVAL));assert!(trace.is_empty());assert_eq!(logs.len(),1);assert!(logs[0].contains("stage=geometry errno=-22"));
 }
 let(result,_,logs)=run_candidate(&d,false,Mode::IhkErr(-22));assert_eq!(result,Err(EINVAL));assert!(logs[0].contains("stage=ihk-adopt errno=-22 compat=false start=16384 length=32768 root=4096"));
}
#[test]fn private_compat_decoder_order_uses_source_layout_only_not_actual_i386_producer(){
 let mut d=[0;24];for(i,n)in[0x1000u32,0x4000,0x8000].into_iter().enumerate(){d[i*4..i*4+4].copy_from_slice(&n.to_le_bytes());}
 let(result,trace,logs)=run_candidate(&d,true,Mode::Valid);assert_eq!(result,Ok(0));assert!(logs.is_empty());assert!(trace.iter().any(|s|s.ends_with(":4096:16384:32768")));
}
