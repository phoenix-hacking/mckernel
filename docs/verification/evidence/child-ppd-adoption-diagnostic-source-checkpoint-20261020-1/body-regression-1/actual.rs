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
macro_rules! fixture {($name:ident,$method:literal)=>{mod $name{use super::*;pub(super) struct Context{pub(super) slot:u32,pub(super) generation:u64,pub(super) process:Arc<Process>}
    impl Context {fn process(&self)->Result<Arc<Process>>{event("process");if mode()==Mode::ProcessErr{Err(EINVAL)}else{Ok(self.process.clone())}}
    include!($method);
    pub(super) fn execute(context:&Context,descriptor:&[u8;24],compat:bool)->Result<isize>{context.adopt_current_fork_v4(descriptor,compat)}
}}}
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
fn descriptor(start:u64,length:u64,root:u64,compat:bool)->[u8;24]{let mut d=[0u8;24];if compat{for(i,n)in[start,length,root].into_iter().enumerate(){d[i*4..i*4+4].copy_from_slice(&(n as u32).to_le_bytes());}d[12..].fill(0xa5);}else{for(i,n)in[start,length,root].into_iter().enumerate(){d[i*8..i*8+8].copy_from_slice(&n.to_le_bytes());}}d}
fn differential(m:Mode,start:u64,length:u64,root:u64,compat:bool,stage:Option<&str>,expected:Result<isize>,drops:usize,ihk:usize,callbacks:usize){
    let bytes=descriptor(start,length,root,compat);let(a,al)=run(m,&bytes,compat,false);let(b,bl)=run(m,&bytes,compat,true);assert_eq!(a,b,"body difference: {m:?}");assert_eq!(a.result,expected,"wrong errno: {m:?}");assert_eq!((a.drops,a.ihk,a.callbacks),(drops,ihk,callbacks),"wrong effects: {m:?}");assert_eq!(a.pending,m==Mode::PendingBusy);assert!(al.is_empty());
    if let Some(stage)=stage{assert_eq!(bl.len(),1);let decoded=if compat{(start as u32 as u64,length as u32 as u64,root as u32 as u64)}else{(start,length,root)};let child=if ihk==1{301}else{0};let expected=format!("application_fork_adoption=failed os=0 generation=1 stage={stage} errno={} compat={compat} start={} length={} root={} child_pid={child}\n",expected.unwrap_err().0,decoded.0,decoded.1,decoded.2);assert_eq!(bl[0],expected);}else{assert!(bl.is_empty());}
}
#[test]fn exact_adoption_methods_preserve_geometry_errors_and_effects(){for(start,length,root)in[(0,4096,0),(0,4096,4097),(1,4096,4096),(0,0,4096),(0,4097,4096),(u64::MAX-4095,4096,4096)]{differential(Mode::Valid,start,length,root,false,Some("geometry"),Err(EINVAL),0,0,0);}}
#[test]fn exact_adoption_methods_preserve_all_error_stages_and_ownership(){for(m,stage,err,drops,ihk,callbacks)in[
    (Mode::ProcessErr,"process",-22,0,0,0),(Mode::CurrentErr,"current-identity",-3,0,0,0),(Mode::WrongCurrent,"current-identity",-13,0,0,0),(Mode::PendingBusy,"pending-reservation",-16,0,0,0),(Mode::AlreadyRegistered,"existing-registration",-22,1,0,0),(Mode::MirrorErr,"inherited-registration",-22,1,0,0),(Mode::ParentSlot,"parent-identity",-13,1,0,0),(Mode::ParentGeneration,"parent-identity",-13,1,0,0),(Mode::ParentCurrent,"parent-identity",-13,1,0,0),(Mode::ChildErr,"child-acquire",-22,1,0,0),(Mode::IhkErr(-22),"ihk-adopt",-22,1,1,0),(Mode::IhkErr(-13),"ihk-adopt",-13,1,1,0),(Mode::IhkErr(-71),"ihk-adopt",-71,1,1,0),(Mode::MissingCalled,"callback-publication",-71,1,1,0),(Mode::MissingPublished,"callback-publication",-71,1,1,1)]{differential(m,0,8192,4096,false,Some(stage),Err(Error(err)),drops,ihk,callbacks);}}
#[test]fn exact_adoption_methods_decode_lp64_and_compat_and_preserve_success(){for compat in[false,true]{differential(Mode::Valid,0,8192,4096,compat,None,Ok(0),1,1,1);differential(Mode::IhkErr(-22),0,8192,4096,compat,Some("ihk-adopt"),Err(EINVAL),1,1,0);}}
