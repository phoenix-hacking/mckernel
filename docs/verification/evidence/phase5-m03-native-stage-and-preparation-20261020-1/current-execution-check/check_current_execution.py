"""Three actual current execution-role checks only, no physical projection."""
from pathlib import Path
import copy, hashlib, importlib.util, json
D=Path(__file__).resolve().parent
pins=json.loads((D/'INPUTS.json').read_bytes())
p=Path(pins['decoder']['path']);raw=p.read_bytes()
assert len(raw)==pins['decoder']['bytes'] and hashlib.sha256(raw).hexdigest()==pins['decoder']['sha256']
s=importlib.util.spec_from_file_location('actual_current_execution_helper',p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
execution=m.checked(pins['execution_review']);release=m.checked(pins['execution_release'])
target=m.execution_join(execution,pins['execution_review'],release)
assert target==execution['cleanup_payload_without_execution_review']['observation']['target']
reasons=[]
def refuses(action, expected):
 try:action()
 except ValueError as error:
  assert str(error)==expected,(str(error),expected)
  reasons.append(str(error));return
 raise AssertionError('required current-execution refusal absent')
changed=dict(pins['execution_review'],bytes=pins['execution_review']['bytes']+1)
refuses(lambda:m.checked(changed),'bounded regular physical descriptor')
changed=copy.deepcopy(release);changed['execution_review']['evidence_sha256']='0'*64
refuses(lambda:m.execution_join(execution,pins['execution_review'],changed),'exact actual full current inline review SHA and payload ownership')
result=dict(status='PASS_THREE_CURRENT_EXECUTION_AUTHORITY_HELPER_CASES_ONLY',cases=3,positive_actual_current_body_inline_target=True,changed_FD_length_refused=True,changed_inline_report_SHA_refused=True,negative_reasons=reasons,execution_review=pins['execution_review'],execution_release=pins['execution_release'],decoder=pins['decoder'],actual_physical_report=None,actual_physical_projection=None,snapshot=None,runtime_release=None,root_operations=0,guest_runs=0)
with(D/'RESULT.json').open('x')as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(dict(status=result['status'],cases=3,root_operations=0,guest_runs=0)))
