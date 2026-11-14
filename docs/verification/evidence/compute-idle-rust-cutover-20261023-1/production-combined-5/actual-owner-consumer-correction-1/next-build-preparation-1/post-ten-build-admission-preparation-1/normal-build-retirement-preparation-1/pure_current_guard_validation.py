"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Only actual retained-data pure functions. No engine.main/configure/recover,
Docker/root command, record mutation, release, cleanup or workload."""
from pathlib import Path
import copy,hashlib,importlib.util,json
D=Path(__file__).resolve().parent;P=D/'bound-current-normal-image-source-1'
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def data(path):return json.loads(Path(path).read_bytes())
m=load('current_normal_cleanup_pure',P/'cleanup_pass_image.py')
o=load('current_normal_observer_pure',P/'observe_current_pass_image_retirement.py')
case=data(P/'PASS-CASE-STATIC.json');refs=case['finite_roles'];target=case['target']
request=data(refs['request']['path']);owner=data(refs['owner_receipt']['path']);guard=data(refs['guard_result']['path'])
item=data(refs['terminal_inspection']['path'])[0]
m.validate_attempt_binding(target,{'path':str(m.REQUEST),'sha256':m.REQUEST_SHA})
m.image_request_binding(request)
command,mounts=m.image_layout(request)
assert command.count('--native-fork-owned-transaction')==1 and mounts
m.image_receipt_binding(owner,guard,target,item,refs['owner_receipt']['sha256'])
retirement=data(refs['retained_review']['path'])
shared=retirement['shared_record_from_actual_owner']['record']
m.image_record_binding(m.SHARED,{'device':shared['device'],'inode':shared['inode']},shared,request,target,shared['boot_id'])
assert hashlib.sha256(m.canonical(request)).hexdigest()==shared['request_sha256']=='2176c6f4ce78d73122e2180864afd9ffc0c90abadf55a589f8205089c9b85274'
common_expected=hashlib.sha256(json.dumps(request,sort_keys=True).encode()).hexdigest()
assert common_expected!=shared['request_sha256'] and refs['request']['sha256'] not in (common_expected,shared['request_sha256'])
m.typed_source_binding(request,{'candidate_root':{'inode':request['source_identity']['inode']}},{r['path']:{'sha256':r['sha256']} for r in refs.values()})
o.current_pass_prerequisites(retirement,case,data(case['current_live_postjoin']['path']),data(case['artifact_acceptance']['path']))
paths=o.decode_finite_case(case);assert len(paths)==case['finite_unique_path_count']
negatives=[]
def reject(action,label):
 try:action()
 except (m.Refusal,RuntimeError,ValueError):negatives.append(label)
 else:raise AssertionError('accepted mutation '+label)
for key,value in [('pid',guard['pid']+1),('proc_start_ticks','1'),('direct_child_joined',False),('process_group_absent',False),('streams_closed',False),('returncode',1)]:
 changed=copy.deepcopy(guard);changed[key]=value
 reject(lambda:m.image_receipt_binding(owner,changed,target,item,refs['owner_receipt']['sha256']),'closed-'+key)
changed=copy.deepcopy(shared);changed['request_sha256']=refs['request']['sha256']
reject(lambda:m.image_record_binding(m.SHARED,{'device':shared['device'],'inode':shared['inode']},changed,request,target,shared['boot_id']),'prepared-file-digest-cannot-replace-shared-canonical')
changed=copy.deepcopy(item);changed['State']['Pid']=999
reject(lambda:m.image_receipt_binding(owner,guard,target,changed,refs['owner_receipt']['sha256']),'current-inspect-PID-drift')
changed=data(case['artifact_acceptance']['path']);changed['owner_sha256']='0'*64
reject(lambda:o.current_pass_prerequisites(retirement,case,data(case['current_live_postjoin']['path']),changed),'artifact-owner-source-drift')
print(json.dumps({'status':'PASS_ACTUAL_RETAINED_NORMAL_IMAGE_TYPED_GUARDS_PURE_ONLY','current_closed_owner':True,'actual_fresh_inspect':True,'actual_shared_record_canonical':shared['request_sha256'],'expected_common_record_codec':common_expected,'actual_common_record_checked':False,'actual_common_record_requirement':'Fresh root observer must acquire stable original common identity and run unchanged image_record_binding; pure test claims no common-file observation.','finite_roles':case['finite_role_count'],'finite_paths':len(paths),'negative_controls':negatives,'mutations':0,'privileged_or_Docker_or_cleanup_calls':0,'physical_clearance':False}))
