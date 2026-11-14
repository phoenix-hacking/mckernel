"""Functional exception-evidence regression only; no security testing/effects.
Run the actual recover() function with mocked transaction, masks and hold loop.
"""
import contextlib,importlib.util,io,json
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parent;E=ROOT.parent
SOURCE=E/'current290-dead-caller-normal-cleanup-source-1/bounded-observer-correction-source-1/native_rust_cutover_image_terminal_cleanup.CURRENT290.EXACT-DEAD-CALLER.py'
PREP=E/'current290-dead-caller-normal-cleanup-source-1/ROOT-NORMAL-RETIREMENT-PREPARATION-1'
def recover_record(path,reason):
 spec=importlib.util.spec_from_file_location('quarantine_reason_regression',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 m.RELEASE=json.loads((PREP/'RELEASE.PASS_EXECUTION_RELEASE.json').read_text());captures=[];closed=[]
 class StopMockHold(Exception):pass
 def fail(execute):raise m.Refusal(reason)
 def hold():raise StopMockHold()
 tx=SimpleNamespace(fd=99,root_locked=True,mutation_started=True,run=fail,create=lambda name,raw:captures.append(raw),close=lambda:closed.append(True))
 m.Transaction=lambda:tx;m.quarantine_wait=hold;m.signal=SimpleNamespace(SIG_BLOCK=0,SIG_SETMASK=1,pthread_sigmask=lambda *args:None)
 with contextlib.redirect_stdout(io.StringIO()):
  try:m.recover(True)
  except StopMockHold:pass
  else:raise AssertionError('mock hold must stop local test')
 assert closed==[True] and len(captures)==1
 return json.loads(captures[0])
first=recover_record(SOURCE,'fixture-A-not-actual-cause');second=recover_record(SOURCE,'fixture-B-not-actual-cause')
assert first==second and first['error_type']=='Refusal' and 'reason' not in first
print(json.dumps(dict(status='PASS_REPRODUCED_LOSS_OF_DISTINCT_REFUSAL_REASONS',original_record=first,scope='diagnostic reporting defect only; does not identify actual runtime refusal'),indent=2))
