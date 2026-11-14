#!/usr/bin/env python3
"""This exact case's no-effect source/manifest/create/QEMU admission check."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent

def need(ok, why):
    if not ok:
        raise ValueError(why)

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def checked(row):
    p = Path(row['path'])
    st = p.lstat()
    data = p.read_bytes()
    need(st.st_mode == row['mode'] and len(data) == row['bytes'] and
         hashlib.sha256(data).hexdigest() == row['sha256'], 'source pin drift')
    return data

pins = json.loads((HERE / 'source-pins.json').read_text())
current = pins['current_owner']
prior = pins['prior_source_body_owner']
newbody, oldbody = checked(current), checked(prior)
need(current['path'] == str(HERE / 'native_diagnostic_container_owner.py'), 'one current owner path')
for row in pins['HERE_siblings']:
    need(checked(row['accepted']) == checked(row['private']), 'HERE sibling byte drift')
    need(Path(row['private']['path']).parent == HERE, 'HERE source locality')
for key in ('unchanged_absolute_RUNNER', 'unchanged_absolute_bound_manifest_diagnostic'):
    checked(pins[key])
oldtree, newtree = ast.parse(oldbody), ast.parse(newbody)
class Normalize(ast.NodeTransformer):
    def __init__(self):
        self.path_count = self.mount_count = 0
    def visit_Assign(self, node):
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if 'SELF' in names:
            need(ast.literal_eval(node.value) == current['path'], 'current SELF')
            node.value = ast.Constant(prior['path'])
            self.path_count += 1
        elif 'EXTRA_READONLY' in names:
            roots = ast.literal_eval(node.value)
            need(roots[-1] == str(HERE.parent) and roots.count(str(HERE.parent)) == 1, 'one exact private RO prefix')
            node.value = ast.parse(repr(roots[:-1]), mode='eval').body
            self.mount_count += 1
        return node
norm = Normalize()
normalized = norm.visit(newtree)
need(norm.path_count == norm.mount_count == 1 and ast.dump(oldtree, include_attributes=False) == ast.dump(normalized, include_attributes=False), 'unrelated owner AST drift')

binding = json.loads((HERE / 'binding.json').read_text())
engine = load('m02_existing_binding_engine_no_main', HERE / 'native_owner_binding.py')
result = engine.verify(binding)
need(result['clocks_or_host_effects'] == 0 and result['native_execution_release'] is None, 'no-effect contract')
need(result['owner_argv'][2] == current['path'] and result['owner_argv'][4] == current['sha256'], 'outer current owner pin')
inside = result['inside_owner_argv']
need(inside[1] == current['path'] and inside[4] == current['sha256'], 'inside current owner pin')
create = result['container_create_argv']
need(create[-len(inside):] == inside, 'create inside suffix')

def readonly_roots(argv):
    roots = []
    for i, value in enumerate(argv[:-1]):
        if value == '--mount':
            fields = argv[i+1].split(',')
            if fields[0] == 'type=bind' and 'readonly' in fields:
                roots.append(next(v[4:] for v in fields if v.startswith('src=')))
    return roots

def require_owner_mount(argv):
    ownerpath = Path(current['path'])
    roots = [Path(p) for p in readonly_roots(argv)]
    need(any(ownerpath == p or p in ownerpath.parents for p in roots), 'current owner read-only mount missing')
require_owner_mount(create)
missing = list(create)
mount = 'type=bind,src=' + str(HERE.parent) + ',dst=' + str(HERE.parent) + ',readonly'
i = missing.index(mount)
need(missing[i-1] == '--mount', 'mount pair')
del missing[i-1:i+1]
try:
    require_owner_mount(missing)
except ValueError as exc:
    need(str(exc) == 'current owner read-only mount missing', 'wrong mount refusal')
else:
    raise AssertionError('missing current owner mount accepted')
# Genuine strict manifest-row hash refusal, before create/backend/clock access.
bad = dict(binding, manifest=dict(binding['manifest'], sha256='0' * 64))
try:
    engine.verify(bad)
except ValueError as exc:
    need(str(exc) == 'M03 staged scratch manifest identity changed', 'wrong stale manifest refusal')
else:
    raise AssertionError('stale manifest pin accepted')
qmp = result['paths']['qmp_socket']
need(result['paths']['qmp_socket_bytes'] == len(os.fsencode(qmp)) <= 107, 'actual AF_UNIX bound')
qemu = result['qemu_argv']
need(qemu[qemu.index('-qmp')+1] == 'unix:' + qmp + ',server=on,wait=off', 'full QEMU QMP join')
need(not os.path.lexists(result['paths']['attempt']), 'fresh attempt namespace')
parent = Path(binding['attempt_parent'])
need(not os.path.lexists(parent.with_name(parent.name + '.owner-' + binding['nonce'])), 'fresh owner evidence namespace')
print(json.dumps(dict(status='PASS_WHOLE_SOURCE_NO_EFFECT_PREFLIGHT_ONLY', current_owner=current,
    actual=result, checks=dict(byte_identical_HERE_siblings=5, owner_AST_only_SELF_and_RO_prefix=True,
    missing_current_owner_mount_refused=True, stale_manifest_pin_refused=True),
    native_timeout_acceptance=False, future_LAST=None, runtime_release=None), sort_keys=True))
