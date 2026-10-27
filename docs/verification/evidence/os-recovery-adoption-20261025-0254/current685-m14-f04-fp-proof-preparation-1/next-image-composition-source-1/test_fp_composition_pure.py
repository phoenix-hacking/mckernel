"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure packet constraints and exact existing trace/BEGIN validator controls.
No image/materialization/mock guest/compiler/nonce/clock/runtime invocation.
"""
from pathlib import Path
import ast,copy,hashlib,json,re
import stage_next10_fp_specific as adapter
HERE=Path(__file__).resolve().parent
assert hashlib.sha256((HERE/'FROZEN-FP-COMPOSITION.json').read_bytes()).hexdigest()==adapter.FROZEN_SHA
cfg=json.loads((HERE/'FROZEN-FP-COMPOSITION.json').read_text());source=json.loads((HERE/'NEXT10-FP-STAGING-INPUTS.SOURCE-ONLY.json').read_text());rows=[]
def record(name,call,success):
    try:call();passed=True;error=None
    except (ValueError,KeyError,TypeError) as exc:passed=False;error=str(exc)
    rows.append({'case':name,'accepted':passed,'expected':success,'error':error})
    assert passed==success,rows[-1]
record('unbound_NEXT10_source_packet',lambda:adapter.validate(cfg,source),True)
record('unbound_NEXT10_cannot_stage',lambda:adapter.validate(cfg,source,final=True),False)
# Synthetic references exercise only pure shape/binding logic. No files exist,
# no accepted image/review is inferred, and the real packet remains imageNULL.
model=copy.deepcopy(source)
def dummy(path,digest):return {'path':path,'size':1,'sha256':digest,'mode':0o100600}
model['NEXT10_image']=dummy('/MODEL_ONLY/NEXT10/mckernel.img','a'*64)
model['image_qualification']={'record':dummy('/MODEL_ONLY/image-review.json','b'*64),'image_sha256':'a'*64}
model['stage_review']=dummy('/MODEL_ONLY/stage-review.json','c'*64)
record('final_model_data_shape_only',lambda:adapter.validate(cfg,model,final=True),True)
def mutate(name,edit):
    d=copy.deepcopy(model);edit(d);record(name,lambda:adapter.validate(cfg,d,final=True),False)
mutate('image_NULL',lambda d:d.__setitem__('NEXT10_image',None))
mutate('image_relative_path',lambda d:d['NEXT10_image'].__setitem__('path','relative.img'))
mutate('image_parent_path',lambda d:d['NEXT10_image'].__setitem__('path','/x/../old.img'))
mutate('image_nonregular',lambda d:d['NEXT10_image'].__setitem__('mode',0o040700))
mutate('current685_not_NEXT10',lambda d:d['NEXT10_image'].__setitem__('sha256',cfg['disallowed_image_sha256'][1]))
mutate('old_FP_image_not_NEXT10',lambda d:d['NEXT10_image'].__setitem__('sha256',cfg['disallowed_image_sha256'][0]))
mutate('qualification_wrong_image',lambda d:d['image_qualification'].__setitem__('image_sha256','d'*64))
mutate('missing_image_qualification',lambda d:d.__setitem__('image_qualification',None))
mutate('missing_stage_review',lambda d:d.__setitem__('stage_review',None))
mutate('wrong_output_path',lambda d:d.__setitem__('output_directory','/MODEL_ONLY/elsewhere'))
mutate('module_pair_change',lambda d:d['protected']['modules'][2].__setitem__('sha256','d'*64))
mutate('module_path_change',lambda d:d['protected']['modules'][1].__setitem__('path','/other/smp.ko'))
mutate('payload_binary_change',lambda d:d['protected']['payload'].__setitem__('sha256','d'*64))
mutate('launcher_change',lambda d:d['protected']['launcher'].__setitem__('sha256','d'*64))
mutate('collector_change',lambda d:d['protected']['collector'].__setitem__('sha256','d'*64))
mutate('oracle_stdout_changed',lambda d:d['protected']['payload_contract']['oracle'].__setitem__('stdout_hex',''))
mutate('oracle_exit77_as_success',lambda d:d['protected']['payload_contract']['oracle'].__setitem__('exit_code',77))
mutate('argv_threads_expanded',lambda d:d['protected']['payload_contract']['argv'].__setitem__(2,'2'))
mutate('profile_resource_expansion',lambda d:d['protected']['profile'].__setitem__('memory_mib',16384))
mutate('bootstrap_no_oversubscribe',lambda d:d['protected']['source_capability'].__setitem__('boot_argv',['/bin/native-boot']))
mutate('AVX_requirement_weakened',lambda d:d['protected']['fp_requirements'].__setitem__('AVX','optional'))
mutate('bootstrap_provenance_overclaimed',lambda d:d['protected']['source_capability'].__setitem__('native_boot_provenance_limit','exact compiler receipt proved'))
mutate('AVX_runtime_capability_invented',lambda d:d['protected']['fp_requirements'].__setitem__('runtime_AVX_already_passed',True))
mutate('rounds_reduced',lambda d:d['protected']['fp_requirements'].__setitem__('rounds_each',1))
mutate('real_thread_count_reduced',lambda d:d['protected']['fp_requirements'].__setitem__('real_std_worker_threads',1))
mutate('BEGIN_not_required',lambda d:d['protected']['postrun_constraints'].__setitem__('positive_BEGIN_ack_and_retirement',False))
mutate('normal_cleanup_not_required',lambda d:d['protected']['postrun_constraints'].__setitem__('normal_owner_cleanup_and_positive_physical_retirement',False))
mutate('FP_threads_as_fork_projection',lambda d:d['protected']['postrun_constraints'].__setitem__('trace_child_domain',True))
mutate('daemon_repair_bypassed',lambda d:d['protected']['postrun_constraints'].__setitem__('daemon_repair_qualified_before_guest',False))
mutate('nonce_staged',lambda d:d.__setitem__('nonce','MODEL_ONLY_NOT_A_RUNTIME_NONCE'))
mutate('runtime_authority_staged',lambda d:d.__setitem__('runtime_authority',{}))
# Execute only four unchanged pure definitions from exact pinned existing
# diagnostic source. No module imports, clock/backend/owner code or new oracle.
nd=cfg['protected']['diagnostic_module'];raw=Path(nd['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==nd['sha256']
names={'DiagnosticError','_need','_check_begin_cleanup','_check_syscall_trace'}
nodes=[n for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
assert {n.name for n in nodes}==names
ns={'re':re};exec(compile(ast.Module(body=nodes,type_ignores=[]),nd['path']+':EXACT_PURE_TRACE_BEGIN','exec'),ns)
prefix='os=0 generation=1 pid=7'
lines=[
'application_syscall=delivered '+prefix+' worker=1 delivery=1 cpu=0 number=39',
'application_syscall=return_route '+prefix+' worker=1 delivery=1 launcher_cpu=1 guest_cpu=0',
'application_syscall=returned '+prefix+' worker=1 delivery=1 cpu=0 value=7',
'application_syscall=delivered '+prefix+' worker=2 delivery=1 cpu=0 number=39',
'application_syscall=returned '+prefix+' worker=2 delivery=1 cpu=0 value=7',
'application_syscall=delivered '+prefix+' worker=1 delivery=2 cpu=0 number=231',
'application_process=cleanup_requested '+prefix+' intent_errno=0',
'application cleanup ACK '+prefix+' token=11 errno=0 abandoned=0',
'application retirement '+prefix+' token=12 errno=0']
serial='\n'.join(lines)
def trace(text):return ns['_check_syscall_trace'](text,prefix,begin_cleanup=True,child_domain=False)
record('existing_trace_positive_BEGIN_control',lambda:trace(serial),True)
record('existing_trace_missing_ACK_rejected',lambda:trace('\n'.join(x for x in lines if 'cleanup ACK' not in x)),False)
record('existing_trace_ACK_zero_token_rejected',lambda:trace(serial.replace('token=11 errno=0','token=0 errno=0')),False)
record('existing_trace_ACK_errno_rejected',lambda:trace(serial.replace('token=11 errno=0','token=11 errno=-5')),False)
record('existing_trace_retirement_errno_rejected',lambda:trace(serial.replace('token=12 errno=0','token=12 errno=-11')),False)
record('existing_trace_foreign_pid_rejected',lambda:trace(serial.replace('worker=2 delivery=1 cpu=0 number=39','worker=2 delivery=1 cpu=0 number=39')+'\napplication_syscall=delivered os=0 generation=1 pid=8 worker=3 delivery=1 cpu=0 number=39'),False)
record('existing_trace_non_group_exit_rejected',lambda:trace(serial.replace('number=231','number=60')),False)
record('existing_trace_incomplete_RET_rejected',lambda:trace('\n'.join(x for x in lines if 'returned' not in x)),False)
assert not Path(cfg['output_directory']).exists()
assert source['NEXT10_image'] is None and source['image_qualification'] is None and source['stage_review'] is None
result={'scope':cfg['scope'],'status':'PASS_PURE_FP_COMPOSITION_AND_UNCHANGED_TRACE_BEGIN_CONTROLS_ONLY','cases':len(rows),'rows':rows,'exact_existing_trace_source':nd,'adapter_sha256':hashlib.sha256((HERE/'stage_next10_fp_specific.py').read_bytes()).hexdigest(),'NEXT10_image':None,'materialization_actions':0,'guest_compiler_clock_nonce_grant_actions':0,'normal_cleanup_limit':'Only the mandatory unchanged owner-normal-retirement contract is guarded here; actual daemon/owner/cgroup/physical proof remains Root runtime prerequisite, not simulated or claimed.','AVX_limit':'Purecontract/sourceguard only; actualCPUID/XCR0 probe occurs only in unchangedpayload on eventualnative run. No runtime capability asserted.'}
(HERE/'PURE-FOCUSED-CONTROLS.RESULT.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'status':result['status'],'cases':len(rows),'NEXT10_image':None,'materialization_actions':0},indent=2))
