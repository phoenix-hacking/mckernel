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
assert request_path.is_absolute() and request_path.parent==Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1')
request_raw=request_path.read_bytes()
assert hashlib.sha256(request_raw).hexdigest()==inputs['request_sha256']
request=json.loads(request_raw)
assert request['request_path']==str(request_path)
OWNER = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/two-command-owner-source-1/bfd_original_c_twice_owner.PREFIX-SOURCE-CORRECTED.py')
assert hashlib.sha256(OWNER.read_bytes()).hexdigest()=='cca85a8205ee8875da705676c9c104d4801e095cb683acd1f008545b3b77fada'
spec=importlib.util.spec_from_file_location('library_sdk_admission_owner',OWNER)
owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
source_sha256 = {'scripts/native_exact_historical_lease_observer.py': '463ae558e141c2a6fe5a016fb19baddb26ed883c3bf6d39c114b27711ee78a51', 'scripts/native_running_external_modules_offline.py': '8d6a7226d35a7b61dc1e7d80a4f29ac6cb4edc9ad8db5c26626e61b99331d5f2', 'scripts/native_running_external_modules_owner.py': 'cca85a8205ee8875da705676c9c104d4801e095cb683acd1f008545b3b77fada', 'scripts/native_rust_exact_build_container_owner.py': '96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1', 'scripts/native_rust_exact_build_image_prepare.py': '45cb12e0fd58d164468badfb99a3ed922e65e06046bf38b4a50e27e18595a27b', 'scripts/native_rust_exact_build_image_rebind.py': 'f10ab116e55a24e8db7a8157d71efdd01198ba3453a8141bc8bbf596eda6b61e', 'scripts/native_rust_exact_build_image_rebind_probe.py': '412d46de7e078746a7ec979a13ccb25753d6fa34708610932e35be8f02a89635', 'scripts/native_rust_exact_build_offline.py': 'cc243126ab8cc0754c62175c77e46d6ba0d98294f8168cc77893a2c12249cd1a', 'scripts/native_rust_exact_disk_build_wrapper.py': 'c252ee341eb61752704f8b818503c0a5dc97400845494707ca3110f5f23df6d1', 'scripts/native_rust_exact_mckernel_image_container_owner.py': 'e9861cf73b0328c9fe2eacb987ea179933146cbeddbc3951405d4e60e89560f4', 'scripts/tests/test_native_running_external_modules_owner.py': 'c816f7dfd6fa167670876d8e64e8474bec119e1f19280fcc1cb902dff1a2c340'}
owner.validate_runtime_source_bindings(source_sha256)
STATIC_SOURCE_PROOF = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ACTUAL-FETCHED-BFD-C-C-SOURCE25-54D5BF00.json', 'bytes': 27197, 'sha256': 'b87f75b80f58f1de3e6221390fb7669f7a24471541242606d7bc9189dd4cc558'}
STATIC_SOURCE_APPROVAL = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ACTUAL-OWNER-CONSUMABLE-BFD-C-C-SOURCE-APPROVAL.json', 'bytes': 2216, 'sha256': 'd1338edc97dc7e6fbccc40479742f2657a3faefe3cf1285466eebc235f273537'}
assert STATIC_SOURCE_PROOF is not None and STATIC_SOURCE_APPROVAL is not None, 'genuine fetched30 sourceproof and independent11 approval required'
source_proof=owner.bound({field:STATIC_SOURCE_PROOF[field] for field in ('path','sha256')})
source_approval=owner.bound({field:STATIC_SOURCE_APPROVAL[field] for field in ('path','sha256')})
assert source_approval['decision']=='PASS_SOURCE' and source_approval['implementation_ownership'] is False and source_approval['source_sha256']==source_sha256

