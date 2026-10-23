"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import hashlib,json,os,resource,signal,stat,time
D=Path(__file__).resolve().parent
PREVIOUS=D.parent/'failed-m05-495e-raw-1/RETENTION-MAP.json'
G=Path('/home/holden/mckernel-work/native-runs/m05h1/p/attempt-758924c510a14144a46fe53801f9e356')
W=Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/procfs-delete-native-successor-1/m05-first-v3-failure-1/coherent-successor-preparation-1/next-native-preparation-1/actual-M05-HOST-owner-capture-1')
FIELDS=('st_dev','st_ino','st_uid','st_gid','st_mode','st_size','st_nlink','st_mtime_ns','st_ctime_ns')
def identity(s):return {k:getattr(s,k) for k in FIELDS}
def write(p,v):
 with p.open('x') as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def main():
 start=time.monotonic();os.sched_setaffinity(0,{6});assert os.getuid()==os.geteuid()==1000
 for k,v in [(resource.RLIMIT_AS,2<<30),(resource.RLIMIT_CPU,30),(resource.RLIMIT_FSIZE,32<<20),(resource.RLIMIT_NOFILE,256),(resource.RLIMIT_CORE,0)]:resource.setrlimit(k,(v,v))
 def stop(*_):raise TimeoutError('retention wall60 exhausted')
 signal.signal(signal.SIGALRM,stop);signal.setitimer(signal.ITIMER_REAL,60)
 previous=json.loads(PREVIOUS.read_text());rows=[]
 for row in previous['files']:
  category=Path(row['retained']).parent.name;name=Path(row['retained']).name
  assert category in ('guest','capture');rows.append(((G if category=='guest' else W)/name,D/category/name))
 assert len(rows)==14 and sum(t.parent.name=='guest' for _,t in rows)==7
 assert os.statvfs(D).f_bavail*os.statvfs(D).f_frsize>=16*2**30+(16<<20)
 (D/'guest').mkdir(mode=0o700);(D/'capture').mkdir(mode=0o700)
 retained=[]
 with (D/'retention-journal.jsonl').open('x') as journal:
  for source,target in rows:
   before=source.lstat();assert stat.S_ISREG(before.st_mode) and before.st_uid==1000 and before.st_nlink==1 and before.st_size<=32<<20
   fd=os.open(source,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC);digest=hashlib.sha256();count=0
   with os.fdopen(fd,'rb') as inp,target.open('xb') as out:
    opened=os.fstat(inp.fileno())
    for block in iter(lambda:inp.read(65536),b''):
     count+=len(block);assert count<=32<<20;digest.update(block);out.write(block)
    out.flush();os.fsync(out.fileno());closed=os.fstat(inp.fileno())
   after=source.lstat();assert identity(before)==identity(opened)==identity(closed)==identity(after) and count==before.st_size
   target.chmod(0o600);assert target.stat().st_nlink==1 and target.stat().st_size==count
   # The finite retained copy is read back once to bind durable target bytes.
   assert hashlib.sha256(target.read_bytes()).hexdigest()==digest.hexdigest()
   row=dict(source=str(source),retained=str(target),sha256=digest.hexdigest(),bytes=count,source_identity=identity(after));retained.append(row);journal.write(json.dumps(row,sort_keys=True)+'\n');journal.flush();os.fsync(journal.fileno())
 result=json.loads((D/'guest/result.json').read_text());first=(D/'guest/first-failure.jsonl').read_text()
 receipt=dict(status='PASS_STABLE_ORDINARY_UID1000_FAILED_RUN_RETENTION',scope=__doc__,files=retained,native_acceptance=False,total_copies=len(retained),total_bytes=sum(x['bytes'] for x in retained),seconds=time.monotonic()-start,raw_result=result,raw_first_failure=first,previous_scheme=str(PREVIOUS),profile=dict(cpu=6,jobs=1,as_bytes=2<<30,cpu_seconds=30,wall_seconds=60,fsize_bytes=32<<20,nofile=256,core=0))
 write(D/'RETENTION-MAP.json',receipt);signal.setitimer(signal.ITIMER_REAL,0)
 print(json.dumps({k:receipt[k] for k in ('status','total_copies','total_bytes','seconds','raw_first_failure')}))
if __name__=='__main__':main()
