"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import json,hashlib,signal,importlib.util
D=Path(__file__).parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('h',H);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(n,h.stop)
base=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m15-libihk-next/new-window-installed-consumer-source-1/binder-successor-source-1/actual-copy7-late-bound-1/current-install-physical-postflight-source-1/exact-driver-status-source-revision-2')
rows=[('readonly_installed_consumer_current_proc.py', 'b0a8a0764d0d60db52f75857b4eb1006faf52fdea3808ade94156ba4a546744e'), ('readonly_installed_consumer_mutex_physical.py', 'bee763ca5123ab52ef6b25bc9bddf2d139f3b4edb7898667fa4c6590998812db')]
for i,(name,sha) in enumerate(rows):
 p=base/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==sha
 out=D/str(i);out.mkdir(mode=0o700)
 cmd=dict(argv=['/usr/bin/sudo','-A','/usr/bin/taskset','-c','7','/usr/bin/prlimit','--as=2147483648:2147483648','--cpu=30:30','--fsize=33554432:33554432','--core=0:0','--nofile=256','--','/home/holden/anaconda3/bin/python3','-I','-B',str(p)],purpose=__doc__+' Existing read-only M14 normal retirement terminal PROC or mutex/exclusion proof; no cleanup or workload.')
 signal.setitimer(signal.ITIMER_REAL,70);r=h.owned_capture(cmd,out,60,lambda:None);h.write(out/'WHOLE-JOIN.json',r);signal.setitimer(signal.ITIMER_REAL,0)
 assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None and not r['timed_out']
 print(json.dumps(dict(index=i,returncode=r['returncode'],seconds=r['seconds'])))
