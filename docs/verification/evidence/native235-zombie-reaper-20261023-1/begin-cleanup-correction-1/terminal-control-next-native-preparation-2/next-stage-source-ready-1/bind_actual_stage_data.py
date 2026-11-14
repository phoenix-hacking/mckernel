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
 parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['sdk','snapshot','base']);phase=parser.parse_args().phase
 release=load(E/'ACTUAL-SDK5-RELEASE.PENDING.json');assert release['source_identity']=='ba0e1be79e6cd6b06fe0b7cbd1c2c3c689e86579439e13deea9b3f3776069120';acceptance=release['independent_acceptance'];assert acceptance is not None;accepted=checked(acceptance);assert accepted['status']=='PASS'and accepted['physical_acceptance']is True and accepted['source_identity']==release['source_identity'];reads=checked(accepted['actual_reads']);assert reads['evidence']['owner_receipt']==release['owner_receipt']==accepted['owner_receipt'];owner=checked(release['owner_receipt']);driver=owner['driver_receipt'];assert driver['status']=='BUILD_ARTIFACT_CHECKS_PASS'and driver['source_candidate_sha']==release['source_identity']
 for key,digest in {'smp_application.rs':'f5c56d83a13f10a712a4555849f52078c2d410254080150d34408011daf527a5','smp_service.rs':'ffefabadb349f55ecc4d474f6463e73e0c6b432aea6c41eb973a91f115ded0f7','current_fork_control.rs':'81228204d50bd5e95bcad7671d4c6bb272ef9c516d0163b2b39a0f6a5c23a126','mcctrl_vm.rs':'ba957d7349a45cda47ba135dd265885516cf40c00872658ca8309a98aa8d19c1','mcctrl_process.rs':'8bf30cd8ae79cc778bd91816f30aaf7a37ccc2aab59822ca2a03587426a212b8'}.items():assert driver['source_sha256'][key]==digest
 for name,digest in {'ihk.ko':'daced2910f2391f15f1963399838c5089ef7ac6be8f6614db88ff8443c48900c','mcctrl.ko':'06e8b9b571f21b41821aa03a32ebf4ae20ae19cf4b110c3af2c81b491b92ef86','ihk-smp-x86_64.ko':'2eb3e8e6d7e43f55ca262cb455212e205831e26980f10d4ce8ef99556fd2269d'}.items():assert accepted['artifacts'][name]['sha256']==digest
 if phase=='sdk':
  m=load(E/'case-235/STRICT-NATIVE-MANIFEST.SOURCE-BOUND.json');save(E/'PRODUCER-TWO-MODULES.ACTUAL.json',dict(status='ACTUAL_ACCEPTED_SDK5_SMP_ONLY_SUCCESSOR',sdk_independent_artifact_acceptance=acceptance,sdk_actual_build_receipt=release['owner_receipt'],actual_runtime_tuple=m['modules']));print('PASS acceptedSDK5 source/tuple bound');return
 if phase=='snapshot':
  r=captured(E/'ACTUAL-SMP-SNAPSHOT-CAPTURE-RESULT.json');d=load(E/'SMP-ONE-RECORD-PATCH-INPUTS.SOURCE-BOUND.json');assert r['status']=='ACTUAL_EXCLUSIVE_PAYLOAD_SNAPSHOT_ONLY'and r['copied']==d['new_runtime_tuple']['modules/ihk-smp-x86_64.ko'];assert r['copied_identity']['st_mode']==33188 and r['copied_identity']['st_nlink']==1;d['matched_artifact_acceptance']=dict(sdk=acceptance,snapshot_capture=ref(E/'ACTUAL-SMP-SNAPSHOT-CAPTURE-RESULT.json'));save(E/'SMP-ONE-RECORD-PATCH-INPUTS.ACTUAL.json',d);print('PASS actualSMPsnapshot bound');return
 r=captured(E/'ACTUAL-SMP-ONE-RECORD-PATCH-CAPTURE-RESULT.json');assert r['status']=='PASS_ONE_SMP_RECORD_PATCH_ONLY_NO_NATIVE'and r['actual_changed_members']==['modules/ihk-smp-x86_64.ko']and r['all_other_final_members_identical']and r['all_original_record_order_metadata_preserved'];final=r['final_map']
 for key,digest in {'images/mckernel.img':'10972f87277e8429e2badd238d3ac53e451b8a2351a8ebf013941e1dfb95e1e2','bin/native-boot':'cccbf269ce80d92a4c16256f5189a65bc7cbc83044d70f752e4910a92c2b45ec','bin/mcexec':'dca0250159ce04a272a72dd1217213a4b6e0f21ec8c21da211eede250c451954','modules/ihk.ko':'daced2910f2391f15f1963399838c5089ef7ac6be8f6614db88ff8443c48900c','modules/mcctrl.ko':'06e8b9b571f21b41821aa03a32ebf4ae20ae19cf4b110c3af2c81b491b92ef86','modules/ihk-smp-x86_64.ko':'2eb3e8e6d7e43f55ca262cb455212e205831e26980f10d4ce8ef99556fd2269d'}.items():assert final[key]['sha256']==digest
 for case in ['235','227']:
  C=E/('case-'+case);m=load(C/'STRICT-NATIVE-MANIFEST.SOURCE-BOUND.json');m['artifacts']['initramfs']=r['patched_gzip'];m['artifacts']['root_base']=r['patched_gzip'];m['staging']['base_initramfs']=r['patched_gzip'];save(C/'STRICT-NATIVE-MANIFEST.BASE-BOUND.json',m);data=load(C/'CASE-DATA.SOURCE-BOUND.json');data['fresh_authorities']['matched_artifact_acceptance']=dict(sdk=acceptance);data['actual_patched_base']=dict(cpio=r['patched_cpio'],gzip=r['patched_gzip'],receipt=ref(E/'ACTUAL-SDK5-SMP-ONE-RECORD-BASE-PATCH-1.json'));save(C/'CASE-DATA.BASE-BOUND.json',data);argv=load(C/'OVERLAY-ARGV.PENDING.json')
  for flag,value in [('--base-sha256',r['patched_gzip']['sha256']),('--base-size',str(r['patched_gzip']['size'])),('--base-cpio-sha256',r['patched_cpio']['sha256']),('--base-cpio-size',str(r['patched_cpio']['size']))]:argv[argv.index(flag)+1]=value
  assert all(x is not None for x in argv);save(C/'OVERLAY-ARGV.ACTUAL.json',argv)
 print('PASS SMPonlyactualbase bound original235/227')
if __name__=='__main__':main()
