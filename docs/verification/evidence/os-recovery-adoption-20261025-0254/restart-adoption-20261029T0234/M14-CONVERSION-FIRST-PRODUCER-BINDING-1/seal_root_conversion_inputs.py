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
NEWSC=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/recovery-quota-confirmation-1')
INITIAL=NEWSC/'EARLIEST-CONTROL-CAPS.json'
OLD_ROOT_INPUT={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/actual-weekly-binding-source-1/LIVE-REVALIDATION-CAP-CORRECTION-1/current119/ROOT-CURRENT119-INPUT.ACTUAL.json', 'bytes': 3783, 'sha256': '4b4fad8c6cc915a4e27c8aba79dd67cf55e7e28e67b41fa0e26daa2b1057a36c'}
ROOT68_FREE={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/CURRENT119-POSTJOIN-CURRENTFREE-PREPARATION-1/actual-acceptance-1/CURRENT-FREE.ACTUAL.json', 'bytes': 49224, 'sha256': '3fd1a6facf34a9e6ac9259526da96ddee2dd22c6032ee47b37be97e56d0086e3'}
ROOT68_LEDGER={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/ROOT68-CURRENT119-ADOPTION-1/ROOT68-NONCE-LEDGER.ACTUAL.json', 'bytes': 89874, 'sha256': 'd948ba50890c2e735bb92b541c997694154c9cf62963e748bf47f1a992b57022'}
ROOT68_BOUNDARY={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/ROOT68-CURRENT119-ADOPTION-1/ROOT68-CURRENT-BOUNDARY.ACTUAL.json', 'bytes': 1958, 'sha256': 'acebac5fd5bc97597251bff18b97518a7bf3868ad28900e59d6d56aa0d2599e3'}
ROOT68_REVIEW={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/ROOT68-CURRENT119-ADOPTION-1/independent-review-1/ADOPTION-REVIEW.ACTUAL.json', 'bytes': 3843, 'sha256': '0c9b567e31debc957a654f4098288910cd90067f1109c28370151b4391ce1789'}
CANDIDATE={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-CONVERSION-FIRST-COMPOSITION-1/SOURCE-READY.json', 'bytes': 4755, 'sha256': 'caef14198a096315e21380de49982772d8070a6489ec91d4d2f0c4d2dde3473e'}
AFFECTED={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-CONVERSION-FIRST-COMPOSITION-1/AFFECTED-UNIT-CANDIDATE-INPUTS.json', 'bytes': 30940, 'sha256': '40756e0e6bfc1606a500bf97df7a27c48bd591ecb5bb8a1008a1ed51722a5bbe'}
RECIPE={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-CONVERSION-FIRST-PRODUCER-BINDING-1/THREE-COMMANDS.SOURCE-ONLY.json', 'bytes': 19209, 'sha256': '79a0054d5771b4bdb1bade8156c77533a31d5d68b17a5c41daa31cc36947159b'}
SNAPSHOT_MAP={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-CONVERSION-FIRST-PRODUCER-BINDING-1/SNAPSHOT-INPUT-MAP.SOURCE-ONLY.json', 'bytes': 60002, 'sha256': 'd649ea41aad41037d7508f94c4d181c24ebec521f951a639458a91402f343a58'}
PROFILE119={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234/M14-WEEKLY-OPERATION-CONSUMER-SOURCE-1/actual-weekly-binding-source-1/LIVE-REVALIDATION-CAP-CORRECTION-1/current119/PROFILE.SOURCE-ONLY.json', 'bytes': 129458, 'sha256': 'b60b342ca18fe438cfa9d342972ac73cafa83f65ee19a32d88c915c9b5d9b0d5'}



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
 assert set(q)=={'author','decision','runtime_authority','request','nonce','current_free','current_ledger','current_bindings','runtime_guard','runtime_guard_source_review','origin_directory','origin_receipt','armed_controls','control_bundle','cutoffs','candidate_snapshot_manifest','reuse_descriptor'}
 assert q['author']=='/root' and q['decision']=='BIND_CONVERSION_FIRST_PRODUCER_SOURCE_INPUTS_ONLY' and q['runtime_authority']is None
 for key in ['request','current_free','current_ledger','current_bindings','runtime_guard','runtime_guard_source_review','origin_receipt','armed_controls','control_bundle','candidate_snapshot_manifest','reuse_descriptor']:auth(q[key])
 assert q['armed_controls']['path']==str(NEWSC/'ACTUAL-CONTROLS-ARMED.json'),'real new control receipt, not historical4889'
 free=read(auth(q['current_free']));ledger=read(auth(q['current_ledger']))
 # Preserve the previously accepted full Root65 chain, then authenticate the
 # separately independently reviewed Root68 successor boundary and full ledger.
 oldq=read(auth(OLD_ROOT_INPUT)); oldfree=read(auth(oldq['current_free'])); oldledger=read(auth(oldq['current_ledger']))
 accepted.accepted_metadata(oldq,oldfree,oldledger); accepted.accepted_chain(oldq)
 assert q['current_free']==ROOT68_FREE and q['current_ledger']==ROOT68_LEDGER and q['current_bindings']==ROOT68_BOUNDARY
 boundary=read(auth(q['current_bindings'])); review=read(auth(ROOT68_REVIEW))
 assert boundary['nonce_ledger']==q['current_ledger'] and boundary['native_custody_clearance']==q['current_free'] and boundary['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert review['decision']=='PASS_EXACT_ROOT68_CURRENT119_CURRENT_BOUNDARY_ADOPTION' and review['independent'] is True and review['implementation_ownership'] is False
 assert review['nonce_ledger']==q['current_ledger'] and review['current_boundary']==q['current_bindings'] and review['independent_current_free']==q['current_free']
 assert all(review['checks'].values()) and len(ledger['consumed_nonces'])==73 and ledger['latest_accepted_free_boundary']==q['current_free'] and ledger['current_physical_clearance_pending'] is False
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
 runner=(HERE/'run_build_only.template.py').read_text(); worker=(HERE/'build_only_worker.template.py').read_text()
 start=runner.index('RUNTIME_GUARD_REF=');end=runner.index('\n',start);runner=runner[:start]+'RUNTIME_GUARD_REF='+repr(guard_ref)+runner[end:]
 start=runner.index('CUTOFFS=');end=runner.index('\n',start);runner=runner[:start]+'CUTOFFS='+repr(limits)+runner[end:]
 start=worker.index('CUTOFFS=');end=worker.index('\n',start);worker=worker[:start]+'CUTOFFS='+repr(limits)+worker[end:]
 return runner,worker

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root-input',type=Path,required=True);parser.add_argument('--root-input-sha256',required=True);args=parser.parse_args()
 assert ref(args.root_input)['sha256']==args.root_input_sha256
 q=read(args.root_input);limits,generated=validate_root(q)
 request=read(auth(q['request']));assert request['author']=='/root' and request['runtime_authority'] is None and request['candidate']==CANDIDATE and request['recipe']==RECIPE and request['snapshot_map']==SNAPSHOT_MAP
 profile=read(auth(PROFILE119));affected=read(auth(AFFECTED)); recipe=read(auth(RECIPE));mapping=read(auth(SNAPSHOT_MAP))
 manifest=read(auth(q['candidate_snapshot_manifest']));root=Path(manifest['export_root'])
 assert manifest['schema']=='mckernel.exact-kernel-rust-subtree-readonly.v1' and manifest['runtime_authority'] is None and manifest['container_destination']=='/src/kernel/rust'
 assert manifest['base_source_root']==profile['inputs']['source6153']+'/kernel/rust' and root.is_absolute() and root.is_dir() and not root.is_symlink()
 assert manifest['external_inputs']==profile['inputs']['external_relative_modules'] and len(manifest['files'])==149
 expected={r['relative']:r['source'] for r in mapping['entries']};actual={}
 for row in manifest['files']:
  relative=Path(row['relative']);assert not relative.is_absolute() and '..' not in relative.parts and str(relative)==row['relative'] and row['relative'] not in actual
  assert row['snapshot']['path']==str(root/relative);auth(row['snapshot'])
  source=expected[row['relative']];assert row['snapshot']['sha256']==source['sha256'] and row['snapshot']['bytes']==source['bytes'];actual[row['relative']]=row['snapshot']
 assert set(actual)==set(expected) and all(not p.is_symlink() for p in root.rglob('*'))
 assert {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}==set(expected)
 profile.update(request_sha256=q['request']['sha256'],actual_nonce=q['nonce'],native_custody_clearance=q['current_free'],fixed_three_clock_cutoffs=limits,deadline_epoch=limits[0],origin_source_materialization=generated,source_preparation_current_context=dict(current_ledger=q['current_ledger'],current_free=q['current_free'],armed_controls=q['armed_controls'],runtime_guard=q['runtime_guard'],runtime_guard_source_review=q['runtime_guard_source_review'],current_bindings=q['current_bindings'],control_bundle=q['control_bundle'],cutoffs=limits))
 profile['status']='CONVERSION_FIRST_INPUTS_BOUND_NOT_EXECUTION_RELEASE';profile['runtime_authority']=None
 profile['exact_commands']=recipe['ordered_commands'];profile['reuse_descriptor']=q['reuse_descriptor']['path']
 profile['inputs']['source_directory_exports']=[dict(host_path=str(root),container_destination='/src/kernel/rust',readonly=True,manifest=q['candidate_snapshot_manifest'])]
 overlay={r['target']:r['source'] for r in affected['file_overlay']}
 for row in profile['inputs']['postimages']:
  if row['relative'] in ('kernel/syscall.c','kernel/CMakeLists.txt'):row['postimage']=overlay[row['relative']]
  elif row['relative'].endswith('/f06_rt_sigreturn_origin.h'):row['postimage']=generated['actual_generated_header']
  elif row['relative'].endswith('/f06_clone_cpuid_metadata.rs'):row['postimage']=generated['actual_generated_metadata']
 retained={r['link_token']:r['source'] for r in recipe['retained_inputs']}
 for row in profile['inputs']['objects']:
  if row['link_token'] in retained:row['replace']=False;row['source']=retained[row['link_token']]
  else:row['replace']=True
 profile['inputs']['retained_count']=9;profile['inputs']['replaced_count']=2
 profile['producer_contract']['new_objects']=['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/syscall.c.o'];profile['producer_contract']['reused_objects']=9
 profile['producer_contract']['process_delta']='Accepted CURRENT119 process and arch objects retained; new Rust crate and generic syscall C only.'
 profile['cohort_source_bindings']=[dict(relative=r['relative'],postimage=r['postimage']) for r in profile['inputs']['postimages']]+[dict(relative='kernel/rust/'+r['relative'],postimage=r['snapshot']) for r in manifest['files']]
 runner,worker=render_sources(limits,q['runtime_guard']);assert not any((HERE/name).exists() for name in ['run_build_only.py','build_only_worker.py','PROFILE.SOURCE-ONLY.json','ROOT-SOURCE-BINDING.ACTUAL.json'])
 ast.parse(runner);ast.parse(worker)
 write('run_build_only.py',runner);write('build_only_worker.py',worker);write('PROFILE.SOURCE-ONLY.json',profile)
 write('ROOT-SOURCE-BINDING.ACTUAL.json',dict(scope=SCOPE,status='ROOT_EXACT_CONVERSION_FIRST_SOURCE_DATA_SEALED_NOT_EXECUTION_AUTHORITY',root_input=ref(args.root_input),runner=ref(HERE/'run_build_only.py'),worker=ref(HERE/'build_only_worker.py'),profile=ref(HERE/'PROFILE.SOURCE-ONLY.json'),runtime_guard=q['runtime_guard'],cutoffs=limits,runtime_authority=None))
 print(json.dumps(read(HERE/'ROOT-SOURCE-BINDING.ACTUAL.json')))
if __name__=='__main__':main()
