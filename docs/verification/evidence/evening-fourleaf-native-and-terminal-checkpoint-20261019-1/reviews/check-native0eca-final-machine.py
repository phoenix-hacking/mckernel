import os,sys,json,hashlib,time,stat,copy
from pathlib import Path
O=Path('/home/holden/mckernel-work/host-preparation/evening-git-owner-review-20261019-1');N=Path('/home/holden/mckernel-work/host-preparation/evening-fourleaf-native-continuation-20261019-1/native-final-preparation-1')
STATIC=dict(path=str(O/'NATIVE0ECA-CONDITIONAL-STATIC-ENVELOPE-REVIEW.json'),sha256='1c174b8d736f1d830bc79bf11bdb848c62ac610f70b87a69db86803d90f35f64')
PRED=dict(path='/home/holden/mckernel-work/host-preparation/evening-two-cpu-end-to-end-review-20261019-1/decision-actual-short2-failed-diagnostic-physical-retirement.json',sha256='be68a21eb8940a3fb60a4cf675a9a16af98106bbc106f18796d9e18edfe74b9a')
OUTPUT=N/'final-machine-execution-review-1.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(d):return (json.dumps(d,sort_keys=True,separators=(',',':'))+'\n').encode()
def md(s):return dict(device=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode),nlink=s.st_nlink,size=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
def read(p,expected=None,root=False):
 p=Path(p);fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW)
 try:
  a=os.fstat(fd);assert stat.S_ISREG(a.st_mode) and a.st_nlink==1 and a.st_size<=33554432
  if root:assert (a.st_uid,a.st_gid,stat.S_IMODE(a.st_mode))==(0,0,0o644)
  chunks=[]
  while True:
   b=os.read(fd,65536)
   if not b:break
   chunks.append(b)
  b=b''.join(chunks);z=os.fstat(fd);named=os.stat(p,follow_symlinks=False);assert md(a)==md(z)==md(named) and len(b)==a.st_size
  if expected is not None:assert sha(b)==expected
  return b,md(a)
 finally:os.close(fd)
