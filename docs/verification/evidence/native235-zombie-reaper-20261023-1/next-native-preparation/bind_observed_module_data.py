"""Functional OS only; no security testing. Bind observed module build facts to pending metadata only."""
from pathlib import Path
import ast,copy,hashlib,json,os
E=Path(__file__).resolve().parent;H=Path('/home/holden/mckernel-work/host-preparation/native235-zombie-sdk-successor-20261023-1/next-native-preparation');O=H/'future-runtime-metadata';V=H/'mcctrl-only-observed-1';V.mkdir(mode=0o700);S=V/'future-runtime-metadata';S.mkdir(mode=0o700)
N=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1');P=N/'fork-v3-matched-process-successor-1';F=N/'zombie-sdk-native-successor-1'
R=Path('/home/holden/mckernel/docs/verification/evidence/native235-zombie-reaper-20261023-1/sdk-build-release/actual-build/owner-receipt.json');receipt=json.loads(R.read_text());driver=receipt['driver_receipt'];assert driver['status']=='BUILD_ARTIFACT_CHECKS_PASS'and driver['source_candidate_sha']=='15334501928a36becca541c8cd8beeead3da0acd8737f955abaf98f34cece515'
def load(p):return json.loads(Path(p).read_text())
def ref(p):p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def save(p,v):p.write_text(json.dumps(v,sort_keys=True,indent=2)+'\n')
def rename(s):return s.replace('THREE-','ONE-').replace('three-record','one-record').replace('three-module-record','one-module-record')
for p in O.rglob('*'):
 if p.is_file():
  q=S/rename(str(p.relative_to(O)));q.parent.mkdir(mode=0o700,parents=True,exist_ok=True);q.write_text(rename(p.read_text()) if p.name!='bind_actual_v3_case_data.py' else p.read_text())
M=Path('/home/holden/mckernel-work/host-preparation/native-running-modules-host-output/native-running-modules-candidate-9850d940ac3649a6b8e7ebebf3251853/modules');observed={}
for k in ['ihk','ihk-smp-x86_64','mcctrl']:
 a=driver['artifacts'][k];path=M/(k+'.ko');observed['modules/'+k+'.ko']={'path':str(path),'sha256':a['sha256'],'size':a['bytes'],'mode':path.stat().st_mode}
oldmanifest=load(P/'case-235/ACTUAL-V3-NATIVE235-MANIFEST.json');oldmods={Path(x['path']).name:x for x in oldmanifest['modules']}
assert all(observed['modules/'+k]['sha256']==oldmods[k]['sha256']and observed['modules/'+k]['size']==oldmods[k]['size']for k in ['ihk.ko','ihk-smp-x86_64.ko'])
mc=observed['modules/mcctrl.ko'];assert mc['sha256']=='d8d8c4a0b004f64d2c7aceb98c2bed337996bc955a419d1ebfa51f184451b9bc'and mc['size']==2656112
producerpath=S/'PRODUCER-ONE-MODULES.PENDING.json';producer=load(producerpath);producer['status']='OBSERVED_ACTUAL_SDK3_BUILD_PENDING_INDEPENDENT_ARTIFACT_PHYSICAL_ACCEPTANCE';producer['sdk_actual_build_receipt']=ref(R);producer['actual_observed_tuple']=observed;producer['changed_runtime_snapshots']=['modules/mcctrl.ko'];producer['reused_accepted_runtime_modules']={k:oldmods[k]for k in ['ihk.ko','ihk-smp-x86_64.ko']}
for k,row in producer['modules'].items():
 row['actual_producer_descriptor']=observed[k]
 if k!='modules/mcctrl.ko':row.update(planned_runtime_snapshot=oldmods[Path(k).name]['path'],actual_runtime_descriptor=oldmods[Path(k).name],stable_fd_copy_receipt='REUSE_ACCEPTED_IMMUTABLE_RUNTIME_SNAPSHOT_NO_NEW_COPY')
