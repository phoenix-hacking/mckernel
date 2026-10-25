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
assert request_path.is_absolute() and request_path.parent==Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/stripped-storage-correction-source-6/two-command-owner-source-1')
request_raw=request_path.read_bytes()
assert hashlib.sha256(request_raw).hexdigest()==inputs['request_sha256']
request=json.loads(request_raw)
assert request['request_path']==str(request_path)
OWNER = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/stripped-storage-correction-source-6/two-command-owner-source-1/bfd_original_c_twice_owner.py')
assert hashlib.sha256(OWNER.read_bytes()).hexdigest()=='c6ffabc59f8ed610d89e632b6ca47250aef964d6a7d7bd08a0171ccab89850b9'
spec=importlib.util.spec_from_file_location('library_sdk_admission_owner',OWNER)
owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
source_sha256 = {'scripts/native_exact_historical_lease_observer.py': '463ae558e141c2a6fe5a016fb19baddb26ed883c3bf6d39c114b27711ee78a51', 'scripts/native_running_external_modules_offline.py': '5cd7b98dbefac4063734539935a13a7735f77aef38d79eaec7bf6bcd96c25de7', 'scripts/native_running_external_modules_owner.py': 'c6ffabc59f8ed610d89e632b6ca47250aef964d6a7d7bd08a0171ccab89850b9', 'scripts/native_rust_exact_build_container_owner.py': '96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1', 'scripts/native_rust_exact_build_image_prepare.py': '45cb12e0fd58d164468badfb99a3ed922e65e06046bf38b4a50e27e18595a27b', 'scripts/native_rust_exact_build_image_rebind.py': 'f10ab116e55a24e8db7a8157d71efdd01198ba3453a8141bc8bbf596eda6b61e', 'scripts/native_rust_exact_build_image_rebind_probe.py': '412d46de7e078746a7ec979a13ccb25753d6fa34708610932e35be8f02a89635', 'scripts/native_rust_exact_build_offline.py': 'cc243126ab8cc0754c62175c77e46d6ba0d98294f8168cc77893a2c12249cd1a', 'scripts/native_rust_exact_disk_build_wrapper.py': 'c252ee341eb61752704f8b818503c0a5dc97400845494707ca3110f5f23df6d1', 'scripts/native_rust_exact_mckernel_image_container_owner.py': 'e9861cf73b0328c9fe2eacb987ea179933146cbeddbc3951405d4e60e89560f4', 'scripts/tests/test_native_running_external_modules_owner.py': 'c816f7dfd6fa167670876d8e64e8474bec119e1f19280fcc1cb902dff1a2c340'}
owner.validate_runtime_source_bindings(source_sha256)
STATIC_SOURCE_PROOF = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ACTUAL-FETCHED-CORRECTED-BFD-C-C-SOURCE25-94D9FEE8.json', 'bytes': 28379, 'sha256': '7b9d13e9bb33fb44deb98799119d454b5c0da3f924a17649d6a0cd7196268894'}
STATIC_SOURCE_APPROVAL = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ACTUAL-OWNER-CONSUMABLE-CORRECTED-BFD-C-C-SOURCE-APPROVAL.json', 'bytes': 2665, 'sha256': '8b537cd872c85dd401ee69b647a4fc0a501dde924c9ff14ad5e0d20e44aaa823'}
assert STATIC_SOURCE_PROOF is not None and STATIC_SOURCE_APPROVAL is not None, 'genuine fetched30 sourceproof and independent11 approval required'
source_proof=owner.bound({field:STATIC_SOURCE_PROOF[field] for field in ('path','sha256')})
source_approval=owner.bound({field:STATIC_SOURCE_APPROVAL[field] for field in ('path','sha256')})
assert source_approval['decision']=='PASS_SOURCE' and source_approval['implementation_ownership'] is False and source_approval['source_sha256']==source_sha256

