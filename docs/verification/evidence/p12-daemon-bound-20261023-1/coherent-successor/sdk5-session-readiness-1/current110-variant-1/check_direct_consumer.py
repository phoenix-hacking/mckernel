"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Corrected private actual CommandChild.wait/bounded_command/ledger consumers; no shim installed.
Only controlled ordinary Python3.8 children; no root/live owner/Docker/history repair.
"""
from pathlib import Path
import hashlib,importlib.util,json,os,signal,sys,time,traceback
D=Path(__file__).resolve().parent
OWNER=D/'source/native_diagnostic_container_owner.py'
OWNER_SHA='34b680365f9015d8180046421cc5048d349ca59e59df860c24754ba87480d980'
def load(path,name,sha):
 raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==sha
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
report=dict(scope=__doc__.splitlines()[0],python=sys.version,owner_source_sha256=OWNER_SHA,reused_fixture_receipt_sha256='83fb9aa601903552794ad3237c289596ecb1d77ff6e606bd2f728133e0801bff',root=0,live_owner=0,Docker=0,historical_statuses_reconstructed=False)
start=time.monotonic();records=[];waits=[]
try:
 assert sys.version_info[:2]==(3,8) and not hasattr(os,'waitstatus_to_exitcode')
 o=load(OWNER,'corrected_private_owner_wait_consumer',OWNER_SHA)
 report['shim_installed']=False;assert not hasattr(os,'waitstatus_to_exitcode')
 actual_wait=o.CommandChild.wait
 def observed_wait(child,timeout):
  code=actual_wait(child,timeout)
  waits.append(dict(record=child.record(),returncode=code));return code
 o.CommandChild.wait=observed_wait
 for label,tail,expected in [('exit0','raise SystemExit(0)',0),('nonzero37','raise SystemExit(37)',37),('signaledTERM','os.kill(os.getpid(),signal.SIGTERM)',-15)]:
  ledger=o.CommandLedger()
  argv=['/usr/bin/python3','-I','-B','-c',"import os,signal,time;time.sleep(.03);os.write(1,b'fixture-out');os.write(2,b'fixture-err');"+tail]
  before=len(waits)
  result=o.bounded_command(argv,timeout=3,env={'PATH':'/usr/bin:/bin','LANG':'C','LC_ALL':'C'},ledger=ledger)
  record=result.command_record
  assert result.returncode==expected and result.stdout==b'fixture-out' and result.stderr==b'fixture-err'
  assert len(waits)==before+1 and waits[-1]['returncode']==expected
  assert record['reaped'] is True and record['returncode']==expected and record['pid']==record['pgid'] and record['proc_starttime']>0
  try:os.waitpid(record['pid'],os.WNOHANG)
  except ChildProcessError:echild=True
  else:raise AssertionError('child reap not final')
  try:os.getpgid(record['pid'])
  except ProcessLookupError:absent=True
  else:raise AssertionError('child identity still exists')
  assert not ledger.pending and not ledger.errors and not ledger.final_reap_records
  ledger.retire_pending(timeout=.1)
  snapshot=ledger.peek_final_reap_records();ledger.ack_final_reap_records(snapshot)
  assert snapshot==() and ledger.pending==set() and ledger.final_reap_records==[]
  records.append(dict(case=label,returncode=result.returncode,stdout=result.stdout.decode(),stderr=result.stderr.decode(),record=record,echild=echild,child_identity_absent=absent,pending_ledger=0,ledger_errors=[],retirement_consumer='actual CommandLedger.retire_pending + peek/ack completed'))
 report.update(status='PASS_3_ACTUAL_PYTHON38_WAIT_BOUNDED_COMMAND_LEDGER_CONSUMERS',cases=records,actual_wait_observations=waits,seconds=time.monotonic()-start)
except BaseException:
 report.update(status='FAIL_FIRST_CANDIDATE_PRESERVED',cases=records,traceback=traceback.format_exc(),seconds=time.monotonic()-start)
(D/'DIRECT-CONSUMER-RESULT.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
if report['status'].startswith('FAIL'):raise SystemExit(1)
