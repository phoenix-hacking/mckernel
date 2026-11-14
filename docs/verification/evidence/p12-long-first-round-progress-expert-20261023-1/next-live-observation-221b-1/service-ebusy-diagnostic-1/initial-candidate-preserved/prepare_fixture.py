# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json,hashlib
P=Path(__file__).resolve().parent;F=P/'fixture';R=Path('/home/holden/mckernel');b=json.loads((P/'SOURCE-BINDINGS.json').read_text())
orig={k:Path(v['selected_original']['path']).read_text() for k,v in b['changes'].items()};new={k:(P/'source'/k).read_text() for k in orig}
def function(s,marker):
 lines=s.splitlines(keepends=True);hits=[i for i,x in enumerate(lines) if x.lstrip().startswith(marker)];assert len(hits)==1,(marker,hits);a=hits[0];indent=len(lines[a])-len(lines[a].lstrip());end=next(i for i in range(a+1,len(lines)) if lines[i].rstrip()==' '*indent+'}');return ''.join(lines[a:end+1]).rstrip('\n')
def structure(s,marker):
 a=s.index(marker);end=s.index('\n}',a)+2;return s[a:end]
def pin(p):
 raw=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
def write(p,s):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s)
# Actual typed Request representation, decoder and only the existing getters
# used in diagnostics. Unused packet argument/padding bytes are never decoded.
request=Path(b['unmodified_error_ownership_modules']['application_syscall.rs']['path']).read_text()
req=structure(request,'pub(crate) struct Request {');methods='\n'.join(function(request,'pub(crate) fn '+name+'(') for name in ['decode','cpu','pid','requester','target','response','number'])
write(F/'actual_request.rs','const REQUEST_BYTES:usize=72;const RESPONSE_BYTES:usize=40;\n#[derive(Clone,Debug,Eq,PartialEq)]\n'+req+'\nimpl Request {\n'+methods+'\n}\n')
# The following branch is copied from the real unchanged Remote::syscall_request;
# the fixture rehosts only its entry/result primitives, not the live Remote.
remote=Path(b['unmodified_error_ownership_modules']['smp_application.rs']['path']).read_text();branch='''            if let Err(error) = result {
                if error != -11 {
                    entry.quarantined = true;
                }
                return Err(errno(error));
            }
            Ok(())''';assert branch in remote
