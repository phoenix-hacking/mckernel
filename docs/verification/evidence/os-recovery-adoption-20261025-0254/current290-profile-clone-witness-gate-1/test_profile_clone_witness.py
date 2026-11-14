"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure retained-text/proof controls; no compiler, workload, or object mutation.
"""
import ast,copy,hashlib,json
from pathlib import Path
from profile_clone_witness import validate
D=Path(__file__).resolve().parent;Q=D.parent/'current290-actual-build3-qualification-source-1'
text=(Q/'new-production-rust-undefined.nm').read_text()
proof=json.loads((Q/'CLONE-FINAL-POINTER-AND-WARNINGS.json').read_text())
results=[]
def positive(name,t,p):
    validate(t,p);results.append({'case':name,'result':'PASS_ACCEPTED'})
def negative(name,t,p):
    try:validate(t,p)
    except RuntimeError as e:results.append({'case':name,'result':'PASS_REJECTED','reason':str(e)})
    else:raise AssertionError('unexpected accepted control: '+name)
positive('exact retained current profile',text,proof)
lines=text.splitlines()
for kind in ('U','w','v'):
    changed=lines.copy();changed[0]=kind+' '+changed[0].strip().split(None,1)[1]
    positive('nm accepted type '+kind,'\n'.join(changed),proof)
for name,t in [
 ('empty',''),('blank row',text+'\n'),('malformed missing name','U'),
 ('unsupported type',text+'T foreign_provider\n'),
 ('clone U reintroduced',text+'U clone_thread\n'),
 ('clone weak reintroduced',text+'w clone_thread\n'),
 ('bounds panic',text+'U core::panicking::panic_bounds_check\n'),
 ('unwrap panic',text+'v core::result::unwrap_failed\n'),
 ('provider removed','\n'.join(lines[1:])),
 ('provider added',text+'U foreign_provider\n'),
 ('provider duplicated',text+lines[0]+'\n')]:negative(name,t,proof)
for field in ('source','new_Rust_object','new_process_object','new_image'):
    changed=copy.deepcopy(proof);changed[field]['sha256']='0'*64
    negative('wrong '+field,text,changed)
for field in ('clone_thread_object_symbol','clone_thread_final_symbol'):
    for key,value in [('bind',2),('shndx',0),('size',28)]:
        changed=copy.deepcopy(proof);changed[field][key]=value
        negative(field+' wrong '+key,text,changed)
for index in (0,1):
    for key,value in [('type',2),('offset',7),('addend',1)]:
        changed=copy.deepcopy(proof);changed['resolved_R64_final_pointers'][index]['relocation'][key]=value
        negative('pointer '+str(index)+' wrong '+key,text,changed)
changed=copy.deepcopy(proof);changed['resolved_R64_final_pointers'].pop()
negative('missing pointer',text,changed)
changed=copy.deepcopy(proof);changed['final_function_exact_object_code_with_only_two_R64_patches']=False
negative('no exact final bytes',text,changed)
negative('missing profile proof',text,{})
driver=Q.parent/'current290-driver-identity-repair-source-1/native_rust_exact_mckernel_image_offline.CURRENT290.VIEW-AND-FRESH-OBJECT-GATE.py'
raw=driver.read_bytes();assert hashlib.sha256(raw).hexdigest()=='9d2d39a0f4a28dc15638fe2c1a01052e64886078d39c3b1e7bf57eccf68bbdfd'
nodes=[n for n in ast.parse(raw).body if isinstance(n,ast.FunctionDef) and n.name in ('_fail','_no_core_panic_undefined')]
ns={'ImageBuildError':RuntimeError};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(driver)+':UNCHANGED_GENERIC_NEGATIVE_CONTROL','exec'),ns)
try:ns['_no_core_panic_undefined'](text)
except RuntimeError as e:
    assert str(e)=='production Rust undefined provider witness'
    results.append({'case':'unchanged generic original failure preserved','result':'PASS_EXPECTED_ORIGINAL_FAILURE','reason':str(e)})
else:raise AssertionError('original generic failure disappeared')
report={'scope':__doc__.splitlines()[0],'status':'PASS','controls':results,'count':len(results)}
(D/'REGRESSION-RESULT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':'PASS','controls':len(results)}))
