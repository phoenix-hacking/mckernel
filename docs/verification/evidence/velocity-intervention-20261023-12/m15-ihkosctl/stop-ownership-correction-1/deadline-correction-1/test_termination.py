"""Functional OS/Rust only; no security testing. Requires explicit ordinary grant."""
import json,os,signal,subprocess,sys,time
from pathlib import Path
from owned_process import Owner
P=Path(__file__).resolve().parent
if len(sys.argv)>1 and sys.argv[1]=='worker':
    out=Path(sys.argv[2]);owner=Owner(out)
    child="import os,time;from pathlib import Path;p=os.fork();\nif p==0: os.setsid();Path('escaped.json').write_text(str(os.getpid()));time.sleep(30)\nelse: Path('ready').write_text(str(os.getpid()));time.sleep(30)"
    try:owner.run([sys.executable,'-c',child],os.environ.copy(),out,20,'child')
    except BaseException:sys.exit(1)
    raise SystemExit('unexpected success')
root=P/'termination-fixture-output';root.mkdir()
for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGALRM):
    out=root/str(int(sig));out.mkdir();outer=Owner(out)
    # A finite controller is itself owned by the corrected helper. The target
    # worker has its own session; controller retains its direct PID until wait.
    script="""import os,signal,subprocess,sys,time
from pathlib import Path
out=Path(sys.argv[1]);p=subprocess.Popen([sys.executable,sys.argv[2],'worker',str(out)],start_new_session=True)
try:
 end=time.monotonic()+4
 while not ((out/'ready').exists() and (out/'escaped.json').exists()):
  if time.monotonic()>end:raise RuntimeError('worker readiness timeout')
  time.sleep(.01)
 os.kill(p.pid,int(sys.argv[3]));rc=p.wait(timeout=7)
 assert rc==1,rc
 row=__import__('json').loads((out/'child.closed.json').read_text())
 assert row['retirement_seconds']<6,row
 assert row['retirement_deadline']-row['retirement_started']==6,row
 assert row['retirement_action_deadline']==row['retirement_deadline']-1,row
 assert row['direct_child_joined'] and row['whole_descendants_joined'] and row['closed_streams'] and row['status_kind']=='FAIL',row
 for pid in [row['leader'],int((out/'escaped.json').read_text())]:assert not Path('/proc/'+str(pid)).exists(),pid
finally:
 if p.returncode is None:
  try:os.killpg(p.pid,signal.SIGKILL)
  except ProcessLookupError:pass
  p.wait(timeout=3)
"""
    run=outer.run([sys.executable,'-c',script,str(out),str(P/'test_termination.py'),str(int(sig))],os.environ.copy(),P,14,'controller')
    assert run.returncode==0,run.stderr
print('PASS actual TERM/INT/ALRM direct+escaped-session child joins; durable FAIL/closed streams')
