"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure resource boundaries and literal prepared-validator controls; no live observer.
"""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json,struct
D=Path(__file__).resolve().parent
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
c=load('current110_pure_resource_helpers',D/'capture_resources.py')
baseline=dict(memory={'MemAvailable':32<<30},capacity={'host':20<<30,'scratch':14091616256},
 other_memory=6<<30,other_pids=0,aggregate_pids=1024,threads=1000,thread_limit=10000)
assert c.valid_resource_facts(**baseline)
cases=1
for key,value in [('other_memory',c.AGGREGATE-(12<<30)+1),('memory',{'MemAvailable':(22<<30)-1}),
 ('capacity',{'host':(16<<30)-1,'scratch':14091616256}),('capacity',{'host':20<<30,'scratch':14091616255}),
 ('other_pids',513),('threads',10000)]:
 row=copy.deepcopy(baseline);row[key]=value
 try:c.valid_resource_facts(**row)
 except AssertionError:cases+=1
 else:raise AssertionError(('resource negative unexpectedly passed',key))
inputs=json.loads((D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json').read_text())
assert len(inputs['all_Rust_exports'])==45 and len(set(inputs['all_Rust_exports']))==45
assert [len(inputs['expected_C_function_sets'][token]['expected_remaining_names']) for token in ['CMakeFiles/mckernel.img.dir/syscall.c.o','CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o']]==[69,25]
assert inputs['process_expected_OBJECT_count']==68
assert inputs['exact_undefined_delta']==dict(removed=['process_idle_offsets','process_idle_values'],added=[],all_other_provider_witnesses_exact=True)
assert [r['bytes'] for r in inputs['idle116']['tables']]==[80,36]
manifest=json.loads((D/'VALIDATOR-TEMPLATE-SOURCES.json').read_text())
for name,row in manifest['templates'].items():
 raw=(D/'validator-templates'/name).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['template_sha256'];ast.parse(raw)
assert len(manifest['templates'])==7
runner=(D/'run_build_only.py').read_text()
assert "'sha256': '1f152e3f18384643cd35d203fcc2a4292950a1c90758734859bdb980cf45fda0'" in runner
assert '/actual-guardian-clamp-successor-1/actual_account_window_v2.py' in runner
assert "'sha256': '8bf26bae56a019876c6a1463945733c85be5016d21ac5f6f955c29fd131a8cbe'" not in runner
for name in ['run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py','capture_resources.py','materialize_admission.py','check_postbuild_current.py','qualify_produced_cohort.py']:
 ast.parse((D/name).read_text(),filename=name)
# Exercise only the exact final-relocation patch predicate using inert fake bytes.
source=(D/'validator-templates/qualify_idle116_and_inherited_consumers.py').read_text();tree=ast.parse(source)
node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='patched_final')
raw=bytes(16);rel=[dict(offset=4,type=1,addend=3,target={'name':'actual_target'})]
namespace=dict(struct=struct,object_bytes=lambda elf,sym:raw,relocs=lambda elf,sym:rel)
exec(compile(ast.Module(body=[node],type_ignores=[]),'exact-final-patch-pure-test','exec'),namespace)
fn=dict(name='consumer',size=16,type=2);target=dict(name='actual_target',value=0x123400,shndx=1)
def symbol(name):return target if name=='actual_target' else fn
expected=bytearray(raw);struct.pack_into('<Q',expected,4,target['value']+3)
assert len(namespace['patched_final'](None,fn,symbol,lambda sym:bytes(expected)))==1
patchcases=1
for badrel,badbytes in [([dict(offset=4,type=2,addend=3,target={'name':'actual_target'})],bytes(expected)),
 ([dict(offset=4,type=1,addend=3,target={'name':''})],bytes(expected)),(rel,bytes(16)),
 ([dict(offset=4,type=1,addend=3,target={'name':'actual_target'}),dict(offset=8,type=1,addend=0,target={'name':'actual_target'})],bytes(expected))]:
 namespace['relocs']=lambda elf,sym,rs=badrel:rs
 try:namespace['patched_final'](None,fn,symbol,lambda sym,bs=badbytes:bs)
 except AssertionError:patchcases+=1
 else:raise AssertionError('invalid current relocation/final bytes accepted')
print(json.dumps(dict(status='PASS_PURE_CURRENT110_CONTROLS',resource_cases=cases,final_relocation_patch_cases=patchcases,
 validator_templates=7,expected_Rust_exports=45,expected_C_functions=94,expected_process_objects=68,
 expected_idle_bytes=116,live_guard=False,physical_observer=False,Docker=False,compiler=False,artifact_gates=False)))
