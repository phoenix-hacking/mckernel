"""Functional OS driver JSON publication regression only; no security testing.
AST-extract only the JSON helper; never import/execute the build driver.
"""
import ast
import hashlib
import json
import os
from pathlib import Path
import traceback
import uuid

ROOT = Path(__file__).resolve().parent
inputs = json.loads((ROOT / 'inputs.json').read_text())
work = ROOT / 'regression-output'
work.mkdir()

def helper(path, gate):
    source = Path(path).read_text()
    tree = ast.parse(source)
    nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_atomic_json']
    assert len(nodes) == 1
    namespace = dict(Path=Path, uuid=uuid, json=json, os=os, _check_signal=gate)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), path, 'exec'), namespace)
    return namespace['_atomic_json']

ref = inputs['compile_database']
raw = Path(ref['path']).read_bytes()
assert len(raw) == ref['bytes'] and hashlib.sha256(raw).hexdigest() == ref['sha256']
rows = json.loads(raw)
assert isinstance(rows, list) and rows and all(isinstance(row, dict) for row in rows)
original = helper(inputs['original_driver'], lambda: None)
try:
    original(work / 'original-list.json', rows)
except AttributeError as error:
    assert str(error) == "'list' object has no attribute 'get'"
    (ROOT / 'original-reproduction.traceback.txt').write_text(traceback.format_exc())
else:
    raise AssertionError('original defect did not reproduce')
assert not (work / 'original-list.json').exists()
calls = []
corrected = helper(inputs['corrected_driver'], lambda: calls.append('signal-check'))
cases = [ ('actual-list-fresh', rows), ('dict-no-status', {'commands': []}),
          ('dict-nonpass', {'status': 'FAIL'}), ('dict-pass-fixture', {'status': 'PASS'}) ]
for name, value in cases:
    dest = work / (name + '.json')
    old_count = len(calls)
    corrected(dest, value)
    assert json.loads(dest.read_text()) == value
    assert len(calls) - old_count == int(isinstance(value, dict) and value.get('status') == 'PASS')
dest = work / 'actual-list-fresh.json'
corrected(dest, rows)
assert json.loads(dest.read_text()) == rows
assert not list(work.glob('actual-list-fresh.json.tmp-*'))
class Interrupted(Exception):
    pass
def interrupt():
    raise Interrupted('fixture interrupt before PASS publication')
blocked = helper(inputs['corrected_driver'], interrupt)
dest = work / 'interrupted-pass.json'
try:
    blocked(dest, {'status': 'PASS'})
except Interrupted:
    pass
else:
    raise AssertionError('PASS signal gate bypassed')
assert not dest.exists()
# Existing evidence is an immutable input; validate its original recorded binding.
evidence = Path(inputs['original_evidence'])
receipt = json.loads((evidence / 'receipt.json').read_text())
provenance = (evidence / 'provenance.json').read_bytes()
assert len(provenance) == 43309288
assert hashlib.sha256(provenance).hexdigest() == receipt['inventory']['provenance.json']['sha256']
assert receipt['commands'] == [] and receipt['phase'] == 'identity'
assert receipt['error'] == "'list' object has no attribute 'get'"
print(json.dumps(dict(result='all 7 functional helper checks passed',
    checks=['original retained-list failure reproduced', 'actual list fresh publication',
            'actual list replacement publication', 'dict without status', 'dict nonPASS',
            'dict PASS fixture invokes signal gate', 'interrupted PASS fixture not published'],
    retained_compile_rows=len(rows), original_provenance_bytes=len(provenance),
    scope='source helper regression only; no compiler/build/native acceptance'), indent=2))
