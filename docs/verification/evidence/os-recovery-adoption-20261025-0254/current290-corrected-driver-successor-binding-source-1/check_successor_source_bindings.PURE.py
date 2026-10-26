#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source binding regression; no owner import, command dispatch or output namespace mutation.
"""
import ast
import copy
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent

def reference(path):
    path = Path(path)
    raw = path.read_bytes()
    return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())

def assigned(tree, name):
    return [n.value for n in tree.body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == name for t in n.targets)]

def main():
    plan = json.loads((D / 'SUCCESSOR-BINDING-PLAN.SOURCE-ONLY.NOT-GRANTED.json').read_text())
    delta = json.loads((D / 'REQUEST-SUCCESSOR-EXACT-DELTA.SOURCE-ONLY.NOT-GRANTED.json').read_text())
    for row in (plan['old_driver'], plan['corrected_driver'], plan['old_owner'],
                plan['successor_owner'], delta['base'], plan['request_delta'],
                *plan['unchanged_closures'].values()):
        assert reference(row['path']) == row
    old = json.loads(Path(delta['base']['path']).read_text())
    successor = copy.deepcopy(old)
    for item in delta['replacements']:
        key = item['pointer'].removeprefix('/')
        assert '/' not in key and successor[key] == item['before']
        successor[key] = item['after']
    expected_keys = {'attempt_root', 'common_exclusion_path', 'evidence_root', 'lease_path',
                     'output_root', 'owner_evidence_root', 'work_root', 'driver_path', 'driver_sha256'}
    assert {k for k in old if old[k] != successor[k]} == expected_keys
    for key in plan['unchanged_request_fields']:
        assert successor[key] == old[key]
    root = delta['namespace_root']
    assert not Path(root).exists()
    assert successor['driver_path'] == plan['corrected_driver']['path']
    assert successor['driver_sha256'] == plan['corrected_driver']['sha256']
    assert plan['mount_binding']['provenance']['host'] == old['provenance_path']
    assert reference(old['provenance_path']) == plan['unchanged_closures']['provenance']
    before = ast.parse(Path(plan['old_owner']['path']).read_bytes())
    after = ast.parse(Path(plan['successor_owner']['path']).read_bytes())
    assert ast.literal_eval(assigned(after, '_REUSE_DRIVER_SHA256')[0]) == successor['driver_sha256']
    assert ast.literal_eval(assigned(after, 'COMMON_EXCLUSION')[0]) == successor['common_exclusion_path']
    # The frozen three-postimage/nine-object descriptor is identical.
    assert ast.dump(assigned(before, '_REUSE_FIXED')[0]) == ast.dump(assigned(after, '_REUSE_FIXED')[0])
    # Production callable bodies, including the mounted driver/provenance argv, are unchanged.
    functions = lambda tree: [ast.dump(n) for n in tree.body
                              if isinstance(n, (ast.FunctionDef, ast.ClassDef))]
    assert functions(before) == functions(after)
    old_common = old['common_exclusion_path']
    retired = assigned(after, 'RETIRED_COMMON_EXCLUSIONS')
    assert any(old_common in [n.value for n in ast.walk(v) if isinstance(n, ast.Constant)] for v in retired)
    driver = ast.parse(Path(plan['corrected_driver']['path']).read_bytes())
    assert any(isinstance(n, ast.Import) and any(a.name == 'native_rust_exact_build_offline'
               for a in n.names) for n in driver.body)
    print(json.dumps(dict(status='PASS_PURE_SOURCE_BINDINGS', exact_request_replacements=9,
                         unchanged_callable_bodies=True, unchanged_reuse_descriptor=True,
                         namespace_absent=True, owner_imported=False,
                         compiler_or_container_run=False), sort_keys=True))

if __name__ == '__main__':
    main()
