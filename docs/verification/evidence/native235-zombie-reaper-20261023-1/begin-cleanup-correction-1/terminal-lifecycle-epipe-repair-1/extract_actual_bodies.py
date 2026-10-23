from pathlib import Path
import hashlib,json
P=Path(__file__).resolve().parent
ROOT=P.parents[6]
def body(text,signature):
 at=text.index(signature); start=text.index('{',at); depth=0
 for i in range(start,len(text)):
  if text[i]=='{': depth+=1
  elif text[i]=='}':
   depth-=1
   if depth==0:return text[at:i+1]
 raise ValueError(signature)
app=P.joinpath('smp_application.rs').read_text()
service=P.joinpath('smp_service.rs').read_text()
old=P.joinpath('smp_service.rs.preimage').read_text()
proc=Path('/home/holden/mckernel/host-kernel/native-rust/smp_procfs.rs').read_text()
backend=body(app,'    fn backend_ready(')
lookup=body(app,'    pub(crate) fn procfs_process(')
delete=body(app,'    pub(crate) fn procfs_delete_process(')
ledger=body(proc,'    pub(super) fn delete(')
def dispatch(text,name):
 t=body(text,'    fn dispatch(')
 t=t[:t.index('        if zero_pages::Request::candidate(packet)')]
 return t.replace('fn dispatch(',f'fn {name}(',1)+'        Err(EINVAL)\n    }'
