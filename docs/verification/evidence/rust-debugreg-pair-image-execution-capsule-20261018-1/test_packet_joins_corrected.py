"""Source-bound guard fixtures only; no actual ordinary/compiler/runtime acceptance."""
from pathlib import Path
import copy,importlib.util,json
R=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('paired_corrected_guard',R/'native_exact_scratch22_authority3_image_guard_corrected.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
identity=[101,202,1000,1000,448]
request={'source_root':'FIXTURE_SOURCE_ONLY'}
request_sha='a'*64
pointer={'path':'FIXTURE_ORDINARY_ONLY','sha256':'b'*64}
release={'author':'fixture-author','request':{'path':'FIXTURE_REQUEST_ONLY','sha256':request_sha},'prerequisites':{'ordinary':pointer},'live_admission_required':{'source_identity':identity}}
ordinary={'status':'PASS_ONE_ORDINARY_PREPARATION_SEQUENCE','bindings':{'image-request.json':dict(release['request'],bytes=1)},'source_identity':{'device':101,'inode':202},'stages':[{'stage':name,'exit_code':0,'direct_child_joined':True,'process_identity_captured':True,'observer_error':None,'stderr_bytes':0} for name in ['materialize','mkdir','prepare','consume']]}
acceptance={'schema':'mckernel.debugreg-pair-actual-ordinary-consumer-acceptance.v1','decision':'PASS_ACTUAL_ORDINARY_RESULT','ordinary_result_accepted':True,'implementation_ownership':False,'reviewer':'independent-fixture-reviewer','ordinary_result':pointer,'request':release['request'],'source_identity':identity,'verified':{'actual_driver_and_owner_request_consumers':True,'actual_full_source_validation':True}}
def check(o,a,r):g.require_actual_ordinary(request,request_sha,r,o,a,identity)
check(ordinary,acceptance,release)
negatives=[]
for label,target,path,value in [
 ('ordinary_request_hash','ordinary',['bindings','image-request.json','sha256'],'0'*64),
 ('ordinary_source_inode','ordinary',['source_identity','inode'],999),
 ('ordinary_stage_directjoin','ordinary',['stages',0,'direct_child_joined'],False),
 ('ordinary_stage_observer','ordinary',['stages',0,'observer_error'],{'type':'fixture'}),
 ('ordinary_generic_pass','ordinary',['status'],'PASS'),
 ('acceptance_pending','acceptance',['decision'],'PENDING'),
 ('acceptance_boolean_only','acceptance',['schema'],'generic'),
 ('acceptance_request_hash','acceptance',['request','sha256'],'0'*64),
 ('acceptance_source_identity','acceptance',['source_identity'],[101,999,1000,1000,448]),
 ('acceptance_result_pointer','acceptance',['ordinary_result','sha256'],'0'*64),
 ('acceptance_author','acceptance',['reviewer'],'fixture-author'),
 ('release_source_identity','release',['live_admission_required','source_identity'],[101,999,1000,1000,448]),
]:
 o,a,r=copy.deepcopy(ordinary),copy.deepcopy(acceptance),copy.deepcopy(release);obj={'ordinary':o,'acceptance':a,'release':r}[target]
 for key in path[:-1]:obj=obj[key]
 obj[path[-1]]=value
 try:check(o,a,r)
 except RuntimeError:negatives.append(label)
 else:raise AssertionError('invalid fixture accepted: '+label)
print(json.dumps({'status':'PASS_GUARD_ORDINARY_JOIN_FIXTURES_ONLY','positive_fixtures':1,'negative_fixtures':len(negatives),'negative_families':negatives,'actual_ordinary_acceptance':False,'builds':0,'guests':0}))
