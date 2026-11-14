
import os,sys,json,stat,resource,hashlib
resource.setrlimit(resource.RLIMIT_AS,(268435456,268435456))
resource.setrlimit(resource.RLIMIT_CPU,(10,10))
assert os.sched_getaffinity(0)=={0}
ALLOW=set(["/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/cleanup-namespace-successor-preparation-1/cleanup_pass_image.py","/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/bound-terminal-source-1/capture_critical_two.py","/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/cleanup-namespace-successor-preparation-1/check_actual_fresh_preflight.py","/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/cleanup-namespace-successor-preparation-1/postjoin_readback.py","/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/cleanup-namespace-successor-preparation-1/OPERATION-cleanup.ACTUAL.json","/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/cleanup-namespace-successor-preparation-1/OPERATION-postjoin.ACTUAL.json","/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/cleanup-namespace-successor-preparation-1/cleanup-execution-release.json","/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/cleanup-namespace-successor-preparation-1/actual-cleanup-capture-1/stdout","/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/cleanup-namespace-successor-preparation-1/actual-cleanup-capture-1/stderr","/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/cleanup-namespace-successor-preparation-1/actual-cleanup-capture-1/status","/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/cleanup-namespace-successor-preparation-1/actual-cleanup-capture-1/status.json","/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/cleanup-namespace-successor-preparation-1/actual-cleanup-capture-1/command.json","/home/holden/mckernel-work/host-preparation/numa-insert-clear-image-successor-preparation-20261021-1/cleanup-namespace-successor-preparation-1/actual-cleanup-capture-1/operation.json","/home/holden/mckernel-work/scratch/numa-insert-clear-image-terminal-20261021-1.quarantine.json","/home/holden/mckernel-work/scratch/numa-insert-clear-image-terminal-20261021-1.journal.jsonl","/home/holden/mckernel-work/scratch/numa-insert-clear-image-terminal-20261021-1.plan.json","/home/holden/mckernel-work/scratch/numa-insert-clear-image-terminal-20261021-1.mutex","/home/holden/mckernel-work/scratch/numa-insert-clear-image-terminal-20261021-1.docker-logs.capture","/run/lock/mckernel-development.lock","/home/holden/mckernel/.git/os-autopilot/state.json","/home/holden/mckernel/AGENTS.md","/home/holden/mckernel/docs/verification/os-milestones-20260914/HANDOFF.md","/home/holden/mckernel/docs/verification/os-milestones-20260914/CURRENT.md"])
PIDS={2776191:40940896,2590193:37928121,2761632:40670225,2761633:40670229,2761636:40670236}
SEEN={}
def pst(pid):
 p='/proc/%d/stat'%pid
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
 try: b=os.read(fd,8192)
 finally: os.close(fd)
 fields=b.rsplit(b')',1)[1].split()
 return int(fields[19]),b.decode()
SELF=os.getpid(); BIRTH=pst(SELF)[0]; PIDS[SELF]=BIRTH
def meta(s):
 return {k:getattr(s,k) for k in ('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_atime_ns','st_mtime_ns','st_ctime_ns')}
def emit(v):
 v.update(reader_pid=SELF,reader_start_ticks=BIRTH)
 s=json.dumps(v,sort_keys=True)
 if len(s.encode())>1048576: s=json.dumps(dict(error='serialized-response-cap',reader_pid=SELF,reader_start_ticks=BIRTH))
 print(s,flush=True)
mem={}
with open('/proc/meminfo') as f:
 for line in f:
  k,v=line.split(':',1)
  if k=='MemAvailable': mem[k]=int(v.split()[0])*1024
