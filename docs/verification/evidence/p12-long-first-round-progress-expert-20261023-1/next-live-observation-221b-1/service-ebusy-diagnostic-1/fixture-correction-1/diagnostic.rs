// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// PURE host fixture. std Arc/Mutex/Vec and owned AtomicU64 backing stand in for
// kernel primitives/guest mappings; this is not a kernel/module/layout proof.
#![allow(dead_code)]
use std::sync::{Arc,Mutex as StdMutex};
use std::sync::atomic::{AtomicBool,AtomicI32,AtomicU64,AtomicUsize,Ordering};
use std::cell::RefCell;
#[derive(Clone,Copy,Debug,Eq,PartialEq)] struct Error(i32);
impl Error {fn to_errno(self)->i32{self.0}}
type Result<T=()> = std::result::Result<T,Error>;
const EINVAL:Error=Error(-22);const EBUSY:Error=Error(-16);const EAGAIN:Error=Error(-11);const EIO:Error=Error(-5);
fn errno(n:i32)->Error{Error(n)}
thread_local!{static EVENTS:RefCell<Vec<String>>=const{RefCell::new(Vec::new())};}
fn event(s:String){EVENTS.with(|v|v.borrow_mut().push(s));}
fn take_events()->Vec<String>{EVENTS.with(|v|std::mem::take(&mut *v.borrow_mut()))}
macro_rules! pr_err {($($x:tt)*)=>{{event(format!($($x)*));}};}
#[derive(Clone,Copy)] struct Owner{slot:u32,generation:u64}
impl Owner {fn slot(self)->u32{self.slot}fn generation(self)->u64{self.generation}}
const OWNER:Owner=Owner{slot:0,generation:1};
fn is_diag(s:&str)->bool{s.starts_with("IHK-")&&!s.starts_with("IHK-SMP:")}
fn check_lines(v:&[String]){for s in v.iter().filter(|s|is_diag(s)){assert!(s.len()+96<=255,"line bytes+prefix={} {}",s.len()+96,s);}}
#[path="actual_wire.rs"] mod actual_wire;
#[path="original_wire.rs"] mod original_wire;
use actual_wire as sysfs_request;
#[path="actual_rpc.rs"] mod actual_rpc;
#[path="original_rpc.rs"] mod original_rpc;
#[path="actual_request.rs"] mod application_syscall;
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
enum FailureOrigin {
    Packet { channel: usize, guest_cpu: u32, port: i32, message: i32 },
    ControlPump,
    RegularPump,
    PublishRemote,
    PublishApplications,
    PublishSyscalls,
    AdvanceApplications,
    PublishProcfs,
    Metadata,
    Zeroing,
}
impl FailureOrigin {
    fn label(self) -> &'static str {
        match self {
            Self::Packet { .. } => "packet_dispatch",
            Self::ControlPump => "control_pump", Self::RegularPump => "regular_pump",
            Self::PublishRemote => "publish_remote", Self::PublishApplications => "publish_apps",
            Self::PublishSyscalls => "publish_syscalls", Self::AdvanceApplications => "advance_apps",
            Self::PublishProcfs => "publish_procfs", Self::Metadata => "metadata", Self::Zeroing => "zeroing",
        }
    }
}
fn diagnostic_ticket(counter: &AtomicU64) -> Option<u64> {
    counter.fetch_update(Ordering::Relaxed, Ordering::Relaxed, |old| {
        if old < 16 { Some(old + 1) } else { None }
    }).ok().map(|old| old + 1)
}
struct Application {calls:AtomicUsize,quarantines:AtomicUsize}
impl Application {fn fail_service(&self,error:&AtomicI32,e:Error)->bool {
 self.calls.fetch_add(1,Ordering::Relaxed);
 if error.compare_exchange(0,e.to_errno(),Ordering::AcqRel,Ordering::Acquire).is_ok(){self.quarantines.fetch_add(1,Ordering::Relaxed);event("service_quarantine".into());true}else{false}
}}
struct Runtime {owner:Owner,application:Application,error:AtomicI32,failure_contexts:AtomicU64}
impl Runtime {fn new()->Self{Self{owner:OWNER,application:Application{calls:AtomicUsize::new(0),quarantines:AtomicUsize::new(0)},error:AtomicI32::new(0),failure_contexts:AtomicU64::new(0)}}
    fn original_fail(&self, error: Error) {
        if self.application.fail_service(&self.error, error) {
            pr_err!("IHK-SMP: continuing service error os={} generation={} errno={}; workers and all started owners retained\n",
                self.owner.slot(), self.owner.generation(), error.to_errno());
        }
    }
    fn failure_context(&self, error: Error, origin: FailureOrigin) {
        if let Some(diag) = diagnostic_ticket(&self.failure_contexts) {
            pr_err!("IHK-E os={} g={} d={} at={} e={}\n",
                self.owner.slot(), self.owner.generation(), diag, origin.label(), error.to_errno());
            if let FailureOrigin::Packet { channel, guest_cpu, port, message } = origin {
                pr_err!("IHK-P os={} g={} d={} ch={} c={} port={} m={:x}\n",
                    self.owner.slot(), self.owner.generation(), diag, channel, guest_cpu, port, message);
            }
        }
    }
    fn fail(&self, error: Error, origin: FailureOrigin) {
        self.failure_context(error, origin);
        if self.application.fail_service(&self.error, error) {
            pr_err!("IHK-SMP: continuing service error os={} generation={} errno={}; workers and all started owners retained\n",
                self.owner.slot(), self.owner.generation(), error.to_errno());
        }
    }
}
mod memory {
use super::*;
use crate::application_syscall::Request as SyscallRequest;
use crate::actual_wire as wire;
const RESPONSE_BYTES:usize=40;
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
pub(super) struct Span {
    physical: u64,
    end: u64,
}
impl Span {
    pub(super) fn new(physical: u64, bytes: usize) -> Result<Self> {
        if physical == 0 || bytes == 0 {
            return Err(EINVAL);
        }
        Ok(Self {
            physical,
            end: physical.checked_add(bytes as u64).ok_or(EINVAL)?,
        })
    }
    fn overlaps(self, other: Self) -> bool {
        self.physical < other.end && other.physical < self.end
    }
}
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
struct Tagged {
    span: Span,
    serial: u64,
}
// Diagnostic snapshots contain only initialized, host-owned ledger fields.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum ConflictKind { Fixed, Request, Payload, Response, ExecPayload, Snoop, Procfs, Zeroing }

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct FailureConflict {
    kind: ConflictKind,
    slot: usize,
    member: Option<usize>,
    serial: Option<u64>,
    span: Span,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct SyscallFailureContext {
    cpu: i32, pid: i32, requester: i32, target: i32, number: u64,
    response: u64, response_end: Option<u64>,
    conflict: Option<FailureConflict>,
}

fn syscall_failure_context(request: &SyscallRequest, conflict: Option<FailureConflict>) -> SyscallFailureContext {
    SyscallFailureContext {
        cpu: request.cpu(), pid: request.pid(), requester: request.requester(),
        target: request.target(), number: request.number(),
        response: request.response(), response_end: request.response().checked_add(RESPONSE_BYTES as u64),
        conflict,
    }
}

fn log_conflict(os: u32, generation: u64, diag: u64, conflict: Option<FailureConflict>) {
    if let Some(old) = conflict {
        pr_err!("IHK-C os={} g={} d={} k={:?} i={} j={:?} s={:?}\n",
            os, generation, diag, old.kind, old.slot, old.member, old.serial);
        pr_err!("IHK-O os={} g={} d={} a={:x} b={:x}\n",
            os, generation, diag, old.span.physical, old.span.end);
    } else {
        pr_err!("IHK-C os={} g={} d={} k=none\n", os, generation, diag);
    }
}

fn log_syscall_failure(os: u32, generation: u64, diag: u64, error: Error, context: SyscallFailureContext) {
    pr_err!("IHK-E os={} g={} d={} at=syscall_claim e={}\n", os, generation, diag, error.to_errno());
    pr_err!("IHK-P os={} g={} d={} c={} p={} rq={} to={}\n",
        os, generation, diag, context.cpu, context.pid, context.requester, context.target);
    if let Some(end) = context.response_end {
        pr_err!("IHK-S os={} g={} d={} n={:x} a={:x} b={:x}\n",
            os, generation, diag, context.number, context.response, end);
    } else {
        pr_err!("IHK-S os={} g={} d={} n={:x} a={:x} b=none\n",
            os, generation, diag, context.number, context.response);
    }
    log_conflict(os, generation, diag, context.conflict);
}

#[derive(Clone,Debug)]
struct Ledger {
    fixed: Vec<Span>,
    requests: Vec<Option<Tagged>>,
    responses: Vec<Option<Tagged>>,
    payloads: Vec<Option<Tagged>>,
    // Separate bounded per-response exec group; ordinary payload semantics stay strict.
    exec_payloads: Vec<Option<Vec<Tagged>>>,
    snoops: Vec<Tagged>,
    procfs: Vec<Tagged>,
    zeroing: Vec<Tagged>,
    serial: u64,
}
static CONFLICT_CALLS:AtomicUsize=AtomicUsize::new(0);static TAG_CALLS:AtomicUsize=AtomicUsize::new(0);
impl Ledger {
 fn conflicts(&self,span:Span,snoops:bool)->bool{CONFLICT_CALLS.fetch_add(1,Ordering::Relaxed);self.actual_conflicts(span,snoops)}
 fn tag(&mut self,span:Span)->Result<Tagged>{TAG_CALLS.fetch_add(1,Ordering::Relaxed);self.actual_tag(span)}
    fn actual_conflicts(&self, span: Span, snoops: bool) -> bool {
        self.fixed.iter().any(|old| old.overlaps(span))
            || self
                .requests
                .iter()
                .flatten()
                .any(|old| old.span.overlaps(span))
            || self
                .payloads
                .iter()
                .flatten()
                .any(|old| old.span.overlaps(span))
            || self
                .responses
                .iter()
                .flatten()
                .any(|old| old.span.overlaps(span))
            || self.exec_payloads.iter().flatten().any(|group| group.iter().any(|old| old.span.overlaps(span)))
            || snoops && self.snoops.iter().any(|old| old.span.overlaps(span))
            || self.procfs.iter().any(|old| old.span.overlaps(span))
            || self.zeroing.iter().any(|old| old.span.overlaps(span))
    }
    fn actual_tag(&mut self, span: Span) -> Result<Tagged> {
        self.serial = self.serial.checked_add(1).ok_or_else(|| errno(-75))?;
        Ok(Tagged {
            span,
            serial: self.serial,
        })
    }
    fn diagnostic_conflict(&self, span: Span, snoops: bool) -> Option<FailureConflict> {
        for (slot, old) in self.fixed.iter().enumerate() {
            if old.overlaps(span) {
                return Some(FailureConflict { kind: ConflictKind::Fixed, slot, member: None, serial: None, span: *old });
            }
        }
        for (kind, slots) in [(ConflictKind::Request, &self.requests), (ConflictKind::Payload, &self.payloads), (ConflictKind::Response, &self.responses)] {
            for (slot, old) in slots.iter().enumerate() {
                if let Some(old) = old {
                    if old.span.overlaps(span) {
                        return Some(FailureConflict { kind, slot, member: None, serial: Some(old.serial), span: old.span });
                    }
                }
            }
        }
        for (slot, group) in self.exec_payloads.iter().enumerate() {
            if let Some(group) = group {
                for (member, old) in group.iter().enumerate() {
                    if old.span.overlaps(span) {
                        return Some(FailureConflict { kind: ConflictKind::ExecPayload, slot, member: Some(member), serial: Some(old.serial), span: old.span });
                    }
                }
            }
        }
        for (kind, tags, enabled) in [(ConflictKind::Snoop, &self.snoops, snoops), (ConflictKind::Procfs, &self.procfs, true), (ConflictKind::Zeroing, &self.zeroing, true)] {
            if enabled {
                for (slot, old) in tags.iter().enumerate() {
                    if old.span.overlaps(span) {
                        return Some(FailureConflict { kind, slot, member: None, serial: Some(old.serial), span: old.span });
                    }
                }
            }
        }
        None
    }
}
struct KernelMutex<T>(StdMutex<T>);
impl<T> KernelMutex<T>{fn lock(&self)->std::sync::MutexGuard<'_,T>{self.0.lock().unwrap()}}
struct Memory {owner:Owner,ledger:KernelMutex<Ledger>,failure_contexts:AtomicU64,address_calls:AtomicUsize,address_error:Option<Error>,backing:Box<[AtomicU64;5]>}
struct SyscallResponse {memory:Arc<Memory>,address:u64,tag:Tagged,slot:usize,payload:Option<()>,exec_group:Option<()>}
impl Memory {
 fn address(&self,_physical:u64,_bytes:usize)->Result<u64>{self.address_calls.fetch_add(1,Ordering::Relaxed);self.address_error.map_or(Ok(self.backing.as_ptr() as u64),Err)}
    pub(super) fn original_syscall(self: &Arc<Self>, request: &SyscallRequest) -> Result<SyscallResponse> {
        let physical = request.response();
        if physical % 8 != 0 {
            return Err(EINVAL);
        }
        let address = self.address(physical, RESPONSE_BYTES)?;
        let span = Span::new(physical, RESPONSE_BYTES)?;
        let mut ledger = self.ledger.lock();
        if ledger.conflicts(span, true) {
            return Err(EBUSY);
        }
        let slot = ledger
            .responses
            .iter()
            .position(Option::is_none)
            .ok_or(EAGAIN)?;
        // SAFETY: The checked exact-generation RAM is aligned and disjoint
        // from every active service access. The guest owns only atomic state.
        let status = unsafe { AtomicU64::from_ptr((address as *mut u8).add(8).cast()) };
        // SAFETY: The same retained, response-sized mapping covers the
        // eight-byte-aligned state word at offset 16. The held ledger claim
        // excludes host aliases, while the guest accesses this shared word
        // atomically; this creates no Rust reference to guest memory.
        let state = unsafe { AtomicU64::from_ptr((address as *mut u8).add(16).cast()) };
        if status.load(Ordering::Acquire) != 0 || !matches!(state.load(Ordering::Acquire), 0 | 2) {
            return Err(errno(-71));
        }
        let tag = ledger.tag(span)?;
        ledger.responses[slot] = Some(tag);
        Ok(SyscallResponse {
            memory: self.clone(),
            address,
            tag,
            slot,
            payload: None,
            exec_group: None,
        })
    }
    pub(super) fn syscall(self: &Arc<Self>, request: &SyscallRequest) -> Result<SyscallResponse> {
        let mut conflict = None;
        let result = (|| {
            let physical = request.response();
            if physical % 8 != 0 {
                return Err(EINVAL);
            }
            let address = self.address(physical, RESPONSE_BYTES)?;
            let span = Span::new(physical, RESPONSE_BYTES)?;
            let mut ledger = self.ledger.lock();
            if ledger.conflicts(span, true) {
                conflict = ledger.diagnostic_conflict(span, true);
                return Err(EBUSY);
            }
            let slot = ledger
                .responses
                .iter()
                .position(Option::is_none)
                .ok_or(EAGAIN)?;
            // SAFETY: The checked exact-generation RAM is aligned and disjoint
            // from every active service access. The guest owns only atomic state.
            let status = unsafe { AtomicU64::from_ptr((address as *mut u8).add(8).cast()) };
            // SAFETY: The same retained, response-sized mapping covers the
            // eight-byte-aligned state word at offset 16. The held ledger claim
            // excludes host aliases, while the guest accesses this shared word
            // atomically; this creates no Rust reference to guest memory.
            let state = unsafe { AtomicU64::from_ptr((address as *mut u8).add(16).cast()) };
            if status.load(Ordering::Acquire) != 0 || !matches!(state.load(Ordering::Acquire), 0 | 2) {
                return Err(errno(-71));
            }
            let tag = ledger.tag(span)?;
            ledger.responses[slot] = Some(tag);
            Ok(SyscallResponse {
                memory: self.clone(),
                address,
                tag,
                slot,
                payload: None,
                exec_group: None,
            })
        
        })();
        // The original ledger guard has ended. The copied snapshot has no
        // borrowed tag/pointer, and this diagnostic runs BEFORE returning the
        // same error to the unchanged mailbox/Remote quarantine path.
        if let Err(error) = &result {
            if *error != EAGAIN {
                if let Some(diag) = super::diagnostic_ticket(&self.failure_contexts) {
                    log_syscall_failure(self.owner.slot(), self.owner.generation(), diag,
                        *error, syscall_failure_context(request, conflict));
                }
            }
        }
        result
    }
    fn diagnostic_conflict_failure(&self, at: &'static str, span: Span,
        conflict: Option<FailureConflict>, own: Option<Tagged>, node_overlap: bool,
        route: Option<(i32, i32)>) {
        if let Some(diag) = super::diagnostic_ticket(&self.failure_contexts) {
            pr_err!("IHK-E os={} g={} d={} at={} e=-16 node={}\n",
                self.owner.slot(), self.owner.generation(), diag, at, node_overlap as u8);
            pr_err!("IHK-S os={} g={} d={} a={:x} b={:x}\n",
                self.owner.slot(), self.owner.generation(), diag, span.physical, span.end);
            if let Some((pid, cpu)) = route {
                pr_err!("IHK-P os={} g={} d={} p={} c={}\n",
                    self.owner.slot(), self.owner.generation(), diag, pid, cpu);
            }
            if let Some(own) = own {
                pr_err!("IHK-T os={} g={} d={} s={} a={:x} b={:x}\n",
                    self.owner.slot(), self.owner.generation(), diag, own.serial, own.span.physical, own.span.end);
            }
            log_conflict(self.owner.slot(), self.owner.generation(), diag, conflict);
        }
    }
    fn diagnostic_completion_failure(&self, kind: wire::Kind, tag: Tagged, operation_error: i32, busy: i32) {
        if let Some(diag) = super::diagnostic_ticket(&self.failure_contexts) {
            pr_err!("IHK-M os={} g={} d={} k={:?} busy={} op_e={} e=-16\n",
                self.owner.slot(), self.owner.generation(), diag, kind, busy, operation_error);
            pr_err!("IHK-T os={} g={} d={} s={} a={:x} b={:x}\n",
                self.owner.slot(), self.owner.generation(), diag, tag.serial, tag.span.physical, tag.span.end);
        }
    }
}
struct Entry{quarantined:bool}
fn quarantine_result(entry:&mut Entry,result:std::result::Result<(),i32>)->Result {
            if let Err(error) = result {
                if error != -11 {
                    entry.quarantined = true;
                }
                return Err(errno(error));
            }
            Ok(())
}
fn make_ledger(mask:u32,capacity:bool,serial:u64)->Ledger {
 let far=Span{physical:0x8000,end:0x8028};let overlap=Span{physical:0x1010,end:0x1038};
 let mut l=Ledger{fixed:vec![far],requests:vec![None;3],responses:vec![None;3],payloads:vec![None;3],exec_payloads:vec![None;3],snoops:vec![Tagged{span:far,serial:900}],procfs:vec![Tagged{span:far,serial:901}],zeroing:vec![Tagged{span:far,serial:902}],serial};
 if !capacity {for (i,t) in l.responses.iter_mut().enumerate(){*t=Some(Tagged{span:far,serial:800+i as u64})}}
 for bit in 0..8 {if mask&(1<<bit)==0{continue}let tag=Tagged{span:overlap,serial:100+bit};match bit{
 0=>l.fixed.push(overlap),1=>l.requests[1]=Some(tag),2=>l.payloads[1]=Some(tag),3=>l.responses[1]=Some(tag),4=>l.exec_payloads[1]=Some(vec![Tagged{span:far,serial:777},tag]),5=>l.snoops.push(tag),6=>l.procfs.push(tag),7=>l.zeroing.push(tag),_=>unreachable!()}}
 l
}
fn request(number:u64)->SyscallRequest{
 let mut p=[0xa5;128];for (at,value) in [(8,4i32),(24,1),(32,641),(48,643),(52,0)]{p[at..at+4].copy_from_slice(&value.to_le_bytes())}
 p[56..64].copy_from_slice(&1u64.to_le_bytes());p[64..72].copy_from_slice(&number.to_le_bytes());p[120..128].copy_from_slice(&0x1000u64.to_le_bytes());SyscallRequest::decode(&p,2).unwrap()
}
fn memory(l:Ledger,status:u64,state:u64,address_error:Option<Error>)->Arc<Memory>{Arc::new(Memory{owner:OWNER,ledger:KernelMutex(StdMutex::new(l)),failure_contexts:AtomicU64::new(0),address_calls:AtomicUsize::new(0),address_error,backing:Box::new([AtomicU64::new(0),AtomicU64::new(status),AtomicU64::new(state),AtomicU64::new(0),AtomicU64::new(0)])})}
#[derive(Debug,Eq,PartialEq)] struct Seen {errno:Option<i32>,response:Option<(Tagged,usize,bool,bool,bool)>,state:String,address_calls:usize,predicate_calls:usize,tag_calls:usize,quarantined:bool}
fn run(m:&Arc<Memory>,r:&SyscallRequest,actual:bool)->(Seen,Vec<String>){
 CONFLICT_CALLS.store(0,Ordering::Relaxed);TAG_CALLS.store(0,Ordering::Relaxed);take_events();let result=if actual {m.syscall(r)}else{m.original_syscall(r)};
 let error=result.as_ref().err().map(|e|e.to_errno());let response=result.as_ref().ok().map(|v|(v.tag,v.slot,v.address==m.backing.as_ptr() as u64,v.payload.is_none(),v.exec_group.is_none()));
 let mut entry=Entry{quarantined:false};let rr=quarantine_result(&mut entry,result.map(|_|()).map_err(|e|e.to_errno()));assert_eq!(rr.err().map(|e|e.to_errno()),error);if entry.quarantined{event("admission_quarantine".into())}
 (Seen{errno:error,response,state:format!("{:?}",*m.ledger.lock()),address_calls:m.address_calls.load(Ordering::Relaxed),predicate_calls:CONFLICT_CALLS.load(Ordering::Relaxed),tag_calls:TAG_CALLS.load(Ordering::Relaxed),quarantined:entry.quarantined},take_events())
}
pub(super) fn test()->usize {
 let mut n=0;
 for mask in 0..256 {for status in [0,1] {for state in [0,1,2,3] {for capacity in [false,true] {for serial in [0,u64::MAX] {
  let l=make_ledger(mask,capacity,serial);let a=memory(l.clone(),status,state,None);let b=memory(l,status,state,None);let r=request([11,228,0,u64::MAX][mask as usize%4]);let (old,old_events)=run(&a,&r,false);let (new,events)=run(&b,&r,true);assert_eq!(old,new);assert_eq!(old_events,events.iter().filter(|s|!is_diag(s)).cloned().collect::<Vec<_>>());
  assert_eq!(new.address_calls,1);assert_eq!(new.predicate_calls,1);assert_eq!(new.tag_calls,usize::from(mask==0&&capacity&&status==0&&(state==0||state==2)));
  if let Some(error)=new.errno {if error!=-11 {assert!(events[0].contains("at=syscall_claim"));assert!(events.iter().any(|s|s.contains("p=641 rq=643")));assert!(events.iter().any(|s|s.contains("a=1000")));assert_eq!(events.last().unwrap(),"admission_quarantine");assert!(events[..events.len()-1].iter().all(|s|is_diag(s)));check_lines(&events)}else{assert!(events.is_empty())}}
  if mask!=0 {let kinds=[ConflictKind::Fixed,ConflictKind::Request,ConflictKind::Payload,ConflictKind::Response,ConflictKind::ExecPayload,ConflictKind::Snoop,ConflictKind::Procfs,ConflictKind::Zeroing];let first=mask.trailing_zeros() as usize;let guard=b.ledger.lock();let c=guard.diagnostic_conflict(Span{physical:0x1000,end:0x1028},true).unwrap();assert_eq!(c.kind,kinds[first]);assert_eq!(c.slot,1);assert_eq!(c.serial,if first==0{None}else{Some(100+first as u64)});assert_eq!(c.member,if first==4{Some(1)}else{None});}
  n+=1;
 }}}}}
 // Exact half-open boundaries, snoop-ignore semantics and mixed firstmatch.
 for mask in 0..256 {let l=make_ledger(mask,true,0);for span in [Span{physical:0x1000,end:0x1010},Span{physical:0x1010,end:0x1020},Span{physical:0x1038,end:0x1040}] {for snoops in [false,true] {assert_eq!(l.actual_conflicts(span,snoops),l.diagnostic_conflict(span,snoops).is_some());}}}
 // Mapping errors retain zero ledger/predicate/tag calls and same quarantine.
 for e in [-5,-14,-22] {let r=request(11);let a=memory(make_ledger(0,true,0),0,0,Some(errno(e)));let b=memory(make_ledger(0,true,0),0,0,Some(errno(e)));let (x,_)=run(&a,&r,false);let(y,events)=run(&b,&r,true);assert_eq!(x,y);assert_eq!(y.predicate_calls,0);assert_eq!(y.tag_calls,0);assert!(events.iter().any(|s|s.contains("k=none")));n+=1;}
 // Ordinary EAGAIN must not consume fatal-context tickets before a later EBUSY.
 let m=memory(make_ledger(0,false,0),0,0,None);let r=request(11);for _ in 0..100 {assert_eq!(m.syscall(&r).err().unwrap().to_errno(),-11)}assert_eq!(m.failure_contexts.load(Ordering::Relaxed),0);assert!(take_events().is_empty());
 m.ledger.lock().fixed.push(Span{physical:0x1000,end:0x1028});for _ in 0..100 {assert_eq!(m.syscall(&r).err().unwrap().to_errno(),-16)}assert_eq!(m.failure_contexts.load(Ordering::Relaxed),16);assert_eq!(take_events().iter().filter(|s|s.starts_with("IHK-E")).count(),16);
 n
}

pub(super) fn width_test(){
 take_events();let os=u32::MAX;let gen=u64::MAX;let span=Span{physical:u64::MAX-1,end:u64::MAX};
 let conflict=FailureConflict{kind:ConflictKind::ExecPayload,slot:usize::MAX,member:Some(usize::MAX),serial:Some(u64::MAX),span};
 for end in [None,Some(u64::MAX)] {log_syscall_failure(os,gen,16,errno(i32::MIN),SyscallFailureContext{cpu:i32::MIN,pid:i32::MIN,requester:i32::MIN,target:i32::MIN,number:u64::MAX,response:u64::MAX,response_end:end,conflict:Some(conflict)});}
 let mut m=memory(make_ledger(0,true,0),0,0,None);Arc::get_mut(&mut m).unwrap().owner=Owner{slot:os,generation:gen};
 for at in ["zero_control","zero_header","zero_chunk","zeroed_head","procfs_overlap"] {m.diagnostic_conflict_failure(at,span,Some(conflict),Some(Tagged{span,serial:u64::MAX}),true,Some((i32::MIN,i32::MIN)));}
 for kind in [wire::Kind::Create,wire::Kind::Mkdir,wire::Kind::Symlink,wire::Kind::Lookup,wire::Kind::Unlink]{m.diagnostic_completion_failure(kind,Tagged{span,serial:u64::MAX},i32::MIN,i32::MIN);}
 check_lines(&take_events());
}
}

mod remote_fixture {
use super::*;
const ENODEV:Error=Error(-19);
struct KernelMutex<T>(StdMutex<T>);impl<T> KernelMutex<T>{fn lock(&self)->std::sync::MutexGuard<'_,T>{self.0.lock().unwrap()}}
struct State{peer_stopped:bool,exchange:actual_rpc::Exchange}
struct Data{owner:Owner}
struct Changed(AtomicUsize);impl Changed{fn notify_all(&self){self.0.fetch_add(1,Ordering::Relaxed);}}
struct Remote{state:KernelMutex<State>,data:Data,changed:Changed,failure_contexts:AtomicU64}
impl Remote {
    pub(crate) fn original_reply(&self, packet: &[u8]) -> Result {
        let mut state = self.state.lock();
        if state.peer_stopped {
            return Err(ENODEV);
        }
        state.exchange.accept(packet).map_err(errno)?;
        drop(state);
        self.changed.notify_all();
        Ok(())
    }
    pub(crate) fn reply(&self, packet: &[u8]) -> Result {
        let mut state = self.state.lock();
        if state.peer_stopped {
            return Err(ENODEV);
        }
        if let Err(error) = state.exchange.accept(packet) {
            if error == -16 {
                if let Some(context) = state.exchange.reply_failure_context(packet) {
                    if let Ok(diag) = self.failure_contexts.fetch_update(Ordering::Relaxed, Ordering::Relaxed,
                        |old| if old < 16 { Some(old + 1) } else { None }) {
                        pr_err!("IHK-R os={} g={} d={} m={:x} t={:x} pt={:x} ph={:?} e=-16\n",
                            self.data.owner.slot(), self.data.owner.generation(), diag + 1,
                            context.message, context.token, context.pending_token, context.phase);
                        pr_err!("IHK-V os={} g={} d={} peer_e={} value={}\n",
                            self.data.owner.slot(), self.data.owner.generation(), diag + 1, context.error, context.result);
                    }
                }
            }
            return Err(errno(error));
        }
        drop(state);
        self.changed.notify_all();
        Ok(())
    }
}
pub(super) fn test()->usize {
 let mut n=0;
 for phase in 0..3 {for wrong in 0..4 {for stopped in [false,true] {
 let create=||{let mut e=actual_rpc::Exchange::new();let t=e.begin(actual_wire::Client{operations:1001,instance:2},actual_rpc::Call::Show{capacity:10}).unwrap();if phase!=0{e.published(t).unwrap();}if phase==2{let mut p=[0u8;128];p[8..12].copy_from_slice(&0x3bi32.to_le_bytes());p[24..32].copy_from_slice(&t.wire().to_le_bytes());e.accept(&p).unwrap();} (Remote{state:KernelMutex(StdMutex::new(State{peer_stopped:stopped,exchange:e})),data:Data{owner:Owner{slot:u32::MAX,generation:u64::MAX}},changed:Changed(AtomicUsize::new(0)),failure_contexts:AtomicU64::new(0)},t)};
 let (a,ta)=create();let (b,tb)=create();let packet=|t:actual_rpc::Token|{let mut p=vec![0u8;128];p[8..12].copy_from_slice(&(if wrong==1{0x3d}else{0x3b} as i32).to_le_bytes());p[12..16].copy_from_slice(&i32::MIN.to_le_bytes());p[16..24].copy_from_slice(&0x1122334455667788u64.to_le_bytes());p[24..32].copy_from_slice(&(t.wire()+u64::from(wrong==2)).to_le_bytes());p[32..40].copy_from_slice(&i64::MIN.to_le_bytes());if wrong==3{p.pop();}p};
 take_events();let x=a.original_reply(&packet(ta));let xe=take_events();let y=b.reply(&packet(tb));let ye=take_events();assert_eq!(x,y);assert!(xe.is_empty());assert_eq!(a.changed.0.load(Ordering::Relaxed),b.changed.0.load(Ordering::Relaxed));assert_eq!(a.state.lock().exchange.completed(ta),b.state.lock().exchange.completed(tb));
 if y==Err(EBUSY){assert_eq!(ye.len(),2);assert!(ye[0].contains(&format!("t={:x}",tb.wire())));assert!(!ye[0].contains("1122334455667788"));assert!(ye[0].contains(if phase==0{"Queued"}else{"Complete"}));}else{assert!(ye.is_empty());}check_lines(&ye);n+=1;
 }}}
 n
}
}
mod application_fixture {
use super::*;
struct Preparation(Option<i32>);impl Preparation{fn result(&self)->Option<i32>{self.0}}
struct Ingress{host_revoke:Option<()>,sealed:AtomicBool}
struct Cleanup;impl Cleanup{fn pid(&self)->i32{i32::MIN}fn reserved(&self)->bool{true}fn result(&self)->Option<i32>{Some(i32::MIN)}fn token(&self)->Token{Token}}
struct Token;impl Token{fn wire(&self)->u64{u64::MAX}}
struct Mailbox;impl Mailbox{fn drained(&self)->bool{true}}
struct Entry{prepare:Option<Preparation>,fork_ingress:Option<Ingress>,inherited_root:Option<()>,cleanup:Cleanup,needs_cleanup:bool,scheduled:bool,quarantined:bool,closed:bool,syscalls:Mailbox}
struct Remote{owner:Owner,failure_contexts:AtomicU64}
impl Remote {
    fn diagnostic_application_failure(&self, at: &'static str, entry: &Entry, cpu: i32, error: Error) {
        if let Ok(ticket) = self.failure_contexts.fetch_update(Ordering::Relaxed, Ordering::Relaxed,
            |old| if old < 16 { Some(old + 1) } else { None }) {
            let diag = ticket + 1;
            let prepare = entry.prepare.as_ref().and_then(|image| image.result());
            let revoke = entry.fork_ingress.as_ref().is_some_and(|owner| owner.host_revoke.is_some());
            let sealed = entry.fork_ingress.as_ref().map(|owner| owner.sealed.load(Ordering::Acquire));
            pr_err!("IHK-A os={} g={} d={} at={} p={} c={} e={}\n",
                self.owner.slot(), self.owner.generation(), diag, at, entry.cleanup.pid(), cpu, error.to_errno());
            pr_err!("IHK-B os={} g={} d={} prep={} ret={:?} rev={} inh={} seal={:?}\n",
                self.owner.slot(), self.owner.generation(), diag, entry.prepare.is_some() as u8,
                prepare, revoke as u8, entry.inherited_root.is_some() as u8, sealed);
            pr_err!("IHK-F os={} g={} d={} need={} sch={} q={} closed={} drain={} res={} ret={:?}\n",
                self.owner.slot(), self.owner.generation(), diag, entry.needs_cleanup as u8,
                entry.scheduled as u8, entry.quarantined as u8, entry.closed as u8,
                entry.syscalls.drained() as u8, entry.cleanup.reserved() as u8, entry.cleanup.result());
            pr_err!("IHK-K os={} g={} d={} token={:x}\n",
                self.owner.slot(), self.owner.generation(), diag, entry.cleanup.token().wire());
        }
    }
}
pub(super) fn test(){
 let r=Remote{owner:Owner{slot:u32::MAX,generation:u64::MAX},failure_contexts:AtomicU64::new(0)};
 let mut e=Entry{prepare:Some(Preparation(Some(i32::MIN))),fork_ingress:Some(Ingress{host_revoke:Some(()),sealed:AtomicBool::new(false)}),inherited_root:Some(()),cleanup:Cleanup,needs_cleanup:true,scheduled:true,quarantined:true,closed:true,syscalls:Mailbox};
 take_events();for i in 0..100{r.diagnostic_application_failure(if i%2==0{"procfs_backend"}else{"prepare_cleanup"},&e,i32::MIN,errno(i32::MIN));}let events=take_events();assert_eq!(events.len(),64);assert_eq!(r.failure_contexts.load(Ordering::Relaxed),16);assert!(events.iter().any(|s|s.contains("at=procfs_backend")));assert!(events.iter().any(|s|s.contains("at=prepare_cleanup")));check_lines(&events);
 // Explicit absent/none host state is logged without dereferencing absent data.
 e.prepare=None;e.fork_ingress=None;e.inherited_root=None;let r=Remote{owner:OWNER,failure_contexts:AtomicU64::new(0)};r.diagnostic_application_failure("procfs_backend",&e,0,EBUSY);check_lines(&take_events());
}
}
fn protocol_test()->(usize,usize){
 let mut completions=0;
 for (ok,nk) in [(original_wire::Kind::Create,actual_wire::Kind::Create),(original_wire::Kind::Mkdir,actual_wire::Kind::Mkdir),(original_wire::Kind::Symlink,actual_wire::Kind::Symlink),(original_wire::Kind::Lookup,actual_wire::Kind::Lookup),(original_wire::Kind::Unlink,actual_wire::Kind::Unlink)] {
 for busy in [i32::MIN,-1,0,1,2,i32::MAX] {for error in [-16,0,-22] {
 let mut a=Box::new([0u64;512]);let mut b=Box::new([0u64;512]);let ap=a.as_mut_ptr().cast::<u8>();let bp=b.as_mut_ptr().cast::<u8>();let layout=nk.layout();assert_eq!(layout.busy,ok.layout().busy);
 unsafe{AtomicI32::from_ptr(ap.add(layout.busy).cast()).store(busy,Ordering::Relaxed);AtomicI32::from_ptr(bp.add(layout.busy).cast()).store(busy,Ordering::Relaxed);}
 let handle=if error==0&&matches!(nk,actual_wire::Kind::Mkdir|actual_wire::Kind::Lookup){Some(1)}else{None};let mut observed=Vec::new();let x=unsafe{original_wire::complete(ok,ap,error,handle)};let y=unsafe{actual_wire::complete_observed(nk,bp,error,handle,|v|observed.push(v))};assert_eq!(x,y);assert_eq!(a.as_ref(),b.as_ref());assert_eq!(observed.len(),usize::from(busy!=1));if busy!=1{assert_eq!(observed[0].value,busy);assert_eq!(observed[0].kind,nk);}completions+=1;
 }}}
 // Full original/actual exchange accept with typed tokens normalized only in
 // request construction. No expected token is guessed or taken from app16.
 let mut rpc=0;
 for phase in 0..3 {for wrong in 0..4 {
 let mut a=original_rpc::Exchange::new();let mut b=actual_rpc::Exchange::new();let client=actual_wire::Client{operations:1001,instance:u64::MAX};let ta=a.begin(client,original_rpc::Call::Show{capacity:10}).unwrap();let tb=b.begin(client,actual_rpc::Call::Show{capacity:10}).unwrap();
 if phase!=0{a.published(ta).unwrap();b.published(tb).unwrap();}
 let packet=|t:u64|{let mut p=vec![0;128];p[8..12].copy_from_slice(&0x3bi32.to_le_bytes());p[16..24].copy_from_slice(&0x1122334455667788u64.to_le_bytes());p[24..32].copy_from_slice(&t.to_le_bytes());p};
 if phase==2{a.accept(&packet(ta.wire())).unwrap();b.accept(&packet(tb.wire())).unwrap();}
 let change=|mut p:Vec<u8>|{match wrong{1=>p[8..12].copy_from_slice(&0x3di32.to_le_bytes()),2=>p[24..32].copy_from_slice(&u64::MAX.to_le_bytes()),3=>{p.pop();},_=>()}p};let pa=change(packet(ta.wire()));let pb=change(packet(tb.wire()));let before=b.completed(tb);let ctx=b.reply_failure_context(&pb);assert_eq!(before,b.completed(tb));if pb.len()==128{let ctx=ctx.unwrap();assert_eq!(ctx.token,if wrong==2{u64::MAX}else{tb.wire()});assert_eq!(ctx.pending_token,tb.wire());assert_eq!(ctx.phase,[actual_rpc::ReplyFailurePhase::Queued,actual_rpc::ReplyFailurePhase::Published,actual_rpc::ReplyFailurePhase::Complete][phase]);}else{assert!(ctx.is_none());}
 assert_eq!(a.accept(&pa),b.accept(&pb));assert_eq!(a.completed(ta),b.completed(tb));assert_eq!(a.finish(ta),b.finish(tb));rpc+=1;
 }}(completions,rpc)
}
fn main(){let n=memory::test();memory::width_test();let (completions,rpc)=protocol_test();assert_eq!(completions,90);assert_eq!(rpc,12);assert_eq!(remote_fixture::test(),24);application_fixture::test();assert_eq!(n,8195);
 let origins=[FailureOrigin::Packet{channel:2,guest_cpu:1,port:503,message:4},FailureOrigin::ControlPump,FailureOrigin::RegularPump,FailureOrigin::PublishRemote,FailureOrigin::PublishApplications,FailureOrigin::PublishSyscalls,FailureOrigin::AdvanceApplications,FailureOrigin::PublishProcfs,FailureOrigin::Metadata,FailureOrigin::Zeroing];
 let old=Runtime::new();let new=Runtime::new();for i in 0..100{take_events();old.original_fail(EBUSY);let a=take_events();new.fail(EBUSY,origins[i%origins.len()]);let b=take_events();assert_eq!(a,b.iter().filter(|s|!is_diag(s)).cloned().collect::<Vec<_>>());if i<16{assert!(b[0].contains("at="));check_lines(&b);if i==0{let q=b.iter().position(|s|s=="service_quarantine").unwrap();assert!(b[..q].iter().all(|s|is_diag(s)));}}else{assert!(!b.iter().any(|s|is_diag(s)));}}
 assert_eq!(old.application.calls.load(Ordering::Relaxed),new.application.calls.load(Ordering::Relaxed));assert_eq!(new.application.calls.load(Ordering::Relaxed),100);assert_eq!(old.application.quarantines.load(Ordering::Relaxed),1);assert_eq!(new.application.quarantines.load(Ordering::Relaxed),1);assert_eq!(old.error.load(Ordering::Acquire),new.error.load(Ordering::Acquire));assert_eq!(new.failure_contexts.load(Ordering::Relaxed),16);
 let mut wide=Runtime::new();wide.owner=Owner{slot:u32::MAX,generation:u64::MAX};for origin in [FailureOrigin::Packet{channel:usize::MAX,guest_cpu:u32::MAX,port:i32::MIN,message:i32::MIN},FailureOrigin::PublishApplications]{wide.failure_context(errno(i32::MIN),origin);}check_lines(&take_events());
 for i in 0..origins.len(){for j in 0..i{assert_ne!(format!("{:?}",origins[i]),format!("{:?}",origins[j]));}}
 println!("PASS memory_pairs={} conflict_bucket_masks=256 origins=10 observer_before_quarantine=1 errors_claims_callcounts_unchanged=1 budgets=16 metadata_pairs=90 rpc_pairs=12 remote_pairs=24 line_prefix_budget=96; HOST_PRIMITIVES_MODELED_NO_NATIVE",n);
}
