"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One immutable artifact retention archive; reads originals and verifies archive bytes.
No compiler, SDK, Docker, native, cleanup, permissions or cache changes.
"""
from pathlib import Path
import hashlib,json,os,stat,tarfile,time
D=Path(__file__).resolve().parent;A=D.parent;R=A/'ROOT-CURRENT119-BUILD-ADMISSION-1';W=R/'OUTPUT/work'

def read(p):return json.loads(Path(p).read_bytes())
def file_ref(p):
 p=Path(p);h=hashlib.sha256();size=0
 with p.open('rb')as f:
  for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk);size+=len(chunk)
 return dict(path=str(p),bytes=size,sha256=h.hexdigest())
def auth(row):assert file_ref(row['path'])==row,row['path'];return Path(row['path'])
def write_new(p,obj):
 with p.open('x')as f:json.dump(obj,f,indent=2);f.write('\n')
grant=read(R/'ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json');profilepath=auth(grant['profile']);profile=read(profilepath);worker=read(W/'evidence/worker-result.json');producer=read(W/'evidence/producer-contract.json');assert len(worker['commands'])==4 and producer['commands']==worker['commands']and producer['contract']==profile['producer_contract']
selected={};outputs=[]
for actual,planned in zip(worker['commands'],profile['exact_commands']):
 assert actual['argv']==planned['argv']and actual['cwd']==planned['cwd']and actual['returncode']==0
 p=W/Path(actual['output']['path']).relative_to('/work');r=file_ref(p);assert(r['bytes'],r['sha256'])==(actual['output']['bytes'],actual['output']['sha256']);outputs.append(r);selected[str(p.relative_to(R))]=p
for relative in ['OUTPUT/work/output/build/kernel/mckernel.img.map','OUTPUT/work/output/build/kernel/CMakeFiles/mckernel.img.dir/link.d','OUTPUT/work/evidence/worker-result.json','OUTPUT/work/evidence/producer-contract.json','OUTPUT/plan.json','OUTPUT/terminal.json','OUTPUT/claim.json','OUTPUT/container.cid','OUTPUT/container.stdout','OUTPUT/container.stderr','ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json','ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json','ROOT-HOLDER-TOOL-JOIN.ACTUAL.json','HOLDER/RUNNER.JOINED.json']:
 selected[relative]=R/relative
for i in range(4):
 for suffix in ['stdout','stderr']:
  relative='OUTPUT/work/evidence/%02d.%s'%(i,suffix);selected[relative]=R/relative
selected['METADATA/PROFILE.ACTUAL.json']=profilepath
members=[]
for member,p in sorted(selected.items()):
 assert p.is_file()and not p.is_symlink();r=file_ref(p);members.append(dict(member=member,original=r,mode=stat.S_IMODE(p.stat().st_mode)))
retained=[row for row in profile['inputs']['objects']if not row['replace']];assert len(retained)==8
external=dict(actual_profile=grant['profile'],source_adoption=profile['actual_root_adoption'],readonly_source_exports=profile['inputs']['source_directory_exports'],source6153_root=profile['inputs']['source6153'],postimages=profile['inputs']['postimages'],configuration=profile['inputs']['configuration'],toolchain_manifest=file_ref(Path(profile['inputs']['toolchain_manifest'])),toolchain_lock_sha256=profile['inputs']['toolchain_lock_sha256'],toolchain_image=profile['inputs']['image'],toolchain_mounts=profile['inputs']['toolchain_mounts'],source_recipe119=profile['qualified119_source_recipe'],source_cohort=profile['cohort_source_bindings'],origin=profile['origin_source_materialization'],retained_eight_qualified_objects=retained,retained_seed=profile['inputs']['retained_seed'],reuse_descriptor=file_ref(Path(profile['reuse_descriptor'])))
manifest=dict(scope=__doc__.splitlines()[0],status='EXACT_ACTUAL119_ARCHIVE_MEMBER_MANIFEST_NO_NEW_ACCEPTANCE',actual_compiled_outputs=outputs,members=members,existing_reproduction_references=external,retained_placeholder_objects_archived=0,originals_deleted_or_modified=False,artifact_acceptance_credit=0,runtime_authority=None)
manifestpath=D/'MEMBERS-AND-REPRODUCTION-REFERENCES.json';write_new(manifestpath,manifest)
archive=D/'CURRENT119-EXACT-NEW-ARTIFACTS-AND-BUILD-RECORDS.tar.gz'
start=time.monotonic()
with tarfile.open(str(archive),'x:gz',compresslevel=6)as tar:
 for row in members:
  p=Path(row['original']['path']);info=tar.gettarinfo(str(p),arcname=row['member']);assert info.isfile();info.uid=info.gid=0;info.uname=info.gname=''
  with p.open('rb')as f:tar.addfile(info,f)
 info=tar.gettarinfo(str(manifestpath),arcname='METADATA/MEMBERS-AND-REPRODUCTION-REFERENCES.json');info.uid=info.gid=0;info.uname=info.gname=''
 with manifestpath.open('rb')as f:tar.addfile(info,f)
expected={row['member']:row['original']for row in members};expected['METADATA/MEMBERS-AND-REPRODUCTION-REFERENCES.json']=file_ref(manifestpath);verified=[]
with tarfile.open(str(archive),'r:gz')as tar:
 actual=tar.getmembers();assert len(actual)==len(expected)and{r.name for r in actual}==set(expected)
 for member in actual:
  assert member.isfile()and member.size==expected[member.name]['bytes'];f=tar.extractfile(member);h=hashlib.sha256();size=0
  for chunk in iter(lambda:f.read(1048576),b''):h.update(chunk);size+=len(chunk)
  assert size==expected[member.name]['bytes']and h.hexdigest()==expected[member.name]['sha256'];verified.append(member.name)
# Reconfirm every selected original after archive/readback. Nothing is removed.
for row in members:assert file_ref(row['original']['path'])==row['original']
receipt=dict(scope=manifest['scope'],status='PASS_EXACT_ARCHIVE_READBACK_AND_ORIGINALS_PRESERVED',archive=file_ref(archive),manifest=file_ref(manifestpath),members_verified=len(verified),uncompressed_member_bytes=sum(r['bytes']for r in expected.values()),actual_compiled_outputs=outputs,archive_wall_seconds=time.monotonic()-start,retained_original_objects=8,retained_empty_bind_placeholders_archived=0,originals_unchanged=True,all_original_sources_outputs_SDKs_failures_preserved=True,compiler_Docker_native_cleanup_chmod_calls=0,new_acceptance_credit=0,runtime_authority=None)
write_new(D/'ARCHIVE-READBACK.ACTUAL.json',receipt);print(json.dumps(receipt))
