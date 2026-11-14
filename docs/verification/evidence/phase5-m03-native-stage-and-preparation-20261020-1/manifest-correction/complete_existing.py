"""Remaining metadata publication only after the separately checked boundary."""
from pathlib import Path
import argparse,hashlib,json,os,importlib.util
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("checked_existing_m03",D/"check_existing.py");checked=importlib.util.module_from_spec(spec);spec.loader.exec_module(checked)
authority=checked.authority;write_json=checked.write_json;FIELDS=checked.FIELDS
p=argparse.ArgumentParser();p.add_argument('--validation-sha256',required=True);args=p.parse_args()
raw=(D/'LOCAL-CHECK-RESULT.json').read_bytes()
if hashlib.sha256(raw).hexdigest()!=args.validation_sha256:raise ValueError('exact independently reviewed local validation bytes')
proof=json.loads(raw)
if proof['status']!='PASS_COMPLETE_ACTUAL_MANIFEST_ARCHIVE_AND_TWO_NEGATIVES' or len(proof['negatives'])!=2 or proof['manifest_published'] or proof['recompression']:raise ValueError('complete actual prior validation')
inputs,parent,binding,collector,overlay,doc,nd,identities=authority()
if proof['manifest_proposal']!=inputs['proposal'] or proof['exact_existing_archive']!=inputs['archive'] or proof['exact_existing_overlay']!=inputs['overlay'] or proof['identities']!=identities:raise ValueError('same immutable actual authority after review')
if any((D/name).exists() for name in ['manifest.json','stage-result.json','COMPLETION-RESULT.json']):raise ValueError('fresh metadata outputs')
write_json(D/'manifest.json',doc)
# Re-read through the actual unchanged typed loader before reporting completion.
if nd.load_manifest(str(D/'manifest.json'))!=doc:raise ValueError('whole emitted typed manifest')
def ref(path):
 b=path.read_bytes();s=path.lstat();return dict(path=str(path),sha256=hashlib.sha256(b).hexdigest(),size=s.st_size,mode=s.st_mode)
result=dict(status='M03_EXISTING_ARCHIVE_METADATA_COMPLETION_ONLY',manifest=ref(D/'manifest.json'),original_archive=inputs['archive'],original_overlay=inputs['overlay'],parent=inputs['parent_manifest'],local_validation=dict(path=str(D/'LOCAL-CHECK-RESULT.json'),sha256=args.validation_sha256,size=len(raw)),original_prefix_unchanged=True,only_final_changed_members=['apps/app','init'],original_failed_stage_preserved=True,recompression=False,new_archive_copies=False,app_execution=False,guest_runs=0,native_acceptance=False)
write_json(D/'stage-result.json',result)
write_json(D/'COMPLETION-RESULT.json',dict(result,stage_result=ref(D/'stage-result.json')))
print(json.dumps(dict(status='PASS_METADATA_COMPLETION_ONLY',manifest=ref(D/'manifest.json'),recompression=False,guest_runs=0)))
