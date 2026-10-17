// Additional deterministic owners for consumed production shutdown consumers.
// Linux namespace removal, real task exit and actual hardware remain boundaries.
static IRQ_PRE_STATUS:AtomicI32=AtomicI32::new(0);
static SERVICE_LOCKS:AtomicU32=AtomicU32::new(0);
static JOIN_COUNT:AtomicU32=AtomicU32::new(0);
static JOIN_BLOCK:std::sync::atomic::AtomicBool=std::sync::atomic::AtomicBool::new(false);
static JOIN_ENTERED:AtomicU32=AtomicU32::new(0);
static NAMESPACE_DROPS:AtomicU32=AtomicU32::new(0);
static CALLBACK_DRAIN_BLOCK:std::sync::atomic::AtomicBool=std::sync::atomic::AtomicBool::new(false);
static CALLBACK_DRAIN_ENTERED:AtomicU32=AtomicU32::new(0);
static CALLBACK_STORAGE_DROPS:AtomicU32=AtomicU32::new(0);
static MEMORY_COMMITS:AtomicU32=AtomicU32::new(0);
static IRQ_RELEASE_STATUS:AtomicI32=AtomicI32::new(0);
static MAP_STATUS:AtomicI32=AtomicI32::new(0);
static INJECT_STALE:std::sync::atomic::AtomicBool=std::sync::atomic::AtomicBool::new(false);
struct AdapterMutex<T>(std::sync::Mutex<T>);
impl<T> AdapterMutex<T> {
 fn new(value:T)->Self{Self(std::sync::Mutex::new(value))}
 fn lock(&self)->CountedGuard<'_,T>{let guard=self.0.lock().unwrap();SERVICE_LOCKS.fetch_add(1,Ordering::AcqRel);CountedGuard{guard,counter:&SERVICE_LOCKS}}
}
fn no_dependent_locks(){assert_eq!((CPU_LOCKS.load(Ordering::Acquire),MEMORY_LOCKS.load(Ordering::Acquire),HOTPLUG_LOCKS.load(Ordering::Acquire),SERVICE_LOCKS.load(Ordering::Acquire)),(0,0,0,0));}
trait ErrorNumber {fn to_errno(self)->i32;}
impl ErrorNumber for i32 {fn to_errno(self)->i32{self}}
mod kernel {pub mod error {pub type Error=i32;}}
const EINVAL:i32=-22;
const IHK_SMP_SHUTDOWN_V6_POST_EFFECT:i64=1_i64<<62;
macro_rules! pr_info {($($t:tt)*)=>{{let _=format_args!($($t)*);}}}
// PRODUCTION_PROVIDER

mod smp_application {
 use super::smp_cpu::{OsToken,Result};
 use super::AdapterMutex as Mutex;
 use std::sync::atomic::{AtomicBool,AtomicI32,Ordering};
 const EBUSY:i32=-16;const ENODEV:i32=-19;const EINVAL:i32=-22;const EAGAIN:i32=-11;
 fn errno(error:i32)->i32{error}
 #[derive(Clone,Copy)] pub(super) struct Token(u64);
 struct Exchange{pid:i32,token:Token}
 impl Exchange {fn new(_owner:i32,_cpu:i32,pid:i32)->Result<Self>{Ok(Self{pid,token:Token(pid as u64)})}fn pid(&self)->i32{self.pid}fn token(&self)->Token{self.token}}
 struct Mailbox{busy:bool}
 impl Mailbox {fn new()->Result<Self>{Ok(Self{busy:false})}fn drained(&self)->bool{!self.busy}}
 struct Entry {cleanup:Exchange,owner_slot:i32,prepare:Option<()>,schedule:Option<()>,retirement:Option<()>,retirement_after:u64,procfs:Option<()>,syscalls:Mailbox,scheduled:bool,needs_cleanup:bool,closed:bool,quarantined:bool}
 struct Registry{entries:Mutex<Vec<Option<()>>>}
 impl Registry {// PRODUCTION_PAGER_CHECK
 }
 pub(super) struct Remote {owner:OsToken,slots:Mutex<Vec<Option<Entry>>>,shutdown_closed:AtomicBool,transport_error:AtomicI32,releases:Mutex<Mailbox>,pagers:Registry}
 impl Remote {
  // PRODUCTION_APP_METHODS
  pub(super) fn fixture()->Self {Self{owner:super::smp_cpu::fixture_owner(7,91),slots:Mutex::new(vec![None,None]),shutdown_closed:AtomicBool::new(false),transport_error:AtomicI32::new(0),releases:Mutex::new(Mailbox{busy:false}),pagers:Registry{entries:Mutex::new(vec![None,None])}}}
  pub(super) fn fixture_busy(&self){assert!(self.reserve(123).is_ok());}
  pub(super) fn fixture_retained(&self)->usize{self.slots.lock().iter().filter(|slot|slot.is_some()).count()}
  pub(super) fn fixture_pager_busy(&self){self.pagers.entries.lock()[0]=Some(());}
 }
}

