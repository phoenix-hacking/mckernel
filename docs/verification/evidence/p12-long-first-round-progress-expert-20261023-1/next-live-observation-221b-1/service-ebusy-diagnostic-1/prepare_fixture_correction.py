# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import shutil
P=Path(__file__).resolve().parent
save=P/'initial-fixture-preserved';save.mkdir(exist_ok=True)
for name in ['fixture','FIXTURE-SOURCE-BINDINGS.json']:
 q=P/name;dest=save/name
 if not dest.exists():
  if q.is_dir():shutil.copytree(q,dest)
  else:shutil.copy2(q,dest)
s=(P/'prepare_fixture.py').read_text()
s=s.replace("F=P/'fixture'", "F=P/'fixture-correction-1'")
s=s.replace("const REQUEST_BYTES:usize=72;const RESPONSE_BYTES:usize=40;", "const REQUEST_BYTES:usize=72;const RESPONSE_BYTES:usize=40;pub(crate) const REQUEST_MESSAGE:i32=4;")
s=s.replace("#[derive(Clone,Copy)] struct Owner;\nimpl Owner {fn slot(self)->u32{0}fn generation(self)->u64{1}}", "#[derive(Clone,Copy)] struct Owner{slot:u32,generation:u64}\nimpl Owner {fn slot(self)->u32{self.slot}fn generation(self)->u64{self.generation}}\nconst OWNER:Owner=Owner{slot:0,generation:1};\nfn is_diag(s:&str)->bool{s.starts_with(\"IHK-\")&&!s.starts_with(\"IHK-SMP:\")}\nfn check_lines(v:&[String]){for s in v.iter().filter(|s|is_diag(s)){assert!(s.len()+96<=255,\"line bytes+prefix={} {}\",s.len()+96,s);}}\n#[path=\"actual_wire.rs\"] mod actual_wire;\n#[path=\"original_wire.rs\"] mod original_wire;\nuse actual_wire as sysfs_request;\n#[path=\"actual_rpc.rs\"] mod actual_rpc;\n#[path=\"original_rpc.rs\"] mod original_rpc;")
s=s.replace("Self{owner:Owner,application", "Self{owner:OWNER,application")
s=s.replace("owner:Owner,ledger:KernelMutex(StdMutex::new(l))", "owner:OWNER,ledger:KernelMutex(StdMutex::new(l))")
s=s.replace("+origin+'\\n'+ticket+", "+origin+'\\n'+structure(service,'impl FailureOrigin {')+'\\n'+ticket+")
s=s.replace("+oldfail+'\\n'+newfail+'\\n}\\n'", "+oldfail+'\\n'+function(service,'fn failure_context(')+'\\n'+newfail+'\\n}\\n'")
s=s.replace("use crate::application_syscall::Request as SyscallRequest;", "use crate::application_syscall::Request as SyscallRequest;\nuse crate::actual_wire as wire;")
s=s.replace("+oldcall+'\\n'+newcall+'\\n}\\n'", "+oldcall+'\\n'+newcall+'\\n'+function(m,'fn diagnostic_conflict_failure(')+'\\n'+function(m,'fn diagnostic_completion_failure(')+'\\n}\\n'")
s=s.replace('!s.starts_with("IHK-SMP: service failure context")', '!is_diag(s)')
s=s.replace('assert!(events[0].contains("origin=syscall_response_claim"));assert!(events[0].contains("pid: 641")&&events[0].contains("requester: 643")&&events[0].contains("response: 4096"));assert!(events[1]=="admission_quarantine");assert_eq!(events.len(),2)', 'assert!(events[0].contains("at=syscall_claim"));assert!(events.iter().any(|s|s.contains("p=641 rq=643")));assert!(events.iter().any(|s|s.contains("a=1000")));assert_eq!(events.last().unwrap(),"admission_quarantine");assert!(events[..events.len()-1].iter().all(|s|is_diag(s)));check_lines(&events)')
s=s.replace('events[0].contains("conflict: None")', 'events.iter().any(|s|s.contains("k=none"))')
s=s.replace('assert_eq!(take_events().len(),16);', 'assert_eq!(take_events().iter().filter(|s|s.starts_with("IHK-E")).count(),16);')
s=s.replace('assert!(b[0].contains("origin="));if i==0{assert_eq!(b[1],"service_quarantine");}', 'assert!(b[0].contains("at="));check_lines(&b);if i==0{let q=b.iter().position(|s|s=="service_quarantine").unwrap();assert!(b[..q].iter().all(|s|is_diag(s)));}')
s=s.replace('!b.iter().any(|s|s.starts_with("IHK-SMP: service failure context"))', '!b.iter().any(|s|is_diag(s))')
# Extra tests share the exact extracted log bodies; scalars are synthetic width
# vectors, not runtime packet identities. The original/new complete/RPC modules
# themselves are whole-file copies of the selected source.
augment=r'''
for name,key in [('wire','abi/sysfs_request.rs'),('rpc','sysfs_rpc.rs')]:
 write(F/('original_'+name+'.rs'),orig[key]);write(F/('actual_'+name+'.rs'),new[key])
assert 'pub(crate) const REQUEST_MESSAGE: i32 = 4;' in request
assert function(orig['smp_application.rs'],'fn backend_ready(')==function(new['smp_application.rs'],'fn backend_ready(')
assert function(orig['smp_application.rs'],'fn request_cleanup(')==function(new['smp_application.rs'],'fn request_cleanup(')
assert function(orig['sysfs_rpc.rs'],'pub(crate) fn accept(')==function(new['sysfs_rpc.rs'],'pub(crate) fn accept(')
# Supplemental actual memory helper log width/branch coverage.
extra_memory=r"""
pub(super) fn width_test(){
 take_events();let os=u32::MAX;let gen=u64::MAX;let span=Span{physical:u64::MAX-1,end:u64::MAX};
 let conflict=FailureConflict{kind:ConflictKind::ExecPayload,slot:usize::MAX,member:Some(usize::MAX),serial:Some(u64::MAX),span};
 for end in [None,Some(u64::MAX)] {log_syscall_failure(os,gen,16,errno(i32::MIN),SyscallFailureContext{cpu:i32::MIN,pid:i32::MIN,requester:i32::MIN,target:i32::MIN,number:u64::MAX,response:u64::MAX,response_end:end,conflict:Some(conflict)});}
 let mut m=memory(make_ledger(0,true,0),0,0,None);Arc::get_mut(&mut m).unwrap().owner=Owner{slot:os,generation:gen};
 for at in ["zero_control","zero_header","zero_chunk","zeroed_head","procfs_overlap"] {m.diagnostic_conflict_failure(at,span,Some(conflict),Some(Tagged{span,serial:u64::MAX}),true,Some((i32::MIN,i32::MIN)));}
 for kind in [wire::Kind::Create,wire::Kind::Mkdir,wire::Kind::Symlink,wire::Kind::Lookup,wire::Kind::Unlink]{m.diagnostic_completion_failure(kind,Tagged{span,serial:u64::MAX},i32::MIN,i32::MIN);}
 check_lines(&take_events());
}
"""
mem=mem[:-2]+extra_memory+'}\n'
application_helper=function(new['smp_application.rs'],'fn diagnostic_application_failure(')
remote_old=function(orig['sysfs_remote.rs'],'pub(crate) fn reply(').replace('fn reply(','fn original_reply(',1)
remote_new=function(new['sysfs_remote.rs'],'pub(crate) fn reply(')
extra=r"""
mod remote_fixture {
use super::*;
const ENODEV:Error=Error(-19);
struct KernelMutex<T>(StdMutex<T>);impl<T> KernelMutex<T>{fn lock(&self)->std::sync::MutexGuard<'_,T>{self.0.lock().unwrap()}}
struct State{peer_stopped:bool,exchange:actual_rpc::Exchange}
struct Data{owner:Owner}
struct Changed(AtomicUsize);impl Changed{fn notify_all(&self){self.0.fetch_add(1,Ordering::Relaxed);}}
struct Remote{state:KernelMutex<State>,data:Data,changed:Changed,failure_contexts:AtomicU64}
impl Remote {
"""+remote_old+'\n'+remote_new+r"""
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
"""+application_helper+r"""
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
"""
main=main.replace('fn main(){let n=memory::test();','fn main(){let n=memory::test();memory::width_test();let (completions,rpc)=protocol_test();assert_eq!(completions,90);assert_eq!(rpc,12);assert_eq!(remote_fixture::test(),24);application_fixture::test();')
main=main.replace(' for i in 0..origins.len()', ' let mut wide=Runtime::new();wide.owner=Owner{slot:u32::MAX,generation:u64::MAX};for origin in [FailureOrigin::Packet{channel:usize::MAX,guest_cpu:u32::MAX,port:i32::MIN,message:i32::MIN},FailureOrigin::PublishApplications]{wide.failure_context(errno(i32::MIN),origin);}check_lines(&take_events());\n for i in 0..origins.len()')
main=main.replace('budgets=16; HOST_PRIMITIVES_MODELED_NO_NATIVE','budgets=16 metadata_pairs=90 rpc_pairs=12 remote_pairs=24 line_prefix_budget=96; HOST_PRIMITIVES_MODELED_NO_NATIVE')
main=extra+main
'''
s=s.replace("write(F/'diagnostic.rs',prefix+runtime+mem+main)",augment+"\nwrite(F/'diagnostic.rs',prefix+runtime+mem+main)")
s=s.replace("P/'FIXTURE-SOURCE-BINDINGS.json'", "P/'FIXTURE-CORRECTION-1-SOURCE-BINDINGS.json'")
exec(compile(s,str(P/'prepare_fixture_corrected_generated.py'),'exec'))
