"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Data-only successor of the existing --bind-fresh branch; no observation or grant.
"""
from pathlib import Path
import argparse,hashlib,json,math
R=Path(__file__).resolve().parent;A=R

def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())

def write(p,value):
 with p.open('x') as f:json.dump(value,f,indent=2,sort_keys=True);f.write('\n')

AUTHORIZED_FIXED_LIMITS = (1793774133, 1556235.568922472, 1571573.6959699572)

def cutoff_triplet(values, label):
 if type(values) not in (list, tuple) or len(values) != 3:
  raise ValueError(label + ': three clock values required')
 if any(type(value) not in (int, float) or not math.isfinite(value) or value <= 0 for value in values):
  raise ValueError(label + ': finite positive numeric clocks required')
 return tuple(values)

def validate_resource_cutoffs(resource_cutoffs, declared_cutoffs):
 resource = cutoff_triplet(resource_cutoffs, 'resource cutoffs')
 declared = cutoff_triplet(declared_cutoffs, 'static declared ceilings')
 if not all(actual <= ceiling <= authorized for actual, ceiling, authorized in zip(resource, declared, AUTHORIZED_FIXED_LIMITS)):
  raise ValueError('resource/static cutoffs widen an inherited ceiling')
 return list(resource)

def packet_for(static,staticref,resources,fresh,publication):
 # Same actual resource predicates as the accepted original --bind-fresh branch.
 assert resources['actual_latest_operation_postjoin_acceptance']==static['latest_serial_operation_physical_acceptance'],'fresh observation not bound to latest accepted daemon physical clearance'
 assert resources['boot_id']=='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb' and resources['no_existing_heavy'] is True and resources['pids_current']==0,'current boot/occupancy differs'
 assert resources['root_ledger35']==static['root_ledger35']
 actual_resource_cutoffs = validate_resource_cutoffs(resources['fixed_cutoffs'], static['fixed_cutoffs'])
 assert static['expected_case']=='P-M06-01-process-exec-wait-235B'
 return dict(author='/root',decision='PENDING_ONE_EXACT_NATIVE_M15_STARTUP_RELEASE',maximum_invocations=1,nonce=static['nonce'],exact_argv=static['exact_argv'],static_bindings=staticref,fresh_resource_physical=fresh,current_physical=static['latest_serial_operation_physical_acceptance'],source_publication=publication,capture_directory=str(A/'CAPTURE'),fixed_cutoffs=actual_resource_cutoffs,artifact_acceptance=static['artifact_acceptance'],source_scope=__doc__.splitlines()[0],application_acceptance=False,independent_review=None,runtime_authority=None,expected_case=static['expected_case'],expected_oracle=static['expected_oracle'],manifest=static['manifest'],scratch_manifest_stage=static['scratch_manifest_stage'],attempt_parent=static['attempt_parent'],profile=static['profile'],capture_sources=static['capture_sources'],expected_new_image_sha256=static['expected_new_image_sha256'],owner_sha256=static['owner_source']['sha256'],evaluator_sha256=static['evaluator_source']['sha256'],root_ledger35=static['root_ledger35'],source_authority=static['source_authority'],case_capability=static['case_capability'],stage_map_acceptance=static['stage_map_acceptance'])

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--resource',required=True,type=Path);args=p.parse_args()
 assert args.resource==R/'ROOT-FRESH-NATIVE-RESOURCE-PHYSICAL-1.json','exact Resource2 output only'
 staticpath=R/'STATIC-NATIVE-BINDINGS.NOT-RELEASED.json'
 static=json.loads(staticpath.read_bytes());fresh=ref(args.resource);resources=json.loads(args.resource.read_bytes())
 joinedpath=R/'RESOURCE-1-CAPTURE-JOIN.json';joined=json.loads(joinedpath.read_bytes())
 assert joined['direct_child_joined'] is True and joined['returncode']==0 and joined['streams_closed'] is True
 assert joined['resource']==fresh and joined['stderr']['bytes']==0
 assert joined['argv']==['/home/holden/anaconda3/bin/python3','-I','-B',str(R/'capture_fresh_startup_resource.py'),'--output-path',str(args.resource)]
 packet=packet_for(static,ref(staticpath),resources,fresh,ref(R/'ACTUAL-STATIC-SOURCE-PUBLICATION.json'))
 packet['resource_output_retention']=ref(joinedpath)
 write(R/'ROOT-EXECUTION-GRANT.PENDING-REVIEW.json',packet)
 template=dict(decision=None,author='/root',maximum_invocations=1,nonce=static['nonce'],exact_argv=static['exact_argv'],execution_review=None,fresh_resource_physical=fresh,pending_execution_packet=ref(R/'ROOT-EXECUTION-GRANT.PENDING-REVIEW.json'),runtime_authority=None)
 write(R/'ROOT-GRANT.TEMPLATE.NOT-RELEASED.json',template)
 print(json.dumps(dict(status='PENDING_EXACT_FP_RESOURCE2_EXECUTION_REVIEW_AND_ROOT_GRANT',packet=ref(R/'ROOT-EXECUTION-GRANT.PENDING-REVIEW.json'),resource=fresh,runtime_authority=None)))
if __name__=='__main__':main()
