"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Seal existing119 producer DATA/source only after Root has genuine fresh origin and
control/current-free bindings. Does not generate origin, import guards or execute.
"""
from pathlib import Path
import argparse,ast,copy,json,math,re
import importlib.util
import accepted_bindings as accepted
HERE=Path(__file__).resolve().parent
TEMPLATES=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/CURRENT119-JOINT-M14-REGISTRY-REPAIR-SOURCE-1/m14-exclusive-producer-binding-1')
base_path=TEMPLATES/'prepare_current119_binding.py'
spec=importlib.util.spec_from_file_location('frozen_current119_binding_data',base_path)
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
JOINT,E,OLD,SCOPE,ref,auth,read=base.JOINT,base.E,base.OLD,base.SCOPE,base.ref,base.auth,base.read
def write(name,value):
 with (HERE/name).open('x')as stream:stream.write(value if isinstance(value,str)else json.dumps(value,indent=2)+'\n')
NEWSC=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1')
INITIAL=NEWSC/'EARLIEST-CONTROL-CAPS.json'


def cutoffs(values,armed,bootstrap):
 minimum=accepted.weekly_limits(armed,bootstrap)
 accepted.CUTOFF.validate_monotone_cutoffs(minimum,values)
 assert values==minimum,'one identical earliest original/bootstrap/actual-armed triplet'
 return minimum

def origin(directory,receipt):
 path=Path(directory);assert path.is_absolute() and path.is_dir()
 names=['f06_rt_sigreturn_origin.h','f06_clone_cpuid_metadata.rs','ORIGIN-BINDING.json','rust-environment.json','f06_rt_sigreturn_origin.cmake']
 rows={name:ref(path/name)for name in names}
 binding=read(path/'ORIGIN-BINDING.json');source=ref(Path('/home/holden/mckernel/arch/x86_64/kernel/syscall.c'));profile=ref(Path('/home/holden/mckernel/scripts/f06_origin_command_profile.json'));profile_data=read(profile['path'])
 assert profile['sha256']=='49dba5414cae3d4f7aff20d6d90c1554bc75630d461885bdda650f468ff003d1'
 assert source['sha256']=='b5e9a382491d0f6dc4b71a55f54f76f3d4ca610fa9f81adc60e70ec97a194669'
 assert binding['profile_sha256']==profile['sha256'] and binding['source_sha256']==source['sha256'] and binding['source_path']==source['path'] and binding['origin_utf8']=='/src/arch/x86_64/kernel/syscall.c','genuine119 changed-source origin, never old118'
 command=read(JOINT/'CURRENT119-FOUR-COMMANDS.NOT-GRANTED.json')['ordered_commands'][2]
 assert binding['command']['argv']==command['argv'] and binding['command']['cwd']==command['cwd']
 assert binding['clone_cpuid_debug_slots']==profile_data['clone_cpuid_origin_reference']['retained_C_metadata']
 actual=read(auth(receipt));assert actual['author']=='/root' and actual['returncode']==0 and actual['child_positive_join']is True and actual['closed_streams']is True and actual['source_generation_only']is True and actual['compiler']is False and actual['runtime_authority']is None
 assert actual['argv']==['/usr/bin/python3','-B','/home/holden/mckernel/scripts/derive_f06_origin.py','--profile',profile['path'],'--source',source['path'],'--output',str(path)]
 assert actual['outputs']==[rows[name]for name in names]
 return dict(actual_origin_producer=receipt,actual_generated_header=rows[names[0]],actual_generated_metadata=rows[names[1]],actual_origin_binding=rows[names[2]],actual_Rust_environment=rows[names[3]],actual_CMake_origin=rows[names[4]])

def validate_root(q):
 assert set(q)=={'author','decision','runtime_authority','request','nonce','current_free','current_ledger','current_bindings','runtime_guard','runtime_guard_source_review','origin_directory','origin_receipt','armed_controls','control_bundle','cutoffs'}
 assert q['author']=='/root' and q['decision']=='BIND_CURRENT119_PRODUCER_SOURCE_INPUTS_ONLY' and q['runtime_authority']is None
 for key in ['request','current_free','current_ledger','current_bindings','runtime_guard','runtime_guard_source_review','origin_receipt','armed_controls','control_bundle']:auth(q[key])
 assert q['armed_controls']['path']==str(NEWSC/'ACTUAL-CONTROLS-ARMED.json'),'real new control receipt, not historical4889'
 free=read(auth(q['current_free']));ledger=read(auth(q['current_ledger']))
 accepted.accepted_metadata(q,free,ledger)
 # Full existing pure d216 validation additionally authenticates all72/native
 # history, actual retirement/capture/positive joins and Root65 boundary/schema.
 accepted.accepted_chain(q)
 assert re.fullmatch('[0-9a-f]{32}',q['nonce']) and q['nonce']!='e984210ca59641b299cf42d392eb953b'
 assert q['nonce']not in ledger['consumed_nonces']+ledger['reserved_abandoned_unconsumed_nonces']
 assert q['runtime_guard']['sha256']!='a3b53520ab34929d6fab13caea6afaa1364ef4209b191ffbb63bfa93595ac208','consumed A3 guard cannot be replayed'
 tree=ast.parse(auth(q['runtime_guard']).read_bytes());assert any(isinstance(n,ast.FunctionDef)and n.name=='guard'and not n.args.args for n in tree.body)
 accepted.review_binds_guard(read(auth(q['runtime_guard_source_review'])),q['runtime_guard'])
 bundle=read(auth(q['control_bundle']));assert bundle['armed']==q['armed_controls']
 for key,relative in [('config','armed-controller/CONFIG.json'),('packet','armed-controller/FROZEN-PACKET.json'),('bridge','armed-controller/bridge-start.json')]:
  assert bundle[key]['path']==str(NEWSC/relative);auth(bundle[key])
 armed=read(auth(q['armed_controls']));config=read(auth(bundle['config']));bootstrap=read(INITIAL)
 state=read(accepted.STATE)
 assert state['phase']=='running' and state['goal']['status']=='active' and config['expected_thread']==state['thread_id'],'actual current launcher thread/config'
 accepted.armed_metadata(armed,bundle['packet'],state['thread_id'],bootstrap)
 limits=cutoffs(q['cutoffs'],armed,bootstrap)
 return limits,origin(q['origin_directory'],q['origin_receipt'])

def render_sources(limits,guard_ref):
 accepted.CUTOFF.positive_triplet(limits)
 runner=(HERE/'run_build_only.corrected-template.py').read_text();old='RUNTIME_GUARD_REF=None  # Root must seal exact fresh current119 operation consumer.';assert runner.count(old)==1;runner=runner.replace(old,'RUNTIME_GUARD_REF='+repr(guard_ref))
 runner=runner.replace('DEADLINE=1793253600','DEADLINE='+repr(limits[0]))
 a=runner.index('CUTOFFS=');b=runner.index('\n',a);runner=runner[:a]+'CUTOFFS='+repr(limits)+runner[b:]
 worker=(TEMPLATES/'build_only_worker.template.py').read_text();a=worker.index('CUTOFFS=');b=worker.index('\n',a);worker=worker[:a]+'CUTOFFS='+repr(limits)+worker[b:]
 return runner,worker

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root-input',type=Path,required=True);parser.add_argument('--root-input-sha256',required=True);args=parser.parse_args()
 assert ref(args.root_input)['sha256']==args.root_input_sha256
 q=read(args.root_input);limits,generated=validate_root(q)
 profile=read(TEMPLATES/'PROFILE.TEMPLATE.SOURCE-ONLY.json');profile.update(request_sha256=q['request']['sha256'],actual_nonce=q['nonce'],native_custody_clearance=q['current_free'],fixed_three_clock_cutoffs=limits,deadline_epoch=limits[0],origin_source_materialization=generated,source_preparation_current_context=dict(current_ledger=q['current_ledger'],current_free=q['current_free'],armed_controls=q['armed_controls'],runtime_guard=q['runtime_guard'],runtime_guard_source_review=q['runtime_guard_source_review'],current_bindings=q['current_bindings'],control_bundle=q['control_bundle'],cutoffs=limits))
 profile['status']='CURRENT119_SOURCE_INPUTS_BOUND_NOT_EXECUTION_RELEASE'
 for row in profile['inputs']['postimages']:
  if row['relative'].endswith('/f06_rt_sigreturn_origin.h'):row['postimage']=generated['actual_generated_header']
  elif row['relative'].endswith('/f06_clone_cpuid_metadata.rs'):row['postimage']=generated['actual_generated_metadata']
 profile['cohort_source_bindings']=[dict(relative=r['relative'],postimage=r['postimage'])for r in profile['inputs']['postimages']]+[dict(relative='kernel/rust/'+r['relative'],postimage=r['snapshot'])for r in read(TEMPLATES/'CURRENT119-EXISTING-EXPORT-MANIFEST.json')['files']]
 runner,worker=render_sources(limits,q['runtime_guard'])
 assert not any((HERE/name).exists()for name in ['run_build_only.py','build_only_worker.py','PROFILE.SOURCE-ONLY.json','ROOT-SOURCE-BINDING.ACTUAL.json'])
 ast.parse(runner);ast.parse(worker)
 write('run_build_only.py',runner);write('build_only_worker.py',worker);write('PROFILE.SOURCE-ONLY.json',profile)
 write('ROOT-SOURCE-BINDING.ACTUAL.json',dict(scope=SCOPE,status='ROOT_EXACT_CURRENT119_SOURCE_DATA_SEALED_NOT_EXECUTION_AUTHORITY',root_input=ref(args.root_input),runner=ref(HERE/'run_build_only.py'),worker=ref(HERE/'build_only_worker.py'),profile=ref(HERE/'PROFILE.SOURCE-ONLY.json'),actual_origin=generated,runtime_guard=q['runtime_guard'],cutoffs=limits,new_compiler_or_Docker_guard_calls=0,runtime_authority=None))
 print(json.dumps(read(HERE/'ROOT-SOURCE-BINDING.ACTUAL.json')))
 # CODE/templates can be published before this source seal. Newly sealed output
 # files are published/fetched after seal and before execution review/entry.

if __name__=='__main__':main()
