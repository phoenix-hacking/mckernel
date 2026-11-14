"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Additive unexecuted argv correction: accepted Python3.9 for supervisor callers.
"""
from pathlib import Path
import copy,hashlib,json
E=Path(__file__).resolve().parent
old=E/'REVIEW-READY-NEXT-STAGE-PACKET.json';raw=old.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='3f28e1e73b43d1b503aa61bbe0d801404c1714336b9e1eabfefa3b5dce722cf7'
packet=json.loads(raw);changes=[]
for group in ['operations_in_order','conditional_following_227']:
 for row in packet[group]:
  argv=row['argv'];before=copy.deepcopy(argv);i=argv.index('/usr/bin/timeout');j=argv.index('/usr/bin/python3',i+1);argv[j]='/home/holden/anaconda3/bin/python3'
  assert [n for n in range(len(argv))if argv[n]!=before[n]]==[j]
  changes.append(dict(operation=row['name'],changed_argv_index=j,old=before[j],new=argv[j]))
packet['status']='SOURCE_STATIC_DATA_READY_ACCEPTED_PY39_OUTER_CALLERS_NOT_STAGE_RELEASED'
packet['supersedes_unexecuted_argv_only']={'path':str(old),'sha256':hashlib.sha256(raw).hexdigest()}
packet['outer_interpreter_correction']={'reason':'Observed prior restoration child0 capture failed because Python3.8 lacks os.waitstatus_to_exitcode. Accepted Python3.9 supervisor caller avoids unchanged deterministic observer failure. Frozen inner snapshot/overlay/patch argv unchanged.','changes':changes,'stage_executions':0}
out=E/'REVIEW-READY-NEXT-STAGE-PACKET.PY39.json'
with out.open('x')as f:json.dump(packet,f,sort_keys=True,indent=2);f.write('\n')
print(json.dumps(dict(status=packet['status'],path=str(out),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),changed_outer_callers=len(changes))))
