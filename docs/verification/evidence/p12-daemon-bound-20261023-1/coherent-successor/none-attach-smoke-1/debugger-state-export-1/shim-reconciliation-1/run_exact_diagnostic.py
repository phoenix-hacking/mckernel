"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Exact missing wait-converter reconciliation; no owner flags or cleanup calls."""
from pathlib import Path
import os,json,hashlib,subprocess,time,stat
D=Path(__file__).resolve().parent
PID=3502879
PYTHON_SHA='298a9e830ed52f36c299427565485d717d1ce0179c0597cc16560513eb780b06'
GDB_SHA='ee638c585936025f85a5f0f967e3929c9b36cb286d37ef662b23705682e31e2a'
OWNER='/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/source/native_diagnostic_container_owner.py'
OWNER_SHA='a15680bb1a50d05bc8ee167ca20b0c1d3e34b8dc5fc1d1bdd593f4dc4f31eefe'
SMOKE='/home/holden/mckernel/docs/verification/evidence/p12-daemon-bound-20261023-1/coherent-successor/none-attach-smoke-1/smoke.NOT-RELEASED.py'
SMOKE_SHA='f0b344881c1bf89c6db88102ef37ae072233c1d6dad0989bba0163d0de92abb1'
SCRIPT_SHA='c5fcab2c90219c4d84e142c5f14ad351e33ffbb060b7ef29237f2a76071746cf'
START=52840595
assert os.geteuid()==0
assert os.sched_getaffinity(0)=={7}
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def proc(allow_missing=False):
 try:raw=Path('/proc/%d/stat'%PID).read_text()
 except FileNotFoundError:
  if allow_missing:return {'pid':PID,'start':START,'positive_ENOENT':True,'state':'ABSENT'}
  raise
 p=raw.rpartition(') ')[2].split();assert int(p[19])==START
 return {'pid':PID,'start':int(p[19]),'state':p[0],'ppid':int(p[1]),'pgid':int(p[2]),'sid':int(p[3])}
before=proc();assert before['ppid']==3502874 and before['sid']==3502874
assert len(list(Path('/proc/%d/task'%PID).iterdir()))==1
assert os.readlink('/proc/%d/exe'%PID)=='/usr/bin/python3.8'
assert digest('/usr/bin/python3.8')==PYTHON_SHA
assert digest('/usr/bin/gdb')==GDB_SHA
assert digest(OWNER)==OWNER_SHA and digest(SMOKE)==SMOKE_SHA
assert digest(D/'export.gdb')==SCRIPT_SHA
assert not (D/'TARGET-STATE.json').exists()
lock=Path('/run/lock/mckernel-development.lock').stat();assert (lock.st_dev,lock.st_ino)==(27,4)
key=f'{os.major(lock.st_dev):02x}:{os.minor(lock.st_dev):02x}:4'
assert any(len(x.split())>=6 and x.split()[4]==str(PID) and x.split()[5]==key for x in Path('/proc/locks').read_text().splitlines())
out=D/'actual-root-controller-1';out.mkdir(mode=0o700)
argv=['/usr/bin/gdb','--nx','--nh','--batch','-iex','set auto-load off','-p',str(PID),'-x',str(D/'export.gdb')]
t=time.monotonic()
with (out/'stdout').open('xb') as so,(out/'stderr').open('xb') as se:
 c=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=so,stderr=se,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C','DEBUGINFOD_URLS':''})
 rc=c.wait()
after=proc(allow_missing=True)
record={'scope':__doc__,'debugger_returncode':rc,'debugger_pid':c.pid,'debugger_direct_joined':True,'debugger_streams_closed':True,'elapsed_seconds':time.monotonic()-t,'target_before':before,'target_after':after,'target_not_ptrace_stopped':after['state'] not in ('T','t'),'physical_clearance':False,'owner_methods_invoked':0,'owner_flags_changed':0}
for name in ('stdout','stderr'):
 p=out/name;assert p.stat().st_size<=2**20;record['debugger_'+name]=p.read_text(errors='replace')
p=D/'TARGET-STATE.json'
if p.exists():
 fd=os.open(p,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
 try:
  s=os.fstat(fd);assert stat.S_ISREG(s.st_mode) and s.st_uid==0 and s.st_nlink==1
  with os.fdopen(fd,'rb',closefd=False) as f:raw=f.read(16*2**20+1)
 finally:os.close(fd)
 assert len(raw)<=16*2**20;record['target_export_sha256']=hashlib.sha256(raw).hexdigest();record['target_export']=json.loads(raw)
(out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,sort_keys=True))
assert rc==0 and record['target_not_ptrace_stopped'] and record.get('target_export',{}).get('status')=='WAITSTATUS_COMPATIBILITY_INSTALLED_ONLY'
