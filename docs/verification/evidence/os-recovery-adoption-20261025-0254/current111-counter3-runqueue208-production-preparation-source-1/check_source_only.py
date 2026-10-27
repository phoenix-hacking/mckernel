"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source/reference checks; never call execute, guard, materializer or publication.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path

D=Path(__file__).resolve().parent
E=D.parent

def read(p):return json.loads(p.read_text())
def ref(p):
    p=Path(p);raw=p.read_bytes()
    return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def checked(row):assert ref(row['path'])==row
p=read(D/'PROFILE.SOURCE-ONLY.json'); prior=read(E/'ROOT-CURRENT110-HOST19-BUILD-ADMISSION-1/PROFILE.SOURCE-ONLY.json')
assert p['runtime_authority'] is None
assert all(p[k] is None for k in ['request_sha256','actual_nonce','actual_root_adoption','actual_execution_review','actual_resource_authority','actual_output_root','actual_holder','native_custody_clearance'])
assert p['fixed_three_clock_cutoffs']==[1793165769.0,947874.5689514667,963213.6960030915]
assert p['aggregate_memory_budget_bytes']==23259332608
for key in ['CPU','memory_bytes','pids','maximum_wall_seconds','execution_mode','docker_client_prefix']:
    assert p[key]==prior[key]
for key in ['image','source6153','retained_seed','configuration','toolchain_mounts','toolchain_manifest','toolchain_lock_sha256']:
    assert p['inputs'][key]==prior['inputs'][key]
for row in p['inputs']['objects']: checked(row['source'])
for row in p['inputs']['configuration']:checked(row['source'])
for row in p['inputs']['postimages']:checked(row['postimage'])
m=read(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json')
assert len(m['files'])==112
for row in m['files']:checked(row['snapshot'])
assert {str(x.relative_to(D/'rust-subtree')) for x in (D/'rust-subtree').rglob('*') if x.is_file()}=={r['relative'] for r in m['files']}
commands=p['exact_commands'];assert len(commands)==4
assert commands[0]['argv'].count('f03_perf_counter_control_bridges_selected_candidate')==1
assert commands[2]['argv'].count('-DMCKERNEL_RUST_F03_PERF_COUNTER_CONTROL_BRIDGES')==1
assert commands[1]==prior['exact_commands'][1] and commands[3]==prior['exact_commands'][4]
assert commands[0]['argv']==prior['exact_commands'][0]['argv'][:-2]+['--cfg','f03_perf_counter_control_bridges_selected_candidate']+prior['exact_commands'][0]['argv'][-2:]
ns={'__file__':str(D/'run_build_only.py'),'__name__':'source_check_only'}
exec(compile((D/'run_build_only.py').read_text(),ns['__file__'],'exec'),ns)
# Literal in-memory sentinel is neither saved nor used as Root authority.
q=copy.deepcopy(p);q['request_sha256']='0'*64
assert ns['commands_for_plan'](q)==commands
failures=[]
for label,mutate in [
 ('missing_Root_request',lambda x:x.update(request_sha256=None)),
 ('replayed_arch_compile',lambda x:x['exact_commands'].insert(3,prior['exact_commands'][3])),
 ('wrong_output',lambda x:x['exact_commands'][1].update(new_output='/work/output/build/old.o')),
 ('arch_marked_rebuild',lambda x:next(r for r in x['inputs']['objects'] if r['build_relative'].endswith('/arch/x86_64/kernel/syscall.c.o')).update(replace=True)),
 ('changed_Rust_binding',lambda x:x['cohort_source_bindings'].pop()),
]:
    bad=copy.deepcopy(q);mutate(bad)
    try:ns['commands_for_plan'](bad)
    except RuntimeError as error:failures.append(dict(control=label,rejected=str(error)))
    else:raise AssertionError('negative control accepted: '+label)
for name in ['prepare_source.py','run_build_only.py','build_only_worker.py','hold_and_run_build_only.py','publish_approved_ready.py','check_source_only.py']:
    ast.parse((D/name).read_text(),filename=name)
result=dict(scope=p['scope'],status='PASS_SOURCE_ONLY_NO_EXECUTION_AUTHORITY',profile=ref(D/'PROFILE.SOURCE-ONLY.json'),closed_Rust_sources=112,actual_compilers=0,actual_workloads=0,commands=4,changed_objects=3,retained_objects=8,source_reference_checks=True,original_profile_resource_and_toolchain_fields_unchanged=True,exact_command_derivation=True,positive_commands_for_plan=True,negative_controls=failures,AST_only_tools=6,execution_guard_called=False,Root_authority_minted=False,limits='Pure in-memory/reference checks, not actual admission, compiler, default/native or whole-file acceptance.')
with (D/'SOURCE-ONLY-CHECK-RESULT.json').open('x') as stream:stream.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
