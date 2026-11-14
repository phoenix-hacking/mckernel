from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent
s=(D/'candidate/smp_application.rs').read_text()
def body(src,start):
 a=src.index(start);op=src.index('{',a);depth=1;i=op+1
 while depth:
  if src[i]=='{':depth+=1
  if src[i]=='}':depth-=1
  i+=1
 return src[a:i]
helper=body(s,'    fn current_host_start_child(')
a=s.index('        if published {',s.index('pub(crate) fn publish_syscall'));b=s.index('        let entry = slots',a);publication=s[a:b]
fixture='''#![allow(dead_code)]
use std::sync::atomic::{AtomicBool,Ordering};
type Token=u64; type Result<T=()>=std::result::Result<T,i32>;
const EACCES:i32=-13;const ENOENT:i32=-2;fn errno(e:i32)->i32{e}
#[derive(Clone)]struct Request{a:[u64;6],pid:i32,cpu:i32,requester:i32,target:i32}
impl Request{fn arguments(&self)->[u64;6]{self.a}fn cpu(&self)->i32{self.cpu}fn pid(&self)->i32{self.pid}fn requester(&self)->i32{self.requester}fn target(&self)->i32{self.target}}
struct Mailbox{call:Option<(u64,u64,Request)>,open:bool,completed:Option<(u64,u64)>}
impl Mailbox{fn has_open_worker(&self)->bool{self.open}fn unique_delivered_fork(&self,f:impl Fn(&Request)->bool)->Result<Option<(u64,u64,Request)>>{Ok(self.call.as_ref().filter(|(_,_,r)|f(r)).cloned())}fn returned(&self,w:u64,s:u64)->Result<bool>{Ok(self.completed==Some((w,s)))}}
struct Cleanup{pid:i32}impl Cleanup{fn pid(&self)->i32{self.pid}}
struct ChildTask{pid:i32}impl ChildTask{fn tgid(&self)->i32{self.pid}}
struct Response{r:Request}impl Response{fn request(&self)->&Request{&self.r}}
struct Owner{parent:Token,child:Token,child_task:ChildTask,host_start_return:Option<(u64,u64)>,host_revoke:Option<()>,sealed:AtomicBool,first_return_published:bool,response:Response}
struct Image{start:u64,end:u64,root:u64}
struct Entry{key:Token,cleanup:Cleanup,syscalls:Mailbox,fork_ingress:Option<Owner>,inherited_root:Option<Image>,closed:bool,needs_cleanup:bool,quarantined:bool,scheduled:bool}
impl Entry{fn key(&self)->Token{self.key}fn backend_ready(&self)->Result{if self.fork_ingress.as_ref().is_some_and(|o|o.sealed.load(Ordering::Acquire)&&o.host_revoke.is_none()){Ok(())}else{Err(EACCES)}}}
struct Remote;impl Remote{
'''+helper+'''
fn publish_actualbody(&self,slots:&mut [Option<Entry>],token:Token,published:bool)->Result{
'''+publication+'''Ok(())}}
fn setup()->Vec<Option<Entry>>{
 let marker=0x313030434b46434d;
 let original=Request{a:[0,0x1000,0x2000,0x3000,0x4000,marker],pid:255,cpu:0,requester:255,target:0};
 let start=Request{a:[1,258,0x2000,0x3000,0x4000,marker],..original.clone()};
 let entry=|key,pid,call,owner,image|Some(Entry{key,cleanup:Cleanup{pid},syscalls:Mailbox{call,open:true,completed:None},fork_ingress:owner,inherited_root:image,closed:false,needs_cleanup:false,quarantined:false,scheduled:key==10});
 vec![entry(10,255,Some((6,35,start)),None,None),entry(20,258,None,Some(Owner{parent:10,child:20,child_task:ChildTask{pid:258},host_start_return:None,host_revoke:None,sealed:AtomicBool::new(true),first_return_published:true,response:Response{r:original}}),Some(Image{start:0x1000,end:0x3000,root:0x3000}))]
}
fn select(v:&[Option<Entry>])->Result<Option<usize>>{Remote.current_host_start_child(v,10,6,35,0,0,0)}
#[test]fn exact_host_start_selects_owned_child(){assert_eq!(select(&setup()),Ok(Some(1)));}
#[test]fn failed_start_never_schedules(){assert_eq!(Remote.current_host_start_child(&setup(),10,6,35,0,-10,0),Ok(None));}
#[test]fn wrong_worker_is_not_this_return(){assert_eq!(Remote.current_host_start_child(&setup(),10,7,35,0,0,0),Ok(None));}
#[test]fn requires_real_first_publication(){let mut v=setup();v[1].as_mut().unwrap().fork_ingress.as_mut().unwrap().first_return_published=false;assert_eq!(select(&v),Err(EACCES));}
#[test]fn rejects_wrong_carrier_root_and_requester(){for field in 0..3{let mut v=setup();let r=&mut v[0].as_mut().unwrap().syscalls.call.as_mut().unwrap().2;match field{0=>r.a[4]+=8,1=>r.a[3]+=4096,_=>r.requester+=1};assert_eq!(select(&v),Err(EACCES));}}
#[test]fn rejects_closed_quarantined_revoke_and_missing_worker(){for field in 0..4{let mut v=setup();let c=v[1].as_mut().unwrap();match field{0=>c.closed=true,1=>c.quarantined=true,2=>c.fork_ingress.as_mut().unwrap().host_revoke=Some(()),_=>c.syscalls.open=false};assert_eq!(select(&v),Err(EACCES));}}
#[test]fn scheduled_only_after_exact_published_ret(){let mut v=setup();assert_eq!(select(&v),Ok(Some(1)));v[1].as_mut().unwrap().fork_ingress.as_mut().unwrap().host_start_return=Some((6,35));Remote.publish_actualbody(&mut v,10,true).unwrap();assert!(!v[1].as_ref().unwrap().scheduled);v[0].as_mut().unwrap().syscalls.completed=Some((6,34));Remote.publish_actualbody(&mut v,10,true).unwrap();assert!(!v[1].as_ref().unwrap().scheduled);v[0].as_mut().unwrap().syscalls.completed=Some((6,35));Remote.publish_actualbody(&mut v,10,false).unwrap();assert!(!v[1].as_ref().unwrap().scheduled);Remote.publish_actualbody(&mut v,10,true).unwrap();assert!(v[1].as_ref().unwrap().scheduled);assert!(v[1].as_ref().unwrap().fork_ingress.is_some());}
#[test]fn retains_adoption_and_does_not_set_destructor_ack(){let mut v=setup();let c=v[1].as_mut().unwrap();c.fork_ingress.as_mut().unwrap().host_start_return=Some((6,35));v[0].as_mut().unwrap().syscalls.completed=Some((6,35));Remote.publish_actualbody(&mut v,10,true).unwrap();let o=v[1].as_ref().unwrap().fork_ingress.as_ref().unwrap();assert!(o.host_revoke.is_none());assert_eq!(o.child_task.tgid(),258);}
'''
(D/'actualbody-start.rs').write_text(fixture)
l=(D/'candidate/mcexec_helpers.rs').read_text();main=body(l,'pub unsafe extern "C" fn act_main_loop_body(')
# Use an actual subprocess to verify exit status, matching the bridge's contract.
launcher='''#![allow(dead_code,non_camel_case_types)]
type c_int=i32;type c_long=i64;type c_ulong=u64;use std::ffi::c_void;
const PATH_MAX:usize=4096;const EINTR:i32=4;const MCEXEC_UP_WAIT_SYSCALL:c_ulong=0x30a02903;
struct McexecThreadData{cpu:c_int,remote_tid:c_int}
struct McexecSyscallRequest{rtid:i32,ttid:i32,valid:i32,number:c_ulong,args:[c_ulong;6]}
struct McexecSyscallWaitDesc{cpu:c_ulong,sr:McexecSyscallRequest,pid:i32}
unsafe fn getpid()->i32{255}static mut ERRNO:i32=22;unsafe fn __errno_location()->*mut i32{&raw mut ERRNO}
unsafe fn ioctl(_:i32,_:u64,_:u64)->i32{-1}
unsafe fn act_main_loop_iteration(_:&McexecSyscallWaitDesc,_:i32,_:*mut McexecThreadData,_:*mut u8,_:*mut u8,_:*mut i64,_:i32)->i32{panic!("failed WAIT cannot dispatch")}
unsafe fn mcexec_main_loop_timeout_bridge(){}unsafe fn mcexec_exit_cmd_servers_bridge(){}
unsafe fn mcexec_exit_process_bridge(status:i32){std::process::exit(status)}
'''+main+'''
fn main(){let mut td=McexecThreadData{cpu:0,remote_tid:0};let _=unsafe{act_main_loop_body(&mut td,3,0)};std::process::exit(0)}
'''
(D/'actualbody-launcher.rs').write_text(launcher)
(D/'ACTUALBODY-SOURCE-BINDING.json').write_text(json.dumps({'method':'exact brace-delimited candidate body extraction; stubs are fixture-only','source_sha256':hashlib.sha256(s.encode()).hexdigest(),'launcher_sha256':hashlib.sha256(l.encode()).hexdigest(),'host_start_helper_sha256':hashlib.sha256(helper.encode()).hexdigest(),'publication_block_sha256':hashlib.sha256(publication.encode()).hexdigest(),'launcher_main_loop_body_sha256':hashlib.sha256(main.encode()).hexdigest()},indent=2)+'\n')
p=(D/'candidate/mcctrl_process.rs').read_text();pool=body(p,'    pub(super) fn pool_thread_limit(').replace('pub(super) fn','fn',1)
# Only visibility adapts for the standalone crate; entire executable body is exact.
fixture='''#![allow(dead_code,non_camel_case_types,non_upper_case_globals)]
use std::{ptr,sync::{Mutex,MutexGuard,atomic::{AtomicUsize,Ordering}},ptr::NonNull};
type Result<T=()>=std::result::Result<T,i32>;const EIO:i32=-5;
struct Lock<T>(Mutex<T>);impl<T> Lock<T>{fn lock(&self)->MutexGuard<'_,T>{self.0.lock().unwrap()}}
mod bindings {
use super::*;
pub struct Signal{pub nr_threads:i32}pub struct task_struct{pub signal:*mut Signal}pub struct pid{pub task:*mut task_struct}
pub struct Mask{pub bits:[u64;1]}pub static mut __cpu_online_mask:Mask=Mask{bits:[3]};pub static mut nr_cpu_ids:u32=2;
pub const pid_type_PIDTYPE_TGID:u32=1;pub static GET:AtomicUsize=AtomicUsize::new(0);pub static PUT:AtomicUsize=AtomicUsize::new(0);pub static CPU:AtomicUsize=AtomicUsize::new(0);
pub unsafe fn get_pid_task(pid:*mut pid,_:u32)->*mut task_struct{let t=(*pid).task;if !t.is_null(){GET.fetch_add(1,Ordering::SeqCst);}t}
pub unsafe fn put_task_struct(_:*mut task_struct){PUT.fetch_add(1,Ordering::SeqCst);}
pub unsafe fn cpus_read_lock(){CPU.fetch_add(1,Ordering::SeqCst);}pub unsafe fn cpus_read_unlock(){CPU.fetch_sub(1,Ordering::SeqCst);}
}
struct ProcessId(NonNull<bindings::pid>);unsafe impl Send for ProcessId{}
struct Process{slot:u32,generation:u64,registration:Lock<Option<()>>,pid:ProcessId}
struct Entry{process:Process}static TABLE:Lock<Vec<Entry>>=Lock(Mutex::new(Vec::new()));fn table()->&'static Lock<Vec<Entry>>{&TABLE}
struct Context{slot:u32,generation:u64}impl Context{fn registered(&self)->Result{Ok(())}
'''+pool+'''
}
fn setup(counts:&[(u32,u64,i32,bool)]){let mut entries=table().lock();entries.clear();for &(slot,generation,n,registered) in counts{let signal=Box::into_raw(Box::new(bindings::Signal{nr_threads:n}));let task=Box::into_raw(Box::new(bindings::task_struct{signal}));let pid=Box::into_raw(Box::new(bindings::pid{task}));entries.push(Entry{process:Process{slot,generation,registration:Lock(Mutex::new(if registered{Some(())}else{None})),pid:ProcessId(NonNull::new(pid).unwrap())}});}bindings::GET.store(0,Ordering::SeqCst);bindings::PUT.store(0,Ordering::SeqCst);unsafe{bindings::__cpu_online_mask.bits=[3];}}
#[test]fn legacy_threshold_and_scope(){let c=Context{slot:0,generation:1};setup(&[(0,1,128,true),(0,1,128,true),(1,1,999,true),(0,2,999,true),(0,1,999,false)]);assert_eq!(c.pool_thread_limit(),Ok(0));assert_eq!(bindings::GET.load(Ordering::SeqCst),2);assert_eq!(bindings::PUT.load(Ordering::SeqCst),2);setup(&[(0,1,128,true),(0,1,129,true)]);assert_eq!(c.pool_thread_limit(),Ok(1));assert_eq!(bindings::CPU.load(Ordering::SeqCst),0);}
#[test]fn zero_online_is_error_and_references_balance(){setup(&[(0,1,4,true)]);unsafe{bindings::__cpu_online_mask.bits=[0];}assert_eq!(Context{slot:0,generation:1}.pool_thread_limit(),Err(EIO));assert_eq!(bindings::GET.load(Ordering::SeqCst),bindings::PUT.load(Ordering::SeqCst));assert_eq!(bindings::CPU.load(Ordering::SeqCst),0);}
'''
(D/'actualbody-pool.rs').write_text(fixture)
binding=json.loads((D/'ACTUALBODY-SOURCE-BINDING.json').read_text());binding['pool_body_sha256']=hashlib.sha256(pool.encode()).hexdigest();binding['pool_source_sha256']=hashlib.sha256(p.encode()).hexdigest();binding['pool_visibility_only_adjustment']='pub(super) fn to fn for standalone crate';(D/'ACTUALBODY-SOURCE-BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
import re
m=(D/'candidate/mcctrl.rs').read_text();dispatch=body(m,'unsafe extern "C" fn ioctl(')
abi=(Path('/home/holden/mckernel-work/host-preparation/m05-sdk68-current-source-bundle-20261022-1/source-modules/abi/x86_64.rs')).read_text()
constants='\n'.join(re.search(r'pub const '+name+r':[^;]+;',abi).group(0) for name in sorted(set(re.findall(r'abi::(MCEXEC_UP_[A-Z_]+)',dispatch))))
fixture='''#![allow(dead_code,non_upper_case_globals)]
use std::ffi::c_void;use std::sync::atomic::{AtomicI32,Ordering};
#[derive(Clone,Copy)]struct Error(i32);impl Error{fn to_errno(&self)->i32{self.0}}
const EINVAL:Error=Error(-22);type Result<T>=std::result::Result<T,Error>;
mod abi{'''+constants+'''}
mod service_abi{pub fn topology_query(c:u32)->bool{c==super::abi::MCEXEC_UP_GET_CPU}}
mod mcctrl_exec{use super::*;pub fn credentials(_:usize)->Result<isize>{Ok(0)}pub fn copy_string(_:usize,_:bool)->Result<isize>{Ok(0)}}
struct FileContext{slot:u32,generation:u64,pool:AtomicI32,calls:AtomicI32}
impl FileContext{fn pool_thread_limit(&self)->Result<isize>{self.calls.fetch_add(1,Ordering::SeqCst);let v=self.pool.load(Ordering::SeqCst);if v<0{Err(Error(v))}else{Ok(v as isize)}}
'''
for name in ('open_executable','close_executable','create_process','prepare_image','start_image','transfer_image','wait_syscall','return_syscall','clear_user_space'):
 args='' if name=='close_executable' else '_:usize' if name=='open_executable' else '_:usize,_:bool'
 fixture+=f'fn {name}(&self{"," if args else ""}{args})->Result<isize>{{Ok(0)}}\n'
fixture+='''}
unsafe fn ihk_os_topology_query_v1(_:u32,_:u64,_:u32)->i64{0}
'''+dispatch+'''
fn context(v:i32)->FileContext{FileContext{slot:0,generation:1,pool:AtomicI32::new(v),calls:AtomicI32::new(0)}}
fn call(c:&FileContext,arg:u64,compat:u32)->i64{unsafe{ioctl(c as *const _ as *mut c_void,abi::MCEXEC_UP_GET_NUM_POOL_THREADS,arg,compat)}}
#[test]fn actual_dispatch_preserves_predicate_and_error(){for value in [0,1,-5]{let c=context(value);assert_eq!(call(&c,0,0),value as i64);assert_eq!(c.calls.load(Ordering::SeqCst),1);}}
#[test]fn actual_dispatch_compat_gates_precede_handler(){let c=context(1);assert_eq!(call(&c,0,2),-22);assert_eq!(call(&c,1u64<<32,1),-22);assert_eq!(c.calls.load(Ordering::SeqCst),0);assert_eq!(call(&c,u32::MAX as u64,1),1);}
#[test]fn unknown_command_still_errors(){let c=context(1);assert_eq!(unsafe{ioctl(&c as *const _ as *mut c_void,0xff,0,0)},-22);assert_eq!(c.calls.load(Ordering::SeqCst),0);}
'''
(D/'actualbody-dispatch.rs').write_text(fixture)
binding=json.loads((D/'ACTUALBODY-SOURCE-BINDING.json').read_text());binding['mcctrl_dispatch_body_sha256']=hashlib.sha256(dispatch.encode()).hexdigest();binding['mcctrl_source_sha256']=hashlib.sha256(m.encode()).hexdigest();(D/'ACTUALBODY-SOURCE-BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
