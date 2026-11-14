"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual Root61 data + exact original227 consumer projection, never live observation.
"""
from pathlib import Path
import ast,copy,importlib.util,json
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('actual61_consumer_shape',D/'observe_current61_original227.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ledger,free,ext,actors=m.validate_current(m.CURRENT)
assert len(ledger['consumed_nonces'])==70 and len(actors)==61
capture=m.checked(m.PINS['capture2'])
physical=m.consumer_value(capture,capture['observed_clocks'],capture['last_observed_clocks'],capture['fixed_cutoffs'],capture['boot_id'])
checks=['genuine actualRoot61/free6c83/capture2 +61actorrows retained validation']
tree=ast.parse((D/'cohort/capture_fresh_startup_resource.py').read_bytes())
keys=set()
assertions=[]
for node in ast.walk(tree):
 if isinstance(node,ast.Subscript) and isinstance(node.value,ast.Name) and node.value.id=='physical':
  value=node.slice.value if isinstance(node.slice,ast.Index) else node.slice
  if isinstance(value,ast.Constant):keys.add(value.value)
 if isinstance(node,ast.Assert) and any(isinstance(x,ast.Name)and x.id=='physical' for x in ast.walk(node)):assertions.append(node)
assert len(keys)>=10 and 'Root61' in keys and 'Root59' not in keys
for key in keys:assert key in physical,key
checks.append('all exact original227 physical consumer keys present with Root61 branch')
st=dict(root_ledger35=m.CURRENT['ledger'],latest_serial_operation_physical_acceptance=m.CURRENT['latest_free'])
exec(compile(ast.fix_missing_locations(ast.Module(body=assertions,type_ignores=[])),'EXACT_ORIGINAL227_PHYSICAL_ASSERTIONS_ONLY','exec'),dict(physical=physical,st=st))
checks.append('unchanged exact original227 physical assertions pass against actualcapture2 projection')
for badkey in ['Root61','capacity','running_container_observation','retained_stopped_observation']:
 bad=copy.deepcopy(physical);bad.pop(badkey)
 try:
  for key in keys:bad[key]
 except KeyError:checks.append('reject missing consumer field '+badkey)
 else:raise AssertionError('missingkey accepted')
assert physical['Root61']==m.CURRENT['ledger'] and physical['actual_latest_operation_postjoin_acceptance']==m.CURRENT['latest_free']
assert physical['actual_latest_operation_postjoin_acceptance']!=capture['previous_accepted_free_boundary']
checks.append('new currentfree6c83 explicitly differs from oldf76')
for name in ['run_native_startup_capture.py','bind_startup_resource.py']:
 assert '(1793253600.0, 1035705.5689454618, 1051043.6959931096)' in (D/'cohort'/name).read_text()
checks.append('all original227 helper inheritedclamps preserve actual earliestmin')
result=dict(scope=__doc__.splitlines()[0],decision='PASS_ACTUAL61_EXACT_ORIGINAL227_PHYSICAL_CONSUMER_SHAPE',checks=checks,count=len(checks),physical_keys=sorted(keys),root61=m.CURRENT['ledger'],current_free=m.CURRENT['latest_free'],guard_calls=0,observations=0,runtime_authority=None)
with (D/'ACTUAL-CONSUMER-CONTROLS.json').open('x')as out:out.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
