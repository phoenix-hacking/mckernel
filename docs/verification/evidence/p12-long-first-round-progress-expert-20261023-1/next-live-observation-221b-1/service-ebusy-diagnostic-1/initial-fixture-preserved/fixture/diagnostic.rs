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
#[derive(Clone,Copy)] struct Owner;
impl Owner {fn slot(self)->u32{0}fn generation(self)->u64{1}}
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
fn diagnostic_ticket(counter: &AtomicU64) -> bool {
    counter.fetch_update(Ordering::Relaxed, Ordering::Relaxed, |old| {
        if old < 16 { Some(old + 1) } else { None }
    }).is_ok()
}
struct Application {calls:AtomicUsize,quarantines:AtomicUsize}
impl Application {fn fail_service(&self,error:&AtomicI32,e:Error)->bool {
 self.calls.fetch_add(1,Ordering::Relaxed);
 if error.compare_exchange(0,e.to_errno(),Ordering::AcqRel,Ordering::Acquire).is_ok(){self.quarantines.fetch_add(1,Ordering::Relaxed);event("service_quarantine".into());true}else{false}
}}
struct Runtime {owner:Owner,application:Application,error:AtomicI32,failure_contexts:AtomicU64}
impl Runtime {fn new()->Self{Self{owner:Owner,application:Application{calls:AtomicUsize::new(0),quarantines:AtomicUsize::new(0)},error:AtomicI32::new(0),failure_contexts:AtomicU64::new(0)}}
    fn original_fail(&self, error: Error) {
        if self.application.fail_service(&self.error, error) {
            pr_err!("IHK-SMP: continuing service error os={} generation={} errno={}; workers and all started owners retained\n",
                self.owner.slot(), self.owner.generation(), error.to_errno());
        }
    }
    fn fail(&self, error: Error, origin: FailureOrigin) {
        if diagnostic_ticket(&self.failure_contexts) {
            pr_err!("IHK-SMP: service failure context os={} generation={} origin={:?} errno={}; diagnostic only, owners unchanged\n",
                self.owner.slot(), self.owner.generation(), origin, error.to_errno());
        }
        if self.application.fail_service(&self.error, error) {
            pr_err!("IHK-SMP: continuing service error os={} generation={} errno={}; workers and all started owners retained\n",
                self.owner.slot(), self.owner.generation(), error.to_errno());
        }
    }
}
mod memory {
use super::*;
use crate::application_syscall::Request as SyscallRequest;
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
            if *error != EAGAIN && super::diagnostic_ticket(&self.failure_contexts) {
                let context = syscall_failure_context(request, conflict);
                pr_err!("IHK-SMP: service failure context os={} generation={} origin=syscall_response_claim errno={} route={:?}; diagnostic only, owners unchanged\n",
                    self.owner.slot(), self.owner.generation(), error.to_errno(), context);
            }
        }
        result
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
fn memory(l:Ledger,status:u64,state:u64,address_error:Option<Error>)->Arc<Memory>{Arc::new(Memory{owner:Owner,ledger:KernelMutex(StdMutex::new(l)),failure_contexts:AtomicU64::new(0),address_calls:AtomicUsize::new(0),address_error,backing:Box::new([AtomicU64::new(0),AtomicU64::new(status),AtomicU64::new(state),AtomicU64::new(0),AtomicU64::new(0)])})}
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
  let l=make_ledger(mask,capacity,serial);let a=memory(l.clone(),status,state,None);let b=memory(l,status,state,None);let r=request([11,228,0,u64::MAX][mask as usize%4]);let (old,old_events)=run(&a,&r,false);let (new,events)=run(&b,&r,true);assert_eq!(old,new);assert_eq!(old_events,events.iter().filter(|s|!s.starts_with("IHK-SMP: service failure context")).cloned().collect::<Vec<_>>());
  assert_eq!(new.address_calls,1);assert_eq!(new.predicate_calls,1);assert_eq!(new.tag_calls,usize::from(mask==0&&capacity&&status==0&&(state==0||state==2)));
  if let Some(error)=new.errno {if error!=-11 {assert!(events[0].contains("origin=syscall_response_claim"));assert!(events[0].contains("pid: 641")&&events[0].contains("requester: 643")&&events[0].contains("response: 4096"));assert!(events[1]=="admission_quarantine");assert_eq!(events.len(),2)}else{assert!(events.is_empty())}}
  if mask!=0 {let kinds=[ConflictKind::Fixed,ConflictKind::Request,ConflictKind::Payload,ConflictKind::Response,ConflictKind::ExecPayload,ConflictKind::Snoop,ConflictKind::Procfs,ConflictKind::Zeroing];let first=mask.trailing_zeros() as usize;let guard=b.ledger.lock();let c=guard.diagnostic_conflict(Span{physical:0x1000,end:0x1028},true).unwrap();assert_eq!(c.kind,kinds[first]);assert_eq!(c.slot,1);assert_eq!(c.serial,if first==0{None}else{Some(100+first as u64)});assert_eq!(c.member,if first==4{Some(1)}else{None});}
  n+=1;
 }}}}}
 // Exact half-open boundaries, snoop-ignore semantics and mixed firstmatch.
 for mask in 0..256 {let l=make_ledger(mask,true,0);for span in [Span{physical:0x1000,end:0x1010},Span{physical:0x1010,end:0x1020},Span{physical:0x1038,end:0x1040}] {for snoops in [false,true] {assert_eq!(l.actual_conflicts(span,snoops),l.diagnostic_conflict(span,snoops).is_some());}}}
 // Mapping errors retain zero ledger/predicate/tag calls and same quarantine.
 for e in [-5,-14,-22] {let r=request(11);let a=memory(make_ledger(0,true,0),0,0,Some(errno(e)));let b=memory(make_ledger(0,true,0),0,0,Some(errno(e)));let (x,_)=run(&a,&r,false);let(y,events)=run(&b,&r,true);assert_eq!(x,y);assert_eq!(y.predicate_calls,0);assert_eq!(y.tag_calls,0);assert!(events[0].contains("conflict: None"));n+=1;}
 // Ordinary EAGAIN must not consume fatal-context tickets before a later EBUSY.
 let m=memory(make_ledger(0,false,0),0,0,None);let r=request(11);for _ in 0..100 {assert_eq!(m.syscall(&r).err().unwrap().to_errno(),-11)}assert_eq!(m.failure_contexts.load(Ordering::Relaxed),0);assert!(take_events().is_empty());
 m.ledger.lock().fixed.push(Span{physical:0x1000,end:0x1028});for _ in 0..100 {assert_eq!(m.syscall(&r).err().unwrap().to_errno(),-16)}assert_eq!(m.failure_contexts.load(Ordering::Relaxed),16);assert_eq!(take_events().len(),16);
 n
}
}
fn main(){let n=memory::test();assert_eq!(n,8195);
 let origins=[FailureOrigin::Packet{channel:2,guest_cpu:1,port:503,message:4},FailureOrigin::ControlPump,FailureOrigin::RegularPump,FailureOrigin::PublishRemote,FailureOrigin::PublishApplications,FailureOrigin::PublishSyscalls,FailureOrigin::AdvanceApplications,FailureOrigin::PublishProcfs,FailureOrigin::Metadata,FailureOrigin::Zeroing];
 let old=Runtime::new();let new=Runtime::new();for i in 0..100{take_events();old.original_fail(EBUSY);let a=take_events();new.fail(EBUSY,origins[i%origins.len()]);let b=take_events();assert_eq!(a,b.iter().filter(|s|!s.starts_with("IHK-SMP: service failure context")).cloned().collect::<Vec<_>>());if i<16{assert!(b[0].contains("origin="));if i==0{assert_eq!(b[1],"service_quarantine");}}else{assert!(!b.iter().any(|s|s.starts_with("IHK-SMP: service failure context")));}}
 assert_eq!(old.application.calls.load(Ordering::Relaxed),new.application.calls.load(Ordering::Relaxed));assert_eq!(new.application.calls.load(Ordering::Relaxed),100);assert_eq!(old.application.quarantines.load(Ordering::Relaxed),1);assert_eq!(new.application.quarantines.load(Ordering::Relaxed),1);assert_eq!(old.error.load(Ordering::Acquire),new.error.load(Ordering::Acquire));assert_eq!(new.failure_contexts.load(Ordering::Relaxed),16);
 for i in 0..origins.len(){for j in 0..i{assert_ne!(format!("{:?}",origins[i]),format!("{:?}",origins[j]));}}
 println!("PASS memory_pairs={} conflict_bucket_masks=256 origins=10 observer_before_quarantine=1 errors_claims_callcounts_unchanged=1 budgets=16; HOST_PRIMITIVES_MODELED_NO_NATIVE",n);
}
