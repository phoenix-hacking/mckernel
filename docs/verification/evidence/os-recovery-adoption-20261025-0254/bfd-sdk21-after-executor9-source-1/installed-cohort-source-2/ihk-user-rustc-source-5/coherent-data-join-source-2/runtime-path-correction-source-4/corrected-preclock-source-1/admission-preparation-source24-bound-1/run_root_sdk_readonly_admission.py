"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only actual SDK capacity/identity/image admission; no target, lease, container or cleanup entry.
"""
from pathlib import Path
import sys,json,hashlib,os,time
D=Path(__file__).parent
import importlib.util
assert len(sys.argv)==2
inputs_path=D/'QUERY-INPUTS.ROOT.json'
raw=inputs_path.read_bytes()
assert hashlib.sha256(raw).hexdigest()==sys.argv[1]
inputs=json.loads(raw)
assert set(inputs)=={'request','request_sha256'} and isinstance(inputs['request'],str)
request_path=Path(inputs['request'])
assert request_path.is_absolute() and request_path.parent==Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/runtime-path-correction-source-4')
request_raw=request_path.read_bytes()
assert hashlib.sha256(request_raw).hexdigest()==inputs['request_sha256']
request=json.loads(request_raw)
assert request['request_path']==str(request_path)
OWNER = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/runtime-path-correction-source-4/native_running_external_modules_owner.INSTALLED-OWNER-CORRECTED.py')
assert hashlib.sha256(OWNER.read_bytes()).hexdigest()=='ab6a91396fa803ff3ec75cfee255ea4110e7a1eaebf854cbda0904351018e0f5'
spec=importlib.util.spec_from_file_location('library_sdk_admission_owner',OWNER)
owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
source_sha256 = {'scripts/native_exact_historical_lease_observer.py': '463ae558e141c2a6fe5a016fb19baddb26ed883c3bf6d39c114b27711ee78a51', 'scripts/native_running_external_modules_offline.py': '87f1d3d67a86bd7e7bcf622b01417937176a75a3dc0414ae4e12f842a9ec9d58', 'scripts/native_running_external_modules_owner.py': 'ab6a91396fa803ff3ec75cfee255ea4110e7a1eaebf854cbda0904351018e0f5', 'scripts/native_rust_exact_build_container_owner.py': '96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1', 'scripts/native_rust_exact_build_image_prepare.py': '45cb12e0fd58d164468badfb99a3ed922e65e06046bf38b4a50e27e18595a27b', 'scripts/native_rust_exact_build_image_rebind.py': 'f10ab116e55a24e8db7a8157d71efdd01198ba3453a8141bc8bbf596eda6b61e', 'scripts/native_rust_exact_build_image_rebind_probe.py': '412d46de7e078746a7ec979a13ccb25753d6fa34708610932e35be8f02a89635', 'scripts/native_rust_exact_build_offline.py': 'cc243126ab8cc0754c62175c77e46d6ba0d98294f8168cc77893a2c12249cd1a', 'scripts/native_rust_exact_disk_build_wrapper.py': 'c252ee341eb61752704f8b818503c0a5dc97400845494707ca3110f5f23df6d1', 'scripts/native_rust_exact_mckernel_image_container_owner.py': 'e9861cf73b0328c9fe2eacb987ea179933146cbeddbc3951405d4e60e89560f4', 'scripts/tests/test_native_running_external_modules_owner.py': 'c816f7dfd6fa167670876d8e64e8474bec119e1f19280fcc1cb902dff1a2c340'}
owner.validate_runtime_source_bindings(source_sha256)
STATIC_SOURCE_PROOF = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ACTUAL-FETCHED-BFD24-CORRECTED-SOURCE-D5B3D798.json', 'bytes': 24909, 'sha256': '9725c0ca9e65d069a96442015051f2116ea8f519557d9cd0f6364a1e0db71a95'}
STATIC_SOURCE_APPROVAL = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ACTUAL-OWNER-CONSUMABLE-BFD24-SOURCE-APPROVAL.json', 'bytes': 2435, 'sha256': '259ce8e57c2ad769ad1b5c10c37f8eb64d8f111ad81a30c872240c052be4f626'}
assert STATIC_SOURCE_PROOF is not None and STATIC_SOURCE_APPROVAL is not None, 'genuine fetched30 sourceproof and independent11 approval required'
source_proof=owner.bound({field:STATIC_SOURCE_PROOF[field] for field in ('path','sha256')})
source_approval=owner.bound({field:STATIC_SOURCE_APPROVAL[field] for field in ('path','sha256')})
assert source_approval['decision']=='PASS_SOURCE' and source_approval['implementation_ownership'] is False and source_approval['source_sha256']==source_sha256

# Genuine F4D SDK producer success/current acceptance; no historical03c/P12 authority substitution.
F4D_ACCEPTANCE = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/F4D-ACTUAL-PHYSICAL-AND-CURRENT-ACCEPTANCE.json', 'bytes': 2492, 'sha256': 'b0bda4434a541afaecf7d4b9e94d3242e871d5104aebba033e033667a967cb21'}
F4D_RAW_REFS = {'0/stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-f4d-sdk-producer-success-physical-postflight-source-1/artifact-snapshot-schema-source-revision-2/0/stdout', 'bytes': 44983, 'sha256': 'f0d4e9551eb62a8571a3a9c41e9a49f16da442206be1899e40c3b6bae36d1e72'}, '0/WHOLE-JOIN.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-f4d-sdk-producer-success-physical-postflight-source-1/artifact-snapshot-schema-source-revision-2/0/WHOLE-JOIN.json', 'bytes': 1405, 'sha256': 'c34553ba49e697119517fe73e7cf86223fe71e4205de00dc4ff8186b46a5df57'}, '1/stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-f4d-sdk-producer-success-physical-postflight-source-1/artifact-snapshot-schema-source-revision-2/1/stdout', 'bytes': 46884, 'sha256': '66481de95cbf9b4b24c4772001c41bb3b2bc4dc91c03877896b9d18c1992c088'}, '1/WHOLE-JOIN.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-f4d-sdk-producer-success-physical-postflight-source-1/artifact-snapshot-schema-source-revision-2/1/WHOLE-JOIN.json', 'bytes': 1404, 'sha256': 'c79a66e7a653048639f6fad193e8e06c91f08ee4b15816c0a37c69dfe19e4978'}, 'actual-helpers-postjoin-1/0/stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-f4d-sdk-producer-success-physical-postflight-source-1/artifact-snapshot-schema-source-revision-2/actual-helpers-postjoin-1/0/stdout', 'bytes': 48362, 'sha256': '324e5e3b7a68d100342598b66a0410b86b571b04e924fa4993fff374e45c7335'}, 'actual-helpers-postjoin-1/0/WHOLE-JOIN.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-f4d-sdk-producer-success-physical-postflight-source-1/artifact-snapshot-schema-source-revision-2/actual-helpers-postjoin-1/0/WHOLE-JOIN.json', 'bytes': 1456, 'sha256': 'e715cdcc38006e41f978e89b5357a3437dbc65fe3383940854a42f4b71dd6e36'}}
F4D_EXPECTED_ACCEPTANCE = {'schema': 'mckernel.m15.executor.sdk-producer-success.current-acceptance.v1', 'status': 'PASS', 'reviewer': '/root/recovery_review', 'implementation_ownership': False, 'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.', 'physical_acceptance': True, 'current_postjoin_acceptance': True, 'evidence_root': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-f4d-sdk-producer-success-physical-postflight-source-1/artifact-snapshot-schema-source-revision-2', 'evidence_sha256_by_relative_path': {'0/stdout': 'f0d4e9551eb62a8571a3a9c41e9a49f16da442206be1899e40c3b6bae36d1e72', '0/WHOLE-JOIN.json': 'c34553ba49e697119517fe73e7cf86223fe71e4205de00dc4ff8186b46a5df57', '1/stdout': '66481de95cbf9b4b24c4772001c41bb3b2bc4dc91c03877896b9d18c1992c088', '1/WHOLE-JOIN.json': 'c79a66e7a653048639f6fad193e8e06c91f08ee4b15816c0a37c69dfe19e4978', 'actual-helpers-postjoin-1/0/stdout': '324e5e3b7a68d100342598b66a0410b86b571b04e924fa4993fff374e45c7335', 'actual-helpers-postjoin-1/0/WHOLE-JOIN.json': 'e715cdcc38006e41f978e89b5357a3437dbc65fe3383940854a42f4b71dd6e36'}, 'owner': [579459, '70867966'], 'prior_helpers': [[583813, '70914604'], [583810, '70914596'], [583818, '70914644'], [583815, '70914638']], 'postjoin_python': [584138, '70920853'], 'postjoin_sudo': [584135, '70920846'], 'runtime_nonce': 'f4dcf272cd194553825efd493d5c034a', 'operation_lease_nonce': '147a992ae4af459f96a1592540c5a510', 'container_id': 'a90b15151293983db424078fac928449ca1b3d5ce026bbca003a5e928bf17382', 'protected_refs': 577, 'candidate': {'entries': 557, 'files': 446, 'bytes': 3527255}, 'SDK_command_records': 9, 'SDK_commands_executed': 6, 'retained_prefix_indices': [0, 1, 2], 'new_command_indices': [3, 4, 5, 6, 7, 8], 'inner_command_births_namespace': 'container', 'permanent_mutex': {'device': 27, 'inode': 4, 'free_before': True, 'free_after': True, 'flock_acquired': False}, 'original_failed_observer_preserved': True, 'original_failed_python_birth': None, 'native_acceptance': False, 'default_acceptance': False, 'heavy_execution_released': False}
F4D_TERMINAL = {'bytes': 2524, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/F4D-ACTUAL-SDK-SUFFIX-RESULT-AND-TOOL-TERMINAL.json', 'sha256': '596f2718898b42ff4b7b4772648d2f9b3b0e39c1ecda2ee524030f6c44c532e7'}
F4D_INVENTORY = {'bytes': 242240, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-f4d-sdk-producer-success-physical-postflight-source-1/EXACT-F4D-SDK-PRODUCER-CANDIDATE-FD-INVENTORY.json', 'sha256': 'f135705b37c5a5d60553265ca7ac4d095a400c1be73445474827a1ef81f32496'}
F4D_MANIFEST = {'bytes': 345038, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-f4d-sdk-producer-success-physical-postflight-source-1/artifact-snapshot-schema-source-revision-2/EXACT-F4D-ARTIFACT-SNAPSHOT-SCHEMA-CORRECTED.INPUTS.json', 'sha256': '435aaf56635931fcafe1f8d95b874a38153f7eb382a5434b29aca6461b98f5fd'}
acceptance=owner.bound({field:F4D_ACCEPTANCE[field] for field in ('path','sha256')});assert acceptance==F4D_EXPECTED_ACCEPTANCE
assert acceptance['status']=='PASS' and acceptance['physical_acceptance'] is True and acceptance['current_postjoin_acceptance'] is True and acceptance['implementation_ownership'] is False
observed={k:owner.bound({field:v[field] for field in ('path','sha256')}) for k,v in F4D_RAW_REFS.items()}
current_proc=observed['0/stdout'];current_physical=observed['1/stdout'];current_postjoin=observed['actual-helpers-postjoin-1/0/stdout']
assert current_proc['status']=='PASS_M15_EXECUTOR_SDK_PRODUCER_SUCCESS_EXACT_PROC'
assert current_physical['status']=='PASS_M15_EXECUTOR_SDK_PRODUCER_SUCCESS_MUTEX_HELD_CURRENT_PHYSICAL'
assert current_postjoin['status']=='PASS_M15_EXECUTOR_SDK_PRODUCER_SUCCESS_CURRENT_HELPERS_POSTJOIN_MUTEX_FREE'
for row in [current_proc,current_physical,current_postjoin]:
 assert row['original_workload_status']=='PASS' and row['SDK_command_records']==9 and row['SDK_commands_executed']==6 and row['retained_prefix_indices']==[0,1,2] and row['new_command_indices']==[3,4,5,6,7,8]
 assert row['owner']=={'pid':579459,'starttime':'70867966'} and row['direct_terminal']==F4D_TERMINAL and row['manifest']==F4D_MANIFEST
for name,pid,start,stream in [('0/WHOLE-JOIN.json',583810,70914596,'0/stdout'),('1/WHOLE-JOIN.json',583815,70914638,'1/stdout'),('actual-helpers-postjoin-1/0/WHOLE-JOIN.json',584135,70920846,'actual-helpers-postjoin-1/0/stdout')]:
 row=observed[name];assert row['pid']==pid and int(row['start'])==start and row['returncode']==0
 assert all(row[k] is True for k in ['direct_child_joined','group_absent','closed_streams']) and row['error'] is None and row['retirement_error'] is None and row['timed_out'] is False and row['remaining_group_members']==row['unexpected_group_members']==[]
 assert row['captures']['stdout']['sha256']==F4D_RAW_REFS[stream]['sha256']
assert current_postjoin['current_reader_identity']['pid']==584138 and current_postjoin['current_reader_identity']['starttime']=='70920853'
assert current_postjoin['permanent_mutex_free_before'] is True and current_postjoin['permanent_mutex_free_after'] is True and current_postjoin['flock_acquired'] is False and current_postjoin['terminal_evidence_unchanged'] is True
assert current_physical['partial_candidate_inventory']==F4D_INVENTORY
terminal=owner.bound({field:F4D_TERMINAL[field] for field in ('path','sha256')});inventory=owner.bound({field:F4D_INVENTORY[field] for field in ('path','sha256')});owner.bound({field:F4D_MANIFEST[field] for field in ('path','sha256')})
assert inventory['entry_count']==557 and inventory['file_count']==446 and inventory['total_file_bytes']==3527255
# All accepted outer HOST owner/helper births must remain absent; inner SDK command births are a separate container namespace.
for pid,start in acceptance['prior_helpers']+[acceptance['owner'],acceptance['postjoin_python'],acceptance['postjoin_sudo']]:
 try:actual=owner.image._proc_starttime(pid)
 except FileNotFoundError:actual=None
 assert actual!=str(start), 'accepted F4D outer process still live'

PRIOR_FAILED_BFD_QUERY_BIRTH = {'bytes': 1196, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/preclock-F4D-source-3/admission-preparation-bound-1/root-readonly-admission-capture-1/DIRECT-PROCESS-BEFORE-EXEC.json', 'sha256': '589b483106302bfd7f86813555164f7f8c6fabc7903bc35a1b98f22a5de30445'}
PRIOR_FAILED_BFD_QUERY_EXIT = {'bytes': 168, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/preclock-F4D-source-3/admission-preparation-bound-1/root-readonly-admission-capture-1/ACTUAL-DIRECT-CHILD-EXIT.json', 'sha256': '8c508d4da546463f7e4b773529eb878c385570d8ab61137c58a13b014803172f'}
prior_failed_birth=owner.bound({field:PRIOR_FAILED_BFD_QUERY_BIRTH[field] for field in ('path','sha256')})
prior_failed_exit=owner.bound({field:PRIOR_FAILED_BFD_QUERY_EXIT[field] for field in ('path','sha256')})
assert prior_failed_birth['pid']==prior_failed_exit['pid']==588566 and prior_failed_exit['returncode']==1 and prior_failed_exit['direct_child_joined'] is True
try:prior_failed_actual_birth=owner.image._proc_starttime(prior_failed_birth['pid'])
except FileNotFoundError:prior_failed_actual_birth=None
assert prior_failed_actual_birth!=str(prior_failed_birth['starttime']), 'failed prior BFD query identity remains live'

owner.output_namespace(request)
mount=owner.live_admission(request);capacity=owner.measure(request)
conflicts={owner.LEASE,owner.COMMON,Path(owner.shared.SHARED_HEAVY_LOCK_PATH),Path(owner.image.COMMON_EXCLUSION),Path(owner.host.OPERATIONAL_EXCLUSION_PATH)}
conflicts.update(owner.ROOT.glob('native-exact-mckernel-image-lease-*.json'))
assert not any(os.path.lexists(p) for p in conflicts)
E=D/'root-readonly-admission-preview-1';E.mkdir(mode=0o700)
with owner.DeferredSignals() as latch:
 client=owner.ExternalDocker(E/'image-inspect.log',latch,sudo=True)
 result=client.call(['image','inspect',request['image_id']],timeout=15)
 assert result.returncode==0 and not client.client_retirement_unproven
 info=json.loads(result.stdout);assert len(info)==1 and info[0]['Id']==request['image_id'] and info[0]['Architecture']=='amd64'
 client.check_all_client_groups();assert not client.client_retirement_unproven
summary=dict(scope=__doc__,status='PASS_READONLY_SDK_CAPACITY_IDENTITY_IMAGE_ONLY',at=time.time(),request_sha256=inputs['request_sha256'],resources=capacity,mount=mount,image_id=info[0]['Id'],image_Architecture=info[0]['Architecture'],group_checks=client.group_checks,conflict_paths_absent=[str(p) for p in sorted(conflicts)],current_physical_acceptance=F4D_RAW_REFS['1/stdout']['sha256'],current_postjoin=F4D_RAW_REFS['actual-helpers-postjoin-1/0/stdout']['sha256'],current_independent_acceptance=F4D_ACCEPTANCE,current_retained_closure=F4D_RAW_REFS,current_clearance_scope=current_physical['status'],current_owner_identity=current_physical['owner'],original_workload_status='PASS',SDK_commands_executed=6,SDK_command_records=9,retained_prefix_indices=[0,1,2],new_command_indices=[3,4,5,6,7,8],original_direct_terminal=F4D_TERMINAL,source_proof=STATIC_SOURCE_PROOF,source_approval=STATIC_SOURCE_APPROVAL,target_calls=0,container_create_calls=0,execution_release=False)
(E/'ADMISSION.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(status=summary['status'],at=summary['at'],resources=capacity,image=info[0]['Id'],target_calls=0)))
