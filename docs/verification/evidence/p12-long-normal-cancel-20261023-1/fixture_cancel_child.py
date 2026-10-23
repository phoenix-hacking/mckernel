"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual pidfd API and same cancellation function on one owned ordinary TESTONLY child only.
"""
import copy,hashlib,importlib.util,json,os,select,subprocess,sys,time
from pathlib import Path
D=Path(__file__).resolve().parent;PY='/home/holden/anaconda3/bin/python3'
assert os.getuid()==os.geteuid()==1000 and sys.executable==PY and sys.version_info[:3]==(3,9,12)
spec=importlib.util.spec_from_file_location('actual_cancel_source',D/'cancel_exact_owner_once.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert callable(getattr(m.os,'pidfd_open',None)) and callable(getattr(m.signal,'pidfd_send_signal',None)),'required APIs unavailable; no fallback'
path=D/'test_child.py';argv=[PY,'-I','-B',str(path),'TESTONLY-never-live-owner'];p=subprocess.Popen(argv,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
checks=[];record=None
try:
 assert p.pid!=m.EXPECTED['pid'] and select.select([p.stdout],[],[],3)[0]
 assert p.stdout.readline()==b'TESTONLY_CHILD_READY\n'
 e=dict(pid=p.pid,start=0,pgid=os.getpgid(p.pid),sid=os.getsid(p.pid),uid=1000,gid=1000,controller_uid=1000,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),source_path=str(path),source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),cmdline=argv,nonce='TESTONLY-never-live-owner')
 fact=m.snapshot(e);e['start']=fact['start'];assert m.verify(e,fact)=='MATCHED_LIVE_IDENTITY'
 for name,change in [('wrongbirth',lambda x:x.update(start=x['start']+1)),('wrongPGID',lambda x:x.update(pgid=x['pgid']+1)),('wrongSID',lambda x:x.update(sid=x['sid']+1)),('wrongUID',lambda x:x.update(uid=0)),('wrongGID',lambda x:x.update(gid=0)),('wrongcmdline',lambda x:x.update(cmdline=x['cmdline']+['foreign'])),('wrongsourcehash',lambda x:x.update(source_sha256='0'*64)),('wrongboot',lambda x:x.update(boot_id='TESTONLY-WRONGBOOT')),('wrongcontrollerUID',lambda x:x.update(controller_uid=0))]:
  x=copy.deepcopy(e);change(x)
  try:m.cancel(x)
  except ValueError as exc:checks.append(dict(name=name,status='PASS_REFUSE',error=str(exc)))
  else:raise AssertionError('guard accepted '+name)
  assert p.poll() is None,'negative guard signaled child'
 record=m.cancel(e);assert record['status']=='ONE_SIGTERM_SENT_TO_EXACT_OWNER_ONLY' and record['signal_calls']==1
 out,err=p.communicate(timeout=3);assert p.returncode==42 and err==b'' and json.loads(out)==dict(received_SIGTERM=1,nonce='TESTONLY-never-live-owner')
 checks.append(dict(name='actual_pidfd_exactly_one_SIGTERM',status='PASS',receipt=record,child_returncode=42,child_stdout=out.decode()))
 absent=m.cancel(e);assert absent['status']=='OBSERVED_ALREADY_ABSENT_NO_SIGNAL' and absent['signal_calls']==0;checks.append(dict(name='alreadyexited_no_signal',status='PASS',receipt=absent))
 try:os.waitpid(p.pid,os.WNOHANG)
 except ChildProcessError:pass
 else:raise AssertionError('child not ECHILD')
 report=dict(scope=__doc__,status='PASS_ACTUAL_API_AND_OWNED_CHILD_FIXTURE_NOT_LIVE_CANCEL',interpreter=sys.executable,version=sys.version,pidfd_open_available=True,pidfd_send_signal_available=True,checks=checks,all_child_reaped_ECHILD=True,live_owner_not_read_or_signaled=True,live_owner_PID=m.EXPECTED['pid'],fixture_child_PID=p.pid,root=0,Docker=0,workload=0,actual_live_cancel=None,physical_clearance=False)
 (D/'ACTUAL-API-CHILD-FIXTURE-RESULT.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps(report,sort_keys=True))
finally:
 # Never issue a second signal even on fixturefailure; the owned child has its
 # own30s end and the outer60s supervisor retains and joins its processgroup.
 if p.poll() is None:p.wait(timeout=35)
 if p.stdout:p.stdout.close()
 if p.stderr:p.stderr.close()
