from pathlib import Path
import hashlib,json,difflib
P=Path(__file__).parent
s=(P/'actual-control-receipt.rs').read_text()
original=s
def once(a,b):
 global s
 assert s.count(a)==1,(a[:90],s.count(a))
 s=s.replace(a,b,1)
once('pub old_owner:*mut c_void, pub writing:bool, pub cleared:bool,','pub old_owner:*mut c_void, pub zap_owner:*mut c_void, pub writing:bool, pub cleared:bool,')
once('assert_eq!((**pointer).vm_private_data,(**pointer).old_owner);','assert_eq!((**pointer).vm_private_data,(**pointer).zap_owner); assert_eq!((**pointer).vm_mm,m.mm);')
once('vm_private_data:raw,old_owner:raw,vm_ops:', 'vm_private_data:raw,old_owner:raw,zap_owner:raw,vm_ops:')
helper='''
// Fixture-only phase oracle: inheritance zaps use the initial owner. After
// authentic adoption, bind the revoke adapter to the installed child owner.
// Never change the initial-owner history or a production VMA owner pointer.
fn bind_actual_inherited_zap_owners(j:&mut Joined){
 let mirror=j.mm.child_registration.mapping.lock().as_ref().unwrap().clone();
 let mm=mirror.mm.0.as_ptr();assert_eq!(mm,&mut *j.mm.child_mm as *mut _);
 assert_eq!((mirror.start,mirror.end),(0,0x8000));
 unsafe{mckernel_inherited_mmap_write_lock(mm)};
 for (index,v) in j.mm.children.iter_mut().enumerate(){
  let raw=&mut **v as *mut bindings::vm_area_struct;
  {let owner=unsafe{vma_owner(raw)}.unwrap();
   assert!(ptr::eq(&*owner.registration,&*j.mm.child_registration));
   assert!(ptr::eq(&*owner.mirror,&*mirror));}
  assert_eq!(v.vm_mm,mm);assert_eq!(v.vm_ops,&VM_OPERATIONS.0 as *const _);
  assert_eq!((v.__bindgen_anon_1.__bindgen_anon_1.vm_start,v.__bindgen_anon_1.__bindgen_anon_1.vm_end),((index as u64)*0x4000,((index+1)as u64)*0x4000));
  assert_ne!(v.vm_private_data,v.old_owner);assert!(!v.writing);
  v.zap_owner=v.vm_private_data;
 }
 unsafe{mckernel_inherited_mmap_write_unlock(mm)};
}
'''
once('fn resume_receipt(j:',helper+'\nfn resume_receipt(j:')
needle='let mut j=RetainedJoined::new();assert_eq!(j.adopt(),0);j.first_return();'
# Existing older tests are retained unchanged. Only these three new tests opt in.
for name in ['actual_control_receipt_real_mm_proof_writes_exact_frame_without_ret','actual_control_receipt_mm_validation_error_writes_nothing_retains_owners','actual_control_receipt_copy_error_quarantines_journal_and_original_claim']:
 marker='#[test]fn '+name+'(){\n '+needle
 once(marker,marker+'bind_actual_inherited_zap_owners(&mut j);')
target=P/'actual-control-receipt-corrected.rs'
assert not target.exists();target.write_text(s)
(P/'receipt-fixture-correction.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='actual-control-receipt.rs',tofile=target.name)))
runner=(P/'run_receipt_check.py').read_text().replace("E=R/'check-1'","E=R/'check-2'").replace("R/'actual-control-receipt.rs'","R/'actual-control-receipt-corrected.rs'").replace("R/'fixture-inputs.json'","R/'fixture-correction-inputs.json'")
assert not(P/'run_receipt_check_correction.py').exists();(P/'run_receipt_check_correction.py').write_text(runner)
rows=json.loads((P/'fixture-inputs.json').read_text())['inputs']
for f in [Path(__file__),target,P/'run_receipt_check_correction.py',P/'receipt-fixture-correction.patch',P/'check-1/compile.status.json',P/'check-1/scenario-1.status.json',P/'check-1/scenario-1.stderr']:
 rows.append({'path':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'bytes':f.stat().st_size})
(P/'fixture-correction-inputs.json').write_text(json.dumps({'inputs':rows,'new_tests':3,'isolation':'one exact test per process','production_unchanged':True,'original_failure_preserved':True,'old59_executed':False},indent=2)+'\n')
proposal={'status':'READY_NOT_RUN','source_patch_sha256':hashlib.sha256((P/'control-receipt.patch').read_bytes()).hexdigest(),'source_unchanged':True,'fixture_delta':str(P/'receipt-fixture-correction.patch'),'profile':'CPU6/1job/1GiB/30CPU/global28/outer35+2/32MiB/nofile256','runner':str(P/'run_receipt_check_correction.py'),'outputs':str(P/'check-2'),'inputs':str(P/'fixture-correction-inputs.json'),'original_failure':str(P/'check-1/scenario-1.status.json'),'adapter_audit':'locked/writing/mm/range invariants retained; initial old_owner remains immutable; only three new receipt tests snapshot authenticated installed child owner before revoke; old59 untouched/filtered','argv':['/usr/bin/timeout','--signal=TERM','--kill-after=2','35','/usr/bin/taskset','-c','6','/usr/bin/prlimit','--as=1073741824:1073741824','--cpu=30:30','--fsize=33554432:33554432','--nofile=256:256','--core=0:0','/home/holden/anaconda3/bin/python3','-I','-B',str(P/'run_receipt_check_correction.py')]}
(P/'receipt-fixture-correction-proposal.json').write_text(json.dumps(proposal,indent=2)+'\n')
print('new_tests=3 source_unchanged=true proposal_sha256='+hashlib.sha256((P/'receipt-fixture-correction-proposal.json').read_bytes()).hexdigest())
