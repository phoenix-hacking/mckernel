"""Functional OS cutoff arithmetic regression only; no clocks, guards or workloads."""
from pathlib import Path
import ast
import hashlib
import json
import math

HERE = Path(__file__).resolve().parent

def pure_namespace(name, functions):
    source = HERE/name
    tree = ast.parse(source.read_bytes())
    nodes = [n for n in tree.body if
             (isinstance(n,ast.FunctionDef) and n.name in functions) or
             (isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id == 'AUTHORIZED_FIXED_LIMITS' for t in n.targets))]
    namespace = {'math':math,'Path':Path,'A':Path('/PURE-NONRUNNABLE-CONTEXT'),
                 '__doc__':__doc__}
    exec(compile(ast.Module(body=nodes,type_ignores=[]),str(source)+':PURE_CUTOFF_FUNCTIONS_ONLY','exec'),namespace)
    return namespace

binder = pure_namespace('bind_f05_v2_resource.py',{'cutoff_triplet','validate_resource_cutoffs','packet_for'})
entry = pure_namespace('run_native_f05_v2_capture.py',{'cutoff_triplet','entry_clamps'})
authorized = list(binder['AUTHORIZED_FIXED_LIMITS'])
resource = [1793165769.0,947874.5689514667,963213.6959701729]
now = [limit-1000 for limit in resource]
observed = [value-1 for value in now]
rows = []

def check(label, accepted, call):
    try:
        value = call()
    except (ValueError,AssertionError,KeyError,TypeError,OverflowError):
        actual = False
        value = None
    else:
        actual = True
    assert actual == accepted, label
    rows.append(dict(case=label,expected_accept=accepted,result='PASS'))
    return value

value = check('exact original33microsecond tighter BOOTTIME resource',True,
              lambda:binder['validate_resource_cutoffs'](resource,authorized))
assert value == resource
check('unchanged three ceilings',True,lambda:binder['validate_resource_cutoffs'](authorized,authorized))
clamps = check('entry same live guardian as exact resource',True,
               lambda:entry['entry_clamps'](now,observed,resource,resource,resource))
assert clamps['effectiveCutoffs'] == resource
for clock in range(3):
    live = resource.copy()
    live[clock] -= .0001
    result = check('entry further guardian tightening clock'+str(clock),True,
                   lambda live=live:entry['entry_clamps'](now,observed,resource,resource,live))
    assert result['effectiveCutoffs'][clock] == live[clock]
    wider = authorized.copy()
    wider[clock] = math.nextafter(float(wider[clock]),math.inf)
    check('static ceiling widening clock'+str(clock),False,
          lambda wider=wider:binder['validate_resource_cutoffs'](resource,wider))
    declared = [v-1 for v in authorized]
    larger_resource = declared.copy()
    larger_resource[clock] = math.nextafter(larger_resource[clock],math.inf)
    check('resource exceeds static ceiling clock'+str(clock),False,
          lambda d=declared,r=larger_resource:binder['validate_resource_cutoffs'](r,d))
    r = [v-1 for v in resource]
    live = r.copy()
    live[clock] = math.nextafter(live[clock],math.inf)
    check('entry guardian widening even within authorized ceiling clock'+str(clock),False,
          lambda r=r,live=live:entry['entry_clamps'](now,observed,r,r,live))
    packet = resource.copy()
    packet[clock] -= .125
    check('entry P/R mismatch even tighter packet clock'+str(clock),False,
          lambda packet=packet:entry['entry_clamps'](now,observed,resource,packet,resource))
    age120 = now.copy()
    age120[clock] -= 120
    check('exact120second resource age rejects clock'+str(clock),False,
          lambda prior=age120:entry['entry_clamps'](now,prior,resource,resource,resource))
    future = observed.copy()
    future[clock] = now[clock]+1
    check('future resource observation rejects clock'+str(clock),False,
          lambda prior=future:entry['entry_clamps'](now,prior,resource,resource,resource))
    expired = now.copy()
    expired[clock] = resource[clock]
    check('effective deadline equality rejects clock'+str(clock),False,
          lambda current=expired:entry['entry_clamps'](current,current,resource,resource,resource))

invalid = [None,True,42,'123',{},[],[1],[1,2],[1,2,3,4],
           [True,2,3],[1,'2',3],[1,None,3]]
for bad in [math.nan,math.inf,-math.inf,0,-1]:
    for index in range(3):
        values = resource.copy()
        values[index] = bad
        invalid.append(values)
for index,bad in enumerate(invalid):
    check('malformed resource vector '+str(index),False,
          lambda bad=bad:binder['validate_resource_cutoffs'](bad,authorized))
    check('malformed static vector '+str(index),False,
          lambda bad=bad:binder['validate_resource_cutoffs'](resource,bad))
    for position in range(5):
        args = [now,observed,resource,resource,resource]
        args[position] = bad
        check('malformed entry argument '+str(position)+' vector '+str(index),False,
              lambda args=args:entry['entry_clamps'](*args))

check('119.999second resource age stays valid',True,
      lambda:entry['entry_clamps'](now,[v-119.999 for v in now],resource,resource,resource))
# Exercise the actual pure packet constructor with minimal immutable data.
static = dict(latest_serial_operation_physical_acceptance={'fixed':'physical'},root_ledger32={'fixed':'Root32'},
    fixed_cutoffs=authorized,expected_case='M14-05-05-owned-processvm-v2-204B',nonce='PURE_ONLY_NOT_A_NONCE',
    exact_argv=[],artifact_acceptance={},expected_oracle={},manifest={},scratch_manifest_stage={},attempt_parent='',
    profile={},capture_sources={},expected_new_image_sha256='',owner_source={'sha256':''},
    evaluator_source={'sha256':''},source_authority={},case_capability={},stage_map_acceptance={})
resources = dict(actual_latest_operation_postjoin_acceptance=static['latest_serial_operation_physical_acceptance'],
    boot_id='7bfc5687-6c04-4d15-84eb-b92ab9a55dcb',no_existing_heavy=True,pids_current=0,
    root_ledger32=static['root_ledger32'],fixed_cutoffs=resource)
packet = check('pure packet constructor seals actual tighter resource cutoffs',True,
               lambda:binder['packet_for'](static,{},resources,{},{}))
assert packet['fixed_cutoffs'] == resource and packet['fixed_cutoffs'] != static['fixed_cutoffs']
record = dict(scope=__doc__,status='PASS_PURE_CUTOFF_TIGHTENING_ONLY',cases=rows,count=len(rows),
    reproduced_original_static_BOOTTIME=authorized[2],actual_tighter_resource_BOOTTIME=resource[2],
    effective_resource_delta_seconds=authorized[2]-resource[2],
    helper_modules_imported=False,clocks_guards_accounts_queries_workloads_called=False)
(HERE/'PURE-CUTOFF-TEST-RESULT.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(dict(status=record['status'],count=record['count'])))
