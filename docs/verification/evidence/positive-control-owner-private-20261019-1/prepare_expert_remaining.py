from pathlib import Path
import sys,hashlib,json,difflib
sys.path.insert(0,'/home/holden/mckernel');from scripts.tests.test_shutdown_cpu_reclaim import balanced_item
P=Path(__file__).parent;A=P/'second-failed-inputs';assert not A.exists();A.mkdir();archive=[]
for n in ['actual-control-park.rs','fixture-link.rs','fixture-ingress.rs','fixture-inputs.json','run_control_check_correction.py','check-correction-proposal.json','actual-body-bindings-correction.json','fixture-correction-delta.json']:
 f=P/n;data=f.read_bytes();(A/n).write_bytes(data);archive.append({'consumed_path':str(f),'retained_path':str(A/n),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
(A/'archive-map.json').write_text(json.dumps(archive,indent=2)+'\n')
s=(P/'actual-control-park.rs').read_text();old=s
helper='''
// Test-only retain-on-unwind guard: a failed assertion still fails libtest, but
// never treats the static guest arena as a safely destructible owned mapping.
// This does not catch errors or authorize any production cleanup/release.
struct RetainedJoined { value:Option<Joined> }
impl RetainedJoined { fn new()->Self{Self{value:Some(Joined::new())}} fn retain(self){} }
impl core::ops::Deref for RetainedJoined { type Target=Joined;fn deref(&self)->&Joined{self.value.as_ref().unwrap()} }
impl core::ops::DerefMut for RetainedJoined { fn deref_mut(&mut self)->&mut Joined{self.value.as_mut().unwrap()} }
impl Drop for RetainedJoined { fn drop(&mut self){if let Some(j)=self.value.take(){j.retain();}} }
fn concurrent_link_request()->crate::Request {
 let args=original_request(true).arguments();let mut bytes=[0u8;128];
 bytes[8..12].copy_from_slice(&4i32.to_le_bytes());bytes[24..28].copy_from_slice(&0i32.to_le_bytes());
 bytes[32..36].copy_from_slice(&101i32.to_le_bytes());bytes[48..52].copy_from_slice(&101i32.to_le_bytes());
 // Distinct authentic fixture Linux worker and matching Request requester.
 bytes[52..56].copy_from_slice(&202i32.to_le_bytes());bytes[56..64].copy_from_slice(&1u64.to_le_bytes());
 bytes[64..72].copy_from_slice(&56u64.to_le_bytes());for(n,a)in args.iter().enumerate(){bytes[72+n*8..80+n*8].copy_from_slice(&a.to_le_bytes());}
 // first_return() proved zero response claims, then parkedcontrol owns ONLY
 // 0x1c00000. Admit below must itself prove 0x1b00000 is available again.
 bytes[120..128].copy_from_slice(&0x1b00000u64.to_le_bytes());crate::Request::decode(&bytes,1).unwrap()
}
'''
needle='fn control_request(change:Option<(usize,u64)>)->crate::Request {';assert s.count(needle)==1;s=s.replace(needle,helper+'\n'+needle)
tests=['actual_control_fresh_response_parked_once_and_blocks_link_return_removal','actual_control_wrong_identity_epoch_phase_and_overflow_have_no_transfer','actual_control_restore_conflict_retains_exact_claim_and_response_after_close','actual_control_ordinary_first_return_passes_without_pin_or_payload_effect']
for name in tests:
 a=balanced_item(s,'fn '+name+'(');assert a.count('let mut j=Joined::new();')==1;b=a.replace('let mut j=Joined::new();','let mut j=RetainedJoined::new();');s=s.replace(a,b,1)
needle='let(lw,ls)=crate::smp_application::delivered(&j.remote,j.parent,&j.memory,original_request(true));'
assert s.count(needle)==1;s=s.replace(needle,'assert_eq!(crate::smp_memory::storage::claims(&j.memory),(1,1));let(lw,ls)=crate::smp_application::delivered_concurrent_link(&j.remote,j.parent,&j.memory,concurrent_link_request());')
helper='''pub(crate) fn delivered_concurrent_link(remote:&Remote,parent:Token,memory:&Arc<crate::smp_memory::storage::Memory>,request:Request)->(u64,u64){
 let mut slots=remote.slots.lock();let p=slots.iter_mut().flatten().find(|p|p.key()==parent).unwrap();
 assert_eq!(p.syscalls.open_worker(201),Err(EBUSY));let w=p.syscalls.open_worker(202).unwrap();
 p.syscalls.admit(request,|r|memory.syscall(r)).unwrap();let(s,_)=p.syscalls.reserve(w).unwrap().unwrap();p.syscalls.copied(w,s,true).unwrap();(w,s)
}
'''
needle='pub(crate) fn delivered(remote:';assert s.count(needle)==1;s=s.replace(needle,helper+needle)
f=P/'actual-control-park-expert.rs';f.write_text(s)
# Exact same chain/profile, same four uncompleted tests. Prior failures remain
# in the SAME family; this is only the expert-prescribed ingress correction.
f=P/'run_control_check_expert.py';r=(P/'run_control_check_correction.py').read_text();r=r.replace("E=R/'check-2'","E=R/'check-3'").replace("R/'actual-control-park.rs'","R/'actual-control-park-expert.rs'").replace("R/'fixture-inputs.json'","R/'fixture-inputs-expert.json'");f.write_text(r)
inputs=json.loads((P/'fixture-inputs.json').read_text());inputs['inputs']=[r for r in inputs['inputs']if Path(r['path']).name not in ['actual-control-park.rs','run_control_check_correction.py']]
for f in [P/'actual-control-park-expert.rs',P/'run_control_check_expert.py',Path(__file__)]:inputs['inputs'].append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
inputs['expert_diagnosis']={'path':'/home/holden/mckernel-work/host-preparation/provider-ownership-review-20261019-1/POSITIVE-CONTROL-CONCURRENT-DELIVERY-FIXTURE-EXPERT-DIAGNOSIS.json','sha256':'700be595546d8be09590dfb0b2d5d14a92cf3aff626918b3dfc03e815bb4cfef'}
(P/'fixture-inputs-expert.json').write_text(json.dumps(inputs,indent=2)+'\n')
proposal=json.loads((P/'check-correction-proposal.json').read_text());proposal['status']='EXPERT_PRESCRIBED_REMAINING_SAME_FAILURE_FAMILY_READY_NOT_RUN';proposal['argv'][-1]=str(P/'run_control_check_expert.py');proposal['capture_stdout']=str(P/'whole-check-expert.stdout');proposal['capture_stderr']=str(P/'whole-check-expert.stderr');proposal['output']=str(P/'check-3');proposal['inputs']=[]
for f in [P/'positive-control-park.patch',P/'source-pins.json',P/'fixture-inputs-expert.json',P/'actual-control-park-expert.rs',P/'run_control_check_expert.py',A/'archive-map.json']:
 proposal['inputs'].append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
proposal['prior_failures']=[str(P/'whole-check.status.json'),str(P/'whole-check-correction.status.json')];proposal['expert_diagnosis']=inputs['expert_diagnosis'];(P/'check-expert-proposal.json').write_text(json.dumps(proposal,indent=2)+'\n')
(P/'fixture-expert-delta.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='failed-fixture.rs',tofile='expert-remaining-fixture.rs')))
(P/'new-four-delivery-setup-review.json').write_text(json.dumps({'production_source_unchanged':True,'same_failure_family':True,'reviewed_tests':tests,'concurrent_link':{'held_control_worker':201,'held_control_response':'0x1c00000','link_worker':202,'link_wire_requester':202,'link_response':'0x1b00000','requires_actual_claims_before_admit':[1,1],'uses_actual_mailbox_admit_reserve_copied':True,'assert_duplicate201_refused':True},'other_tests':'Each iteration owns freshJoined/realREADY; no additional concurrentdelivery; original_request and delivered helpers unchanged','unwind_guard':'Test-only unconditional ownership retention, no catch/suppress/acceptance or productionDrop change','prior_archive':str(A/'archive-map.json')},indent=2)+'\n')
print('expert_proposal_sha256',hashlib.sha256((P/'check-expert-proposal.json').read_bytes()).hexdigest(),'delta_bytes',(P/'fixture-expert-delta.patch').stat().st_size)
