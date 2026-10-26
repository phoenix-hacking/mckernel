"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One ordinary reviewed initialization: exact three empty namespace dirs only.
No lease/common/shared/mutex/capture/output/root query or owner operation.
"""
from pathlib import Path
import hashlib,json,os,stat,sys,types
INPUT=Path(__file__).parent / 'ACTUAL004F-POSTACC55-AND-EXACT-NAMESPACE2-INITIALIZATION.INPUTS.json'
INPUT_SHA='41bf8d65de750468e65d404a15165114fd43702605eeeeede617d21947872b75'
VALIDATOR={'path': '/home/holden/mckernel/docs/verification/evidence/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/new-window-source-18-current289-union-source-1/qualified-getsiginfo-current290-successor-1/default-image-current290-coherent-overlay-source-1/authenticated-materialization-and-entry-source-1/attempt2-coherent-entry-preparation-source-1/genuine-postshared-binding-successor-source-1/validate_actual004f_postshared_physical.SOURCE-ONLY.py', 'sha256': 'd2c14d13f400ab37fb0e7743b573041fbd465807baec69ec06e0839b395569cc', 'bytes': 3937}

def need(ok,message):
 if not ok:raise RuntimeError('namespace2 init: '+message)
def ref(path):
 path=Path(path);b=path.read_bytes();return dict(path=str(path),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
def write(path,value):
 raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
 with path.open('xb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
 return ref(path)
def run(grant_path,grant_sha):
 need(os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={0},'ordinary UID1000 CPU0')
 need(ref(INPUT)['sha256']==INPUT_SHA and ref(VALIDATOR['path'])==VALIDATOR,'exact source/data/physical consumer')
 d=json.loads(INPUT.read_bytes());g=json.loads(Path(grant_path).read_bytes());need(ref(grant_path)['sha256']==grant_sha,'exact actual one-shot root grant')
 need(g['author']=='/root' and g['decision']=='GRANT_ONE_ORDINARY_ATTEMPT2_THREE_NAMESPACE_INITIALIZATION' and g['maximum_invocations']==1 and g['source']==ref(__file__) and g['inputs']==ref(INPUT) and g['physical']==d['current_physical_acceptance'] and g['request']==d['request'] and g['image_entry_owner']==d['image_entry_owner'] and g['host_control_owner']==d['host_control_owner'] and g['actual_no_new_heavy_since_acceptance'] is True,'exact root one-use ordinary initialization grant')
 m=types.ModuleType('actual004f_physical');m.__file__=VALIDATOR['path'];exec(compile(Path(m.__file__).read_bytes(),m.__file__,'exec'),m.__dict__);m.validate(d['current_physical_acceptance'],d['postreturn'])
 target=Path(d['planned_namespace']);q=json.loads(Path(d['request']['path']).read_bytes());need(q['work_root']==str(target/'owner-work') and q['owner_evidence_root']==str(target/'owner-evidence'),'exact request namespace paths')
 output=Path(__file__).parent/'ACTUAL-ATTEMPT2-THREE-NAMESPACE-INITIALIZATION.json';need(not os.path.lexists(output),'fresh initialization receipt')
 fds=[];rows=[]
 try:
  fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC);fds.append(fd)
  for index,expected in enumerate(d['parent_ancestry']):
   if index:fd=os.open(Path(expected['path']).name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd);fds.append(fd)
   s=os.fstat(fd);need(dict(path=expected['path'],device=s.st_dev,inode=s.st_ino,mode=s.st_mode,uid=s.st_uid,gid=s.st_gid)==expected,'pinned parent ancestry')
  os.mkdir(target.name,mode=0o700,dir_fd=fd)
  rootfd=os.open(target.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd);fds.append(rootfd)
  def identity(path,s,entries):return dict(path=str(path),device=s.st_dev,inode=s.st_ino,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid,entries=entries)
  for name in ['owner-work','owner-evidence']:
   os.mkdir(name,mode=0o700,dir_fd=rootfd);child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=rootfd);fds.append(child);s=os.fstat(child);need(s.st_uid==s.st_gid==1000 and stat.S_IMODE(s.st_mode)==0o700 and os.listdir(child)==[],'actual empty private child');rows.append(identity(target/name,s,[]))
  s=os.fstat(rootfd);need(s.st_uid==s.st_gid==1000 and stat.S_IMODE(s.st_mode)==0o700 and sorted(os.listdir(rootfd))==['owner-evidence','owner-work'],'actual private base');rows.insert(0,identity(target,s,['owner-evidence','owner-work']))
  for expected in d['parent_ancestry']:
   s=os.lstat(expected['path']);need((s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid)==tuple(expected[k] for k in ['device','inode','mode','uid','gid']),'same parent ancestry after creation')
  need(all(not os.path.lexists(q[k]) for k in ['attempt_root','common_exclusion_path','lease_path','output_root','evidence_root']),'all driver-owned record/output/capture children absent')
  result=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_ACTUAL_ORDINARY_SOURCE_PREPARATION_NAMESPACE_INITIALIZATION_ONLY',request=d['request'],owner=d['image_entry_owner'],host_control_owner=d['host_control_owner'],identities=rows,ancestry=d['parent_ancestry'],physical=d['current_physical_acceptance'],postreturn=d['postreturn'],grant=ref(grant_path),source=ref(__file__),no_live_query_or_owner_admission=True)
  receipt=write(output,result);print(json.dumps(receipt,sort_keys=True));return receipt
 finally:
  for fd in reversed(fds):os.close(fd)
if __name__=='__main__':
 need(len(sys.argv)==3,'exact root grant path and SHA required');run(Path(sys.argv[1]),sys.argv[2])
