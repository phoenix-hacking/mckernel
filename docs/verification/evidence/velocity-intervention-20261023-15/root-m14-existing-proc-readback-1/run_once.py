"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
import importlib.util,hashlib,json,signal,time
from pathlib import Path
D=Path(__file__).parent
P=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-15/m14-default-build-retirement-preparation-1/honest-cli-proof-correction-1/current-failed-observer-1/receipt-schema-correction-1/root-observation-m14-union2-failed-image-observation-schema-correction-20261024-1')
H=Path('/home/holden/mckernel/docs/verification/evidence/phase5-m03-handshake-runtime-checkpoint-20261020-1/sdk-physical-source/run_two_commands_source_bound_corrected.py')
assert hashlib.sha256(H.read_bytes()).hexdigest()=='990807ab7ecaee4bd4386908270e2d68f2172d09b505a5602949247dd3e7fdc8'
s=importlib.util.spec_from_file_location('owned',H);h=importlib.util.module_from_spec(s);s.loader.exec_module(h)
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):signal.signal(sig,h.stop)
rows=[];begin=time.monotonic();signal.setitimer(signal.ITIMER_REAL,72)
try:
 for n in ['process-00.json','process-01.json']:
  out=D/n[:-5];out.mkdir()
  argv=['/usr/bin/sudo','-A','/usr/bin/taskset','-c','7','/usr/bin/prlimit','--as=2147483648:2147483648','--cpu=30:30','--fsize=33554432:33554432','--nofile=256:256','--core=0:0','--','/usr/bin/cat','--',str(P/n)]
  command=dict(argv=argv,purpose=__doc__+' Exact existing retained process report readback only; no new census/mutation.')
  left=60-(time.monotonic()-begin);assert left>0
  r=h.owned_capture(command,out,left,lambda:None);h.write(out/'WHOLE-JOIN.json',r)
  assert r['returncode']==0 and r['direct_child_joined'] and r['group_absent'] and r['closed_streams'] and r['error'] is None and r['retirement_error'] is None and not r['timed_out']
  raw=(out/'stdout').read_bytes();json.loads(raw);rows.append(dict(source=str(P/n),export=str(out/'stdout'),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),wholejoin=r))
 h.write(D/'RESULT.json',dict(status='PASS_AUTHENTICATED_EXISTING_TWO_PROCESS_REPORT_READBACK_ONLY',rows=rows,seconds=time.monotonic()-begin));print(json.dumps([{k:v for k,v in r.items() if k!='wholejoin'} for r in rows]))
finally:signal.setitimer(signal.ITIMER_REAL,0)
