# Root dispatcher only. Prepares genuine release then runs exact reviewed owner once.
import json,os,time,hashlib,subprocess,resource,types
from pathlib import Path
W=Path(__file__).parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def bound(ref):
 b=Path(ref['path']).read_bytes();assert sha(b)==ref['sha256'] and len(b)==ref['bytes'];return json.loads(b)
raw=(W/'ROOT-ONCE-DATA-EXECUTION-PENDING.json').read_bytes();assert sha(raw)=='fee43f8462f40ccd40c43737d8df4843e54e3bbede625f3f06a3ca543554654a';d=json.loads(raw)
for k in ('request','profile','source_manifest','release_DATA'):bound(d[k])
for k in ('owner','driver'):
 r=d[k];b=Path(r['path']).read_bytes();assert sha(b)==r['sha256'] and len(b)==r['bytes']
peer=d['independent_execution_boundary_review'];assert peer is not None,'genuine current caller-batch conditional review required';bound(peer)
physical=d['latest_accepted_physical_predecessor'];bound(physical)
bound(d['prior_finite_compiler_source_review'])
s=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());assert s['phase']=='running' and not s.get('pause_reason') and s.get('stop_reason') is None and s['last_rate_limits']['primary']['usedPercent']<100
assert resource.getrlimit(resource.RLIMIT_AS)==(-1,-1) and resource.getrlimit(resource.RLIMIT_CPU)==(-1,-1) and os.environ.get('SUDO_ASKPASS')
resource.setrlimit(resource.RLIMIT_FSIZE,(33554432,33554432))
capacity_owner=types.ModuleType('_exact_capacity_split_owner')
capacity_owner.__file__=d['owner']['path']
exec(compile(Path(capacity_owner.__file__).read_bytes(),capacity_owner.__file__,'exec'),capacity_owner.__dict__)
request=bound(d['request'])
engine,retirement=capacity_owner.load_transports(request)
capacity=capacity_owner.capacity_before_ownership(request,engine,retirement,'outer')
work=Path(request['work_root']);assert not work.exists();work.mkdir(mode=0o700)
for name in ('output','home','tmp'):(work/name).mkdir(mode=0o700)
mem=int(next(z.split()[1] for z in Path('/proc/meminfo').read_text().splitlines() if z.startswith('MemAvailable:')))*1024;assert mem>=19327352832
for p in d['original_three_records'].values():assert not os.path.lexists(p),p
out=Path(d['owner_capture_root']);assert not out.exists();out.mkdir(mode=0o700)
release=bound(d['release_DATA']);assert release['status']=='NOT_RELEASED';release.update(status='PASS',independent_execution_boundary_review=peer,prior_compiler_boundary=d['prior_finite_compiler_source_review'],latest_accepted_physical_predecessor=physical)
b=(json.dumps(release,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode();(W/'execution-release.json').open('xb').write(b)
argv=list(d['owner_argv']);assert argv[-1]=='GENUINE_ROOT_RELEASE_SHA256_REQUIRED';argv[-1]=sha(b)
(out/'admission.json').open('x').write(json.dumps({'epoch':time.time(),'usage':s['last_rate_limits']['primary']['usedPercent'],'capacity':capacity,'mem_available':mem,'latest_physical':physical,'release_sha256':sha(b)},indent=2)+'\n')
begin=time.time();c=None;start=None;rc=None;error=None;absent=False
try:
 with (out/'stdout').open('xb') as so,(out/'stderr').open('xb') as se:
  c=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=so,stderr=se,start_new_session=True)
  z=Path('/proc/%d/stat'%c.pid).read_text();start=int(z[z.rfind(')')+2:].split()[19]);(out/'child.json').open('x').write(json.dumps({'pid':c.pid,'start':start,'argv':argv,'epoch':begin})+'\n');rc=c.wait()
except BaseException as e:
 error=repr(e)
 if c is not None:rc=c.wait()
if c is not None:
 try:os.killpg(c.pid,0)
 except ProcessLookupError:absent=True
record={'returncode':rc,'pid':None if c is None else c.pid,'start':start,'direct_child_joined':c is not None and c.returncode is not None,'process_group_absent':absent,'observer_error':error,'started_at':begin,'finished_at':time.time(),'elapsed_seconds':time.time()-begin,'argv':argv}
(out/'direct-join.json').open('x').write(json.dumps(record,indent=2)+'\n');streams={}
for key in ('stdout','stderr'):
 p=out/key;raw=p.read_bytes();st=p.stat();streams[key]={'path':str(p),'sha256':sha(raw),'bytes':len(raw),'device':st.st_dev,'inode':st.st_ino,'mode':st.st_mode,'mtime_ns':st.st_mtime_ns,'ctime_ns':st.st_ctime_ns}
record['streams']=streams;(out/'status.json').open('x').write(json.dumps(record,indent=2)+'\n');print(json.dumps({k:record[k] for k in ('returncode','direct_child_joined','process_group_absent','observer_error','elapsed_seconds')}));raise SystemExit(0 if rc==0 and absent and error is None else 1)
