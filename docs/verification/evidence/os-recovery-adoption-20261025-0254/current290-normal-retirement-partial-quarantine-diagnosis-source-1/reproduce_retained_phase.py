"""Functional source/state replay only; no security testing or runtime effects.
Every transaction filesystem call is backed by retained plan/journal metadata.
No Transaction constructor, root query, write, signal, Docker or cleanup runs.
"""
import hashlib,importlib.util,json,stat
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parent
E=ROOT.parent
SOURCE=E/'current290-dead-caller-normal-cleanup-source-1/bounded-observer-correction-source-1/native_rust_cutover_image_terminal_cleanup.CURRENT290.EXACT-DEAD-CALLER.py'
PREP=E/'current290-dead-caller-normal-cleanup-source-1/ROOT-NORMAL-RETIREMENT-PREPARATION-1'
SNAP=PREP/'ROOT-ACTUAL-CLEANUP-OUTER-1/ROOT-UNPRIVILEGED-TRANSACTION-IDENTITIES.json'
spec=importlib.util.spec_from_file_location('forensic_e49',SOURCE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
release=json.loads((PREP/'RELEASE.PASS_EXECUTION_RELEASE.json').read_text())
rows={row['key']:row for row in json.loads(SNAP.read_text())}
plan=m.parse(rows['PLAN']['raw_utf8']);journal=rows['JOURNAL']['raw_utf8'].encode()
assert m.canonical(plan)+b'\n'==rows['PLAN']['raw_utf8'].encode()
assert len(journal.splitlines())==4 and not rows['ATTEMPT']['exists'] and rows['SHARED']['size']==269
assert m.digest(m.canonical(release))==json.loads(rows['QUARANTINE']['raw_utf8'])['release_sha256']
paths=(m.ATTEMPT,m.SHARED);m.DEVICE=plan['device'];m.OWNERSHIP_CASE='FAIL_COMMON_AND_SHARED'
m.RECORDS={Path(row[0]):tuple(row[3:]) for row in plan['records']}
meta=lambda dev,ino,mode:SimpleNamespace(st_dev=dev,st_ino=ino,st_mode=mode)
plan_identity=json.loads(journal.splitlines()[0])['plan_identity']
metadata={
 (10,m.PLAN.name):meta(*plan_identity,stat.S_IFREG|0o600),
 (20,m.ARCHIVE_NAMES[0]):meta(m.NAMESPACE_BINDING['device'],plan['records'][0][4],stat.S_IFREG|0o600),
 (10,m.ARCHIVE_NAMES[1]):meta(*plan['sentinels'][1],stat.S_IFDIR|0o700),
 (10,m.SHARED.name):meta(plan['device'],plan['records'][1][4],stat.S_IFREG|0o600),
}
existing={(10,m.PLAN.name),(10,m.JOURNAL.name),(20,m.ARCHIVE_NAMES[0]),(10,m.ARCHIVE_NAMES[1]),(10,m.SHARED.name)}
trace=[]
def parent(path):return 20 if path==m.ATTEMPT else 10
def read_at(fd,name,binding=None,**kw):
 trace.append(['read_at',fd,name])
 if name==m.PLAN.name:return rows['PLAN']['raw_utf8'].encode(),metadata[(10,name)]
 if name==m.JOURNAL.name:return journal,SimpleNamespace(st_dev=plan['device'],st_ino=plan['journal_identity'][1])
 if (fd,name)==(20,m.ARCHIVE_NAMES[0]):raw=(E/'current290-post-recovery-retirement-review-1/quarantine-readonly-snapshot-1/COMMON-ARCHIVE.json').read_bytes();assert (m.digest(raw),metadata[(fd,name)].st_ino,len(raw))==binding;return raw,metadata[(fd,name)]
 if (fd,name)==(10,m.SHARED.name):
  raw=rows['SHARED']['raw_utf8'].encode();assert (m.digest(raw),metadata[(fd,name)].st_ino,len(raw))==binding
  return raw,metadata[(fd,name)]
 raise AssertionError(('unexpectedread',fd,name))
def sentinel(name,wanted,parentfd):
 assert name==m.ARCHIVE_NAMES[1] and wanted==plan['sentinels'][1] and parentfd==10
 trace.append(['sentinel',name,wanted])
m.read_at=read_at;m.exists=lambda fd,name:(fd,name) in existing
m.os=SimpleNamespace(stat=lambda name,**kw:metadata[(kw['dir_fd'],name)],path=SimpleNamespace(lexists=lambda path:False))
m.protected_files=lambda:trace.append(['protected-files-already-proved-separately'])
m.capture_logs=lambda *args,**kwargs:trace.append(['no-effect-capture-mock'])
m.census=lambda:False
obj=m.Transaction.__new__(m.Transaction);obj.fd=10;obj.mutation_started=False
obj.parent_fd=parent;obj.preserved=lambda:trace.append(['preservation-snapshot-mock']);obj.pinned=lambda:trace.append(['pinned-snapshot-mock']);obj.sentinel=sentinel
actual_rows,actual=obj.state(plan)
assert len(actual_rows)==4 and actual==['after_release','before_exchange']
class StopBeforeMutation(Exception):pass
obj.lock=lambda execute:None;obj.load_plan=lambda:plan
obj.append=lambda plan,rows,event,index:(_ for _ in ()).throw(StopBeforeMutation((event,index)))
try:obj.run(True)
except StopBeforeMutation as stop:assert stop.args[0]==('before_exchange',1)
else:raise AssertionError('must stop before any new journal mutation')
# A transient later census Refusal yields the same retained four-event prefix.
def transient():raise m.Refusal('forensic-fixture-census-refusal-not-actual-cause')
m.census=transient
try:obj.run(True)
except m.Refusal as exc:assert str(exc)=='forensic-fixture-census-refusal-not-actual-cause'
else:raise AssertionError('missing fixture refusal')
print(json.dumps(dict(status='PASS_SOURCE_PHASE_REPLAY_ONLY',actual_state=actual,journal_events=4,next_event=['before_exchange',1],conclusion='Retained state passes e49state and advances through e49run to the next append in a stable mocked census. Exact actual Refusal cause is not recoverable from error_type alone; injected census refusal is only an ambiguity demonstration.',source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),snapshot_sha256=hashlib.sha256(SNAP.read_bytes()).hexdigest(),trace=trace),indent=2))
