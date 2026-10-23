"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Bind accepted actual SDK descriptors to existing ordinary snapshot/patch templates; no stage.
"""
from pathlib import Path
import argparse,copy,hashlib,json,os
E=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/begin-cleanup-native-successor-2')
def load(p):return json.loads(p.read_text())
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def save(p,d):
 with p.open('x')as f:json.dump(d,f,sort_keys=True,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def main():
 p=argparse.ArgumentParser();p.add_argument('--acceptance',type=Path,required=True);p.add_argument('--acceptance-sha256',required=True);p.add_argument('--owner-receipt',type=Path,required=True);a=p.parse_args()
 assert ref(a.acceptance)['sha256']==a.acceptance_sha256
 accepted=load(a.acceptance);producer=load(E/'PRODUCER-TWO-MODULES.PENDING.json');owner=load(a.owner_receipt);driver=owner['driver_receipt']
 assert accepted['status']=='PASS'and accepted['physical_acceptance']is True and accepted['source_identity']==producer['source_identity']and accepted['nonce']==producer['sdk_build_nonce']
 assert accepted['owner_receipt_sha256']==ref(a.owner_receipt)['sha256']and owner['retired']is True and owner['terminal_container_retained']is False
 assert driver['status']=='BUILD_ARTIFACT_CHECKS_PASS'and driver['source_candidate_sha']==producer['source_identity']
 actual={}
 for name in ['ihk','ihk-smp-x86_64','mcctrl']:
  row=accepted['artifacts'][name+'.ko'];compiled=driver['artifacts'][name];assert row['sha256']==compiled['sha256']and row['bytes']==compiled['bytes']
  path=Path(producer['planned_producer_directory'])/(name+'.ko');assert row['path']==str(path)and path.is_file()and not path.is_symlink()
  actual['modules/'+name+'.ko']=dict(path=str(path),sha256=row['sha256'],size=row['bytes'],mode=path.stat().st_mode)
 ihk=producer['expected_unchanged_ihk'];assert actual['modules/ihk.ko']['sha256']==ihk['sha256']and actual['modules/ihk.ko']['size']==ihk['size'],'IHK changed: stop, needs coherent reviewed broader tuple'
 inputs=load(E/'TWO-RECORD-BASE-PATCH-INPUTS.PENDING.json');members=inputs['changed_record_allowlist'];assert all(actual[k]['sha256']!=inputs['old_record_sha256'][k]for k in members),'not exact reviewed two-record delta'
 producer.update(status='ACCEPTED_ACTUAL_SDK_TUPLE_PENDING_STABLE_SNAPSHOTS',sdk_independent_artifact_acceptance=ref(a.acceptance),sdk_physical_retirement=ref(a.acceptance),sdk_actual_build_receipt=ref(a.owner_receipt),actual_observed_tuple=actual)
 for k,row in producer['modules'].items():row['actual_producer_descriptor']=actual[k]
 save(E/'PRODUCER-TWO-MODULES.ACTUAL.json',producer)
 snapshots=load(E/'TWO-EXCLUSIVE-RUNTIME-SNAPSHOT-ARGV.PENDING.json')
 for row in snapshots:
  member=row['member'];d=actual[member];argv=row['fullargv'];pi=argv.index('/usr/bin/python3');i=argv.index('-c',pi+1)+1
  for offset,v in [(1,d['path']),(3,d['sha256']),(4,str(d['size'])),(5,str(d['mode']))]:argv[i+offset]=v
  assert all(v is not None for v in argv);save(E/('SNAPSHOT-'+Path(member).stem+'-ARGV.ACTUAL.json'),argv)
  row.update(status='ACTUAL_ACCEPTED_DESCRIPTOR_BOUND_NOT_EXECUTED',missing_actual_arguments=[],execution_grant=None,actual_producer_descriptor=d)
 save(E/'TWO-EXCLUSIVE-RUNTIME-SNAPSHOT-ARGV.ACTUAL.json',snapshots)
 save(E/'TWO-RECORD-PATCH-ARGV.ACTUAL.json',load(E/'TWO-RECORD-PATCH-ARGV.PENDING.json'))
 for n in ['235','227']:
  C=E/('case-'+n);m=load(C/'STRICT-NATIVE-MANIFEST.PENDING.json')
  for row in m['modules']:
   if Path(row['path']).name!='ihk.ko':
    d=actual['modules/'+Path(row['path']).name];row.update(sha256=d['sha256'],size=d['size'],mode=33188)
  save(C/'STRICT-NATIVE-MANIFEST.SDK-BOUND.json',m)
 print(json.dumps(dict(status='PASS_ACTUAL_ACCEPTED_TWO_RECORD_MODULE_DATA_BOUND_NO_STAGE',producer=ref(E/'PRODUCER-TWO-MODULES.ACTUAL.json'),actual_tuple=actual)))
if __name__=='__main__':main()
