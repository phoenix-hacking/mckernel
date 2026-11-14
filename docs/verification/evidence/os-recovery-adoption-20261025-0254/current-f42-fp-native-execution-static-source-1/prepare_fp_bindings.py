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
 p=argparse.ArgumentParser(description=__doc__);mode=p.add_mutually_exclusive_group(required=True);mode.add_argument('--nonce');mode.add_argument('--bind-fresh',action='store_true');mode.add_argument('--check-static',action='store_true');args=p.parse_args()
 b=read(A/'STATIC-NATIVE-BINDINGS.TEMPLATE.NOT-RELEASED.json')
 for key in ['owner_source','offline_manifest','capture_helper','collector','payload','overlay','overlay_manifest','latest_serial_operation_physical_acceptance','artifact_acceptance']:
  checked(b[key])
 manifest=read(Path(b['offline_manifest']['path']));need(manifest['case_id']=='practical.rust-std.fp-thread-state' and manifest['payload']['oracle']==b['expected_oracle'] and len(bytes.fromhex(b['expected_oracle']['stdout_hex']))==254 and b['expected_oracle']['exit_code']==0 and b['expected_oracle']['stderr_hex']=='','original FP254 oracle differs')
 # Real first API imports and full immutable manifest validation, no backend/guest.
 import importlib.util
 owner=checked(b['owner_source']);validator=owner.with_name('native_diagnostic.py');need(hashlib.sha256(validator.read_bytes()).hexdigest()=='f368324242bfdfb0ad1f3f524a906dcf51730ef0beb311315e6b66f5d585748c','exact existing manifest validator')
 spec=importlib.util.spec_from_file_location('fp_pure_native_owner',owner);pure_owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(pure_owner)
 spec=importlib.util.spec_from_file_location('fp_real_manifest_validator',validator);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v);validated=v.load_manifest(b['offline_manifest']['path'])
 need([r['sha256'] for r in validated['modules'][1:]]==['887dc3567e6035c921588e61b45b41a8ef32a972d142fe2ba82ec48442353b12','57546af5110c0674b307e5ac5a328228abbe784f890f69521db5f594f21f6ae8'],'actual RustMM module tuple')
 need(validated['artifacts']['mckernel_image']['sha256']=='f42a871d83fcd1f30c9ee66734a8ba760a8587797c4e076079da0e37bfbcb908','actual NEXT10 f42 image')
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
  b['capture_sources']={name:ref(A/name) for name in ['capture_fresh_fp_resource.py','run_native_fp_capture.py','prepare_fp_bindings.py']}
  write(A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json',b);(A/'CAPTURE').mkdir(mode=0o700)
  print(json.dumps(dict(status='STATIC_FP_THREAD_STATE_NONCE_BOUND_NO_RELEASE',static_bindings=ref(A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json'),nonce=args.nonce,runtime_authority=False)));return
 static=read(A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json');fresh=ref(A/'ROOT-FRESH-NATIVE-RESOURCE-PHYSICAL-1.json');resources=read(Path(fresh['path']))
 need(resources['actual_latest_operation_postjoin_acceptance']==static['latest_serial_operation_physical_acceptance'],'fresh observation not bound to latest accepted daemon physical clearance')
 need(resources['boot_id']=='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb' and resources['no_existing_heavy'] is True and resources['pids_current']==0,'current boot/occupancy differs')
 packet=dict(author='/root',decision='PENDING_ONE_EXACT_NATIVE_FP_THREAD_STATE_RELEASE',maximum_invocations=1,nonce=static['nonce'],exact_argv=static['exact_argv'],static_bindings=ref(A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json'),fresh_resource_physical=fresh,current_physical=static['latest_serial_operation_physical_acceptance'],source_publication=ref(A/'ACTUAL-STATIC-SOURCE-PUBLICATION.json'),capture_directory=str(A/'CAPTURE'),fixed_cutoffs=static['fixed_cutoffs'],artifact_acceptance=static['artifact_acceptance'],source_scope=__doc__.splitlines()[0],application_acceptance=False,independent_review=None,runtime_authority=None,expected_case=static['expected_case'],expected_oracle=static['expected_oracle'],manifest=static['manifest'],scratch_manifest_stage=static['scratch_manifest_stage'],attempt_parent=static['attempt_parent'],profile=static['profile'],capture_sources=static['capture_sources'])
 write(A/'ROOT-EXECUTION-GRANT.PENDING-REVIEW.json',packet)
 template=dict(decision=None,author='/root',maximum_invocations=1,nonce=static['nonce'],exact_argv=static['exact_argv'],execution_review=None,fresh_resource_physical=fresh,pending_execution_packet=ref(A/'ROOT-EXECUTION-GRANT.PENDING-REVIEW.json'),runtime_authority=None)
 write(A/'ROOT-GRANT.TEMPLATE.NOT-RELEASED.json',template)
 print(json.dumps(dict(status='PENDING_EXACT_FP_THREAD_STATE_EXECUTION_REVIEW_AND_ROOT_GRANT',packet=ref(A/'ROOT-EXECUTION-GRANT.PENDING-REVIEW.json'),runtime_authority=False)))
if __name__=='__main__':main()
