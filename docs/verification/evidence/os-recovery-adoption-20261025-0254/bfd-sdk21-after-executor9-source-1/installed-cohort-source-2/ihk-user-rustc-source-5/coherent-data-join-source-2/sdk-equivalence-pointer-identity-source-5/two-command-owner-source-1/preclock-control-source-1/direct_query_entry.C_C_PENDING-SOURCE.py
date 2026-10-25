"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Root-approved direct exec, no outer timeout/CPU watchdog. PID retained across exec; no controller.
"""
from pathlib import Path
import os,json,hashlib,time
A=Path(__file__).parent/'admission-preparation-1';D=A/'root-readonly-admission-capture-1'
assert os.getuid()==os.geteuid()==os.getgid()==1000
pins = {'run_root_sdk_readonly_admission.py': '01e5d7cbd94657845ce8df0818349096b5e618b6648dc53ad31e2a7b73bbf362', 'QUERY-INPUTS.ROOT.json': '8945bd36cdced15bfe9ec117bc424461dc66a7680b952c288f39206f0311a54c'}
for n,s in pins.items():assert hashlib.sha256((A/n).read_bytes()).hexdigest()==s
assert not os.path.lexists(A/'root-readonly-admission-preview-1')
back=Path('/home/holden/mckernel-work/scratch.ext4').stat();gap=max(0,back.st_size-back.st_blocks*512)
mem={x.split(':')[0]:int(x.split()[1])*1024 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')}
hv=os.statvfs('/');sv=os.statvfs('/home/holden/mckernel-work/scratch')
resources=dict(memory_available=mem['MemAvailable'],host_free=hv.f_bavail*hv.f_frsize,scratch_free=sv.f_bavail*sv.f_frsize,full_sparse_gap=gap)
assert resources['memory_available']>=25501368320 and resources['host_free']>=26449281024+gap and resources['scratch_free']>=14091616256
pid=os.getpid()
if os.getpgid(pid)!=pid:os.setsid()
assert os.getpgid(pid)==pid
birth=Path('/proc/'+str(pid)+'/stat').read_text().rsplit(')',1)[1].split()[19]
argv=['/usr/bin/taskset','-c','7','/usr/bin/prlimit','--as=2147483648:2147483648','--fsize=33554432:33554432','--nofile=256:256','--core=0:0','--','/home/holden/anaconda3/bin/python3','-I','-B',str(A/'run_root_sdk_readonly_admission.py'),pins['QUERY-INPUTS.ROOT.json']]
record=dict(scope=__doc__,pid=pid,starttime=birth,pgid=os.getpgid(pid),boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),argv=argv,at=time.time(),preflight_resources=resources,outer_timeout=None,outer_CPU_rlimit=None,capture_method='exclusive descriptors + samePID exec; actual exec_command terminal receipt required')
fd=os.open(D/'DIRECT-PROCESS-BEFORE-EXEC.json',os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
with os.fdopen(fd,'w') as f:json.dump(record,f,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
for target,name in ((1,'stdout'),(2,'stderr')):
 fd=os.open(D/name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600);os.dup2(fd,target);os.close(fd)
os.execv(argv[0],argv)
