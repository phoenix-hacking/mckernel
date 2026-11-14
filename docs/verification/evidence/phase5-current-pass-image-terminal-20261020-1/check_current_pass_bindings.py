"""Ordinary actual current PASS callbacks only; no root/cleanup/Docker/process job."""
import copy,hashlib,json,types
from pathlib import Path
B=Path(__file__).resolve().parent
pins=json.loads((B/'SOURCE-PINS.json').read_bytes())['sources']
def load(name):
 p=B/name;raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==pins[name]['sha256']
 m=types.ModuleType('_current_pass_check_'+p.stem);m.__file__=str(p);exec(compile(raw,str(p),'exec'),m.__dict__);return m
m=load('cleanup_pass_image.py');o=load('observe_current_pass_image_retirement.py')
for n in ('readback_observer.py','read_original_five_metadata.py','export_raw_five.py','postjoin_readback.py','check_actual_fresh_preflight.py'):load(n)
case=json.loads(o.stable_bytes(o.FAILURE_CASE,o.FAILURE_CASE_SHA,4<<20));physical=json.loads(o.stable_bytes(o.RETIREMENT,o.RETIREMENT_SHA))
request=m.parse(m.read_bounded(m.REQUEST));owner=json.loads(o.stable_bytes(Path(physical['owner_receipt']['path']),physical['owner_receipt']['sha256']))
guard=json.loads(o.stable_bytes(Path(physical['guard_result']['path']),physical['guard_result']['sha256']))
inspection=json.loads(o.stable_bytes(Path(physical['fresh_terminal_inspect']['path']),physical['fresh_terminal_inspect']['sha256']))
argv,mounts=m.image_layout(request)
actual=sorted((v['Destination'],v['Source'],v['Type'],v['RW']) for v in inspection['Mounts'] if v['Type']=='bind')
assert argv==inspection['Config']['Cmd']==inspection['Args'] and mounts==actual
m.image_receipt_binding(owner,guard,case['target'],inspection,physical['owner_receipt']['sha256'])
selected={v['path']:dict(path=v['path'],sha256=v['sha256']) for v in m.SOURCE_REFS.values()}
m.typed_source_binding(request,dict(candidate_root=dict(inode=request['source_identity']['inode'])),selected)
def refuses(fn,prefix):
 try:fn()
 except m.Refusal as error:
  assert str(error).startswith(prefix),(prefix,str(error));return
 raise AssertionError('expected specific refusal '+prefix)
changed=copy.deepcopy(owner);changed['status']='FAIL'
refuses(lambda:m.image_receipt_binding(changed,guard,case['target'],inspection,physical['owner_receipt']['sha256']),'image-positive-owner-retirement')
changed=copy.deepcopy(guard);changed['retired']=False
refuses(lambda:m.image_receipt_binding(owner,changed,case['target'],inspection,physical['owner_receipt']['sha256']),'image-positive-owner-and-guard-retirement')
changed=copy.deepcopy(selected);artifact=m.SOURCE_REFS['artifacts:mcexec']['path'];changed[artifact]['sha256']='0'*64
refuses(lambda:m.typed_source_binding(request,dict(candidate_root=dict(inode=request['source_identity']['inode'])),changed),'current-selected-source:artifacts:mcexec')
for path in (m.ATTEMPT,m.SHARED):
 row=m.observe_identity(path);record=m.parse(m.read_bounded(path));m.image_record_binding(path,row,record,request,case['target'],o.BOOT)
 changed=copy.deepcopy(row);changed['inode']+=1
 refuses(lambda:m.image_record_binding(path,changed,record,request,case['target'],o.BOOT),'image-exclusion-owner-binding')
m.CANDIDATE=Path(request['source_root']);m.PROTECTED=[m.observe_identity(Path(artifact))]
obs=dict(inventories={str(root):m.metadata_inventory(root) for root in (m.OUTPUT,m.EVIDENCE)},candidate_root=m.observe_identity(m.CANDIDATE),backup_root=m.observe_identity(Path(request['backup_root'])))
m.RELEASE=dict(observation=obs);m.protected_files();m.PROTECTED[0]['inode']+=1
refuses(m.protected_files,'selected-artifact-or-receipt-drift:')
print(json.dumps(dict(status='PASS_CURRENT_ACTUAL_PASS_CALLBACKS_NO_EFFECTS',checks=['seven_actual_module_imports','actual_optin_layout','actual_PASS_receipt_guard_and_FAIL_refusals','actual27_typed_source_refs_and_artifact_SHA_refusal','two_actual_record_inode_refusals','actual_protected_inventory_and_changed_artifact_inode_refusal'],source_ref_count=len(m.SOURCE_REFS),artifact_primary_count=len(case['artifact_names']),finite_role_count=case['finite_role_count'],finite_unique_path_count=case['finite_unique_path_count'],cleanup_executed=False,root_or_docker_executed=False),sort_keys=True))
