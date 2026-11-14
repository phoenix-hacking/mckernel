"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Materialize only fixed batch constants from an actual profile and actual first-review.
No workload, model acceptance, proof boolean, native release or hooks are invented.
"""
from pathlib import Path
import argparse,ast,hashlib,json
HERE=Path(__file__).resolve().parent
OLD=Path('/home/holden/mckernel-work/host-preparation/p-m05-fixed-profile-batch-adaptation-20261023-1')
PROFILE_ID='current68-zombie-d8d8-image10972-launcherdca0-p05-short32'
SDK=Path('/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/sdk-build-release/INDEPENDENT-ACTUAL-SDK-ARTIFACT-AND-PHYSICAL-ACCEPTANCE.json')
def need(v,m):
 if not v:raise ValueError(m)
def digest(b):return hashlib.sha256(b).hexdigest()
def bound(r):
 p=Path(r['path']);raw=p.read_bytes();need(digest(raw)==r['sha256'],'exact reference drift');return json.loads(raw)
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--profile',required=True);args=p.parse_args(argv)
 raw=Path(args.profile).read_bytes();profile=json.loads(raw)
 need(profile['profile_id']==PROFILE_ID and profile['prior_cycle_credit']==0 and profile['future_v3_artifacts'] is None,'fixed current zombie tuple and zero prior credit')
 manifest=bound(profile['manifest']);sdk=json.loads(SDK.read_text())
 need({Path(r['path']).name:{'bytes':r['size'],'sha256':r['sha256']}for r in manifest['modules']}=={k:{n:v[n]for n in ('bytes','sha256')}for k,v in sdk['artifacts'].items()},'exact three accepted current SDK modules')
 need(manifest['artifacts']['mckernel_image']['sha256']=='10972f87277e8429e2badd238d3ac53e451b8a2351a8ebf013941e1dfb95e1e2' and manifest['artifacts']['mcexec']['sha256']=='dca0250159ce04a272a72dd1217213a4b6e0f21ec8c21da211eede250c451954','unchanged accepted image and launcher')
 # This raw independent review is a prerequisite supplied by the dispatcher.
 # Three profile/tuple acceptance wrappers are separately required by Hooks.
 first=bound(profile['first_restoration_review'])
 need(first.get('physical_acceptance') is True and first.get('P_M05_02_literal_complete') is True,'actual first complete restoration and physical acceptance required')
 inner_ref=profile['first_restoration_inner_result'];inner=bound(inner_ref)
 need(inner_ref['sha256']==first['inner_result_sha256'],'actual first-review inner result hash')
 actual_argv=inner['admitted_qemu_argv'];need(actual_argv[actual_argv.index('-initrd')+1]==manifest['staging']['derived_initramfs']['path'],'first review belongs to this staged current tuple')
 need(profile['expected_epochs']==[[0,1,1],[0,2,2]],'unchanged two-generation epochs')
 source=(OLD/'native_diagnostic_batch.py').read_text();tree=ast.parse(source)
 names=['operation_ancestry','epoch_authority','resource_decoder','source_cohort','first_restoration_review','release_route','linked_provider','strict_consumer']
 pins={name:profile[name]['sha256']for name in names}
 for name in names:bound(profile[name])
 substitutions=dict(PROFILE_ID=PROFILE_ID,MANIFEST_SHA=profile['manifest']['sha256'],AUTHORITY_SHA=pins)
 lines=source.splitlines(True)
 for node in sorted([n for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(z,ast.Name)and z.id in substitutions for z in n.targets)],key=lambda n:n.lineno,reverse=True):
  name=node.targets[0].id;lines[node.lineno-1:node.end_lineno]=[name+' = '+repr(substitutions[name])+'\n']
 result=''.join(lines);ast.parse(result)
 out=HERE/'reviewed-ten-cycle-successor';need(not out.exists(),'fresh derivative namespace');out.mkdir(mode=0o700)
 (out/'native_diagnostic_batch.py').write_text(result)
 (out/'production_hooks.py').write_bytes((OLD/'production-adapter-1/production_hooks.py').read_bytes())
 (out/'export_closed_owner.py').write_bytes((OLD/'production-adapter-1/export_closed_owner.py').read_bytes())
 (out/'FIXED-CURRENT-PROFILE.json').write_bytes(raw)
 record=dict(status='FIXED_CONSTANTS_DERIVED_FROM_ACTUAL_FIRST_REVIEW_NOT_EXECUTION_RELEASE',profile_sha256=digest(raw),source_sha256=digest(result.encode()),changed_source_assignments=['PROFILE_ID','MANIFEST_SHA','AUTHORITY_SHA'],first_complete_review=profile['first_restoration_review'],future_acceptance_wrappers_required=['sdk_acceptance','launcher_acceptance','first_complete_restoration'],ten_case_release=None,native_runs=0)
 (out/'DERIVATION.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n');print(json.dumps(record))
if __name__=='__main__':main()
