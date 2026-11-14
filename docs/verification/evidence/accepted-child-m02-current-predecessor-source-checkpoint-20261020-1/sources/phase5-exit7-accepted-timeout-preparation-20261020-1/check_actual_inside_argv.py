#!/usr/bin/env python3
"""Finite source-body check. No owner import, process, Docker, or guest."""
import ast
import json
import math
import re
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent
OLD = Path('/home/holden/mckernel-work/host-preparation/phase5-exit7-grace-retry-binding-20261020-1/runtime-source-1/native_diagnostic_container_owner.py')
NEW = HERE / 'native_diagnostic_container_owner.py'
RUNNER = OLD.parent / 'native_diagnostic_runner.py'

def need(ok, reason):
    if not ok:
        raise ValueError(reason)

oldtree, newtree = (ast.parse(p.read_text()) for p in (OLD, NEW))
# Normalize exactly the two approved literals, requiring unique matches.
class Normalize(ast.NodeTransformer):
    def __init__(self):
        self.path_count = self.timeout_count = 0
    def visit_Assign(self, node):
        if any(isinstance(t, ast.Name) and t.id == 'SELF' for t in node.targets):
            need(isinstance(node.value, ast.Constant) and node.value.value == str(NEW), 'SELF candidate')
            node.value.value = str(OLD)
            self.path_count += 1
        return self.generic_visit(node)
    def visit_FunctionDef(self, node):
        if node.name == '_inside':
            for item in ast.walk(node):
                if isinstance(item, ast.Constant) and item.value == '40':
                    item.value = '300'
                    self.timeout_count += 1
        return self.generic_visit(node)
normal = Normalize()
normalized = normal.visit(ast.parse(NEW.read_text()))
need(normal.path_count == normal.timeout_count == 1, 'exact two literal changes')
need(ast.dump(oldtree, include_attributes=False) == ast.dump(normalized, include_attributes=False), 'whole owner AST drift')

inside = next(n for n in newtree.body if isinstance(n, ast.FunctionDef) and n.name == '_inside')
assignments = {}
for node in newtree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in ('SELF', 'RUNNER', 'QEMU', 'QEMU_SHA256', 'QEMU_VERSION_STDOUT'):
                assignments[target.id] = ast.literal_eval(node.value)
seen = []
class ExecReached(Exception):
    pass

def execve(path, argv, env):
    seen.append((path, argv, env))
    raise ExecReached()

ns = dict(assignments, need=need, HEX=re.compile(r'[0-9a-f]{64}'), re=re, Path=Path,
          os=SimpleNamespace(getuid=lambda: 1000, geteuid=lambda: 1000,
                             path=SimpleNamespace(lexists=lambda p: False), execve=execve),
          private_parent=lambda p: None, _manifest_outside_writable_parent=lambda *a: None,
          _manifest_identity=lambda *a: None, bound_manifest=lambda *a: None,
          _digest=lambda p: 'a' * 64 if p == str(NEW) else assignments['QEMU_SHA256'],
          bounded_command=lambda *a: SimpleNamespace(returncode=0, stderr=b'', stdout=assignments['QEMU_VERSION_STDOUT']))
exec(compile(ast.Module(body=[inside], type_ignores=[]), str(NEW), 'exec'), ns)
try:
    ns['_inside']('/private/p', 'b' * 32, 'a' * 64, '/readonly/manifest.json', 'c' * 64)
except ExecReached:
    pass
need(len(seen) == 1, 'one exec construction')
argv = seen[0][1]
need(argv == ['/usr/bin/python3', '-B', str(RUNNER), '--manifest', '/readonly/manifest.json',
              '--attempt-parent', '/private/p', '--attempt-name', 'attempt-' + 'b' * 32,
              '--timeout', '40'], 'actual inside argv')
try:
    ns['_inside']('/private/p', 'bad', 'a' * 64, '/readonly/manifest.json', 'c' * 64)
except ValueError as e:
    need(str(e) == 'inside nonce', 'wrong refusal')
else:
    raise AssertionError('invalid nonce accepted')
need(len(seen) == 1, 'refusal reached exec')
runner = ast.parse(RUNNER.read_text())
timeout = next(n for n in runner.body if isinstance(n, ast.FunctionDef) and n.name == '_timeout')
rns = {'math': math}
exec(compile(ast.Module(body=[timeout], type_ignores=[]), str(RUNNER), 'exec'), rns)
need(rns['_timeout']('40') == 40, 'accepted runner deadline')
for bad in ('0', '-1', 'nan', 'inf', '3601', 'junk'):
    try:
        rns['_timeout'](bad)
    except ValueError:
        pass
    else:
        raise AssertionError('invalid deadline accepted: ' + bad)
print(json.dumps({'status': 'PASS_SOURCE_BODY_ONLY', 'whole_owner_AST_except_two_literals_equal': True,
                  'actual_inside_argv_deadline': '40', 'invalid_nonce_preexec_refused': True,
                  'invalid_deadline_vectors_refused': 6, 'processes_Docker_guests': 0}))
