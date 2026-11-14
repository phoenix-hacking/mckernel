"""Whole actual require_actual_ordinary body: genuine current join + stale refusal.
No authenticate PASS release, root/owner/lock/findmnt/materialization/build action.
"""
from pathlib import Path
import ast,copy,hashlib,json,sys
R=Path(__file__).resolve().parent
assert sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:3]==(3,9,12)
assert Path('/').is_relative_to(Path('/')) and not Path('/outside').is_relative_to(Path('/inside'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bound(r):
 p=Path(r['path']);raw=p.read_bytes();assert sha(p)==r['sha256'] and ('bytes' not in r or len(raw)==r['bytes']);return json.loads(raw)
j= json.loads((R/'ACTUAL-SOURCE-RUNTIME-STATIC-JOIN-DATA.json').read_text());assert j['status']=='ACTUAL_SOURCE_RUNTIME_STATIC_JOIN_INPUTS_ONLY_NOT_EXECUTION_RELEASE' and j['execution_authority'] is None
p=Path(j['guard']['path']);assert p.stat().st_size==j['guard']['bytes'] and sha(p)==j['guard']['sha256']
tree=ast.parse(p.read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='require_actual_ordinary');ns={'Path':Path,'hashlib':hashlib,'bound':bound}
exec(compile(ast.Module(body=[fn],type_ignores=[]),str(p),'exec'),ns)
q=bound(j['request']);ordinary=bound(j['prerequisites']['ordinary']);acceptance=bound(j['source_materialization_acceptance']);identity=[q['source_identity'][k] for k in ('dev','inode','uid','gid','mode')]
# Exactly the actual whole production caller body; all referenced reports/streams genuine.
assert ns['require_actual_ordinary'](q,j['request']['sha256'],j,ordinary,acceptance,identity) is None
wrong=copy.deepcopy(j);wrong['source_materialization_acceptance']={'path':'/home/holden/mckernel-work/host-preparation/phase5-panic-free-full-image-driver-independent-review-20261020-1/ACTUAL-FOUR-DELTA-6959-SOURCE-MATERIALIZATION-AND-IDENTITY-BINDING-REVIEW.json','sha256':'672181a8a0634ee8a8d613a5874050587074b364d8afb12a8025a16ce567c53c','bytes':7637}
bound(wrong['source_materialization_acceptance'])
try:ns['require_actual_ordinary'](q,j['request']['sha256'],wrong,ordinary,acceptance,identity)
except RuntimeError as e:assert str(e)=='exact current source/runtime request authority required'
else:raise AssertionError('stale genuine source report accepted')
result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PASS_WHOLE_ACTUAL_SOURCE_RUNTIME_CALLER_AND_STALE_REPORT_REFUSAL_ONLY','guard':j['guard'],'join_input_sha256':sha(R/'ACTUAL-SOURCE-RUNTIME-STATIC-JOIN-DATA.json'),'source_acceptance':j['source_materialization_acceptance'],'runtime_acceptance':j['runtime_binding_acceptance'],'request':j['request'],'genuine_current_positive':1,'genuine_stale_report_negative':1,'whole_actual_function_body_unmodified':True,'no_synthetic_PASS_release':True,'authenticate_or_owner_or_lock_or_findmnt_or_compiler':False,'current_image_or_native_acceptance':False}
with (R/'ACTUAL-WHOLE-SOURCE-RUNTIME-JOIN-RESULT.json').open('x') as out:out.write(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result))
