"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import os,json,hashlib,signal,importlib.util
D=Path(__file__).parent;test=D/'test_actual_sdk_core_and_pre_rm_uncertainty_TEMPFILE_ONLY.py'
assert os.getuid()==os.geteuid()==1000
assert hashlib.sha256(test.read_bytes()).hexdigest()=='efa45fa74bc346c05a166b24305ff8a4d89b1d681bc3e001bdefbe0d10029e8b'
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py');assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8';s=importlib.util.spec_from_file_location('h',H);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(n,h.stop)
out=D/'actual-pure-core-capture-1';out.mkdir(mode=0o700)
argv=['/usr/bin/taskset','-c','0','/usr/bin/prlimit','--as=536870912:536870912','--cpu=15:15','--fsize=4194304:4194304','--nofile=256:256','--core=0:0','--','/home/holden/anaconda3/bin/python3','-I','-B',str(test)]
mem={r.split(':')[0]:r.split(':')[1].strip() for r in Path('/proc/meminfo').read_text().splitlines()};host=os.statvfs('/home/holden');scratch=os.statvfs('/home/holden/mckernel-work/scratch')
h.write(out/'EXACT-ARGV-GRANT-AND-PREFLIGHT.json',dict(scope=__doc__,argv=argv,root_grant='PENDING_ROOT_EXACT_DISPOSABLE_SDK_CORE_AND_MAIN_GRANT',memory_available=mem['MemAvailable'],host_available=host.f_bavail*host.f_frsize,scratch_available=scratch.f_bavail*scratch.f_frsize,root_mutex_touched=False,sudo=False))
signal.setitimer(signal.ITIMER_REAL,31);r=h.owned_capture(dict(argv=argv,purpose=__doc__+' actualSDK3recordcore TEMPFILE and actualmain pre-rm uncertainty controls; no rootmutex, sudo or productioncleanup.'),out,25,lambda:None);h.write(out/'WHOLE-JOIN.json',r);signal.setitimer(signal.ITIMER_REAL,0);print(json.dumps(r,sort_keys=True));assert r['returncode']==0 and all(r[k] is True for k in ('direct_child_joined','group_absent','closed_streams')) and not r['timed_out'] and r['error'] is None and r['retirement_error'] is None;print((out/'stdout').read_text())