mod callback_boundary {
 use std::{ptr,sync::Arc};
 struct ParentMutex(std::sync::Mutex<bool>);
 impl ParentMutex{fn lock(&self)->std::sync::MutexGuard<'_,bool>{self.0.lock().unwrap()}}
 struct ObjectRef(*mut ());
 unsafe impl Send for ObjectRef{} unsafe impl Sync for ObjectRef{}
 struct DirectoryState{registered:ParentMutex,object:ObjectRef}
 trait AttributeOps:Send+Sync{}
 struct Marker;
 impl AttributeOps for Marker{}
 impl Drop for Marker{fn drop(&mut self){assert!(!crate::CALLBACK_DRAIN_BLOCK.load(crate::Ordering::Acquire));crate::CALLBACK_STORAGE_DROPS.fetch_add(1,crate::Ordering::AcqRel);}}
 struct Attribute{attr:usize}
 struct AttributeStorage<T>{attribute:Attribute,_operations:T}
 struct File<T:AttributeOps>{parent:Arc<DirectoryState>,storage:Box<AttributeStorage<T>>}
 mod bindings{pub unsafe fn sysfs_remove_file_ns(_object:*mut (),_attribute:*const usize,_namespace:*const ()){
  crate::no_dependent_locks();crate::CALLBACK_DRAIN_ENTERED.fetch_add(1,crate::Ordering::AcqRel);
  while crate::CALLBACK_DRAIN_BLOCK.load(crate::Ordering::Acquire){std::thread::yield_now();}
 }}
 // PRODUCTION_FILE_DROP
 struct Node{_file:File<Marker>}
 pub(super) struct Tree{nodes:Vec<Node>}
 // PRODUCTION_TREE_DROP
 pub(super) fn tree()->Tree{let parent=Arc::new(DirectoryState{registered:ParentMutex(std::sync::Mutex::new(true)),object:ObjectRef(ptr::null_mut())});Tree{nodes:vec![Node{_file:File{parent,storage:Box::new(AttributeStorage{attribute:Attribute{attr:0},_operations:Marker})}}]}}
}

mod integration_service_fixture {
 use crate::smp_cpu::Result;
 use crate::ErrorNumber;
 type Error=i32;
 use crate::AdapterMutex as Mutex;
 use std::sync::{Arc,atomic::{AtomicBool,Ordering}};
 const EBUSY:i32=-16;const EINVAL:i32=-22;
 struct Tagged;
 struct Ledger{requests:Vec<Option<Tagged>>,responses:Vec<Option<Tagged>>,payloads:Vec<Option<Tagged>>,snoops:Vec<Tagged>,procfs:Vec<Tagged>,zeroing:Vec<Tagged>}
 struct LedgerMutex(Mutex<Ledger>);
 impl LedgerMutex{fn lock(&self)->crate::CountedGuard<'_,Ledger>{
  if crate::INJECT_STALE.swap(false,Ordering::AcqRel){crate::smp_memory::replace_epoch(crate::smp_cpu::fixture_owner(7,91));}
  self.0.lock()
 }}
 pub(super) struct Memory{pub(super) owner:crate::smp_cpu::OsToken,ledger:LedgerMutex}
 impl Memory{
  // PRODUCTION_MEMORY_CHECK
 }
 pub(super) struct ProcfsRemote{memory:Arc<Memory>,active:AtomicBool,slots:Mutex<Vec<Option<()>>>}
 impl ProcfsRemote{
  // PRODUCTION_PROCFS_CHECK
 }
 struct Namespace{_tree:crate::callback_boundary::Tree}
 impl Namespace{fn new()->Self{Self{_tree:crate::callback_boundary::tree()}}}
 impl Drop for Namespace{fn drop(&mut self){crate::no_dependent_locks();crate::NAMESPACE_DROPS.fetch_add(1,Ordering::AcqRel);}}
 struct Service{_namespace:Namespace}
 struct ProcfsService{processes:Vec<()>,_namespace:Namespace}
 impl ProcfsService{
  // PRODUCTION_PROCFS_SERVICE_CHECK
 }
 struct Pending{length:usize}
 struct Transport{master_reply:Option<[u8;56]>}
 struct Runtime{
  remote:Arc<crate::sysfs_remote::Remote>,application:Arc<crate::smp_application::Remote>,procfs:ProcfsRemote,memory:Arc<Memory>,
  pending:Mutex<Pending>,procfs_pending:Mutex<Vec<()>>,zero_pending:Mutex<Vec<()>>,transport:Mutex<Transport>,service:Mutex<Option<Service>>,procfs_service:Mutex<Option<ProcfsService>>,
 }
 struct Thread{role:u32,joined:AtomicBool}
 impl Thread{fn stop_join(&self){
  crate::no_dependent_locks();
  if !self.joined.swap(true,Ordering::AcqRel){
   crate::JOIN_ENTERED.fetch_add(1,Ordering::AcqRel);
   while crate::JOIN_BLOCK.load(Ordering::Acquire){std::thread::yield_now();}
   crate::JOIN_COUNT.fetch_add(1,Ordering::AcqRel);
   if self.role==0{crate::STOP_CALLS.fetch_add(1,Ordering::AcqRel);}
  }
 }}
 // PRODUCTION_STARTED_STRUCT
 impl Started{
  // PRODUCTION_STARTED_METHODS
 }
 static LAST:std::sync::Mutex<Option<Arc<Runtime>>>=std::sync::Mutex::new(None);
 pub(super) fn fixture_started()->Started{
  let memory=Arc::new(Memory{owner:crate::smp_cpu::fixture_owner(7,91),ledger:LedgerMutex(Mutex::new(Ledger{requests:vec![None],responses:vec![None],payloads:vec![None],snoops:vec![],procfs:vec![],zeroing:vec![]}))});
  let runtime=Arc::new(Runtime{remote:crate::sysfs_remote::fixture_service_remote(),application:Arc::new(crate::smp_application::Remote::fixture()),procfs:ProcfsRemote{memory:memory.clone(),active:AtomicBool::new(true),slots:Mutex::new(vec![None])},memory,pending:Mutex::new(Pending{length:0}),procfs_pending:Mutex::new(vec![]),zero_pending:Mutex::new(vec![]),transport:Mutex::new(Transport{master_reply:None}),service:Mutex::new(Some(Service{_namespace:Namespace::new()})),procfs_service:Mutex::new(Some(ProcfsService{processes:vec![],_namespace:Namespace::new()}))});
  *LAST.lock().unwrap()=Some(runtime.clone());
  Started{runtime,metadata:Arc::new(Thread{role:1,joined:AtomicBool::new(false)}),packets:Arc::new(Thread{role:0,joined:AtomicBool::new(false)}),zeroing:Arc::new(Thread{role:2,joined:AtomicBool::new(false)})}
 }
 pub(crate) fn configure(kind:u32){let r=LAST.lock().unwrap();let r=r.as_ref().unwrap();match kind{
  1=>r.application.fixture_busy(),2=>r.remote.fixture_callbacks(1),3=>r.memory.ledger.lock().responses[0]=Some(Tagged),
  4=>r.pending.lock().length=1,5=>r.procfs.slots.lock()[0]=Some(()),6=>r.application.fixture_pager_busy(),7=>r.procfs_service.lock().as_mut().unwrap().processes.push(()),_=>()}}
 pub(crate) fn app_retained()->usize{LAST.lock().unwrap().as_ref().unwrap().application.fixture_retained()}
 pub(crate) fn reserve_after_close()->bool{LAST.lock().unwrap().as_ref().unwrap().application.reserve(456).is_err()}
 pub(crate) fn namespaces_retained()->bool{let r=LAST.lock().unwrap();let r=r.as_ref().unwrap();r.service.lock().is_some()&&r.procfs_service.lock().is_some()}
}
