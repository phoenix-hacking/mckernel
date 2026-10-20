"""Selected closed HOST66 export; accepted stable-reader/tar family, no workloads."""
from pathlib import Path
import gzip,hashlib,json,os,resource,stat,tarfile,time
O=Path(__file__).resolve().parent;P=O.parent;D=P/'stage-preparation-1';Q=D/'native-packet-1';H=P.parents[1];R=H/'current-v6-composite-native-probe-independent-review-20261020-1'
assert os.geteuid()==1000 and os.sched_getaffinity(0)=={6}
assert resource.getrlimit(resource.RLIMIT_AS)==(1<<30,1<<30) and resource.getrlimit(resource.RLIMIT_CPU)==(30,30) and resource.getrlimit(resource.RLIMIT_FSIZE)==(32<<20,32<<20)
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());assert state['phase']=='running' and state.get('stop_reason') is None and state['last_rate_limits']['primary']['usedPercent']<100
for path,floor in [(O,16<<30),(Path('/home/holden/mckernel-work/scratch'),12<<30)]:
 s=os.statvfs(path);assert s.f_bavail*s.f_frsize>=floor+(640<<20)+(64<<20)
assert int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024>=2<<30
fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
rows=json.loads((O/'SELECTION.json').read_bytes());assert len(rows)==288 and sum(x['bytes'] for x in rows)==10446854
selected={x['path']:(Path(x['path']),x['member']) for x in rows};assert len(selected)==len(rows)
expected={}
def gather(v):
 if isinstance(v,dict):
  if isinstance(v.get('path'),str) and isinstance(v.get('sha256'),str):expected[v['path']]=v
  for x in v.values():gather(x)
 elif isinstance(v,list):
  for x in v:gather(x)
for p in [Q/'NATIVE-COHERENT-REVIEW-PACKET.json',R/'ACTUAL-HOST66-NATIVE-POSITIVE-PHYSICAL-RETIREMENT-REVIEW.json']:
 gather(json.loads(p.read_bytes()))
start=time.monotonic();copied=[];archive=O/'evidence.tar.gz'
class Reader:
 def __init__(self,f):self.f=f;self.h=hashlib.sha256();self.n=0
 def read(self,n=-1):
  b=self.f.read(n);self.h.update(b);self.n+=len(b);return b
with archive.open('xb') as af,gzip.GzipFile(filename='',mode='wb',fileobj=af,mtime=0,compresslevel=6) as gz,tarfile.open(fileobj=gz,mode='w|') as tar:
 for p,member in selected.values():
  fd=os.open(p,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
  with os.fdopen(fd,'rb') as f:
   before=os.fstat(f.fileno());assert stat.S_ISREG(before.st_mode) and before.st_size<=32<<20
   info=tarfile.TarInfo(member);info.size=before.st_size;info.mode=stat.S_IMODE(before.st_mode);info.uid=before.st_uid;info.gid=before.st_gid;info.mtime=int(before.st_mtime)
   reader=Reader(f);tar.addfile(info,reader);after=os.fstat(f.fileno());named=p.lstat();assert all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in fields) and reader.n==before.st_size
   digest=reader.h.hexdigest();authority=expected.get(str(p))
   if authority:assert digest==authority['sha256'] and authority.get('bytes',authority.get('size',reader.n))==reader.n
   copied.append(dict(source=str(p),member=member,sha256=digest,bytes=reader.n,mode=oct(info.mode)))

assert archive.stat().st_size<32<<20
stage=json.loads((D/'stage-launches-1/manifest.json').read_bytes())
manifest=dict(schema='mckernel.closed-host66-native-evidence-export.v1',scope='Functional OS/apps plus Rust cutover; closed HOST66 native captures preserved; semantic report remains separately authoritative; no positive CREATE_PPD/parentclose/ACK or library-default credit',archive=ref(archive),files=copied,descriptor_only_artifacts=dict(artifacts=stage.get('artifacts'),staging=stage.get('staging'),modules=stage.get('modules'),pair=stage.get('pair')),source_physical_acceptance=ref(R/'ACTUAL-HOST66-NATIVE-POSITIVE-PHYSICAL-RETIREMENT-REVIEW.json'),source_semantic_acceptance=ref(R/'ACTUAL-HOST66-NATIVE-STRICT-TWENTY-MODULE-ABI-AND-DRAIN-SEMANTIC-REVIEW.json'),semantic_status='PASS_STRICT20_NORMAL_MODULE_ABI_AND_BOUNDED_DRAIN_ONLY',original_failed64_evidence_ref=ref(R/'ACTUAL-COMPOSITE64-NATIVE-FAILURE-FINAL-PHYSICAL-RETIREMENT-REVIEW.json'),original_metadata_failures_retained_and_selected=True,stage_kernel_module_binaries_copied=False,full_toolchain_catalog_replayed_or_rehashed=False,guest_runs_by_exporter=0,elapsed_seconds=time.monotonic()-start,exporter=ref(Path(__file__)))
with (O/'manifest.json').open('x') as f:json.dump(manifest,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(dict(files=len(copied),bytes=sum(x['bytes'] for x in copied),manifest_sha256=ref(O/'manifest.json')['sha256'])))
