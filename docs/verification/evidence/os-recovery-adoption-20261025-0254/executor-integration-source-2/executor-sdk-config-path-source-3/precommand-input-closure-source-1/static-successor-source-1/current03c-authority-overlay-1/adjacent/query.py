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
assert request_path.is_absolute() and request_path.parent==Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-config-path-source-3/precommand-input-closure-source-1/static-successor-source-1')
request_raw=request_path.read_bytes()
assert hashlib.sha256(request_raw).hexdigest()==inputs['request_sha256']
request=json.loads(request_raw)
assert request['request_path']==str(request_path)
OWNER=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/executor-sdk-config-path-source-3/precommand-input-closure-source-1/target_tools_sdk_owner.py')
assert hashlib.sha256(OWNER.read_bytes()).hexdigest()=='4ae4a61e9aaab555077c52955f97b46a92a7f25b33cb3d29c448eeb856099a2c'
spec=importlib.util.spec_from_file_location('library_sdk_admission_owner',OWNER)
owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
source_sha256 = {'scripts/native_exact_historical_lease_observer.py': '463ae558e141c2a6fe5a016fb19baddb26ed883c3bf6d39c114b27711ee78a51', 'scripts/native_running_external_modules_offline.py': '8543093fbfa216a69de29fcec0866370fca1f53409afe67540fa33c03e1b3cc0', 'scripts/native_running_external_modules_owner.py': '4ae4a61e9aaab555077c52955f97b46a92a7f25b33cb3d29c448eeb856099a2c', 'scripts/native_rust_exact_build_container_owner.py': '96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1', 'scripts/native_rust_exact_build_image_prepare.py': '45cb12e0fd58d164468badfb99a3ed922e65e06046bf38b4a50e27e18595a27b', 'scripts/native_rust_exact_build_image_rebind.py': 'f10ab116e55a24e8db7a8157d71efdd01198ba3453a8141bc8bbf596eda6b61e', 'scripts/native_rust_exact_build_image_rebind_probe.py': '412d46de7e078746a7ec979a13ccb25753d6fa34708610932e35be8f02a89635', 'scripts/native_rust_exact_build_offline.py': 'cc243126ab8cc0754c62175c77e46d6ba0d98294f8168cc77893a2c12249cd1a', 'scripts/native_rust_exact_disk_build_wrapper.py': 'c252ee341eb61752704f8b818503c0a5dc97400845494707ca3110f5f23df6d1', 'scripts/native_rust_exact_mckernel_image_container_owner.py': 'e9861cf73b0328c9fe2eacb987ea179933146cbeddbc3951405d4e60e89560f4', 'scripts/tests/test_native_running_external_modules_owner.py': 'c816f7dfd6fa167670876d8e64e8474bec119e1f19280fcc1cb902dff1a2c340'}
owner.validate_runtime_source_bindings(source_sha256)
# Distinct historical SDK normal retirement and current PREVALIDATION token clearance.
prior_sdk_normal_retirement={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-sdk-library-tool-FD-failure-postjoin-1/ROOT-RECORDED-INDEPENDENT-PHYSICAL-ACCEPTANCE.json', 'sha256': '4dedde1fc45dbcbddbf35f934e82c4f65bbed75417d9e3f13199d98ad7f7e123'}
prior_sdk_normal_postjoin={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-sdk-library-tool-FD-failure-postjoin-1/CURRENT-LIVE-POSTJOIN.json', 'sha256': '65e71cfbc9c36e1f795cfb2d7ee6b2d9a14361d70627629a09ebda163da9e0bd'}
prior=owner.bound(prior_sdk_normal_retirement)
prior_live=owner.bound(prior_sdk_normal_postjoin)
assert prior['status']=='PASS_ACTUAL_M15_SDK_LIBRARY_FAILED_BUILD_PHYSICAL_RETIREMENT'
assert prior['original_build_status']=='FAIL' and prior['artifact_native_acceptance'] is False
assert prior_live['physical_acceptance']==prior_sdk_normal_retirement
assert prior_live['status']=='PASS_CURRENT_LIVE_POSTJOIN_NONNULL'
current_token_clearance={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-copy5-reconciled-token-postjoin-1/ROOT-RECORDED-INDEPENDENT-PHYSICAL-ACCEPTANCE.json', 'sha256': '06779cc315a82b257236a0842262bf73ea5cd688ae11b3bb8a4ed2ef59867621'}
current_token_postjoin={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-copy5-reconciled-token-postjoin-1/CURRENT-LIVE-POSTJOIN.json', 'sha256': '419ebe58613034695f42eefa4cbf6325b4c04d05712c543ebbf664c5eeba6c72'}
clearance=owner.bound(current_token_clearance)
current_live=owner.bound(current_token_postjoin)
assert clearance['status']=='CLOSED_PREVALIDATION_SHARED_TOKEN_NORMAL_RECONCILIATION'
assert clearance['owner']=={'pid':189516,'starttime':'65397349'}
assert clearance['api_child']=={'pid':195301,'starttime':'65488487'}
assert clearance['build_status']=='FAIL_PRESERVED_STOPPED' and clearance['build_acceptance'] is False
assert clearance['current_live_postjoin_accepted_non_null'] is True
assert clearance['implementation_ownership'] is False and clearance['reviewer']=='/root/native235_release_review'
assert current_live['status']=='PASS_CURRENT_LIVE_POSTJOIN_NONNULL'
assert current_live['physical_acceptance']==current_token_clearance and current_live['shared_token_reconciled'] is True
assert current_live['original_build_status']=='FAIL_PRESERVED_STOPPED' and current_live['artifact_native_acceptance'] is False
expected_links={'api_result': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-retained-validator-continuation-1/copy4-readelf-stream-correction-1/retained49-copy5-successor-1/actual-bound-copy5-admission-preparation-1/latest-tool-FD-retirement-binding-1/prevalidation-shared-token-reconciliation-preparation-1/ACTUAL-RECONCILIATION-RESULT.json', 'sha256': '93670ec1830787aedc88e94da86bcbea98d2d6e5bd69656aad43cfcddb9600c4'}, 'api_whole_join': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-copy5-prevalidation-token-normal-api-reconciliation-1/WHOLE-JOIN.json', 'sha256': '9bc68106bbd92c32ce211dd3d0903aab41a1f3a835239292d55851954b6b1e79'}, 'proc_whole_join': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-copy5-reconciled-token-postjoin-1/0/WHOLE-JOIN.json', 'sha256': '03f268df0b7ba8a5e3c430e3ceb7b2e1b881f84dbf436b56567e336240e8012d'}, 'mutex_whole_join': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-copy5-reconciled-token-postjoin-1/1/WHOLE-JOIN.json', 'sha256': '9bfa2c3ad91218f2b448fa44e4d3f08c2228ee1c7428f82bbcd275dcc24e9712'}}
for key,ref in expected_links.items():
    assert clearance[key]==ref
api_result=owner.bound(expected_links['api_result'])
assert api_result['status']=='PASS_NORMAL_API_PREFLIGHT_TOKEN_RECONCILIATION' and api_result['token_absent'] is True
assert api_result['physical_receipt_sha256']=='b787ad27b1c683ce4325cdff7a47042b660fca78cb79e8b965a86c1901f07004'
assert api_result['contract_sha256']=='c252ee341eb61752704f8b818503c0a5dc97400845494707ca3110f5f23df6d1'
assert api_result['permanent_mutex']==[27,4]
assert api_result['build_status']=='FAIL_PRESERVED_STOPPED' and api_result['build_acceptance'] is False
joined={};observed={}
for key in ('api_whole_join','proc_whole_join','mutex_whole_join'):
    join=owner.bound(expected_links[key])
    assert join['returncode']==0 and join['direct_child_joined'] and join['group_absent'] and join['closed_streams']
    assert join['error'] is None and join['retirement_error'] is None and join['timed_out'] is False
    assert join['remaining_group_members']==[] and join['unexpected_group_members']==[]
    err=join['captures']['stderr'];err_path=owner.safe_path(err['path'],False)
    assert err['size']==err_path.stat().st_size==0 and owner.host.digest(err_path)==err['sha256']
    out=join['captures']['stdout']
    observed[key]=owner.bound({'path':out['path'],'sha256':out['sha256']})
    joined[key]=join
assert joined['api_whole_join']['pid']==195301 and str(joined['api_whole_join']['start'])=='65488487'
assert observed['api_whole_join']==api_result
proc=observed['proc_whole_join']
assert proc['status']=='CURRENT_FAILED235_COMPLETE_PROC_OBSERVATION'
assert proc['proc']['schema']=='fp-save-image.proc.v2' and proc['proc']['status']=='COMPLETE'
assert proc['proc']['uid']==0 and proc['proc']['boot_id']==owner.BOOT
assert proc['proc']['failure'] is None and proc['proc']['publishers']==[] and len(proc['proc']['snapshots'])==2
assert all(not any(row[0] in (189516,195301) for row in sweep) for sweep in proc['proc']['snapshots'])
mutex=observed['mutex_whole_join']
assert mutex['status']=='PASS_CURRENT_FAILED235_27_4_AND_8_PATH_ABSENCE' and mutex['lock']==[27,4]
assert mutex['paths']==['/home/holden/mckernel-work/scratch/native-running-external-modules.lease.json', '/home/holden/mckernel-work/scratch/native-running-external-modules-operational-exclusion.json', '/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch18-image-1.json', '/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock', '/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/lease.json', '/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/image-lease.json']
assert str(owner.shared.SHARED_HEAVY_LOCK_PATH)=='/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock'
assert not os.path.lexists(owner.shared.SHARED_HEAVY_LOCK_PATH)


# Latest SDK normal retirement follows the historical prevalidation token clearance above.
latest_sdk_retirement={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-sdk-library-missing-BFD-header-postjoin-1/ROOT-RECORDED-INDEPENDENT-PHYSICAL-ACCEPTANCE.json', 'sha256': '45f9a9cf1ebf8426efda5e02358e16b34a6aa52599074a5f83b08cf4ab4936aa'}
latest_sdk_postjoin={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-sdk-library-missing-BFD-header-postjoin-1/CURRENT-LIVE-POSTJOIN.json', 'sha256': 'b69550a33eca07368bad03fdedb1909c2c461996fb49b61eb66a5584ac1576d0'}
latest=owner.bound(latest_sdk_retirement)
latest_live=owner.bound(latest_sdk_postjoin)
assert latest['status']=='PASS_ACTUAL_M15_SDK_LIBRARY_FAILED_BUILD_PHYSICAL_RETIREMENT'
assert latest['owner']=={'pid':198637,'starttime':'65544028'}
assert latest['original_build_status']=='FAIL' and latest['artifact_native_acceptance'] is False
assert latest['implementation_ownership'] is False and latest['reviewer']=='/root/native235_release_review'
assert latest_live['status']=='PASS_CURRENT_LIVE_POSTJOIN_NONNULL' and latest_live['physical_acceptance']==latest_sdk_retirement
assert latest_live['original_build_status']=='FAIL' and latest_live['artifact_native_acceptance'] is False
latest_owner=owner.bound(latest['owner_stdout'])
assert latest_owner['status']=='FAIL' and latest_owner['cleanup_status']=='PASS_OWNED_REMOVAL_AND_RECORD_RELEASE'
assert latest_owner['retired'] is True and latest_owner['cleanup_separately_required'] is False
for key in ('proc_whole_join','mutex_whole_join'):
    join=owner.bound(latest[key])
    assert join['returncode']==0 and join['direct_child_joined'] and join['group_absent'] and join['closed_streams']
    assert join['error'] is None and join['retirement_error'] is None and join['timed_out'] is False
    assert join['remaining_group_members']==[] and join['unexpected_group_members']==[]
    err=join['captures']['stderr'];err_path=owner.safe_path(err['path'],False)
    assert err['size']==err_path.stat().st_size==0 and owner.host.digest(err_path)==err['sha256']
    out=join['captures']['stdout'];value=owner.bound({'path':out['path'],'sha256':out['sha256']})
    if key=='proc_whole_join':
        assert latest['proc_stdout']=={'path':out['path'],'sha256':out['sha256']}
        assert value['proc']['schema']=='fp-save-image.proc.v2' and value['proc']['status']=='COMPLETE'
        assert value['proc']['uid']==0 and value['proc']['boot_id']==owner.BOOT
        assert value['proc']['failure'] is None and value['proc']['publishers']==[] and len(value['proc']['snapshots'])==2
        assert all(not any(row[0]==198637 for row in sweep) for sweep in value['proc']['snapshots'])
    else:
        assert value['status']=='PASS_CURRENT_FAILED235_27_4_AND_8_PATH_ABSENCE' and value['lock']==[27,4]
        assert value['paths']==mutex['paths']
selected_image_receipt={'path': '/home/holden/mckernel-exact-image-evidence-942c927b-scratch22-authority3-image1-20261017/image-receipt.json', 'sha256': '352102798e60bfcf8a72facded532430a93ba30f949a55e1d8eaf54a2f351550'}
image_authority=owner.bound(selected_image_receipt)
assert image_authority['status']=='PASS' and image_authority['retired'] is True
assert image_authority['image_id']==owner.IMAGE==request['image_id']=='sha256:41778f1f22fd68897c1209e225a9807a197ed47bf0edd17835821bb5986e50b5'
assert image_authority['source_free'] is True and image_authority['runtime_network']=='none'
assert image_authority['candidate_sha']==owner.CANDIDATE
assert image_authority['packages']['binutils-devel']=='binutils-devel-0:2.41-63.el10.x86_64'
assert image_authority['tools']['cc']['sha256']==owner.LIBRARY_PREPARATION['target_tools']['/usr/bin/cc']
bfd=image_authority['libraries']['libbfd']
assert bfd['headers']['/usr/include/bfd.h']['sha256']==owner.LIBRARY_PREPARATION['target_tools']['/usr/include/bfd.h']
assert bfd['linker']['sha256']==owner.LIBRARY_PREPARATION['target_tools']['/usr/lib64/libbfd.so']

# Current COPY6 normal retirement is a distinct typed authority, not SDK or artifact acceptance.
current_copy6_physical={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-copy6-normal-retirement-postjoin-1/ROOT-RECORDED-INDEPENDENT-PHYSICAL-ACCEPTANCE.json', 'sha256': '6c5acdd2e39a30a6e4eee9f601ddab887920a7c494b30e899ef82d339c59c4be', 'bytes': 892}
current_copy6_postjoin={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-copy6-normal-retirement-postjoin-1/CURRENT-LIVE-POSTJOIN.json', 'sha256': '9133afffb23e2645cf7b5b544fa901656b86f354aaa5295e9d1e282347a254df', 'bytes': 1484}
assert set(current_copy6_physical)=={'path','sha256','bytes'} and type(current_copy6_physical['bytes']) is int and current_copy6_physical['bytes']>=0
assert owner.safe_path(current_copy6_physical['path'],False).stat().st_size==current_copy6_physical['bytes']
copy6=owner.bound({k:current_copy6_physical[k] for k in ('path','sha256')})
assert owner.safe_path(current_copy6_physical['path'],False).stat().st_size==current_copy6_physical['bytes']
assert set(current_copy6_postjoin)=={'path','sha256','bytes'} and type(current_copy6_postjoin['bytes']) is int and current_copy6_postjoin['bytes']>=0
assert owner.safe_path(current_copy6_postjoin['path'],False).stat().st_size==current_copy6_postjoin['bytes']
copy6_live=owner.bound({k:current_copy6_postjoin[k] for k in ('path','sha256')})
assert owner.safe_path(current_copy6_postjoin['path'],False).stat().st_size==current_copy6_postjoin['bytes']
assert copy6['status']=='PASS_ACTUAL_M14_COPY6_RETAINED_VALIDATOR_PHYSICAL_RETIREMENT'
assert copy6['original_workload_status']=='FAIL' and copy6['artifact_native_acceptance'] is False
assert copy6['current_live_postjoin_accepted_non_null'] is True
assert copy6['implementation_ownership'] is False and copy6['reviewer']=='/root/native235_release_review'
assert copy6['client_births'] is None and copy6['historical_outer_identity'] is None and copy6['host_init_identity'] is None
assert copy6_live['schema']=='mckernel.current-live-postjoin.v1' and copy6_live['status']=='ACCEPTED_NON_NULL'
assert copy6_live['physical_acceptance']==current_copy6_physical
assert copy6_live['original_workload_status']=='FAIL' and copy6_live['artifact_native_acceptance'] is False
copy6_normal_ref={'bytes': 364603, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-copy6-actual-normal-retirement-1/stdout', 'sha256': '3c4bd9e00392bfae077405aec15e7654b2ed1b5b72e80a7056eaccc8e63f63fa'}
copy6_links={'mutex': {'bytes': 1092, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-copy6-normal-retirement-postjoin-1/1/WHOLE-JOIN.json', 'sha256': 'abb29f946dd65a74e9cbe6bee568ecfe4048df0df687734fd465889f315f7f92'}, 'proc': {'bytes': 1090, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-copy6-normal-retirement-postjoin-1/0/WHOLE-JOIN.json', 'sha256': '9148bf4b3df80859f4c56fa5db8e7cf1237481b94c22abe2499217f0c735e495'}}
assert copy6_live['actual_cleanup']==copy6_normal_ref and copy6_live['current_live_postjoin']==copy6_links
assert copy6['normal_result_sha256']==copy6_normal_ref['sha256']
assert copy6['proc_whole_join_sha256']==copy6_links['proc']['sha256']
assert copy6['mutex_whole_join_sha256']==copy6_links['mutex']['sha256']
assert set(copy6_normal_ref)=={'path','sha256','bytes'} and type(copy6_normal_ref['bytes']) is int and copy6_normal_ref['bytes']>=0
assert owner.safe_path(copy6_normal_ref['path'],False).stat().st_size==copy6_normal_ref['bytes']
copy6_normal=owner.bound({k:copy6_normal_ref[k] for k in ('path','sha256')})
assert owner.safe_path(copy6_normal_ref['path'],False).stat().st_size==copy6_normal_ref['bytes']
assert copy6_normal['status']=='PASS_EXECUTED' and copy6_normal['terminal'] is True
assert copy6_normal['container_absent'] is True and copy6_normal['boot_id']==owner.BOOT
for key in ('proc','mutex'):
    assert set(copy6_links[key])=={'path','sha256','bytes'} and type(copy6_links[key]['bytes']) is int and copy6_links[key]['bytes']>=0
    assert owner.safe_path(copy6_links[key]['path'],False).stat().st_size==copy6_links[key]['bytes']
    join=owner.bound({k:copy6_links[key][k] for k in ('path','sha256')})
    assert owner.safe_path(copy6_links[key]['path'],False).stat().st_size==copy6_links[key]['bytes']
    assert join['returncode']==0 and join['direct_child_joined'] and join['group_absent'] and join['closed_streams']
    assert join['error'] is None and join['retirement_error'] is None and join['timed_out'] is False
    assert join['remaining_group_members']==[] and join['unexpected_group_members']==[]
    err=join['captures']['stderr'];err_path=owner.safe_path(err['path'],False)
    assert err['size']==err_path.stat().st_size==0 and owner.host.digest(err_path)==err['sha256']
    out=join['captures']['stdout']
    value=owner.bound({'path':out['path'],'sha256':out['sha256']})
    if key=='proc':
        assert value['status']=='CURRENT_FAILED235_COMPLETE_PROC_OBSERVATION'
        assert value['proc']['schema']=='fp-save-image.proc.v2' and value['proc']['status']=='COMPLETE'
        assert value['proc']['uid']==0 and value['proc']['boot_id']==owner.BOOT
        assert value['proc']['failure'] is None and value['proc']['publishers']==[] and len(value['proc']['snapshots'])==2
    else:
        assert value['status']=='PASS_CURRENT_FAILED235_27_4_AND_8_PATH_ABSENCE' and value['lock']==[27,4]
        assert value['paths']==mutex['paths']
# Current NORMAL81 normal retirement is a distinct typed authority, not SDK or artifact acceptance.
current_normal81_physical={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-normal81-normal-retirement-postjoin-1/ROOT-RECORDED-INDEPENDENT-PHYSICAL-ACCEPTANCE.json', 'sha256': '7ae40213a39ca2408009e15323464c3816bf795c4909ce6febd030033fe7b82d', 'bytes': 869}
current_normal81_postjoin={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-normal81-normal-retirement-postjoin-1/CURRENT-LIVE-POSTJOIN.json', 'sha256': 'ec95e79d18c665f06f7ee21407e5caa5c167472bf830d6f774070f6465121527', 'bytes': 1496}
assert set(current_normal81_physical)=={'path','sha256','bytes'} and type(current_normal81_physical['bytes']) is int and current_normal81_physical['bytes']>=0
assert owner.safe_path(current_normal81_physical['path'],False).stat().st_size==current_normal81_physical['bytes']
normal81=owner.bound({k:current_normal81_physical[k] for k in ('path','sha256')})
assert owner.safe_path(current_normal81_physical['path'],False).stat().st_size==current_normal81_physical['bytes']
assert set(current_normal81_postjoin)=={'path','sha256','bytes'} and type(current_normal81_postjoin['bytes']) is int and current_normal81_postjoin['bytes']>=0
assert owner.safe_path(current_normal81_postjoin['path'],False).stat().st_size==current_normal81_postjoin['bytes']
normal81_live=owner.bound({k:current_normal81_postjoin[k] for k in ('path','sha256')})
assert owner.safe_path(current_normal81_postjoin['path'],False).stat().st_size==current_normal81_postjoin['bytes']
assert normal81['status']=='PASS_ACTUAL_M14_NORMAL_CURRENT81_FAILED_IMAGE_PHYSICAL_RETIREMENT'
assert normal81['original_workload_status']=='FAIL' and normal81['artifact_native_acceptance'] is False
assert normal81['current_live_postjoin_accepted_non_null'] is True
assert normal81['implementation_ownership'] is False and normal81['reviewer']=='/root/native235_release_review'
assert normal81['client_births'] is None and normal81['historical_outer_identity'] is None and normal81['host_init_identity'] is None
assert normal81_live['schema']=='mckernel.current-live-postjoin.v1' and normal81_live['status']=='ACCEPTED_NON_NULL'
assert normal81_live['physical_acceptance']==current_normal81_physical
assert normal81_live['original_workload_status']=='FAIL' and normal81_live['artifact_native_acceptance'] is False
normal81_normal_ref={'bytes': 362909, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-normal81-actual-normal-retirement-1/stdout', 'sha256': 'c21cfd8b13740a16d78411ab0fe6cbd1a9138fa644651026ed4effddd4722c45'}
normal81_links={'mutex': {'bytes': 1097, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-normal81-normal-retirement-postjoin-1/1/WHOLE-JOIN.json', 'sha256': '33b98b3db3a075d60f5ce7dc08a9550a6beea909aaa24333f8af783ed3354723'}, 'proc': {'bytes': 1097, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-normal81-normal-retirement-postjoin-1/0/WHOLE-JOIN.json', 'sha256': '45b89ddf417cde1b419f71eec725ec0c0dc66b7c35c1eb42d9def98039b602f6'}}
assert normal81_live['actual_cleanup']==normal81_normal_ref and normal81_live['current_live_postjoin']==normal81_links
assert normal81['normal_result_sha256']==normal81_normal_ref['sha256']
assert normal81['proc_whole_join_sha256']==normal81_links['proc']['sha256']
assert normal81['mutex_whole_join_sha256']==normal81_links['mutex']['sha256']
assert set(normal81_normal_ref)=={'path','sha256','bytes'} and type(normal81_normal_ref['bytes']) is int and normal81_normal_ref['bytes']>=0
assert owner.safe_path(normal81_normal_ref['path'],False).stat().st_size==normal81_normal_ref['bytes']
normal81_normal=owner.bound({k:normal81_normal_ref[k] for k in ('path','sha256')})
assert owner.safe_path(normal81_normal_ref['path'],False).stat().st_size==normal81_normal_ref['bytes']
assert normal81_normal['status']=='PASS_EXECUTED' and normal81_normal['terminal'] is True
assert normal81_normal['container_absent'] is True and normal81_normal['boot_id']==owner.BOOT
for key in ('proc','mutex'):
    assert set(normal81_links[key])=={'path','sha256','bytes'} and type(normal81_links[key]['bytes']) is int and normal81_links[key]['bytes']>=0
    assert owner.safe_path(normal81_links[key]['path'],False).stat().st_size==normal81_links[key]['bytes']
    join=owner.bound({k:normal81_links[key][k] for k in ('path','sha256')})
    assert owner.safe_path(normal81_links[key]['path'],False).stat().st_size==normal81_links[key]['bytes']
    assert join['returncode']==0 and join['direct_child_joined'] and join['group_absent'] and join['closed_streams']
    assert join['error'] is None and join['retirement_error'] is None and join['timed_out'] is False
    assert join['remaining_group_members']==[] and join['unexpected_group_members']==[]
    err=join['captures']['stderr'];err_path=owner.safe_path(err['path'],False)
    assert err['size']==err_path.stat().st_size==0 and owner.host.digest(err_path)==err['sha256']
    out=join['captures']['stdout']
    value=owner.bound({'path':out['path'],'sha256':out['sha256']})
    if key=='proc':
        assert value['status']=='CURRENT_FAILED235_COMPLETE_PROC_OBSERVATION'
        assert value['proc']['schema']=='fp-save-image.proc.v2' and value['proc']['status']=='COMPLETE'
        assert value['proc']['uid']==0 and value['proc']['boot_id']==owner.BOOT
        assert value['proc']['failure'] is None and value['proc']['publishers']==[] and len(value['proc']['snapshots'])==2
    else:
        assert value['status']=='PASS_CURRENT_FAILED235_27_4_AND_8_PATH_ABSENCE' and value['lock']==[27,4]
        assert value['paths']==mutex['paths']
# Latest accepted SDK suffix normal removal; distinct PASS producer and physical-only scope.
current_suffix_physical={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-sdk-retained10-five-suffix-postjoin-1/ROOT-RECORDED-INDEPENDENT-PHYSICAL-ACCEPTANCE.json', 'sha256': 'd28b7a873a47f462bf06b4df4f6e0230b0190f45bcba3b7341da4bd8a6228b64', 'bytes': 691}
current_suffix_postjoin={'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-sdk-retained10-five-suffix-postjoin-1/CURRENT-LIVE-POSTJOIN.json', 'sha256': '22aa8d692203423bd795770227af1221f4e6eec4f88b8c24c6ef53b658294206', 'bytes': 1733}
suffix_owner_ref={'bytes': 126448, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/selected-SDK-library-operation-1/private-library-successor-1/selected-source-1/toolchain-mount-correction-1/tool-FD-expert-correction-1/selected-BFD-image-correction-1/actual-compiler-diagnostics-correction-1/runtime-suffix-successor-1/ROOT-ACTUAL-OWNER-STDOUT.SUFFIX1', 'sha256': '90e402ed2716f0649af54cfe00d8ab299394c7318c8c8d45fdf35127919c3dda'}
suffix_links={'mutex': {'bytes': 1098, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-sdk-retained10-five-suffix-postjoin-1/1/WHOLE-JOIN.json', 'sha256': 'fc89b9e9e822a1fd56cb436308761bbb259e9ba402d1d10940933e9b5b321fb9'}, 'proc': {'bytes': 1098, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/root-sdk-retained10-five-suffix-postjoin-1/0/WHOLE-JOIN.json', 'sha256': '01c040ab0fe394f3c77e161ad921ddb7167e7a5c868339938dc83a6ebec454c9'}}
for ref in (current_suffix_physical,current_suffix_postjoin,suffix_owner_ref,*suffix_links.values()):
    assert set(ref)=={'path','sha256','bytes'} and type(ref['bytes']) is int and ref['bytes']>=0
    assert owner.safe_path(ref['path'],False).stat().st_size==ref['bytes']
suffix=owner.bound({k:current_suffix_physical[k] for k in ('path','sha256')})
suffix_live=owner.bound({k:current_suffix_postjoin[k] for k in ('path','sha256')})
assert suffix['status']=='PASS_ACTUAL_M15_SDK_LIBRARY_SUFFIX_PHYSICAL_RETIREMENT'
assert suffix['owner']=={'pid':261413,'starttime':'66429206'}
assert suffix['artifact_native_acceptance'] is False and suffix['current_live_postjoin_accepted_non_null'] is True
assert suffix['implementation_ownership'] is False and suffix['reviewer']=='/root/native235_release_review'
assert suffix['client_births'] is None and suffix['historical_outer_identity'] is None and suffix['host_init_identity'] is None
assert suffix_live['schema']=='mckernel.current-live-postjoin.v1' and suffix_live['status']=='ACCEPTED_NON_NULL'
assert suffix_live['physical_acceptance']==current_suffix_physical
assert suffix_live['original_workload_status']=='PASS' and suffix_live['artifact_native_acceptance'] is False
assert suffix_live['actual_cleanup']==suffix_owner_ref and suffix_live['current_live_postjoin']==suffix_links
assert suffix['owner_stdout_sha256']==suffix_owner_ref['sha256']
assert suffix['proc_whole_join_sha256']==suffix_links['proc']['sha256'] and suffix['mutex_whole_join_sha256']==suffix_links['mutex']['sha256']
suffix_owner=owner.bound({k:suffix_owner_ref[k] for k in ('path','sha256')})
assert suffix_owner['status']=='PASS' and suffix_owner['retired'] is True
assert suffix_owner['cleanup_status']=='PASS_OWNED_REMOVAL_AND_RECORD_RELEASE' and suffix_owner['cleanup_separately_required'] is False
for key in ('proc','mutex'):
    join=owner.bound({k:suffix_links[key][k] for k in ('path','sha256')})
    assert join['returncode']==0 and all(join[k] is True for k in ('direct_child_joined','group_absent','closed_streams'))
    assert join['error'] is None and join['retirement_error'] is None and join['timed_out'] is False
    assert join['remaining_group_members']==[] and join['unexpected_group_members']==[]
    err=join['captures']['stderr'];err_path=owner.safe_path(err['path'],False)
    assert err['size']==err_path.stat().st_size==0 and owner.host.digest(err_path)==err['sha256']
    out=join['captures']['stdout'];value=owner.bound({'path':out['path'],'sha256':out['sha256']})
    if key=='proc':
        assert value['status']=='CURRENT_FAILED235_COMPLETE_PROC_OBSERVATION'
        assert value['proc']['schema']=='fp-save-image.proc.v2' and value['proc']['status']=='COMPLETE'
        assert value['proc']['uid']==0 and value['proc']['boot_id']==owner.BOOT
        assert value['proc']['failure'] is None and value['proc']['publishers']==[] and len(value['proc']['snapshots'])==2
        assert all(not any(row[0]==261413 for row in sweep) for sweep in value['proc']['snapshots'])
    else:
        assert value['status']=='PASS_CURRENT_FAILED235_27_4_AND_8_PATH_ABSENCE' and value['lock']==[27,4]
        assert value['paths']==mutex['paths']
for ref in (current_suffix_physical,current_suffix_postjoin,suffix_owner_ref,*suffix_links.values()):
    assert owner.safe_path(ref['path'],False).stat().st_size==ref['bytes']

def current_bound(ref):
    assert set(ref)=={'path','sha256','bytes'} and type(ref['bytes']) is int and ref['bytes']>=0
    p=owner.safe_path(ref['path'],False)
    assert p.stat().st_size==ref['bytes']
    value=owner.bound({k:ref[k] for k in ('path','sha256')})
    assert p.stat().st_size==ref['bytes']
    return value

def current_join(label,stdout_label,pid,start):
    j=current_bound(CURRENT_REFS[label])
    assert j['returncode']==0 and all(j[k] is True for k in ('direct_child_joined','group_absent','closed_streams'))
    assert j['pid']==pid and str(j['start'])==start
    assert j['error'] is None and j['retirement_error'] is None and j['timed_out'] is False
    assert j['remaining_group_members']==j['unexpected_group_members']==[]
    out=j['captures']['stdout'];expected=CURRENT_REFS[stdout_label]
    assert {k:out[k] for k in ('path','sha256')}=={k:expected[k] for k in ('path','sha256')} and out['size']==expected['bytes']
    err=j['captures']['stderr'];ep=owner.safe_path(err['path'],False)
    assert ep.stat().st_size==err['size']==0 and owner.host.digest(ep)==err['sha256']
    return j

def current_bound_raw(ref):
    p=owner.safe_path(ref['path'],False)
    assert p.stat().st_size==ref['bytes'] and owner.host.digest(p)==ref['sha256']
    return p.read_bytes()
# Latest52f normal retirement is distinct from retained historical M14/COPY evidence.
CURRENT_REFS = {'proc_stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current52f-precommand-failure-physical-postflight-source-1/0/stdout', 'bytes': 41567, 'sha256': '2b8b80402830da058ec48382afcf8474a890d5e90543ad0ec86f39348a0156a3'}, 'proc_join': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current52f-precommand-failure-physical-postflight-source-1/0/WHOLE-JOIN.json', 'bytes': 1313, 'sha256': '061408361a013ae8d3dc7c38f4189256954b68c5b3471c18da92263a7f329eb0'}, 'physical_stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current52f-precommand-failure-physical-postflight-source-1/1/stdout', 'bytes': 43074, 'sha256': 'c3fd562034169f319cefc1f221828431936b156a8d782661e1210568b249ad5c'}, 'physical_join': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current52f-precommand-failure-physical-postflight-source-1/1/WHOLE-JOIN.json', 'bytes': 1312, 'sha256': 'ca04edc74b23dfb95f8a030d14912dd6b29292de30857565f56c31909663066b'}, 'postjoin_stdout': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current52f-precommand-failure-physical-postflight-source-1/actual-helpers-postjoin-1/0/stdout', 'bytes': 45076, 'sha256': 'bad22bd0da7dbcd4c9d8c4dc0c1133c2f28e40d48e427c49ae805cf7ea17ffd6'}, 'postjoin_join': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current52f-precommand-failure-physical-postflight-source-1/actual-helpers-postjoin-1/0/WHOLE-JOIN.json', 'bytes': 1365, 'sha256': '2386161ce128eb907d7233d976c432f608040bc07d47d81e03e2840c3a11f5dc'}, 'proc_source': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current52f-precommand-failure-physical-postflight-source-1/readonly_precommand_failure_current_proc.py', 'bytes': 8256, 'sha256': 'f7b538bf167baee57486d559429a7ba3748532e3af0b2a1c60eb4f070f3a7eaa'}, 'physical_source': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current52f-precommand-failure-physical-postflight-source-1/readonly_precommand_failure_mutex_physical.py', 'bytes': 9968, 'sha256': '667417bff4fab5840ea883914ade4e01156aaa5514be8d2b24f49d88442e8c84'}, 'postjoin_source': {'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current52f-precommand-failure-physical-postflight-source-1/readonly_precommand_failure_helpers_postjoin.ACTUAL-CAPTURES.NOT-RELEASED.py', 'bytes': 13541, 'sha256': '40b1d7192391438aa4fce5bd8e9d440778d0eb6571004837920ff85250d747b9'}, 'manifest': {'bytes': 80161, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/executor-next-binder-query-source-1/current52f-precommand-failure-physical-postflight-source-1/EXACT-52F-PRECOMMAND-FAILURE-POSTFLIGHT.INPUTS.json', 'sha256': '5866ffab973a0a5e81089c630365b8a3d0541ab535e5f08da819a04cd0ce8b5d'}, 'direct_terminal': {'bytes': 2647, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/52F7-ACTUAL-OWNER-FAILURE-AND-TOOL-TERMINAL.json', 'sha256': 'be86bb8a60e2fe5cafb11a2d7efca3d69b14ac07dfe2cf3bf7f4e71bcff61f9b'}, 'independent_current': {'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/52F7-ACTUAL-PHYSICAL-AND-CURRENT-ACCEPTANCE.json', 'bytes': 1766, 'sha256': 'a9f80ab33d3ae1758b4f8bbc89f5e1abfd2422b0f860faea439d2f49c3c0f862'}}
CURRENT_EXPECTED_INDEPENDENT = {'schema': 'mckernel.m15.executor.precommand-failure.current-acceptance.v1', 'status': 'PASS', 'reviewer': '/root/recovery_review', 'implementation_ownership': False, 'physical_accepted': True, 'current_live_postjoin_accepted': True, 'owner': {'pid': 557761, 'starttime': '70585035'}, 'runtime_nonce': '52f76375b2944beeabbc456aa483ed8a', 'operation_lease_nonce': 'dfa90bc0b8e1402fbfa075cf977342cf', 'manifest_sha256': '5866ffab973a0a5e81089c630365b8a3d0541ab535e5f08da819a04cd0ce8b5d', 'physical_stdout_sha256': 'c3fd562034169f319cefc1f221828431936b156a8d782661e1210568b249ad5c', 'physical_join_sha256': 'ca04edc74b23dfb95f8a030d14912dd6b29292de30857565f56c31909663066b', 'postjoin_stdout_sha256': 'bad22bd0da7dbcd4c9d8c4dc0c1133c2f28e40d48e427c49ae805cf7ea17ffd6', 'postjoin_whole_join_sha256': '2386161ce128eb907d7233d976c432f608040bc07d47d81e03e2840c3a11f5dc', 'current_reader_identity': {'pid': 561541, 'starttime': '70634942', 'boot_id': '7bfc5687-6c04-4d15-84eb-b92ab9a55dcb'}, 'joined_direct_child': {'pid': 561538, 'starttime': '70634935', 'returncode': 0, 'group_absent': True}, 'owner_clients': 14, 'admission_clients': 1, 'additional_query_helpers': 2, 'prior_helpers': 4, 'client_births': None, 'inner_command_births': [], 'permanent_mutex_free_before': True, 'permanent_mutex_free_after': True, 'terminal_evidence_unchanged': True, 'original_workload_status': 'FAIL', 'SDK_commands_executed': 0, 'artifact_native_acceptance': False, 'heavy_execution_released': False, 'scope': 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Actual52f normal-retirement physical and current helper postjoin evidence only.'}
current_proc=current_bound(CURRENT_REFS['proc_stdout'])
current_physical=current_bound(CURRENT_REFS['physical_stdout'])
current_postjoin=current_bound(CURRENT_REFS['postjoin_stdout'])
current_independent=current_bound(CURRENT_REFS['independent_current'])
current_manifest=current_bound(CURRENT_REFS['manifest'])
current_terminal=current_bound(CURRENT_REFS['direct_terminal'])
for key in ('proc_source','physical_source','postjoin_source'):current_bound_raw(CURRENT_REFS[key])
assert current_independent==CURRENT_EXPECTED_INDEPENDENT
assert current_independent['status']=='PASS' and current_independent['implementation_ownership'] is False
assert current_independent['reviewer']=='/root/recovery_review' and current_independent['physical_accepted'] is True and current_independent['current_live_postjoin_accepted'] is True
assert current_independent['heavy_execution_released'] is False and current_independent['artifact_native_acceptance'] is False
assert current_independent['owner']=={'pid':557761,'starttime':'70585035'} and current_independent['runtime_nonce']=='52f76375b2944beeabbc456aa483ed8a'
assert current_independent['operation_lease_nonce']=='dfa90bc0b8e1402fbfa075cf977342cf'
assert current_independent['manifest_sha256']==CURRENT_REFS['manifest']['sha256']
assert current_independent['physical_stdout_sha256']==CURRENT_REFS['physical_stdout']['sha256'] and current_independent['physical_join_sha256']==CURRENT_REFS['physical_join']['sha256']
assert current_independent['postjoin_stdout_sha256']==CURRENT_REFS['postjoin_stdout']['sha256'] and current_independent['postjoin_whole_join_sha256']==CURRENT_REFS['postjoin_join']['sha256']
assert current_independent['current_reader_identity']==current_postjoin['current_reader_identity']
for value,identity in ((current_proc,{'boot_id':owner.BOOT,'pid':560722,'starttime':'70624890'}),(current_physical,{'boot_id':owner.BOOT,'pid':560727,'starttime':'70624918'}),(current_postjoin,{'boot_id':owner.BOOT,'pid':561541,'starttime':'70634942'})):
    assert value['current_reader_identity']==identity and value['owner']==current_independent['owner']
    assert value['manifest']==CURRENT_REFS['manifest'] and value['direct_terminal']==CURRENT_REFS['direct_terminal']
    assert value['client_births'] is None and value['inner_command_births']==[] and value['SDK_commands_executed']==0 and value['original_workload_status']=='FAIL'
    proc=value['proc'];assert proc['schema']=='fp-save-image.proc.v2' and proc['status']=='COMPLETE' and proc['uid']==0 and proc['boot_id']==owner.BOOT
    assert proc['failure'] is None and proc['publishers']==[] and len(proc['snapshots'])==2
    assert all(not any(row[0]==557761 for row in sweep) for sweep in proc['snapshots'])
assert current_proc['schema']==current_physical['schema']=='mckernel.m15.executor.precommand-failure.physical-readback.v1'
assert current_proc['status']=='PASS_M15_EXECUTOR_PRECOMMAND_FAILURE_EXACT_PROC' and current_proc['owner_client_count']==14 and current_proc['admission_client_count']==1
assert current_physical['status']=='PASS_M15_EXECUTOR_PRECOMMAND_FAILURE_MUTEX_HELD_CURRENT_PHYSICAL'
assert current_physical['container_absent']=={'id':'e7b186804d5df09464fa7a4a966be4c5428bbecf085998a80a754c1422a6c36c','name':'mckernel-external-52f76375b2944beeabbc456aa483ed8a','nonce':'52f76375b2944beeabbc456aa483ed8a'}
assert current_physical['installed_artifacts']==[] and current_physical['artifact_native_acceptance'] is False
assert current_physical['owner_clients']==current_postjoin['owner_clients']==14 and current_physical['admission_clients']==current_postjoin['admission_clients']==1
assert current_physical['root_lock']==current_postjoin['root_lock']=={'device': 27, 'gid': 0, 'inode': 4, 'mode': '0o644', 'nlink': 1, 'path': '/run/lock/mckernel-development.lock', 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855', 'size': 0, 'uid': 0}
assert current_physical['absence_paths']==current_postjoin['absence_paths']==['/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/image-lease.json', '/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/lease.json', '/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock', '/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch18-image-1.json', '/home/holden/mckernel-work/scratch/native-running-external-modules-operational-exclusion.json', '/home/holden/mckernel-work/scratch/native-running-external-modules.lease.json']
assert current_postjoin['schema']=='mckernel.m15.executor.precommand-failure.postjoin-readback.v1'
assert current_postjoin['status']=='PASS_M15_EXECUTOR_PRECOMMAND_FAILURE_CURRENT_HELPERS_POSTJOIN_MUTEX_FREE'
assert current_postjoin['known_prior_helpers']==[{'pid': 560722, 'role': 'proc-python', 'starttime': '70624890'}, {'pid': 560719, 'role': 'proc-sudo', 'starttime': '70624883'}, {'pid': 560727, 'role': 'physical-python', 'starttime': '70624918'}, {'pid': 560724, 'role': 'physical-sudo', 'starttime': '70624911'}]
assert current_postjoin['prior_captures']=={k:CURRENT_REFS[k] for k in ('proc_stdout','proc_join','physical_stdout','physical_join')}
assert current_postjoin['permanent_mutex_free_before'] is True and current_postjoin['permanent_mutex_free_after'] is True and current_postjoin['flock_acquired'] is False and current_postjoin['terminal_evidence_unchanged'] is True
assert all(not any(row[0] in {560722,560719,560727,560724} for row in sweep) for sweep in current_postjoin['proc']['snapshots'])
current_join('proc_join','proc_stdout',560719,'70624883')
current_join('physical_join','physical_stdout',560724,'70624911')
current_join('postjoin_join','postjoin_stdout',561538,'70634935')

mountpoint=owner.safe_path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/lib/libdwarf/libdwarf')
assert owner.node(mountpoint)==request['libdwarf_mountpoint_identity']=={'device': 66306, 'gid': 1000, 'inode': 59513832, 'mode': 448, 'path': '/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/executor-integration-source-2/sdk11-lifetime-adapter-source-1/source-materialization-1/materialized-source/executer/user/lib/libdwarf/libdwarf', 'uid': 1000}
assert mountpoint.stat().st_uid==mountpoint.stat().st_gid==1000 and (mountpoint.stat().st_mode & 0o7777)==0o700 and not list(mountpoint.iterdir())

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
summary=dict(scope=__doc__,status='PASS_READONLY_SDK_CAPACITY_IDENTITY_IMAGE_ONLY',at=time.time(),request_sha256=inputs['request_sha256'],resources=capacity,mount=mount,image_id=info[0]['Id'],image_Architecture=info[0]['Architecture'],group_checks=client.group_checks,conflict_paths_absent=[str(p) for p in sorted(conflicts)],current_physical_acceptance=CURRENT_REFS['physical_stdout']['sha256'],current_postjoin=CURRENT_REFS['postjoin_stdout']['sha256'],current_clearance_scope=current_physical['status'],current_retained_closure=CURRENT_REFS,historical_F03_original_cleanup_identity=None,historical_F03_original_full_stdout=None,historical_F03_original_stdout_capture_complete=False,current_owner_identity=current_physical['owner'],original_workload_status=current_physical['original_workload_status'],SDK_commands_executed=current_physical['SDK_commands_executed'],original_full_stdout=current_terminal['owner_stdout'],original_stdout_capture_complete=True,original_direct_terminal=CURRENT_REFS['direct_terminal'],root_metadata_publisher_identity=None,current_suffix_physical=current_suffix_physical,current_suffix_postjoin=current_suffix_postjoin,current_suffix_owner=suffix_owner_ref,historical_normal81_physical=current_normal81_physical,historical_normal81_postjoin=current_normal81_postjoin,historical_normal81_normal=normal81_normal_ref,historical_copy6_physical=current_copy6_physical,historical_copy6_postjoin=current_copy6_postjoin,historical_copy6_normal=copy6_normal_ref,historical_latest_sdk_retirement=latest_sdk_retirement,historical_latest_sdk_postjoin=latest_sdk_postjoin,historical_token_clearance=current_token_clearance,historical_token_postjoin=current_token_postjoin,selected_image_receipt=selected_image_receipt,prior_sdk_normal_retirement=prior_sdk_normal_retirement,prior_sdk_normal_postjoin=prior_sdk_normal_postjoin,reconciliation_links=expected_links,target_calls=0,container_create_calls=0,execution_release=False)
(E/'ADMISSION.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(status=summary['status'],at=summary['at'],resources=capacity,image=info[0]['Id'],target_calls=0)))
