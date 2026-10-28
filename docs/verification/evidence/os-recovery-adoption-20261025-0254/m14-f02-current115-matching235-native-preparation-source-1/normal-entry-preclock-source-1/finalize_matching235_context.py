"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Mechanical preclock data/source fill for existing normal227 helper/once-entry pipeline.
No guard/observation, compiler, compose, staging, grant, guest or native entry here.
"""
from pathlib import Path
import argparse,ast,hashlib,importlib.util,json,re
D=Path(__file__).resolve().parent;T=D/'templates';F=D/'root-adopted-matching115-process235-entry-1'
HOST_STATIC=D/'STATIC-NATIVE-BINDINGS.HOST-BOUND.NOT-RELEASED.json'
NAMES=['prepare_startup_bindings.py','bind_startup_resource.py','run_startup_resource_once.py','capture_fresh_startup_resource.py','run_native_startup_capture.py']
CASE='P-M06-01-process-exec-wait-235B'
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
 q=json.loads(path.read_bytes());assert q['author']=='/root' and q['decision']=='BIND_EXISTING_ORIGINAL235_NORMAL_ENTRY_SOURCE_ONLY'
 assert q['Root_attests_exact_current_boundary'] is True
 ledger=checked(q['current_ledger']);free=checked(q['latest_free']);assert ledger['latest_accepted_free_boundary']==q['latest_free']
 assert ledger['author']=='/root' and ledger['complete_within_declared_current_boundary'] is True and ledger['root_attests_no_unlisted_post_boundary_execution_or_custody_operation'] is True
 assert free['independent'] is True and free['current_free'] is True and free['normal_owned_retirement'] is True
 return q,ledger

def main(args):
 if args.check_template:
  for name in NAMES+['root_once_startup_entry.py','observe_postcompose_current.py']:ast.parse((T/name).read_text())
  s=json.loads(HOST_STATIC.read_bytes());assert s['expected_case']==CASE and s['compiled_collector_facts']['sha256'].startswith('c900ad58')
  assert s['collector']['sha256']=='ab3e775e6a9df8d36bbbb974ddafbb26493c24f1aaf49487f5fc27c5583bed6c'
  assert len(bytes.fromhex(s['expected_oracle']['stdout_hex']))==235
  print(json.dumps(dict(status='PASS_MATCHING115_ORIGINAL235_TEMPLATES_ACTUAL_STAGE_CURRENT57_KNOWN_AUTHORITY_PENDING',runtime_authority=None)));return
 if args.bind_bridge:
  p=F/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json';st=json.loads(p.read_bytes());assert st['expected_case']==CASE
  text=(T/'root_once_startup_entry.py').read_text();text=text.replace('ROOT_FINAL_STATIC_SHA256',ref(p)['sha256']).replace('ROOT_NEW_UNUSED_235_NONCE',st['nonce'])
  text=re.sub(r"HELPER_SHA = '[0-9a-f]{64}'",'HELPER_SHA = '+repr(ref(F/'run_native_startup_capture.py')['sha256']),text,count=1)
  source(F/'root_once_startup_entry.py',text);print(json.dumps(dict(status='NORMAL_ONCE_BRIDGE_BOUND_NOT_EXECUTED',bridge=ref(F/'root_once_startup_entry.py'))));return
 assert args.root_inputs and args.root_inputs_sha256
 path=Path(args.root_inputs);assert ref(path)['sha256']==args.root_inputs_sha256;q,ledger=root_inputs(path)
 if args.bind_current_observer:
  name=Path(q['current_ledger']['path']).name;match=re.fullmatch(r'ROOT-CURRENT-NONCE-LEDGER([0-9]+)\.json',name);assert match
  key='Root'+match.group(1)
  current=dict(ledger=q['current_ledger'],latest_free=q['latest_free'],compose_result=q['compose_result'],ledger_key=key,root_inputs=ref(path))
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
 assert manifest['artifacts']['payload']['sha256']=='537cb22b2af1f7fca1202afaf45b017364823c185c2ec47474093e51647ba5b8'
 assert stage['nonce'] is None and stage['runtime_authority'] is None and stage['source_manifest']==q['offline_manifest']
 assert stage['scratch_manifest']==q['manifest'] and binding['manifest']['sha256']==q['offline_manifest']['sha256']
 nonce=q['nonce'];assert re.fullmatch('[0-9a-f]{32}',nonce) and nonce not in ledger['consumed_nonces']+ledger['reserved_abandoned_unconsumed_nonces']
 reservation=checked(q['nonce_reservation']);assert reservation['author']=='/root' and reservation['nonce']==nonce
 socket_path=str(Path(stage['planned_attempt_parent'])/('attempt-'+nonce)/'qmp.sock');assert len(socket_path.encode())<=107,'complete actual UNIX socket path too long'
 for key in ['source_authority','case_capability','stage_map_acceptance']:checked(q[key])
 st=json.loads(HOST_STATIC.read_bytes());assert st['expected_oracle']==manifest['payload']['oracle'] and len(bytes.fromhex(st['expected_oracle']['stdout_hex']))==235
 for key in ['offline_manifest','manifest','composed_case_binding','scratch_manifest_stage','source_authority','case_capability','stage_map_acceptance','nonce_reservation']:st[key]=q[key]
 st['nonce']=nonce;st['root_ledger35']=q['current_ledger'];st['latest_serial_operation_physical_acceptance']=q['latest_free'];st['attempt_parent']=stage['planned_attempt_parent'];st['planned_attempt_parent']=stage['planned_attempt_parent'];st['stage_result']=q['scratch_manifest_stage'];st['source_only_QMPproof']=q['stage_map_acceptance']
 st['overlay']=manifest['staging']['derived_initramfs'];st['overlay_manifest']=manifest['staging']['overlay_manifest'];st['current_observer_source']=observer;st['current_observer_source_review']=q['current_observer_source_review'];st['current_observer_schema']=q['current_observer_schema'];st['Root_actual_final_fill_inputs']=ref(path)
 for flag,value in [('--attempt-parent',st['attempt_parent']),('--manifest',q['manifest']['path']),('--manifest-sha256',q['manifest']['sha256']),('--nonce',nonce)]:st['exact_argv'][st['exact_argv'].index(flag)+1]=value
 F.mkdir(mode=0o700)  # Original prepare --nonce exclusively creates CAPTURE; never precreate it here.
 for name in NAMES:
  text=(T/name).read_text()
  if name=='prepare_startup_bindings.py':text=text.replace("'ROOT_CURRENT_CONSUMED_COUNT'",str(len(ledger['consumed_nonces'])))
  if name=='capture_fresh_startup_resource.py':text=text.replace('OBSERVER_REF=None  # ROOT_ACTUAL_REVIEWED_OBSERVER_LITERAL','OBSERVER_REF='+repr(observer)).replace("physical['Root54']",'physical['+repr(module.CURRENT['ledger_key'])+']')
  source(F/name,text)
 st['capture_sources']={name:ref(F/name) for name in NAMES};st['capture_helper']=ref(F/'run_native_startup_capture.py');st['capture_directory']=str(F/'CAPTURE');st['root_admission_directory']=str(F);st['author']=None;st['runtime_authority']=None;st['status']='ROOT_ACTUAL_NORMAL235_SOURCE_FILLED_NOT_RUNTIME_RELEASE'
 write(F/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json',st);write(F/'ACTUAL-SCRATCH-MANIFEST-STAGE.json',stage)
 print(json.dumps(dict(status='ACTUAL_NORMAL235_SOURCE_CONTEXT_FILLED_NO_RUNTIME_AUTHORITY',output=str(F),next_argv=['/home/holden/anaconda3/bin/python3','-I','-B',str(F/'prepare_startup_bindings.py'),'--check-static'])))
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True)
 for name in ['check-template','bind-current-observer','seal-source-context','bind-bridge']:g.add_argument('--'+name,action='store_true')
 p.add_argument('--root-inputs');p.add_argument('--root-inputs-sha256');main(p.parse_args())
