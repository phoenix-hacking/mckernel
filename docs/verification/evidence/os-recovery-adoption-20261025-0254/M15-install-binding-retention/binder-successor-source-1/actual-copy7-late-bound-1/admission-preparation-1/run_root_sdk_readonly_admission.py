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
assert request_path.is_absolute() and request_path.parent==Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1')
request_raw=request_path.read_bytes()
assert hashlib.sha256(request_raw).hexdigest()==inputs['request_sha256']
request=json.loads(request_raw)
assert request['request_path']==str(request_path)
OWNER=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/actual-source-SDK11-installed-consumer-preparation-1/sdk-install-top-level-mount-correction-1/target_tools_sdk_owner.py')
assert hashlib.sha256(OWNER.read_bytes()).hexdigest()=='2ec8e85696e47f9abcfa2a5eeada22880471ecdd022dc89424480d950184a03f'
spec=importlib.util.spec_from_file_location('library_sdk_admission_owner',OWNER)
owner=importlib.util.module_from_spec(spec);spec.loader.exec_module(owner)
source_sha256 = {'scripts/native_exact_historical_lease_observer.py': '463ae558e141c2a6fe5a016fb19baddb26ed883c3bf6d39c114b27711ee78a51', 'scripts/native_running_external_modules_offline.py': 'b15e0a5bc85c8d517c7804aba5e0d0e36ca76231a7dd672221b2839a29f2c328', 'scripts/native_running_external_modules_owner.py': '2ec8e85696e47f9abcfa2a5eeada22880471ecdd022dc89424480d950184a03f', 'scripts/native_rust_exact_build_container_owner.py': '96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1', 'scripts/native_rust_exact_build_image_prepare.py': '45cb12e0fd58d164468badfb99a3ed922e65e06046bf38b4a50e27e18595a27b', 'scripts/native_rust_exact_build_image_rebind.py': 'f10ab116e55a24e8db7a8157d71efdd01198ba3453a8141bc8bbf596eda6b61e', 'scripts/native_rust_exact_build_image_rebind_probe.py': '412d46de7e078746a7ec979a13ccb25753d6fa34708610932e35be8f02a89635', 'scripts/native_rust_exact_build_offline.py': 'cc243126ab8cc0754c62175c77e46d6ba0d98294f8168cc77893a2c12249cd1a', 'scripts/native_rust_exact_disk_build_wrapper.py': 'c252ee341eb61752704f8b818503c0a5dc97400845494707ca3110f5f23df6d1', 'scripts/native_rust_exact_mckernel_image_container_owner.py': 'e9861cf73b0328c9fe2eacb987ea179933146cbeddbc3951405d4e60e89560f4', 'scripts/tests/test_native_running_external_modules_owner.py': 'c816f7dfd6fa167670876d8e64e8474bec119e1f19280fcc1cb902dff1a2c340'}
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

