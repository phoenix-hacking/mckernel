"""Finite closed first HOSTSDK cfg(MODULE) compiler failure text export; no binaries/workloads."""
from pathlib import Path
import gzip,hashlib,json,os,resource,stat,tarfile,time
O=Path(__file__).resolve().parent;H=Path('/home/holden/mckernel-work/host-preparation');B=H/'phase5-host-fork-adoption-opt-in-20261020-1'
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

authority=json.loads(read(O/'CLOSED-CASE-AUTHORITY.json'))
assert authority['status']=='CLOSED_FIRST_COMPILER_FAILURE_AND_POSITIVE_PHYSICAL_BOUND'
for key in ('compiler_failure_review','positive_physical_review','outer_closed_status','driver_receipt'):
 r=authority[key];assert ref(Path(r['path']))==r
outer=json.loads(read(Path(authority['outer_closed_status']['path'])))
assert outer['returncode']==1 and outer['direct_child_joined'] and outer['process_group_absent'] and outer['observer_error'] is None
receipt=json.loads(read(Path(authority['driver_receipt']['path'])))
assert receipt['status']=='FAIL' and receipt['make_returncode']==2
artifact_state=json.loads(read(O/'BINARY-ARTIFACT-STATE.json'))
assert artifact_state['produced_module_descriptors']==[]
for row in artifact_state['prospective_modules']:assert not os.path.lexists(row['path']) and row['descriptor'] is None
absence=json.loads(read(O/'ABSENT-PROSPECTIVE-TEXT.json'))
for row in absence['rows']:assert not os.path.lexists(row['path'])
rows=json.loads(read(O/'SELECTION.json'));assert len(rows)==51 and sum(x['bytes'] for x in rows)==256008
selected={r['path']:(Path(r['path']),r['member']) for r in rows};assert len(selected)==len(rows)
assert all(p.suffix not in {'.ko','.o'} for p,member in selected.values())
expected={row['path']:row for row in rows}
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
   digest=reader.h.hexdigest();file_authority=expected.get(str(p))
   if file_authority:assert digest==file_authority['sha256'] and file_authority.get('bytes',file_authority.get('size',reader.n))==reader.n
   copied.append(dict(source=str(p),member=member,sha256=digest,bytes=reader.n,mode=oct(info.mode)))

assert archive.stat().st_size<32<<20

manifest=dict(schema='mckernel.closed-first-host-sdk-cfg-module-failure-text-export.v1',scope='Functional OS/apps plus Rust cutover; exact original failedHOSTSDK case text and separate positivephysical proof only. No compile/module/native/default/ACK acceptance.',archive=ref(archive),files=copied,compiler_failure_review=authority['compiler_failure_review'],positive_physical_review=authority['positive_physical_review'],original_outer_returncode=1,original_make_returncode=2,prospective_module_states=artifact_state['prospective_modules'],descriptor_only_produced_modules=[],retained_intermediate_metadata_only=artifact_state['retained_intermediate_metadata_only'],binary_objects_copied=False,full_source_or_toolchain_inputs_copied_or_rehashed=False,compiler_root_guest_runs_by_exporter=0,elapsed_seconds=time.monotonic()-start,exporter=ref(Path(__file__)))
with (O/'manifest.json').open('x') as f:json.dump(manifest,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(dict(files=len(copied),bytes=sum(x['bytes'] for x in copied),manifest_sha256=ref(O/'manifest.json')['sha256'],module_descriptors=0,absent_modules=3)))
