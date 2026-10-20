from pathlib import Path
import json,hashlib,sys
sys.path.insert(0,'/home/holden/mckernel')
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item
P=Path(__file__).parent;OLD=P.parent/'control-receipt-1';S=P/'source/host-kernel/native-rust'
s=(OLD/'actual-control-receipt-corrected.rs').read_text()
def once(a,b):
 global s
 assert s.count(a)==1,(a[:100],s.count(a));s=s.replace(a,b,1)
for module,name in [('application_syscall','application_syscall.rs'),('smp_application_syscall','smp_application_syscall.rs')]:
 old=balanced_item(s,'mod '+module+'{') if 'mod '+module+'{'in s else balanced_item(s,'mod '+module+' {')
 once(old,'mod '+module+'{\n'+(S/name).read_text()+'\n}')
oldlink=(OLD/'fixture-link.rs').read_text();oldsource=(OLD/'source/host-kernel/native-rust/smp_fork_link.rs').read_text();assert oldlink.startswith(oldsource)
link=(S/'smp_fork_link.rs').read_text()
view='''
#[cfg(test)] pub(super) fn transport_observation(remote:&Remote)->(bool,bool,bool,bool){
 let mut slots=remote.slots.lock();let c=slots[1].as_mut().unwrap().fork.as_mut().unwrap().control.as_mut().unwrap();
 (c.receipt.queued,c.receipt.published,c.receipt.uncertain,c._response.response().is_ok())
}
'''
(P/'fixture-link.rs').write_text(link+oldlink[len(oldsource):]+view)
once(str(OLD/'fixture-link.rs'),str(P/'fixture-link.rs'))
app=(S/'smp_application.rs').read_text()
once(balanced_item(s,'pub(crate) fn publish_syscall('),balanced_item(app,'pub(crate) fn publish_syscall('))
once('impl Remote{fn transport_health','impl Remote{\n'+balanced_item(app,'pub(crate) fn return_syscall(')+'\n'+balanced_item(app,'pub(crate) fn notify_syscalls(')+'\nfn transport_health')
condvar='''
// Test-only Linux Condvar adapter. It releases/reacquires the SAME tracked
// slots mutex and never publishes or invents a control response.
struct FixtureCondvar{inner:std::sync::Condvar,waits:AtomicUsize}
impl FixtureCondvar{
 fn new()->Self{Self{inner:std::sync::Condvar::new(),waits:AtomicUsize::new(0)}}
 fn notify_all(&self){self.inner.notify_all();}
 fn wait<T>(&self,g:&mut FixtureGuard<'_,T>){
  let inner=g.inner.take().unwrap();LOCK_DEPTH.with(|d|{assert!(d.get()>0);d.set(d.get()-1)});
  self.waits.fetch_add(1,Ordering::Release);
  let inner=self.inner.wait(inner).unwrap();
  LOCK_DEPTH.with(|d|d.set(d.get()+1));g.inner=Some(inner);
 }
}
'''
once('mod smp_application {use super::*;',condvar+'\nmod smp_application {use super::*;')
once('releases: Mutex<Mailbox<Memory>> }','releases: Mutex<Mailbox<Memory>>, changed:FixtureCondvar }')
once('releases:Mutex::new(Mailbox::new().unwrap())}','releases:Mutex::new(Mailbox::new().unwrap()),changed:FixtureCondvar::new()}')
view='''
pub(crate) fn delivered_unrelated(remote:&Remote,parent:Token,memory:&Arc<crate::smp_memory::storage::Memory>,request:Request)->(u64,u64){assert_eq!(request.requester(),202);assert_eq!(request.response(),0x1d00000);assert_eq!(request.number(),39);let mut slots=remote.slots.lock();let p=slots.iter_mut().flatten().find(|p|p.key()==parent).unwrap();let w=p.syscalls.open_worker(202).unwrap();p.syscalls.admit(request,|r|memory.syscall(r)).unwrap();let(s,_)=p.syscalls.reserve(w).unwrap().unwrap();p.syscalls.copied(w,s,true).unwrap();(w,s)}
pub(crate) fn transport_observation(remote:&Remote)->(bool,bool,bool,bool){fork_link::transport_observation(remote)}
pub(crate) fn transport_waits(remote:&Remote)->usize{remote.changed.waits.load(Ordering::Acquire)}
pub(crate) fn queue_control_transfer_actual(remote:&Remote,parent:Token,w:u64,s:u64,destination:u64,length:u64)->Result{
 let mut slots=remote.slots.lock();fork_link::queue_control_receipt_in_slots(remote,&mut slots,parent,w,s,0,destination,length).map(|_|())
}
pub(crate) fn queue_control_actual(remote:&Remote,parent:Token,w:u64,s:u64)->Result{
 let mut slots=remote.slots.lock();fork_link::queue_control_receipt_in_slots(remote,&mut slots,parent,w,s,0,0,0).map(|_|())
}
'''
once('pub(crate) fn return_actual(remote:',view+'\npub(crate) fn return_actual(remote:')
once('fn resume_receipt(j:',(P/'delivery_tests.rs.in').read_text()+'\nfn resume_receipt(j:')
target=P/'actual-control-delivery.rs';assert not target.exists();target.write_text(s)
rows=[]
for name,needle in [('smp_application.rs','pub(crate) fn return_syscall('),('smp_application.rs','pub(crate) fn publish_syscall('),('smp_application.rs','pub(crate) fn notify_syscalls(')]:
 actual=balanced_item((S/name).read_text(),needle);assert actual==balanced_item(s,needle);rows.append({'source':name,'item':needle,'sha256':hashlib.sha256(actual.encode()).hexdigest(),'exact':True})
