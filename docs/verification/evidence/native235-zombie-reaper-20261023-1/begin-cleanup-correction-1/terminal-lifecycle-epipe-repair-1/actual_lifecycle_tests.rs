#![allow(dead_code,unused_variables,unused_imports,non_upper_case_globals)]
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
    fn backend_ready(&self)->Result {
        // This mutex also covers every inherited-root read. Installing the
        // owned revoke capsule therefore closes admission and drains all
        // earlier backend accesses before the out-of-lock Linux MM callback.
        if self.fork_ingress.as_ref().is_some_and(|owner|owner.host_revoke.is_some()){return Err(EBUSY);}
        if let Some(image)=&self.prepare{return kernel::error::to_result(image.result().ok_or(EBUSY)?).map(|_|());}
        if self.inherited_root.as_ref().is_some_and(|image|image.control_cpu>=0)&&self.fork_ingress.as_ref().is_some_and(|f|f.sealed.load(Ordering::Acquire)){return Ok(());}
        Err(EINVAL)
    }
}
struct Remote{slots:Lock<Vec<Option<Entry>>>}
impl Remote {
    pub(crate) fn procfs_process(&self, pid: i32, cpu: i32) -> Result<Arc<ProcfsProcess>> {
        let slots = self.slots.lock();
        let entry = slots
            .iter()
            .flatten()
            .find(|entry| entry.cleanup.pid() == pid)
            .ok_or(ENOENT)?;
        entry.backend_ready()?;
        if entry.quarantined || cpu < 0 {
            return Err(EINVAL);
        }
        entry.procfs.as_ref().cloned().ok_or(EIO)
    }
    pub(crate) fn procfs_delete_process(&self, pid: i32, cpu: i32) -> Result<Arc<ProcfsProcess>> {
        let slots = self.slots.lock();
        let entry = slots
            .iter()
            .flatten()
            .find(|entry| entry.cleanup.pid() == pid)
            .ok_or(ENOENT)?;
        if entry.quarantined || cpu < 0 {
            return Err(EINVAL);
        }
        entry.procfs.as_ref().cloned().ok_or(EIO)
    }
}
struct Owner;impl Owner{fn slot(&self)->u32{0}}
struct Completion;struct Memory{reads:AtomicU64}
impl Memory{fn procfs(&self,_physical:u64,_create:bool)->Result<Completion>{self.reads.fetch_add(1,Ordering::Relaxed);Ok(Completion)}}
struct Replies;impl Replies{fn reply(&self,_p:&[u8;128])->Result{Ok(())}}
mod procfs {use super::*;pub(super) struct Event{pub process:Arc<Process>,pub tid:i32,pub completion:Option<Completion>}}
struct Pending(Vec<procfs::Event>);impl Pending{fn len(&self)->usize{self.0.len()}fn push(&mut self,e:procfs::Event,_flag:())->Result{self.0.push(e);Ok(())}}
struct Runtime{application:Remote,owner:Owner,cpus:Vec<()>,procfs:Replies,procfs_pending:Lock<Pending>,memory:Memory,rejected:AtomicU64}
impl Runtime{
    fn dispatch_baseline(&self, port: i32, packet: &[u8; CONTROL_PACKET_BYTES]) -> Result {
        let message = i32::from_le_bytes(packet[8..12].try_into().unwrap());
        if port != 503 {
            return Err(EINVAL);
        }
        if message == 0x13 {
            if let Err(error) = self.procfs.reply(packet) {
                if error != ENOENT {
                    return Err(error);
                }
                self.rejected.fetch_add(1, Ordering::Relaxed);
            }
            return Ok(());
        }
        if message == 0x44
            || message == application_rpc::TID_DELETE
                && u64::from_le_bytes(packet[40..48].try_into().unwrap()) != 0
        {
            let cpu = i32::from_le_bytes(packet[24..28].try_into().unwrap());
            let os = i32::from_le_bytes(packet[28..32].try_into().unwrap());
            let pid = i32::from_le_bytes(packet[32..36].try_into().unwrap());
            let tid = u64::from_le_bytes(packet[40..48].try_into().unwrap());
            if os != self.owner.slot() as i32
                || cpu < 0
                || cpu as usize >= self.cpus.len()
                || tid == 0
                || tid > i32::MAX as u64
            {
                return Err(EINVAL);
            }
            let process = self.application.procfs_process(pid, cpu)?;
            let mut pending = self.procfs_pending.lock();
            // Refuse overflow without acknowledging CREATE. Retain started
            // ownership and report a service failure, but keep draining this
            // channel: a later answer may unblock namespace rundown.
            if pending.len() == METADATA_CAPACITY {
                return Err(ENOMEM);
            }
            let completion = if message == 0x44 {
                Some(
                    self.memory
                        .procfs(
                            u64::from_le_bytes(packet[120..128].try_into().unwrap()),
                            true,
                        )
                        .map_err(|error| if error == EAGAIN { ENOMEM } else { error })?,
                )
            } else {
                None
            }; // DELETE resp_pa is expired guest stack; never use it.
            pending.push(
                procfs::Event {
                    process,
                    tid: tid as i32,
                    completion,
                },
                GFP_KERNEL,
            )?;
            return Ok(());
        }
        Err(EINVAL)
    }
    fn dispatch_candidate(&self, port: i32, packet: &[u8; CONTROL_PACKET_BYTES]) -> Result {
        let message = i32::from_le_bytes(packet[8..12].try_into().unwrap());
        if port != 503 {
            return Err(EINVAL);
        }
        if message == 0x13 {
            if let Err(error) = self.procfs.reply(packet) {
                if error != ENOENT {
                    return Err(error);
                }
                self.rejected.fetch_add(1, Ordering::Relaxed);
            }
            return Ok(());
        }
        if message == 0x44
            || message == application_rpc::TID_DELETE
                && u64::from_le_bytes(packet[40..48].try_into().unwrap()) != 0
        {
            let cpu = i32::from_le_bytes(packet[24..28].try_into().unwrap());
            let os = i32::from_le_bytes(packet[28..32].try_into().unwrap());
            let pid = i32::from_le_bytes(packet[32..36].try_into().unwrap());
            let tid = u64::from_le_bytes(packet[40..48].try_into().unwrap());
            if os != self.owner.slot() as i32
                || cpu < 0
                || cpu as usize >= self.cpus.len()
                || tid == 0
                || tid > i32::MAX as u64
            {
                return Err(EINVAL);
            }
            let process = if message == 0x44 {
                self.application.procfs_process(pid, cpu)?
            } else {
                // A real destructor may send DELETE after host revoke closed
                // every MM/backend admission. Drain only the retained ledger.
                self.application.procfs_delete_process(pid, cpu)?
            };
            let mut pending = self.procfs_pending.lock();
            // Refuse overflow without acknowledging CREATE. Retain started
            // ownership and report a service failure, but keep draining this
            // channel: a later answer may unblock namespace rundown.
            if pending.len() == METADATA_CAPACITY {
                return Err(ENOMEM);
            }
            let completion = if message == 0x44 {
                Some(
                    self.memory
                        .procfs(
                            u64::from_le_bytes(packet[120..128].try_into().unwrap()),
                            true,
                        )
                        .map_err(|error| if error == EAGAIN { ENOMEM } else { error })?,
                )
            } else {
                None
            }; // DELETE resp_pa is expired guest stack; never use it.
            pending.push(
                procfs::Event {
                    process,
                    tid: tid as i32,
                    completion,
                },
                GFP_KERNEL,
            )?;
            return Ok(());
        }
        Err(EINVAL)
    }
}
struct Tid{tid:i32}struct Published{process:Arc<Process>,tids:Vec<Tid>}
struct Service{processes:Vec<Published>}
impl Service{
    pub(super) fn delete(&mut self, process: &Process, tid: i32) -> Result {
        if let Some(entry) = self
            .processes
            .iter_mut()
            .find(|entry| entry.process.context.key == process.context.key)
        {
            if let Some(index) = entry.tids.iter().position(|entry| entry.tid == tid) {
                drop(entry.tids.remove(index));
            }
        }
        // Namespace rundown may already have removed all nodes. Preserve the
        // ledger until this advisory event; never access DELETE's resp_pa.
        let mut tids = process.tids.lock();
        if let Some(index) = tids.iter().position(|value| *value == tid) {
            tids.remove(index);
            pr_info!(
                "IHK-SMP: application procfs deleted os={} generation={} pid={} tid={}\n",
                process.remote.memory.owner.slot(),
                process.remote.memory.owner.generation(),
                process.context.pid,
                tid
            );
        }
        Ok(())
    }
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
