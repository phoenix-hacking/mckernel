"""Minimal DATA join and source-pin successor; no stage/archive/VM action."""
from pathlib import Path
import copy,difflib,hashlib,json,stat
HERE=Path(__file__).resolve().parent
BASE=Path('/home/holden/mckernel-work/host-preparation/phase5-child-exec-wait-native-preparation-20261020-1/source/scripts/application-tests/native_diagnostic_stager.py')
BATCH=Path('/home/holden/mckernel-work/host-preparation/p-m06-production-launcher-native-batch-binding-20261022-1/NEXT-NATIVE-BATCH-DATA.json')
Q=Path('/home/holden/mckernel-work/host-preparation/m05-sdk68-canonical-host-output-request-20261022-1')
P=Path('/home/holden/mckernel-work/host-preparation/seven-check-closure-20261022-1/provider-opt-in-1/current-export-contract-correction-1')
G=Path('/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/owner-work')
MODULES=Path('/home/holden/mckernel-work/host-preparation/native-running-modules-host-output/native-running-modules-candidate-20352dabb9c94403a03c224ec2826ff2/modules')
REPORT=P/'readonly-validation-1/report.json';ACCEPT=Q/'INDEPENDENT-CURRENT68-RETAINED-ARTIFACT-ACCEPTANCE-1.json';RETIRE=Q/'INDEPENDENT-ACTUAL-FAILED-SDK-RETIREMENT-2.json'
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def validate_join(report,acceptance,retirement,original):
 assert report['schema']=='mckernel.current68.retained-artifact-revalidation.v1' and report['status']=='RETAINED_CURRENT68_ARTIFACT_CHECKS_PASS','typed retained observation'
 assert acceptance['status']=='PASS' and acceptance['decision']=='ACCEPT_CURRENT68_RETAINED_LINKED_ARTIFACTS_AND_SOURCE_BINDINGS_ONLY' and acceptance['implementation_ownership']is False,'independent artifact acceptance'
 assert acceptance['export_profile']=='current-v6-adopt-v4-control-v1','accepted current export profile'
 assert acceptance['source_identity']==report['source_identity']=='d9b827db21614e84e45f647deddf6df0a8fec8703da8a716d976d843f78ff3b9','exact current68 source tuple'
 assert acceptance['preparation_sha256']==report['preparation_sha256']=='26a572abd9ee003ca6fef03fbe110d3a5ec6e54aa701ae3b5ffc9b798318f7cb','exact preparation tuple'
 assert report['before_after_retained_hashes_match']is True and report['build_reexecuted']is False and report['compiled_bytes_modified']is False,'retained observation preservation'
 assert original['status']=='FAIL' and original['make_returncode']==0 and report['original_driver_status']=='FAIL','original failed build receipt is immutable'
 assert original['source_candidate_sha']==report['source_identity'] and original['preparation_sha256']==report['preparation_sha256'],'original build tuple'
 assert retirement['status']=='PASS' and retirement['decision']=='ACCEPT_FAILED_SDK_HOST_OWNER_CONTAINER_AND_RECORD_RETIREMENT_ONLY' and retirement['host_retirement_accepted']is True and retirement['build_status']=='FAIL','separate physical retirement'
 assert retirement['container_absent']is True and retirement['owner_direct_joined_streams_closed_group_absent']is True and retirement['owned_records_archived_and_released']==3,'positive owner/container/record retirement'
 assert set(acceptance['artifacts'])=={'ihk.ko','ihk-smp-x86_64.ko','mcctrl.ko'} and set(report['artifacts'])=={'ihk','ihk-smp-x86_64','mcctrl'},'exact three modules'
 vermagics=set()
 for filename,accepted in acceptance['artifacts'].items():
  row=report['artifacts'][filename[:-3]]
  assert (row['sha256'],row['bytes'])==(accepted['sha256'],accepted['bytes']),'accepted artifact hash/size'
  vermagics.add(row['modinfo']['vermagic'])
 assert vermagics=={'6.12.0-211.44.1.el10_2.mckernel1.x86_64 SMP preempt mod_unload '},'matching exact vermagic'
 assert report['artifacts']['ihk']['export_contract']['profile']==acceptance['export_profile'],'source-aware export profile'
 assert report['artifacts']['mcctrl']['actual_mm_provider']['status']=='PASS_ACTUAL_COMPOSITE_MM_PROVIDER_SYMBOLS','retained MM provider proof'
 return True

