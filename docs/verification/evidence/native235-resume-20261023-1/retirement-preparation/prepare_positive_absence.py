"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import ast,difflib,hashlib,json,os
D=Path(__file__).resolve().parent;assert os.sched_getaffinity(0)=={7}
S=D/'readonly_current_mutex_paths.py';P=D/'CURRENT-FAILED235-RETIREMENT-PACKET.json'
for p in (S,P):
 q=D/(p.name+'.candidate1');q.open('xb').write(p.read_bytes())
a=S.read_text();old="need(all(not os.path.lexists(p) for p in paths),'fresh exact current SDK/image/launcher ownership paths absent')";assert a.count(old)==1
function="""def require_absence(paths):
 for path in paths:
  try:
   os.lstat(path)
  except FileNotFoundError as exc:
   if exc.errno != errno.ENOENT:
    raise
  else:
   raise RuntimeError('ownership path present: '+os.fspath(path))
"""
b=a.replace('import fcntl,json,os\n','import errno,fcntl,json,os\n',1).replace("need(os.geteuid()==0,'authenticated root read-only observation')",function+"need(os.geteuid()==0,'authenticated root read-only observation')",1).replace(old,'require_absence(paths)')
N=D/'readonly_current_mutex_paths_positive.py';N.write_text(b);ast.parse(b)
(D/'POSITIVE-ABSENCE-CORRECTION.diff').write_text(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile=S.name,tofile=N.name)))
packet=json.loads(P.read_text());original=next(r for r in packet['additional_readonly_observation_commands']if r['source']['path'].endswith('readonly_current_mutex_paths.py'))
argv=original['argv'][:];argv[-1]=str(N.resolve())
def ref(p):
 r=p.read_bytes();return dict(path=str(p.resolve()),bytes=len(r),sha256=hashlib.sha256(r).hexdigest())
r=dict(scope=__doc__,status='ONE_BOUNDED_POSITIVE_ABSENCE_CORRECTION_PENDING_FOCUSED_REVIEW',source=ref(N),argv=argv,original_source=ref(S),frozen_reviewed_packet=ref(P),source_delta='Only require_absence lstat/ENOENT predicate replaces lexists; original mutex27:4 identity/acquire/readback/release unchanged.',failure_family=dict(findings=1,bounded_corrections=1,history='Candidate1 lexists suppresses OSError and cannot prove absence; one correction prepared; no unchanged replay.'),review=None,root_Docker_native_operations=0,physical_acceptance=False)
(D/'POSITIVE-ABSENCE-OPERATION.json').write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(source=r['source'],status=r['status'])))
