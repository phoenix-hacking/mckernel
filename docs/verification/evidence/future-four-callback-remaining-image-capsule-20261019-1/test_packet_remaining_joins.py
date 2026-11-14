from pathlib import Path
import copy,hashlib,json,types
P=Path(__file__).resolve().parent
path=P/'native_exact_scratch22_authority3_image_guard_corrected.py';blob=path.read_bytes();g=types.ModuleType('exact_remaining_guard');g.__file__=str(path);exec(compile(blob,str(path),'exec'),g.__dict__)
r=json.loads((P/'review-target-release-payload.json').read_text());q=json.loads(Path(r['request']['path']).read_text());o=json.loads(Path(r['prerequisites']['ordinary']['path']).read_text());a=json.loads(Path(r['ordinary_result_acceptance']['path']).read_text());identity=r['live_admission_required']['source_identity']
def check(ordinary,acceptance,release):g.require_actual_ordinary(q,r['request']['sha256'],release,ordinary,acceptance,identity)
check(o,a,r);negative=0
for key in ['request','actual_result','actual_owner_consumer']:
 z=copy.deepcopy(a);z[key]['sha256']='0'*64
 try:check(o,z,r)
 except (RuntimeError,FileNotFoundError):negative+=1
 else:raise AssertionError('changed actual reference accepted')
z=copy.deepcopy(r);z['retained_prebuild_acceptance']['sha256']='0'*64
try:check(o,a,z)
except RuntimeError:negative+=1
else:raise AssertionError('changed retained acceptance accepted')
print(json.dumps({'status':'PASS_ACTUAL_REMAINING_GUARD_INPUT_JOINS','positive':1,'negative':negative,'actual_seed':False,'owner_run':False,'compiler':False}))
