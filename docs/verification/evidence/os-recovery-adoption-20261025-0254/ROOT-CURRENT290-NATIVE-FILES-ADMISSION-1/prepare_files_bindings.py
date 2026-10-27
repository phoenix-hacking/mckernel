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
 for key in ['owner_source','manifest','scratch_manifest_stage','capture_helper','collector','overlay','overlay_manifest','latest_serial_operation_physical_acceptance']:
  checked(b[key])
 manifest=read(Path(b['manifest']['path']));need(manifest['case_id']=='baseline.core.files' and manifest['payload']['oracle']==b['expected_oracle'] and bytes.fromhex(b['expected_oracle']['stdout_hex'])==b'NATIVE_CORE PASS files\n','existing files oracle differs')
 need(not list(Path(b['attempt_parent']).iterdir()),'fresh attempt parent is not empty')
 if args.check_static:
  print(json.dumps(dict(status='PASS_STATIC_FILES_REFERENCES_ONLY',runtime_authority=False)));return
 if args.nonce:
  need(re.fullmatch('[0-9a-f]{32}',args.nonce) is not None,'exact Root fresh nonce required')
  need(not os.path.lexists(Path(b['attempt_parent'])/('attempt-'+args.nonce)),'nonce already entered')
  need(not (A/'CAPTURE').exists(),'capture directory already exists')
  b['nonce']=args.nonce;b['exact_argv'][b['exact_argv'].index('--nonce')+1]=args.nonce
  b['capture_sources']={name:ref(A/name) for name in ['capture_fresh_files_resource.py','run_native_files_capture.py','prepare_files_bindings.py']}
  write(A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json',b);(A/'CAPTURE').mkdir(mode=0o700)
  print(json.dumps(dict(status='STATIC_FILES_NONCE_BOUND_NO_RELEASE',static_bindings=ref(A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json'),nonce=args.nonce,runtime_authority=False)));return
 static=read(A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json');fresh=ref(A/'ROOT-FRESH-NATIVE-RESOURCE-PHYSICAL-1.json');resources=read(Path(fresh['path']))
 need(resources['actual_latest_SDK_postjoin_acceptance']==static['latest_serial_operation_physical_acceptance'],'fresh observation not bound to latest accepted SDK')
 need(resources['boot_id']=='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb' and resources['no_existing_heavy'] is True and resources['pids_current']==0,'current boot/occupancy differs')
 packet=dict(author='/root',decision='PENDING_ONE_EXACT_NATIVE_FILES_RELEASE',maximum_invocations=1,nonce=static['nonce'],exact_argv=static['exact_argv'],static_bindings=ref(A/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json'),fresh_resource_physical=fresh,current_physical=static['latest_serial_operation_physical_acceptance'],source_publication=ref(A/'ACTUAL-STATIC-SOURCE-PUBLICATION.json'),capture_directory=str(A/'CAPTURE'),fixed_cutoffs=static['fixed_cutoffs'],strict_profile_acceptance=static['strict_profile_acceptance'],source_scope=__doc__.splitlines()[0],application_acceptance=False,independent_review=None,runtime_authority=None,expected_case=static['expected_case'],expected_oracle=static['expected_oracle'],manifest=static['manifest'],scratch_manifest_stage=static['scratch_manifest_stage'],attempt_parent=static['attempt_parent'],profile=static['profile'],capture_sources=static['capture_sources'])
 write(A/'ROOT-EXECUTION-GRANT.PENDING-REVIEW.json',packet)
 template=dict(decision=None,author='/root',maximum_invocations=1,nonce=static['nonce'],exact_argv=static['exact_argv'],execution_review=None,fresh_resource_physical=fresh,pending_execution_packet=ref(A/'ROOT-EXECUTION-GRANT.PENDING-REVIEW.json'),runtime_authority=None)
 write(A/'ROOT-GRANT.TEMPLATE.NOT-RELEASED.json',template)
 print(json.dumps(dict(status='PENDING_EXACT_FILES_EXECUTION_REVIEW_AND_ROOT_GRANT',packet=ref(A/'ROOT-EXECUTION-GRANT.PENDING-REVIEW.json'),runtime_authority=False)))
if __name__=='__main__':main()
