import os,json,hashlib,stat
from pathlib import Path
H=Path('/home/holden/mckernel-work/host-preparation');N=H/'current-host-pair-205-three-rounds-20261020-1';D=N/'stage-preparation-1';Q=D/'native-packet-1';R=H/'current-host-pair-205-three-rounds-independent-review-20261020-1';C=H/'current-host-rust-pair-native-snapshot-20261019-1/three-round205-case-1';P=H/'current-host-pair-205-three-rounds-physical-review-20261020-1'
OLD=H/'current-host-pair-205-two-rounds-20261019-1'
def read(p):return json.loads(Path(p).read_bytes())
def meta(s):return dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode),nlink=s.st_nlink,size=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
def checked(p,limit=2*1024*1024):
 p=Path(p);fd=os.open(str(p),os.O_RDONLY|os.O_NOFOLLOW)
 try:
  a=os.fstat(fd);assert stat.S_ISREG(a.st_mode) and a.st_size<=limit and a.st_nlink>=1
  data=b''
  while len(data)<a.st_size:
   chunk=os.read(fd,min(131072,a.st_size-len(data)));assert chunk;data+=chunk
  assert meta(a)==meta(os.fstat(fd)) and len(data)==a.st_size
 finally:os.close(fd)
 return dict(path=str(p),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
def write(p,x):
 raw=(json.dumps(x,indent=2,sort_keys=True)+'\n').encode()
 with Path(p).open('xb') as f:f.write(raw)
 return checked(p)
def row(p,r=None):
 p=Path(p);r=r or checked(p);return dict(source_path=str(p),repository_path='docs/verification/evidence/'+str(p.relative_to(H)),sha256=r['sha256'],bytes=r['bytes'])
semantic=R/'ACTUAL-THREE-ROUND-SIX-APP-NATIVE-AND-THROUGHPUT-REVIEW.json';physical=P/'decision.json';joined=R/'ACTUAL-SIX-APP-SEMANTIC-AND-PHYSICAL-JOIN-ADDENDUM.json'
for p,sha,size in [(semantic,'65be31f97541a4910321083d09973295e57e67b1c110246140dbf90676994fb4',24263),(physical,'33e1d2c5e000b789f9adf0595e02a5e50075cbe54a61e6154f267a92bb9ca196',16451),(joined,'88aa54e87eeeec57edeee7ba5925d3a366ce0a4abcc013aea4600bf7c0ed65a3',1217)]:
 r=checked(p);assert r['sha256']==sha and r['bytes']==size
stagefile=D/'stage-three-rounds-1/stage-result.json';stage=read(stagefile);stageauthority=checked(stagefile)
artifacts=[];excluded=set()
for dirname,role in [('04-readback-1','native_owner_archive'),('06-readback-3','native_attempt_archive')]:
 statuspath=Q/'captures'/dirname/'status.json';status=read(statuspath);desc=status['streams']['stdout'];assert status['returncode']==0 and status['direct_child_joined'] and status['process_group_absent'];excluded.add(desc['path']);artifacts.append(dict(role=role,descriptor=desc,authority=checked(statuspath),export_policy='DESCRIPTOR_ONLY_PRESERVE_RAW_PRIVATE'))
for key,role in [('original_collector','compiled_three_round_collector'),('collector','staged_three_round_collector'),('overlay','staged_initramfs')]:
 desc=stage[key];p=Path(desc['path']);s=p.lstat();assert stat.S_ISREG(s.st_mode) and s.st_size==desc['size'] and s.st_mode==desc['mode'];excluded.add(str(p));artifacts.append(dict(role=role,descriptor=desc,actual_current_metadata=meta(s),authority=stageauthority,export_policy='DESCRIPTOR_ONLY_PRESERVE_ACTUAL_PRIVATE_BINARY',sha256_reused_from_genuine_closed_stage=True))
body=N/'ordinary-check-1/actual-body';br=checked(body);excluded.add(str(body));artifacts.append(dict(role='actual_body_fixture_binary',descriptor=br,actual_current_metadata=meta(body.lstat()),authority=checked(N/'ordinary-check-1/compile-actual-body/status.json'),export_policy='DESCRIPTOR_ONLY_PRESERVE_PRIVATE_FIXTURE_BINARY'))
descpath=N/'ACTUAL-STAGE-AND-RUNTIME-ARTIFACT-DESCRIPTORS-1.json';descref=write(descpath,dict(scope='Actual existing artifacts pinned only; no archive or binary copies',artifacts=artifacts,actual_runtime_whole=checked(Q/'root-seven-whole-1.json'),native_semantic_acceptance=checked(semantic),native_physical_acceptance=checked(physical),native_join_addendum=checked(joined)))
oldpath=OLD/'ACTUAL-SOURCE-ORDINARY-RUNTIME-CHECKPOINT-ALLOWLIST-1.json';old=read(oldpath);oldaddpath=OLD/'ACCEPTED-NATIVE-REPORTS-CHECKPOINT-ADDENDUM-1.json';oldadd=read(oldaddpath)
rows=list(old['rows']);known={r['source_path'] for r in rows}
for r in oldadd['rows']:
 if r['source_path'] not in known:rows.append(r);known.add(r['source_path'])
reused=len(rows)
newrows=[]
for root in [N,R,C,P]:
 for p in sorted(root.rglob('*')):
  if '__pycache__' in p.parts:continue
  s=p.lstat()
  if stat.S_ISDIR(s.st_mode):continue
  assert stat.S_ISREG(s.st_mode),str(p)
  if str(p) in excluded:continue
  assert str(p) not in known
  rr=row(p);newrows.append(rr);known.add(str(p))
rows.extend(newrows);assert len({r['repository_path'] for r in rows})==len(rows)
reports=[checked(p) for p in sorted(R.glob('*.json'))]+[checked(physical)]
out=N/'ACTUAL-SOURCE-ORDINARY-RUNTIME-CHECKPOINT-ALLOWLIST-1.json'
result=write(out,dict(status='ACTUAL_SIX_STRICT_APPS_THREE_ROUNDS_AND_PHYSICAL_RELEASE_ACCEPTED',rows=rows,row_count=len(rows),total_bytes=sum(r['bytes'] for r in rows),new_row_count=len(newrows),new_bytes=sum(r['bytes'] for r in newrows),reused_rows_without_rehash=reused,reused_exports=[checked(oldpath),checked(oldaddpath)],artifact_descriptors=descref,genuine_current_reports=reports,actual_scope=dict(boots=1,native_lifecycle_cycles=1,sequential_pair_rounds=3,strict_successful_Rust_app_launches=6,completed_owner_seconds=46.60141389700584,baseline_apps=2,baseline_owner_seconds=44.160327,apps_per_completed_owner_ratio=2.8428532510364875,target_minimum_ratio=2.3,target_met=True,new_logical_cases=0,new_Rust_retired_paths=0,stress_quotas_closed=False,full_FP_provider_claim=False),unchanged_reused_sources_rehashed=False,archives_binaries_copied=False))
print(json.dumps(dict(allowlist=result,rows=len(rows),reused=reused,new_rows=len(newrows),new_bytes=sum(r['bytes'] for r in newrows),descriptor_only_artifacts=len(artifacts))))
