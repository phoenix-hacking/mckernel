"""Exact remaining-only3 observation; original captures and failed14 preserved."""
from pathlib import Path
import hashlib,json,os,stat,subprocess,sys,time
def digest(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(65536),b''):h.update(b)
 return h.hexdigest()
def bound(row):
 p=Path(row['path']);assert digest(p)==row['sha256'];return json.loads(p.read_text())
def write(p,d):
 with p.open('x') as f:json.dump(d,f,sort_keys=True,indent=2);f.write('\n')
def identity(p):
 s=os.lstat(p);assert stat.S_ISREG(s.st_mode)
 return dict(dev=s.st_dev,inode=s.st_ino,uid=s.st_uid,gid=s.st_gid,mode=stat.S_IMODE(s.st_mode),bytes=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)
def main(argv=None):
 args=sys.argv[1:] if argv is None else argv;assert len(args)==2
 release=bound(dict(path=args[0],sha256=args[1]));review=bound(release['execution_review']);payload={k:v for k,v in release.items() if k!='execution_review'}
 assert release['status']=='PASS_EXACT_ORDINARY_POSTBUILD_READONLY_RELEASE' and review['decision']=='PASS_EXACT_ORDINARY_POSTBUILD_READONLY' and review['implementation_ownership'] is False and review['reviewer']!=release['author']
 assert review['reviewed_release_payload_sha256']==hashlib.sha256((json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()).hexdigest()
 for key in ['dispatcher','descriptor_facts_producer']:assert digest(release[key]['path'])==release[key]['sha256']
 assert release['dispatcher']['path']==str(Path(__file__).resolve())
 plan=bound(release['commands']);profile=bound(release['profile']);tools=bound(release['tools']);O=Path(release['output_directory'])
 assert len(plan['operations'])==3 and {o['role'] for o in plan['operations']}=={'rust-release','rust-replace','image-range'}
 copies=bound(release['copy_receipt']);original=bound(release['original_observation_release'])
 for role,row in release['input_artifacts'].items():
  c=copies['artifacts'][role];assert c['sha256']==row['sha256'] and c['retained_path']==row['path'] and c['retained_dev']==row['dev'] and c['retained_inode']==row['inode'] and c['bytes']==row['bytes']
 # Reuse exact prior completed copy hashes; stable FD/stat identity, no image rehash.
 held=[]
 for row in release['input_artifacts'].values():
  fd=os.open(row['path'],os.O_RDONLY|os.O_NOFOLLOW);held.append((fd,row))
 def sourcecheck():
  for fd,row in held:
   s=os.fstat(fd);assert stat.S_ISREG(s.st_mode) and s.st_nlink==1
   assert identity(row['path'])=={k:row[k] for k in ['dev','inode','uid','gid','mode','bytes','mtime_ns','ctime_ns']}
   assert (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)==(row['dev'],row['inode'],row['bytes'],row['mtime_ns'],row['ctime_ns'])
 for row in tools.values():assert str(Path(row['path']).resolve())==row['resolved_path'] and digest(row['path'])==row['sha256'] and identity(Path(row['path']).resolve())==row['identity']
 def capacitycheck(remaining):
  for label,path in [('host',Path('/home/holden')),('scratch',Path('/home/holden/mckernel-work/scratch'))]:
   cap=profile['fresh_admission'][label];fs=os.statvfs(path);assert fs.f_bavail*fs.f_frsize>=cap['floor_bytes']+cap['emergency_bytes']+(remaining if label=='host' else 0)
 for p in profile['required_absent_paths']:assert not os.path.lexists(p)
 sourcecheck();remaining=profile['absolute_total_output_cap_bytes'];capacitycheck(remaining);O.mkdir(mode=0o700);results=[]
 def run(argv,stdout,stderr,status_path,label,reservation,contract):
  nonlocal remaining
  assert reservation<=remaining;capacitycheck(remaining);sourcecheck()
  write(Path(str(status_path)+'.command.json'),dict(argv=argv,stage=label,reservation_bytes=reservation,release_sha256=args[1]))
  start=time.monotonic();observer_error=None
  with Path(stdout).open('xb') as out,Path(stderr).open('xb') as err:
   child=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err)
   try:write(Path(str(status_path)+'.child.json'),dict(pid=child.pid,monotonic_start=start,proc_queries=False))
   except BaseException as ex:observer_error=dict(type=type(ex).__name__,error=str(ex))
   finally:code=child.wait()
  row=dict(stage=label,observer_error=observer_error,argv=argv,returncode=code,direct_child_joined=True,elapsed_seconds=time.monotonic()-start,stdout_bytes=Path(stdout).stat().st_size,stderr_bytes=Path(stderr).stat().st_size,stdout_sha256=digest(stdout),stderr_sha256=digest(stderr))
  write(Path(status_path),row);results.append(row)
  assert code==contract['returncode'] and observer_error is None,label
  if contract['stderr_policy']=='empty':assert row['stderr_bytes']==0,label
  assert row['stdout_bytes']<reservation//2 and row['stderr_bytes']<reservation//2,label
  sourcecheck();remaining-=reservation
 for op in plan['operations']:
  run(op['argv'],op['stdout_path'],op['stderr_path'],op['status_path'],'remaining-'+op['role'],op['both_stream_reservation_bytes'],dict(returncode=0,stderr_policy='empty'))
 completion=O/'completed-remaining-receipt.json';write(completion,dict(status='PASS_REMAINING3_COMPLETION_ONLY',release_sha256=args[1],results=results,original14_failure_preserved=True,production_or_native_acceptance=False))
 factsargv=['/home/holden/anaconda3/bin/python3','-I','-B',release['descriptor_facts_producer']['path'],'--plan',release['commands']['path'],'--plan-sha256',release['commands']['sha256'],'--release',args[0],'--release-sha256',args[1],'--completion',str(completion),'--completion-sha256',digest(completion),'--output',str(O/'four-leaf-facts-v3.json')]
 run(factsargv,str(O/'facts.stdout'),str(O/'facts.stderr'),str(O/'facts.status.json'),'facts-v3',2*1048576,dict(returncode=0,stderr_policy='empty'))
 write(O/'result.json',dict(status='PASS_REMAINING3_AND_STRICT_V3_FACTS_ONLY',release_sha256=args[1],stages=len(results),facts_sha256=digest(O/'four-leaf-facts-v3.json'),original14_failure_preserved=True,original_full_DWARF_gap_open=True,production_or_native_acceptance=False))
 for fd,_ in held:os.close(fd)
 print('PASS remaining3+facts; preserved original14failure; DWARFgap OPEN')
if __name__=='__main__':main()
