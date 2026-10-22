from pathlib import Path
import ast,hashlib,json,pathlib,sys,os
C=Path(__file__).resolve().parent
E=C.parent
assert sys.executable=="/home/holden/anaconda3/bin/python3" and sys.version_info[:3]==(3,9,12) and sys.dont_write_bytecode
q=json.loads((E/"image-request-SOURCE-BOUND-BASIS.json").read_text())
d=json.loads((E/"FINAL-ROOT-RELEASE-DATA-ROOT-BOUND.TEMPLATE.json").read_text())
old_d=json.loads((C/"FINAL-ROOT-RELEASE-DATA-ROOT-BOUND.TEMPLATE.json.INITIAL").read_text())
for p in [E/"image-execution-release.json",E/"image-request.json",E/"actual-root-owner-1",E/"final-release-payload-ROOT-DATA-1.json"]:assert not os.path.lexists(p)
def tree(path):return ast.parse(path.read_text(),str(path))
def segment(path,node):return ast.get_source_segment(path.read_text(),node)
def actual_nodes(path,nodes,namespace):exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),"exec"),namespace)
caller=E/"root-launch-reviewed-full-once.PENDING.py"
original=C/"root-launch-reviewed-full-once.PENDING.py.INITIAL"
def profile_nodes(path):
 t=tree(path);assignment=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=="profile" for x in n.targets));assertion=next(n for n in t.body if isinstance(n,ast.Assert) and "FINAL-ROOT-LAUNCH-AND-CAPTURE-PROFILE.json" in segment(path,n));argv=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=="argv" for x in n.targets));argv_check=next(n for n in t.body if isinstance(n,ast.Assert) and "ACTUAL_FINAL_RELEASE_SHA256_FROM_FILE" in segment(path,n));return [assignment,assertion,argv,argv_check]
namespace={"H":E,"hashlib":hashlib,"json":json}
actual_nodes(caller,profile_nodes(caller),namespace)
try:actual_nodes(original,profile_nodes(original),{"H":E,"hashlib":hashlib,"json":json})
except AssertionError:pass
else:raise AssertionError("original consumer profile assertion accepted current profile")
# Execute actual dispatcher source read and identity assert only; no live/root admission or dispatch.
dispatch=E/"dispatch-image-once.py";t=tree(dispatch);source_read=next(n for n in t.body if isinstance(n,ast.Assign) and any(isinstance(x,ast.Name) and x.id=="source" for x in n.targets));identity_assert=next(n for n in t.body if isinstance(n,ast.Assert) and "live_admission_required" in segment(dispatch,n) and "source_identity" in segment(dispatch,n));actual_nodes(dispatch,[source_read,identity_assert],{"pathlib":pathlib,"q":q,"d":d})
try:actual_nodes(dispatch,[source_read,identity_assert],{"pathlib":pathlib,"q":q,"d":old_d})
except AssertionError:pass
else:raise AssertionError("original live identity accepted new source")
# Evaluate unchanged real guard source-fingerprint rejection predicates with actual request.
# No PASS_EXECUTION_RELEASE object, snapshot, review or other execution authority is fabricated.
def fingerprint_predicates(path):
 t=tree(path);fn=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=="authenticate");answer=[]
 for n in ast.walk(fn):
  if isinstance(n,ast.Compare) and isinstance(n.left,ast.Call) and isinstance(n.left.func,ast.Attribute) and isinstance(n.left.func.value,ast.Name) and n.left.func.value.id=="request" and n.left.func.attr=="get" and isinstance(n.left.args[0],ast.Constant) and n.left.args[0].value in ["source_derivative_sha256","materialization_sha256"] and isinstance(n.comparators[0],ast.Constant):answer.append(n)
 assert len(answer)==2;return answer
for node in fingerprint_predicates(E/"native_exact_current_optin_image_guard.py"):assert eval(compile(ast.Expression(node),str(E/"native_exact_current_optin_image_guard.py"),"eval"),{"request":q}) is False
for node in fingerprint_predicates(C/"native_exact_current_optin_image_guard.py.INITIAL"):assert eval(compile(ast.Expression(node),str(C/"native_exact_current_optin_image_guard.py.INITIAL"),"eval"),{"request":q}) is True
# Actual pure final-binder ref function and already available assert expressions.
binder=E/"prepare_final_image_binding_from_root_snapshot.py";t=tree(binder);refdef=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=="ref");ns={"pathlib":pathlib,"hashlib":hashlib,"d":d,"G":E};actual_nodes(binder,[refdef],ns)
chosen=[n for n in t.body if isinstance(n,ast.Assert) and any(k in segment(binder,n) for k in ["d['bound_request_basis']","d['dispatcher']","d['source_sha256']"])]
assert len(chosen)==3
actual_nodes(binder,chosen,ns)
# Enumerate and check all currently consumed source/request/guard/profile references.
guardtree=tree(E/"native_exact_current_optin_image_guard.py");values={}
for node in guardtree.body:
 if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in ["SOURCES","SOURCE_REF","GATES_REF","BINDINGS","RECEIPT_REF","RESULT_REF","MATERIAL_CAPTURE_REF","VALIDATOR_CAPTURE_REF"]:values[node.targets[0].id]=ast.literal_eval(node.value)
assert set(d["source_sha256"])==set(values["SOURCES"])
for path,checksum in d["source_sha256"].items():assert hashlib.sha256(Path(path).read_bytes()).hexdigest()==checksum
assert d["source_materialization_acceptance"]==values["SOURCE_REF"] and d["whole_source_gate_acceptance"]==values["GATES_REF"]
assert d["runtime_binding_acceptance"]==values["BINDINGS"]["runtime_ref"] and d["bound_request_basis"]==values["BINDINGS"]["basis_ref"]
for pointer in [values[k] for k in ["SOURCE_REF","GATES_REF","RECEIPT_REF","RESULT_REF","MATERIAL_CAPTURE_REF","VALIDATOR_CAPTURE_REF"]]+list(values["BINDINGS"].values()):
 raw=Path(pointer["path"]).read_bytes();assert hashlib.sha256(raw).hexdigest()==pointer["sha256"] and len(raw)==pointer["bytes"]
assert namespace["profile"]["expected_release_path"]==str(E/"image-execution-release.json")
assert namespace["argv"][-2]==str(E/"dispatch-image-once.py")
assert (E/"root-launch-reviewed-full-once.PENDING.py").read_text().count("PENDING_GENUINE_CANONICAL_PAYLOAD_SHA256")==1
for p in [E/"image-execution-release.json",E/"image-request.json",E/"actual-root-owner-1",E/"final-release-payload-ROOT-DATA-1.json"]:assert not os.path.lexists(p)
print(json.dumps({"scope":"Functional McKernel OS/apps and Rust/assembly migration only; no security testing.","status":"PASS_ACTUAL_FINALCONTROL_PROFILE_IDENTITY_FINGERPRINT_AND_BOUND_SOURCE_REF_EXPRESSIONS_ONLY","actual_corrected_caller_profile_load_and_assert":True,"original_caller_profile_refused":True,"actual_dispatcher_source_read_identity_assert":True,"original_template_identity_refused":True,"actual_current_guard_fingerprint_predicates_admit":2,"original_guard_fingerprint_predicates_reject":2,"actual_finalbinder_asserts":3,"exact_guard_source_closure":11,"bound_evidence_ref_hashes":8,"final_release_or_dispatch_or_root_or_owner_main":False},sort_keys=True))
