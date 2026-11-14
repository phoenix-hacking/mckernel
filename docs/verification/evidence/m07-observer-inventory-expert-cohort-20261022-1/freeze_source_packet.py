"""Source comparison/in-memory compile only. Does not import generated modules or tests."""
from pathlib import Path
import ast,difflib,hashlib,json
D=Path(__file__).parent;G=D/'bound-terminal-expert-source-1';OLD=D.parent/'m07-observer-full-inventory-schema-correction-20261022-1'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def ref(p):return dict(path=str(p),bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
def create(p,raw):
 if isinstance(raw,str):raw=raw.encode()
 with p.open('xb') as s:s.write(raw)
 p.chmod(0o600)
def dump(p,value):create(p,json.dumps(value,indent=2,sort_keys=True)+'\n')
def funcs(p):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(p.read_bytes()).body if isinstance(n,ast.FunctionDef)}
comparisons={}
for name in ('observe_current_pass_image_retirement.py','postjoin_readback.py','readback_observer.py'):
 a=funcs(G/name);b=funcs(OLD/name);different=[k for k in a if a[k]!=b.get(k)];assert not different,(name,different);assert set(a)==set(b),(name,'function set differs')
 comparisons[name]=dict(function_count=len(a),all_functions_AST_identical_to_reviewed_direct_copy=True,generated=ref(G/name),reviewed_direct_copy=ref(OLD/name))
 create(D/(name+'.generated.diff'),''.join(difflib.unified_diff((OLD/name).read_text().splitlines(True),(G/name).read_text().splitlines(True),fromfile=str(OLD/name),tofile=str(G/name))))
case=json.loads((G/'PASS-CASE-STATIC.json').read_bytes());assert case['finite_unique_path_count']==len(case['finite_unique_paths'])==88;assert case['finite_role_count']==len(case['finite_roles'])==97
assert case['current_live_postjoin']==case['finite_roles']['guard_postjoin'];assert case['current_live_postjoin']['sha256']=='2f092dd706e7b1f6bb740164eda938a66ed7dcc7a92cee38a304bf878ccff357'
assert all(case[k] is None for k in ('postjoin_result','cleanup_release','cleanup_result','observation','observation_release'))
t=(D/'test_generated_full_main.TEMPLATE.py').read_text().replace('__CASE_SHA__',repr(sha((G/'PASS-CASE-STATIC.json').read_bytes()))).replace('__PATH_COUNT__',repr(case['finite_unique_path_count'])).replace('__ROLE_COUNT__',repr(case['finite_role_count']))
compile(t,str(D/'test_generated_full_main.py'),'exec');create(D/'test_generated_full_main.py',t)
compiled=[]
for path in sorted(D.rglob('*.py')):
 if path.name.endswith('.TEMPLATE.py'):continue
 compile(path.read_bytes(),str(path),'exec');compiled.append(ref(path))
dump(D/'SOURCE-ONLY-COMPARISONS.json',dict(status='PASS_SOURCE_COMPARISON_AND_IN_MEMORY_COMPILE_ONLY_NOT_TEST_ACCEPTANCE',functions=comparisons,in_memory_compiled=compiled,production_case=ref(G/'PASS-CASE-STATIC.json'),pinned_case_paths=88,pinned_case_roles=97,predecessor_guard_postjoin_preserved=True,null_future_fields_preserved=True,test_imported=False,test_executed=False,execution_authorized=False))
command='taskset -c 6 /usr/bin/timeout 30 /usr/bin/prlimit --as=1073741824 --cpu=20 -- /usr/bin/python3 -I -B '+str(D/'test_generated_full_main.py')+' > '+str(D/'full-test-1.stdout')+' 2> '+str(D/'full-test-1.stderr')
dump(D/'SINGLE-TEST-COMMAND.PENDING.json',dict(status='PENDING_INDEPENDENT_SOURCE_VERIFICATION_NO_TEST_RUN_YET',command=command,test=ref(D/'test_generated_full_main.py'),only_one_invocation=True,no_local_retry=True,scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',root_or_guest_actions=False))
print(json.dumps(dict(status='PASS_SOURCE_ONLY_NO_TEST_RUN',function_comparisons={k:v['function_count'] for k,v in comparisons.items()},compiled=len(compiled)),sort_keys=True))
