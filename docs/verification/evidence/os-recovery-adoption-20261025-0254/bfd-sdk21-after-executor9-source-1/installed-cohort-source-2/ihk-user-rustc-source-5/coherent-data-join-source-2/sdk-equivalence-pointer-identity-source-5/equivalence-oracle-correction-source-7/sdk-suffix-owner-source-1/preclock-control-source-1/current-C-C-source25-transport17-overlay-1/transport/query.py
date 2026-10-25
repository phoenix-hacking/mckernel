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
assert request_path.is_absolute() and request_path.parent==Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/equivalence-oracle-correction-source-7/sdk-suffix-owner-source-1')
request_raw=request_path.read_bytes()
assert hashlib.sha256(request_raw).hexdigest()==inputs['request_sha256']
request=json.loads(request_raw)
assert request['request_path']==str(request_path)
OWNER = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/bfd-sdk21-after-executor9-source-1/installed-cohort-source-2/ihk-user-rustc-source-5/coherent-data-join-source-2/sdk-equivalence-pointer-identity-source-5/equivalence-oracle-correction-source-7/sdk-suffix-owner-source-1/bfd_semantic_sdk_suffix_owner.py')
assert hashlib.sha256(OWNER.read_bytes()).hexdigest()=='477e64c599de043248c7077dd88fb865d7701d0e31382f5303285286f64a8708'
spec=importlib.util.spec_from_file_location('library_sdk_admission_owner',OWNER)
owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
source_sha256 = {'scripts/native_exact_historical_lease_observer.py': '463ae558e141c2a6fe5a016fb19baddb26ed883c3bf6d39c114b27711ee78a51', 'scripts/native_running_external_modules_offline.py': '5a887189cbdf6ada52d33800e959a4540f6426ec04226f6ffe441d478feaa962', 'scripts/native_running_external_modules_owner.py': '477e64c599de043248c7077dd88fb865d7701d0e31382f5303285286f64a8708', 'scripts/native_rust_exact_build_container_owner.py': '96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1', 'scripts/native_rust_exact_build_image_prepare.py': '45cb12e0fd58d164468badfb99a3ed922e65e06046bf38b4a50e27e18595a27b', 'scripts/native_rust_exact_build_image_rebind.py': 'f10ab116e55a24e8db7a8157d71efdd01198ba3453a8141bc8bbf596eda6b61e', 'scripts/native_rust_exact_build_image_rebind_probe.py': '412d46de7e078746a7ec979a13ccb25753d6fa34708610932e35be8f02a89635', 'scripts/native_rust_exact_build_offline.py': 'cc243126ab8cc0754c62175c77e46d6ba0d98294f8168cc77893a2c12249cd1a', 'scripts/native_rust_exact_disk_build_wrapper.py': 'c252ee341eb61752704f8b818503c0a5dc97400845494707ca3110f5f23df6d1', 'scripts/native_rust_exact_mckernel_image_container_owner.py': 'e9861cf73b0328c9fe2eacb987ea179933146cbeddbc3951405d4e60e89560f4', 'scripts/tests/test_native_running_external_modules_owner.py': 'c816f7dfd6fa167670876d8e64e8474bec119e1f19280fcc1cb902dff1a2c340'}
owner.validate_runtime_source_bindings(source_sha256)
STATIC_SOURCE_PROOF = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ACTUAL-FETCHED-BFD-SEMANTIC-SOURCE32-773E4430.json', 'bytes': 36338, 'sha256': '881f9daae481f982eb82500ee5a9a8f412f393ca478790e29be4edb54806e99e'}
STATIC_SOURCE_APPROVAL = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/ACTUAL-OWNER-CONSUMABLE-BFD-SEMANTIC-SDK-SOURCE-APPROVAL.json', 'bytes': 2594, 'sha256': 'ed7286dbed39e6d50d3ab6b2bc67e855518dd7cf17d14d423917373e5f289cb0'}
assert STATIC_SOURCE_PROOF is not None and STATIC_SOURCE_APPROVAL is not None, 'genuine fetched30 sourceproof and independent11 approval required'
source_proof=owner.bound({field:STATIC_SOURCE_PROOF[field] for field in ('path','sha256')})
source_approval=owner.bound({field:STATIC_SOURCE_APPROVAL[field] for field in ('path','sha256')})
assert source_approval['decision']=='PASS_SOURCE' and source_approval['implementation_ownership'] is False and source_approval['source_sha256']==source_sha256

