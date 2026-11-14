"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Actual retained data and pure mutation controls; no live guard or observation.
"""
from pathlib import Path
import copy
import importlib.util
import json
D=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('typed_current60_test',D/'observe_current60_postjoin.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
rows,common,actors=m.validate_current();checks=['actual Root60/f76/native-history/4commands/53actors positive retained validation']
order=['ledger60','ledger59','profile','actual_grant','once_entry','container_claim','worker_result','terminal','runner_started','runner_join','holder_ready','holder_local_terminal','plan']
def reject(call,label):
 try:call()
 except (ValueError,AssertionError,KeyError):checks.append(label)
 else:raise AssertionError('negative accepted '+label)
def bundle(d):return m.validate_bundle(*[d[k] for k in order])
for label,edit in [
 ('reject duplicate/spent nonce',lambda d:d['ledger60']['consumed_nonces'].append(m.NONCE)),
 ('reject f76 relabeled newclearance',lambda d:d['ledger60'].__setitem__('current_physical_clearance_pending',False)),
 ('reject native relabeled ordinary',lambda d:d['ledger60']['current_native_operation'].__setitem__('nonce',m.NONCE)),
 ('reject added ordinary alias',lambda d:d['ledger60']['ordinary_operations_since_prior_heavy_boundary'].append({'nonce':m.NONCE})),
 ('reject failed build tool',lambda d:d['ledger60']['current116_build'].__setitem__('holder_tool_joined_returncode',1)),
 ('reject second invocation',lambda d:d['actual_grant'].__setitem__('maximum_invocations',2)),
 ('reject wrong once nonce',lambda d:d['once_entry'].__setitem__('nonce','0'*32)),
 ('reject native container claim',lambda d:d['container_claim'].__setitem__('native_authority',True)),
 ('reject missing compiler command',lambda d:d['worker_result']['commands'].pop()),
 ('reject failed compiler command',lambda d:d['worker_result']['commands'][0].__setitem__('returncode',1)),
 ('reject changed compiler argv',lambda d:d['worker_result']['commands'][1]['argv'].append('--changed')),
 ('reject stopped CID mismatch',lambda d:d['terminal'].__setitem__('container','0'*64)),
 ('reject OOM',lambda d:d['terminal']['state'].__setitem__('OOMKilled',True)),
 ('reject running container',lambda d:d['terminal']['state'].__setitem__('Running',True)),
 ('reject absent runner join',lambda d:d['runner_join'].__setitem__('joined',False)),
 ('reject runner birth mismatch',lambda d:d['runner_started'].__setitem__('starttime',0)),
 ('reject permanent mutex inode change',lambda d:d['holder_ready']['holder'].__setitem__('inode',5)),
 ('reject holder nonzero',lambda d:d['holder_local_terminal'].__setitem__('returncode',1)),
]:
 changed=copy.deepcopy(rows);edit(changed);reject(lambda d=changed:bundle(d),label)
A=Path(m.PINS['terminal']['path']).parent.parent
history=json.loads((A/'ROOT-PREHOLDER-PHYSICAL-1.json').read_bytes())['physical']
inspected=[dict(Id=m.CID,Name='/'+m.NAME,State=copy.deepcopy(rows['terminal']['state']))]
assert m.validate_physical(history,actors,inspected,rows['terminal'])
checks.append('actual retained preholder history and actual terminal-state projection positive pure fixture')
for label,edit in [
 ('reject live pids cgroup',lambda h:h.__setitem__('pids_current',1)),
 ('reject active heavy',lambda h:h.__setitem__('no_existing_heavy',False)),
 ('reject active shared custody',lambda h:h.__setitem__('active_shared_records_absent',False)),
 ('reject incomplete mutex probes',lambda h:h['closed_exclusive_probes'].pop()),
 ('reject incomplete census',lambda h:h['group_membership_observation']['errors'].append('fixture-error')),
 ('reject new holder group remains',lambda h:h['group_membership_observation']['rows'].append(dict(pid=999999,pgrp=1901931))),
 ('reject prior native actor remains',lambda h:h['group_membership_observation']['rows'].append(dict(pid=actors[0]['pid'],pgrp=1))),
 ('reject host storage belowfloor',lambda h:h['capacity'].__setitem__('/home/holden/mckernel',1)),
]:
 changed=copy.deepcopy(history);edit(changed);reject(lambda h=changed:m.validate_physical(h,actors,inspected,rows['terminal']),label)
bad=copy.deepcopy(inspected);bad[0]['State']['ExitCode']=1
reject(lambda:m.validate_physical(history,actors,bad,rows['terminal']),'reject changed live full State')
bad=copy.deepcopy(inspected);bad[0]['Name']='/wrong'
reject(lambda:m.validate_physical(history,actors,bad,rows['terminal']),'reject stopped CID name alias')
result=dict(scope=__doc__.splitlines()[0],decision='PASS_ACTUAL_ROOT60_TYPED_POSTJOIN_PURE_CONTROLS',checks=checks,count=len(checks),guard_calls=0,observations=0,Docker_calls=0,native_calls=0,runtime_authority=None)
with (D/'PURE-CONTROLS.json').open('x') as out:out.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
