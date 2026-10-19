"""Case-specific root admission snapshot. Source preparation grants no execution.
Adapts the accepted one-CPU snapshot; no owner/guest/root-module operation occurs here.
"""
import argparse,fcntl,hashlib,json,os,stat,subprocess,time
from pathlib import Path
N=Path(__file__).resolve().parent
BINDING_SHA256='6ac23782fff379bc7fb53332aeeb6bd404944e691e8ddce462ddb1e982491cb3'
def checked(r):
 data=Path(r['path']).read_bytes();assert hashlib.sha256(data).hexdigest()==r['sha256'];return json.loads(data)
def shortref(path,digest):return dict(path=path,sha256=digest)
def confined_new(path,prefix):
 p=Path(path);assert p.parent==N and p.name.startswith(prefix)and p.name.endswith('.json')and not os.path.lexists(p);return p

def publish_root_json(path,obj):
 assert os.getuid()==os.geteuid()==0
 raw=(json.dumps(obj,indent=2)+'\n').encode();fd=os.open(path,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644)
 try:
  os.fchmod(fd,0o644);position=0
  while position<len(raw):position+=os.write(fd,raw[position:])
  os.fsync(fd);before=os.fstat(fd);assert stat.S_ISREG(before.st_mode)and before.st_uid==before.st_gid==0 and stat.S_IMODE(before.st_mode)==0o644 and before.st_nlink==1
  readback=os.pread(fd,len(raw)+1,0);after=os.fstat(fd);assert readback==raw and (before.st_dev,before.st_ino,before.st_size,before.st_mode,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mode,after.st_mtime_ns,after.st_ctime_ns)
  return dict(path=str(path),sha256=hashlib.sha256(readback).hexdigest(),bytes=len(readback),device=after.st_dev,inode=after.st_ino,uid=after.st_uid,gid=after.st_gid,mode=stat.S_IMODE(after.st_mode),nlink=after.st_nlink)
 finally:os.close(fd)