parts={'Entry::backend_ready':backend,'Remote::procfs_process':lookup,'Remote::procfs_delete_process':delete,'Service::delete':ledger,'Runtime::dispatch_candidate':dispatch(service,'dispatch_candidate'),'Runtime::dispatch_baseline':dispatch(old,'dispatch_baseline')}
pins={k:hashlib.sha256(v.encode()).hexdigest() for k,v in parts.items()}
P.joinpath('extracted-body-pins.json').write_text(json.dumps(pins,indent=2)+'\n')
prefix=r"""#![allow(dead_code,unused_variables,unused_imports,non_upper_case_globals)]
// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// Generated from complete production admission/delete bodies and the complete
// procfs dispatch branch. Linux/kernel allocation/channel facades are explicit.
mod fixture {
use std::sync::{Arc,Mutex,atomic::{AtomicBool,AtomicU64,Ordering}};
type Result<T=()> = std::result::Result<T,i32>;
const EAGAIN:i32=-11; const EBUSY:i32=-16; const EINVAL:i32=-22; const ENOENT:i32=-2; const EIO:i32=-5; const ENOMEM:i32=-12; const GFP_KERNEL:()=();
const METADATA_CAPACITY:usize=64; const CONTROL_PACKET_BYTES:usize=128;
macro_rules! pr_info {($($t:tt)*)=>{{}}}
mod kernel {pub mod error {pub fn to_result(v:i32)->std::result::Result<(),i32>{if v<0{Err(v)}else{Ok(())}}}}
mod application_rpc {pub const TID_DELETE:i32=0x45;}
struct Lock<T>(Mutex<T>); impl<T> Lock<T>{fn lock(&self)->std::sync::MutexGuard<'_,T>{self.0.lock().unwrap()}}
struct Cleanup(i32);impl Cleanup{fn pid(&self)->i32{self.0}}
struct Ingress{host_revoke:Option<()>,sealed:AtomicBool}
struct Prepare(Option<i32>);impl Prepare{fn result(&self)->Option<i32>{self.0}}
struct Image{control_cpu:i32}
struct Context{key:u64,pid:i32}
struct Process{context:Context,tids:Lock<Vec<i32>>}
type ProcfsProcess=Process;
struct Entry{cleanup:Cleanup,quarantined:bool,closed:bool,needs_cleanup:bool,fork_ingress:Option<Ingress>,prepare:Option<Prepare>,inherited_root:Option<Image>,procfs:Option<Arc<Process>>,pins:usize,credits:usize}
impl Entry {
"""
mid=r"""
}
struct Remote{slots:Lock<Vec<Option<Entry>>>}
impl Remote {
"""
facade=r"""
}
struct Owner;impl Owner{fn slot(&self)->u32{0}}
struct Completion;struct Memory{reads:AtomicU64}
impl Memory{fn procfs(&self,_physical:u64,_create:bool)->Result<Completion>{self.reads.fetch_add(1,Ordering::Relaxed);Ok(Completion)}}
struct Replies;impl Replies{fn reply(&self,_p:&[u8;128])->Result{Ok(())}}
mod procfs {use super::*;pub(super) struct Event{pub process:Arc<Process>,pub tid:i32,pub completion:Option<Completion>}}
struct Pending(Vec<procfs::Event>);impl Pending{fn len(&self)->usize{self.0.len()}fn push(&mut self,e:procfs::Event,_flag:())->Result{self.0.push(e);Ok(())}}
struct Runtime{application:Remote,owner:Owner,cpus:Vec<()>,procfs:Replies,procfs_pending:Lock<Pending>,memory:Memory,rejected:AtomicU64}
impl Runtime{
"""
suffix=r"""
}
struct Tid{tid:i32}struct Published{process:Arc<Process>,tids:Vec<Tid>}
struct Service{processes:Vec<Published>}
impl Service{
"""
tests=r"""
}
fn setup()->(Runtime,Arc<Process>){let process=Arc::new(Process{context:Context{key:9,pid:258},tids:Lock(Mutex::new(vec![258]))});let entry=Entry{cleanup:Cleanup(258),quarantined:false,closed:false,needs_cleanup:true,fork_ingress:Some(Ingress{host_revoke:Some(()),sealed:AtomicBool::new(true)}),prepare:None,inherited_root:Some(Image{control_cpu:0}),procfs:Some(process.clone()),pins:1,credits:1};(Runtime{application:Remote{slots:Lock(Mutex::new(vec![Some(entry)]))},owner:Owner,cpus:vec![()],procfs:Replies,procfs_pending:Lock(Mutex::new(Pending(Vec::new()))),memory:Memory{reads:AtomicU64::new(0)},rejected:AtomicU64::new(0)},process)}
fn packet(message:i32)->[u8;128]{let mut p=[0;128];p[8..12].copy_from_slice(&message.to_le_bytes());p[24..28].copy_from_slice(&0i32.to_le_bytes());p[28..32].copy_from_slice(&0i32.to_le_bytes());p[32..36].copy_from_slice(&258i32.to_le_bytes());p[40..48].copy_from_slice(&258u64.to_le_bytes());p}
fn changed(r:&Runtime,f:impl FnOnce(&mut Entry)){f(r.application.slots.lock()[0].as_mut().unwrap());}
#[test]fn baseline_real_dispatch_refuses_genuine_post_revoke_delete(){let(r,p)=setup();assert_eq!(r.dispatch_baseline(503,&packet(application_rpc::TID_DELETE)),Err(EBUSY));assert_eq!(*p.tids.lock(),vec![258]);assert_eq!(r.procfs_pending.lock().len(),0);}
#[test]fn candidate_real_dispatch_and_delete_drain_exact_retained_ledger(){let(r,p)=setup();r.dispatch_candidate(503,&packet(application_rpc::TID_DELETE)).unwrap();let event=r.procfs_pending.lock().0.remove(0);assert!(Arc::ptr_eq(&event.process,&p));assert!(event.completion.is_none());let mut service=Service{processes:vec![Published{process:p.clone(),tids:vec![Tid{tid:258}]}]};service.delete(&event.process,event.tid).unwrap();assert!(p.tids.lock().is_empty());assert!(service.processes[0].tids.is_empty());assert_eq!(r.memory.reads.load(Ordering::Relaxed),0);let slots=r.application.slots.lock();let e=slots[0].as_ref().unwrap();assert_eq!((e.pins,e.credits),(1,1));assert!(e.needs_cleanup);assert!(e.fork_ingress.as_ref().unwrap().host_revoke.is_some());}
#[test]fn candidate_delete_after_final_ack_without_mm_namespace_still_drains(){let(r,p)=setup();changed(&r,|e|{e.closed=true;e.inherited_root=None;e.fork_ingress=None;});r.dispatch_candidate(503,&packet(application_rpc::TID_DELETE)).unwrap();let event=r.procfs_pending.lock().0.remove(0);let mut service=Service{processes:vec![]};service.delete(&event.process,event.tid).unwrap();assert!(p.tids.lock().is_empty());assert_eq!(r.memory.reads.load(Ordering::Relaxed),0);}
#[test]fn candidate_create_preserves_revoke_backend_gate(){let(r,p)=setup();assert_eq!(r.dispatch_candidate(503,&packet(0x44)),Err(EBUSY));assert_eq!(r.memory.reads.load(Ordering::Relaxed),0);assert_eq!(*p.tids.lock(),vec![258]);}
#[test]fn candidate_create_before_revoke_keeps_real_completion_path(){let(r,_)=setup();changed(&r,|e|e.fork_ingress.as_mut().unwrap().host_revoke=None);r.dispatch_candidate(503,&packet(0x44)).unwrap();let event=r.procfs_pending.lock().0.remove(0);assert!(event.completion.is_some());assert_eq!(r.memory.reads.load(Ordering::Relaxed),1);}
#[test]fn candidate_delete_quarantine_still_refuses(){let(r,_)=setup();changed(&r,|e|e.quarantined=true);assert_eq!(r.dispatch_candidate(503,&packet(application_rpc::TID_DELETE)),Err(EINVAL));assert_eq!(r.procfs_pending.lock().len(),0);}
#[test]fn candidate_delete_missing_entry_or_process_refuses(){let(r,_)=setup();let mut p=packet(application_rpc::TID_DELETE);p[32..36].copy_from_slice(&259i32.to_le_bytes());assert_eq!(r.dispatch_candidate(503,&p),Err(ENOENT));changed(&r,|e|e.procfs=None);assert_eq!(r.dispatch_candidate(503,&packet(application_rpc::TID_DELETE)),Err(EIO));}
#[test]fn candidate_packet_identity_validation_still_precedes_lookup(){for (at,value)in[(24,-1i32),(24,1),(28,1)]{let(r,_)=setup();let mut p=packet(application_rpc::TID_DELETE);p[at..at+4].copy_from_slice(&value.to_le_bytes());assert_eq!(r.dispatch_candidate(503,&p),Err(EINVAL));assert_eq!(r.procfs_pending.lock().len(),0);}let(r,_)=setup();assert_eq!(r.dispatch_candidate(501,&packet(application_rpc::TID_DELETE)),Err(EINVAL));}
#[test]fn actual_delete_is_idempotent_after_namespace_and_ledger_retire(){let(_r,p)=setup();let mut service=Service{processes:vec![]};service.delete(&p,258).unwrap();service.delete(&p,258).unwrap();assert!(p.tids.lock().is_empty());}
}
"""
P.joinpath('actual_lifecycle_tests.rs').write_text(prefix+backend+mid+lookup+'\n'+delete+facade+parts['Runtime::dispatch_baseline']+'\n'+parts['Runtime::dispatch_candidate']+suffix+ledger+tests)
print('Generated actual-body lifecycle tests; '+str(len(parts))+' source bodies pinned.')