save(producerpath,producer)
dpath=S/'ONE-RECORD-BASE-PATCH-INPUTS.PENDING.json';D=load(dpath);D['status']='OBSERVED_MCCTRL_ONLY_NEW_BYTES_PENDING_INDEPENDENT_ACCEPTANCE_AND_SNAPSHOT';D['changed_record_allowlist']=['modules/mcctrl.ko'];D['old_record_sha256']={'modules/mcctrl.ko':D['old_record_sha256']['modules/mcctrl.ko']};D['new_runtime_tuple']={'modules/mcctrl.ko':None};save(dpath,D)
argvpath=S/'ONE-RECORD-PATCH-ARGV.PENDING.json';argv=load(argvpath);ci=argv.index('-c')+1;code=argv[ci];old="allowed={'modules/ihk.ko','modules/ihk-smp-x86_64.ko','modules/mcctrl.ko'}";assert code.count(old)==1;code=code.replace(old,"allowed={'modules/mcctrl.ko'}").replace('PASS_THREE_MODULE_RECORD_PATCH_ONLY_NO_NATIVE','PASS_ONE_MCCTRL_RECORD_PATCH_ONLY_NO_NATIVE');ast.parse(code);argv[ci]=code;save(argvpath,argv)
spath=S/'ONE-EXCLUSIVE-RUNTIME-SNAPSHOT-ARGV.PENDING.json';snap=next(r for r in load(spath)if r['member']=='modules/mcctrl.ko');sargv=snap['fullargv'];si=sargv.index('-c')+1
for offset,value in [(1,mc['path']),(3,mc['sha256']),(4,str(mc['size'])),(5,str(mc['mode']))]:sargv[si+offset]=value
snap.update(status='OBSERVED_ACTUAL_DESCRIPTOR_NOT_RELEASED',missing_actual_arguments=[],observed_descriptor=mc,execution_grant=None);save(spath,[snap])
for n in ['235','227']:
 C=S/('case-'+n);m=load(C/'STRICT-NATIVE-MANIFEST.PENDING.json')
 m['modules']=[copy.deepcopy(oldmods[k])if k!='mcctrl.ko'else dict(path=str(F/'runtime-inputs/mcctrl.ko'),sha256=mc['sha256'],size=mc['size'],mode=33188)for k in ['ihk.ko','ihk-smp-x86_64.ko','mcctrl.ko']];save(C/'STRICT-NATIVE-MANIFEST.PENDING.json',m)
 data=load(C/'CASE-DATA.PENDING.json');data['status']='OBSERVED_REPAIRED_SDK_TUPLE_PENDING_INDEPENDENT_ACCEPTANCE_BASE_OVERLAY_AND_FRESH_NATIVE_RELEASE';data['producer']['path']=str(F/producerpath.name);data['producer'].update(sha256=ref(producerpath)['sha256'],bytes=producerpath.stat().st_size);data['strict_manifest'].update(sha256=ref(C/'STRICT-NATIVE-MANIFEST.PENDING.json')['sha256'],bytes=(C/'STRICT-NATIVE-MANIFEST.PENDING.json').stat().st_size);save(C/'CASE-DATA.PENDING.json',data)
ready=load(S/'NEXT-NATIVE-READY.PENDING.json');ready.update(status='OBSERVED_NEW_MCCTRL_ONLY_TUPLE_PENDING_INDEPENDENT_ACCEPTANCE_AND_ROOT_GRANT',owned_host_preparation=str(V),changed_record_allowlist=['modules/mcctrl.ko'],actual_build_receipt_observed=ref(R),actual_observed_tuple=observed,new_snapshot_bytes=2656112,reused_accepted_unchanged_runtime_modules={k:oldmods[k]for k in ['ihk.ko','ihk-smp-x86_64.ko']})
for key,name in [('producer',producerpath.name),('base_patch_inputs',dpath.name),('base_patch_fullargv',argvpath.name),('snapshots',spath.name)]:row=ref(S/name);row['path']=str(F/name);ready[key]=row
ready['cases']=[dict(ref(S/('case-'+n)/'CASE-DATA.PENDING.json'),path=str(F/('case-'+n)/'CASE-DATA.PENDING.json'))for n in ['235','227']];save(S/'NEXT-NATIVE-READY.PENDING.json',ready)
files=[dict(relative=str(p.relative_to(S)),source=ref(p),future_path=str(F/p.relative_to(S)))for p in sorted(S.rglob('*'))if p.is_file()];inventory={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'OBSERVED_MODULE_FACTS_HOST_METADATA_ONLY_NOT_STAGED','source_root':str(S),'future_root':str(F),'files':files,'total_bytes':sum(r['source']['bytes']for r in files),'file_count':len(files),'effects':ready['effects'],'preserved_preliminary_revision':str(O),'supersedes_pending_source_inventory_only':ref(H/'METADATA-INVENTORY.json')};save(V/'METADATA-INVENTORY.json',inventory);save(E/'METADATA-INVENTORY.MCCTRL-ONLY-OBSERVED.json',inventory);save(E/'NEXT-NATIVE-READY.MCCTRL-ONLY-OBSERVED.json',ready)
print(json.dumps({'inventory':ref(E/'METADATA-INVENTORY.MCCTRL-ONLY-OBSERVED.json'),'ready':ref(E/'NEXT-NATIVE-READY.MCCTRL-ONLY-OBSERVED.json'),'metadata_files':len(files),'metadata_bytes':inventory['total_bytes'],'new_snapshot_bytes':2656112,'effects':ready['effects']},indent=2))
