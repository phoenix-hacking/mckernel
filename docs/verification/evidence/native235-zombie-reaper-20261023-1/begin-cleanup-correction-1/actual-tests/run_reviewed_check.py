#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Only root-approved exact source/profile operations; no root/kernel/Docker/network.
"""
import sys,os,json,hashlib,resource,subprocess,selectors,time,signal
from pathlib import Path
O=Path(__file__).resolve().parent
R=Path('/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc')
expected_rustc='028fd60b' # Full exact digest recorded and verified against caller argument.
def run(label,argv,expected_source):
 source,sha=expected_source;assert hashlib.sha256(Path(source).read_bytes()).hexdigest()==sha
 assert hashlib.sha256(R.read_bytes()).hexdigest()==sys.argv[4]
 mem={r.split(':')[0]:r.split(':')[1].strip() for r in Path('/proc/meminfo').read_text().splitlines() if r.startswith('MemAvailable:')}
 assert int(mem['MemAvailable'].split()[0])*1024>18*1024**3
 record={'purpose':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Root-approved exact source actual-body regression, ordinary unprivileged CPU6 onejob.','argv':argv,'source':source,'source_sha256':sha,'rustc_sha256':sys.argv[4],'profile':{'AS':2*1024**3,'CPU_seconds':60,'wall_seconds':90,'kill_grace_seconds':6,'FSIZE':32*1024**2,'CORE':0,'NOFILE':256,'NPROC':'inherited','output_each':8*1024**2,'RUST_MIN_STACK':'2097152'},'fresh_memory':mem}
 (O/(label+'.command.json')).write_text(json.dumps(record,indent=2)+'\n')
 def limits():
  resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3));resource.setrlimit(resource.RLIMIT_CPU,(60,60));resource.setrlimit(resource.RLIMIT_FSIZE,(32*1024**2,32*1024**2));resource.setrlimit(resource.RLIMIT_CORE,(0,0));resource.setrlimit(resource.RLIMIT_NOFILE,(256,256))
 p=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,preexec_fn=limits,env=dict(os.environ,RUST_MIN_STACK='2097152'))
 (O/(label+'.started.json')).write_text(json.dumps({'pid':p.pid,'pgid':p.pid,'at':time.time()})+'\n')
 sel=selectors.DefaultSelector();streams={};counts={}
 for name in ['stdout','stderr']:
  stream=getattr(p,name);os.set_blocking(stream.fileno(),False);sel.register(stream,selectors.EVENT_READ,name);streams[name]=(O/(label+'.'+name)).open('xb');counts[name]=0
 start=time.monotonic();term_at=None;reason=None
 while sel.get_map() or p.poll() is None:
  now=time.monotonic()
  if term_at is None and now-start>90:reason='wall_timeout'
  if reason and term_at is None:
   try:os.killpg(p.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   term_at=now
  if term_at is not None and now-term_at>6:
   try:os.killpg(p.pid,signal.SIGKILL)
   except ProcessLookupError:pass
  for key,_ in sel.select(.1):
   chunk=os.read(key.fileobj.fileno(),65536)
   if not chunk:sel.unregister(key.fileobj);key.fileobj.close();continue
   n=key.data;remain=8*1024**2-counts[n];streams[n].write(chunk[:max(0,remain)]);counts[n]+=len(chunk)
   if counts[n]>8*1024**2:reason='output_cap'
 result=p.wait()
 for stream in streams.values():stream.close()
 try:os.killpg(p.pid,0);absent=False
 except ProcessLookupError:absent=True
 final={'exit':result,'elapsed':time.monotonic()-start,'stop_reason':reason,'direct_join':True,'streams_closed':True,'process_group_absent':absent,'output_bytes':counts,'maxrss_kib':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss}
 (O/(label+'.status.json')).write_text(json.dumps(final,indent=2)+'\n');print(label,json.dumps(final))
 return result==0 and absent and reason is None
mode=sys.argv[1];sha=sys.argv[2];number=sys.argv[3];source=str(O/(mode+'.rs'));binary=str(O/(mode+'-'+number));label='compile-'+mode+'-'+number
assert run(label,['taskset','-c','6',str(R),'--edition=2021','--test','-Ccodegen-units=1',source,'-o',binary],(source,sha))
assert run('run-'+mode+'-'+number,['taskset','-c','6',binary,'--test-threads=1','--nocapture'],(source,sha))
