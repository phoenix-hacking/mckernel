"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import json,hashlib,signal,importlib.util
D=Path(__file__).parent
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('h',H);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
for n in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(n,h.stop)
base=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-qualified-source-integration-1/current81-default-image-preparation/next-normal-cfg-only-source-preparation-1/namespace-request-preparation-cfg-only-1/bounded-runtime-import-binding-correction-1/expert-current-process-TID-source-identity-correction-1/retained-normal-prefix-continuation-preparation-1/copy7-normal-image-retirement-preparation-1/recovery-source-reconciliation-20261025-1/physical-postflight-source-1')
rows=[('readonly_COPY7_current_proc.py', 'e25f2bb4edfd838687c30f1db61d52e39da371df9cba468b63f4b195333c055e'), ('readonly_COPY7_mutex_physical.py', '01e7ea6cac6e00f97977ceaf34de9d57a9b73ad025e79da525813c74a6a967b5')]
for i,(name,sha) in enumerate(rows):
 p=base/name;assert hashlib.sha256(p.read_bytes()).hexdigest()==sha
 out=D/str(i);out.mkdir(mode=0o700)
 cmd=dict(argv=['/usr/bin/sudo','-A','/usr/bin/taskset','-c','7','/usr/bin/prlimit','--as=2147483648:2147483648','--cpu=30:30','--fsize=33554432:33554432','--core=0:0','--nofile=256','--','/home/holden/anaconda3/bin/python3','-I','-B',str(p)],purpose=__doc__+' COPY7 read-only normal retirement PROC or mutex-held physical proof; no cleanup or workload.')
 signal.setitimer(signal.ITIMER_REAL,70);r=h.owned_capture(cmd,out,60,lambda:None);h.write(out/'WHOLE-JOIN.json',r);signal.setitimer(signal.ITIMER_REAL,0)
 assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None and not r['timed_out']
 print(json.dumps(dict(index=i,returncode=r['returncode'],seconds=r['seconds'])))
