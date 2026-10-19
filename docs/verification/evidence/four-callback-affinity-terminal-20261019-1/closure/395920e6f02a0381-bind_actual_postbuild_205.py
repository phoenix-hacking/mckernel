"""Case-specific actual205 data join; no subprocess, copies, tools, root or acceptance."""
from pathlib import Path
import hashlib,json,os,stat,sys
B=Path(__file__).resolve().parent;A=B.parent
def snapshot(ref):
 data=Path(ref['path']).read_bytes();assert len(data)==ref['bytes'] and hashlib.sha256(data).hexdigest()==ref['sha256'];return json.loads(data)
def observe(path):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  before=os.fstat(fd);assert stat.S_ISREG(before.st_mode) and before.st_nlink==1
  h=hashlib.sha256();size=0
  while True:
   block=os.read(fd,65536)
   if not block:break
   size+=len(block);assert size<=before.st_size;h.update(block)
  after=os.fstat(fd);stable=lambda v:tuple(getattr(v,k) for k in ('st_dev','st_ino','st_mode','st_nlink','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns'));assert stable(before)==stable(after)==stable(os.lstat(path)) and size==before.st_size
  return dict(path=str(path),device=after.st_dev,inode=after.st_ino,uid=after.st_uid,gid=after.st_gid,mode=oct(stat.S_IMODE(after.st_mode)),size=size,mtime_ns=after.st_mtime_ns,ctime_ns=after.st_ctime_ns,nlink=after.st_nlink,sha256=h.hexdigest())
 finally:os.close(fd)