write(F/'actual_quarantine_branch.rs',branch+'\n')
prefix='''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
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
'''
service=new['smp_service.rs'];origin=structure(service,'enum FailureOrigin {');ticket=function(service,'fn diagnostic_ticket(')
# Compile BOTH actual original/new Runtime.fail bodies; only application and
# owner primitives are mocked. Existing fail_service call/counts stay identical.
oldfail=function(orig['smp_service.rs'],'fn fail(&self, error: Error)').replace('fn fail(', 'fn original_fail(',1);newfail=function(service,'fn fail(&self, error: Error, origin:')
runtime='''#[derive(Clone,Copy,Debug,Eq,PartialEq)]
'''+origin+'\n'+ticket+'''
struct Application {calls:AtomicUsize,quarantines:AtomicUsize}
impl Application {fn fail_service(&self,error:&AtomicI32,e:Error)->bool {
 self.calls.fetch_add(1,Ordering::Relaxed);
 if error.compare_exchange(0,e.to_errno(),Ordering::AcqRel,Ordering::Acquire).is_ok(){self.quarantines.fetch_add(1,Ordering::Relaxed);event("service_quarantine".into());true}else{false}
}}
struct Runtime {owner:Owner,application:Application,error:AtomicI32,failure_contexts:AtomicU64}
impl Runtime {fn new()->Self{Self{owner:Owner,application:Application{calls:AtomicUsize::new(0),quarantines:AtomicUsize::new(0)},error:AtomicI32::new(0),failure_contexts:AtomicU64::new(0)}}
'''+oldfail+'\n'+newfail+'\n}\n'
m=new['sysfs_memory.rs'];om=orig['sysfs_memory.rs'];span=structure(m,'pub(super) struct Span {');tagged=structure(m,'struct Tagged {');ledger=structure(m,'struct Ledger {');contexts=m[m.index('// Diagnostic snapshots'):m.index('struct Ledger {')]
# Actual Ledger methods retained. Instrumented wrappers count invocations of
# the original predicate/tag bodies identically on both candidate paths.
conflicts=function(m,'fn conflicts(').replace('fn conflicts(','fn actual_conflicts(',1);tag=function(m,'fn tag(').replace('fn tag(','fn actual_tag(',1)
scanner=function(m,'fn diagnostic_conflict(');spanmethods='\n'.join(function(m,mark) for mark in ['pub(super) fn new(physical:','fn overlaps(self,'])
oldcall=function(om,'pub(super) fn syscall(').replace('fn syscall(', 'fn original_syscall(',1);newcall=function(m,'pub(super) fn syscall(')
mem='''mod memory {
use super::*;
use crate::application_syscall::Request as SyscallRequest;
const RESPONSE_BYTES:usize=40;
#[derive(Clone,Copy,Debug,Eq,PartialEq)]
'''+span+'\nimpl Span {\n'+spanmethods+'\n}\n#[derive(Clone,Copy,Debug,Eq,PartialEq)]\n'+tagged+'\n'+contexts+'#[derive(Clone,Debug)]\n'+ledger+'''
static CONFLICT_CALLS:AtomicUsize=AtomicUsize::new(0);static TAG_CALLS:AtomicUsize=AtomicUsize::new(0);
impl Ledger {
 fn conflicts(&self,span:Span,snoops:bool)->bool{CONFLICT_CALLS.fetch_add(1,Ordering::Relaxed);self.actual_conflicts(span,snoops)}
 fn tag(&mut self,span:Span)->Result<Tagged>{TAG_CALLS.fetch_add(1,Ordering::Relaxed);self.actual_tag(span)}
'''+conflicts+'\n'+tag+'\n'+scanner+'''
}
struct KernelMutex<T>(StdMutex<T>);
impl<T> KernelMutex<T>{fn lock(&self)->std::sync::MutexGuard<'_,T>{self.0.lock().unwrap()}}
struct Memory {owner:Owner,ledger:KernelMutex<Ledger>,failure_contexts:AtomicU64,address_calls:AtomicUsize,address_error:Option<Error>,backing:Box<[AtomicU64;5]>}
struct SyscallResponse {memory:Arc<Memory>,address:u64,tag:Tagged,slot:usize,payload:Option<()>,exec_group:Option<()>}
impl Memory {
 fn address(&self,_physical:u64,_bytes:usize)->Result<u64>{self.address_calls.fetch_add(1,Ordering::Relaxed);self.address_error.map_or(Ok(self.backing.as_ptr() as u64),Err)}
'''+oldcall+'\n'+newcall+'\n}\n'
# Quarantine policy branch is exactly the real source bytes. The entry/admit
# receiver is an explicit model; no real task, MM, ACK or launcher is involved.
mem+='''struct Entry{quarantined:bool}
fn quarantine_result(entry:&mut Entry,result:std::result::Result<(),i32>)->Result {
'''+branch+'''\n}
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
'''
# Counted fields in fixture response permit exact equality; no production layout
# or kernel primitive implementation is being asserted by these models.
mem=mem.replace('#[derive(Clone,Copy,Debug,Eq,PartialEq)]\nstruct Tagged', '#[derive(Clone,Copy,Debug,Eq,PartialEq)]\nstruct Tagged',1)
# Actual Tagged production only derivesCopy; fixture adds comparison traits above.
main='''fn main(){let n=memory::test();assert_eq!(n,8195);
 let origins=[FailureOrigin::Packet{channel:2,guest_cpu:1,port:503,message:4},FailureOrigin::ControlPump,FailureOrigin::RegularPump,FailureOrigin::PublishRemote,FailureOrigin::PublishApplications,FailureOrigin::PublishSyscalls,FailureOrigin::AdvanceApplications,FailureOrigin::PublishProcfs,FailureOrigin::Metadata,FailureOrigin::Zeroing];
 let old=Runtime::new();let new=Runtime::new();for i in 0..100{take_events();old.original_fail(EBUSY);let a=take_events();new.fail(EBUSY,origins[i%origins.len()]);let b=take_events();assert_eq!(a,b.iter().filter(|s|!s.starts_with("IHK-SMP: service failure context")).cloned().collect::<Vec<_>>());if i<16{assert!(b[0].contains("origin="));if i==0{assert_eq!(b[1],"service_quarantine");}}else{assert!(!b.iter().any(|s|s.starts_with("IHK-SMP: service failure context")));}}
 assert_eq!(old.application.calls.load(Ordering::Relaxed),new.application.calls.load(Ordering::Relaxed));assert_eq!(new.application.calls.load(Ordering::Relaxed),100);assert_eq!(old.application.quarantines.load(Ordering::Relaxed),1);assert_eq!(new.application.quarantines.load(Ordering::Relaxed),1);assert_eq!(old.error.load(Ordering::Acquire),new.error.load(Ordering::Acquire));assert_eq!(new.failure_contexts.load(Ordering::Relaxed),16);
 for i in 0..origins.len(){for j in 0..i{assert_ne!(format!("{:?}",origins[i]),format!("{:?}",origins[j]));}}
 println!("PASS memory_pairs={} conflict_bucket_masks=256 origins=10 observer_before_quarantine=1 errors_claims_callcounts_unchanged=1 budgets=16; HOST_PRIMITIVES_MODELED_NO_NATIVE",n);
}
'''
write(F/'diagnostic.rs',prefix+runtime+mem+main)
manifest=dict(scope=b['scope'],status='EXECUTABLE_SOURCE_PREPARATION_ONLY_NOT_COMPILED',fixture_sources={x.name:pin(x) for x in F.iterdir() if x.is_file()},actual_extracted_bodies=['original/instrumented Memory::syscall','original Ledger::conflicts/tag','new diagnostic_conflict/context constructor/budget','original/instrumented Runtime::fail','actual Request type/decode/getters','unchanged actual Remote::syscall_request error/quarantine branch'],models='stdArc/Mutex/Vec, ownedAtomic backing/address mapping, Runtime.application.fail_service and Remote entry/admit receiver only. No kernel layout/module/runtime proof.',tests='8195 original/instrumented memory error/claim/quarantine pairs,256bucketmasks/halfopen/snoopignore,10originvariants,16ticket saturating budgets,100EAGAINthenEBUSY preservation,existing callcounts/serials/claims/unmodifiederrors. No trace attribution or semantic repair claimed.')
write(P/'FIXTURE-SOURCE-BINDINGS.json',json.dumps(manifest,indent=2)+'\n');print(json.dumps(dict(fixture=pin(F/'diagnostic.rs'),files=len(manifest['fixture_sources']))))
