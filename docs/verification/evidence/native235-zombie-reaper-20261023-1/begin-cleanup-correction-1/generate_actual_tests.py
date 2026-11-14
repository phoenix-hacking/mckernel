"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Extract frozen production bodies; Linux locking/FFI/clock are explicit adapters.
"""
from pathlib import Path
import hashlib,json,sys,shutil
sys.path.insert(0,str(Path.cwd()))
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item as item
O=Path(__file__).resolve().parent
E=O.parent
T=O/'actual-tests';T.mkdir(exist_ok=True)
old=(E/'candidate-actual.rs').read_text()
consumer=(O/'consumer/mcctrl_process.rs').read_text()
remote=(O/'provider/smp_application.rs').read_text()
service=(O/'provider/smp_service.rs').read_text()
dispatch=(O/'provider/ihk_smp_x86_64.rs').read_text()
abi=(O/'provider/abi/application.rs').read_text()
source=old
source=source.replace('Option<(mailbox::Mailbox<TestMemory>,Arc<TestRam>)>','Option<(SharedMailbox,Arc<TestRam>)>')
source=source.replace('BACKEND.with(|b|*b.borrow_mut()=Some((q,ram)));','let q=SharedMailbox(std::rc::Rc::new(std::cell::RefCell::new(q))); setup_provider(q.clone()); BACKEND.with(|b|*b.borrow_mut()=Some((q,ram)));')
source=source.replace('pub const CLEANUP:u32=4;pub const WORKER_CLOSE:u32=5;', 'pub const CLEANUP:u32=1;pub const BEGIN_CLEANUP:u32=22;pub const WORKER_CLOSE:u32=6;')
for name in ['CLEANUP','BEGIN_CLEANUP','WORKER_CLOSE']:
 assert f'const {name}: u32 = '+str({'CLEANUP':1,'BEGIN_CLEANUP':22,'WORKER_CLOSE':6}[name])+';' in abi
for signature in ['fn request_cleanup(&self)','fn detach_owners(&self)']:
 source=source.replace(item(source,signature),item(consumer,signature))
oldffi=item(source,'unsafe fn ihk_os_application_invoke_v1(')
source=source.replace(oldffi,'''unsafe fn ihk_os_application_invoke_v1(context:*mut c_void,command:u32,buffer:*mut u8,bytes:usize)->i64 {
 crate::CLEANUPS.with(|n|n.set(n.get()+1));
 crate::invoke_context(context as usize,command,buffer,bytes) as i64
}''')
shared=r'''
// Adapter only: each shared handle aliases the SAME real production mailbox.
#[derive(Clone)]struct SharedMailbox(std::rc::Rc<std::cell::RefCell<mailbox::Mailbox<TestMemory>>>);
impl SharedMailbox {
 fn close(&mut self)->Result<(),i32>{self.0.borrow_mut().close()}
 fn close_worker(&mut self,h:u64)->Result<(),i32>{self.0.borrow_mut().close_worker(h)}
 fn drained(&self)->bool{self.0.borrow().drained()}
 fn publish(&mut self,cpu:i32,f:impl FnOnce(&[u8;128])->Result<(),i32>)->Result<bool,i32>{self.0.borrow_mut().publish(cpu,f)}
}
thread_local! {static PROVIDER:std::cell::RefCell<Option<Arc<provider::Remote>>>=const{std::cell::RefCell::new(None)};static SLOTS_HELD:std::cell::Cell<bool>=const{std::cell::Cell::new(false)};static NOTIFICATIONS:std::cell::Cell<usize>=const{std::cell::Cell::new(0)};}
pub mod error{pub fn to_result(v:i32)->Result<(),i32>{if v<0{Err(v)}else{Ok(())}}}
mod provider {
 use super::*;use application_rpc::{Exchange,Token};
 type Result<T=()> = std::result::Result<T,i32>;const ENOENT:i32=-2;const EINVAL:i32=-22;fn errno(v:i32)->i32{v}
 mod bindings{pub unsafe fn ktime_get_seconds()->i64{0}}
 // Explicit std/clock/procfs/preparation adapters; main vectors have no procfs
 // or preparation. Exchange, request_cleanup and mailbox/response are real bodies.
 struct Input{cpu:i32}struct Preparation{input:Input,thread:u64}
 impl Preparation{fn result(&self)->Option<i32>{None}}
 struct ProcfsProcess;impl ProcfsProcess{fn close(&self){}fn drained(&self)->bool{true}fn threads_retired(&self)->bool{false}}
 struct Mutex<T>(std::sync::Mutex<T>);
 struct Guard<'a,T>(std::sync::MutexGuard<'a,T>);
 impl<T> Mutex<T>{fn new(v:T)->Self{Self(std::sync::Mutex::new(v))}fn lock(&self)->Guard<'_,T>{let guard=self.0.lock().unwrap();SLOTS_HELD.with(|n|assert!(!n.replace(true)));Guard(guard)}}
 impl<T> std::ops::Deref for Guard<'_,T>{type Target=T;fn deref(&self)->&T{&self.0}}
 impl<T> std::ops::DerefMut for Guard<'_,T>{fn deref_mut(&mut self)->&mut T{&mut self.0}}
 impl<T> Drop for Guard<'_,T>{fn drop(&mut self){SLOTS_HELD.with(|n|assert!(n.replace(false)));}}
 struct Notify;impl Notify{fn notify_all(&self){SLOTS_HELD.with(|n|assert!(!n.get(),"notify under slots lock"));NOTIFICATIONS.with(|n|n.set(n.get()+1));}}
 struct Entry{cleanup:Exchange,owner_slot:i32,prepare:Option<Preparation>,schedule:Option<Exchange>,retirement:Option<Exchange>,retirement_after:u64,procfs:Option<Arc<ProcfsProcess>>,syscalls:SharedMailbox,scheduled:bool,needs_cleanup:bool,closed:bool,quarantined:bool,parent_slot_pins:usize}
 impl Entry {
 @ENTRY@
 }
 pub(crate) struct Remote{slots:Mutex<Vec<Option<Entry>>>,changed:Notify,contexts:Vec<(usize,Token)>}
 impl Remote {
 @REMOTE@
 pub(crate) fn new(rows:Vec<(usize,i32,SharedMailbox)>)->Arc<Self>{let mut slots=Vec::new();let mut contexts=Vec::new();for(context,pid,q)in rows{let cleanup=Exchange::new(0,0,pid).unwrap();contexts.push((context,cleanup.token()));slots.push(Some(Entry{cleanup,owner_slot:0,prepare:None,schedule:None,retirement:None,retirement_after:0,procfs:None,syscalls:q,scheduled:false,needs_cleanup:false,closed:false,quarantined:false,parent_slot_pins:1}));}Arc::new(Self{slots:Mutex::new(slots),changed:Notify,contexts})}
 pub(crate) fn token(&self,context:usize)->Token{self.contexts.iter().find(|(c,_)|*c==context).unwrap().1}
 pub(crate) fn inspect(&self,context:usize)->(bool,bool,usize,bool,bool){let token=self.token(context);let s=self.slots.lock();let e=s.iter().flatten().find(|e|e.key()==token).unwrap();(e.needs_cleanup,e.release_ready(),e.parent_slot_pins,e.closed,e.cleanup.reserved())}
 pub(crate) fn quarantine(&self,context:usize){let token=self.token(context);let mut s=self.slots.lock();s.iter_mut().flatten().find(|e|e.key()==token).unwrap().quarantined=true;}
 }
 struct Runtime{application:Arc<Remote>}struct Started{runtime:Runtime}
 pub(crate) struct Application{started:Started,token:Token}
 impl Application{
 pub(crate) fn new(remote:Arc<Remote>,token:Token)->Self{Self{started:Started{runtime:Runtime{application:remote}},token}}
 @SERVICE@
 }
 pub(crate) fn invoke(application:&Application,command:u32,buffer:*mut u8,bytes:usize)->Result {
 // Exact new pre-slice branch, with unrelated dispatch removed by the adapter.
 if command == application_abi::BEGIN_CLEANUP @DISPATCH@ else {Err(EINVAL)}
 }
}
fn setup_provider(q:SharedMailbox){NOTIFICATIONS.with(|n|n.set(0));PROVIDER.with(|p|*p.borrow_mut()=Some(provider::Remote::new(vec![(100,257,q.clone()),(200,260,q)])));}
fn invoke_context(context:usize,command:u32,buffer:*mut u8,bytes:usize)->i32{PROVIDER.with(|p|{let p=p.borrow();let remote=p.as_ref().unwrap();let application=provider::Application::new(remote.clone(),remote.token(context));match provider::invoke(&application,command,buffer,bytes){Ok(())=>0,Err(e)=>e}})}
'''
shared=shared.replace('@ENTRY@','\n'.join(item(remote,s) for s in ['fn key(&self)','fn release_ready(&self)','fn request_cleanup(&mut self)']))
shared=shared.replace('@REMOTE@',item(remote,'pub(crate) fn begin_cleanup(&self, token: Token)'))
shared=shared.replace('@SERVICE@',item(service,'pub(in super::super) fn begin_cleanup(&self)').replace('pub(in super::super)','pub(crate)'))
branch=item(dispatch,'if command == application_abi::BEGIN_CLEANUP')
assert branch.startswith('if command == application_abi::BEGIN_CLEANUP {')
shared=shared.replace('@DISPATCH@',branch[len('if command == application_abi::BEGIN_CLEANUP '):])
source=source.replace('thread_local! { static WORKER:',shared+'\nthread_local! { static WORKER:')
extra=r'''
#[test]fn two_retained_children_begin_without_waiting_for_each_other(){
 crate::setup_backend();let first=crate::BACKEND.with(|b|b.borrow().as_ref().unwrap().clone());
 crate::setup_backend();let second=crate::BACKEND.with(|b|b.borrow().as_ref().unwrap().clone());
 crate::PROVIDER.with(|p|*p.borrow_mut()=Some(crate::provider::Remote::new(vec![(100,257,first.0.clone()),(200,260,first.0.clone()),(300,261,second.0.clone())])));
 let(p,c,one)=fixture_pair();let d=Registration::new(261,300);let vma=d.clone();let weak=Arc::downgrade(&d);let proof=application_abi::ForkPreparedV3{geometry:application_abi::ForkGeometryV3{root:4096,start:8192,length:4096},child_pid:261,reserved:0,child_mm:301,response:0x800000,nonce:10};d.reserve_fork_pair(&p,&proof).unwrap();
 let two=Arc::new(Process{slot:1,generation:7,pid:d._pid.clone(),registration:Mutex::new(Some(d.clone())),executable:Mutex::new(Some(()))});table().lock().push(Entry{process:two.clone(),files:1});drop(d);
 drop(Binding(one.clone()));drop(Binding(two.clone()));assert!(table().lock().is_empty());
 crate::CLEANUPS.with(|n|assert_eq!(n.get(),2));crate::CLOSES.with(|n|assert_eq!(n.get(),0));assert!(weak.upgrade().is_some());assert_eq!(p.control_children.lock().len(),2);
 crate::PROVIDER.with(|r|{let r=r.borrow();for context in [200,300]{assert_eq!(r.as_ref().unwrap().inspect(context),(true,false,1,false,true));}});
 for(mut q,ram)in[first,second]{assert_eq!(ram.status(),0);assert!(ram.claimed.load(Ordering::Acquire));assert_eq!(q.publish(0,|_|Err(-11)),Err(-11));assert_eq!(ram.status(),0);assert_eq!(ram.releases.load(Ordering::Acquire),0);assert_eq!(q.publish(0,|_|Ok(())),Ok(true));assert_eq!(ram.status(),1);assert_eq!(ram.releases.load(Ordering::Acquire),1);}
 crate::PROVIDER.with(|r|{let r=r.borrow();for context in [200,300]{assert_eq!(r.as_ref().unwrap().inspect(context),(true,false,1,false,true));}});
 one.detach_owners();two.detach_owners();crate::CLEANUPS.with(|n|assert_eq!(n.get(),2));
 // Test-only teardown of pair/VMA adapters, after ownership assertions. It is
 // deliberately not a production ACK or credit release mechanism.
 let d=weak.upgrade().unwrap();while !p.control_children.lock().is_empty(){p.control_children.lock().swap_remove(0);}c.fork_parent.lock().take();d.fork_parent.lock().take();drop(c);drop(d);drop(vma);crate::CLOSES.with(|n|assert_eq!(n.get(),2));drop(p);crate::CLOSES.with(|n|assert_eq!(n.get(),3));crate::CLEANUPS.with(|n|assert_eq!(n.get(),3));
}
#[test]fn begin_error_retains_owner_and_onceflag(){
 crate::setup_backend();crate::PROVIDER.with(|p|p.borrow().as_ref().unwrap().quarantine(200));let(p,c,process)=fixture_pair();drop(Binding(process.clone()));process.detach_owners();assert!(c.armed.load(Ordering::Acquire));assert!(c.cleanup_requested.load(Ordering::Acquire));assert_eq!(p.control_children.lock().len(),1);assert!(c.mapping.lock().is_some());crate::CLEANUPS.with(|n|assert_eq!(n.get(),1));crate::CLOSES.with(|n|assert_eq!(n.get(),0));crate::BACKEND.with(|b|{let b=b.borrow();assert_eq!(b.as_ref().unwrap().1.status(),0);assert!(b.as_ref().unwrap().1.claimed.load(Ordering::Acquire));});
 p.control_children.lock().swap_remove(0);c.fork_parent.lock().take();drop(c);drop(p);
}
'''
source=source.replace('\n}\nuse process::{application_abi,mcctrl_vm};',extra+'\n}\nuse process::{application_abi,mcctrl_vm};')
source+=r'''
#[test]fn dispatch_rejects_stale_and_malformed_before_any_slice(){
 setup_backend();PROVIDER.with(|p|{let p=p.borrow();let remote=p.as_ref().unwrap();let stale=application_rpc::Token::allocate().unwrap();let app=provider::Application::new(remote.clone(),stale);assert_eq!(provider::invoke(&app,22,std::ptr::null_mut(),0),Err(-2));let valid=provider::Application::new(remote.clone(),remote.token(200));assert_eq!(provider::invoke(&valid,22,std::ptr::null_mut(),1),Err(-22));assert_eq!(provider::invoke(&valid,22,std::ptr::dangling_mut(),0),Err(-22));assert_eq!(remote.inspect(200),(false,false,1,false,true));});NOTIFICATIONS.with(|n|assert_eq!(n.get(),1));
}
'''
(T/'begin-actual.rs').write_text(source)
shutil.copyfile(E/'run_reviewed_check.py',T/'run_reviewed_check.py')
paths=[O/'consumer/mcctrl_process.rs',O/'provider/abi/application.rs',O/'provider/ihk_smp_x86_64.rs',O/'provider/smp_service.rs',O/'provider/smp_application.rs',T/'begin-actual.rs',T/'run_reviewed_check.py',Path(__file__).resolve()]
(T/'SOURCE-PINS.json').write_text(json.dumps({'scope':__doc__,'sources':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}for p in paths],'limits':'Linux task/MM/provider connection authentication and native timing require real SDK/native checks. Preparation/procfs and clock are explicit adapters; main vectors retain real Exchange reserved, real parent-slot pin=1 and real Mailbox/ResponseMemory. No synthetic full-retirement ACK.'},indent=2)+'\n')
print(hashlib.sha256(source.encode()).hexdigest(),len(source))
