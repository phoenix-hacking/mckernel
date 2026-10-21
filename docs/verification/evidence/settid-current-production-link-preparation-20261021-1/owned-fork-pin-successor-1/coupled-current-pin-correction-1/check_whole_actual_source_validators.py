"""Actual whole validators, current source gates and genuine old-pin refusals.
No extraction, monkeypatch, fake artifact, compiler, root, lock or materializer.
Affinity full PASS is a later real build obligation; this check observes its
source gates by reaching a genuinely missing compile_commands.json read.
"""
from pathlib import Path
import ast,hashlib,importlib.util,json,os,sys
R=Path(__file__).resolve().parent
O=R.parent.parent
source=O/'source-materialization-1/materialized-source'
missing=R/'missing-build-read-boundary-1'
assert sys.executable=='/home/holden/anaconda3/bin/python3' and sys.version_info[:3]==(3,9,12)
assert sys.dont_write_bytecode and Path('/').is_relative_to(Path('/')) and not Path('/outside').is_relative_to(Path('/inside'))
assert not os.path.lexists(missing)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(O/'native_rust_exact_build_offline.py')=='0407c1d87fe85fbcda7f23872f3f47fe64c238f7ef6cc0c6e4f21fd63253fd4d'
assert sha(O/'native_rust_exact_mckernel_image_offline.py')=='319790fd648ea82c7ef3adc129cc9cc329c08ea23beed105fdfeeb6770f09d9a'
assert sha(R/'native_rust_exact_mckernel_image_offline.py')=='c269f7387b0937368fd2da53a837d49699c4f3a311b22b80fd0966dcb948a986'
# Import entire genuine modules under isolated names. Only their real main guards
# suppress build execution; no function/source AST is extracted or rewritten.
sys.path.insert(0,str(O))
def whole_module(name,path):
 spec=importlib.util.spec_from_file_location(name,str(path));module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
old=whole_module('_retained_full_actual_image_driver',O/'native_rust_exact_mckernel_image_offline.py')
new=whole_module('_successor_full_actual_image_driver',R/'native_rust_exact_mckernel_image_offline.py')
assert Path(new.provenance.__file__).resolve()==O/'native_rust_exact_build_offline.py'
assert new.provenance is old.provenance
for name,count in [('OWNED_FORK_CURRENT_SOURCE_PINS',13),('AFFINITY_SOURCE_PINS',5)]:
 a=getattr(old,name);b=getattr(new,name);assert len(a)==len(b)==count
 assert [k for k in a if a[k]!=b[k]]==['kernel/syscall.c','kernel/rust/syscall_policy.rs']
assert new._validate_owned_fork_current_sources(source) is None
try:old._validate_owned_fork_current_sources(source)
except old.ImageBuildError as e:assert str(e)=='owned fork current prerequisite drift kernel/syscall.c'
else:raise AssertionError('genuine old owned pins accepted currentsource')
args=(source,missing,None,None,None,None,None,1,[])
try:new._validate_clone_affinity_production(*args)
except FileNotFoundError as e:
 assert e.errno==2 and e.filename==str(missing/'compile_commands.json')
else:raise AssertionError('missing real compile database boundary not observed')
assert not os.path.lexists(missing)
try:old._validate_clone_affinity_production(*args)
except old.ImageBuildError as e:assert str(e)=='affinity actual dependency drift kernel/syscall.c'
else:raise AssertionError('genuine old affinity pins reached current build boundary')
assert not os.path.lexists(missing)
result={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PASS_WHOLE_OWNED_VALIDATOR_AND_ACTUAL_AFFINITY_SOURCE_GATES_ONLY','whole_owned_current_positive':True,'whole_owned_genuine_old_pin_refusal':True,'whole_affinity_current_source_gates_completed':True,'whole_affinity_observed_endpoint':{'exception':'FileNotFoundError','errno':2,'filename':str(missing/'compile_commands.json'),'build_path_remains_absent':True},'whole_affinity_genuine_old_pin_refusal':True,'whole_affinity_function_PASS':False,'whole_affinity_compiler_output_acceptance':False,'entire_modules_imported':True,'function_extraction_or_monkeypatch_or_stubs':False,'compiler_root_Docker_lock_lease_materialization':False,'same_current_source':str(source),'source_or_scheduler_changes':False}
with (R/'WHOLE-ACTUAL-SOURCE-VALIDATOR-RESULT.json').open('x') as out:out.write(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps(result))
