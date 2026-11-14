from pathlib import Path
import copy,importlib.util,json
R=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('fp_guard',R/'native_exact_scratch22_authority3_image_guard_corrected.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
r=json.loads((R/'review-target-release-payload.json').read_text())
o=json.loads(Path(r['prerequisites']['ordinary']['path']).read_text())
a=json.loads(Path(r['ordinary_result_acceptance']['path']).read_text())
q=json.loads(Path(r['request']['path']).read_text())
identity=r['live_admission_required']['source_identity']
def check(ordinary,acceptance,release):g.require_actual_ordinary(q,r['request']['sha256'],release,ordinary,acceptance,identity)
check(o,a,r)
labels=[]
for target,key in [('request','path'),('request','sha256'),('request','bytes'),('ordinary_result','path'),('ordinary_result','sha256'),('ordinary_result','bytes')]:
 changed=copy.deepcopy(a);changed[target][key]=0 if key=='bytes' else 'CHANGED'
 try:check(o,changed,r)
 except RuntimeError:labels.append(target+'.'+key)
 else:raise AssertionError('changed pointer accepted')
changed=copy.deepcopy(o);changed['bindings']['image-request.json']['bytes']+=1
try:check(changed,a,r)
except RuntimeError:labels.append('bound_request.bytes')
else:raise AssertionError('changed actual bound size accepted')
print(json.dumps({'status':'PASS_EXACT_COMPLETED_ORDINARY_SEMANTIC_JOINS','positive':1,'negative':len(labels),'controls':labels,'compiler_executions':0}))
