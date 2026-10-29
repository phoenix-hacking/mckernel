#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Only prepare non-authority data skeletons from predecessor admission records.
"""
import hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;A=D.parent;OLD=A/'ROOT-CURRENT119-BUILD-ADMISSION-1'
PROD=A/'M14-CONVERSION-FIRST-PRODUCER-BINDING-1';S=PROD/'current-frontier-successor-1'
GUARD=A/'M14-CONVERSION-FIRST-BUILD-GUARD-PREPARATION-1'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_text())
actual_profile=read(S/'PROFILE.SOURCE-ONLY.json')
assert ref(S/'PROFILE.SOURCE-ONLY.json')['sha256']=='8ab49c299dfc9218ddcf8df3cf71474d51e87167abe4cd166841ea47c3a32e2d'
assert ref(S/'run_build_only.py')['sha256']=='791fcf29b66dde1ff6418763b4307c3704c6a18d768970a5da726ab933b3a2f8'
assert ref(S/'build_only_worker.py')['sha256']=='6d018afbd71aaaa2d497cf4ecb403ae3cf8c5b801f278f51b665cfdc8ab704cc'
oldboot=read(OLD/'ROOT-HOLDER-BOOTSTRAP-GRANT.json');oldresource=read(OLD/'ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.R2.json');oldexport=read(OLD/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json');oldgrant=read(OLD/'ROOT-EXECUTION-INPUT.GRANT-PENDING-REVIEW.R2.json');oldreview=read(OLD/'independent-execution-review-1/REVIEW.R2.ACTUAL.json')
intent=read(GUARD/'ROOT-PRODUCER-INTENT.ACTUAL.json');ctx=intent['context']
assert intent['author']=='/root' and intent['runtime_authority'] is None and ctx['nonce']=='4709c9fae2c743a7acd662e93a663358'
assert ctx['current_free']['sha256']=='5326dd3a1ecf9f679717fcb42e29c75741765f2d46ea443e25d50c355d51654e' and ctx['current_bindings']['sha256']=='d0ef2c4ec7b2cea52711d6c3e46f0b88862af73b4f4ce6b97d7187b253f1f645'
for key in ('request','current_free','current_ledger','current_bindings','candidate_snapshot_manifest','reuse_descriptor'):
 assert ref(ctx[key]['path'])==ctx[key]
assert ref(PROD/'THREE-COMMANDS.SOURCE-ONLY.json')['sha256']=='79a0054d5771b4bdb1bade8156c77533a31d5d68b17a5c41daa31cc36947159b'
assert ref(S/'hold_and_run_build_only.py')['sha256']=='d17bd70e3e3e6ef7febe48b6f0f892ab6f1a94c74e89d43808bbea8b5dc21551'
assert oldresource['reservation_kind']=='PERMANENT_27_4_ONE_HEAVY_AFTER_CLEARANCE' and oldresource['cpus']==[2,3,4,5] and oldresource['container_memory_bytes']==12884901888 and oldresource['container_pids']==512
assert oldboot['decision']=='GRANT_ONE_POSTCLEANUP27_4_BUILD_ONLY_HOLDER' and oldgrant['decision']=='GRANT_ONE_CURRENT290_BUILD_ONLY' and oldreview['decision']=='PASS_EXACT_BUILD_ONLY_EXECUTION'
assert oldexport['SDK21_recompiled'] is False and oldexport['source6153_entries']==6153
future=A/'ROOT-CONVERSION-FIRST-BUILD-ADMISSION-1'
bootstrap={k:None for k in oldboot};bootstrap.update(decision=oldboot['decision'],maximum_invocations=1,permanent_mutex_path=oldboot['permanent_mutex_path'],fresh_handshake_root=str(future/'HOLDER'))
resource={k:None for k in oldresource};resource.update(cpus=[2,3,4,5],container_memory_bytes=12884901888,container_pids=512,heavy_slots_held=1,other_heavy_slots=0,reservation_kind='PERMANENT_27_4_ONE_HEAVY_AFTER_CLEARANCE',coexistence_decision='REVIEWED_POSTCLEANUP_ONE_HEAVY',fresh_output_root=str(future/'OUTPUT'))
resource['actual_observations']={k:None for k in oldresource['actual_observations']}
resource['reservation_holder']={'device':27,'inode':4,'path':oldboot['permanent_mutex_path'],'pid':None,'starttime':None,'fd':None}
export={k:None for k in oldexport};export.update(scope=SCOPE,decision='PASS_EXACT_UID1000_READONLY_BUILD_EXPORTS',runtime_authority=None,Rust_release='1.95.0-nightly',GCC_major=14,SDK21_recompiled=False,source6153_entries=6153)
pending={k:None for k in oldgrant};pending.update(decision='GRANT_ONE_CURRENT290_BUILD_ONLY',maximum_invocations=1,fresh_output_root=str(future/'OUTPUT'),root_docker_client_only=True,docker_client_prefix=oldgrant['docker_client_prefix'])
review={k:None for k in oldreview};review.update(schema=oldreview['schema'],decision='PASS_EXACT_BUILD_ONLY_EXECUTION',scope=SCOPE,independent=None,implementation_ownership=None,runtime_authority=None,artifact_acceptance=False,native_acceptance=False,root_docker_client_only=True,docker_client_prefix=oldgrant['docker_client_prefix'],fresh_output_root=str(future/'OUTPUT'))
go={'author':None,'nonce':None,'grant':None}
for name,data in [('HOLDER-BOOTSTRAP.TEMPLATE.NOT-AUTHORITY.json',bootstrap),('RESOURCE.TEMPLATE.NOT-AUTHORITY.json',resource),('INPUT-EXPORT.TEMPLATE.NOT-AUTHORITY.json',export),('PENDING-GRANT.TEMPLATE.NOT-AUTHORITY.json',pending),('EXECUTION-REVIEW.TEMPLATE.NOT-AUTHORITY.json',review),('HOLDER-GO.TEMPLATE.NOT-AUTHORITY.json',go)]:
 (D/name).write_text(json.dumps(data,indent=2)+'\n')
assert all(x['author'] is None for x in (bootstrap,resource,export,pending,go)) and review['reviewer'] is None and review['independent'] is None
assert all(x is None for x in (bootstrap['runner'],bootstrap['profile'],bootstrap['worker'],bootstrap['nonce'],resource['observed_at_epoch'],resource['reservation_ready_record'],export['qualified_readonly_files'],pending['profile'],pending['runner'],pending['resource_authority'],pending['review']))
mi=actual_profile['inputs'];manifest=read(mi['source_directory_exports'][0]['manifest']['path'])
qualified=[r['source'] for r in mi['configuration']]+[r['source'] for r in mi['objects'] if not r['replace']]+[r['postimage'] for r in mi['postimages']]+[r['snapshot'] for r in manifest['files']]+[r['source'] for r in mi['external_relative_modules']]
assert [len(mi['configuration']),sum(not r['replace'] for r in mi['objects']),len(mi['postimages']),len(manifest['files']),len(mi['external_relative_modules'])]==[10,9,6,149,3] and len(qualified)==177
(D/'QUALIFIED-FILES.CANDIDATE.NOT-AUTHORITY.json').write_text(json.dumps(dict(scope=SCOPE,status='CANDIDATE_FILE_CLOSURE_NOT_UID1000_READABILITY_AUTHORITY',profile=ref(S/'PROFILE.SOURCE-ONLY.json'),qualified_readonly_files=qualified,runtime_authority=None),indent=2)+'\n')
context={'scope':SCOPE,'status':'KNOWN_SOURCE_CONTEXT_NOT_CURRENT_ADMISSION','producer_intent':ref(GUARD/'ROOT-PRODUCER-INTENT.ACTUAL.json'),'selected_context':ctx,'guard_source':ref(GUARD/'runtime_guard.py'),'guard_independent_review':'PASS_SOURCE_AND_OPERATION_AS_REPORTED_BY_ROOT; REVALIDATE_ACTUAL_FRESH_GATES','producer_recipe':ref(PROD/'THREE-COMMANDS.SOURCE-ONLY.json'),'predecessor_resource_shape':ref(OLD/'ROOT-ACTUAL-BUILD-RESOURCE-AUTHORITY.R2.json'),'predecessor_export_shape':ref(OLD/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json'),'predecessor_holder_shape':ref(OLD/'ROOT-HOLDER-BOOTSTRAP-GRANT.json'),'predecessor_grant_shape':ref(OLD/'ROOT-EXECUTION-INPUT.GRANT-PENDING-REVIEW.R2.json'),'predecessor_execution_review_shape':ref(OLD/'independent-execution-review-1/REVIEW.R2.ACTUAL.json'),'holder_source':ref(S/'hold_and_run_build_only.py'),'sealed_source_profile':ref(S/'PROFILE.SOURCE-ONLY.json'),'sealed_runner':ref(S/'run_build_only.py'),'sealed_worker':ref(S/'build_only_worker.py'),'root_source_binding':ref(S/'ROOT-SOURCE-BINDING.ACTUAL.json'),'guard_source_review':ref(GUARD/'independent-source-review-1/SOURCE-REVIEW.ACTUAL.json'),'guard_operation_review':ref(GUARD/'independent-source-review-1/OPERATION-REVIEW.ACTUAL.json'),'guard_actual_binding':ref(GUARD/'ROOT-PRODUCER-GUARD-BINDING.ACTUAL.json'),'candidate_qualified_files':ref(D/'QUALIFIED-FILES.CANDIDATE.NOT-AUTHORITY.json'),'proposed_fresh_namespace':str(future),'runtime_authority':None}
(D/'SOURCE-CONTEXT.NOT-AUTHORITY.json').write_text(json.dumps(context,indent=2)+'\n')
print('PASS_NONAUTHORITY_ADMISSION_DATA_TEMPLATES')
