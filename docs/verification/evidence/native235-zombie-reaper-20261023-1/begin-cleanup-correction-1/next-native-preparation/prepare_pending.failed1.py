"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare finite source/data successors only. No snapshot, archive, root or native execution.
"""
from pathlib import Path
import ast,copy,hashlib,json,uuid
E=Path(__file__).resolve().parent
N=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1')
OLD=N/'zombie-sdk-native-successor-1'
F=N/'begin-cleanup-native-successor-1'
R=N/'native-runtime-ready-1'
SDK=Path('/home/holden/mckernel-work/host-preparation/native235-begin-cleanup-sdk-successor-20261023-2')
IDENTITY='db7f2ac4ddc023874ddf6b2b8de2c86c41bbf6efb601f33d4d0f501aa1957598'
MEMBERS=['modules/ihk-smp-x86_64.ko','modules/mcctrl.ko']
def load(p):return json.loads(p.read_text())
def ref(p):b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def save(p,d):
 p.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
 with p.open('x')as f:json.dump(d,f,sort_keys=True,indent=2);f.write('\n')
def src(p,s):ast.parse(s);p.write_text(s)
def rewrite(d):return json.loads(json.dumps(d).replace(str(OLD),str(F)).replace('shared-zombie-sdk-base-1','shared-begin-cleanup-base-1').replace('zombie-native','begin-cleanup-native'))
assert not F.exists();F.mkdir(mode=0o700);(F/'runtime-inputs').mkdir(mode=0o700)
assert load(SDK/'preparation.json')['source_candidate_sha']==IDENTITY
request=load(SDK/'REQUEST.TEMPLATE.PENDING-LIVE-IDENTITIES.json')
binder=OLD/'bind_actual_v3_case_data.py';assert ref(binder)['sha256']=='1bd397b832ae076e9617bed79bd4d8a70bc34bfbf37be1eee1896acdc8d0569c'
(F/binder.name).write_bytes(binder.read_bytes())
patch=load(OLD/'ACTUAL-ONE-RECORD-BASE-PATCH-1.json')
oldmanifest=load(OLD/'case-235/ACTUAL-V3-NATIVE235-MANIFEST.json')
ihk=next(m for m in oldmanifest['modules']if Path(m['path']).name=='ihk.ko')
producer={'scope':__doc__.splitlines()[0],'status':'PENDING_ACTUAL_ACCEPTED_BEGIN_SDK_TUPLE','source_identity':IDENTITY,'sdk_build_nonce':request['nonce'],'planned_producer_directory':str(Path(request['candidate_root'])/'modules'),'sdk_actual_build_receipt':None,'sdk_independent_artifact_acceptance':None,'sdk_physical_retirement':None,'actual_observed_tuple':None,'modules':{k:{'actual_producer_descriptor':None,'actual_runtime_descriptor':None,'stable_fd_copy_receipt':None,'planned_runtime_snapshot':str(F/'runtime-inputs'/Path(k).name)}for k in MEMBERS},'reused_accepted_ihk':ihk,'expected_unchanged_ihk':ihk,'launcher_acceptance':load(OLD/'PRODUCER-ONE-MODULES.PENDING.json')['launcher_acceptance'],'native_acceptance':False,'execution_release':None}
save(F/'PRODUCER-TWO-MODULES.PENDING.json',producer)
inputs=load(OLD/'ONE-RECORD-BASE-PATCH-INPUTS.ACTUAL.json')
inputs.update(status='PENDING_ACTUAL_ACCEPTED_SMP_MCCTRL_SNAPSHOTS',input_cpio=patch['patched_cpio'],input_receipt=ref(OLD/'ACTUAL-ONE-RECORD-BASE-PATCH-1.json'),changed_record_allowlist=MEMBERS,old_record_sha256={k:patch['final_map'][k]['sha256']for k in MEMBERS},new_runtime_tuple={k:None for k in MEMBERS},matched_artifact_acceptance=None,patched_cpio=str(F/'shared-begin-cleanup-base-1.cpio'),patched_gzip=str(F/'shared-begin-cleanup-base-1.cpio.gz'),patch_receipt=str(F/'ACTUAL-TWO-RECORD-BASE-PATCH-1.json'),actual_patched_cpio=None,actual_patched_gzip=None)
save(F/'TWO-RECORD-BASE-PATCH-INPUTS.PENDING.json',inputs)
argv=load(OLD/'ONE-RECORD-PATCH-ARGV.ARTIFACT-BOUND.json');pi=argv.index('/usr/bin/python3');ci=argv.index('-c',pi+1)+1
before=argv[ci];assert before.count("allowed={'modules/mcctrl.ko'}")==1
argv[ci]=before.replace("allowed={'modules/mcctrl.ko'}","allowed={'modules/ihk-smp-x86_64.ko','modules/mcctrl.ko'}").replace('PASS_ONE_MCCTRL_RECORD_PATCH_ONLY_NO_NATIVE','PASS_TWO_SMP_MCCTRL_RECORD_PATCH_ONLY_NO_NATIVE');ast.parse(argv[ci]);argv[ci+1]=str(F/'TWO-RECORD-BASE-PATCH-INPUTS.ACTUAL.json')
save(F/'TWO-RECORD-PATCH-ARGV.PENDING.json',argv)
caller=(OLD/'run-one-record-patch.ARTIFACT-BOUND.py').read_text().replace('ONE-RECORD','TWO-RECORD').replace('one-record','two-record').replace('one-module-record','two-module-record').replace('ARTIFACT-BOUND.json','ACTUAL.json')
src(F/'run-two-record-patch.py',caller)
snapshots=[];oldsnap=load(N/'fork-v3-matched-process-successor-1/FOUR-EXCLUSIVE-RUNTIME-SNAPSHOT-ARGV.PENDING.json')
for member in MEMBERS:
 row=copy.deepcopy(next(r for r in oldsnap if r['member']==member));a=row['fullargv'];pi=a.index('/usr/bin/python3');i=a.index('-c',pi+1)+1
 a[i+1]=None;a[i+2]=str(F/'runtime-inputs'/Path(member).name)
 for j in [3,4,5]:a[i+j]=None
 row.update(actual_copied_descriptor=None,execution_grant=None,status='PENDING_ACCEPTED_PRODUCER_DESCRIPTOR_REFUSES_EXECUTION')
 snapshots.append(row)
save(F/'TWO-EXCLUSIVE-RUNTIME-SNAPSHOT-ARGV.PENDING.json',snapshots)
cases=[]
for n in ['235','227']:
 C=F/('case-'+n);C.mkdir(mode=0o700);oldC=OLD/C.name
 nonce=uuid.uuid4().hex;short=Path('/home/holden/mckernel-work/scratch')/('n'+n+'b1');assert not short.exists();attempt=short/'p'/('attempt-'+nonce);qmp=attempt/'qmp.sock';assert len(str(qmp).encode())==93
 m=rewrite(load(oldC/('ACTUAL-V3-NATIVE'+n+'-MANIFEST.json')))
 for k in ['initramfs','root_base']:m['artifacts'][k]={'path':inputs['patched_gzip'],'sha256':None,'size':None,'mode':None}
 m['staging']['base_initramfs']=copy.deepcopy(m['artifacts']['root_base'])
 for k in ['derived_initramfs','overlay_manifest']:
  for field in ['sha256','size','mode']:m['staging'][k][field]=None
 m['modules']=[copy.deepcopy(ihk)if Path(r['path']).name=='ihk.ko'else dict(path=str(F/'runtime-inputs'/Path(r['path']).name),sha256=None,size=None,mode=33188)for r in m['modules']]
 assert m['payload']==load(oldC/('ACTUAL-V3-NATIVE'+n+'-MANIFEST.json'))['payload']
 save(C/'STRICT-NATIVE-MANIFEST.PENDING.json',m)
 overlay=rewrite(load(oldC/'OVERLAY-ARGV.ACTUAL.json'))
 for flag in ['--base-sha256','--base-size','--base-cpio-sha256','--base-cpio-size']:overlay[overlay.index(flag)+1]=None
 save(C/'OVERLAY-ARGV.PENDING.json',overlay)
 for name in ['run-overlay.ACTUAL.py','run-strict-consumer.ACTUAL.py']:src(C/name,(oldC/name).read_text())
 strict=rewrite(load(oldC/'STRICT-CONSUMER-ARGV.ACTUAL.json'));save(C/'STRICT-CONSUMER-ARGV.PENDING.json',strict)
 op=rewrite(load(oldC/'NATIVE-OPERATION.ACTUAL.json'))
 for flag,value in [('--attempt-parent',str(short/'p')),('--nonce',nonce),('--manifest',str(short/'m.json')),('--manifest-sha256',None)]:op['argv'][op['argv'].index(flag)+1]=value
 op.update(status='PENDING_ACCEPTED_BEGIN_SDK_AND_SEPARATE_NATIVE_RELEASE',actual_release=None,execution_review=None,fresh_root_admission=None)
 save(C/'NATIVE-OPERATION.PENDING.json',op)
 cap=rewrite(load(oldC/'NATIVE-CAPTURE-ARGV.ACTUAL.json'));cap[-1]=None;save(C/'NATIVE-CAPTURE-ARGV.PENDING.json',cap)
 metadata=rewrite(load(oldC/'METADATA-PUBLICATION-ARGV.ACTUAL.json'));metadata[-3:]=[str(C/('ACTUAL-V3-NATIVE'+n+'-MANIFEST.json')),str(short),None];save(C/'METADATA-PUBLICATION-ARGV.PENDING.json',metadata)
 data=rewrite(load(oldC/'CASE-DATA.PENDING.json'))
 data.update(status='PENDING_ACCEPTED_BEGIN_SDK_BASE_OVERLAY_AND_FRESH_NATIVE_AUTHORITY',nonce=nonce,short_root=str(short),owner_parent=str(short/'p'),attempt=str(attempt),qmp_socket=str(qmp),qmp_encoded_bytes=93,root_absent_at_preparation=True,actual_overlay=None,actual_manifest=None,actual_expected_qemu_argv=None,fresh_authorities={k:None for k in data['fresh_authorities']},producer=ref(F/'PRODUCER-TWO-MODULES.PENDING.json'))
 for key,name in [('strict_manifest','STRICT-NATIVE-MANIFEST.PENDING.json'),('overlay_argv','OVERLAY-ARGV.PENDING.json'),('ordinary_caller','run-overlay.ACTUAL.py'),('native_operation','NATIVE-OPERATION.PENDING.json'),('native_capture_argv','NATIVE-CAPTURE-ARGV.PENDING.json'),('metadata_publication_argv','METADATA-PUBLICATION-ARGV.PENDING.json')]:data[key]=ref(C/name)
 save(C/'CASE-DATA.PENDING.json',data);cases.append({k:data[k]for k in ['case','nonce','short_root','owner_parent','attempt','qmp_socket','qmp_encoded_bytes']})
profile={'cpu':6,'AS_bytes':536870912,'jobs':1,'CPU_seconds':30,'FSIZE_bytes':134217728,'NOFILE':256,'CORE':0,'NPROC':'inherited','outer_wall_seconds':35,'TERM_then_KILL_grace_seconds':3,'supervisor_wall_seconds':30,'stream_cap_each':8388608,'expected_stage_seconds_about':11}
ready={'scope':__doc__.splitlines()[0],'status':'SOURCE_DATA_READY_PENDING_ACTUAL_SDK_ACCEPTANCE_NO_STAGE_RELEASE','runtime_root':str(F),'source_identity':IDENTITY,'producer':ref(F/'PRODUCER-TWO-MODULES.PENDING.json'),'base_patch_inputs':ref(F/'TWO-RECORD-BASE-PATCH-INPUTS.PENDING.json'),'two_record_argv':ref(F/'TWO-RECORD-PATCH-ARGV.PENDING.json'),'stable_snapshots':ref(F/'TWO-EXCLUSIVE-RUNTIME-SNAPSHOT-ARGV.PENDING.json'),'binder':ref(F/binder.name),'case_bindings':cases,'changed_record_allowlist':MEMBERS,'expected_unchanged_ihk':ihk,'unchanged_image_sha256':inputs['unchanged_image_sha256'],'unchanged_helper_sha256':inputs['unchanged_helper_sha256'],'unchanged_launcher_sha256':inputs['unchanged_launcher_sha256'],'ordinary_profile':profile,'current_live_postjoin':None,'live_join_status':'REFUSE_NATIVE_RELEASE_UNTIL_NON_NULL_ACCEPTED_SDK_POSTJOIN_PLUS_ACTUAL_FRESH_ADMISSION','geometry':{'backing_bytes':110*2**30,'backing_inode':47468427,'UUID':'2a5768c8-718d-4914-bdc0-6b32c5a92a52','permanent_mutex':[27,4],'activation':'110GiB only; actual resize requires accepted coherent142 successor before any root consumer'},'SDK_actual_artifact_acceptance':None,'stage_execution_grant':None,'native_release':None,'effects':dict(snapshots=0,archives=0,overlays=0,compilers=0,root=0,Docker=0,guests=0),'failure_history':'8646 parent never reaped;58b3 real childACK+wait progressed but synchronous fullCLEANUP held finalFD ~5.6s beyond unchanged6s app deadline. BEGIN source+6actualbody tests independently accepted. Fresh changed-provider observation only; no unchanged replay.','next_sequence':['Accept actual SDK56d2 artifacts and physicalpostjoin','Bind real descriptors; require IHK bitidentity and exactlySMP+mcctrl changed; root grants ordinary stage','Stable2module snapshots→bind actual receipts→2record genericbasepatch→basebind','235overlay→unchangedstrict1bd397 binder→actual source-bound admission/metadata/manifest-derived guard→separate native release','After actual235 and positive physical retirement, separately227 and restoration matchedtuple'],'native_acceptance':False,'compute_C_retirement_credit':False}
save(E/'NEXT-NATIVE-READY.PENDING.json',ready);save(F/'NEXT-NATIVE-READY.PENDING.json',ready)
(E/'TWO-RECORD-WRAPPER-DELTA.patch').write_text(__import__('difflib').unified_diff(before.splitlines(True),argv[ci].splitlines(True),fromfile='accepted-one-record-inline',tofile='new-two-record-inline').__iter__().__next__() if False else ''.join(__import__('difflib').unified_diff(before.splitlines(True),argv[ci].splitlines(True),fromfile='accepted-one-record-inline',tofile='new-two-record-inline')))
print(json.dumps({'ready':ref(E/'NEXT-NATIVE-READY.PENDING.json'),'runtime_root':str(F),'cases':cases,'metadata_bytes':sum(p.stat().st_size for p in F.rglob('*')if p.is_file()),'effects':ready['effects']},indent=2))