# Genuine current BFD qualifier-failure physical/postjoin authority; not Rust/SDK acceptance.
CURRENT_BFD_ACCEPTANCE = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/BFD-ACTUAL-PHYSICAL-AND-CURRENT-ACCEPTANCE.json', 'bytes': 2478, 'sha256': '3e1dc1150b51c43ab270558f68d22f3b4ed44299f969e4bc199283c45c1e68fc'}
CURRENT_BFD_RAW_REFS = {'0/stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-first-qualifier-failure-physical-postflight-source-1/0/stdout', 'bytes': 41306, 'sha256': '5defa3d32fa74278a4ba605e3bb93dd52b9a1a798d82725eb0eec653420417ae'}, '0/WHOLE-JOIN.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-first-qualifier-failure-physical-postflight-source-1/0/WHOLE-JOIN.json', 'bytes': 1324, 'sha256': '70ad0a8c73d7bbfc7e896bd97e59e648babccd8187a214ff9ce9dbb1eb42b0e5'}, '1/stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-first-qualifier-failure-physical-postflight-source-1/1/stdout', 'bytes': 43213, 'sha256': '42ccd9913d54c2b9443d3316f9c4db5099b3e7925fef8bbd5c0c634873243cb7'}, '1/WHOLE-JOIN.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-first-qualifier-failure-physical-postflight-source-1/1/WHOLE-JOIN.json', 'bytes': 1324, 'sha256': 'e05025e859de98dbc78f0cd70c39f1583640a519dc3bd771f69fd0b21397870c'}, 'actual-helpers-postjoin-1/0/stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-first-qualifier-failure-physical-postflight-source-1/actual-helpers-postjoin-1/0/stdout', 'bytes': 44612, 'sha256': '20230e7edeb8bdbbf7b2c288b6142d91143f7aa334c9212fd876f9d28faefb07'}, 'actual-helpers-postjoin-1/0/WHOLE-JOIN.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-first-qualifier-failure-physical-postflight-source-1/actual-helpers-postjoin-1/0/WHOLE-JOIN.json', 'bytes': 1375, 'sha256': 'd9e07e033e4358d319abe5894e5db58c8d8a265971dd915f772398fbf38ba266'}}
CURRENT_BFD_EXPECTED_ACCEPTANCE = {'schema': 'mckernel.m15.executor.bfd.qualifier-failure.current-acceptance.v1', 'status': 'PASS', 'reviewer': '/root/recovery_review', 'implementation_ownership': False, 'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Actual BFD failed qualifier normal retirement physical and current postjoin only.', 'physical_acceptance': True, 'current_postjoin_acceptance': True, 'evidence_root': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-first-qualifier-failure-physical-postflight-source-1', 'evidence_sha256_by_relative_path': {'0/stdout': '5defa3d32fa74278a4ba605e3bb93dd52b9a1a798d82725eb0eec653420417ae', '0/WHOLE-JOIN.json': '70ad0a8c73d7bbfc7e896bd97e59e648babccd8187a214ff9ce9dbb1eb42b0e5', '1/stdout': '42ccd9913d54c2b9443d3316f9c4db5099b3e7925fef8bbd5c0c634873243cb7', '1/WHOLE-JOIN.json': 'e05025e859de98dbc78f0cd70c39f1583640a519dc3bd771f69fd0b21397870c', 'actual-helpers-postjoin-1/0/stdout': '20230e7edeb8bdbbf7b2c288b6142d91143f7aa334c9212fd876f9d28faefb07', 'actual-helpers-postjoin-1/0/WHOLE-JOIN.json': 'd9e07e033e4358d319abe5894e5db58c8d8a265971dd915f772398fbf38ba266'}, 'owner': [598507, '71107266'], 'prior_helpers': [[601242, '71146149'], [601239, '71146142'], [601247, '71146181'], [601244, '71146174']], 'postjoin_python': [602041, '71152456'], 'postjoin_sudo': [602038, '71152449'], 'runtime_nonce': '0ccec66ed738427296d4e7b6bff0b4c5', 'operation_lease_nonce': '39247d7fc921471f83db241bf1c837eb', 'container_id': '5a274c67bda1f55eb90346caf3e7e854332b65f78bfb8f5c8ef4dec96e61f936', 'protected_refs': 131, 'candidate': {'entries': 42, 'files': 38, 'bytes': 6682841}, 'original_workload_status': 'FAIL', 'qualifier_capture_count': 1, 'qualification_commands_recorded': 10, 'qualification_successful_prefix_count': 9, 'qualification_failure_rc': -6, 'inner_command_births_namespace': 'container', 'permanent_mutex': {'device': 27, 'inode': 4, 'free_before': True, 'free_after': True, 'flock_acquired': False}, 'native_acceptance': False, 'default_acceptance': False, 'SDK_acceptance': False, 'heavy_execution_released': False}
CURRENT_BFD_TERMINAL = {'bytes': 1101, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/BFD-ACTUAL-FIRST-ATTEMPT-TOOL-TERMINAL.json', 'sha256': '9aa878bbcf567de869cab0ccbc951b058b0dd31a64a0be5d5146a158375da463'}
CURRENT_BFD_INVENTORY = {'bytes': 17157, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-first-qualifier-failure-physical-postflight-source-1/EXACT-BFD-FAILED-QUALIFIER-CANDIDATE-FD-INVENTORY.json', 'sha256': 'b22d9768b98eb4d310b6361f8bfce9957e846b90c7cbf7a3fded00892b1a4217'}
CURRENT_BFD_MANIFEST = {'bytes': 113271, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-bfd-first-qualifier-failure-physical-postflight-source-1/EXACT-BFD-FIRST-QUALIFIER-FAILURE-NORMAL-RETIREMENT.INPUTS.json', 'sha256': '9bf4c8434cf497a273f1e92eb0420b912d1a04637d829c75a8da13dd176a4ea4'}
acceptance=owner.bound({field:CURRENT_BFD_ACCEPTANCE[field] for field in ('path','sha256')});assert acceptance==CURRENT_BFD_EXPECTED_ACCEPTANCE
assert acceptance['status']=='PASS' and acceptance['physical_acceptance'] is True and acceptance['current_postjoin_acceptance'] is True and acceptance['implementation_ownership'] is False
observed={key:owner.bound({field:row[field] for field in ('path','sha256')}) for key,row in CURRENT_BFD_RAW_REFS.items()}
current_proc=observed['0/stdout'];current_physical=observed['1/stdout'];current_postjoin=observed['actual-helpers-postjoin-1/0/stdout']
assert current_proc['status']=='PASS_M15_EXECUTOR_BFD_QUALIFIER_FAILURE_EXACT_PROC'
assert current_physical['status']=='PASS_M15_EXECUTOR_BFD_QUALIFIER_FAILURE_MUTEX_HELD_CURRENT_PHYSICAL'
assert current_postjoin['status']=='PASS_M15_EXECUTOR_BFD_QUALIFIER_FAILURE_CURRENT_HELPERS_POSTJOIN_MUTEX_FREE'
for row in [current_proc,current_physical,current_postjoin]:
 assert row['original_workload_status']=='FAIL' and row['qualifier_capture_count']==1 and row['qualification_commands_recorded']==10
 assert row['owner']=={'pid':598507,'starttime':'71107266'} and row['direct_terminal']==CURRENT_BFD_TERMINAL and row['manifest']==CURRENT_BFD_MANIFEST
for name,pid,start,stream in [('0/WHOLE-JOIN.json',601239,71146142,'0/stdout'),('1/WHOLE-JOIN.json',601244,71146174,'1/stdout'),('actual-helpers-postjoin-1/0/WHOLE-JOIN.json',602038,71152449,'actual-helpers-postjoin-1/0/stdout')]:
 row=observed[name];assert row['pid']==pid and int(row['start'])==start and row['returncode']==0
 assert all(row[k] is True for k in ['direct_child_joined','group_absent','closed_streams']) and row['error'] is None and row['retirement_error'] is None and row['timed_out'] is False and row['remaining_group_members']==row['unexpected_group_members']==[]
 assert row['captures']['stdout']['sha256']==CURRENT_BFD_RAW_REFS[stream]['sha256']
assert current_postjoin['current_reader_identity']['pid']==602041 and current_postjoin['current_reader_identity']['starttime']=='71152456'
assert current_postjoin['permanent_mutex_free_before'] is True and current_postjoin['permanent_mutex_free_after'] is True and current_postjoin['flock_acquired'] is False and current_postjoin['terminal_evidence_unchanged'] is True
assert current_physical['partial_candidate_inventory']==CURRENT_BFD_INVENTORY
terminal=owner.bound({field:CURRENT_BFD_TERMINAL[field] for field in ('path','sha256')});inventory=owner.bound({field:CURRENT_BFD_INVENTORY[field] for field in ('path','sha256')});owner.bound({field:CURRENT_BFD_MANIFEST[field] for field in ('path','sha256')})
assert inventory['entry_count']==42 and inventory['file_count']==38 and inventory['total_file_bytes']==6682841
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
summary=dict(scope=__doc__,status='PASS_READONLY_SDK_CAPACITY_IDENTITY_IMAGE_ONLY',at=time.time(),request_sha256=inputs['request_sha256'],resources=capacity,mount=mount,image_id=info[0]['Id'],image_Architecture=info[0]['Architecture'],group_checks=client.group_checks,conflict_paths_absent=[str(p) for p in sorted(conflicts)],current_physical_acceptance=CURRENT_BFD_RAW_REFS['1/stdout']['sha256'],current_postjoin=CURRENT_BFD_RAW_REFS['actual-helpers-postjoin-1/0/stdout']['sha256'],current_independent_acceptance=CURRENT_BFD_ACCEPTANCE,current_retained_closure=CURRENT_BFD_RAW_REFS,current_clearance_scope=current_physical['status'],current_owner_identity=current_physical['owner'],original_workload_status='FAIL',qualification_commands_recorded=10,qualification_successful_prefix_count=9,qualification_failure_rc=-6,original_direct_terminal=CURRENT_BFD_TERMINAL,source_proof=STATIC_SOURCE_PROOF,source_approval=STATIC_SOURCE_APPROVAL,target_calls=0,container_create_calls=0,execution_release=False)
(E/'ADMISSION.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(status=summary['status'],at=summary['at'],resources=capacity,image=info[0]['Id'],target_calls=0)))
