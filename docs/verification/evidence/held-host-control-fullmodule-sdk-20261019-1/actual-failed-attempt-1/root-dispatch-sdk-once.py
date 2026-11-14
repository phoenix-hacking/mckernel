import os,json,time,resource,subprocess,hashlib
from pathlib import Path
H=Path(__file__).parent
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(x):return (json.dumps(x,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode()
draw=(H/'ROOT-EXACT-SDK-DISPATCH-DATA-PENDING.json').read_bytes()
assert sha(draw)=='7762b28a83c794ca5b7ba879e34e0edd7b1b45fc6645537e440086a5330f4da9'
d=json.loads(draw);raw=(H/'execution-release-FINAL-PAYLOAD.json').read_bytes();assert sha(raw)=='a709449e6b53e9313d09ef02e432e96d6311d1f58bc3ce6043e341b788f78a80'
v=json.loads(raw);assert raw==canonical(v)
r=json.loads((H/'ROOT-FINAL-EXECUTION-REVIEW-REF.json').read_bytes());rb=Path(r['path']).read_bytes();assert sha(rb)==r['sha256'];review=json.loads(rb)
assert review['decision']=='PASS_EXECUTION' and review['implementation_ownership'] is False and review['reviewer']!=v['author'] and review['reviewed_release_payload_sha256']==sha(raw)
s=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());assert s['phase']=='running' and not s.get('pause_reason') and s['last_rate_limits']['primary']['usedPercent']<97
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==v['boot_id']
storage={}
for key,path,floor in [('host','/home/holden/mckernel',17179869184),('scratch','/home/holden/mckernel-work/scratch',12884901888)]:
 f=os.statvfs(path);free=f.f_bavail*f.f_frsize;assert free>=floor+671088640;storage[key]=free
mem=int(next(z.split()[1] for z in Path('/proc/meminfo').read_text().splitlines() if z.startswith('MemAvailable:')))*1024;assert mem>=17179869184
op=d['operations'][0];p=d['profiles'][op['profile']];argv=list(op['argv_template']);assert argv[-1] is None
parent=Path(d['root_capture_parent']);assert not parent.exists() and not Path(d['root_installed_release_path']).exists()
assert resource.getrlimit(resource.RLIMIT_CPU)==(-1,-1) and os.environ.get('SUDO_ASKPASS')
v['execution_review']={'path':r['path'],'sha256':r['sha256']};release=canonical(v);Path(d['root_installed_release_path']).open('xb').write(release);argv[-1]=sha(release)
parent.mkdir(mode=0o700);(parent/'admission.json').open('x').write(json.dumps({'timestamp':time.time(),'storage':storage,'mem_available':mem,'usage':s['last_rate_limits']['primary']['usedPercent'],'latest_physical':v['latest_accepted_physical_predecessor'],'release_sha256':sha(release)},indent=2)+'\n')
def limits():
 os.sched_setaffinity(0,{p['cpu']});resource.setrlimit(resource.RLIMIT_AS,(p['address_space_limit_bytes'],)*2);resource.setrlimit(resource.RLIMIT_CPU,(resource.RLIM_INFINITY,)*2);resource.setrlimit(resource.RLIMIT_FSIZE,(p['stream_fsize'],)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
c=None;rc=None;error=None;start=None;absent=False;begin=time.time()
try:
 with Path(op['stdout_path']).open('xb') as out,Path(op['stderr_path']).open('xb') as err:
  c=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=True,preexec_fn=limits)
  z=Path('/proc/%d/stat'%c.pid).read_text();start=int(z[z.rfind(')')+2:].split()[19]);(parent/'child.json').open('x').write(json.dumps({'pid':c.pid,'start':start,'argv':argv,'timestamp':begin})+'\n');rc=c.wait()
except BaseException as e:
 error=repr(e)
 if c is not None:rc=c.wait()
if c is not None:
 try:os.killpg(c.pid,0)
 except ProcessLookupError:absent=True
streams={}
for k in ('stdout_path','stderr_path'):
 path=Path(op[k]);b=path.read_bytes();st=path.stat();streams[k]={'path':str(path),'sha256':sha(b),'bytes':len(b),'device':st.st_dev,'inode':st.st_ino,'mode':st.st_mode,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns}
record={'returncode':rc,'pid':None if c is None else c.pid,'start':start,'direct_child_joined':c is not None and c.returncode is not None,'process_group_absent':absent,'observer_error':error,'started_at':begin,'finished_at':time.time(),'elapsed_seconds':time.time()-begin,'argv':argv,'streams':streams}
Path(op['status_path']).open('x').write(json.dumps(record,indent=2)+'\n');print(json.dumps({k:record[k] for k in ('returncode','direct_child_joined','process_group_absent','observer_error','elapsed_seconds')}));raise SystemExit(0 if rc==0 and absent and error is None else 1)
