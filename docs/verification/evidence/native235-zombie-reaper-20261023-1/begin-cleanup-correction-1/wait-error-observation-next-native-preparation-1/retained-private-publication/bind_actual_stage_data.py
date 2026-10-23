"""Functional OS only; no security testing. Bind actual completed snapshot/base captures; no stage/native run."""
from pathlib import Path
import argparse,hashlib,json,os
E=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text())
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def save(p,d):
 with p.open('x')as f:json.dump(d,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
def captured(p):
 r=load(p);assert r['status']=='COMPLETED'and r['cleanup_complete']is True and r['wait_status']=={'kind':'exited','code':0}and r['descendants']==[]
 for label in ['stdout','stderr']:
  s=r['streams'][label];assert s['eof']is True and s['truncated']is False and s['discarded_observed_bytes']==0;q=s['artifact'];raw=Path(q['path']).read_bytes();assert len(raw)==q['size']and hashlib.sha256(raw).hexdigest()==q['sha256'];assert label!='stderr'or not raw
 return json.loads(Path(r['streams']['stdout']['artifact']['path']).read_text())
def checked(reference):
 p=Path(reference['path']);assert ref(p)==reference;return load(p)
def main():
 parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['sdk','snapshot','base']);a=parser.parse_args();C=E/'case-235'
 if a.phase=='sdk':
  release=load(E/'ACTUAL-SDK-RELEASE.json');acceptance=release['independent_acceptance'];accepted=checked(acceptance);assert accepted['status']=='PASS'and accepted['physical_acceptance']is True and accepted['source_identity']=='6a3314024fba61f72ad633508b65dd60d79da4db3c5bd113ae35118cb60482a5'
  ownerref=release['owner_receipt'];assert ownerref==accepted['owner_receipt'];owner=checked(ownerref);driver=owner['driver_receipt'];assert driver['status']=='BUILD_ARTIFACT_CHECKS_PASS'and driver['source_candidate_sha']=='6a3314024fba61f72ad633508b65dd60d79da4db3c5bd113ae35118cb60482a5'
  oldmanifest=load(C/'STRICT-NATIVE-MANIFEST.PENDING.json');oldmodules=oldmanifest['modules'];producer={}
  for key in ['ihk','ihk-smp-x86_64','mcctrl']:
   r=driver['artifacts'][key];p=Path(accepted['artifacts'][key+'.ko']['path']);ar=accepted['artifacts'][key+'.ko'];assert ar['sha256']==r['sha256']and ar['bytes']==r['bytes'];producer[key]=dict(path=str(p),sha256=r['sha256'],size=r['bytes'],mode=33188)
  for key,index in [('ihk',0),('ihk-smp-x86_64',1)]:assert producer[key]['sha256']==oldmodules[index]['sha256']and producer[key]['size']==oldmodules[index]['size']
  mc=producer['mcctrl'];assert mc['sha256']!='20fbc505e569f3b50529993896c4e043720272c776fb361391ddce44a70b8d2e'and mc['size']>0
  assert mc['path']=='/home/holden/mckernel-work/host-preparation/native-running-modules-host-output/native-running-modules-candidate-56bc171c4a724f9b81060ae6713e9a1c/modules/mcctrl.ko'
  runtime=dict(mc,path=str(E/'runtime-inputs/mcctrl.ko'));manifest=oldmanifest;manifest['modules'][-1]=runtime;assert manifest['cleanup_profile']['modules']is None;manifest['cleanup_profile']['modules']=manifest['modules'];save(C/'STRICT-NATIVE-MANIFEST.SDK-BOUND.json',manifest)
  prod=dict(status='ACTUAL_ACCEPTED_WAIT_OBSERVER_MCCTRL_ONLY',sdk_independent_artifact_acceptance=acceptance,sdk_actual_build_receipt=ownerref,actual_observed_tuple=producer,actual_runtime_tuple=manifest['modules']);save(E/'PRODUCER-ONE-MODULES.ACTUAL.json',prod)
  data=load(C/'CASE-DATA.PENDING.json');data['producer']=ref(E/'PRODUCER-ONE-MODULES.ACTUAL.json');data['fresh_authorities']['matched_artifact_acceptance']={'sdk':acceptance};save(C/'CASE-DATA.SDK-BOUND.json',data)
  argv=load(E/'SNAPSHOT-ARGV.PENDING.json');i=argv.index('-c')+1;assert argv[i+1]==mc['path']and argv[i+3]is None and argv[i+4]is None;argv[i+3]=mc['sha256'];argv[i+4]=str(mc['size']);assert all(v is not None for v in argv);save(E/'SNAPSHOT-ARGV.ACTUAL.json',argv);print(json.dumps(dict(status='PASS_ACTUAL_SDK_SNAPSHOT_COMMAND_BOUND',producer=ref(E/'PRODUCER-ONE-MODULES.ACTUAL.json'))));return
 producer=load(E/'PRODUCER-ONE-MODULES.ACTUAL.json');acceptance=producer['sdk_independent_artifact_acceptance'];accepted=checked(acceptance);assert accepted['status']=='PASS'and accepted['physical_acceptance']is True
 if a.phase=='snapshot':
  result=captured(E/'ACTUAL-MCCTRL-SNAPSHOT-CAPTURE-RESULT.json');assert result['status']=='ACTUAL_EXCLUSIVE_PAYLOAD_SNAPSHOT_ONLY';copy=result['copied'];assert copy==producer['actual_runtime_tuple'][-1]
  assert result['source']['sha256']==copy['sha256']and result['copied_identity']['st_nlink']==1 and result['copied_identity']['st_mode']==33188
  d=load(E/'ONE-RECORD-BASE-PATCH-INPUTS.PENDING.json');d.update(status='ACCEPTED_ACTUAL_MCCTRL_SNAPSHOT_BASE_PATCH_INPUTS_ONLY',new_runtime_tuple={'modules/mcctrl.ko':copy},matched_artifact_acceptance={'sdk':acceptance,'snapshot_capture':ref(E/'ACTUAL-MCCTRL-SNAPSHOT-CAPTURE-RESULT.json')});save(E/'ONE-RECORD-BASE-PATCH-INPUTS.ACTUAL.json',d);print(json.dumps(dict(status='PASS_ACTUAL_SNAPSHOT_BOUND_NO_STAGE',inputs=ref(E/'ONE-RECORD-BASE-PATCH-INPUTS.ACTUAL.json'))));return
 result=captured(E/'ACTUAL-ONE-RECORD-PATCH-CAPTURE-RESULT.json');assert result['status']=='PASS_ONE_MCCTRL_RECORD_PATCH_ONLY_NO_NATIVE'and result['actual_changed_members']==['modules/mcctrl.ko']and result['all_other_final_members_identical']is True and result['all_original_record_order_metadata_preserved']is True
 assert result['final_map']['modules/ihk-smp-x86_64.ko']['sha256']=='1053fc9f588f8e82d7b8792d605cf49cc69792f5fdbc243a4d0fc0fa2a8c1209'
 assert result['final_map']['images/mckernel.img']['sha256']=='10972f87277e8429e2badd238d3ac53e451b8a2351a8ebf013941e1dfb95e1e2'and result['final_map']['bin/native-boot']['sha256']=='cccbf269ce80d92a4c16256f5189a65bc7cbc83044d70f752e4910a92c2b45ec'and result['final_map']['bin/mcexec']['sha256']=='dca0250159ce04a272a72dd1217213a4b6e0f21ec8c21da211eede250c451954'
 gzip=result['patched_gzip'];cpio=result['patched_cpio'];assert gzip['path']==str(E/'shared-wait-observer-base-1.cpio.gz')and cpio['path']==str(E/'shared-wait-observer-base-1.cpio')
 m=load(C/'STRICT-NATIVE-MANIFEST.SDK-BOUND.json');m['artifacts']['initramfs']=gzip;m['artifacts']['root_base']=gzip;m['staging']['base_initramfs']=gzip;save(C/'STRICT-NATIVE-MANIFEST.BASE-BOUND.json',m)
 data=load(C/'CASE-DATA.SDK-BOUND.json');data.update(status='ACCEPTED_ACTUAL_MCCTRL_SHARED_BASE_BOUND_NO_NATIVE_RELEASE',actual_patched_base=dict(cpio=cpio,gzip=gzip,receipt=ref(E/'ACTUAL-ONE-RECORD-BASE-PATCH-1.json')));save(C/'CASE-DATA.BASE-BOUND.json',data)
 argv=load(C/'OVERLAY-ARGV.PENDING.json')
 for flag,value in [('--base-sha256',gzip['sha256']),('--base-size',str(gzip['size'])),('--base-cpio-sha256',cpio['sha256']),('--base-cpio-size',str(cpio['size']))]:argv[argv.index(flag)+1]=value
 assert all(x is not None for x in argv);save(C/'OVERLAY-ARGV.ACTUAL.json',argv);print(json.dumps(dict(status='PASS_ACTUAL_SHARED_BASE_BOUND_NO_NATIVE_RELEASE',patched_base=cpio)))
if __name__=='__main__':main()
