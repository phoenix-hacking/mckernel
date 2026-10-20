"""Finite closed guest5 five-compiler success export; no binaries or workloads."""
from pathlib import Path
import gzip,hashlib,json,os,resource,stat,tarfile,time
O=Path(__file__).resolve().parent;B=O.parent;H=Path('/home/holden/mckernel-work/host-preparation');R=H/'phase5-current-consumer-compiler-independent-review-20261020-1'
assert os.geteuid()==1000 and os.sched_getaffinity(0)=={6}
assert resource.getrlimit(resource.RLIMIT_AS)==(1<<30,1<<30) and resource.getrlimit(resource.RLIMIT_CPU)==(30,30) and resource.getrlimit(resource.RLIMIT_FSIZE)==(32<<20,32<<20)
state=json.loads(Path('/home/holden/mckernel/.git/os-autopilot/state.json').read_bytes());assert state['phase']=='running' and state.get('stop_reason') is None and state['last_rate_limits']['primary']['usedPercent']<100
for path,floor in [(O,16<<30),(Path('/home/holden/mckernel-work/scratch'),12<<30)]:
 s=os.statvfs(path);assert s.f_bavail*s.f_frsize>=floor+(640<<20)+(64<<20)
assert int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024>=2<<30
fields=('st_dev','st_ino','st_uid','st_gid','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
def read(p):
 fd=os.open(p,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW|os.O_NOATIME)
 with os.fdopen(fd,'rb') as f:
  a=os.fstat(f.fileno());data=f.read(32<<20);z=os.fstat(f.fileno());n=Path(p).lstat();assert stat.S_ISREG(a.st_mode) and len(data)==a.st_size and all(getattr(a,k)==getattr(z,k)==getattr(n,k) for k in fields);return data
def ref(p):
 b=read(p);return dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
report=R/'ACTUAL-PHASE5-GUEST5-FAM-AND-PHYSICAL-REVIEW.json';assert ref(report)['sha256']=='28cde65c396fc20b4135accd85ccbf97c792e8b429c0a42911c09ab0ae34a562'
rows=json.loads(read(O/'SELECTION.json'));assert len(rows)==106 and sum(x['bytes'] for x in rows)==318586
selected={x['path']:(Path(x['path']),x['member']) for x in rows};assert len(selected)==len(rows)
expected={};objects=[]
def gather(v):
 if isinstance(v,dict):
  if isinstance(v.get('path'),str) and isinstance(v.get('sha256'),str):
   expected[v['path']]=v
   if v['path'].endswith('.o'):objects.append(v)
  for x in v.values():gather(x)
 elif isinstance(v,list):
  for x in v:gather(x)
gather(json.loads(read(report)));gather(json.loads(read(B/'guest-request-proposal.json')))
objects=json.loads(read(B/'compiler-attempt-1/work/output/build/current-guest-control-fullcrate-1/result.json'))['artifacts'];assert len(objects)==5 and objects[0]['production_FAM_layout']['words']==[164,168,4,4,8]
assert all(not p.name.endswith('.o') for p,m in selected.values())
start=time.monotonic();copied=[];archive=O/'evidence.tar.gz'
class Reader:
 def __init__(self,f):self.f=f;self.h=hashlib.sha256();self.n=0
 def read(self,n=-1):
  b=self.f.read(n);self.h.update(b);self.n+=len(b);return b
with archive.open('xb') as af,gzip.GzipFile(filename='',mode='wb',fileobj=af,mtime=0,compresslevel=6) as gz,tarfile.open(fileobj=gz,mode='w|') as tar:
 for p,member in selected.values():
  fd=os.open(p,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW|os.O_NOATIME)
  with os.fdopen(fd,'rb') as f:
   before=os.fstat(f.fileno());assert stat.S_ISREG(before.st_mode) and before.st_size<=32<<20
   info=tarfile.TarInfo(member);info.size=before.st_size;info.mode=stat.S_IMODE(before.st_mode);info.uid=before.st_uid;info.gid=before.st_gid;info.mtime=int(before.st_mtime)
   reader=Reader(f);tar.addfile(info,reader);after=os.fstat(f.fileno());named=p.lstat();assert all(getattr(before,k)==getattr(after,k)==getattr(named,k) for k in fields) and reader.n==before.st_size
   digest=reader.h.hexdigest();authority=expected.get(str(p))
   if authority:assert digest==authority['sha256'] and authority.get('bytes',authority.get('size',reader.n))==reader.n
   copied.append(dict(source=str(p),member=member,sha256=digest,bytes=reader.n,mode=oct(info.mode)))

assert archive.stat().st_size<32<<20
manifest=dict(schema='mckernel.closed-phase5-guest-five-object-FAM-compiler-evidence-export.v1',scope='Functional OS/apps plus Rust cutover; all5 real phase5 native/legacyRust and selected/fallback whole syscall plus whole process compilers, actualtypedFAM5wordELF and currentrunnable per-object symbol inventory passed. Combined genuine independent artifact/physical review retained. No actual relocatable/final link or activation/runtime acceptance.',archive=ref(archive),files=copied,descriptor_only_objects=objects,independent_actual_five_object_and_physical_review=ref(report),binary_objects_copied=False,full_source160_or176_toolchain_inputs_copied_or_rehashed=False,saved_symbol_table_independent_proof=False,compiler_or_test_or_root_or_guest_runs_by_exporter=0,elapsed_seconds=time.monotonic()-start,exporter=ref(Path(__file__)))
with (O/'manifest.json').open('x') as f:json.dump(manifest,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(dict(files=len(copied),bytes=sum(x['bytes'] for x in copied),manifest_sha256=ref(O/'manifest.json')['sha256'])))
