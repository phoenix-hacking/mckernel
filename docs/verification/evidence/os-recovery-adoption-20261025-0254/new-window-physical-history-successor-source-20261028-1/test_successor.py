"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source/predicate regressions; no physical/guard/Docker execution.
"""
from pathlib import Path
import ast
import copy
import importlib.util
import json
import types

D = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('physical_successor_tested', D / 'physical_history_successor.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
checks = []


def reject(call, label):
    try:
        call()
    except (AssertionError, ValueError, KeyError):
        checks.append(label)
    else:
        raise AssertionError('negative accepted: ' + label)


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


chain = m.source_chain()
assert len(chain) == 8
checks.append('eight exact source dependencies authenticate')
guard_ref = dict(path='/synthetic/source-only/guard.py', bytes=1, sha256='0' * 64)
reports = {}
for path, reference in chain.items():
    original = ast.parse(Path(path).read_bytes())
    changed, changes = m.transformed(path, guard_ref)
    compile(changed, path + ':TEST_ONLY', 'exec')
    # Every physical assertion is byte-for-byte identical as AST except explicit
    # historical __file__ provenance. Only the expired inline guard loader is replaced.
    def predicates(tree):
        result = []
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name != 'current_window_guard':
                for child in ast.walk(node):
                    if isinstance(child, ast.Assert):
                        result.append(ast.dump(child, include_attributes=False))
        return result
    normalized = m.SuccessorTransform(path, guard_ref).visit(ast.parse(Path(path).read_bytes()))
    assert predicates(normalized) == predicates(changed)
    before = predicates(original)
    after = predicates(changed)
    assert len(before) == len(after)
    # Assert node differences may only be the historical __file__ name expression.
    for before_node, after_node in zip(before, after):
        if before_node != after_node:
            expected = before_node.replace("Name(id='__file__', ctx=Load())", 'Constant(value=' + repr(path) + ')')
            assert expected == after_node
    reports[path] = dict(assertions_preserved=len(after), adaptations=changes)
checks.append('all physical assertions preserved across eight source successors')
root51 = load(m.ROOT, 'retained_root51_predicates')
root51.validate_retained()
checks.append('actual Root51 retained custody and both HOST result predicates')
original_checked = root51.checked
for key, value in [('complete_within_declared_current_boundary', False), ('consumed_nonces', [])]:
    def checked(reference, key=key, value=value):
        result = original_checked(reference)
        if reference == root51.PINS['ledger']:
            result = copy.deepcopy(result)
            result[key] = value
        return result
    root51.checked = checked
    reject(root51.validate_retained, 'Root51 rejects altered ' + key)
root51.checked = original_checked
root49 = load(root51.PINS['base']['path'], 'retained_root49_predicates')
root49.validate_retained()
checks.append('actual Root49 positive holder retirement predicates')
reject(m.binding, 'unconfigured successor refuses observation dependency')
# No live dispatch: replace only underlying subprocess call with a recorder.
old_subprocess = m.subprocess
old_binding = m._BINDING
runtime = dict(historical_sources=chain)
m._BINDING = (dict(path='/source-only/binding', sha256='f' * 64), runtime)
m.binding = lambda: runtime
seen = []
m.subprocess = types.SimpleNamespace(run=lambda argv, *a, **kw: seen.append((argv, a, kw)))
docker = ['/usr/bin/sudo', '-A', '/usr/bin/docker', 'inspect', 'actual-retained-CID']
m.successor_run(docker, capture_output=True, text=True, timeout=15)
assert seen[-1] == (docker, (), dict(capture_output=True, text=True, timeout=15))
checks.append('Docker argv and capture/timeout remain exact')
argv = ['/home/holden/anaconda3/bin/python3', '-I', '-B', str(m.ROOT)]
m.successor_run(argv, capture_output=True, timeout=40)
assert seen[-1][0][:3] == argv[:3] and seen[-1][2] == dict(capture_output=True, timeout=40)
assert '--historical' in seen[-1][0] and '--runtime-binding-sha256' in seen[-1][0]
checks.append('observer children retain interpreter isolation and timeout with explicit binding')
m.subprocess = old_subprocess
m._BINDING = old_binding
out = dict(scope=__doc__.splitlines()[0], status='PASS_PURE_PHYSICAL_SUCCESSOR_SOURCE_AND_ACTUAL_RETAINED_PREDICATES', checks=checks, count=len(checks), source_reports=reports, observations=0, guard_calls=0, Docker_calls=0, runtime_authority=None)
with (D / 'PURE-CONTROLS.json').open('x') as stream:
    stream.write(json.dumps(out, indent=2) + '\n')
print(json.dumps(dict(status=out['status'], count=len(checks), physical_assertions=sum(r['assertions_preserved'] for r in reports.values()), observations=0, guard_calls=0, Docker_calls=0)))
