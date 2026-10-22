"""Cold actual observer-main metadata soft-AS check; no root/Docker/census.
Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Only unavailable physical/release edges are mocked; metadata soft-AS512MiB real.
"""
from pathlib import Path
from contextlib import ExitStack
from unittest.mock import patch
import contextlib,copy,hashlib,io,json,os,resource,sys,types,traceback
D=Path(__file__).resolve().parent;B=D/'bound-current-controller-source-5'
def load(p):return json.loads(Path(p).read_bytes())
def mod(p,name):
 m=types.ModuleType(name);m.__file__=str(p);exec(compile(Path(p).read_bytes(),str(p),'exec'),m.__dict__);return m
def identity(p):
 import stat
 p=Path(p);s=p.lstat();v=dict(path=str(p),device=s.st_dev,inode=s.st_ino,mode=oct(stat.S_IMODE(s.st_mode)),uid=s.st_uid,gid=s.st_gid,size=s.st_size,nlink=s.st_nlink)
 if p.is_file():v['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
 return v
def forbidden(*a,**kw):raise AssertionError('no subprocess/root/cleanup in cold metadata fixture')
def main():
 o=mod(B/'observe_current_launcher_retirement.py','actual_cold_current_observer')
 case=load(B/'LAUNCHER-CASE-STATIC.json');proof=load(case['controller_proof']['path']);owner=load(proof['roles']['owner']['path']);item=owner['terminal_container_info']
 # Do not load the large request/toolchain or run earlier positive/negative tests.
 fixture=D/'TEST_ONLY-cold-observer-metadata-512m-1';fixture.mkdir();o.OUTPUT=fixture/'observation';dummy=fixture/'dummy-mutex';dummy.write_bytes(b'');ds=dummy.stat()
 rootlock=None;oldtrace=sys.gettrace();installed=[];edges=[];real_open=os.open;real_setrlimit=resource.setrlimit;inherited_hard=resource.getrlimit(resource.RLIMIT_AS)[1]
 lock=dict(path='SET_AT_REAL_ENGINE_IMPORT',device=27,inode=4,uid=0,gid=0,mode='0o644',nlink=1,size=0,sha256=hashlib.sha256(b'').hexdigest())
 mount=dict(target=str(o.ROOT),uuid='2a5768c8-718d-4914-bdc0-6b32c5a92a52',fstype='ext4',options='rw,nodev,nosuid');mountbytes=json.dumps(dict(filesystems=[mount])).encode()
 def install(m):
  nonlocal rootlock
  rootlock=m.ROOT_LOCK;lock['path']=str(rootlock);original_identity=m.identity;original_observe=m.observe_identity
  def eid(s):return (27,4)if(s.st_dev,s.st_ino)==(ds.st_dev,ds.st_ino)else original_identity(s)
  def observe(p):return copy.deepcopy(lock)if Path(p)==rootlock else original_observe(Path(p))
  m.identity=eid;m.observe_identity=observe;m.census=lambda:True;m.docker=lambda argv:json.dumps([item]).encode();m.metadata_inventory=lambda p:[identity(p)];installed.append(True);edges.extend(['ROOT_MUTEX','LIVE_MOUNT_DOCKER','PROCESS_CENSUS','FULL_LIVE_METADATA_INVENTORY'])
  print('COLD_PHASE real-engine-installed soft-AS='+str(resource.getrlimit(resource.RLIMIT_AS)),flush=True)
 def trace(frame,event,arg):
  if frame.f_code.co_filename!=str(B/'observe_current_launcher_retirement.py'):return None
  if event=='line'and 'm'in frame.f_locals and not installed:install(frame.f_locals['m']);sys.settrace(None);return None
  return trace
 def open_mock(path,flags,*a,**kw):
  if rootlock is not None and str(path)==rootlock.name and kw.get('dir_fd')is not None:return real_open(dummy,flags)
  return real_open(path,flags,*a,**kw)
 def limits(kind,pair):
  if kind==resource.RLIMIT_AS:
   assert pair[0]==536870912 and pair[1]==2147483648
   real_setrlimit(kind,(536870912,inherited_hard));return
  real_setrlimit(kind,pair)
 def command(argv,limit,retain):
  if argv[0]=='/usr/bin/findmnt':return mountbytes
  if 'inspect'in argv:return json.dumps([item]).encode()
  if 'ps'in argv:return b''
  raise AssertionError('unexpected mock command')
 print('COLD_PHASE start inherited-AS='+str(resource.getrlimit(resource.RLIMIT_AS)),flush=True)
 with ExitStack()as stack:
  for owner_obj,name,value in [(o.os,'getuid',lambda:0),(o.os,'geteuid',lambda:0),(o.os,'open',open_mock),(o.resource,'setrlimit',limits),(o.fcntl,'flock',lambda *a:None),(o,'validate_observation_release',lambda *a:edges.append('UNAVAILABLE_ROOT_RELEASE')),(o,'observed_command',command),(o.subprocess,'Popen',forbidden),(o.subprocess,'run',forbidden)]:stack.enter_context(patch.object(owner_obj,name,value))
  try:
   sys.settrace(trace)
   o.main(['--git-commit','1'*40,'--git-tree','2'*40,'--observation-release','TEST_ONLY_UNAVAILABLE','--observation-release-sha256','0'*64])
  finally:sys.settrace(oldtrace)
 assert installed and load(o.OUTPUT/'cleanup-release-draft.json')['status']=='NOT_RELEASED'
 observer_raw=(B/'observe_current_launcher_retirement.py').read_bytes()
 report=dict(observer=dict(path=str(B/'observe_current_launcher_retirement.py'),sha256=hashlib.sha256(observer_raw).hexdigest(),bytes=len(observer_raw)),scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_COLD_ACTUAL_OBSERVER_MAIN_REAL_METADATA_SOFT_AS512MiB_FIXTURE_ONLY',soft_as_bytes=536870912,hard_as_bytes=inherited_hard,maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,root_operations=0,Docker_commands=0,proc_censuses=0,mocked_edges=sorted(set(edges)),resource_setrlimit_mocked=False,hard_limit_mapping='Original2GiB Docker hard edge capped at inherited1GiB; all Docker/process command edges mocked. Real metadata soft512MiB applied.',runtime_release=None,physical_clearance=False)
 (D/'COLD-OBSERVER-METADATA-512MiB-RESULT.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True)
if __name__=='__main__':main()
