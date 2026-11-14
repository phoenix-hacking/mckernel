import json,os,time,hashlib,subprocess,resource
from pathlib import Path
W=Path(__file__).parent
sha=lambda b:hashlib.sha256(b).hexdigest()
def bound(ref):
 b=Path(ref['path']).read_bytes();assert sha(b)==ref['sha256'] and len(b)==ref['bytes'];return json.loads(b)
raw=(W/'ROOT-COMPILER-SELFRETIRE-CONTINUATION-DATA.json').read_bytes();assert sha(raw)=='1f574faabfa6e7d68785e80eec8a80a442a61213b6147e459aa9531cedd7dd32';d=json.loads(raw)
for k in ('owner','request','driver','profile','source_manifest','retirement_import_closure','frozen_index'):bound(d[k]) if k!='owner' and k!='driver' else None
for k in ('owner','driver'):
 r=d[k];b=Path(r['path']).read_bytes();assert sha(b)==r['sha256'] and len(b)==r['bytes']
peer={'path':'/home/holden/mckernel-work/host-preparation/current-guest-fullcrate-owner-independent-review-20261020-1/FINAL-FINITE-CRATE-SELFRETIREMENT-BOUNDARY-REVIEW.json','sha256':'3dc4479e25a90e632332c7eaf898c524ebf22807edc8ccb4c47f59cf9d300c41','bytes':13801};bound(peer);bound(d['prior_finite_compiler_source_review'])
physical={'path':'/home/holden/mckernel-work/host-preparation/held-host-control-fullmodule-independent-review-20261019-1/HELD-HOST-CONTROL-CORRECTED-SDK-FAILED-BUILD-ACTUAL-PHYSICAL-RETIREMENT-REVIEW.json','sha256':'0e3d62a04117f946470e736547cc3e29845b502f76395c587f7cf57290523e86','bytes':28173};bound(physical)
s=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());assert s['phase']=='running' and not s.get('pause_reason') and s.get('stop_reason') is None and s['last_rate_limits']['primary']['usedPercent']<97
assert resource.getrlimit(resource.RLIMIT_AS)==(-1,-1) and resource.getrlimit(resource.RLIMIT_CPU)==(-1,-1) and os.environ.get('SUDO_ASKPASS')
capacity={}
for label,p,floor,growth in [('host','/home/holden/mckernel',17179869184,671088640),('scratch','/home/holden/mckernel-work/scratch',12884901888,0)]:
 v=os.statvfs(p);free=v.f_bavail*v.f_frsize;assert free>=floor+growth+671088640;capacity[label]=free
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
