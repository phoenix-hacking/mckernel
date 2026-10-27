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
 b['latest_serial_operation_physical_acceptance']=b['proposed_latest_physical_acceptance']
 for key in ['owner_source','offline_manifest','capture_helper','collector','payload','overlay','overlay_manifest','latest_serial_operation_physical_acceptance','artifact_acceptance']:
  checked(b[key])
 manifest=read(Path(b['offline_manifest']['path']));need(manifest['case_id']=='practical.rust-std.fp-thread-state' and manifest['payload']['oracle']==b['expected_oracle'] and len(bytes.fromhex(b['expected_oracle']['stdout_hex']))==254 and b['expected_oracle']['exit_code']==0 and b['expected_oracle']['stderr_hex']=='','original FP254 oracle differs')
 # Real first API imports and full immutable manifest validation, no backend/guest.
 import importlib.util
 owner=checked(b['owner_source']);validator=owner.with_name('native_diagnostic.py');need(hashlib.sha256(validator.read_bytes()).hexdigest()=='f368324242bfdfb0ad1f3f524a906dcf51730ef0beb311315e6b66f5d585748c','exact existing manifest validator')
 spec=importlib.util.spec_from_file_location('fp_pure_native_owner',owner);pure_owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(pure_owner)
 spec=importlib.util.spec_from_file_location('fp_real_manifest_validator',validator);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v);validated=v.load_manifest(b['offline_manifest']['path'])
 need([r['sha256'] for r in validated['modules'][1:]]==['887dc3567e6035c921588e61b45b41a8ef32a972d142fe2ba82ec48442353b12','57546af5110c0674b307e5ac5a328228abbe784f890f69521db5f594f21f6ae8'],'actual RustMM module tuple')
 need(validated['artifacts']['mckernel_image']['sha256']=='26eb201ab8160b98e9a95ac3bae116a6392f343faf60641bb62faa7116a793eb','actual accepted FIVE26eb image')
 need(manifest['payload']['argv']==b['expected_guest_argv'] and manifest['profile']==b['profile']['guest'],'original FP argv/profile differs')
 if args.check_static:
  print(json.dumps(dict(status='PASS_REAL_SIDE_EFFECT_FREE_FP_THREAD_STATE_MANIFEST_AND_OWNER_API_IMPORTS',runtime_authority=None,guest_calls=0,source_path_guards='Root scratch stage still required before nonce binding')));return
 stage=read(A/'ACTUAL-SCRATCH-MANIFEST-STAGE.json');need(stage['source_manifest']==b['offline_manifest'] and stage['runtime_authority'] is None and stage['nonce'] is None,'actual Root ordinary manifest stage required')
 checked(stage['scratch_manifest']);b['manifest']=stage['scratch_manifest'];b['attempt_parent']=stage['planned_attempt_parent'];b['planned_attempt_parent']=stage['planned_attempt_parent'];b['scratch_manifest_stage']=ref(A/'ACTUAL-SCRATCH-MANIFEST-STAGE.json');b['stage_result']=b['scratch_manifest_stage']
 pure_owner._manifest_identity(b['manifest']['path'],b['manifest']['sha256']);pure_owner._manifest_outside_writable_parent(b['manifest']['path'],b['attempt_parent']);v.load_manifest(b['manifest']['path'])
 need(not list(Path(b['attempt_parent']).iterdir()),'fresh attempt parent is not empty')
 for flag,value in [('--manifest',b['manifest']['path']),('--attempt-parent',b['attempt_parent']),('--manifest-sha256',b['manifest']['sha256'])]:b['exact_argv'][b['exact_argv'].index(flag)+1]=value

 if args.nonce:
  need(re.fullmatch('[0-9a-f]{32}',args.nonce) is not None,'exact Root fresh nonce required')
  need(not os.path.lexists(Path(b['attempt_parent'])/('attempt-'+args.nonce)),'nonce already entered')
  need(not (A/'CAPTURE').exists(),'capture directory already exists')
  b['author']='/root';b['nonce']=args.nonce;b['exact_argv'][b['exact_argv'].index('--nonce')+1]=args.nonce
  R=A/'resource-output-retention-source-1'
  b['capture_sources']={name:ref(A/name) for name in ['run_native_fp_capture.py','prepare_fp_bindings.py']}
  b['capture_sources'].update({name:ref(R/name) for name in ['capture_fresh_fp_resource2.py','bind_resource2.py','run_resource2_once.py']})
  write(A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json',b)
  resource_static=dict(b);resource_static['resource_output_successor']=dict(prior_static=ref(A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json'),same_unused_nonce=True,new_runtime_authority=None)
  write(R/'STATIC-NATIVE-BINDINGS.RESOURCE-2.NOT-RELEASED.json',resource_static);(A/'CAPTURE').mkdir(mode=0o700)
  print(json.dumps(dict(status='STATIC_FP_THREAD_STATE_NONCE_BOUND_NO_RELEASE',static_bindings=ref(A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json'),nonce=args.nonce,runtime_authority=False)));return
if __name__=='__main__':main()