for module,name in [('application_syscall','application_syscall.rs'),('smp_application_syscall','smp_application_syscall.rs')]:
 assert (S/name).read_text()in balanced_item(s,'mod '+module+'{');rows.append({'source':name,'whole_module':True,'sha256':hashlib.sha256((S/name).read_bytes()).hexdigest(),'exact':True})
assert (P/'fixture-link.rs').read_text().startswith(link);rows.append({'source':'smp_fork_link.rs','whole_module_prefix':True,'sha256':hashlib.sha256(link.encode()).hexdigest(),'exact':True})
# Existing receipt prepare/resolver, module verification and real Mirror bodies
# remain byte-exact to the accepted predecessor; new transport never mints them.
for needle in ['unsafe extern "C" fn fork_verify_host(', 'fn revoke_fork_aliases(', 'pub(crate) unsafe extern "C" fn prepare_fork_control_receipt_application(']:
 original=balanced_item((OLD/'actual-control-receipt-corrected.rs').read_text(),needle);assert original==balanced_item(s,needle);rows.append({'predecessor':str(OLD/'actual-control-receipt-corrected.rs'),'item':needle,'sha256':hashlib.sha256(original.encode()).hexdigest(),'unchanged':True})
(P/'actual-body-bindings.json').write_text(json.dumps({'status':'SOURCE_PROJECTED_NOT_RUN','rows':rows,'native':False,'new_guest_consumer':False,'linux_mm_and_service_adapters':True,'real_condvar_adapter':True,'full_parent_close_executed':False,'CAS_after_scalar_write_error_injection':False,'bookkeeping_failure_injection':False},indent=2)+'\n')
inputs=[]
for f in [Path(__file__),target,P/'fixture-link.rs',P/'delivery_tests.rs.in',P/'actual-body-bindings.json',OLD/'actual-control-receipt-corrected.rs',OLD/'check-1/scenario-1.status.json',OLD/'check-2/result.json',*S.rglob('*.rs')]:
 inputs.append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
(P/'fixture-inputs.json').write_text(json.dumps({'inputs':inputs,'new_scenarios':4,'isolation':'one exact test process per Joined arena','old_scenarios_not_replayed':True},indent=2)+'\n')
print('new_scenarios',4,'body_bindings',len(rows),'inputs',len(inputs))