# Current NORMAL_CFG normal retirement is a distinct typed authority, not SDK or artifact acceptance.
EXPECTED_CURRENT_PHYSICAL_STATUS = 'PASS_ACTUAL_M14_COPY7_NORMAL_FAILED_IMAGE_PHYSICAL_RETIREMENT'
EXPECTED_OWNER_PID = 413643
EXPECTED_OWNER_START = '68359948'
EXPECTED_CLEANUP_PID = 473751
EXPECTED_CLEANUP_START = '69456080'
current_normal_cfg_physical = {'bytes': 1657, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/copy7-normal-image-retirement-preparation-1/recovery-source-reconciliation-20261025-1/physical-postflight-source-1/ROOT-RECORDED-INDEPENDENT-PHYSICAL-ACCEPTANCE.json', 'sha256': 'dda45e6348748469bb15734ff585733b5a18c405f907f82e9e9e0f9c4c1e0129'}
current_normal_cfg_postjoin = {'bytes': 3918, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/copy7-normal-image-retirement-preparation-1/recovery-source-reconciliation-20261025-1/physical-postflight-source-1/CURRENT-LIVE-POSTJOIN.json', 'sha256': 'f37ff2d1507d6cacd69c76ca0749c91b44b8b5783dd5b3716ff775f80375393f'}
assert set(current_normal_cfg_physical)=={'path','sha256','bytes'} and type(current_normal_cfg_physical['bytes']) is int and current_normal_cfg_physical['bytes']>=0
assert owner.safe_path(current_normal_cfg_physical['path'],False).stat().st_size==current_normal_cfg_physical['bytes']
normal_cfg=owner.bound({k:current_normal_cfg_physical[k] for k in ('path','sha256')})
assert owner.safe_path(current_normal_cfg_physical['path'],False).stat().st_size==current_normal_cfg_physical['bytes']
assert set(current_normal_cfg_postjoin)=={'path','sha256','bytes'} and type(current_normal_cfg_postjoin['bytes']) is int and current_normal_cfg_postjoin['bytes']>=0
assert owner.safe_path(current_normal_cfg_postjoin['path'],False).stat().st_size==current_normal_cfg_postjoin['bytes']
normal_cfg_live=owner.bound({k:current_normal_cfg_postjoin[k] for k in ('path','sha256')})
assert owner.safe_path(current_normal_cfg_postjoin['path'],False).stat().st_size==current_normal_cfg_postjoin['bytes']
assert normal_cfg['status']==EXPECTED_CURRENT_PHYSICAL_STATUS
assert normal_cfg['original_workload_status']=='FAIL' and normal_cfg['artifact_native_acceptance'] is False
assert normal_cfg['schema']=='mckernel.copy7.normal-retirement.physical-acceptance.v1' and normal_cfg_live['status']=='ACCEPTED_NON_NULL' and normal_cfg_live['independent_physical']==current_normal_cfg_physical
assert normal_cfg['implementation_ownership'] is False and normal_cfg['reviewer']=='/root/recovery_review'
assert normal_cfg['client_births'] is None and 'historical_outer_identity' not in normal_cfg and normal_cfg['host_init_identity'] is None
assert normal_cfg_live['schema']=='mckernel.current-live-postjoin.v1' and normal_cfg_live['status']=='ACCEPTED_NON_NULL'
assert normal_cfg_live['independent_physical']==current_normal_cfg_physical
assert normal_cfg_live['original_workload_status']=='FAIL' and normal_cfg_live['native_acceptance'] is False
normal_cfg_normal_ref = {'bytes': 369056, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/copy7-normal-image-retirement-preparation-1/recovery-source-reconciliation-20261025-1/actual-normal-cleanup-1/stdout', 'sha256': 'eef16afae29dd5441d393c22c9010ffa49a698e1eb371f81577a52c4df0eba4e'}
normal_cfg_links = {'proc': {'bytes': 1850, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/copy7-normal-image-retirement-preparation-1/recovery-source-reconciliation-20261025-1/physical-postflight-source-1/0/WHOLE-JOIN.json', 'sha256': '54d6096e927c9420f84b145d8e59a22ec411ff23af71090631e8ff8d49fe1825'}, 'mutex': {'bytes': 1850, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/copy7-normal-image-retirement-preparation-1/recovery-source-reconciliation-20261025-1/physical-postflight-source-1/1/WHOLE-JOIN.json', 'sha256': 'b026ad02b00e5d3e3615763dce52e01b5854bd2094896805d3716752e2b6ffad'}}
assert normal_cfg_live['proc_whole_join']==normal_cfg_links['proc'] and normal_cfg_live['mutex_whole_join']==normal_cfg_links['mutex']
assert normal_cfg['normal_result_sha256']==normal_cfg_normal_ref['sha256']
assert normal_cfg['proc_whole_join_sha256']==normal_cfg_links['proc']['sha256']
assert normal_cfg['mutex_whole_join_sha256']==normal_cfg_links['mutex']['sha256']
assert set(normal_cfg_normal_ref)=={'path','sha256','bytes'} and type(normal_cfg_normal_ref['bytes']) is int and normal_cfg_normal_ref['bytes']>=0
assert owner.safe_path(normal_cfg_normal_ref['path'],False).stat().st_size==normal_cfg_normal_ref['bytes']
normal_cfg_normal=owner.bound({k:normal_cfg_normal_ref[k] for k in ('path','sha256')})
assert owner.safe_path(normal_cfg_normal_ref['path'],False).stat().st_size==normal_cfg_normal_ref['bytes']
assert normal_cfg_normal['status']=='PASS_EXECUTED' and normal_cfg_normal['terminal'] is True
assert normal_cfg_normal['container_absent'] is True and normal_cfg_normal['boot_id']==owner.BOOT
for key in ('proc','mutex'):
    assert set(normal_cfg_links[key])=={'path','sha256','bytes'} and type(normal_cfg_links[key]['bytes']) is int and normal_cfg_links[key]['bytes']>=0
    assert owner.safe_path(normal_cfg_links[key]['path'],False).stat().st_size==normal_cfg_links[key]['bytes']
    join=owner.bound({k:normal_cfg_links[key][k] for k in ('path','sha256')})
    assert owner.safe_path(normal_cfg_links[key]['path'],False).stat().st_size==normal_cfg_links[key]['bytes']
    assert join['returncode']==0 and join['direct_child_joined'] and join['group_absent'] and join['closed_streams']
    assert join['error'] is None and join['retirement_error'] is None and join['timed_out'] is False
    assert join['remaining_group_members']==[] and join['unexpected_group_members']==[]
    err=join['captures']['stderr'];err_path=owner.safe_path(err['path'],False)
    assert err['size']==err_path.stat().st_size==0 and owner.host.digest(err_path)==err['sha256']
    out=join['captures']['stdout']
    value=owner.bound({'path':out['path'],'sha256':out['sha256']})
    assert out['sha256']==normal_cfg['proc_stdout_sha256' if key=='proc' else 'mutex_stdout_sha256']
    assert value['normal_result']==normal_cfg_normal_ref
    assert value['proc']['schema']=='fp-save-image.proc.v2' and value['proc']['status']=='COMPLETE'
    assert value['proc']['uid']==0 and value['proc']['boot_id']==owner.BOOT
    assert value['proc']['failure'] is None and value['proc']['publishers']==[] and len(value['proc']['snapshots'])==2
    if key=='proc':
        assert value['status']=='PASS_COPY7_COMPLETE_PROC_OBSERVATION'
        assert value['known_owner']=={'pid':413643,'starttime':'68359948'}
        assert value['known_cleanup']=={'pid':473751,'starttime':'69456080','sudo_pid':473748}
        assert value['waiter_pids']==[473751,473748,414842,416203,414785,416194,414777,414759,414767]
    else:
        assert value['status']=='PASS_COPY7_MUTEX_HELD_PHYSICAL_POSTFLIGHT'
        assert value['root_lock']['device']==27 and value['root_lock']['inode']==4
        assert value['root_lock']['uid']==value['root_lock']['gid']==0 and value['root_lock']['mode']=='0o644'
        assert value['root_lock']['nlink']==1 and value['root_lock']['size']==0
        assert value['absence_paths']==['/home/holden/mckernel-work/scratch/native-running-external-modules.lease.json', '/home/holden/mckernel-work/scratch/native-running-external-modules-operational-exclusion.json', '/home/holden/mckernel-work/scratch/native-exact-candidate-operational-exclusion-scratch18-image-1.json', '/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock', '/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/lease.json', '/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/common-exclusion.json', '/home/holden/mckernel-work/host-preparation/current68-native235-production-binding-20261022-1/launcher-successor-1/driver-hash-correction-1/pinned-launcher-attempt-1/image-lease.json', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/retained-normal-prefix-attempt-7-retained-witness-validation/common-exclusion.json', '/home/holden/mckernel-work/scratch/mckernel-heavy-operation.lock', '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/retained-normal-prefix-attempt-7-retained-witness-validation/lease.json', '/home/holden/mckernel-work/scratch/m14-copy7-normal-image-retirement-20261024-1.quarantine.json']
        assert value['container_absent']=={'container_id':'0e41e2cf1f390c77108eafef7d031a1d1e561485a38ed7524f77d953e0c62d70','name':'mckernel-image-fbd1b114f56344f4a44ca4c077ceb6e5','nonce':'76b2af948f3440219ad33c013fc3fbcb'}
        assert value['cleanup']=={'pid':473751,'starttime':'69456080','sudo_pid':473748}
        assert value['artifact_native_acceptance'] is False
        assert value['preserved_inventory_rows']==normal_cfg['preserved_inventory_rows']==617
        assert value['preserved_selected_files']==normal_cfg['preserved_selected_files']==71
        assert value['journal_events']==normal_cfg['journal_events']==9
        assert value['transaction_records']==[normal_cfg_normal['plan'],normal_cfg_normal['journal'],normal_cfg_normal['capture'],*normal_cfg_normal['archives']]
assert normal_cfg['owner_pid']==EXPECTED_OWNER_PID and normal_cfg['owner_starttime']==EXPECTED_OWNER_START and normal_cfg['cleanup_pid']==EXPECTED_CLEANUP_PID and normal_cfg['cleanup_starttime']==EXPECTED_CLEANUP_START

mountpoint=owner.safe_path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/source-materialization-1/materialized-source/executer/user/lib/libdwarf/libdwarf')
assert owner.node(mountpoint)==request['libdwarf_mountpoint_identity']=={'device': 66306, 'gid': 1000, 'inode': 59269718, 'mode': 448, 'path': '/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/canonical-source-producer-SDK-target-operation-1/bounded-top-level-cache-dependency-correction-1/source-materialization-1/materialized-source/executer/user/lib/libdwarf/libdwarf', 'uid': 1000}
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
summary=dict(scope=__doc__,status='PASS_READONLY_SDK_CAPACITY_IDENTITY_IMAGE_ONLY',at=time.time(),request_sha256=inputs['request_sha256'],resources=capacity,mount=mount,image_id=info[0]['Id'],image_Architecture=info[0]['Architecture'],group_checks=client.group_checks,conflict_paths_absent=[str(p) for p in sorted(conflicts)],current_physical_acceptance=current_normal_cfg_physical['sha256'],current_postjoin=current_normal_cfg_postjoin['sha256'],current_clearance_scope=normal_cfg['status'],current_normal_cfg_physical=current_normal_cfg_physical,current_normal_cfg_postjoin=current_normal_cfg_postjoin,current_normal_cfg_normal=normal_cfg_normal_ref,current_suffix_physical=current_suffix_physical,current_suffix_postjoin=current_suffix_postjoin,current_suffix_owner=suffix_owner_ref,historical_normal81_physical=current_normal81_physical,historical_normal81_postjoin=current_normal81_postjoin,historical_normal81_normal=normal81_normal_ref,historical_copy6_physical=current_copy6_physical,historical_copy6_postjoin=current_copy6_postjoin,historical_copy6_normal=copy6_normal_ref,historical_latest_sdk_retirement=latest_sdk_retirement,historical_latest_sdk_postjoin=latest_sdk_postjoin,historical_token_clearance=current_token_clearance,historical_token_postjoin=current_token_postjoin,selected_image_receipt=selected_image_receipt,prior_sdk_normal_retirement=prior_sdk_normal_retirement,prior_sdk_normal_postjoin=prior_sdk_normal_postjoin,reconciliation_links=expected_links,target_calls=0,container_create_calls=0,execution_release=False)
(E/'ADMISSION.json').write_text(json.dumps(summary,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(status=summary['status'],at=summary['at'],resources=capacity,image=info[0]['Id'],target_calls=0)))
