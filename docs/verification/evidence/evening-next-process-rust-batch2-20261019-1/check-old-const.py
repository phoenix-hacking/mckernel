from pathlib import Path
import subprocess,resource,time,json,re,os,hashlib,signal
O=Path(__file__).parent
E=O/'checks-3'
records=[]
CAP_BYTES=32*1024**2

def limits(cap_bytes):
 os.sched_setaffinity(0,{7})
 for kind,n in [(resource.RLIMIT_CPU,30),(resource.RLIMIT_AS,1024**3),(resource.RLIMIT_FSIZE,cap_bytes),(resource.RLIMIT_CORE,0)]:
  resource.setrlimit(kind,(n,n))

def run(n,args,*,cap_bytes=CAP_BYTES,wall_seconds=35,kill_grace=2):
 assert re.fullmatch(r'[a-zA-Z0-9_-]+',n) and 0<cap_bytes<=CAP_BYTES
 assert 0<wall_seconds<=35 and 0<kill_grace<=2
 E.mkdir(exist_ok=True)
 t=time.monotonic();p=None;timed_out=False;cleanup=[]
 # Child-owned writes into regular files are subject to the child's FSIZE limit.
 # Exclusive creation preserves every prior attempt and never truncates evidence.
 with (E/(n+'.stdout')).open('xb') as out, (E/(n+'.stderr')).open('xb') as err:
  try:
   p=subprocess.Popen(args,stdout=out,stderr=err,preexec_fn=lambda:limits(cap_bytes),start_new_session=True)
   try:p.wait(timeout=wall_seconds)
   except subprocess.TimeoutExpired:
    timed_out=True
  finally:
   if p is not None and p.poll() is None:
    try:os.killpg(p.pid,signal.SIGTERM);cleanup.append('SIGTERM_process_group')
    except ProcessLookupError:cleanup.append('SIGTERM_group_already_gone')
    try:p.wait(timeout=kill_grace)
    except subprocess.TimeoutExpired:
     try:os.killpg(p.pid,signal.SIGKILL);cleanup.append('SIGKILL_process_group')
     except ProcessLookupError:cleanup.append('SIGKILL_group_already_gone')
     finally:p.wait()
   if p is not None:p.wait()
 # No parent PIPE buffering or parent rewrite of captured child output.
 captures={}
 for ext in ['stdout','stderr']:
  f=E/(n+'.'+ext);size=f.stat().st_size
  h=hashlib.sha256()
  with f.open('rb') as stream:
   for block in iter(lambda:stream.read(32768),b''):h.update(block)
  captures[ext]=dict(bytes=size,sha256=h.hexdigest(),within_cap=size<=cap_bytes,cap_reached=size>=cap_bytes)
 row=dict(label=n,argv=args,pid=p.pid,returncode=p.returncode,direct_child_joined=True,seconds=time.monotonic()-t,timed_out=timed_out,cleanup=cleanup,capture_method='direct regular-file child writes',cap_bytes_per_stream=cap_bytes,captures=captures)
 (E/(n+'.status.json')).write_text(json.dumps(row,indent=2)+'\n');records.append(row);(E/'commands.json').write_text(json.dumps(records,indent=2)+'\n')
 assert not timed_out and p.returncode==0 and all(x['within_cap'] and not x['cap_reached'] for x in captures.values()),(n,'STOP unexpected failure, retained file-backed streams')
 # Success reads at most the configured cap; no unsuccessful output is collected.
 return (E/(n+'.stdout')).read_bytes().decode()


def main():
 E.mkdir(exist_ok=False)
 rc='/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc'
 flags=['panic=abort','opt-level=2','debuginfo=2','code-model=large','relocation-model=static','no-redzone=yes','force-frame-pointers=yes','overflow-checks=off','force-unwind-tables=no','no-vectorize-loops','no-vectorize-slp','target-feature=-sse,-sse2,-sse3,-ssse3,-sse4.1,-sse4.2,-avx,-avx2,-fma']
 rf=[v for f in flags for v in ['-C',f]]
 for label,cfg in [('ordinary',[]),('tofu',['--cfg','enable_tofu'])]:
  run(label+'-affected-const-consumer',[rc,'--edition=2021','--crate-type=lib','-Awarnings']+cfg+rf+['--emit=obj',str(O/'old-const-consumer.rs'),'-o',str(E/(label+'.o'))])
 (E/'summary.json').write_text(json.dumps(dict(status='PASS_ACTUAL_OLD_CONST_AND_CONSUMER_COMPILE',commands=len(records),compile_selections=['ordinary','tofu'],actual_old_hash_detach_body=True,actual_old_const=True,actual_release_process_default_consumer=True,semantic_cases_replayed=0,production_C_ABI=False,full_crate=False,native=False),indent=2)+'\n')
 print('PASS affected old const/body and actual consumer compile TOFUoff/on;2 commands;0 semantic cases replayed')
if __name__=='__main__':main()
