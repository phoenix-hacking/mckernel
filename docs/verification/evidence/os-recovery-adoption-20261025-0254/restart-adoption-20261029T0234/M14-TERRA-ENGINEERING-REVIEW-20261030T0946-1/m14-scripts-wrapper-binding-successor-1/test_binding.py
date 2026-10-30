#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import copy,importlib.util,json,pathlib
O=pathlib.Path(__file__).resolve().parent;sp=importlib.util.spec_from_file_location('owner',O/'owner.py');m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
manifest=m.SCRIPT_MANIFEST.read_bytes();body=m.SCRIPT_BODY.read_bytes();verifier=m.SCRIPT_VERIFIER.read_bytes();doc=json.loads(manifest)
out=O/'fixture-output-must-remain-absent';assert not out.exists()
request={'manifest_path':str(m.SCRIPT_MANIFEST),'body_path':str(m.SCRIPT_BODY),'verifier_path':str(m.SCRIPT_VERIFIER),'source_root':doc['base_scripts_candidate'],'output_root':str(out),'source_identity':None,'output_identity':None,'release':None};cases=[]
def run(name,req,ma=manifest,bo=body,ve=verifier,err=None):
 try:r=m.validate_frozen_scripts_binding(req,ma,bo,ve)
 except Exception as e:
  assert err is not None and err in str(e),(name,str(e),err);cases.append({'case':name,'outcome':'rejected','error':str(e)})
 else:
  assert err is None and r['status']=='SOURCE_BINDING_ONLY_LIVE_ENTRY_BLOCKED' and r['authority'] is None and r['release'] is None and not r['started'];cases.append({'case':name,'outcome':'pass','result':r})
run('valid_source_only',request)
run('manifest_tamper',request,ma=manifest+b' ',err='bound bytes: manifest')
run('body_tamper',request,bo=body+b' ',err='bound bytes: materializer')
run('verifier_tamper',request,ve=verifier+b' ',err='bound bytes: verifier')
for name,key,value,err in [('wrong_source','source_root','/tmp/wrong','source root binding'),('wrong_manifest_path','manifest_path','/tmp/manifest','bound path: manifest_path'),('wrong_body_path','body_path','/tmp/body','bound path: body_path'),('wrong_verifier_path','verifier_path','/tmp/verifier','bound path: verifier_path'),('relative_output','output_root','relative','normalized output'),('nested_output','output_root',request['source_root']+'/sub','source/output lexical separation'),('invented_source_identity','source_identity',{'inode':1},'live state must remain unbound'),('invented_release','release',{'status':'GRANTED'},'live state must remain unbound')]:
 r=copy.deepcopy(request);r[key]=value;run(name,r,err=err)
r=copy.deepcopy(request);r['extra']='x';run('extra_schema',r,err='exact binding schema')
assert not out.exists();(O/'TEST-RESULTS.json').write_text(json.dumps(cases,indent=2)+'\n');print('PASS',len(cases),'source-only binding cases; output not created')