def prepare():
 report=json.loads(REPORT.read_bytes());acceptance=json.loads(ACCEPT.read_bytes());retirement=json.loads(RETIRE.read_bytes());original_path=Path(report['original_driver_receipt']['path']);original=json.loads(original_path.read_bytes())
 assert ref(REPORT)['sha256']==acceptance['validation_report_sha256']=='f11eb168837814022b00a8d1d69f24124e11274e7f1af0eb45ed2ef206fc45e8'
 assert ref(original_path)['sha256']==acceptance['original_failed_receipt_preserved_sha256']==report['original_driver_receipt']['sha256']=='58ffcfb9febb788d6e3f4c6d949f0307c88031b95940655b49f8a577a0bbb2d3'
 assert ref(RETIRE)['sha256']==acceptance['host_retirement_review_sha256']=='b09d1ffa57d34fc4e270de81ab9fdd28d028f732a26ba5766db16e4d8710e989'
 validate_join(report,acceptance,retirement,original)
 batch=json.loads(BATCH.read_bytes());payloads={x['binary']['path']:x['binary']['sha256']for x in batch['cases']}
 raw=BASE.read_text();assert hashlib.sha256(raw.encode()).hexdigest()=='e935383fac40ec9f2e10f6ffdd42c5e7c4c0de49a243cb34ec0e9b417f5ec860'
 post=raw.replace('MCEEXEC_SHA256 = "689dcad27b2ce3a30f49df1bfe9452f2169a14e9c350c24c9677c88b1f152876"','MCEEXEC_SHA256 = "0d774a14c08bdd4abcd0368060ca8eafba18bf44244dafba5459f895c5d78a7a"',1).replace('MCEEXEC_SIZE = 394656','MCEEXEC_SIZE = 394640',1)
 needle='    _fail(_hash(payload) == PAYLOAD_SHA256, "payload hash mismatch")'
 assert post.count(needle)==1
 post=post.replace(needle,'    _fail(str(payload) in SELECTED_APP_PAYLOADS and _hash(payload) == SELECTED_APP_PAYLOADS[str(payload)], "selected app payload path/hash mismatch")',1)
 post=post.replace('LOADER = ', 'SELECTED_APP_PAYLOADS = '+repr(payloads)+'\nLOADER = ',1)
 stage=HERE/'native_diagnostic_stager.current68.py';stage.write_text(post)
 (HERE/'STAGER-PINS-ONLY.diff').write_text(''.join(difflib.unified_diff(raw.splitlines(True),post.splitlines(True),fromfile=str(BASE),tofile=str(stage))))
 image_receipt=G/'evidence/receipt.json';image_data=json.loads(image_receipt.read_bytes());assert image_data['status']=='PASS'
 image=G/'output/build/kernel/mckernel.img';artifact=image_data['artifacts']['mckernel.img']
 def descriptor(p,digest,size):
  p=Path(p);s=p.stat();assert s.st_size==size;return dict(path=str(p),sha256=digest,size=size,mode=stat.S_IMODE(s.st_mode))
 replacements={('modules/'+name):descriptor(MODULES/name,item['sha256'],item['bytes'])for name,item in acceptance['artifacts'].items()}
 replacements['images/mckernel.img']=descriptor(image,artifact['sha256'],artifact['size'])
 replacements['bin/mcexec']=descriptor(batch['new_launcher']['path'],batch['new_launcher']['sha256'],batch['new_launcher']['bytes'])
 (HERE/'REPLACEMENTS.ACTUAL-CURRENT68-AND-IMAGE.json').write_text(json.dumps(replacements,indent=2)+'\n')
 data=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='TYPED_CURRENT68_ACCEPTED_STAGE_INPUT_BINDING_ONLY_NOT_STAGE_OR_RUNTIME_RELEASE',observation=ref(REPORT),independent_artifact_acceptance=ref(ACCEPT),original_failed_driver_receipt=ref(original_path),independent_failed_owner_retirement=ref(RETIRE),source_identity=report['source_identity'],preparation_sha256=report['preparation_sha256'],export_profile=acceptance['export_profile'],vermagic=report['artifacts']['ihk']['modinfo']['vermagic'],original_status='FAIL',original_make_returncode=0,original_receipt_relabelled=False,existing_stager_receipt_parser='None: production replacement consumer takes exactfiledescriptors and does not read BUILD_ARTIFACT_CHECKS_PASS or any buildreceiptstatus; no typedstatusgate added.',stager=ref(stage),stager_preimage=ref(BASE),stager_diff=ref(HERE/'STAGER-PINS-ONLY.diff'),replacement_map=ref(HERE/'REPLACEMENTS.ACTUAL-CURRENT68-AND-IMAGE.json'),launcher=batch['new_launcher'],cases=batch['cases'],collector=batch['reuse_existing_collector'],runner=batch['reuse_runtime']['runner'],existing_runtime=batch['reuse_runtime'],image=dict(artifact=replacements['images/mckernel.img'],driver_receipt=ref(image_receipt),driver_status='PASS',physical_retirement_accepted=None,independent_linked_provider_review=None),stage=None,archive=None,manifest=None,root_runtime_release=None,actual_apps=0,native_acceptance=False,SDK_original_failure_preserved=True)
 (HERE/'CURRENT68-STAGE-INPUT-DATA.json').write_text(json.dumps(data,indent=2)+'\n')
 print(json.dumps(dict(status=data['status'],stager=data['stager'],image=data['image']['artifact'],three_module_hashes={k:v['sha256']for k,v in replacements.items()if k.startswith('modules/')})))
if __name__=='__main__':prepare()
