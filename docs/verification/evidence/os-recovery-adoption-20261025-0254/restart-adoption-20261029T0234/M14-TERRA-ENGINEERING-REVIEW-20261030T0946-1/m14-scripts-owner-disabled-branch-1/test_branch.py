#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import copy,importlib.util,json,pathlib
O=pathlib.Path(__file__).resolve().parent;sp=importlib.util.spec_from_file_location('owner',O/'owner.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
ma=m.SCRIPT_MANIFEST.read_bytes();bo=m.SCRIPT_BODY.read_bytes();ve=m.SCRIPT_VERIFIER.read_bytes();child=m.SCRIPTS_CHILD.read_bytes();doc=json.loads(ma);out=O/'never-created-output';cap=O/'never-created-capture';assert not out.exists() and not cap.exists()
req={'manifest_path':str(m.SCRIPT_MANIFEST),'body_path':str(m.SCRIPT_BODY),'verifier_path':str(m.SCRIPT_VERIFIER),'source_root':doc['base_scripts_candidate'],'output_root':str(out),'source_identity':None,'output_identity':None,'release':None}
results=[]
try:m.scripts_union_branch(req,ma,bo,ve,child,str(cap),1)
except RuntimeError as e:assert 'no authenticated live owner' in str(e);results.append({'case':'live_guard','outcome':'rejected','error':str(e)})
else:raise AssertionError('live guard opened')
# Deliberate fixture-only monkeypatch; no subprocess, custody or authority is created.
m._require_scripts_authority=lambda:None;calls=[]
def run(case,record):
 def capture(cmd,path,wall,limits):
  calls.append({'argv':cmd['argv'],'path':str(path),'wall':wall,'limit_name':limits.__name__});return record
 m._load_scripts_capture=lambda:capture
 r=m.scripts_union_branch(req,ma,bo,ve,child,str(cap),1)
 assert r['status']=='UNKNOWN_RETAIN_OUTPUT' and r['receipt_accepted'] is False and r['release'] is None and r['capture_record']==record
 assert calls[-1]['argv']==['/usr/bin/python3','-I','-B',str(m.SCRIPTS_CHILD)]
 results.append({'case':case,'outcome':r['status'],'receipt_accepted':r['receipt_accepted'],'mocked_capture_record':record})
run('missing_receipt',{'returncode':0,'direct_child_joined':True,'group_absent':True,'fixture_receipt':None})
run('partial_receipt',{'returncode':0,'direct_child_joined':True,'group_absent':True,'fixture_receipt':'{"status":'})
run('success_shaped_receipt',{'returncode':0,'direct_child_joined':True,'group_absent':True,'fixture_receipt':'{"status":"SUCCESS_BODY_ONLY"}'})
run('failed_join',{'returncode':0,'direct_child_joined':False,'group_absent':False,'fixture_receipt':'{"status":"SUCCESS_BODY_ONLY"}'})
run('synthetic_all_true',{'returncode':0,'direct_child_joined':True,'group_absent':True,'closed_streams':True,'custody':True,'durability':True,'fixture_receipt':'{"status":"SUCCESS_BODY_ONLY"}'})
def bad_capture(*args):raise OSError('synthetic capture failure')
m._load_scripts_capture=lambda:bad_capture;r=m.scripts_union_branch(req,ma,bo,ve,child,str(cap),1);assert r['status']=='UNKNOWN_RETAIN_OUTPUT' and r['terminal_proven'] is False and not r['receipt_accepted'];results.append({'case':'capture_exception','outcome':r['status'],'reason':r['reason']})
m._load_scripts_capture=lambda:(_ for _ in ()).throw(AssertionError('capture should not be called'))
for case,change,err in [('child_drift','child','exact scripts child bytes'),('manifest_drift','manifest','bound bytes: manifest')]:
 try:m.scripts_union_branch(req,ma+(b' ' if change=='manifest' else b''),bo,ve,child+(b' ' if change=='child' else b''),str(cap),1)
 except RuntimeError as e:assert err in str(e);results.append({'case':case,'outcome':'rejected','error':str(e)})
 else:raise AssertionError(case)
try:m._future_scripts_limits()
except RuntimeError as e:assert 'no reviewed child limits' in str(e);results.append({'case':'limits_guard','outcome':'rejected','error':str(e)})
else:raise AssertionError('limits guard opened')
assert len(calls)==5 and not out.exists() and not cap.exists();(O/'TEST-RESULTS.json').write_text(json.dumps(results,indent=2)+'\n');print('PASS',len(results),'source-bound mock/guard cases; no child, output or capture created')