def main():
 ap=argparse.ArgumentParser(allow_abbrev=False);ap.add_argument('--static-review',required=True);ap.add_argument('--static-review-sha256',required=True);ap.add_argument('--predecessor',required=True);ap.add_argument('--predecessor-sha256',required=True);ap.add_argument('--snapshot-output',required=True);ap.add_argument('--publication-output',required=True);a=ap.parse_args()
 assert os.getuid()==os.geteuid()==0
 b=checked(shortref(str(N/'snapshot-static-bindings.json'),BINDING_SHA256));proposal=checked(b['proposal']);meta=checked(b['metadata']);ordinary=checked(b['ordinary_acceptance']);terminal=checked(b['terminal_physical_acceptance']);checked(b['parent_receipt']);checked(b['machine_template'])
 static_ref=shortref(a.static_review,a.static_review_sha256);review=checked(static_ref)
 assert review['decision']=='PASS_NON_TEMPORAL_FP_THREAD_PARENT_BOUND_CASE_ENVELOPE'and review['runtime_release']is False
 assert review['proposal']['sha256']==b['proposal']['sha256']and review['proposal']['path']==b['proposal']['path']
 assert review['runtime_wrapper']['sha256']==b['runtime_wrapper']['sha256']and review['runtime_wrapper']['path']==b['runtime_wrapper']['path']
 assert review['root_snapshot_source']['sha256']==hashlib.sha256(Path(__file__).read_bytes()).hexdigest()and review['root_snapshot_source']['path']==str(Path(__file__))
 joins=checked(review['non_temporal_result']);assert joins['status']=='PASS_NON_TEMPORAL_FOURLEAF_NATIVE_INTERFACE_ONLY'and joins['root_or_guest_invoked']is False and joins['runtime_release']is False and joins['parent_identity']==b['parent_identity']
 assert review['non_temporal_source']['path']==str(N/'check_non_temporal.py')and review['non_temporal_source']['sha256']==hashlib.sha256((N/'check_non_temporal.py').read_bytes()).hexdigest()
 assert ordinary['schema']=='mckernel.independent-fourleaf-continuation-actual-ordinary-acceptance.v1'and ordinary['decision']=='PASS_ACTUAL_METADATA_PROJECTION_FIXTURE_AND_FRESH_PARENT'and ordinary['implementation_ownership']is False
 assert meta['proposal']['sha256']==b['proposal']['sha256']and proposal['parent']['identity']==b['parent_identity']
 for r in [b['runtime_wrapper'],b['manifest'],b['source_projection'],b['consumer_metadata']]:checked(r)if r['path'].endswith('.json')else None
 assert hashlib.sha256(Path(b['runtime_wrapper']['path']).read_bytes()).hexdigest()==b['runtime_wrapper']['sha256']
 assert proposal['manifest']==b['manifest']and proposal['mckernel_image']==b['image']and b['image']['sha256']=='0eca91b13bd62ab98441104930eda1a63f247fecd939996858b16f90b7480550'
 profile=proposal['profile'];assert profile['memory']==profile['memory_swap']==12884901888 and profile['cpus']==4 and profile['cpuset']=='2-5'and profile['pids']==512 and profile['network']=='none'and profile['mckernel_cpus']==1 and profile['guest_memory_mib']==8192
 predecessor_ref=shortref(a.predecessor,a.predecessor_sha256);checked(predecessor_ref)
 # The dispatcher independently accepts this actual latest physical predecessor before invoking the recipe.
 parent=Path(proposal['parent']['path']);s=parent.lstat();identity=dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=oct(stat.S_IMODE(s.st_mode)))
 assert identity==b['parent_identity']=={'device':1828,'inode':757493,'uid':1000,'gid':1000,'mode':'0o700'}and parent.resolve(strict=True)==parent and not list(parent.iterdir())
 assert proposal['nonce']==b['nonce']=='01cc688cfc76be9f30652b1a64006189'
 assert not os.path.lexists(parent/('attempt-'+proposal['nonce']))and not os.path.lexists(str(parent)+'.owner-'+proposal['nonce'])
 for name in ['owner.stdout','owner.stderr','owner-join.json']+[f'readback-{i}.{suffix}'for i in range(1,4)for suffix in ['stdout','stderr','command.json']]:assert not os.path.lexists(N/name)
 output=confined_new(a.snapshot_output,'root-live-preflight-');publication=confined_new(a.publication_output,'root-snapshot-publication-');assert output!=publication
 scratch=Path(b['scratch']['path']);assert (scratch.stat().st_dev,scratch.stat().st_ino)==(b['scratch']['device'],b['scratch']['inode'])
 assert json.loads(subprocess.check_output(['/usr/bin/findmnt','-J','-o','TARGET,UUID','-T',str(scratch)],text=True))['filesystems']==[dict(target=str(scratch),uuid=b['scratch']['uuid'])]
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==b['boot_id']
 lock=Path(b['root_mutex']['path']);s=lock.stat();assert (s.st_dev,s.st_ino,s.st_uid,s.st_gid)==(27,4,0,0)
 with lock.open('r')as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(f,fcntl.LOCK_UN)
 assert all(not os.path.lexists(p)for p in b['released_paths'])
 capacity={}
 for path,floor in [(Path('/home/holden/mckernel'),16*2**30),(scratch,12*2**30)]:
  v=os.statvfs(path);free=v.f_bavail*v.f_frsize;assert free>=floor+640*2**20;capacity[str(path)]=dict(available_bytes=free,floor_bytes=floor,reserve_bytes=640*2**20)
 mem=int(next(x for x in Path('/proc/meminfo').read_text().splitlines()if x.startswith('MemAvailable:')).split()[1])*1024;assert mem>=16*2**30
 state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text());assert state['phase']=='running'and state['stop_reason']is None
 used=state['last_rate_limits']['primary']['usedPercent'];assert used<97
 result=dict(status='PASS_LIVE_PREEXECUTION_SNAPSHOT',time_epoch=time.time(),boot_id=b['boot_id'],parent_identity=identity,exclusive_heavy_accepted=True,root_mutex_snapshot_free=True,capacity=capacity,mem_available_bytes=mem,included_usage_percent=used,heavy_profile=profile,released_paths_absent=b['released_paths'],terminal_acceptance=b['terminal_physical_acceptance'],exclusive_queue_predecessor=predecessor_ref,independent_static_execution_decision=static_ref,accepted_actual_stage_fixture_parent_review=b['ordinary_acceptance'],snapshot_static_bindings=shortref(str(N/'snapshot-static-bindings.json'),BINDING_SHA256),root_publication_policy='Root-owned0644/singlelink/fullFDreadback; readable by dispatcher UID1000 without sudo')
 published=publish_root_json(output,result);receipt=dict(status='PASS_ROOT_FD_PUBLISHED_READABLE_SNAPSHOT',snapshot=published,root_readback_bytes_equal=True,dispatcher_other_read_bit=True,owner_or_guest_invoked=False)
 publication_ref=publish_root_json(publication,receipt)
 print(json.dumps(dict(status=result['status'],snapshot=published,publication=publication_ref)),flush=True)
if __name__=='__main__':main()
