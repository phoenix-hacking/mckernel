"""Proposed ordinary no-effects actual callback check. Not a cleanup release."""
import copy,hashlib,json,types
from pathlib import Path
B=Path(__file__).resolve().parent
pins=json.loads((B/'FAILURE-CHAIN-PROPOSAL.json').read_text())['source_pins']
def load(name):
 p=B/name;raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==pins[name]['sha256']
 m=types.ModuleType('_failure_check_'+p.stem);m.__file__=str(p);exec(compile(raw,str(p),'exec'),m.__dict__);return m
m=load('cleanup_failed_image.py');o=load('observe_failed_image_retirement.py')
for n in ('readback_observer.py','read_original_five_metadata.py','export_raw_five.py','postjoin_readback.py'):load(n)
case=json.loads(o.stable_bytes(o.FAILURE_CASE,o.FAILURE_CASE_SHA,4<<20));physical=json.loads(o.stable_bytes(o.RETIREMENT,o.RETIREMENT_SHA))
request=m.parse(m.read_bounded(m.REQUEST));owner=json.loads(o.stable_bytes(Path(physical['owner_receipt']['path']),physical['owner_receipt']['sha256']))
guard=json.loads(o.stable_bytes(Path(physical['guard_result']['path']),physical['guard_result']['sha256']))
inspection=json.loads(o.stable_bytes(Path(physical['terminal_fresh_inspect']['path']),physical['terminal_fresh_inspect']['sha256']))
argv,mounts=m.image_layout(request)
actual=sorted((v['Destination'],v['Source'],v['Type'],v['RW']) for v in inspection['Mounts'] if v['Type']=='bind')
assert argv==inspection['Config']['Cmd']==inspection['Args'] and mounts==actual
m.image_receipt_binding(owner,guard,case['target'],inspection,physical['owner_receipt']['sha256'])
selected={v['path']:dict(path=v['path'],sha256=v['sha256']) for v in m.SOURCE_REFS.values()}
m.typed_source_binding(request,dict(candidate_root=dict(inode=request['source_identity']['inode'])),selected)
def refuses(fn):
 try:fn()
 except m.Refusal:return
 raise AssertionError('expected specific refusal')
changed=copy.deepcopy(guard);changed['owner_status']='PASS'
refuses(lambda:m.image_receipt_binding(owner,changed,case['target'],inspection,physical['owner_receipt']['sha256']))
changed=copy.deepcopy(selected);changed[m.SOURCE_REFS['source_manifest']['path']]['sha256']='0'*64
refuses(lambda:m.typed_source_binding(request,dict(candidate_root=dict(inode=request['source_identity']['inode'])),changed))
for name,path in (('common',m.ATTEMPT),('shared',m.SHARED)):
 old=physical['retained_ownership'][name];m.image_record_binding(path,old,old['record'],request,case['target'],o.BOOT)
 changed=copy.deepcopy(old);changed['inode']+=1
 refuses(lambda:m.image_record_binding(path,changed,old['record'],request,case['target'],o.BOOT))
print(json.dumps(dict(status='PASS_ACTUAL_FAILURE_CALLBACKS_NO_EFFECTS',checks=['six_module_imports','actual_optin_layout','actual_FAIL_receipt','typed_source_and_changed_SHA_refusal','two_original_record_inode_refusals'],cleanup_executed=False)))
