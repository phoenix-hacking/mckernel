from pathlib import Path
import sys,json,hashlib,re
sys.path.insert(0,'/home/holden/mckernel');from scripts.tests.test_shutdown_cpu_reclaim import balanced_item
P=Path(__file__).parent;OLD=P.parent/'positive-control-owner-1';S=P/'source/host-kernel/native-rust';s=(OLD/'actual-control-park-isolated.rs').read_text()
def item(t,n):return balanced_item(t,n)
def once(a,b):
 global s
 assert s.count(a)==1,(a[:90],s.count(a));s=s.replace(a,b,1)
abi=(S/'abi/application.rs').read_text();runtime=(S/'os_runtime.rs').read_text();service=(S/'smp_service.rs').read_text();provider=(S/'ihk_smp_x86_64.rs').read_text()
once(item(s,'mod application_abi {'),'mod application_abi {\n'+abi+'\n}')
once('pub(crate) use fork_link::{PreparedLinkTicket,PreparedControlTicket};','pub(crate) use fork_link::{PreparedLinkTicket,PreparedControlTicket,PreparedControlReceiptTicket,ControlReceiptOutcome};')
# Actual whole new link/control writer module, plus read-only test observations.
link=(S/'smp_fork_link.rs').read_text();oldlink=(OLD/'fixture-link.rs').read_text();oldactual=(OLD/'source/host-kernel/native-rust/smp_fork_link.rs').read_text();assert oldlink.startswith(oldactual)
view='''
#[cfg(test)] pub(super) fn receipt_observation(remote:&Remote)->(bool,bool,bool,bool,bool,Option<[u8;128]>,super::super::application_abi::ForkControlV1){
 let slots=remote.slots.lock();let f=slots[1].as_ref().unwrap().fork.as_ref().unwrap();let c=f.control.as_ref().unwrap();
 (c.receipt.frozen,c.receipt.proof.is_some(),c.receipt.journal.is_some(),c.receipt.written,c.receipt.uncertain,c.receipt.journal,c.descriptor)
}
'''
(P/'fixture-link.rs').write_text(link+oldlink[len(oldactual):]+view);once(str(OLD/'fixture-link.rs'),str(P/'fixture-link.rs'))
once('pub(in super::super) unsafe fn prepare_fork_control(',item(service,'pub(in super::super) unsafe fn prepare_fork_control_receipt(')+'\n'+item(service,'unsafe extern "C" fn resume_fork_control_scope(')+'\n    pub(in super::super) unsafe fn prepare_fork_control(')
once('unsafe extern "C" fn application_prepare_fork_control(',item(provider,'unsafe extern "C" fn application_prepare_fork_control_receipt(')+'\nunsafe extern "C" fn application_prepare_fork_control(')
once(item(s,'struct ApplicationCallbacks {'),item(runtime,'struct ApplicationCallbacks {'))
once('prepare_fork_control:Some(application_prepare_fork_control),','prepare_fork_control:Some(application_prepare_fork_control),prepare_fork_control_receipt:Some(application_prepare_fork_control_receipt),')
once('    fn begin_link_attempt(&mut self) -> Result {',item(runtime,'fn retain_control_uncertain(')+'\n    fn begin_link_attempt(&mut self) -> Result {')
once(item(s,'pub(crate) unsafe extern "C" fn prepare_fork_control_application('),item(runtime,'pub(crate) unsafe extern "C" fn prepare_fork_control_application('))
once('unsafe extern "C" fn resolve_fork_control_scope(',item(runtime,'unsafe extern "C" fn resolve_fork_control_receipt_scope(')+'\n'+item(runtime,'pub(crate) unsafe extern "C" fn prepare_fork_control_receipt_application(')+'\nunsafe extern "C" fn resolve_fork_control_scope(')
# Read-only current-owner view, actual real verifier and actual source writer.
once('pub(crate) fn transport_failure(remote:', '''pub(crate) fn receipt_observation(remote:&Remote)->(bool,bool,bool,bool,bool,Option<[u8;128]>,crate::application_abi::ForkControlV1){fork_link::receipt_observation(remote)}
pub(crate) fn transport_failure(remote:''')
# Explicit ledger corruption fault, not a replacement writer or a fake verifier.
once('pub(crate) fn claims(memory:', '''pub(crate) fn invalidate_payload_ledger_for_copy_error(memory:&Memory){let mut l=memory.ledger.lock();let mut n=0;for slot in l.fork_payloads.iter_mut(){if slot.take().is_some(){n+=1;}}assert_eq!(n,1);}
pub(crate) fn claims(memory:''')
# Freeze a byte contract independently of the writer's serialization loop.
contract={'status':'SOURCE_ONLY_NEW_CONTROL_RECEIPT_NO_GUEST_CONSUMER','length':128,'magic':'MCFKR001','u64_fields':{'8':'epoch','16':'fresh_worker','24':'fresh_delivery','32':'fresh_response','48':'generation','56':'parent','64':'original_worker','72':'original_delivery','80':'child','88':'child_mm','96':'root','104':'start','112':'length','120':'nonce'},'u32_fields':{'40':'slot','44':'child_pid'},'no_result_or_legacy_phase_field':True,'consumer_pending':True}
(P/'RECEIPT-BYTE-CONTRACT.json').write_text(json.dumps(contract,indent=2)+'\n')
tests='''
fn resume_receipt(j:&mut Joined,w:u64,s:u64)->i32{let(p,_)=j.connections.as_mut().unwrap().raw();unsafe{crate::provider_runtime::prepare_fork_control_receipt_application(p,w,s,0,-95)}}
fn carrier_bytes()->[u8;128]{let physical=original_request(false).arguments()[4];let offset=(physical-0x1000000)as usize;assert!(offset+128<=unsafe{guest_arena_bytes()});let mut b=[0u8;128];unsafe{b.copy_from_slice(core::slice::from_raw_parts(guest_arena().add(offset),128));}b}
fn independent_receipt_bytes(d:crate::application_abi::ForkControlV1)->[u8;128]{
 let mut b=[0u8;128];b[..8].copy_from_slice(b"MCFKR001");
 b[8..16].copy_from_slice(&d.epoch.to_le_bytes());b[16..24].copy_from_slice(&d.worker.to_le_bytes());b[24..32].copy_from_slice(&d.delivery.to_le_bytes());b[32..40].copy_from_slice(&d.response.to_le_bytes());
 let k=d.identity;b[40..44].copy_from_slice(&k.slot.to_le_bytes());b[44..48].copy_from_slice(&k.child_pid.to_le_bytes());
 b[48..56].copy_from_slice(&k.generation.to_le_bytes());b[56..64].copy_from_slice(&k.parent.to_le_bytes());b[64..72].copy_from_slice(&k.worker.to_le_bytes());b[72..80].copy_from_slice(&k.delivery.to_le_bytes());b[80..88].copy_from_slice(&k.child.to_le_bytes());b[88..96].copy_from_slice(&k.child_mm.to_le_bytes());b[96..104].copy_from_slice(&k.root.to_le_bytes());b[104..112].copy_from_slice(&k.start.to_le_bytes());b[112..120].copy_from_slice(&k.length.to_le_bytes());b[120..128].copy_from_slice(&k.nonce.to_le_bytes());b
}
fn actual_zaps()->usize{MODEL.with(|m|m.borrow().events.iter().filter(|e|**e=="zap").count())}
#[test]fn actual_control_receipt_real_mm_proof_writes_exact_frame_without_ret(){
 let mut j=RetainedJoined::new();assert_eq!(j.adopt(),0);j.first_return();let r=control_request(None);let(rc,w,s)=control(&mut j,r.clone());assert_eq!(rc,1);
 let before=crate::provider_runtime::control_pending_state();let state=crate::smp_application::control_state(&j.remote);let zaps=actual_zaps();let claims=crate::smp_memory::storage::claims(&j.memory);
 assert_eq!(resume_receipt(&mut j,w,s),1);assert!(actual_zaps()>zaps);
 let(frozen,proof,journal,written,uncertain,bytes,d)=crate::smp_application::receipt_observation(&j.remote);assert!(frozen&&proof&&journal&&written&&!uncertain);assert_eq!(bytes,Some(independent_receipt_bytes(d)));assert_eq!(carrier_bytes(),independent_receipt_bytes(d));
 assert_eq!(crate::provider_runtime::control_pending_state(),before);assert_eq!(crate::smp_memory::storage::claims(&j.memory),claims);assert_eq!(crate::smp_application::control_state(&j.remote).0,state.0);assert_eq!(crate::smp_application::phase(&j.remote),crate::ForkPhase::FirstReturnPublished);
 crate::smp_application::check_control_owned(&j.remote,j.parent,j.child,w,s,&r);assert_eq!(j.remote.publish_syscall(j.parent,0,|_|panic!("receipt must not publish RET"),||Ok(())),Ok(false));
 let zaps=actual_zaps();assert_eq!(resume_receipt(&mut j,w,s),1);assert_eq!(actual_zaps(),zaps);assert_eq!(carrier_bytes(),independent_receipt_bytes(d));j.retain();
}
#[test]fn actual_control_receipt_mm_validation_error_writes_nothing_retains_owners(){
 let mut j=RetainedJoined::new();assert_eq!(j.adopt(),0);j.first_return();let(rc,w,s)=control(&mut j,control_request(None));assert_eq!(rc,1);let before=carrier_bytes();let pending=crate::provider_runtime::control_pending_state();let counts=crate::provider_runtime::pending_owner_counts();let claims=crate::smp_memory::storage::claims(&j.memory);let zaps=actual_zaps();
 // Actual Mirror pass0 rejects matching VMA without VM_PFNMAP before anyzap.
 j.mm.children[1].__bindgen_anon_2.__vm_flags&=!bindings::VM_PFNMAP;
 assert!(resume_receipt(&mut j,w,s)<0);assert_eq!(actual_zaps(),zaps);assert_eq!(carrier_bytes(),before);
 let(frozen,proof,journal,written,uncertain,_,_)=crate::smp_application::receipt_observation(&j.remote);assert!(frozen&&!proof&&!journal&&!written&&!uncertain);
 assert_eq!(crate::provider_runtime::control_pending_state(),pending);assert_eq!(crate::provider_runtime::pending_owner_counts(),counts);assert_eq!(crate::smp_memory::storage::claims(&j.memory),claims);let state=crate::smp_application::control_state(&j.remote);assert_eq!(state.0,2);assert!(state.1&&state.2);j.retain();
}
#[test]fn actual_control_receipt_copy_error_quarantines_journal_and_original_claim(){
 let mut j=RetainedJoined::new();assert_eq!(j.adopt(),0);j.first_return();let(rc,w,s)=control(&mut j,control_request(None));assert_eq!(rc,1);let before=carrier_bytes();let counts=crate::provider_runtime::pending_owner_counts();let zaps=actual_zaps();
 // Existing MM-unlock hook runs after the real verifier's MM guard drops.
 // Corrupt actual ledger, so real ForkPayload.copy_to_guest returnsEIO. This
 // proves conservative uncertainty retention, not an observed partialcopy.
 let memory=j.memory.clone();crate::MM_UNLOCK_HOOK.with(|h|*h.borrow_mut()=Some(Box::new(move||crate::smp_memory::storage::invalidate_payload_ledger_for_copy_error(&memory))));
 assert_eq!(resume_receipt(&mut j,w,s),-5);assert!(actual_zaps()>zaps);assert_eq!(carrier_bytes(),before);
 let(frozen,proof,journal,written,uncertain,bytes,d)=crate::smp_application::receipt_observation(&j.remote);assert!(frozen&&proof&&journal&&!written&&uncertain);assert_eq!(bytes,Some(independent_receipt_bytes(d)));
 assert_eq!(crate::provider_runtime::control_pending_state().0,2);assert_eq!(crate::provider_runtime::pending_owner_counts(),(counts.0+1,counts.1+1,counts.2+1));let state=crate::smp_application::control_state(&j.remote);assert_eq!(state.0,2);assert!(state.1&&state.2);
 assert!(resume_receipt(&mut j,w,s)<0);assert_eq!(carrier_bytes(),before);assert_eq!(crate::smp_application::receipt_observation(&j.remote).5,bytes);j.retain();
}
'''
once('fn control_request(change:',tests+'\nfn control_request(change:')
(P/'actual-control-receipt.rs').write_text(s)
# Prove exact current bodies in the compiled projection; no injected verifier.
rows=[]
for name,needle in [('os_runtime.rs','fn retain_control_uncertain('),('os_runtime.rs','unsafe extern "C" fn resolve_fork_control_receipt_scope('),('os_runtime.rs','pub(crate) unsafe extern "C" fn prepare_fork_control_receipt_application('),('smp_service.rs','pub(in super::super) unsafe fn prepare_fork_control_receipt('),('smp_service.rs','unsafe extern "C" fn resume_fork_control_scope('),('ihk_smp_x86_64.rs','unsafe extern "C" fn application_prepare_fork_control_receipt(')]:
 actual=item((S/name).read_text(),needle);assert actual==item(s,needle);rows.append({'source':name,'item':needle,'sha256':hashlib.sha256(actual.encode()).hexdigest(),'exact':True})
