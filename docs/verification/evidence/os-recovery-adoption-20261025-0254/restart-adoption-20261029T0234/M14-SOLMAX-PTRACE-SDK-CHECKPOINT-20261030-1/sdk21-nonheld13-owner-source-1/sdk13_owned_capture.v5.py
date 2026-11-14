"""One fixed ordinary three-command envelope; never launches a build or guest."""
from pathlib import Path
import ast,hashlib,json,os,resource,signal,stat,subprocess,time
D=Path(__file__).resolve().parent
PROFILE_SHA = 'fcba8c9b29ac9d38b95ab9ac5e2f37a333ef3f0678131b4779a443aa07499982'
FIELDS=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
stopping=False

def need(ok,message):
 if not ok:raise ValueError(message)
def write(path,value):
 fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 with os.fdopen(fd,'w') as f:json.dump(value,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
def hashed(path,maximum):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  a=os.fstat(fd);need(stat.S_ISREG(a.st_mode) and a.st_nlink==1 and a.st_size<=maximum,'bounded regular singlelink FD')
  h=hashlib.sha256();size=0
  while True:
   block=os.read(fd,65536)
   if not block:break
   size+=len(block);need(size<=maximum,'capture growth');h.update(block)
  b=os.fstat(fd);c=path.lstat();need(all(getattr(a,k)==getattr(b,k)==getattr(c,k) for k in FIELDS) and size==b.st_size,'stable FD metadata')
  return dict(path=str(path),sha256=h.hexdigest(),device=b.st_dev,inode=b.st_ino,uid=b.st_uid,gid=b.st_gid,mode=oct(stat.S_IMODE(b.st_mode)),nlink=b.st_nlink,size=size,mtime_ns=b.st_mtime_ns,ctime_ns=b.st_ctime_ns)
 finally:os.close(fd)
def stop(signum,frame):
 global stopping
 if stopping:return
 stopping=True;signal.setitimer(signal.ITIMER_REAL,0)
 raise InterruptedError('ordinary envelope signal '+str(signum))
def cpu_used():
 a=resource.getrusage(resource.RUSAGE_SELF);b=resource.getrusage(resource.RUSAGE_CHILDREN)
 return a.ru_utime+a.ru_stime+b.ru_utime+b.ru_stime

# Reuse exactly one reviewed read-only procfs census, not its Docker transport.
CENSUS_SOURCE=Path('/home/holden/mckernel-work/host-preparation/current-host-rust-pair-sdk-20261019-1/capsule/scripts/native_rust_exact_build_container_owner.py')
CENSUS_SHA='96d17547bfc71454d54e95a705138cc9b26faa1e2cafc34105c9ed8d5a68f4d1'
_CENSUS=None
STOP_SIGNALS={signal.SIGTERM,signal.SIGINT,signal.SIGALRM}

def members(pgid):
 global _CENSUS
 if _CENSUS is None:
  raw=CENSUS_SOURCE.read_bytes();need(hashlib.sha256(raw).hexdigest()==CENSUS_SHA,'pinned accepted census source')
  tree=ast.parse(raw,str(CENSUS_SOURCE));cls=next(x for x in tree.body if isinstance(x,ast.ClassDef) and x.name=='Docker')
  fn=next(x for x in cls.body if isinstance(x,ast.FunctionDef) and x.name=='_surviving_group_members')
  namespace={'Path':Path};exec(compile(ast.Module(body=[fn],type_ignores=[]),str(CENSUS_SOURCE),'exec'),namespace);_CENSUS=namespace[fn.name]
 context=type('CensusContext',(),{})();context.client_retirement_unproven=False
 found=_CENSUS(context,pgid)
 need(not context.client_retirement_unproven,'accepted census uncertainty')
 return sorted(found)

def process_start(pid):
 return int(Path('/proc/'+str(pid)+'/stat').read_text().rsplit(')',1)[1].split()[19])

def terminal_unreaped(process):
 # WNOWAIT keeps our creator PID/PGID reserved until every group signal ends.
 return os.waitid(os.P_PID,process.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT) is not None

def wait_terminal(process,seconds):
 deadline=time.monotonic()+seconds
 while not terminal_unreaped(process):
  if time.monotonic()>=deadline:return False
  time.sleep(min(0.01,max(0,deadline-time.monotonic())))
 return True

def owned_capture(command,path,wall_seconds,limits,started_reader=process_start,effect_gate=None):
 """Fixed ordinary child; errors always retire/join before stream FD reads.

 No signal is sent after reap. Unexpected descendants make this fixed-command
 envelope fail closed even if termination succeeds; their independent reaping
 is not invented. The caller's direct child remains unreaped while signalling.
 """
 global stopping
 process=None;birth=None;rc=None;direct=False;error=None;retirement_error=None;timed=False;unexpected=[];effect_boundary=None;begin=time.monotonic()
 outfd=os.open(path/'stdout',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:errfd=os.open(path/'stderr',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 except BaseException:os.close(outfd);raise
 with os.fdopen(outfd,'wb') as out,os.fdopen(errfd,'wb') as err:
  try:
   # A stop cannot interrupt fork->Popen ownership assignment. The child must
   # restore the old mask before exec so ordinary TERM remains effective.
   previous=signal.pthread_sigmask(signal.SIG_BLOCK,STOP_SIGNALS)
   try:
    def child_limits():
     signal.pthread_sigmask(signal.SIG_SETMASK,previous);limits()
    need(callable(effect_gate),'pre-effect authority gate missing')
    effect_boundary=effect_gate()
    process=subprocess.Popen(command['argv'],stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,preexec_fn=child_limits)
   finally:signal.pthread_sigmask(signal.SIG_SETMASK,previous)
   birth=started_reader(process.pid)
   write(path/'started.json',dict(pid=process.pid,start=birth))
   if not wait_terminal(process,wall_seconds):raise subprocess.TimeoutExpired(command['argv'],wall_seconds)
  except BaseException as exc:
   error=type(exc).__name__+': '+str(exc);timed=isinstance(exc,subprocess.TimeoutExpired)
  finally:
   if process is not None:
    # Suppress asynchronous re-entry throughout bounded retirement and direct
    # wait. A pending stop is observed after ownership is safely resolved.
    previous=signal.pthread_sigmask(signal.SIG_BLOCK,STOP_SIGNALS)
    if error is not None:stopping=True;signal.setitimer(signal.ITIMER_REAL,0)
    anchored=False
    try:
     terminal_unreaped(process);anchored=True
     group=members(process.pid);unexpected=[pid for pid in group if pid!=process.pid]
     if unexpected and error is None:error='unexpected fixed-command group members'
     if error is not None:
      try:os.killpg(process.pid,signal.SIGTERM)
      except ProcessLookupError:pass
      ended=wait_terminal(process,2)
      # While the creator is unreaped its numeric group cannot be reused.
      # Kill any still-present group before reaping; never signal it later.
      group=members(process.pid)
      if not ended or any(pid!=process.pid for pid in group):
       try:os.killpg(process.pid,signal.SIGKILL)
       except ProcessLookupError:pass
       need(wait_terminal(process,2),'owned creator did not terminate after KILL')
    except BaseException as exc:
     retirement_error=type(exc).__name__+': '+str(exc)
     # Only an unreaped known creator permits this group signal. Census
     # uncertainty does not grant authority over a reaped/reused PGID.
     if anchored:
      try:os.killpg(process.pid,signal.SIGKILL)
      except ProcessLookupError:pass
      except BaseException as kill_error:retirement_error+='; KILL '+repr(kill_error)
    finally:
     try:
      rc=process.wait(timeout=2);direct=True
      write(path/'direct-wait.json',dict(pid=process.pid,start=birth,returncode=rc,direct_child_joined=True))
     except BaseException as exc:retirement_error=(retirement_error or '')+'; direct wait '+repr(exc)
     finally:signal.pthread_sigmask(signal.SIG_SETMASK,previous)
  absent=False;remaining=[]
  if process is not None and direct:
   try:remaining=members(process.pid);absent=not remaining
   except BaseException as exc:retirement_error=(retirement_error or '')+'; final census '+repr(exc)
  # No process action follows direct wait; no potentially reused PGID is signalled.
  joined=dict(pid=process.pid if process else None,start=birth,returncode=rc,effect_boundary=effect_boundary,direct_child_joined=direct,group_absent=absent,remaining_group_members=remaining,unexpected_group_members=unexpected,timed_out=timed,error=error,retirement_error=retirement_error,seconds=time.monotonic()-begin)
  write(path/'direct-join.json',joined)
 # FD hashing happens only after direct join has been persisted and files closed.
 joined['closed_streams']=True
 joined['captures']={name:hashed(path/name,32<<20) for name in ('stdout','stderr')}
 return joined


# Inputs keep their reviewed identities; output captures still use hashed()
# above, including its mandatory single-link rule.
SOURCE_AUTHORITIES_SHA = '7d7bc649424de4a764205055b58281240a62e5655e6515b61c66dcfc47da0103'
_SOURCE_AUTH=None

def source_authorities():
 global _SOURCE_AUTH
 if _SOURCE_AUTH is None:
  raw=(D/'pinned-source-authorities-v2.json').read_bytes();need(hashlib.sha256(raw).hexdigest()==SOURCE_AUTHORITIES_SHA,'pinned source metadata authority')
  rows=json.loads(raw);pins=json.loads((D/'source-pins-v2.json').read_text())
  need(set(rows)=={r['path'] for r in pins} and len(rows)==34,'exact declared source paths')
  for row in pins:
   authority=rows[row['path']]
   need(authority['path']==row['path'] and authority['sha256']==row['sha256'] and authority['size']==row['bytes'],'source authority existing byte pins')
   need(authority['uid']==authority['gid']==1000 and type(authority['nlink']) is int and authority['nlink']>=1,'declared source ownership/link count')
  _SOURCE_AUTH=rows
 return _SOURCE_AUTH

def read_pinned_source(path,maximum):
 rows=source_authorities();need(str(path) in rows,'unknown pinned source path');authority=rows[str(path)]
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  a=os.fstat(fd);need(stat.S_ISREG(a.st_mode) and a.st_nlink>=1 and a.st_size<=maximum,'bounded regular pinned source FD')
  h=hashlib.sha256();size=0
  while True:
   block=os.read(fd,65536)
   if not block:break
   size+=len(block);need(size<=maximum,'source growth');h.update(block)
  b=os.fstat(fd);c=path.lstat();need(all(getattr(a,k)==getattr(b,k)==getattr(c,k) for k in FIELDS) and size==b.st_size,'stable source FD metadata')
  row=dict(path=str(path),sha256=h.hexdigest(),device=b.st_dev,inode=b.st_ino,uid=b.st_uid,gid=b.st_gid,mode=oct(stat.S_IMODE(b.st_mode)),nlink=b.st_nlink,size=size,mtime_ns=b.st_mtime_ns,ctime_ns=b.st_ctime_ns)
  need(row==authority,'exact declared pinned source identity/ownership/bytes')
  return row
 finally:os.close(fd)


def main():
 global stopping
 started=time.monotonic();profile_path=D/'EXECUTION-PROFILE-SOURCE-BOUND-v2.json';raw=profile_path.read_bytes();need(hashlib.sha256(raw).hexdigest()==PROFILE_SHA,'fixed profile SHA')
 p=json.loads(raw);need(os.getuid()==os.geteuid()==1000 and os.sched_getaffinity(0)=={7},'ordinary hardCPU7; CPU6 refused')
 need(resource.getrlimit(resource.RLIMIT_AS)==(1<<30,1<<30),'exact 1GiB AS envelope')
 need(resource.getrlimit(resource.RLIMIT_CPU)==(55,55),'exact55CPU whole envelope')
 need(resource.getrlimit(resource.RLIMIT_FSIZE)==(32<<20,32<<20),'exact32MiB file limit')
 need(resource.getrlimit(resource.RLIMIT_CORE)==(0,0),'core0')
 for number in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(number,stop)
 signal.setitimer(signal.ITIMER_REAL,max(0.1,54-(time.monotonic()-started)))
 pins_ref=p['source_pins'];pinraw=Path(pins_ref['path']).read_bytes();need(len(pinraw)==pins_ref['bytes'] and hashlib.sha256(pinraw).hexdigest()==pins_ref['sha256'],'source pin map')
 for r in json.loads(pinraw):
  row=read_pinned_source(Path(r['path']),2<<20);need(row['sha256']==r['sha256'] and row['size']==r['bytes'],'exact source/data pin '+r['path'])
 state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_text());used=state['last_rate_limits']['primary']['usedPercent'];need(used<100,'included usage guard')
 mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 need(mem>=p['RAM_min_available_bytes'],'RAM floor/reserve')
 N=D.parent;scratch=Path(p['capacity_measure_scratch_path']);need(N.stat().st_dev!=scratch.stat().st_dev,'HOST output volume distinct from scratch')
 for name in p['required_absent_paths']:need(not os.path.lexists(name),'fresh output absence '+name)
 O=Path(p['fresh_capture_root']);O.mkdir(mode=0o700)
 def capacity():
  growth=0
  for root in (D/'stage-launches-1',):
   total=count=0
   if root.exists():
    for f in root.rglob('*'):
     count+=1;need(count<=4096,'bounded ordinary output inventory');s=f.lstat();need(stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode),'ordinary output specialfile refused')
     if stat.S_ISREG(s.st_mode):total+=s.st_size
    need(total<=64<<20,'stage64MiB total cap')
   growth+=total
  captures=control=0
  for f in O.rglob('*'):
   s=f.lstat();need(stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode),'capture specialfile refused')
   if stat.S_ISREG(s.st_mode):
    if f.name in ('stdout','stderr'):need(s.st_size<=32<<20,'stream32MiB cap');captures+=s.st_size
    else:control+=s.st_size
  need(captures<=128<<20 and control<=2<<20,'wholecapture/control cap');growth+=captures+control
  hv=os.statvfs(N);sv=os.statvfs(scratch);host=hv.f_bavail*hv.f_frsize;sf=sv.f_bavail*sv.f_frsize
  need(host>=p['host_floor_bytes']+p['emergency_reserve_bytes']+max(0,p['host_total_growth_bytes']-growth),'HOSTfloor+remaininggrowth+640reserve')
  need(sf>=p['scratch_required_free_bytes'],'scratch readonlyfloor+640reserve')
  return dict(host_free_bytes=host,scratch_free_bytes=sf,allocated_envelope_bytes=growth)
 admission=capacity();write(O/'admission.json',dict(profile_sha256=PROFILE_SHA,cpu=7,usage_percent=used,mem_available_bytes=mem,capacity=admission,root_CPU7_grant_required_externally=True))
 records=[];failed=None
 try:
  for number,command in enumerate(p['per_command']):
   need(time.monotonic()-started<54 and cpu_used()<55,'whole work/CPU remainder');capacity()
   path=O/('%02d-%s'%(number,command['role']));path.mkdir(mode=0o700);write(path/'command.json',command)
   def limits():
    os.sched_setaffinity(0,{7});resource.setrlimit(resource.RLIMIT_CPU,(command['cpu_seconds'],command['cpu_seconds']))
   record=owned_capture(command,path,min(command['wall_seconds'],max(0.1,54-(time.monotonic()-started))),limits)
   record.update(role=command['role'],argv=command['argv'])
   write(path/'status.json',record);records.append(record)
   if record['returncode']!=0 or not record['direct_child_joined'] or not record['group_absent'] or record['timed_out'] or record['error'] or record['retirement_error'] or record['captures']['stderr']['size']!=0:failed='first command failure';break
  need(cpu_used()<=55,'whole55CPU cap');capacity()
 except BaseException as exc:failed=type(exc).__name__+': '+str(exc)
 finally:signal.setitimer(signal.ITIMER_REAL,0)
 result=dict(status='PASS_TWO_FIXED_ORDINARY_STEPS_NO_NATIVE' if failed is None and len(records)==2 else 'FAIL_STOPPED_PRESERVE_ALL',profile_sha256=PROFILE_SHA,records=records,error=failed,elapsed_seconds=time.monotonic()-started,total_CPU_seconds=cpu_used(),stage_or_guest_acceptance=False)
 write(O/'whole-result.json',result);print(json.dumps({k:result[k] for k in ('status','elapsed_seconds','total_CPU_seconds')}))
 return 0 if result['status'].startswith('PASS_') else 1
if __name__=='__main__':raise SystemExit(main())
