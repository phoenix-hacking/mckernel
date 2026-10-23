"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure exact-receipt guards and rejection vectors; all process factories forbidden.
"""
from pathlib import Path
import ast, copy, hashlib, json, subprocess, types

D = Path(__file__).resolve().parent
P = D / 'bound-fail-retired-source-1'
factories = []
def forbidden(*args, **kwargs):
    factories.append(repr(args)[:160])
    raise AssertionError('No process factory allowed in pure receipt fixture')
for name in ('Popen', 'run', 'check_call', 'check_output', 'call'):
    setattr(subprocess, name, forbidden)

def load(path, pin):
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == pin
    module = types.ModuleType('_receipt_pure_' + path.stem)
    module.__file__ = str(path)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module

m = load(P / 'cleanup_pass_image.py', 'aff2d2d925779252cfede0010f2fa9fd336420d17127cdecd2d86d06b2204f9e')
o = load(P / 'observe_current_pass_image_retirement.py', '742ee092aa703592772f389bbf5f04626ada87352a900db7068888a98d7a2f12')
case = json.loads((P / 'FAILED-CASE-STATIC.PENDING.json').read_bytes())
ret = json.loads((P / 'CURRENT-RETAINED-BUILD-AUTHORITY.HOLD.json').read_bytes())
hold = json.loads((P / 'CURRENT-LIVE-POSTJOIN.HOLD.json').read_bytes())
artifact = json.loads((D / 'ACTUAL-CLOSED-FAILED-BUILD-AND-RETAINED-OWNERSHIP.json').read_bytes())
owner = json.loads(Path(case['finite_roles']['owner_receipt']['path']).read_bytes())
guard = json.loads(Path(case['finite_roles']['outer_status']['path']).read_bytes())
inspection = json.loads(Path(case['finite_roles']['terminal_inspection']['path']).read_bytes())
assert len(inspection) == 1
item = inspection[0]
assert item['Id'] == case['target']['container_id'] and item['State']['ExitCode'] == 1
assert case['successful_artifacts_required'] is False
o.decode_finite_case(case)
o.current_pass_prerequisites(ret, case, hold, artifact)
m.image_owner_receipt_binding(owner, item, case['finite_roles']['owner_receipt']['sha256'])
m.image_receipt_binding(owner, guard, case['target'], item, case['finite_roles']['owner_receipt']['sha256'])
passed = ['actual_finite_case_decode', 'actual_failed_prerequisites', 'actual_owner_retired_full_current_inspect', 'actual_closed_FAIL1_capture']
refused = []
def reject(name, call):
    try:
        call()
    except (m.Refusal, RuntimeError):
        refused.append(name)
    else:
        raise AssertionError('Invalid fact accepted: ' + name)

for key, value in [('status', 'PASS'), ('retired', False), ('terminal_container_retained', False), ('cleanup_separately_required', False), ('error', 'different failure'), ('exit_code', 0), ('client_retirement_unproven', True)]:
    changed = copy.deepcopy(owner)
    changed[key] = value
    reject('owner_' + key, lambda changed=changed: m.image_owner_receipt_binding(changed, item, case['finite_roles']['owner_receipt']['sha256']))
for key, value in [('status', 'PASS'), ('returncode', 0), ('direct_child_joined', False), ('process_group_absent', False), ('streams_closed', False), ('pid', 1), ('proc_start_ticks', '1')]:
    changed = copy.deepcopy(guard)
    changed[key] = value
    reject('outer_' + key, lambda changed=changed: m.image_receipt_binding(owner, changed, case['target'], item, case['finite_roles']['owner_receipt']['sha256']))
changed = copy.deepcopy(item)
changed['Config']['Labels']['mckernel.owner'] = 'different-owner'
reject('fresh_inspect_owner_changed', lambda: m.image_owner_receipt_binding(owner, changed, case['finite_roles']['owner_receipt']['sha256']))
for section, key, value in [('driver', 'error', 'different observer'), ('driver', 'status', 'PASS'), ('owner', 'retired', False), ('owner', 'status', 'PASS')]:
    changed = copy.deepcopy(artifact)
    changed[section][key] = value
    reject('prerequisite_' + section + '_' + key, lambda changed=changed: o.current_pass_prerequisites(ret, case, hold, changed))
changed = copy.deepcopy(case)
changed['successful_artifacts_required'] = True
reject('cannot_claim_successful_artifacts', lambda: o.current_pass_prerequisites(ret, changed, hold, artifact))
changed = copy.deepcopy(hold)
changed['physical_clearance'] = True
reject('cannot_claim_physical_clearance', lambda: o.current_pass_prerequisites(ret, case, changed, artifact))
reject('no_cleanup_without_independent_exact_release', lambda: m.configure({}, execute=True))
assert not factories
print(json.dumps(dict(scope=__doc__, status='PASS_ACTUAL_FAILED_RECEIPT_AND_PURE_REJECTION_VECTORS_ONLY', positive_cases=passed, rejected_cases=refused, process_factories=factories, compiler=False, root_queries=False, cleanup=False, physical_clearance=False, client_births=None), sort_keys=True))
