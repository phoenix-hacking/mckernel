#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import ast,copy,hashlib,importlib.util,json,pathlib
O=pathlib.Path(__file__).resolve().parent;A=O.parent;sp=importlib.util.spec_from_file_location('v',O/'validator.py');v=importlib.util.module_from_spec(sp);sp.loader.exec_module(v)
paths=[A/'m14-scripts-overlay-proposal-1/SCRIPTS-OVERLAY.NOT-RELEASED.json',A/'m14-nonheld-composition-1/MANIFEST.json',A/'m14-perf-standalone-integration-1/INTEGRATION.json'];pb,mb,db=[x.read_bytes() for x in paths];plan=json.loads(pb);parent=json.loads(mb);delta=json.loads(db)
rows=[{'target':x['target'],'host_candidate':x['host_candidate'],'access':x['access'],'live_identity':None} for x in plan['future_mounts_parent_first']];d=delta['prospective_on_mount_delta'];rows.append({'target':d['target'],'host_candidate':d['host_candidate'],'access':'ro','live_identity':None});rows.sort(key=lambda x:(0 if x['target']=='/work' else 1,len(pathlib.PurePosixPath(x['target']).parts),x['target']))
mem=parent['rust_regular_file_hashes'];bind={'parent_dir':{'device':1,'inode':10,'kind':'directory'},'parent_file':{'device':1,'inode':11,'kind':'file'},'child_file':{'device':1,'inode':12,'kind':'file'},'parent_file_sha256':v.PERF_PRE,'child_file_sha256':v.PERF_POST};records=[]
def check(name,rr=rows,mm=mem,bb=bind,p=pb,q=mb,d=db,err=None):
 try:x=v.validate_perf_one_file_model(rr,mm,bb,p,q,d)
 except Exception as e:
  assert err is not None and err in str(e),(name,type(e).__name__,str(e),err);records.append({'case':name,'outcome':'rejected','error':str(e)})
 else:
  assert err is None and x['authority'] is None and x['source_identity'] is None and x['effective_mount_identity'] is None;records.append({'case':name,'outcome':'source-model-only'})
check('positive')
wrong=copy.deepcopy(rows);i=next(i for i,x in enumerate(wrong) if x['target']==v.PERF_CHILD);wrong[i]['target']='/src/kernel/rust/other.rs';check('unapproved_child',rr=wrong,err='unapproved nested shadow')
wrong=copy.deepcopy(rows);i=next(i for i,x in enumerate(wrong) if x['target']==v.PERF_CHILD);wrong[i]['target']='/src/kernel/rust/sub/other.rs';check('unapproved_grandchild',rr=wrong,err='unapproved nested shadow')
wrong=copy.deepcopy(rows);a=next(i for i,x in enumerate(wrong) if x['target']==v.PERF_CHILD);b=next(i for i,x in enumerate(wrong) if x['target']==v.PERF_PARENT);wrong[a],wrong[b]=wrong[b],wrong[a];check('parent_after_child',rr=wrong,err='parent after child')
wrong=copy.deepcopy(rows);wrong[-1]=copy.deepcopy(wrong[-2]);check('duplicate_target',rr=wrong,err='duplicate mount')
wrong=copy.deepcopy(rows);wrong.pop();check('missing_target',rr=wrong,err='successor target count')
wrong=copy.deepcopy(rows);x=next(x for x in wrong if x['target']==v.PERF_CHILD);x['host_candidate']='/tmp/wrong';check('wrong_child_path',rr=wrong,err='perf source path differs')
for name,key,val,err in [('wrong_parent_hash','parent_file_sha256','0'*64,'source content binding differs'),('wrong_child_hash','child_file_sha256','0'*64,'source content binding differs'),('same_file_inode','child_file',bind['parent_file'],'source inode alias')]:
 b=copy.deepcopy(bind);b[key]=val;check(name,bb=b,err=err)
wrong=dict(mem);del wrong[next(k for k in wrong if k!=v.PERF_NAME)];check('missing_parent_member',mm=wrong,err='parent membership differs')
wrong=dict(mem);wrong[v.PERF_NAME]=v.PERF_POST;check('overwritten_parent_hash',mm=wrong,err='parent membership differs')
wrong=copy.deepcopy(rows);x=next(x for x in wrong if x['target']==v.PERF_CHILD);x['live_identity']={'inode':12};check('invented_live_identity',rr=wrong,err='live identity must stay unbound')
check('manifest_tamper',q=mb+b' ',err='source manifest digest mismatch')
try:v._collect({},None,None,None)
except ValueError as e:assert 'SOURCE_ONLY' in str(e);records.append({'case':'collect_still_blocked','outcome':'rejected','error':str(e)})
else:raise AssertionError('collector unblocked')
mapdoc={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing','status':'SOURCE_MODEL_ONLY_UNRELEASED','authority':None,'mounts_parent_first':rows,'parent_tree_manifest_path':str(paths[1]),'parent_tree_manifest_sha256':v.PERF_PARENT_MANIFEST_SHA,'parent_tree_membership':'unchanged 157-entry Rust parent manifest; underlying perf preimage stays pinned and is shadowed only in effective child view','perf_preimage_sha256':v.PERF_PRE,'perf_child_sha256':v.PERF_POST,'live_source_identities':None,'effective_mount_identity':None,'source_bindings_authenticated':False,'future_driver_requirement':'Rework disabled effective-view validator: validate complete parent tree at host before mounts, then exact child shadow and actual mountinfo/read-only/content/identity, no unapproved mounts. Never treat masked parent entry as absent.'}
(O/'MAP.NOT-RELEASED.json').write_text(json.dumps(mapdoc,indent=2)+'\n');(O/'TEST-RESULTS.json').write_text(json.dumps(records,indent=2)+'\n');print('PASS',len(records),'source-only model tests; no mount, full tree read or live collection')
