"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite source-only adaptations of retained CURRENT109 validators and v2 runner.
No compiler, configure, Docker, guest, Root operation or source materialization.
"""
from pathlib import Path
import ast, copy, difflib, hashlib, json
D=Path(__file__).resolve().parent;P=D.parent;E=P.parent
Q=E/'qualified-current26eb-next-default-source-1'
A=E/'ROOT-CURRENT109-NEXT-DEFAULT-BUILD-ADMISSION-1'
V2=E/'operation-account-window-new12h-source-1/actual-guardian-clamp-successor-1/actual_account_window_v2.py'
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(p):return json.loads(p.read_text())
def write(name,value):
 path=D/name;path.parent.mkdir(parents=True,exist_ok=True)
 raw=value if isinstance(value,str) else json.dumps(value,indent=2)+'\n'
 with path.open('x') as stream:stream.write(raw)
def one(text,a,b):
 assert text.count(a)==1,(a[:100],text.count(a))
 return text.replace(a,b,1)
oldinputs=read(Q/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json');inputs=copy.deepcopy(oldinputs)
profile=read(P/'PROFILE.SOURCE-ONLY.json')
inputs.update(status='FROZEN_CURRENT110_SIX_CALLBACK_IDLE116_EXPECTATIONS_NOT_ACCEPTANCE',
 profile_template=ref(P/'PROFILE.SOURCE-ONLY.json'),source_plan=ref(P/'EXACT-FIVE-COMMAND-PROPOSAL.NOT-GRANTED.json'),
 prior_accepted_artifact=ref(E/'CURRENT109-INDEPENDENT-DEFAULT-ARTIFACT-ACCEPTANCE.json'),
 prior_accepted_producer=ref(A/'OUTPUT/work/evidence/producer-contract.json'))
extra=['perf_event_alloc_kmalloc_bridge','perf_event_alloc_free_bridge','perf_event_alloc_hw_init_bridge',
 'arch_rt_sigreturn_syscall_bridge','arch_rt_sigreturn_set_signal_bridge','arch_rt_sigreturn_check_signal_bridge']
inputs['all_Rust_exports']+=extra;assert len(inputs['all_Rust_exports'])==45
inputs['carried_forward_Rust_exports']=oldinputs['all_Rust_exports'];inputs['new_unique_Rust_exports']=extra
for token,removed in [('CMakeFiles/mckernel.img.dir/syscall.c.o',extra[:3]),('CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o',extra[3:])]:
 row=next(r for r in profile['inputs']['objects'] if r['link_token']==token)
 baseline=oldinputs['expected_C_function_sets'][token]['expected_remaining_names']
 inputs['baseline_C_objects'][token]=dict(object=row['source'],allocated_FUNC_count=len(baseline),all_names=baseline)
 inputs['expected_C_function_sets'][token]=dict(remove=sorted(removed),expected_remaining_names=sorted(set(baseline)-set(removed)))
idle=['process_idle_offsets','process_idle_values']
assert set(idle)<=set(inputs['expected_new_undefined'])
inputs['expected_new_undefined']=sorted(set(inputs['expected_new_undefined'])-set(idle))
inputs['exact_undefined_delta']=dict(removed=idle,added=[],all_other_provider_witnesses_exact=True)
inputs['cumulative_seed_undefined_removed']=sorted(set(inputs['cumulative_seed_undefined_removed'])|set(idle))
inputs['process_expected_OBJECT_count']=68
inputs['process_compile_disposition']=profile['producer_contract']['process_delta']
inputs['current110_actual_baseline']=ref(E/'CURRENT109-INDEPENDENT-DEFAULT-ARTIFACT-ACCEPTANCE.json')
inputs['current110_baseline_Rust']=ref(A/'OUTPUT/work/output/build/kernel/rust/mckernel_rust.o')
inputs['current110_baseline_image']=ref(A/'OUTPUT/work/output/build/kernel/mckernel.img')
inputs['current110_baseline_process']=ref(A/'OUTPUT/work/output/build/kernel/CMakeFiles/mckernel.img.dir/process.c.o')
idle_source=E/'f02-idle-layout-values-next-current-source-1'
idle_tables=read(idle_source/'SOURCE-IMPLEMENTATION-AND-CURRENT-IDLE-TABLES.json')['actual_tables']
inputs['idle116']=dict(tables=idle_tables,HOST=ref(idle_source/'HOST-output-proposed-1/IDLE-DATA-OWNERSHIP.json'),
 HOST_Rust_object=ref(idle_source/'HOST-output-proposed-1/idle.o'),
 ABI_assertions=ref(idle_source/'fixture/genuine_idle_ABI.c'),
 source_implementation=ref(idle_source/'SOURCE-IMPLEMENTATION-AND-CURRENT-IDLE-TABLES.json'))
write('ACCEPTANCE-INPUTS.SOURCE-ONLY.json',inputs)
templates={}
oldstatic=str(Q);newstatic=str(D)
for path in sorted((Q/'validator-templates').glob('*.py')):
 if path.name in ['profile_clone_witness.py','narrow_f02_alias_identity.py']:continue
 text=path.read_text().replace(oldstatic,newstatic)
 if path.name=='qualify_next_providers.py':
  text=one(text,"P['unchanged_completed_process_prefix']['Root_decision']","P['producer_contract']['process_delta']")
  text=text.replace('actual_thirty_nine_Rust_exports','actual_forty_five_Rust_exports').replace('39_RUST_EXPORTS','45_RUST_EXPORTS')
 if path.name=='qualify_retained_f02_owners.py':
  text=text.replace('len(newmeta)==70','len(newmeta)==68')
  text=text.replace("FOUR+THIRTEEN+['process_timer_runtime_offsets']","FOUR+THIRTEEN+['process_timer_runtime_offsets','process_idle_offsets','process_idle_values']")
  text=text.replace('new_allocated_OBJECTs=70','new_allocated_OBJECTs=68').replace('all_70_binding_type_size','all_68_binding_type_size')
  text=text.replace('other_readonly_objects=24','other_readonly_objects=22').replace('_70_PROCESS_METADATA','_68_PROCESS_METADATA')
 ast.parse(text,filename=path.name)
 write('validator-templates/'+path.name,text)
 write('diffs/'+path.name+'.diff',''.join(difflib.unified_diff(path.read_text().splitlines(keepends=True),text.splitlines(keepends=True),fromfile=str(path),tofile=str(D/'validator-templates'/path.name))))
 templates[path.name]=dict(parent=ref(path),template_sha256=hashlib.sha256(text.encode()).hexdigest())
manifest=read(Q/'VALIDATOR-TEMPLATE-SOURCES.json')
write('VALIDATOR-TEMPLATE-SOURCES.json',dict(scope=inputs['scope'],runtime_authority=None,
 status='CURRENT110_EXACT_SOURCE_BOUND_VALIDATOR_ADAPTATION',templates=templates,
 unchanged_helpers=manifest['unchanged_helpers'],predecessor_manifest=ref(Q/'VALIDATOR-TEMPLATE-SOURCES.json')))

# Same actual preflight/acceptance path; only finite source layout/count updates.
text=(Q/'qualify_produced_cohort.py').read_text()
text=one(text,'D=Path(__file__).resolve().parent;E=D.parent','D=Path(__file__).resolve().parent;E=D.parents[1]')
text=text.replace(str(Q),str(D))
text=text.replace("frozen=json.loads((D/'PROFILE.SOURCE-ONLY.json').read_text())","frozen=json.loads((D.parent/'PROFILE.SOURCE-ONLY.json').read_text())")
text=text.replace('actual_thirty_nine_Rust_exports','actual_forty_five_Rust_exports')
text=one(text,"'qualify_retained_f02_owners.py','qualify_host13_storage.py'","'qualify_retained_f02_owners.py','qualify_host13_storage.py','qualify_idle116_and_inherited_consumers.py'")
text=one(text,"'CURRENT-NARROW-ALIAS-IDENTITY-GATE.json']","'CURRENT-NARROW-ALIAS-IDENTITY-GATE.json','IDLE116-AND-INHERITED-CONSUMERS.json']")
write('qualify_produced_cohort.py',text)
write('diffs/qualify_produced_cohort.py.diff',''.join(difflib.unified_diff((Q/'qualify_produced_cohort.py').read_text().splitlines(keepends=True),text.splitlines(keepends=True),fromfile=str(Q/'qualify_produced_cohort.py'),tofile=str(D/'qualify_produced_cohort.py'))))
write('literal_import_probe.py',(Q/'literal_import_probe.py').read_text())
write('check_thirteen_storage.py',(Q/'check_thirteen_storage.py').read_text())
# HOST13's retained reader hash remains exact under the new literal location.
assert inputs['HOST13_storage_reader']['sha256']==ref(D/'check_thirteen_storage.py')['sha256']
inputs['HOST13_storage_reader']=ref(D/'check_thirteen_storage.py')
# The source inputs file has not been granted/published; bind its final literal reader path.
(D/'ACCEPTANCE-INPUTS.SOURCE-ONLY.json').write_text(json.dumps(inputs,indent=2)+'\n')

# v2 itself retains the reviewed account semantics and clamps live guardian data.
runner=(P/'run_build_only.py').read_text()
v1=E/'operation-account-window-new12h-source-1/actual_account_window.py'
runner=runner.replace(str(v1),str(V2)).replace(repr(ref(v1)),repr(ref(V2)))
assert 'actual_account_window_v2.py' in runner and repr(ref(V2)) in runner
write('run_build_only.py',runner)
write('diffs/run_build_only.py.diff',''.join(difflib.unified_diff((P/'run_build_only.py').read_text().splitlines(keepends=True),runner.splitlines(keepends=True),fromfile=str(P/'run_build_only.py'),tofile=str(D/'run_build_only.py'))))
for name in ['build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py']:
 write(name,(P/name).read_text())
print(json.dumps(dict(status='PREPARED_SOURCE_ONLY',templates=len(templates),Rust_exports=45,process_objects=68,C_functions=94,v2guard=ref(V2))))
