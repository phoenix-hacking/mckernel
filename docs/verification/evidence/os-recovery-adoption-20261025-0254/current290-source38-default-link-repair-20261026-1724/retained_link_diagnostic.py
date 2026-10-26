"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only retained default link diagnosis. Never imports/executes an owner driver.
"""
import ast,json,shlex,subprocess
from pathlib import Path
ROOT=Path('/home/holden/mckernel')
BASE=ROOT/'docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt3-coherent-entry-preparation-source-1/genuine-newbe87-physical-binding-preparation-source-1/actual7553-namespace6294-final-source-1/memory-floor-correction1-source-1/query-packet-pin-correction1-source-1/default290-link-data-selector-correction1-source-1/minimal-selected-default-readonly-overlay-and-seed-plan-1/implementation-source-1/exact-consumed-gitlink-view-correction1-source-1/fresh-compiled-object-ownership-gate-source-1'
DRIVER=BASE/'native_rust_exact_mckernel_image_offline.CURRENT290.VIEW-AND-FRESH-OBJECT-GATE.py'
for node in ast.parse(DRIVER.read_text()).body:
    if isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='_REUSE_FIXED' for t in node.targets):
        fixed=json.loads(ast.literal_eval(node.value.args[0]));break
else: raise RuntimeError('missing literal fixed recipe')
c=fixed['commands']
original=shlex.split(c['process_command_selected_original']['command'])
new=c['process_command_expected_argv']
macro='-DMCKERNEL_RUST_PROCESS_GLOBAL_STORAGE'
assert new.count(macro)==1 and macro not in original
assert [x for x in new if x!=macro]==original
assert len(fixed['objects'])==11
assert sum(not x['replace'] for x in fixed['objects'])==9
assert sum(x['replace'] for x in fixed['objects'])==2
assert shlex.split(Path(c['link_actual_default']['path']).read_text())==c['link_argv']
assert '--gc-sections' not in c['link_argv']
# Examine global symbols only; this does not execute/link a retained workload.
def symbols(path):
    r=subprocess.run(['/usr/bin/nm','-g',str(path)],text=True,capture_output=True,check=True)
    result={}
    for line in r.stdout.splitlines():
        v=line.split()
        if len(v)>=2: result[v[-1]]=v[-2]
    return result
providers={n:[] for n in ('resource_set_list','resource_set_lock','runq_reservation_lock')}
for row in fixed['objects']:
    syms=symbols(row['source']['path'])
    for name in providers:
        if syms.get(name) in ('B','D','R','S','G'): providers[name].append(row['build_relative'])
assert all(len(v)==2 for v in providers.values()),providers
corrected=ROOT/'docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/kernel-syscall/default290-corrected-real-crate-source-1/output-1/actual-default-corrected-rust.o'
if not corrected.exists():
    candidates=list(corrected.parent.glob('*.o'))
    assert len(candidates)==1,candidates
    corrected=candidates[0]
syms=symbols(corrected)
assert not any(('panic_const_div_by_zero' in k or 'panic_const_div_overflow' in k) and v=='U' for k,v in syms.items())
assert all(syms.get(n) in ('B','D') for n in providers)
report={'scope':__doc__.splitlines()[0], 'status':'PASS_RETAINED_INPUT_DIAGNOSTIC_ONLY',
 'diagnostic_delta':'Cross-binds retained exact 11-object link and 9 reuse/2 replacement plan with the prepared one-flag process command and corrected whole-Rust object.',
 'original_duplicate_global_providers':providers,'corrected_Rust_object':str(corrected),
 'two_original_division_panic_imports_absent':True,'process_command_only_delta':macro,
 'retained_object_reuse_count':9,'required_new_object_count':2,
 'exact_next_container_cwd':c['container_cwd'],'exact_next_process_argv':new,
 'exact_next_Rust_command':c['Rust_actual_default_command'],'exact_next_raw_link_argv':c['link_argv'],
 'source6153_mutations':0,'SDK21_replays':0,'compiler_or_link_commands_executed':0,
 'Source38_GNU_RETAIN':'OPEN; no waiver, masking, retention or GC credit',
 'blocker':'retained root1060806/parent1060803 custody and positive physical reconciliation; fresh actual workload admission required before selected GCC14 process+Rust/raw-link execution',
 'default_native_file_closures':0}
Path(__file__).with_name('RESULT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ('status','retained_object_reuse_count','required_new_object_count','two_original_division_panic_imports_absent','process_command_only_delta','compiler_or_link_commands_executed','blocker')}))
