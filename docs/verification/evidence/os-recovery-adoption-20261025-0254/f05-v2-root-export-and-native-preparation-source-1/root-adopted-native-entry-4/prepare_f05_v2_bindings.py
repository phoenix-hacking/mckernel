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
 for key in ['source_authority','case_capability','stage_map_acceptance','root_ledger33','owner_source','offline_manifest','capture_helper','collector','payload','overlay','overlay_manifest','latest_serial_operation_physical_acceptance','artifact_acceptance']:
  checked(b[key])
 manifest=read(Path(b['offline_manifest']['path']));need(manifest['case_id']=='M14-05-05-owned-processvm-v2-204B' and manifest['payload']['oracle']==b['expected_oracle'] and len(bytes.fromhex(b['expected_oracle']['stdout_hex']))==204 and b['expected_oracle']['exit_code']==0 and b['expected_oracle']['stderr_hex']=='','actual v2 204B oracle differs')
 # Real first API imports and full immutable manifest validation, no backend/guest.
 import importlib.util
 owner=checked(b['owner_source']);validator=owner.with_name('native_diagnostic.py');need(hashlib.sha256(validator.read_bytes()).hexdigest()=='529830adcd6fafa13979bf6036b2812c88630c5e0112ce4d80f9fc28cc30d4da','exact existing manifest validator')
 spec=importlib.util.spec_from_file_location('bound_f05v2_pure_native_owner',owner);pure_owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(pure_owner)
 spec=importlib.util.spec_from_file_location('bound_f05v2_real_manifest_validator',validator);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v);validated=v.load_manifest(b['offline_manifest']['path'])
 need([r['sha256'] for r in validated['modules'][1:]]==['887dc3567e6035c921588e61b45b41a8ef32a972d142fe2ba82ec48442353b12','57546af5110c0674b307e5ac5a328228abbe784f890f69521db5f594f21f6ae8'],'actual RustMM module tuple')
 need(validated['artifacts']['mckernel_image']['sha256']=='60e62f97ef48ecaf14174af1c5b75d7181969f439c1b45c618d6c16d4bc40d57','accepted CURRENT110 image')
 if args.check_static:
  print(json.dumps(dict(status='PASS_FULL_F05_V2_MANIFEST_AND_LITERAL_OWNER_API_ONLY',runtime_authority=None,guest_calls=0,source_path_guards='Root scratch stage still required before nonce binding')));return
 stage=read(A/'ACTUAL-SCRATCH-MANIFEST-STAGE.json');need(stage['source_manifest']==b['offline_manifest'] and stage['runtime_authority'] is None and stage['nonce'] is None,'actual Root ordinary manifest stage required')
 checked(stage['scratch_manifest']);b['manifest']=stage['scratch_manifest'];b['attempt_parent']=stage['planned_attempt_parent'];b['planned_attempt_parent']=stage['planned_attempt_parent'];b['scratch_manifest_stage']=ref(A/'ACTUAL-SCRATCH-MANIFEST-STAGE.json');b['stage_result']=b['scratch_manifest_stage']
 pure_owner._manifest_identity(b['manifest']['path'],b['manifest']['sha256']);pure_owner._manifest_outside_writable_parent(b['manifest']['path'],b['attempt_parent']);v.load_manifest(b['manifest']['path'])
 need(not list(Path(b['attempt_parent']).iterdir()),'fresh attempt parent is not empty')
 ledger=read(Path(b['root_ledger33']['path']));need(len(ledger['consumed_nonces'])==33 and ledger['latest_accepted_free_boundary']==b['latest_serial_operation_physical_acceptance'],'exact Root33/free boundary')
 for flag,value in [('--manifest',b['manifest']['path']),('--attempt-parent',b['attempt_parent']),('--manifest-sha256',b['manifest']['sha256'])]:b['exact_argv'][b['exact_argv'].index(flag)+1]=value

 if args.nonce:
  need(re.fullmatch('[0-9a-f]{32}',args.nonce) is not None,'exact Root fresh nonce required')
  need(args.nonce not in ledger['consumed_nonces']+ledger['reserved_abandoned_unconsumed_nonces'],'fresh nonce excludes consumed and abandoned')
  need(not os.path.lexists(Path(b['attempt_parent'])/('attempt-'+args.nonce)),'nonce already entered')
  need(not (A/'CAPTURE').exists(),'capture directory already exists')
  b['author']='/root';b['nonce']=args.nonce;b['exact_argv'][b['exact_argv'].index('--nonce')+1]=args.nonce
  b['capture_sources']={name:ref(A/name) for name in ['capture_fresh_f05_v2_resource.py','run_native_f05_v2_capture.py','prepare_f05_v2_bindings.py','bind_f05_v2_resource.py','run_f05_v2_resource_once.py']}
  write(A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json',b);(A/'CAPTURE').mkdir(mode=0o700)
  print(json.dumps(dict(status='STATIC_F05_V2_NONCE_BOUND_NO_RELEASE',static_bindings=ref(A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json'),nonce=args.nonce,runtime_authority=False)));return
if __name__=='__main__':main()