# Genuine current BFD qualifier-failure physical/postjoin authority; not Rust/SDK acceptance.
CURRENT_BFD_ACCEPTANCE = {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/CORRECTED-BFD-C-C-ACTUAL-PHYSICAL-AND-CURRENT-ACCEPTANCE.json', 'bytes': 2680, 'sha256': '71dfa12d70af2b96c101dcb91ea94c30997cb82552e9f495cec42f243fd9e649'}
CURRENT_BFD_RAW_REFS = {'0/WHOLE-JOIN.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-corrected-bfd-original-c-twice-pass-physical-postflight-source-1/0/WHOLE-JOIN.json', 'bytes': 1341, 'sha256': '57480e9931b9acaa10c4901a5ba43e147f447e265a67b140a2907060b488c644'}, '0/stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-corrected-bfd-original-c-twice-pass-physical-postflight-source-1/0/stdout', 'bytes': 41652, 'sha256': '3d4c2cc8d7c01dfa0b0cac7066fc9146d03981759b13f7bcb23796b610c90803'}, '1/WHOLE-JOIN.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-corrected-bfd-original-c-twice-pass-physical-postflight-source-1/1/WHOLE-JOIN.json', 'bytes': 1340, 'sha256': '289919b8c8d8489525192b72b967a0356c1b902d9eba7c8aef95479c897fcbdc'}, '1/stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-corrected-bfd-original-c-twice-pass-physical-postflight-source-1/1/stdout', 'bytes': 43568, 'sha256': 'b536975970941115c38eca6397d40ebb778908981ad37e3320cc6b64015a6479'}, 'actual-helpers-postjoin-1/0/WHOLE-JOIN.json': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-corrected-bfd-original-c-twice-pass-physical-postflight-source-1/actual-helpers-postjoin-1/0/WHOLE-JOIN.json', 'bytes': 1392, 'sha256': '496016d9a08c4e76d4edc7bb08eeb4ddcf79464044629e311280a26bb58be306'}, 'actual-helpers-postjoin-1/0/stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-corrected-bfd-original-c-twice-pass-physical-postflight-source-1/actual-helpers-postjoin-1/0/stdout', 'bytes': 44726, 'sha256': '795f5ca79c0ca0be6ad0bce826a7d1cedb9c1dad09880e7cc8ad29184e0fe7a1'}}
CURRENT_BFD_EXPECTED_ACCEPTANCE = {'Rust_ABI_acceptance': False, 'SDK21_acceptance': False, 'candidate': {'bytes': 6520109, 'entries': 19, 'files': 15}, 'container_id': '4b69ef6d33704d2caee69669da1b43d1643cd111e9a791990a52b57869fc1a06', 'control_result_sha256': 'acf7fa9ccf3cf0482d8e96ae271def0125f1b5c5debf382ab1dbaca4b19926f4', 'current_postjoin_acceptance': True, 'default_acceptance': False, 'evidence_root': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-corrected-bfd-original-c-twice-pass-physical-postflight-source-1', 'evidence_sha256_by_relative_path': {'0/WHOLE-JOIN.json': '57480e9931b9acaa10c4901a5ba43e147f447e265a67b140a2907060b488c644', '0/stdout': '3d4c2cc8d7c01dfa0b0cac7066fc9146d03981759b13f7bcb23796b610c90803', '1/WHOLE-JOIN.json': '289919b8c8d8489525192b72b967a0356c1b902d9eba7c8aef95479c897fcbdc', '1/stdout': 'b536975970941115c38eca6397d40ebb778908981ad37e3320cc6b64015a6479', 'actual-helpers-postjoin-1/0/WHOLE-JOIN.json': '496016d9a08c4e76d4edc7bb08eeb4ddcf79464044629e311280a26bb58be306', 'actual-helpers-postjoin-1/0/stdout': '795f5ca79c0ca0be6ad0bce826a7d1cedb9c1dad09880e7cc8ad29184e0fe7a1'}, 'heavy_execution_released': False, 'implementation_ownership': False, 'inner_command_births_namespace': 'container', 'native_acceptance': False, 'operation_lease_nonce': 'ba0a4037aeb4459182310396654e4b39', 'original_workload_status': 'PASS', 'owner': [625893, '71521270'], 'permanent_mutex': {'device': 27, 'flock_acquired': False, 'free_after': True, 'free_before': True, 'inode': 4}, 'physical_acceptance': True, 'postjoin_python': [627789, '71552771'], 'postjoin_sudo': [627786, '71552764'], 'prior_helpers': [[627652, '71548209'], [627649, '71548202'], [627657, '71548241'], [627654, '71548234']], 'protected_refs': 109, 'qualification_commands_recorded': 2, 'qualification_successful_count': 2, 'qualifier_capture_count': 1, 'reviewed_execution_payload_sha256': '88b693a77810fd0bb8aa2f3a3c1cf117c720c3c272b5ae5c2d6974b97013dd6b', 'reviewer': '/root/recovery_review', 'runtime_nonce': 'bf8f0599937843cb8f19ef582bafba3a', 'schema': 'mckernel.m15.executor.bfd.corrected-original-c-twice-pass.current-acceptance.v1', 'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Corrected C/C normal retirement physical and current postjoin only.', 'status': 'PASS'}
CURRENT_BFD_TERMINAL = {'bytes': 754, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/CORRECTED-BFD-C-C-ACTUAL-TOOL-TERMINAL.json', 'sha256': '96efc561524e64f5ec2d3f48f5383eff3846dbbb78c6c3b7b1b74d188a758631'}
CURRENT_BFD_INVENTORY = {'bytes': 8016, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-corrected-bfd-original-c-twice-pass-physical-postflight-source-1/EXACT-CORRECTED-BFD-C-C-PASS-CANDIDATE-FD-INVENTORY.json', 'sha256': '7f2c62149dadd3bd82233a98cacc8a9516fa7d354749cd07dfa2cbe9496749ce'}
CURRENT_BFD_MANIFEST = {'bytes': 114309, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current-corrected-bfd-original-c-twice-pass-physical-postflight-source-1/EXACT-CORRECTED-BFD-C-C-PASS-NORMAL-RETIREMENT.INPUTS.json', 'sha256': 'c6db3f3b99a2395e05915174e32f8563802793081cdb04c6ed5523270ca92c48'}
acceptance=owner.bound({field:CURRENT_BFD_ACCEPTANCE[field] for field in ('path','sha256')});assert acceptance==CURRENT_BFD_EXPECTED_ACCEPTANCE
assert acceptance['status']=='PASS' and acceptance['physical_acceptance'] is True and acceptance['current_postjoin_acceptance'] is True and acceptance['implementation_ownership'] is False
observed={key:owner.bound({field:row[field] for field in ('path','sha256')}) for key,row in CURRENT_BFD_RAW_REFS.items()}
current_proc=observed['0/stdout'];current_physical=observed['1/stdout'];current_postjoin=observed['actual-helpers-postjoin-1/0/stdout']
assert current_proc['status']=='PASS_M15_EXECUTOR_CORRECTED_BFD_ORIGINAL_C_TWICE_PASS_EXACT_PROC'
assert current_physical['status']=='PASS_M15_EXECUTOR_CORRECTED_BFD_ORIGINAL_C_TWICE_PASS_MUTEX_HELD_CURRENT_PHYSICAL'
assert current_postjoin['status']=='PASS_M15_EXECUTOR_CORRECTED_BFD_ORIGINAL_C_TWICE_PASS_CURRENT_HELPERS_POSTJOIN_MUTEX_FREE'
for row in [current_proc,current_physical,current_postjoin]:
 assert row['original_workload_status']=='PASS' and row['qualifier_capture_count']==1 and row['qualification_commands_recorded']==2
 assert row['owner']=={'pid':625893,'starttime':'71521270'} and row['direct_terminal']==CURRENT_BFD_TERMINAL and row['manifest']==CURRENT_BFD_MANIFEST
for name,pid,start,stream in [('0/WHOLE-JOIN.json',627649,71548202,'0/stdout'),('1/WHOLE-JOIN.json',627654,71548234,'1/stdout'),('actual-helpers-postjoin-1/0/WHOLE-JOIN.json',627786,71552764,'actual-helpers-postjoin-1/0/stdout')]:
 row=observed[name];assert row['pid']==pid and int(row['start'])==start and row['returncode']==0
 assert all(row[k] is True for k in ['direct_child_joined','group_absent','closed_streams']) and row['error'] is None and row['retirement_error'] is None and row['timed_out'] is False and row['remaining_group_members']==row['unexpected_group_members']==[]
 assert row['captures']['stdout']['sha256']==CURRENT_BFD_RAW_REFS[stream]['sha256']
assert current_postjoin['current_reader_identity']['pid']==627789 and current_postjoin['current_reader_identity']['starttime']=='71552771'
assert current_postjoin['permanent_mutex_free_before'] is True and current_postjoin['permanent_mutex_free_after'] is True and current_postjoin['flock_acquired'] is False and current_postjoin['terminal_evidence_unchanged'] is True
assert current_physical['partial_candidate_inventory']==CURRENT_BFD_INVENTORY
terminal=owner.bound({field:CURRENT_BFD_TERMINAL[field] for field in ('path','sha256')});inventory=owner.bound({field:CURRENT_BFD_INVENTORY[field] for field in ('path','sha256')});owner.bound({field:CURRENT_BFD_MANIFEST[field] for field in ('path','sha256')})
assert inventory['entry_count']==19 and inventory['file_count']==15 and inventory['total_file_bytes']==6520109
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
summary=dict(scope=__doc__,status='PASS_READONLY_SDK_CAPACITY_IDENTITY_IMAGE_ONLY',at=time.time(),request_sha256=inputs['request_sha256'],resources=capacity,mount=mount,image_id=info[0]['Id'],image_Architecture=info[0]['Architecture'],group_checks=client.group_checks,conflict_paths_absent=[str(p) for p in sorted(conflicts)],current_physical_acceptance=CURRENT_BFD_RAW_REFS['1/stdout']['sha256'],current_postjoin=CURRENT_BFD_RAW_REFS['actual-helpers-postjoin-1/0/stdout']['sha256'],current_independent_acceptance=CURRENT_BFD_ACCEPTANCE,current_retained_closure=CURRENT_BFD_RAW_REFS,current_clearance_scope=current_physical['status'],current_owner_identity=current_physical['owner'],original_workload_status='PASS',qualification_commands_recorded=2,qualification_successful_count=2,original_direct_terminal=CURRENT_BFD_TERMINAL,source_proof=STATIC_SOURCE_PROOF,source_approval=STATIC_SOURCE_APPROVAL,target_calls=0,container_create_calls=0,execution_release=False)
(E/'ADMISSION.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(status=summary['status'],at=summary['at'],resources=capacity,image=info[0]['Id'],target_calls=0)))
