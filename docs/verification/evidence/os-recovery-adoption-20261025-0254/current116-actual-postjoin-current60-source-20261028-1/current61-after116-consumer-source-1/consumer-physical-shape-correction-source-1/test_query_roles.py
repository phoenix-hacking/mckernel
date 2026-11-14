"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Strict real retained old52ae/new57a5 query roles, no query execution.
"""
from pathlib import Path
import copy,importlib.util,json
D=Path(__file__).resolve().parent;E=D.parent.parent.parent
p=E/'m15-rust-executor-process227-stage-and-entry-preparation-source-1/next-entry-current-boundary-source-1/known-cid-mount-order-correction-source-1/known_cid_inspect_compare.py';s=importlib.util.spec_from_file_location('actual_query_role_cmp',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
cap=json.loads((D.parent.parent/'ACTUAL-POSTJOIN-OBSERVATION-2-CPU0.json').read_bytes());host=cap['historical_Root59_native_and_physical']
old=next(q for q in host['current115_exact_CID_queries'] if 'inspect'in q['argv']);new=cap['queries'][-1]
assert old['argv'][-1].startswith('52ae') and new['argv'][-1].startswith('57a5') and old['argv'][-1]!=new['argv'][-1]
checks=['actual52ae retained priorCURRENT115 role distinct from actual57a5 ordinary116stopped role']
for role,row in [('old52ae',old),('new57a5',new)]:
 m.compare(row,row['returncode'],row['stdout'],row['stderr']);checks.append(role+' actual fullrecord positive')
 variants=[('returncode',row['returncode']+1,row['stdout'],row['stderr']),('stderr',row['returncode'],row['stdout'],row['stderr']+'changed')]
 data=json.loads(row['stdout']);bad=copy.deepcopy(data);bad[0]['State']['Status']='running';variants.append(('State.Status',row['returncode'],json.dumps(bad),row['stderr']))
 bad=copy.deepcopy(data);bad[0].pop('State');variants.append(('missingState',row['returncode'],json.dumps(bad),row['stderr']))
 for label,rc,out,err in variants:
  try:m.compare(row,rc,out,err)
  except (ValueError,AssertionError,KeyError):checks.append(role+' rejects '+label)
  else:raise AssertionError('accepted '+role+label)
result=dict(scope=__doc__.splitlines()[0],decision='PASS_ACTUAL_RETAINED_QUERY_ROLES_STRICT_FIELDS_RC_STDERR',checks=checks,count=len(checks),real_query_calls=0,runtime_authority=None)
with (D/'QUERY-ROLE-CONTROLS.json').open('x')as out:out.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
