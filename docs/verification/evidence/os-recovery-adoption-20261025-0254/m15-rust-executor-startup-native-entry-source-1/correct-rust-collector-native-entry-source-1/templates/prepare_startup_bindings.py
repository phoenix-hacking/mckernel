"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Data-only static/fresh packet binding; no grant, review, observation or workload.
"""
from pathlib import Path
import argparse,hashlib,json,os,re
A=Path(__file__).resolve().parent

def read(p):return json.loads(p.read_bytes())
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(p,value):
 with p.open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')
def need(ok,message):
 if not ok:raise ValueError(message)
def checked(reference):
 p=Path(reference['path']);need(ref(p)==reference,'exact source/reference changed: '+str(p));return p

def main():
 p=argparse.ArgumentParser(description=__doc__);mode=p.add_mutually_exclusive_group(required=True);mode.add_argument('--nonce');mode.add_argument('--check-static',action='store_true');args=p.parse_args()
 b=read(A/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json')
 for key in ['source_authority','case_capability','stage_map_acceptance','root_ledger35','owner_source','offline_manifest','capture_helper','collector','payload','overlay','overlay_manifest','latest_serial_operation_physical_acceptance','artifact_acceptance','compiled_collector_adoption','compiled_collector_caseprofile','compiled_collector_HOST_acceptance','compiled_collector_facts','nonce_reservation']:
  checked(b[key])
 manifest=read(Path(b['offline_manifest']['path']));need(manifest['case_id']=='startup.argv-empty' and manifest['payload']['oracle']==b['expected_oracle'] and len(bytes.fromhex(b['expected_oracle']['stdout_hex']))==91 and b['expected_oracle']['exit_code']==0 and b['expected_oracle']['stderr_hex']=='','original startup oracle differs')
 # Real first API imports and full immutable manifest validation, no backend/guest.
 import importlib.util
 owner=checked(b['owner_source']);validator=owner.with_name('native_diagnostic.py');need(hashlib.sha256(validator.read_bytes()).hexdigest()=='529830adcd6fafa13979bf6036b2812c88630c5e0112ce4d80f9fc28cc30d4da','exact existing manifest validator')
 spec=importlib.util.spec_from_file_location('bound_f05v2_pure_native_owner',owner);pure_owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(pure_owner)
 spec=importlib.util.spec_from_file_location('bound_f05v2_real_manifest_validator',validator);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v);validated=v.load_manifest(b['offline_manifest']['path'])
 need([r['sha256'] for r in validated['modules'][1:]]==['887dc3567e6035c921588e61b45b41a8ef32a972d142fe2ba82ec48442353b12','57546af5110c0674b307e5ac5a328228abbe784f890f69521db5f594f21f6ae8'],'actual RustMM module tuple')
 need(validated['artifacts']['mckernel_image']['sha256']=='60e62f97ef48ecaf14174af1c5b75d7181969f439c1b45c618d6c16d4bc40d57','accepted CURRENT110 image')
 for key in ['executor_supplement','executor_contract','loader_acceptance','composed_case_binding']:checked(b[key])
 need(validated['artifacts']['mcexec']['sha256']=='e5d18169ee50581274b374bba17fcefebe39e828885f367bfee182beaa3df756','actual staged Rust executor')
 facts=read(Path(b['compiled_collector_facts']['path']));profile=read(Path(b['compiled_collector_caseprofile']['path']));adopt=read(Path(b['compiled_collector_adoption']['path']))
 need(facts['actual_test_count']==16 and facts['filtered']==facts['ignored']==0,'reuse all16 actual startup producer controls')
 need(facts['payload_argv']==profile['argv']==validated['payload']['argv']==b['expected_guest_argv'] and facts['payload_env']==profile['env']==validated['payload']['env'] and facts['payload_cwd']==profile['cwd']==validated['payload']['cwd'],'actual compiled startup producer launch profile')
 need(facts['oracle']==profile['oracle']==validated['payload']['oracle'] and facts['source_caseprofile']['sha256']==b['compiled_collector_caseprofile']['sha256'],'compiled original91B oracle/profile join')
 need(facts['actual_collector_artifact']['sha256']==adopt['artifact']['sha256']==validated['staging']['collector']['sha256']=='d0bf61dc45754e72d3ebab34853756c6ce5cce0c9e84ac1713122ba1cf8f0d5a','correct compiled Rust startup collector, never oldc020')
 supplement_path=Path(b['executor_supplement']['path']);spec=importlib.util.spec_from_file_location('literal_original_startup_executor_supplement',supplement_path);supplement=importlib.util.module_from_spec(spec);spec.loader.exec_module(supplement)
 need(supplement.__file__==str(supplement_path) and supplement.__spec__.origin==str(supplement_path),'literal supplement import context')
 need(b['executor_supplement']['sha256']=='29f9add4327e6eff4dffe7dcac02ad1b10a8349ae621b8b3ee673426ba2bfaca' and b['executor_contract']['sha256']=='0e3a0cf6e63914e9cc23b6e8a6850156f1cd2ad4a481b517e1354e76a1fed443','exact executor supplement/contract')
 supplement.check(validated,read(Path(validated['staging']['overlay_manifest']['path'])),read(Path(b['executor_contract']['path'])))

 if args.check_static:
  print(json.dumps(dict(status='PASS_FULL_M15_STARTUP_MANIFEST_AND_LITERAL_OWNER_API_ONLY',runtime_authority=None,guest_calls=0,source_path_guards='Root scratch stage still required before nonce binding')));return
 stage=read(A/'ACTUAL-SCRATCH-MANIFEST-STAGE.json');need(stage['source_manifest']==b['offline_manifest'] and stage['runtime_authority'] is None and stage['nonce'] is None,'actual Root ordinary manifest stage required')
 checked(stage['scratch_manifest']);b['manifest']=stage['scratch_manifest'];b['attempt_parent']=stage['planned_attempt_parent'];b['planned_attempt_parent']=stage['planned_attempt_parent'];b['scratch_manifest_stage']=ref(A/'ACTUAL-SCRATCH-MANIFEST-STAGE.json');b['stage_result']=b['scratch_manifest_stage']
 pure_owner._manifest_identity(b['manifest']['path'],b['manifest']['sha256']);pure_owner._manifest_outside_writable_parent(b['manifest']['path'],b['attempt_parent']);v.load_manifest(b['manifest']['path'])
 need(not list(Path(b['attempt_parent']).iterdir()),'fresh attempt parent is not empty')
 ledger=read(Path(b['root_ledger35']['path']));need(len(ledger['consumed_nonces'])==39 and ledger['latest_accepted_free_boundary']==b['latest_serial_operation_physical_acceptance'],'exact Root39/free boundary')
 for flag,value in [('--manifest',b['manifest']['path']),('--attempt-parent',b['attempt_parent']),('--manifest-sha256',b['manifest']['sha256'])]:b['exact_argv'][b['exact_argv'].index(flag)+1]=value

 if args.nonce:
  need(re.fullmatch('[0-9a-f]{32}',args.nonce) is not None,'exact Root fresh nonce required')
  need(args.nonce not in ledger['consumed_nonces']+ledger['reserved_abandoned_unconsumed_nonces'],'fresh nonce excludes consumed and abandoned')
  need(not os.path.lexists(Path(b['attempt_parent'])/('attempt-'+args.nonce)),'nonce already entered')
  need(not (A/'CAPTURE').exists(),'capture directory already exists')
  b['author']='/root';b['nonce']=args.nonce;b['exact_argv'][b['exact_argv'].index('--nonce')+1]=args.nonce
  b['capture_sources']={name:ref(A/name) for name in ['capture_fresh_startup_resource.py','run_native_startup_capture.py','prepare_startup_bindings.py','bind_startup_resource.py','run_startup_resource_once.py']}
  write(A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json',b);(A/'CAPTURE').mkdir(mode=0o700)
  print(json.dumps(dict(status='STATIC_M15_STARTUP_NONCE_BOUND_NO_RELEASE',static_bindings=ref(A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json'),nonce=args.nonce,runtime_authority=False)));return
if __name__=='__main__':main()
