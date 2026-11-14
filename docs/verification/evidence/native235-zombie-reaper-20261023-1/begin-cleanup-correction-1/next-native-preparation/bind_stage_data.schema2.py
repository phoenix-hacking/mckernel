"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Two-record successor of accepted actual snapshot/base receipt binder; no stage execution.
"""
from pathlib import Path
import argparse,hashlib,json,os
E=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/begin-cleanup-native-successor-2')
def load(p):return json.loads(p.read_text())
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def save(p,d):
 with p.open('x')as f:json.dump(d,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
def captured(p):
 r=load(p);assert r['status']=='COMPLETED'and r['cleanup_complete']is True and r['wait_status']=={'kind':'exited','code':0}and r['descendants']==[]
 for label in ['stdout','stderr']:
  s=r['streams'][label];assert s['eof']is True and s['truncated']is False and s['discarded_observed_bytes']==0;q=s['artifact'];raw=Path(q['path']).read_bytes();assert len(raw)==q['size']and hashlib.sha256(raw).hexdigest()==q['sha256'];assert label!='stderr'or not raw
 return json.loads(Path(r['streams']['stdout']['artifact']['path']).read_text())
def main():
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['snapshot','base']);a=p.parse_args();producer=load(E/'PRODUCER-TWO-MODULES.ACTUAL.json');accepted=producer['sdk_independent_artifact_acceptance'];assert ref(Path(accepted['path']))==accepted and load(Path(accepted['path']))['status']=='PASS'
 members=['modules/ihk-smp-x86_64.ko','modules/mcctrl.ko']
 if a.phase=='snapshot':
  copies={};receipts={}
  for member in members:
   stem=Path(member).stem;receipt=E/('ACTUAL-'+stem+'-SNAPSHOT-CAPTURE-RESULT.json');result=captured(receipt);expected=producer['actual_observed_tuple'][member];copy=result['copied']
   assert result['status']=='ACTUAL_EXCLUSIVE_PAYLOAD_SNAPSHOT_ONLY'and copy==dict(path=str(E/'runtime-inputs'/Path(member).name),sha256=expected['sha256'],size=expected['size'],mode=33188)
   assert result['source']['sha256']==copy['sha256']and result['copied_identity']['st_nlink']==1 and result['copied_identity']['st_mode']==33188
   copies[member]=copy;receipts[member]=ref(receipt)
  d=load(E/'TWO-RECORD-BASE-PATCH-INPUTS.PENDING.json');d.update(status='ACCEPTED_ACTUAL_TWO_SNAPSHOTS_PATCH_INPUTS_ONLY',new_runtime_tuple=copies,matched_artifact_acceptance={'sdk':accepted,'snapshot_captures':receipts});save(E/'TWO-RECORD-BASE-PATCH-INPUTS.ACTUAL.json',d)
  print(json.dumps(dict(status='PASS_TWO_ACTUAL_SNAPSHOTS_BOUND_NO_STAGE',inputs=ref(E/'TWO-RECORD-BASE-PATCH-INPUTS.ACTUAL.json'))));return
 result=captured(E/'ACTUAL-TWO-RECORD-PATCH-CAPTURE-RESULT.json');assert result['status']=='PASS_TWO_SMP_MCCTRL_RECORD_PATCH_ONLY_NO_NATIVE'and result['actual_changed_members']==members and result['all_other_final_members_identical']is True and result['all_original_record_order_metadata_preserved']is True
 inputs=load(E/'TWO-RECORD-BASE-PATCH-INPUTS.ACTUAL.json')
 for member,key in [('images/mckernel.img','unchanged_image_sha256'),('bin/native-boot','unchanged_helper_sha256'),('bin/mcexec','unchanged_launcher_sha256')]:assert result['final_map'][member]['sha256']==inputs[key]
 assert result['final_map']['modules/ihk.ko']['sha256']==producer['expected_unchanged_ihk']['sha256']
 gzip=result['patched_gzip'];cpio=result['patched_cpio'];assert gzip['path']==str(E/'shared-begin-cleanup-base-1.cpio.gz')and cpio['path']==str(E/'shared-begin-cleanup-base-1.cpio')
 for n in ['235','227']:
  c=E/('case-'+n);m=load(c/'STRICT-NATIVE-MANIFEST.SDK-BOUND.json');m['artifacts']['initramfs']=gzip;m['artifacts']['root_base']=gzip;m['staging']['base_initramfs']=gzip;save(c/'STRICT-NATIVE-MANIFEST.BASE-BOUND.json',m)
  data=load(c/'CASE-DATA.SCHEMA2-PENDING.json');data.update(status='ACCEPTED_ACTUAL_TWO_MODULE_BASE_NO_NATIVE_RELEASE',actual_patched_base=dict(cpio=cpio,gzip=gzip,receipt=ref(E/'ACTUAL-TWO-RECORD-BASE-PATCH-1.json')));data['producer']=ref(E/'PRODUCER-TWO-MODULES.ACTUAL.json');data['fresh_authorities']['matched_artifact_acceptance']={'sdk':accepted,'launcher':producer['launcher_acceptance']};save(c/'CASE-DATA.BASE-BOUND.json',data)
  argv=load(c/'OVERLAY-ARGV.PENDING.json')
  for flag,value in [('--base-sha256',gzip['sha256']),('--base-size',str(gzip['size'])),('--base-cpio-sha256',cpio['sha256']),('--base-cpio-size',str(cpio['size']))]:argv[argv.index(flag)+1]=value
  assert all(x is not None for x in argv);save(c/'OVERLAY-ARGV.ACTUAL.json',argv);save(c/'STRICT-CONSUMER-ARGV.ACTUAL.json',load(c/'STRICT-CONSUMER-ARGV.SCHEMA2-PENDING.json'))
 print(json.dumps(dict(status='PASS_ACTUAL_TWO_RECORD_BASE_BOUND_FOR_FRESH235_227_NO_NATIVE_RELEASE',patched_base=cpio)))
if __name__=='__main__':main()