# Genuine current BFD qualifier-failure physical/postjoin authority; not Rust/SDK acceptance.
CURRENT_BFD_ACCEPTANCE = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/BFD-C-C-ACTUAL-PHYSICAL-AND-CURRENT-ACCEPTANCE.json', 'bytes': 2550, 'sha256': '83ffc406fecbec77016b657aed9e61936bb2bc2b71d55044d50cedaae5ced7c2'}
CURRENT_BFD_RAW_REFS = {'0/stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-original-c-twice-failure-physical-postflight-source-1/0/stdout', 'bytes': 41796, 'sha256': '12dc4b2dbc1382e8a3b44fdd4554d84f2c20c7f0cfac9a56383e929e953df23d'}, '0/WHOLE-JOIN.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-original-c-twice-failure-physical-postflight-source-1/0/WHOLE-JOIN.json', 'bytes': 1326, 'sha256': '55425f865e5c1e9640ea3fb53e2468ea803d6d10411df1836ebdb09b2b2435e1'}, '1/stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-original-c-twice-failure-physical-postflight-source-1/1/stdout', 'bytes': 43703, 'sha256': 'bd0623c6d3d8012aca9e336a11f82681ee4a74634e1453facaf7ce93aa232d57'}, '1/WHOLE-JOIN.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-original-c-twice-failure-physical-postflight-source-1/1/WHOLE-JOIN.json', 'bytes': 1326, 'sha256': 'c2519764ff890411c95bd7c43abbfc035c81e1648c404d5379f8b3d2b9dcd9e0'}, 'actual-helpers-postjoin-1/0/stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-original-c-twice-failure-physical-postflight-source-1/actual-helpers-postjoin-1/0/stdout', 'bytes': 44538, 'sha256': 'ad05e23779460678fcf5ad386f10cc0acb85824cf1a204f9c34f2ed9f1ec8848'}, 'actual-helpers-postjoin-1/0/WHOLE-JOIN.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-original-c-twice-failure-physical-postflight-source-1/actual-helpers-postjoin-1/0/WHOLE-JOIN.json', 'bytes': 1378, 'sha256': 'de188deacc44999a3eab7f5c8edc4faa5e32d101dd085d55bd1ee8d83344ebdf'}}
CURRENT_BFD_EXPECTED_ACCEPTANCE = {'schema': 'mckernel.m15.executor.bfd.original-c-twice-failure.current-acceptance.v1', 'status': 'PASS', 'reviewer': '/root/recovery_review', 'implementation_ownership': False, 'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Failed C/C operation normal retirement physical and current postjoin only.', 'physical_acceptance': True, 'current_postjoin_acceptance': True, 'owner': [612401, '71305831'], 'runtime_nonce': '7c9a8056f1234f1e9dce8f40dcd500ef', 'operation_lease_nonce': '72d0671722154cc4b85e20116a88375f', 'container_id': '675ec177ffe190a4bb6363dc7dcccb8f0a947d5f5da2b0a138ab007951423d42', 'evidence_root': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-original-c-twice-failure-physical-postflight-source-1', 'evidence_sha256_by_relative_path': {'0/stdout': '12dc4b2dbc1382e8a3b44fdd4554d84f2c20c7f0cfac9a56383e929e953df23d', '0/WHOLE-JOIN.json': '55425f865e5c1e9640ea3fb53e2468ea803d6d10411df1836ebdb09b2b2435e1', '1/stdout': 'bd0623c6d3d8012aca9e336a11f82681ee4a74634e1453facaf7ce93aa232d57', '1/WHOLE-JOIN.json': 'c2519764ff890411c95bd7c43abbfc035c81e1648c404d5379f8b3d2b9dcd9e0', 'actual-helpers-postjoin-1/0/stdout': 'ad05e23779460678fcf5ad386f10cc0acb85824cf1a204f9c34f2ed9f1ec8848', 'actual-helpers-postjoin-1/0/WHOLE-JOIN.json': 'de188deacc44999a3eab7f5c8edc4faa5e32d101dd085d55bd1ee8d83344ebdf'}, 'protected_refs': 108, 'candidate': {'entries': 19, 'files': 15, 'bytes': 6515124}, 'prior_helpers': [[614187, '71334571'], [614184, '71334564'], [614192, '71334603'], [614189, '71334596']], 'postjoin_python': [615464, '71355278'], 'postjoin_sudo': [615461, '71355271'], 'permanent_mutex': {'device': 27, 'inode': 4, 'free_before': True, 'free_after': True, 'flock_acquired': False}, 'original_workload_status': 'FAIL', 'qualifier_capture_count': 1, 'qualification_commands_recorded': 2, 'qualification_successful_prefix_count': 1, 'qualification_failure_rc': -6, 'inner_command_births_namespace': 'container', 'pointer_hypothesis_observed': False, 'Rust_ABI_acceptance': False, 'SDK_acceptance': False, 'native_acceptance': False, 'default_acceptance': False, 'heavy_execution_released': False}
CURRENT_BFD_TERMINAL = {'bytes': 1578, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/BFD-C-C-ACTUAL-FIRST-ATTEMPT-TOOL-TERMINAL.json', 'sha256': '721b4cec94d4642300aca4c2030fc4d2e7ac62b6e48f0039c342f813dc55b44d'}
CURRENT_BFD_INVENTORY = {'bytes': 7977, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-original-c-twice-failure-physical-postflight-source-1/EXACT-BFD-ORIGINAL-C-TWICE-CANDIDATE-FD-INVENTORY.json', 'sha256': '29513d151fe204e84679fca9188cc1fa742e61cf73ec3fd2b7796d99b4214894'}
CURRENT_BFD_MANIFEST = {'bytes': 105647, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-original-c-twice-failure-physical-postflight-source-1/EXACT-BFD-ORIGINAL-C-TWICE-FAILURE-NORMAL-RETIREMENT.INPUTS.json', 'sha256': '567ac9c3c61b6fa09934491fc68b17d4ca626899e294ca533e6d25204752153e'}
acceptance=owner.bound({field:CURRENT_BFD_ACCEPTANCE[field] for field in ('path','sha256')});assert acceptance==CURRENT_BFD_EXPECTED_ACCEPTANCE
assert acceptance['status']=='PASS' and acceptance['physical_acceptance'] is True and acceptance['current_postjoin_acceptance'] is True and acceptance['implementation_ownership'] is False
observed={key:owner.bound({field:row[field] for field in ('path','sha256')}) for key,row in CURRENT_BFD_RAW_REFS.items()}
current_proc=observed['0/stdout'];current_physical=observed['1/stdout'];current_postjoin=observed['actual-helpers-postjoin-1/0/stdout']
assert current_proc['status']=='PASS_M15_EXECUTOR_BFD_ORIGINAL_C_TWICE_FAILURE_EXACT_PROC'
assert current_physical['status']=='PASS_M15_EXECUTOR_BFD_ORIGINAL_C_TWICE_FAILURE_MUTEX_HELD_CURRENT_PHYSICAL'
assert current_postjoin['status']=='PASS_M15_EXECUTOR_BFD_ORIGINAL_C_TWICE_FAILURE_CURRENT_HELPERS_POSTJOIN_MUTEX_FREE'
for row in [current_proc,current_physical,current_postjoin]:
 assert row['original_workload_status']=='FAIL' and row['qualifier_capture_count']==1 and row['qualification_commands_recorded']==2
 assert row['owner']=={'pid':612401,'starttime':'71305831'} and row['direct_terminal']==CURRENT_BFD_TERMINAL and row['manifest']==CURRENT_BFD_MANIFEST
for name,pid,start,stream in [('0/WHOLE-JOIN.json',614184,71334564,'0/stdout'),('1/WHOLE-JOIN.json',614189,71334596,'1/stdout'),('actual-helpers-postjoin-1/0/WHOLE-JOIN.json',615461,71355271,'actual-helpers-postjoin-1/0/stdout')]:
 row=observed[name];assert row['pid']==pid and int(row['start'])==start and row['returncode']==0
 assert all(row[k] is True for k in ['direct_child_joined','group_absent','closed_streams']) and row['error'] is None and row['retirement_error'] is None and row['timed_out'] is False and row['remaining_group_members']==row['unexpected_group_members']==[]
 assert row['captures']['stdout']['sha256']==CURRENT_BFD_RAW_REFS[stream]['sha256']
assert current_postjoin['current_reader_identity']['pid']==615464 and current_postjoin['current_reader_identity']['starttime']=='71355278'
assert current_postjoin['permanent_mutex_free_before'] is True and current_postjoin['permanent_mutex_free_after'] is True and current_postjoin['flock_acquired'] is False and current_postjoin['terminal_evidence_unchanged'] is True
assert current_physical['partial_candidate_inventory']==CURRENT_BFD_INVENTORY
terminal=owner.bound({field:CURRENT_BFD_TERMINAL[field] for field in ('path','sha256')});inventory=owner.bound({field:CURRENT_BFD_INVENTORY[field] for field in ('path','sha256')});owner.bound({field:CURRENT_BFD_MANIFEST[field] for field in ('path','sha256')})
assert inventory['entry_count']==19 and inventory['file_count']==15 and inventory['total_file_bytes']==6515124
for pid,start in acceptance['prior_helpers']+[acceptance['owner'],acceptance['postjoin_python'],acceptance['postjoin_sudo']]:
 try:actual=owner.image._proc_starttime(pid)
 except FileNotFoundError:actual=None
 assert actual!=str(start), 'accepted prior BFD outer process remains live'

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
summary=dict(scope=__doc__,status='PASS_READONLY_SDK_CAPACITY_IDENTITY_IMAGE_ONLY',at=time.time(),request_sha256=inputs['request_sha256'],resources=capacity,mount=mount,image_id=info[0]['Id'],image_Architecture=info[0]['Architecture'],group_checks=client.group_checks,conflict_paths_absent=[str(p) for p in sorted(conflicts)],current_physical_acceptance=CURRENT_BFD_RAW_REFS['1/stdout']['sha256'],current_postjoin=CURRENT_BFD_RAW_REFS['actual-helpers-postjoin-1/0/stdout']['sha256'],current_independent_acceptance=CURRENT_BFD_ACCEPTANCE,current_retained_closure=CURRENT_BFD_RAW_REFS,current_clearance_scope=current_physical['status'],current_owner_identity=current_physical['owner'],original_workload_status='FAIL',qualification_commands_recorded=2,qualification_successful_prefix_count=1,qualification_failure_rc=-6,original_direct_terminal=CURRENT_BFD_TERMINAL,source_proof=STATIC_SOURCE_PROOF,source_approval=STATIC_SOURCE_APPROVAL,target_calls=0,container_create_calls=0,execution_release=False)
(E/'ADMISSION.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(status=summary['status'],at=summary['at'],resources=capacity,image=info[0]['Id'],target_calls=0)))