free={p:os.statvfs(p).f_bavail*os.statvfs(p).f_frsize for p in ('/home/holden/mckernel','/home/holden/mckernel-work/scratch')}
assert mem['MemAvailable']>=16*1024**3+268435456
assert free['/home/holden/mckernel']>=16*1024**3 and free['/home/holden/mckernel-work/scratch']>=12*1024**3
emit(dict(status='DIAGNOSTIC_READER_READY_READ_ONLY',allowlist=sorted(ALLOW),pid_bindings=PIDS,mem_available=mem['MemAvailable'],free_bytes=free,cpu=sorted(os.sched_getaffinity(0)),as_limit=resource.getrlimit(resource.RLIMIT_AS),cpu_limit=resource.getrlimit(resource.RLIMIT_CPU),prior_transient_report=dict(pid=2776191,start_ticks=40940896,reported_exit=0,independently_verified=False),control_transient_identity='unresolved-preserve-any-census-refusal'))
def readone(e):
 p=e['path']; assert p in ALLOW and os.path.isabs(p) and '..' not in p.split('/')
 cap=int(e.get('bytes',131072)); assert 0<cap<=131072
 if e.get('stat_only'):
  return dict(path=p,metadata=meta(os.lstat(p))),0
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
 try:
  a=os.fstat(fd); assert stat.S_ISREG(a.st_mode)
  off=max(0,a.st_size-cap) if e.get('tail') else 0
  os.lseek(fd,off,0); data=os.read(fd,cap); z=os.fstat(fd)
 finally: os.close(fd)
 SEEN[p]=dict(offset=off,bytes=data,complete=(off==0 and len(data)>=a.st_size),metadata=meta(a))
 text=data.decode('utf-8','backslashreplace')
 if 'first_line' in e:
  first=int(e['first_line']); count=int(e.get('lines',100)); assert first>=1 and 0<count<=160
  text=''.join(text.splitlines(True)[first-1:first-1+count])
 textbytes=text.encode()
 output_truncated=len(textbytes)>32768
 if output_truncated: text=textbytes[:32768].decode('utf-8','backslashreplace')
 return dict(path=p,before=meta(a),after=meta(z),metadata_changed=meta(a)!=meta(z),offset=off,read_bytes=len(data),file_truncated=(off!=0 or len(data)<a.st_size),output_truncated=output_truncated,text=text),len(data)
for raw in sys.stdin:
 try:
  assert len(raw.encode())<=65536
  req=json.loads(raw); op=req['operation']
  if op=='exit':
   emit(dict(status='DIAGNOSTIC_READER_NORMAL_EXIT')); break
  elif op=='read':
   es=req['files']; assert isinstance(es,list) and len(es)<=16
   assert sum(int(e.get('bytes',131072)) for e in es if not e.get('stat_only'))<=1048576
   rows=[]; total=0
   for e in es:
    try:
     row,n=readone(e); total+=n; rows.append(row)
    except Exception as ex: rows.append(dict(path=e.get('path'),error=type(ex).__name__,message=str(ex)))
   emit(dict(operation=op,results=rows,total_read_bytes=total,coherent_snapshot=False))
  elif op=='bind_path':
   p=req['path']; evidence=req['evidence_path']
   assert os.path.isabs(p) and '..' not in p.split('/') and '*' not in p and '?' not in p
   assert evidence in SEEN and req['derivation']
   ALLOW.add(p)
   emit(dict(operation=op,path=p,evidence_path=evidence,derivation=req['derivation'],binding_only=True))
  elif op=='bind_pid':
   pid=int(req['pid']); birth=int(req['start_ticks']); evidence=req['evidence_path']
   assert evidence in SEEN and req['relationship'] and len(PIDS)<16 and int(req['depth'])<=4
   PIDS[pid]=birth
   emit(dict(operation=op,pid=pid,start_ticks=birth,evidence_path=evidence,relationship=req['relationship'],binding_only=True))
  elif op=='proc':
   ps=req['pids']; assert len(ps)<=16
   rows=[]
   for pid in ps:
    pid=int(pid); assert pid in PIDS
    row=dict(pid=pid,expected_start_ticks=PIDS[pid])
    try:
     before,rawstat=pst(pid); row['observed_start_ticks']=before
     assert before==PIDS[pid]
     row['stat']=rawstat
     for leaf in ('status','wchan','syscall','task/%d/children'%pid):
      p='/proc/%d/%s'%(pid,leaf)
      try:
       fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK)
       try:
        a=os.fstat(fd); assert stat.S_ISREG(a.st_mode); d=os.read(fd,16384); z=os.fstat(fd)
       finally: os.close(fd)
       row[leaf]=dict(text=d.decode('utf-8','backslashreplace'),before=meta(a),after=meta(z))
       SEEN[p]=dict(bytes=d,complete=True)
      except Exception as ex: row[leaf]=dict(error=type(ex).__name__,message=str(ex))
     after,_=pst(pid); row['start_ticks_after']=after; row['identity_consistent']=after==before==PIDS[pid]
    except Exception as ex: row['error']=type(ex).__name__; row['message']=str(ex)
    rows.append(row)
   emit(dict(operation=op,processes=rows,coherent_snapshot=False))
  else: raise ValueError('unknown-request-operation')
 except Exception as ex:
  emit(dict(error=type(ex).__name__,message=str(ex),request_rejected=True))
