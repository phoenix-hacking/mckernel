"""Actual whole d55 consumer plus three pure guard mutations; no approvals."""
from pathlib import Path
import hashlib, importlib.util, json
D=Path(__file__).resolve().parent
pins=json.loads((D/'INPUTS.json').read_bytes());p=Path(pins['decoder']['path']);raw=p.read_bytes()
assert len(raw)==pins['decoder']['bytes'] and hashlib.sha256(raw).hexdigest()==pins['decoder']['sha256']
s=importlib.util.spec_from_file_location('actual_whole_terminal_consumer',p)
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
t=m.checked(pins['physical']);projection=m.project(t,pins['physical'])
assert set(projection)=={'boot_id','filesystem_uuid','container_id','owner_nonce','lease_path','common_exclusion','shared_heavy'}
assert projection['container_id']==t['container_id'] and projection['owner_nonce']==t['owner_nonce']
reasons=[]
def refuses(action, expected):
 try:action()
 except ValueError as error:
  assert str(error)==expected,(str(error),expected)
  reasons.append(str(error));return
 raise AssertionError('required actual current guard refusal absent')
# Mutate only actual pure guard inputs in memory. No fabricated approval,
# report file or physical receipt is published or accepted by these negatives.
absent=t['ordinary_exact_absence_check'];paths=absent['paths']
refuses(lambda:m.absence_join(dict(absent,uid=1000),paths,True),'exact source-kind independent lease/quarantine/common/shared absence')
refuses(lambda:m.terminal_kind(dict(t,schema='unknown.cleanup.kind')),'exact existing cleanup physical kind')
engine=m.checked(pins['engine']);release=m.checked(pins['release'])
assert engine['release_sha256']!=pins['release']['sha256']
refuses(lambda:m.release_hash_join(dict(engine,release_sha256='0'*64),t['full_journal'],release,True),'actual canonical release/journal hash')
result=dict(status='PASS_ACTUAL_WHOLE_CURRENT_PHYSICAL_CONSUMER_AND_THREE_REFUSALS_ONLY',cases=4,whole_actual_consumer_positive=True,uid_kind_hash_negatives=True,negative_reasons=reasons,physical=pins['physical'],decoder=pins['decoder'],actual_projection=projection,external_file_SHA=pins['release']['sha256'],internal_canonical_SHA=engine['release_sha256'],root_operations=0,guest_runs=0,snapshot=None,runtime_release=None)
with(D/'RESULT.json').open('x')as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(dict(status=result['status'],cases=4,root_operations=0,guest_runs=0)))