def main():
 assert len(sys.argv)==4,'actual binding path sha256 fresh-output-directory'
 raw=Path(sys.argv[1]).read_bytes();assert hashlib.sha256(raw).hexdigest()==sys.argv[2];actual=json.loads(raw);out=Path(sys.argv[3]);assert not out.exists()
 inputs=json.loads((B/'INPUTS.json').read_bytes());contract=snapshot(inputs['capture_contract']);paths=snapshot(inputs['role_paths']);request=snapshot(inputs['request']);assert actual['request']==inputs['request'] and actual['source_identity']==request['source_identity']
 expected_paths={'owner_receipt':Path(request['owner_evidence_root'])/'owner-receipt.json','driver_receipt':Path(request['evidence_root'])/'receipt.json','process_checks':Path(request['evidence_root'])/'release-tid-production-checks.json','affinity_checks':Path(request['evidence_root'])/'clone-affinity-production-checks.json','primary_copy_receipt':B/'postbuild-readonly-1/retained-artifacts/retention-result.json','postjoin_readback':A/'heavy-proposal-1/image-guard-postjoin-readback.json'}
 for key,path in expected_paths.items():assert actual[key]['path']==str(path),'actual205 receipt namespace '+key
 owner=snapshot(actual['owner_receipt']);guard=snapshot(actual['guard_result']);post=snapshot(actual['postjoin_readback']);driver=snapshot(actual['driver_receipt'])
 for key in ('candidate_sha','candidate_identity_scope','ihk_sha','source_derivative_sha256','materialization_sha256'):
  assert owner[key]==driver[key]==request[key],'actual205 receipt source authority '+key
 assert owner['owner_evidence_root']==request['owner_evidence_root'] and owner['driver_evidence_root']==request['evidence_root'] and owner['attempt_root']==request['attempt_root']
 assert driver['evidence_root']=='/work/evidence' and driver['output_root']=='/work/output' and driver['phase']=='complete'
 for key in ('source_manifest_sha256','toolchain_manifest_sha256','gitlink_manifest_sha256'):assert driver[key]==request[key]
 assert owner['exit_code']==0 and guard['owner_status']=='PASS' and post['status']=='PASS_ORDINARY_GUARD_POSTJOIN_READBACK_ONLY'

 assert owner['status']=='PASS' and owner['retired'] is True and owner['terminal_container_retained'] is True
 assert guard['retired'] is True and guard['retained_for_separate_cleanup'] is True and guard['owner_receipt_sha256']==actual['owner_receipt']['sha256']
 assert post['guard_direct_joined'] is True and post['root27_4_reacquired_after_join'] is True and post['owner_receipt_sha256']==actual['owner_receipt']['sha256'] and post['guard_result_sha256']==actual['guard_result']['sha256']
 assert owner['container_id']==guard['container_id']==post['container_id']==actual['container_id'] and driver['status']=='PASS'
 assert actual['old_compiled_artifacts_adopted'] is False
 c=snapshot(actual['process_checks']);aff=snapshot(actual['affinity_checks']);assert c['status']=='PASS' and c['actual_C_ABI_assertions']==110
 assert aff['status']=='PASS' and aff['layout_cells']==27 and aff['actual_syscall_C_assertions_selected']==10 and aff['actual_syscall_C_assertions_fallback']==8 and aff['old_compiled_inputs_adopted'] is False
 assert set(aff['symbols'])==set(contract['new_affinity_facts']['symbols']) and all(r['exit_code']==0 for r in c['checks']+aff['checks'])
 assert set(actual['primary_pairs'])=={'cpu.c.o','process.c.o','mckernel_rust.o','mckernel.img'}
 copies=snapshot(actual['primary_copy_receipt']);assert copies['status']=='PASS_EXACT_FOUR_ARTIFACT_RETENTION_ONLY' and set(copies['artifacts'])=={'cpu','process','rust','image'}
 copyroles={'cpu.c.o':'cpu','process.c.o':'process','mckernel_rust.o':'rust','mckernel.img':'image'}
 authorities=[];reused=[]
 for role in paths['roles']:
  original=observe(role['original_path']);destination=Path(role['retained_path'])
  if role['action']=='reuse':
   pair=actual['primary_pairs'][role['role']];retained=observe(destination);copied=copies['artifacts'][copyroles[role['role']]]
   converted=dict(original);converted['dev']=converted.pop('device');converted['bytes']=converted.pop('size');converted['mode']=int(converted['mode'],8);converted.pop('nlink')
   assert copied['source']==converted and copied['retained_path']==str(destination) and copied['retained_dev']==retained['device'] and copied['retained_inode']==retained['inode'] and copied['bytes']==retained['size'] and copied['sha256']==retained['sha256']
   assert pair['original']==original and pair['retained']==retained and original['size']==retained['size'] and original['sha256']==retained['sha256'] and all(original[k]==retained[k] for k in ('uid','gid','mode'));reused.append(pair)
  else:assert not os.path.lexists(destination)
  authority=dict(kind=role['role'],action=role['action'],original=original,retained=str(destination))
  if role['action']=='reuse':authority['retained_authority']=retained
  authorities.append(authority)
 assert len(authorities)==len(paths['roles']) and len(reused)==4
 assert sum(r['original']['size'] for r in authorities)<=paths['finite_retention_planning_maximum_bytes']
 out.mkdir(mode=0o700)
 result={'status':'BOUND_ACTUAL205_INPUTS_ONLY_NOT_EXECUTION_OR_FACTS_ACCEPTANCE','request':inputs['request'],'container_id':actual['container_id'],'authority_role_count':len(authorities),'new_copy_count':sum(r['action']=='copy' for r in authorities),'existing_reuse_count':len(reused),'metadata_row_count':2*len(authorities),'pending':['Independently reviewed actual15 tool/copy execution release','New205 source/optimizer/section-aware facts adapter and exact descriptor resolution','Independent actualfacts and finite retention execution/release','Matching strictN3 initialCPU native proof'],'compiler_or_root_or_copy_or_tool_runs':0}
 for name,value in [('actual-retention-authorities.json',authorities),('existing-primary-pairs.json',reused),('actual-input-data-join.json',result)]:
  with (out/name).open('x') as f:json.dump(value,f,sort_keys=True,indent=2);f.write('\n')
 print(json.dumps({'roles':len(authorities),'copies':result['new_copy_count'],'reuse':len(reused),'metadata_rows':2*len(authorities),'acceptance':False}))
if __name__=='__main__':main()
