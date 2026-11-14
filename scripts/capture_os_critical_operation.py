"""Thin critical binding of accepted a6ce capture tail; no outer timeout or kill."""
import argparse,ast,hashlib,json,os,resource,stat,subprocess,sys,time
from pathlib import Path
BASE=Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/terminal-preparation-1/fresh-full-8b-amendment-1/run_fresh8b_capture2.py')
BASE_SHA='a6ce818b1eabea2d13ed811487b88b2b811a4abbdb7dbb6b2cd43058b400e2d1'
p=argparse.ArgumentParser();p.add_argument('--operation',required=True);p.add_argument('--sha256',required=True);a=p.parse_args()
raw=Path(a.operation).read_bytes();assert hashlib.sha256(raw).hexdigest()==a.sha256;op=json.loads(raw)
assert op['role'] in ('cleanup','postjoin') and op['cpu']==7 and op['stream_cap_bytes']==134217728
argv=op['argv'];assert isinstance(argv,list) and all(isinstance(x,str) for x in argv)
assert argv[argv.index('-c')+1]=='7' and '--fsize=134217728:134217728' in argv and '--cpu=unlimited:unlimited' in argv
assert resource.getrlimit(resource.RLIMIT_CPU)==(-1,-1), 'critical capture requires inherited unlimited CPU time'
assert op['profile']['outer_wall_kill'] is None and op['profile']['outer_grace_kill'] is None
assert op['profile']['required_inherited_cpu_limits']==[-1,-1] and op['profile']['cpu']==7
run=Path(op['capture_directory']);assert run.is_absolute() and '..' not in run.parts and not run.exists()
assert run.parent.is_dir() and not any(q.is_symlink() for q in (run.parent,*run.parent.parents))
assert os.getuid()==1000 and 7 in os.sched_getaffinity(0);os.umask(0o077);os.sched_setaffinity(0,{7})
source=BASE.read_bytes();assert hashlib.sha256(source).hexdigest()==BASE_SHA
text=source.decode();tree=ast.parse(text)
# Reuse exact reviewed writer; descriptor changes only its explicit profile cap constant.
for name in ('write','descriptor'):
 node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
 segment=ast.get_source_segment(text,node)
 if name=='descriptor':
  assert segment.count('33554432')==1;segment=segment.replace('33554432','134217728')
 exec(compile(segment,str(BASE),'exec'),globals())
def wait_with_progress(child, run, pid, proc_start, start):
 """Nonterminal hints only; the same direct child must still be joined.

 The cleanup contract emits its quarantine JSON as the first stdout line.
 Inspect only that bounded prefix; never infer root-lock ownership from it.
 Two exclusive evidence files and two flushed lines bound progress output.
 Progress I/O failure must not abandon the owning capture or its direct wait.
 """
 def progress(event):
  record=dict(schema='capture-progress.v1',event=event,terminal=False,
              direct_child_joined=False,release_authorized=False,pid=pid,
              proc_start_ticks=proc_start,capture_directory=str(run),
              elapsed_seconds=time.monotonic()-start)
  name='progress-'+event.lower()+'.json'
  written=False
  try:
   write(name,record)
   written=True
  except OSError:
   # Tagged stderr remains a best-effort independent visibility route.
   pass
  record['progress_path']=str(run/name)
  record['progress_record_written']=written
  try:
   print('CAPTURE_PROGRESS '+json.dumps(record,sort_keys=True),file=sys.stderr,flush=True)
  except OSError:
   pass
 progress('CHILD_JOIN_PENDING')
 reported=False
 while True:
  try:
   return child.wait(timeout=1.0)
  except subprocess.TimeoutExpired:
   if reported:
    continue
   fd=None
   try:
    fd=os.open(run/'stdout',os.O_RDONLY|os.O_NOFOLLOW)
    raw=os.read(fd,4096)
    # Only a complete first JSON line with the exact marker is an observation.
    first,sep,_=raw.partition(b'\n')
    marker=json.loads(first) if sep else None
    observed=isinstance(marker,dict) and marker.get('status')=='QUARANTINED_ROOT_LOCK_HELD'
   except (OSError,ValueError,UnicodeError,RecursionError):
    observed=False
   finally:
    if fd is not None:
     os.close(fd)
   if observed:
    reported=True
    progress('QUARANTINE_MARKER_OBSERVED')

# Only the old admission is omitted. Directwait->streamclose->group->FDhash tail is reused.
start=text.index("stdout=(run/'stdout').open('xb')")
end=text.index('def descriptor(name):',start)
status_start=text.index("status=dict(status='PASS' if rc==0",end)
tail=text[start:end]+text[status_start:]
# Typed CPU label and required direct-join field spelling; no sequencing or capture changes.
tail=tail.replace('cpu6_released','cpu7_released').replace('direct_joined=True','direct_child_joined=True')
# Preserve the accepted terminal tail verbatim except this direct-wait call.
wait_anchor='rc=child.wait();elapsed=time.monotonic()-start'
assert tail.count(wait_anchor)==1
tail=tail.replace(wait_anchor,'rc=wait_with_progress(child,run,pid,proc_start,start);elapsed=time.monotonic()-start')
proposal={'command':argv};run.mkdir(mode=0o700)
write('case-binding.json',dict(operation_path=a.operation,operation_sha256=a.sha256,base_path=str(BASE),base_sha256=BASE_SHA,profile=op['profile'],role=op['role'],cpu=7))
exec(compile(tail,str(BASE)+'::<bound capture tail>','exec'),globals())
if rc!=0:raise SystemExit(rc)
