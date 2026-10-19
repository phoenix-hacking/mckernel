"""Late data assembly with actual UID1000 readback of root-FD-published snapshot.
No owner/guest/root calls. Output is pending external exact final execution decision.
"""
from pathlib import Path
import argparse,hashlib,json,os,stat,time
N=Path(__file__).resolve().parent
BINDING_SHA256='6ac23782fff379bc7fb53332aeeb6bd404944e691e8ddce462ddb1e982491cb3'
def checked(r):
 data=Path(r['path']).read_bytes();assert hashlib.sha256(data).hexdigest()==r['sha256'];return json.loads(data)
def root_readable(r):
 fd=os.open(r['path'],os.O_RDONLY|os.O_NOFOLLOW)
 try:
  before=os.fstat(fd);assert stat.S_ISREG(before.st_mode)and before.st_uid==before.st_gid==0 and stat.S_IMODE(before.st_mode)==0o644 and before.st_nlink==1
  chunks=[]
  while True:
   chunk=os.read(fd,1024*1024)
   if not chunk:break
   chunks.append(chunk)
  data=b''.join(chunks);after=os.fstat(fd);assert (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns,before.st_ctime_ns)==(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns,after.st_ctime_ns)
  assert hashlib.sha256(data).hexdigest()==r['sha256'];return json.loads(data),after
 finally:os.close(fd)
def main():
 ap=argparse.ArgumentParser(allow_abbrev=False);ap.add_argument('--snapshot',required=True);ap.add_argument('--snapshot-sha256',required=True);ap.add_argument('--publication',required=True);ap.add_argument('--publication-sha256',required=True);ap.add_argument('--output',required=True);a=ap.parse_args()
 assert os.getuid()==os.geteuid()==1000
 snapshot_ref=dict(path=a.snapshot,sha256=a.snapshot_sha256);publication_ref=dict(path=a.publication,sha256=a.publication_sha256)
 fresh,snapshot_stat=root_readable(snapshot_ref);publication,_=root_readable(publication_ref);assert publication['status']=='PASS_ROOT_FD_PUBLISHED_READABLE_SNAPSHOT'
 desc=publication['snapshot'];assert desc['path']==a.snapshot and desc['sha256']==a.snapshot_sha256 and (desc['device'],desc['inode'],desc['uid'],desc['gid'],desc['mode'],desc['nlink'])==(snapshot_stat.st_dev,snapshot_stat.st_ino,0,0,0o644,1)
 assert fresh['status']=='PASS_LIVE_PREEXECUTION_SNAPSHOT'and 0<=time.time()-fresh['time_epoch']<=60
 b=checked(dict(path=str(N/'snapshot-static-bindings.json'),sha256=BINDING_SHA256));assert fresh['snapshot_static_bindings']['sha256']==BINDING_SHA256
 machine=checked(b['machine_template']);assert machine['parent_identity']==fresh['parent_identity']==b['parent_identity']
 assert fresh['terminal_acceptance']==b['terminal_physical_acceptance']and fresh['accepted_actual_stage_fixture_parent_review']==b['ordinary_acceptance']
 assert fresh['exclusive_heavy_accepted']is True and fresh['root_mutex_snapshot_free']is True
 machine.update(status='PASS_EXECUTION_RELEASE',runtime_release=True,fresh_live_preflight=snapshot_ref,snapshot_publication=publication_ref,independent_static_execution_decision=fresh['independent_static_execution_decision'],accepted_actual_stage_fixture_parent_review=fresh['accepted_actual_stage_fixture_parent_review'],terminal_cleanup_and_common_shared_release=dict(status='PASS',ref=fresh['terminal_acceptance']),exclusive_queue_predecessor=dict(status='PASS_POSITIVE_PHYSICAL_RELEASE_INDEPENDENTLY_ACCEPTED',ref=fresh['exclusive_queue_predecessor'],image_matching_required=False),unprivileged_snapshot_readback=dict(uid=os.getuid(),snapshot_device=snapshot_stat.st_dev,snapshot_inode=snapshot_stat.st_ino,root_owned_readable0644=True))
 output=Path(a.output);assert output.parent==N and output.name.startswith('machine-execution-release-')and output.name.endswith('.json')and not os.path.lexists(output)
 with output.open('x')as stream:json.dump(machine,stream,indent=2);stream.write('\n')
 print(json.dumps(dict(status='READY_EXACT_MACHINE_PENDING_EXTERNAL_EXECUTION_DECISION',path=str(output),sha256=hashlib.sha256(output.read_bytes()).hexdigest(),snapshot_age_seconds=time.time()-fresh['time_epoch'])),flush=True)
if __name__=='__main__':main()
