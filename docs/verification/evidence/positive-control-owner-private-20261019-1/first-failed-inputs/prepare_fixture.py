from pathlib import Path
import sys,hashlib,json,re
sys.path.insert(0,'/home/holden/mckernel')
from scripts.tests.test_shutdown_cpu_reclaim import balanced_item
P=Path(__file__).parent;Q=P.parent;S=P/'source/host-kernel/native-rust'
f=Q/'actual-parent-pin.rs';s=f.read_text();orig=s
# Existing real Memory/Mailbox/IHK READY/consumer scaffold; old tests filtered.
def item(t,n):return balanced_item(t,n)
def replace(a,b):
 global s
 assert s.count(a)==1,(a[:90],s.count(a));s=s.replace(a,b,1)
a=(S/'smp_application.rs').read_text();r=(S/'os_runtime.rs').read_text();service=(S/'smp_service.rs').read_text();abi=(S/'abi/application.rs').read_text();provider=(S/'ihk_smp_x86_64.rs').read_text()
# Entire actual ABI, not fixture-invented declarations.
replace(item(s,'mod application_abi{'),'mod application_abi {\n'+abi+'\n}')
replace(item(s,'struct ChildFork {'),item(a,'struct ChildFork {'))
replace('owner: child_owner, seal, retained_remote: None, retained_parent: None, ack: None, link: None, held_lease: None,','owner: child_owner, seal, retained_remote: None, retained_parent: None, ack: None, link: None, control: None, held_lease: None,')
replace(item(s,'fn fork_publication_frozen('),item(a,'fn fork_publication_frozen('))
replace(item(s,'fn authorize_fork_return('),item(a,'fn authorize_fork_return('))
replace(item(s,'fn fork_progress_in_slots('),item(a,'fn fork_progress_in_slots('))
replace(item(s,'pub(crate) fn release_fork_ack('),item(a,'pub(crate) fn release_fork_ack('))
replace('struct ForkAckRecord {',item(a,'impl ForkAckRecord {')+'\nstruct ForkAckRecord {')
oldlink='/home/holden/mckernel-work/scratch/native-fork-carrier-link-races-20261017-1/test-correction/sources/smp_fork_link.rs'
replace(oldlink,str(S/'smp_fork_link.rs'))
replace('pub(crate) use fork_link::PreparedLinkTicket;','pub(crate) use fork_link::{PreparedLinkTicket,PreparedControlTicket};')
ing=(Q/'fixture-ingress.rs').read_text();needle='retained_parent: None, ack: None,';assert ing.count(needle)==1;ing=ing.replace(needle,'retained_parent: None, ack: Some(ForkAckRecord::new(scope.epoch)), control: None,')
(P/'fixture-ingress.rs').write_text(ing);replace(str(Q/'fixture-ingress.rs'),str(P/'fixture-ingress.rs'))
# Actual synchronous service methods and actual registered callback.
methods=item(service,'pub(in super::super) unsafe fn prepare_fork_control(')+'\n'+item(service,'unsafe extern "C" fn park_fork_control_scope(')
replace('    pub(in super::super) unsafe fn prepare_fork_link(',methods+'\n    pub(in super::super) unsafe fn prepare_fork_link(')
replace('unsafe extern "C" fn application_prepare_fork_link(',item(provider,'unsafe extern "C" fn application_prepare_fork_control(')+'\nunsafe extern "C" fn application_prepare_fork_link(')
replace('    prepare_fork_link: Option<super::application_abi::ForkPrepareLinkV1>,\n}','    prepare_fork_link: Option<super::application_abi::ForkPrepareLinkV1>,\n    prepare_fork_control: Option<super::application_abi::ForkPrepareControlV1>,\n}')
replace('prepare_fork_link:Some(application_prepare_fork_link)}}','prepare_fork_link:Some(application_prepare_fork_link),prepare_fork_control:Some(application_prepare_fork_control)}}')
replace(item(s,'struct ApplicationCallbacks {'),item(r,'struct ApplicationCallbacks {'))
replace('prepare_fork_control:Some(application_prepare_fork_control)}}','prepare_fork_control:Some(application_prepare_fork_control),fork_progress_payload:None,prepare_fork_ack:None,fork_publication_verify:None,release_fork_ack:None}}')
mailbox=(S/'smp_application_syscall.rs').read_text()
replace('    pub(crate) fn has_fork_link_response(',item(mailbox,'pub(crate) fn has_private_fork_response(')+'\n    pub(crate) fn has_fork_link_response(')
# Old fixture predates final-ACK bookkeeping; add zero initialization only.
replace('    host_revoked: bool,\n    guest_released: bool,\n    attempted: bool,','    host_revoked: bool,\n    guest_released: bool,\n    final_published: bool, consumer_accepted: bool, payload_completed: bool, backend_released: bool,\n    attempted: bool,')
replace('host_revoked: false, guest_released: false, attempted: false, receipt_index:', 'host_revoked: false, guest_released: false, final_published: false, consumer_accepted: false, payload_completed: false, backend_released: false, attempted: false, receipt_index:')
replace('    fn begin_link_attempt(&mut self) -> Result {',item(r,'fn acquire_control(')+'\n    fn begin_link_attempt(&mut self) -> Result {')
replace('    fn begin_link_attempt(&mut self) -> Result {',item(r,'fn restore_control(')+'\n    fn begin_link_attempt(&mut self) -> Result {')
replace('unsafe extern "C" fn resolve_fork_link_scope(',item(r,'unsafe extern "C" fn resolve_fork_control_scope(')+'\n'+item(r,'pub(crate) unsafe extern "C" fn prepare_fork_control_application(')+'\nunsafe extern "C" fn resolve_fork_link_scope(')
# Diagnostic helpers may corrupt metadata to exercise no-effect refusals; none
# supplies a response, capsule, phase proof or trusted receipt to actual code.
helpers='''
pub(crate) fn control_state(remote:&Remote)->(usize,bool,bool,ForkPhase,u64) {
 let slots=remote.slots.lock(); let p=slots[0].as_ref().unwrap();let c=slots[1].as_ref().unwrap();let f=c.fork.as_ref().unwrap();
 (p.fork_prepared_parent_refs,f.control.is_some(),f.control.as_ref().is_some_and(|c|c.quarantined),f.reservation.state.phase(),f.link.as_ref().unwrap().last_sequence)
}
pub(crate) fn parent_count(remote:&Remote,n:usize){remote.slots.lock()[0].as_mut().unwrap().fork_prepared_parent_refs=n;}
pub(crate) fn check_control_owned(remote:&Arc<Remote>,parent:Token,child:Token,w:u64,s:u64,request:&Request) {
 let slots=remote.slots.lock();let f=slots[1].as_ref().unwrap().fork.as_ref().unwrap();let c=f.control.as_ref().unwrap();
 assert_eq!(c.descriptor.worker,w);assert_eq!(c.descriptor.delivery,s);assert_eq!(&c.request,request);
 assert_eq!(c.descriptor.response,request.response());assert_eq!(c._response.request(),request);
 assert_eq!(c._parent.parent,parent);assert_eq!(c._parent.identity.child,child.wire());assert!(Arc::ptr_eq(&c._parent.remote,remote));
 assert!(fork_publication_frozen(&slots,parent,request.cpu()));
 assert_eq!(authorize_fork_return(&slots,parent,w,s,request.cpu() as i64,-95),Err(EBUSY));
}
pub(crate) fn control_no_release(remote:&Remote,parent:Token,child:Token){
 let key=remote.slots.lock()[1].as_ref().unwrap().fork.as_ref().unwrap().reservation.identity;
 let before=control_state(remote);assert_eq!(remote.begin_fork_progress(child,key,crate::application_abi::FORK_HOST_REVOKED_V1),Err(EBUSY));
 assert_eq!(remote.begin_fork_progress(child,key,crate::application_abi::FORK_GUEST_DESTROYED_V1),Err(EBUSY));
 assert_eq!(remote.release_fork_ack(child,key,1),Err(EBUSY));assert_eq!(control_state(remote),before);
 assert!(!remote.slots.lock()[0].as_ref().unwrap().release_ready());let _=parent;
}
'''
# Child module private members are not accessible to parent test helpers: those
# checks live in the actual child module test-only extension instead.
child_helpers='''
#[cfg(test)]
pub(super) fn check_control_owner(remote:&Arc<Remote>,parent:Token,child:Token,w:u64,s:u64,request:&Request) {
 let slots=remote.slots.lock();let f=slots[1].as_ref().unwrap().fork.as_ref().unwrap();let c=f.control.as_ref().unwrap();
 assert_eq!(c.descriptor.worker,w);assert_eq!(c.descriptor.delivery,s);assert_eq!(&c.request,request);
 assert_eq!(c.descriptor.response,request.response());assert_eq!(c._response.request(),request);
 assert_eq!(c._parent.parent,parent);assert_eq!(c._parent.identity.child,child.wire());assert!(Arc::ptr_eq(&c._parent.remote,remote));
 assert!(super::fork_publication_frozen(&slots,parent,request.cpu()));
 assert_eq!(super::authorize_fork_return(&slots,parent,w,s,request.cpu() as i64,-95),Err(EBUSY));
}
#[cfg(test)] pub(super) fn is_quarantined(remote:&Remote)->bool { remote.slots.lock()[1].as_ref().unwrap().fork.as_ref().unwrap().control.as_ref().is_some_and(|c|c.quarantined) }
'''
link=(S/'smp_fork_link.rs').read_text();(P/'fixture-link.rs').write_text(link+child_helpers);replace(str(S/'smp_fork_link.rs'),str(P/'fixture-link.rs'))
helpers=helpers.replace('f.control.as_ref().is_some_and(|c|c.quarantined)','false')
start=helpers.index('pub(crate) fn check_control_owned');end=helpers.index('pub(crate) fn control_no_release')
helpers=helpers[:start]+'''pub(crate) fn check_control_owned(remote:&Arc<Remote>,parent:Token,child:Token,w:u64,s:u64,request:&Request){fork_link::check_control_owner(remote,parent,child,w,s,request)}
'''+helpers[end:]
replace('pub(crate) fn transport_failure(remote:',helpers+'\npub(crate) fn transport_failure(remote:')
provider_helpers='''
pub(crate) fn control_pending_state()->(u32,bool,bool,u64) {
 let raw=OS_OBJECTS[0].load(Ordering::Acquire);let table=unsafe{&*raw}.forks.lock();let e=table.entries.iter().flatten().next().unwrap();(e.phase,e.attempted,e.host_revoked,e.epoch)
}
pub(crate) fn pending_owner_counts()->(usize,usize,usize){let raw=OS_OBJECTS[0].load(Ordering::Acquire);let table=unsafe{&*raw}.forks.lock();let e=table.entries.iter().flatten().next().unwrap();(Arc::strong_count(&e.owner),Arc::strong_count(e.capsule.as_ref().unwrap()),Arc::strong_count(e.payload.as_ref().unwrap()))}
pub(crate) unsafe fn park_with_restore_conflict(remote:&Arc<Remote>,parent:Token,w:u64,s:u64,replace_epoch:bool)->i32 {
 let mut ticket=remote.begin_fork_control(parent,w,s,0,-95).unwrap().unwrap();let d=ticket.descriptor();
 let raw=OS_OBJECTS[0].load(Ordering::Acquire);let object=unsafe{&*raw};
 let child_context={let table=object.forks.lock();table.entries.iter().flatten().next().unwrap().child_context};
 let claim=ForkProviderClaim::acquire_control(object,d.identity,child_context,d.epoch).unwrap();
 {let payload=claim.payload.as_ref().unwrap().context.load(Ordering::Acquire);assert_eq!(unsafe{ticket.park(&*payload.cast::<crate::smp_memory::storage::ForkPayload>())},Ok(()));}
 {let mut table=object.forks.lock();let e=table.entries.iter_mut().flatten().next().unwrap();if replace_epoch{e.epoch+=1;}else{e.phase=FORK_PROVIDER_PENDING;}}
 let status=claim.restore_control().map_or_else(|e|e.to_errno(),|()|0);ticket.quarantine_if_parked();status
}
pub(crate) fn alter_control_pending(phase:Option<u32>,epoch:Option<u64>){let raw=OS_OBJECTS[0].load(Ordering::Acquire);let mut table=unsafe{&*raw}.forks.lock();let e=table.entries.iter_mut().flatten().next().unwrap();if let Some(p)=phase{e.phase=p;}if let Some(v)=epoch{e.epoch=v;}}
'''
replace('pub(crate) fn current_key()->',provider_helpers+'\npub(crate) fn current_key()->')
# New selector2 host delivery producer built from the actual 128-byte decoded
# Request, no new carrier/receipt. This is a host-side ingress fixture only.
tests='''
fn control_request(change:Option<(usize,u64)>)->crate::Request {
 let request=original_request(true);let mut args=request.arguments();args[0]=2;if let Some((i,v))=change{args[i]=v;}
 let mut bytes=[0u8;128];bytes[8..12].copy_from_slice(&4i32.to_le_bytes());bytes[24..28].copy_from_slice(&0i32.to_le_bytes());bytes[32..36].copy_from_slice(&101i32.to_le_bytes());bytes[48..52].copy_from_slice(&101i32.to_le_bytes());bytes[52..56].copy_from_slice(&201i32.to_le_bytes());bytes[56..64].copy_from_slice(&1u64.to_le_bytes());bytes[64..72].copy_from_slice(&56u64.to_le_bytes());for(n,a)in args.iter().enumerate(){bytes[72+n*8..80+n*8].copy_from_slice(&a.to_le_bytes());}bytes[120..128].copy_from_slice(&0x1c00000u64.to_le_bytes());crate::Request::decode(&bytes,1).unwrap()
}
fn control(j:&mut Joined,r:crate::Request)->(i32,u64,u64){let(w,s)=crate::smp_application::delivered(&j.remote,j.parent,&j.memory,r);let(p,_)=j.connections.as_mut().unwrap().raw();(unsafe{crate::provider_runtime::prepare_fork_control_application(p,w,s,0,-95)},w,s)}
#[test]fn actual_control_fresh_response_parked_once_and_blocks_link_return_removal(){
 let mut j=Joined::new();assert_eq!(j.adopt(),0);j.first_return();let before=crate::provider_runtime::control_pending_state();let r=control_request(None);
 let(rc,w,s)=control(&mut j,r.clone());assert_eq!(rc,1);assert_eq!(crate::provider_runtime::control_pending_state(),before);
 let state=crate::smp_application::control_state(&j.remote);assert_eq!(state.0,2);assert!(state.1);assert_eq!(state.3,crate::ForkPhase::FirstReturnPublished);assert_eq!(state.4,1);
 crate::smp_application::check_control_owned(&j.remote,j.parent,j.child,w,s,&r);crate::smp_application::control_no_release(&j.remote,j.parent,j.child);
 let(p,_)=j.connections.as_mut().unwrap().raw();assert!(unsafe{crate::provider_runtime::prepare_fork_control_application(p,w,s,0,-95)}<0);assert_eq!(crate::smp_application::control_state(&j.remote),state);
 assert_eq!(j.remote.publish_syscall(j.parent,0,|_|panic!("parked response must not publish"),||Ok(())),Ok(false));
 let(lw,ls)=crate::smp_application::delivered(&j.remote,j.parent,&j.memory,original_request(true));assert!(unsafe{crate::provider_runtime::prepare_fork_link_application(p,lw,ls,0,0)}<0);assert_eq!(crate::smp_application::control_state(&j.remote),state);
 j.retain();
}
#[test]fn actual_control_wrong_identity_epoch_phase_and_overflow_have_no_transfer(){
 // Independent real owner/claim instances; each failure retains unchanged real response.
 for case in 0..4 {
  let mut j=Joined::new();assert_eq!(j.adopt(),0);j.first_return();
  let old=crate::provider_runtime::control_pending_state();let r=control_request(if case==0{Some((3,0x29000))}else{None});
  if case==1{crate::provider_runtime::alter_control_pending(None,Some(old.3+1));}
  if case==2{crate::provider_runtime::alter_control_pending(Some(2),None);}
  if case==3{crate::smp_application::parent_count(&j.remote,usize::MAX);}
  let before=crate::smp_application::control_state(&j.remote);let pending=crate::provider_runtime::control_pending_state();
  let(rc,_,_)=control(&mut j,r);assert!(rc<0,"case {case}");assert_eq!(crate::smp_application::control_state(&j.remote),before);assert_eq!(crate::provider_runtime::control_pending_state(),pending);j.retain();
 }
}
#[test]fn actual_control_restore_conflict_retains_exact_claim_and_response_after_close(){
 for replace_epoch in [false,true] {
  let mut j=Joined::new();assert_eq!(j.adopt(),0);j.first_return();let r=control_request(None);
  let(w,s)=crate::smp_application::delivered(&j.remote,j.parent,&j.memory,r.clone());
  let old=crate::provider_runtime::control_pending_state();let counts=crate::provider_runtime::pending_owner_counts();let memory=crate::smp_memory::storage::claims(&j.memory);
  assert_eq!(unsafe{crate::provider_runtime::park_with_restore_conflict(&j.remote,j.parent,w,s,replace_epoch)},-5);
  let after=crate::provider_runtime::control_pending_state();assert_eq!(after.0,if replace_epoch{4}else{2});assert_eq!(after.3,old.3+u64::from(replace_epoch));assert_eq!((after.1,after.2),(old.1,old.2));
  assert_eq!(crate::provider_runtime::pending_owner_counts(),(counts.0+1,counts.1+1,counts.2+1));
  assert_eq!(crate::smp_memory::storage::claims(&j.memory),memory);let state=crate::smp_application::control_state(&j.remote);assert_eq!(state.0,2);assert!(state.1);
  crate::smp_application::check_control_owned(&j.remote,j.parent,j.child,w,s,&r);
  crate::smp_application::close_worker_actual(&j.remote,j.parent,w);assert_eq!(crate::smp_memory::storage::claims(&j.memory),memory);let after=crate::smp_application::control_state(&j.remote);assert_eq!(after.0,2);assert!(after.1);j.retain();
 }
}
#[test]fn actual_control_ordinary_first_return_passes_without_pin_or_payload_effect(){
 let mut j=Joined::new();assert_eq!(j.adopt(),0);let before=crate::provider_runtime::control_pending_state();let state=crate::smp_application::control_state(&j.remote);
 let(p,_)=j.connections.as_mut().unwrap().raw();assert_eq!(unsafe{crate::provider_runtime::prepare_fork_control_application(p,j.worker,j.serial,0,102)},0);assert_eq!(crate::provider_runtime::control_pending_state(),before);assert_eq!(crate::smp_application::control_state(&j.remote),state);j.first_return();j.retain();
}
'''
replace('#[test]fn actual_durable_parent_pin_survives_positive_first_ret_failed_link_and_parent_close(){',tests+'\n#[test]fn actual_durable_parent_pin_survives_positive_first_ret_failed_link_and_parent_close(){')
(P/'actual-control-park.rs').write_text(s)
rows=[]
for f in [f,Q/'fixture-ingress.rs',P/'actual-control-park.rs',P/'fixture-ingress.rs',P/'fixture-link.rs',Path(__file__),*S.rglob('*.rs')]:rows.append(dict(path=str(f),sha256=hashlib.sha256(f.read_bytes()).hexdigest(),bytes=f.stat().st_size))
(P/'fixture-inputs.json').write_text(json.dumps(dict(inputs=rows,tests=4,old_tests_filtered=51,scope='Actual mailbox Memory/IHK READY/body park; fixture registration/consumer/OS adapters; no fullcrate/preRETURN ioctl/native/MMrevoke/receipt/ACK authority',actual_methods=['acquire_control','resolve_fork_control_scope','prepare_fork_control_application','Application::prepare_fork_control','park_fork_control_scope','application_prepare_fork_control','Remote::begin_fork_control','PreparedControlTicket::park'],production_hook_static_only=True),indent=2)+'\n')
print('inputs',len(rows),'new_tests',4)
