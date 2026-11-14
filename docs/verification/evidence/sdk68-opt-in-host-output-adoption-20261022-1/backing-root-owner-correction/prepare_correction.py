from pathlib import Path
import copy,difflib,hashlib,json,os,resource
HERE=Path(__file__).resolve().parent
os.sched_setaffinity(0,{7});resource.setrlimit(resource.RLIMIT_AS,(512*2**20,512*2**20));resource.setrlimit(resource.RLIMIT_CPU,(30,30))
CANON=Path('/home/holden/mckernel/scripts/native_running_external_modules_owner.py');raw=CANON.read_bytes();assert hashlib.sha256(raw).hexdigest()=='4f530016e64e4c04db36d8e3f1d30c57366b72dfefec319617af4764cf5e31e9'
old=raw.decode();needle="meta.st_dev == actual['device'] and meta.st_uid == meta.st_gid == 1000 and";assert old.count(needle)==1
new=old.replace(needle,"meta.st_dev == actual['device'] and meta.st_uid == meta.st_gid == 0 and",1)
needle="'exact unchanged110GiB backing inode/size/owner required'";assert new.count(needle)==1
new=new.replace(needle,"'exact unchanged110GiB root-owned backing inode/size/owner required'",1)
source=HERE/'native_running_external_modules_owner.py';source.write_text(new)
def ref(p):
 p=Path(p);data=p.read_bytes();return dict(path=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
(HERE/'BACKING-ROOT-OWNER-ONLY.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile=str(CANON)+'@4f530',tofile=str(source))))
COMB=Path('/home/holden/mckernel-work/host-preparation/seven-check-closure-20261022-1/provider-opt-in-1/combined-host-output-opt-in-1')
cohort=json.loads((COMB/'CANONICAL-RUNTIME-SOURCE-COHORT.json').read_bytes());cohort['source_sha256']['scripts/native_running_external_modules_owner.py']=ref(source)['sha256']
for row in cohort['rows']:
 if row['relative']=='scripts/native_running_external_modules_owner.py':row['source']=ref(source)
cohort['status']='BACKING_ROOT_OWNER_SUCCESSOR11_CANONICAL_COHORT_NOT_INSTALLED';cohort['runtime_release']=None
(HERE/'CANONICAL-RUNTIME-SOURCE-COHORT.SUCCESSOR.json').write_text(json.dumps(cohort,indent=2)+'\n')
runtime=json.loads((COMB/'ACTUAL-CANONICAL-RUNTIME-INPUT-MAP.json').read_bytes());runtime['owner_script_sha256']=ref(source)['sha256'];runtime['release_required_fixed_values']['source_sha256']['scripts/native_running_external_modules_owner.py']=ref(source)['sha256']
assert runtime['owner_argv_shape'][:2]==['/usr/bin/sudo','-A'];runtime['owner_argv_shape']=runtime['owner_argv_shape'][2:]
runtime['owner_caller_correction']='Previously dispatcher-approved ordinaryUID1000owner shape; preserve old244a map. Docker/historicalobserver sudo-A internal unchanged.'
runtime['status']='BACKING_ROOT_OWNER_CANONICAL_RUNTIME_SUCCESSOR_NOT_INSTALLED_NOT_RELEASED'
(HERE/'ACTUAL-CANONICAL-RUNTIME-INPUT-MAP.SUCCESSOR.json').write_text(json.dumps(runtime,indent=2)+'\n')
install=dict(status='NOT_INSTALLED_NOT_RELEASED',scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',rows=[dict(canonical_path=str(CANON),required_preimage_sha256='4f530016e64e4c04db36d8e3f1d30c57366b72dfefec319617af4764cf5e31e9',postimage=ref(source))],unchanged_canonical_driver_sha256='e55c07e286d3f7d712c5f8e9131d37a9ab60b16e166151326672a59f7b88531e',unchanged_preparation_sha256='05ac2a27042b02fa5f89f74c346dabe7cca4df9616cb4eb2243bd619b3711baf',actual_installation=None,actual_source_review=None,actual_Git_fetched_proof=None)
(HERE/'CANONICAL-OWNER-INSTALL-DELTA.json').write_text(json.dumps(install,indent=2)+'\n')
OLD=Path('/home/holden/mckernel-work/host-preparation/m05-sdk68-canonical-host-output-request-20261022-1')
request=json.loads((OLD/'REQUEST.PAYLOAD-TEMPLATE.json').read_bytes());(HERE/'REQUEST.PAYLOAD-TEMPLATE.SUCCESSOR.json').write_text(json.dumps(request,indent=2)+'\n')
release=json.loads((OLD/'RELEASE.PAYLOAD-TEMPLATE.json').read_bytes());release['source_sha256']['scripts/native_running_external_modules_owner.py']=ref(source)['sha256'];(HERE/'RELEASE.PAYLOAD-TEMPLATE.SUCCESSOR.json').write_text(json.dumps(release,indent=2)+'\n')
print(json.dumps(dict(status='SOURCE_PREPARED_NO_EXECUTION',source=ref(source),source_delta='backinguidgid1000to0androot-owneddiagnostic only',canonical_edits=0)))
