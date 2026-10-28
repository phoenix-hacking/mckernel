"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Mechanical preclock data/source fill for existing normal227 helper/once-entry pipeline.
No guard/observation, compiler, compose, staging, grant, guest or native entry here.
"""
from pathlib import Path
import argparse,ast,hashlib,importlib.util,json,re
D=Path(__file__).resolve().parent;T=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current116-actual-postjoin-current60-source-20261028-1/current61-after116-consumer-source-1/consumer-physical-shape-correction-source-1/cohort');F=D/'root-adopted-process227-entry-1'
HOST_STATIC=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-process227-stage-and-entry-preparation-source-1/actual-host-bound-source-1/STATIC-NATIVE-BINDINGS.HOST-BOUND.NOT-RELEASED.json')
NAMES=['prepare_startup_bindings.py','bind_startup_resource.py','run_startup_resource_once.py','capture_fresh_startup_resource.py','run_native_startup_capture.py']
CASE='P-M01-02-child-SIGTERM-and-exec-recovery-227B'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def checked(r):
 assert ref(r['path'])==r;return json.loads(Path(r['path']).read_bytes())
def write(p,v):
 with p.open('x') as out:json.dump(v,out,indent=2,sort_keys=True);out.write('\n')
def source(p,text):
 ast.parse(text)
 with p.open('x') as out:out.write(text)
def load(p):
 spec=importlib.util.spec_from_file_location('literal_227_preclock_source',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def root_inputs(path):
 q=json.loads(path.read_bytes());assert q['author']=='/root' and q['decision']=='BIND_EXISTING_ORIGINAL227_NORMAL_ENTRY_SOURCE_ONLY'
 assert q['Root_attests_exact_current_boundary'] is True
 ledger=checked(q['current_ledger']);free=checked(q['latest_free']);assert ledger['latest_accepted_free_boundary']==q['latest_free']
 assert ledger['author']=='/root' and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert free['independent'] is True and free['current_free'] is True and free['normal_owned_retirement'] is True
 return q,ledger


NEW_ORIGINAL227_MAX_LIMITS=(1793253600.0,1035705.5689454618,1051043.6959931096)
HISTORICAL_STATIC_REF={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-process227-stage-and-entry-preparation-source-1/actual-host-bound-source-1/STATIC-NATIVE-BINDINGS.HOST-BOUND.NOT-RELEASED.json', 'bytes': 7669, 'sha256': '591169399ef6d2bf00fffa09d89e3e2ec0a5b35a3dcae4469126c67dff3a95b1'}
HISTORICAL_FIXED_LIMITS=[1793165769.0,947874.5689514667,963213.6960030915]

def seal_new_operation_window(q,st):
 assert ref(HOST_STATIC)==HISTORICAL_STATIC_REF,'historical original227 static bytes changed'
 assert st['fixed_cutoffs']==HISTORICAL_FIXED_LIMITS,'historical original227 clamp prefix differs'
 adapter=q['operation_guard_adapter'];assert ref(adapter['path'])==adapter
 configref=q['operation_guard_configuration'];assert ref(configref['path'])==configref
 module=load(Path(adapter['path']));assert module.OPERATION=='original227'
 module.configure(configref)  # Pure exact review/config/account-floor validation only.
 limits=module.current_cutoffs()  # No live account/window/guardian guard call.
 previous=checked(q['latest_free']);observed=previous['last_observed_clocks']
 assert type(limits) in (list,tuple) and len(limits)==3
 assert all(type(x) in (int,float) and now<x<=ceiling for now,x,ceiling in zip(observed,limits,NEW_ORIGINAL227_MAX_LIMITS)),'new reviewed operation cutoffs expired or widened relative to actual currentfree/window'
 st['historical_original227_static_window']=dict(source=HISTORICAL_STATIC_REF,fixed_cutoffs=list(st['fixed_cutoffs']),status='HISTORICAL_EXPIRED_NOT_RUNTIME_AUTHORITY')
 st['new_original227_sealing_window_binding']=dict(operation='original227',adapter=adapter,configuration=configref,validated_pure_current_cutoffs=list(limits),runtime_authority=None,live_guard_calls=0)
 st['fixed_cutoffs']=list(limits)
 return st

def main(args):
 if args.check_template:
  for name in NAMES+['root_once_startup_entry.py','runtime_guard.py']:ast.parse((T/name).read_text())
  s=json.loads(HOST_STATIC.read_bytes());assert s['expected_case']==CASE and s['compiled_collector_facts']['sha256'].startswith('2289099d')
  assert s['collector']['sha256']=='ab3e775e6a9df8d36bbbb974ddafbb26493c24f1aaf49487f5fc27c5583bed6c'
  assert len(bytes.fromhex(s['expected_oracle']['stdout_hex']))==227
  print(json.dumps(dict(status='PASS_NORMAL227_SOURCE_TEMPLATES_ACTUAL_HOST_BOUND_FUTURE_ROOT54_NULL',runtime_authority=None)));return
 if args.bind_bridge:
  p=F/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json';st=json.loads(p.read_bytes());assert st['expected_case']==CASE
  text=(T/'root_once_startup_entry.py').read_text().replace('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/current116-actual-postjoin-current60-source-20261028-1/current61-after116-consumer-source-1/consumer-physical-shape-correction-source-1',str(D)).replace(str(T/'runtime_guard.py'),str(F/'runtime_guard.py')).replace(str(D/'cohort'),str(F));text=text.replace('ROOT_FINAL_STATIC_SHA256',ref(p)['sha256']).replace('ROOT_NEW_UNUSED_227_NONCE',st['nonce'])
  text=re.sub(r"HELPER_SHA = '[0-9a-f]{64}'",'HELPER_SHA = '+repr(ref(F/'run_native_startup_capture.py')['sha256']),text,count=1)
  source(F/'root_once_startup_entry.py',text);print(json.dumps(dict(status='NORMAL_ONCE_BRIDGE_BOUND_NOT_EXECUTED',bridge=ref(F/'root_once_startup_entry.py'))));return
 assert args.root_inputs and args.root_inputs_sha256
 path=Path(args.root_inputs);assert ref(path)['sha256']==args.root_inputs_sha256;q,ledger=root_inputs(path)
 if args.bind_current_observer:
  raise ValueError('use separately reviewed configured native observer')
  name=Path(q['current_ledger']['path']).name;match=re.fullmatch(r'ROOT-CURRENT-NONCE-LEDGER([0-9]+)\.json',name);assert match
  key='Root'+match.group(1)
  current=dict(ledger=q['current_ledger'],latest_free=q['latest_free'],compose_result=q['compose_result'],ledger_key=key,root_inputs=q['current_ledger'])
  text=(T/'observe_postcompose_current.py').read_text();assert text.count('CURRENT=None  # ROOT_ACTUAL_POSTCOMPOSE_CURRENT_LITERAL')==1
  text=text.replace('CURRENT=None  # ROOT_ACTUAL_POSTCOMPOSE_CURRENT_LITERAL','CURRENT='+repr(current)).replace('ROOT_CURRENT_LEDGER_KEY',key).replace('ROOT_CURRENT_LEDGER_BASENAME',name);target=D/'BOUND-CURRENT-OBSERVER.SOURCE-ONLY.py';source(target,text)
  module=load(target);module.validate_current(module.CURRENT)  # Receipt reads only; no observe call.
  schema=dict(schema_version='EXACT_OBSERVER_ROOT_LEDGER_FIELD_V1',observer=ref(target),ledger_key=key,expected_status=module.STATUS,current_boundary_key='current_boundary',latest_free_key='actual_latest_operation_postjoin_acceptance')
  write(D/'BOUND-OBSERVER-SCHEMA.SOURCE-ONLY.json',schema)
  print(json.dumps(dict(status='ACTUAL_ROOT54_OBSERVER_SOURCE_FILLED_NOT_OBSERVED',observer=ref(target),schema=ref(D/'BOUND-OBSERVER-SCHEMA.SOURCE-ONLY.json'))));return
 assert args.seal_source_context and not F.exists()
 observer=q['current_observer_source'];module=load(Path(observer['path']));assert ref(observer['path'])==observer
 module.validate_current(module.CURRENT);assert module.CURRENT['ledger']==q['current_ledger'] and module.CURRENT['latest_free']==q['latest_free'] and module.CURRENT['compose_result']==q['compose_result']
 review=checked(q['current_observer_source_review']);assert review['independent'] is True and review['implementation_ownership'] is False and str(review['decision']).startswith('PASS') and observer['sha256'] in json.dumps(review)
 schema=checked(q['current_observer_schema']);assert schema['observer']==observer and schema['ledger_key']==module.CURRENT['ledger_key']
 manifest=checked(q['offline_manifest']);binding=checked(q['composed_case_binding']);stage=checked(q['scratch_manifest_stage'])
 assert manifest['case_id']==CASE and manifest['staging']['collector']['sha256']=='ab3e775e6a9df8d36bbbb974ddafbb26493c24f1aaf49487f5fc27c5583bed6c'
 assert manifest['artifacts']['payload']['sha256']=='6abb5e9046444c64d72139f85fcae9e4796eff7ceb5cc2dd1e5b1a47ef3695a5'
 assert stage['nonce'] is None and stage['runtime_authority'] is None and stage['source_manifest']==q['offline_manifest']
 assert stage['scratch_manifest']==q['manifest'] and binding['manifest']['sha256']==q['offline_manifest']['sha256']
 nonce=q['nonce'];assert re.fullmatch('[0-9a-f]{32}',nonce) and nonce not in ledger['consumed_nonces']+ledger['reserved_abandoned_unconsumed_nonces']
 reservation=checked(q['nonce_reservation']);assert reservation['author']=='/root' and reservation['nonce']==nonce
 socket_path=str(Path(stage['planned_attempt_parent'])/('attempt-'+nonce)/'qmp.sock');assert len(socket_path.encode())<=107,'complete actual UNIX socket path too long'
 for key in ['source_authority','case_capability','stage_map_acceptance']:checked(q[key])
 st=json.loads(HOST_STATIC.read_bytes());seal_new_operation_window(q,st);assert st['expected_oracle']==manifest['payload']['oracle'] and len(bytes.fromhex(st['expected_oracle']['stdout_hex']))==227
 st['executor_contract']={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-rust-executor-process227-stage-and-entry-preparation-source-1/next-entry-current-boundary-source-1/original227-contract-case-correction-source-1/SOURCE-BOUND-NATIVE-CONTRACT.ORIGINAL227-ADDITIVE.json', 'bytes': 9098, 'sha256': '7f06ce9bce0d58a6baeb9df1e1c1fd24d26c7b6d825db384dbf12c2693c629a6'}
 st['collector']=ref(Path(st['collector']['path']));st['payload']=ref(Path(st['payload']['path']))  # Consumerref shape3; actualmanifest artifact(mode/size) schema remains unchanged.
 for key in ['offline_manifest','manifest','composed_case_binding','scratch_manifest_stage','source_authority','case_capability','stage_map_acceptance','nonce_reservation']:st[key]=q[key]
 st['nonce']=nonce;st['root_ledger35']=q['current_ledger'];st['latest_serial_operation_physical_acceptance']=q['latest_free'];st['attempt_parent']=stage['planned_attempt_parent'];st['planned_attempt_parent']=stage['planned_attempt_parent'];st['stage_result']=q['scratch_manifest_stage'];st['source_only_QMPproof']=q['stage_map_acceptance']
 st['overlay']=ref(Path(manifest['staging']['derived_initramfs']['path']));st['overlay_manifest']=ref(Path(manifest['staging']['overlay_manifest']['path']));st['current_observer_source']=observer;st['current_observer_source_review']=q['current_observer_source_review'];st['current_observer_schema']=q['current_observer_schema'];st['Root_actual_final_fill_inputs']=ref(path)
 for flag,value in [('--attempt-parent',st['attempt_parent']),('--manifest',q['manifest']['path']),('--manifest-sha256',q['manifest']['sha256']),('--nonce',nonce)]:st['exact_argv'][st['exact_argv'].index(flag)+1]=value
 F.mkdir(mode=0o700)  # Original prepare --nonce exclusively creates CAPTURE; never precreate it here.
 for name in NAMES:
  text=(T/name).read_text().replace(str(T/'runtime_guard.py'),str(F/'runtime_guard.py'))
  if name=='prepare_startup_bindings.py':text=text.replace("'ROOT_CURRENT_CONSUMED_COUNT'",str(len(ledger['consumed_nonces'])))
  if name=='capture_fresh_startup_resource.py':text=text.replace('OBSERVER_REF=None  # ROOT_ACTUAL_REVIEWED_OBSERVER_LITERAL','OBSERVER_REF='+repr(observer)).replace("physical['Root54']",'physical['+repr(module.CURRENT['ledger_key'])+']')
  source(F/name,text)
 for key in ['operation_guard_adapter']:
  r=q[key];assert ref(r['path'])==r;st[key]=r
 assert q['operation_guard_adapter']=={'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/new-window-operation-guards-source-20261028-1/original227_guard_adapter.py', 'bytes': 3004, 'sha256': '307993c2dfdc44982386e5c3f8c411b3546e16ba0ecc87447ef12551101cba9f'}
 runtime_text=(T/'runtime_guard.py').read_text();source(F/'runtime_guard.py',runtime_text)
 st['capture_sources']={name:ref(F/name) for name in NAMES};st['capture_helper']=ref(F/'run_native_startup_capture.py');st['capture_directory']=str(F/'CAPTURE');st['root_admission_directory']=str(F);st['author']=None;st['runtime_authority']=None;st['status']='ROOT_ACTUAL_NORMAL227_SOURCE_FILLED_NOT_RUNTIME_RELEASE'
 write(F/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json',st);write(F/'ACTUAL-SCRATCH-MANIFEST-STAGE.json',stage)
 print(json.dumps(dict(status='ACTUAL_NORMAL227_SOURCE_CONTEXT_FILLED_NO_RUNTIME_AUTHORITY',output=str(F),next_argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(F/'prepare_startup_bindings.py'),'--check-static'])))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
 for name in ['check-template','bind-current-observer','seal-source-context','bind-bridge']:g.add_argument('--'+name,action='store_true')
 p.add_argument('--root-inputs');p.add_argument('--root-inputs-sha256');main(p.parse_args())
