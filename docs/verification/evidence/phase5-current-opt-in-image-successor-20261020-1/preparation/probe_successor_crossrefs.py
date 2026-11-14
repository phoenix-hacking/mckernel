"""No-effect actual successor crossrefs/copy dispatch, not owner execution."""
import ast,copy,hashlib,importlib.util,json
from pathlib import Path
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('successor_owner',str(P/'native_rust_exact_mckernel_image_container_owner.py'))
owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
request=json.loads((P/'image-request-SOURCE-ONLY-PROPOSAL.json').read_text())
positive=owner.preflight_request_crossrefs(request)
refusals={}
def refused(label,value,expected):
 try:owner.preflight_request_crossrefs(value)
 except owner.OwnerError as error:
  assert expected in str(error),(label,str(error));refusals[label]=str(error)
 else:raise AssertionError('accepted negative '+label)
old=json.loads((P.parent/'runtime-binding-correction-1/image-request.json').read_text())
stale=copy.deepcopy(request)
for key in ['gitlink_manifest','gitlink_manifest_sha256']:stale[key]=old[key]
refused('actual_historical_stale_supplement',stale,'gitlink base manifest hash differs')
wrong=copy.deepcopy(request);wrong['source_manifest_sha256']='0'*64
refused('wrong_source_identity',wrong,'source_manifest deterministic hash differs')
wrong=copy.deepcopy(request);wrong['driver_sha256']='0'*64
refused('wrong_driver_identity',wrong,'driver_path deterministic hash differs')
wrong=copy.deepcopy(request);wrong['candidate_sha']='0'*40
refused('wrong_candidate_join',wrong,'gitlink manifest identity differs')
tree=ast.parse((P/'native_rust_exact_mckernel_image_offline.py').read_text())
run=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_run')
assign=[n for n in ast.walk(run) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='relative' for t in n.targets) and isinstance(n.value,ast.Subscript) and isinstance(n.value.value,ast.Dict)]
assert len(assign)==1
mapping=ast.literal_eval(assign[0].value.value)
expected={'mckernel.img','mckernel.img.map','CMakeCache.txt','compile_commands.json','mckernel_rust.o','build.make','mcexec','mcexec_helpers.o','mcexec-rust-build.make'}
assert set(mapping)==expected and all(mapping[k]==k for k in mapping)
guard=ast.parse((P/'native_exact_current_optin_image_guard-SOURCE-PROPOSAL.py').read_text())
fn=next(n for n in guard.body if isinstance(n,ast.FunctionDef) and n.name=='guarded_execute')
preflight=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='preflight_request_crossrefs')
maintry=next(i for i,n in enumerate(fn.body) if isinstance(n,ast.Try))
assert preflight<maintry
assert any(isinstance(n,ast.ExceptHandler) and isinstance(n.type,ast.Name) and n.type.id=='BaseException' for n in ast.walk(fn))
print(json.dumps({'status':'PASS_NO_EFFECT_SUCCESSOR_CROSSREFS_AND_NINE_COPY','positive':positive,'refusals':refusals,'copy_keys':sorted(mapping),'guard_preflight_before_admission':True,'no_owner_run_or_live_validate':True,'no_Docker_or_locks':True},sort_keys=True))
