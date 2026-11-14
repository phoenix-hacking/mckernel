#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only request metadata and actual production preflight extraction. No owner
import, subprocess, observer, admission, namespace creation or workload.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import stat
HERE = Path(__file__).resolve().parent
JOIN = json.loads((HERE / 'ATTEMPT4-REQUEST-SOURCE-AND-REUSE-JOIN.NOT-GRANTED.json').read_text())
DELTA = json.loads((HERE / 'EXACT-ORIGIN586-TO-ATTEMPT4-REQUEST-DIFFERENCES.json').read_text())
PLAN = json.loads(Path(JOIN['namespace_plan']['path']).read_text())
RESULTS = []
def need(condition, message='metadata check failed'):
    if not condition:
        raise AssertionError(message)
def auth(row):
    path = Path(row['path'])
    raw = path.read_bytes()
    need(len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'], 'exact metadata source changed')
    return raw
def check(name, action):
    action()
    RESULTS.append(dict(name=name, status='PASS'))
def reject(action):
    try:
        action()
    except (AssertionError, RuntimeError, ValueError, KeyError):
        return
    raise AssertionError('negative accepted')
REQUEST = json.loads(auth(JOIN['request']))
ORIGIN = json.loads(auth(DELTA['origin']))
PREDECESSOR = json.loads(auth(DELTA['receipt_family_predecessor']))
SENTINEL = dict(ABSENT_FROM_ORIGIN=True)
def differences(before, after):
    return {key: dict(operation='add' if key not in before else 'remove' if key not in after else 'replace', before=before.get(key, SENTINEL), after=after.get(key, SENTINEL)) for key in sorted(set(before) | set(after)) if key not in before or key not in after or before[key] != after[key]}
def validate(candidate):
    need(differences(ORIGIN, candidate) == DELTA['origin_differences'], 'actual origin586 delta differs')
    need(differences(PREDECESSOR, candidate) == DELTA['predecessor_differences'], 'actual predecessor4d delta differs')
    need(len(DELTA['origin_differences']) == DELTA['origin_difference_count'] and len(DELTA['predecessor_differences']) == DELTA['predecessor_difference_count'])
    need(set(candidate) - set(ORIGIN) == {'image_receipt_candidate_sha', 'readonly_reuse_inputs'})
    need(set(candidate) >= set(ORIGIN))
    need(candidate['driver_path'] == JOIN['driver']['path'] and candidate['driver_sha256'] == JOIN['driver']['sha256'])
    need(candidate['readonly_reuse_inputs'] == JOIN['readonly_reuse_inputs']['path'])
    need(candidate['source_manifest'] == JOIN['base_manifest']['path'] and candidate['source_manifest_sha256'] == JOIN['base_manifest']['sha256'])
    need(candidate['host_owner_path'] == JOIN['host_control_owner']['path'] and candidate['host_owner_sha256'] == JOIN['host_control_owner']['sha256'])
    need(candidate['image_receipt_candidate_sha'] == '942c927b1ec93cc31284ff498455909d9bb2d0fc' and candidate['candidate_sha'] == 'eb3ce544eb1f479a56933a5c7fa8300ab6dfe533')
    need(candidate['candidate_sha'] != candidate['image_receipt_candidate_sha'])
    base = Path(PLAN['namespace_base'])
    expected = dict(work_root=base/'owner-work', owner_evidence_root=base/'owner-evidence', output_root=base/'owner-work/output', evidence_root=base/'owner-work/evidence', attempt_root=base/'owner-evidence/attempt', common_exclusion_path=base/'common-exclusion.json', lease_path=base/'lease.json')
    need(all(candidate[key] == str(value) for key, value in expected.items()))
    need(not os.path.lexists(base) and all(not os.path.lexists(value) for value in expected.values()), 'planned namespace must still be absent')
check('whole-actual-request-and-exact-origin586-predecessor4d-deltas', lambda: validate(REQUEST))
for name, updates in [
    ('wrong-driver-path', {'driver_path': '/stale-driver.py'}),
    ('wrong-driver-hash', {'driver_sha256': '0' * 64}),
    ('wrong-readonly-seed-input', {'readonly_reuse_inputs': '/arbitrary-seed.json'}),
    ('wrong-work-namespace', {'work_root': '/stale/owner-work'}),
    ('wrong-lease-namespace', {'lease_path': '/stale/lease.json'}),
    ('wrong-base-candidate', {'candidate_sha': REQUEST['image_receipt_candidate_sha']}),
    ('coerced-image-candidate', {'image_receipt_candidate_sha': REQUEST['candidate_sha']}),
    ('unexpected-request-key', {'unexpected': True}),
    ('stale-source-manifest', {'source_manifest_sha256': '1b84900fd841d43a836cded0ed8d3ac6188b5bb7f84dffcf112f8ad34ed3549d'}),
    ('image-owner-confused-with-host-role', {'host_owner_sha256': JOIN['owner']['sha256']}),
    ('stale-provenance', {'provenance_sha256': '0' * 64}),
]:
    check(name, lambda updates=updates: reject(lambda: validate(dict(REQUEST, **updates))))
def missing_seed():
    candidate = dict(REQUEST)
    del candidate['readonly_reuse_inputs']
    reject(lambda: validate(candidate))
check('missing-readonly-seed-key', missing_seed)
def canonical_and_base_join():
    auth(JOIN['base_manifest'])
    fixed = json.loads(auth(JOIN['readonly_reuse_inputs']))
    need(fixed['base_manifest'] == JOIN['base_manifest'] and fixed['archive'] == JOIN['seed_archive'])
    need([row for row in fixed['objects'] if not row['replace']] == JOIN['reused_objects'] and len(JOIN['reused_objects']) == 9)
    need([row for row in fixed['objects'] if row['replace']] == JOIN['replacement_objects'] and len(JOIN['replacement_objects']) == 2)
    for row in JOIN['canonical_three_postimages']:
        need(auth(row['canonical']) == auth(row['readonly_selected_postimage']))
    need(JOIN['configuration_mode'] == 'REUSED_CONFIGURATION_DERIVED_CURRENT_DEFAULT_COMMANDS' and JOIN['base69_and9793_remain_original_scope'] is True)
    physical = json.loads(auth(JOIN['current_physical']))
    need(physical['schema'] == JOIN['current_physical_schema'] and physical['decision'] == JOIN['current_physical_decision'])
    need(all(JOIN[key] is None for key in ['actual_PID','actual_five','actual_holder','actual_namespace_identities','actual_root_context','actual_root_grants','actual_fresh_admission_clock']))
check('actual-canonical-three-postimages-base-seed-nine-objects-and-physical-schema-join', canonical_and_base_join)

def actual_production_preflight():
    text = auth(JOIN['owner']).decode()
    names = {'_fail','_sha256','_canonical','_regular','_load_json','_reuse_require','_reuse_file','_reuse_layout','_reuse_authenticate','_reuse_preflight_request_crossrefs','preflight_request_crossrefs'}
    assignments = {'_REUSE_FIXED','_REUSE_INPUT_SHA256','_REUSE_INPUT_BYTES','_REUSE_IDENTITY_BASELINE','_REUSE_DRIVER_SHA256','_REUSE_HOST_INPUT_PATH'}
    nodes = [node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name in names or isinstance(node, ast.ClassDef) and node.name == 'OwnerError' or isinstance(node, ast.Assign) and any(isinstance(target,ast.Name) and target.id in assignments for target in node.targets)]
    namespace = dict(Path=Path,hashlib=hashlib,json=json,os=os,re=re,stat=stat)
    exec(compile(ast.Module(body=nodes,type_ignores=[]), '<actual-production-readonly-preflight-only>', 'exec'),namespace)
    need(namespace['_REUSE_DRIVER_SHA256'] == JOIN['driver']['sha256'] and namespace['_REUSE_HOST_INPUT_PATH'] == JOIN['readonly_reuse_inputs']['path'])
    observed = namespace['preflight_request_crossrefs'](REQUEST)
    need(observed['status'] == 'PASS_DETERMINISTIC_REQUEST_CROSSREFS_ONLY' and observed['driver_sha256'] == JOIN['driver']['sha256'])
check('actual-production-effect-free-owner-preflight-real-request-seed-manifests-driver', actual_production_preflight)
print(json.dumps(dict(scope=__doc__,status='PASS_ATTEMPT4_REQUEST_METADATA_AND_ACTUAL_READONLY_PREFLIGHT',tests=len(RESULTS),results=RESULTS,owner_imported=False,subprocesses=0,namespaces_created=0,live_admission=False),sort_keys=True))
