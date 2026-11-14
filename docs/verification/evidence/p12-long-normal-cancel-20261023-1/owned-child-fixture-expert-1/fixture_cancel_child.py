"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One owned TESTONLY child, unchanged actual helper and child. Retain all outcomes before asserting.
"""
import base64,copy,hashlib,importlib.util,json,os,select,subprocess,sys,time,traceback
from pathlib import Path
D=Path(__file__).resolve().parent;PY='/home/holden/anaconda3/bin/python3'
assert os.getuid()==os.geteuid()==1000 and sys.executable==PY and sys.version_info[:3]==(3,9,12)
helper=D/'cancel_exact_owner_once.py';assert hashlib.sha256(helper.read_bytes()).hexdigest()=='950b8b162e13cf547b05993f1e1ca7e92aa501ceb4ec539ffa815fc372077b21'
spec=importlib.util.spec_from_file_location('actual_cancel_source',helper);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def retain(name,value):
 raw=(json.dumps(value,sort_keys=True,indent=2)+'\n').encode()
 fd=os.open(str(D/name),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_CLOEXEC,0o600)
 try:
  pos=0
  while pos<len(raw):pos+=os.write(fd,raw[pos:])
 finally:os.close(fd)
m.require_architecture()
checks=[]
assert not callable(getattr(m.os,'pidfd_open',None)) and not callable(getattr(m.signal,'pidfd_send_signal',None))
for label,fn,number in [('actual_typed_errno_EINVAL_open',lambda:m.typed_pidfd_open(-1),22),('actual_typed_errno_EBADF_send',lambda:m.typed_pidfd_send_term(-1),9)]:
 try:fn()
 except OSError as exc:assert exc.errno==number,(exc.errno,number);checks.append(dict(name=label,status='PASS',errno=exc.errno))
 else:raise AssertionError('invalid descriptor/PID syscall unexpectedly accepted')
path=D/'test_child.py';argv=[PY,'-I','-B',str(path),'TESTONLY-never-live-owner']
before_all_fds=len(os.listdir('/proc/self/fd'))
p=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
ready=b'';out=None;err=None;record=None;identity=None;error=None;passed=False;reaped=False
try:
 assert p.pid!=m.EXPECTED['pid']
 deadline=time.monotonic()+3
 # Read exactly through LF using raw one-byte reads: no buffered prefetch can
 # hide part of a later handler result from subprocess.communicate(). The
 # unchanged child installs its handler before flushing this readiness line.
 while not ready.endswith(b'\n'):
  remaining=deadline-time.monotonic();assert remaining>0,'bounded handler-ready handshake deadline'
  assert select.select([p.stdout],[],[],remaining)[0],'handler-ready handshake timeout'
  byte=os.read(p.stdout.fileno(),1);assert byte and len(ready)<128,'short/overlong ready handshake';ready+=byte
 assert ready==b'TESTONLY_CHILD_READY\n',repr(ready)
 e=dict(pid=p.pid,start=0,pgid=os.getpgid(p.pid),sid=os.getsid(p.pid),uid=1000,gid=1000,controller_uid=1000,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),source_path=str(path),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),cmdline=argv,nonce='TESTONLY-never-live-owner')
 fact=m.snapshot(e);e['start']=fact['start'];assert m.verify(e,fact)=='MATCHED_LIVE_IDENTITY';identity=dict(expected=e,actual={**fact,'cmdline_base64':base64.b64encode(fact['cmdline']).decode()});del identity['actual']['cmdline']
 retain('ACTUAL-READY-AND-CHILD-IDENTITY.json',dict(ready_base64=base64.b64encode(ready).decode(),identity=identity,live_owner_not_read_or_signaled=True))
 for name,change in [('wrongbirth',lambda x:x.update(start=x['start']+1)),('wrongPGID',lambda x:x.update(pgid=x['pgid']+1)),('wrongSID',lambda x:x.update(sid=x['sid']+1)),('wrongUID',lambda x:x.update(uid=0)),('wrongGID',lambda x:x.update(gid=0)),('wrongcmdline',lambda x:x.update(cmdline=x['cmdline']+['foreign'])),('wrongsourcehash',lambda x:x.update(source_sha256='0'*64)),('wrongboot',lambda x:x.update(boot_id='TESTONLY-WRONGBOOT')),('wrongcontrollerUID',lambda x:x.update(controller_uid=0))]:
  before_fds=len(os.listdir('/proc/self/fd'));x=copy.deepcopy(e);change(x)
  try:m.cancel(x)
  except ValueError as exc:checks.append(dict(name=name,status='PASS_REFUSE',error=str(exc)))
  else:raise AssertionError('guard accepted '+name)
  assert p.poll() is None,'negative guard signaled child'
  assert len(os.listdir('/proc/self/fd'))==before_fds,'pidfd leaked on identity refusal'
 record=m.cancel(e)
 retain('ACTUAL-ONE-SEND-RESULT.json',record)
 assert record['status']=='ONE_SIGTERM_SENT_TO_EXACT_OWNER_ONLY' and record['signal_calls']==1
 out,err=p.communicate(timeout=3)
 # Persist the actual subclauses independently, before the unchanged strict
 # status/empty-stderr/exact handler JSON assertion.
 outcome=dict(returncode=p.returncode,stdout_base64=base64.b64encode(out).decode(),stderr_base64=base64.b64encode(err).decode(),stdout_repr=repr(out),stderr_repr=repr(err))
 retain('ACTUAL-CHILD-OUTCOME.BEFORE-ASSERT.json',outcome)
 assert p.returncode==42,dict(expected=42,actual=p.returncode)
 assert err==b'',repr(err)
 assert json.loads(out)==dict(received_SIGTERM=1,nonce='TESTONLY-never-live-owner'),repr(out)
 checks.append(dict(name='actual_pidfd_exactly_one_SIGTERM',status='PASS',receipt=record,child_returncode=p.returncode,child_stdout=out.decode()))
 absent=m.cancel(e);assert absent['status']=='OBSERVED_ALREADY_ABSENT_NO_SIGNAL' and absent['signal_calls']==0
 checks.append(dict(name='alreadyexited_no_signal',status='PASS',receipt=absent))
 try:os.waitpid(p.pid,os.WNOHANG)
 except ChildProcessError:reaped=True
 else:raise AssertionError('child not ECHILD')
 passed=True
except BaseException as exc:
 error=dict(type=type(exc).__name__,message=str(exc),traceback=traceback.format_exc())
 raise
finally:
 # No second signal. On any failed assertion the unchanged child's own30s
 # exit remains within this fixture's60s owned supervisor. Always retain it.
 if out is None or err is None:
  out,err=p.communicate(timeout=35)
 if p.stdout:p.stdout.close()
 if p.stderr:p.stderr.close()
 after_all_fds=len(os.listdir('/proc/self/fd'))
 report=dict(scope=__doc__,status='PASS_ACTUAL_API_AND_OWNED_CHILD_FIXTURE_NOT_LIVE_CANCEL' if passed else 'FAIL_RETAINED_ACTUAL_CHILD_OUTCOME',interpreter=sys.executable,version=sys.version,checks=checks,child=dict(pid=p.pid,identity=identity,ready_base64=base64.b64encode(ready).decode(),returncode=p.returncode,stdout_base64=base64.b64encode(out).decode(),stderr_base64=base64.b64encode(err).decode()),signal_receipt=record,error=error,child_reaped_ECHILD=reaped,fd_count_before=before_all_fds,fd_count_after=after_all_fds,no_FD_leak=before_all_fds==after_all_fds,live_owner_not_read_or_signaled=True,root=0,Docker=0,workload=0,actual_live_cancel=None,physical_clearance=False)
 retain('ACTUAL-API-CHILD-FIXTURE-RESULT.json',report);print(json.dumps(report,sort_keys=True))
 assert before_all_fds==after_all_fds,'fixture FD leak'