assert(P/'fixture-link.rs').read_text().startswith(link);rows.append({'source':'smp_fork_link.rs','whole_source_prefix':True,'sha256':hashlib.sha256(link.encode()).hexdigest(),'exact':True})
(P/'actual-body-bindings.json').write_text(json.dumps({'status':'SOURCE_PROJECTION_NOT_RUN','rows':rows,'real_consumer_verifier':'Existing actual fork_verify_host -> Registration::revoke_fork -> Mirror::revoke_fork_aliases compiled in retainedscaffold','fullcrate_preRETURN_registration':'PENDING_SOURCE_ONLY','partialcopy_observed':False},indent=2)+'\n')
pins=[]
for f in [OLD/'actual-control-park-isolated.rs',OLD/'fixture-link.rs',P/'fixture-link.rs',P/'actual-control-receipt.rs',P/'actual-body-bindings.json',Path(__file__),*S.rglob('*.rs')]:pins.append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
(P/'fixture-inputs.json').write_text(json.dumps({'inputs':pins,'new_tests':3,'isolation':'ONE --exact process per once-onlyguestfixture','old59_tests_executed':False,'native':False,'new_guest_consumer':False},indent=2)+'\n');print('new_tests',3,'actual_bindings',len(rows),'inputs',len(pins))
