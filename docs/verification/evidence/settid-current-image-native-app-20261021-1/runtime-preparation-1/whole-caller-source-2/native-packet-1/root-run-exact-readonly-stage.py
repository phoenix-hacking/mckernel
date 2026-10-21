import argparse, hashlib, importlib.util, json, os, resource, signal, subprocess, time
from pathlib import Path

ap=argparse.ArgumentParser();ap.add_argument('--index',type=int,choices=range(3),required=True);ap.add_argument('--metadata-hash');ap.add_argument('--commands-file');ap.add_argument('--commands-sha256');a=ap.parse_args();assert bool(a.commands_file)==bool(a.commands_sha256)
RG=Path('/home/holden/mckernel-work/host-preparation/fresh-full-terminal-generator-path-independent-review-20261019-1')
cp=Path(a.commands_file) if a.commands_file else RG/'EXACT-FIRST-THREE-ROOT-COMMANDS.json';assert hashlib.sha256(cp.read_bytes()).hexdigest()==(a.commands_sha256 or '63e715c8b5539d11f04ea1bfc3cf7f0bd6d4b004d85a813a334c20264bce036a')
data=json.loads(cp.read_bytes());op=data['operations'][a.index];profile=data['profiles'][op['profile']];argv=list(op['argv_template'])
hp=Path('/home/holden/mckernel-work/host-preparation/four-callback-affinity-image-preparation-20261019-1/failure-terminal-preparation-1/root-case-critical-capture-failed12.py')
assert hashlib.sha256(hp.read_bytes()).hexdigest()=='5c884624b748b862aa1b48a369d3ee758f311ab6c70e82f1346c93d6b478b10d'
spec=importlib.util.spec_from_file_location('pinned_capture_primitives',str(hp));h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());assert state.get('stop_reason') is None and state['last_rate_limits']['primary']['usedPercent']<100
for root,floor in [('/home/holden',17179869184),('/home/holden/mckernel-work/scratch',12884901888)]:
 v=os.statvfs(root);assert v.f_bavail*v.f_frsize>=floor+679477248
release=Path(data['release']['path']);raw=release.read_bytes();assert hashlib.sha256(raw).hexdigest()==data['release']['sha256'] and len(raw)==data['release']['bytes'];dest=Path(data['root_installed_release_path'])
if a.index==0:h.put(dest,raw)
else:assert dest.read_bytes()==raw
if a.index==2:
 assert a.metadata_hash and len(a.metadata_hash)==64
 pos=argv.index('BIND_GENUINE_SUMMARY_FIVE_HASHFILE_SHA256');argv[pos]=a.metadata_hash
 assert hashlib.sha256(Path(argv[argv.index('--expected-hashes')+1]).read_bytes()).hexdigest()==a.metadata_hash
assert not any(x.startswith('BIND_') for x in argv)
os.umask(0o077);os.sched_setaffinity(0,{profile['cpu']});resource.setrlimit(resource.RLIMIT_FSIZE,(profile['stream_fsize'],profile['stream_fsize']))
outp=Path(op['stdout_path']);errp=Path(op['stderr_path']);sp=Path(op['status_path']);outp.parent.mkdir(mode=0o700,exist_ok=True)
h.write(Path(str(sp)+'.command.json'),dict(argv=argv,role=op['role'],policy=h.ref(cp),profile=profile));t=time.monotonic();error=None;rc=None;joined=False
with outp.open('xb') as out,errp.open('xb') as err:
 c=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True);start=None
 try:start=h.start(c.pid)
 except BaseException as e:error='child_identity_unavailable '+repr(e)
 h.write(Path(str(sp)+'.child.json'),dict(pid=c.pid,start=start,pgid=c.pid,argv=argv))
 try:rc=c.wait(timeout=profile['parent_wall_seconds']);joined=True
 except subprocess.TimeoutExpired:
  error='parent_wall_timeout'
  try:
   assert start is not None and h.start(c.pid)==start;os.killpg(c.pid,signal.SIGTERM)
   deadline=t+profile['parent_wall_seconds']+profile['parent_kill_grace_seconds']
   try:rc=c.wait(timeout=max(0.01,(deadline-time.monotonic())/2));joined=True
   except subprocess.TimeoutExpired:
    assert h.start(c.pid)==start;os.killpg(c.pid,signal.SIGKILL);rc=c.wait(timeout=max(0.01,deadline-time.monotonic()));joined=True
  except BaseException as e:error+='; retirement_uncertain '+repr(e)
 h.write(Path(str(sp)+'.direct-join.json'),dict(pid=c.pid,start=start,argv=argv,returncode=rc,direct_child_joined=joined,observer_error=error,elapsed_seconds=time.monotonic()-t))
 try:os.killpg(c.pid,0);absent=False
 except ProcessLookupError:absent=True
 except PermissionError:absent=False
 if not joined or not absent or 'retirement_uncertain' in (error or ''):
  h.write(sp,dict(role=op['role'],argv=argv,pid=c.pid,start=start,returncode=rc,direct_child_joined=joined,process_group_absent=absent,observer_error=error or 'process_group_retirement_uncertain',elapsed_seconds=time.monotonic()-t,streams=None,stdout_path=str(outp),stderr_path=str(errp)))
  raise RuntimeError('retirement uncertain; capture bytes not inspected; preserve identities and stop')
 out.flush();err.flush();os.fsync(out.fileno());os.fsync(err.fileno());held={k:h.ident(os.fstat(f.fileno())) for k,f in [('stdout',out),('stderr',err)]}
streams={}
for key,p in [('stdout',outp),('stderr',errp)]:
 with p.open('rb') as f:
  before=h.ident(os.fstat(f.fileno()));assert before==held[key]==h.ident(p.stat()) and before['size']<=profile['stream_fsize'];digest=hashlib.sha256(f.read()).hexdigest();assert before==h.ident(os.fstat(f.fileno()))==h.ident(p.stat());streams[key]=dict(path=str(p),sha256=digest,metadata=before)
row=dict(role=op['role'],argv=argv,pid=c.pid,start=start,returncode=rc,direct_child_joined=joined,process_group_absent=absent,observer_error=error,elapsed_seconds=time.monotonic()-t,streams=streams);h.write(sp,row)
print(json.dumps(dict(role=op['role'],returncode=rc,direct_child_joined=joined,process_group_absent=absent,elapsed_seconds=row['elapsed_seconds'],status=str(sp),status_sha256=h.digest(sp))))
assert joined and rc==0 and absent and error is None and streams['stderr']['metadata']['size']==0