def checked(r,root=False):b,m=read(r['path'],r['sha256'],root);return json.loads(b),m
def ref(p):b,m=read(p);return dict(path=str(p),sha256=sha(b),bytes=len(b))
def main():
 assert os.getuid()==os.geteuid()==1000
 assert len(sys.argv)==3 and sys.argv[1]=='--machine-sha256';mh=sys.argv[2];assert len(mh)==64
 static,_=checked(STATIC);assert static['decision']=='PASS_NON_TEMPORAL_FP_THREAD_PARENT_BOUND_CASE_ENVELOPE' and static['runtime_release'] is False
 request,_=checked(static['reviewed_request']);proposal,_=checked(request['proposal']);binding,_=checked(request['snapshot_static_bindings']);template,_=checked(request['machine_template'])
 for r in request['source_pins'].values():read(r['path'],r['sha256'])
 pred,_=checked(PRED);assert pred['schema']=='mckernel.independent-native-failed-diagnostic-physical-retirement.v1' and pred['status']=='PASS_FAILED_DIAGNOSTIC_POSITIVE_PHYSICAL_RETIREMENT'
 assert all(pred[k] is True for k in ['physical_release','terminal','container_absent','owned_groups_empty']) and pred['lease_retained'] is False and pred['application_acceptance'] is False and pred['operation_status']=='FAIL'
 machine_path=N/'machine-execution-release-1.json';machine_raw,mmeta=read(machine_path,mh);machine=json.loads(machine_raw)
 snapshot=machine['fresh_live_preflight'];publication=machine['snapshot_publication'];assert snapshot['path']==str(N/'root-live-preflight-1.json') and publication['path']==str(N/'root-snapshot-publication-1.json')
 fresh,sm=checked(snapshot,True);pub,pm=checked(publication,True);assert pub['status']=='PASS_ROOT_FD_PUBLISHED_READABLE_SNAPSHOT' and pub['root_readback_bytes_equal'] is True and pub['dispatcher_other_read_bit'] is True and pub['owner_or_guest_invoked'] is False
 desc=pub['snapshot'];assert desc['path']==snapshot['path'] and desc['sha256']==snapshot['sha256'] and desc['bytes']==sm['size']
 assert all(desc[k]==sm[k] for k in ['device','inode','uid','gid','mode','nlink'])
 assert fresh['status']=='PASS_LIVE_PREEXECUTION_SNAPSHOT' and fresh['independent_static_execution_decision']==STATIC and fresh['exclusive_queue_predecessor']==PRED
 assert fresh['terminal_acceptance']==binding['terminal_physical_acceptance'] and fresh['accepted_actual_stage_fixture_parent_review']==binding['ordinary_acceptance']
 assert fresh['snapshot_static_bindings']==dict(path=str(N/'snapshot-static-bindings.json'),sha256=request['snapshot_static_bindings']['sha256'])
 assert fresh['heavy_profile']==proposal['profile'] and fresh['parent_identity']==binding['parent_identity'] and fresh['exclusive_heavy_accepted'] is True and fresh['root_mutex_snapshot_free'] is True
 assert fresh['boot_id']==binding['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip() and fresh['included_usage_percent']<97 and fresh['mem_available_bytes']>=16*2**30
 for p,floor in [('/home/holden/mckernel',16*2**30),('/home/holden/mckernel-work/scratch',12*2**30)]:assert fresh['capacity'][p]['available_bytes']>=floor+640*2**20
 assert fresh['released_paths_absent']==binding['released_paths'] and all(not os.path.lexists(p) for p in binding['released_paths'])
 parent=Path(proposal['parent']['path']);ps=parent.lstat();identity=dict(device=ps.st_dev,inode=ps.st_ino,uid=ps.st_uid,gid=ps.st_gid,mode=oct(stat.S_IMODE(ps.st_mode)))
 assert identity==binding['parent_identity']==proposal['parent']['identity'] and parent.resolve(strict=True)==parent and not list(parent.iterdir())
 attempt=parent/('attempt-'+proposal['nonce']);endpoint=str(attempt/'qmp.sock');assert len(os.fsencode(endpoint))==101<=107 and proposal['unix_monitor_endpoints']==[dict(path=endpoint,encoded_bytes=101,max_bytes=107)] and proposal['other_monitor_endpoints']==[]
 expected=copy.deepcopy(template);expected.update(status='PASS_EXECUTION_RELEASE',runtime_release=True,fresh_live_preflight=snapshot,snapshot_publication=publication,independent_static_execution_decision=STATIC,accepted_actual_stage_fixture_parent_review=fresh['accepted_actual_stage_fixture_parent_review'],terminal_cleanup_and_common_shared_release=dict(status='PASS',ref=fresh['terminal_acceptance']),exclusive_queue_predecessor=dict(status='PASS_POSITIVE_PHYSICAL_RELEASE_INDEPENDENTLY_ACCEPTED',ref=PRED,image_matching_required=False),unprivileged_snapshot_readback=dict(uid=1000,snapshot_device=sm['device'],snapshot_inode=sm['inode'],root_owned_readable0644=True))
 assert machine==expected
 capture_refs=[]
 for role,key in [('snapshot','root_snapshot'),('assembly','unprivileged_late_data_assembly')]:
  status_path=N/(role+'-command.status.json');status,_=checked(ref(status_path));assert status['returncode']==0 and status['direct_child_joined'] is True
  expected_argv=request['commands'][key]['argv'];replace={'PENDING_ACTUAL_INDEPENDENT_STATIC_REVIEW_PATH':STATIC['path'],'PENDING_ACTUAL_INDEPENDENT_STATIC_REVIEW_SHA256':STATIC['sha256'],'PENDING_LATEST_ACCEPTED_PHYSICAL_PREDECESSOR_PATH':PRED['path'],'PENDING_LATEST_ACCEPTED_PHYSICAL_PREDECESSOR_SHA256':PRED['sha256'],'PENDING_ACTUAL_FRESH_SNAPSHOT_SHA256':snapshot['sha256'],'PENDING_ACTUAL_ROOT_PUBLICATION_SHA256':publication['sha256']}
  assert status['argv']==[replace.get(x,x)for x in expected_argv]
  err,_=read(N/(role+'-command.stderr'));assert err==b'';out,_=read(N/(role+'-command.stdout'));assert out
  capture_refs.append(dict(role=role,status=ref(status_path),stdout=ref(N/(role+'-command.stdout')),stderr=ref(N/(role+'-command.stderr'))))
 now=time.time();age=now-fresh['time_epoch'];assert 0<=age<=60
 allowed=['/home/holden/anaconda3/bin/python3','-I','-B',str(N/'dispatch-runtime.py'),'--release',str(machine_path),'--release-sha256',mh]
 result=dict(schema='mckernel.independent-fourleaf-native-exact-machine-release-review.v1',decision='PASS_EXACT_FOURLEAF0ECA_MACHINE_RELEASE_AND_OWNER_INVOCATION',reviewer='resume_git_owner_review',implementation_ownership=False,machine_release=dict(path=str(machine_path),sha256=mh,bytes=len(machine_raw)),machine_projection_sha256=sha(canonical(machine)),snapshot=snapshot,snapshot_publication=publication,static_decision=STATIC,snapshot_time_epoch=fresh['time_epoch'],review_time_epoch=now,snapshot_age_seconds=age,allowed_argv=allowed,owner_argv=proposal['argv'],parent_identity=identity,nonce=proposal['nonce'],endpoint_encoded_bytes=101,latest_physical_predecessor=PRED,predecessor_application_acceptance=False,snapshot_FD_metadata=sm,publication_FD_metadata=pm,actual_preparation_captures=capture_refs,execution_count=1,launch_scope='One exact0eca/1McKernelCPU native case under sole accepted4CPU2-5/12GiB/noSwap/512/noNet owner; no outer owner kill; same3boundedpostjoin readbacks; stopunexpectedfailure/no retry.',native_acceptance=False,application_acceptance=False,compute_c_retirement_credit=False,mechanical_instantiation='Reviewer-owned frozen checker; all predicates and actual whole-machine bytes checked. Coordinator must verify this exact output hash, original epoch<=60, machine bytes/projection and argv immediately before exec.')
 b=(json.dumps(result,sort_keys=True,indent=2)+'\n').encode();fd=os.open(OUTPUT,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:os.write(fd,b);os.fsync(fd)
 finally:os.close(fd)
 reread,_=read(OUTPUT);assert reread==b
 print(json.dumps(dict(decision=result['decision'],path=str(OUTPUT),sha256=sha(b),machine_sha256=mh,snapshot_age_seconds=age),sort_keys=True))
if __name__=='__main__':main()
