"""Affected real M05 binding/default-profile checks; root publication modeled.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
from pathlib import Path
from unittest.mock import patch
import ast, copy, hashlib, importlib.util, json, os, socket, subprocess

D = Path(__file__).resolve().parent
S = D.parent
P = S / 'runtime-current68-successor-1'
packet = json.loads((S / 'ACTUAL-P05-STAGE-TO-M05-RUNTIME-PACKET-1.json').read_text())
actual_path = S / 'actual-stage-1/manifest.json'
actual_raw = actual_path.read_bytes()
assert hashlib.sha256(actual_raw).hexdigest() == packet['actual_manifest']['sha256']
planned = Path(packet['publication']['manifest'])


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def forbidden(*args, **kwargs):
    raise AssertionError('no process/socket/backend/root/guest effects')


subprocess.Popen = forbidden
socket.socket = forbidden
os.execve = forbidden
o = load('actual_private_M05_owner', D / 'native_diagnostic_container_owner.py')
adapter = load('actual_private_M05_case', P / 'case_evaluator.py')
runner = load('actual_private_M05_runner', D / 'native_diagnostic_runner.py')

# Only the root-owned, absent scratch manifest publication is projected. Every
# artifact, overlay receipt, source and decoder below is read from its real FD
# or Path. No producer object, plan, map or guard result is replaced.
original_resolve = Path.resolve
original_read_bytes = Path.read_bytes
original_regular = o.regular


def resolve(self, *args, **kwargs):
    if self == planned:
        return self
    return original_resolve(self, *args, **kwargs)


def read_bytes(self):
    if self == planned:
        return actual_raw
    return original_read_bytes(self)


def regular(path, maximum=o.LIMIT):
    if Path(path) == planned:
        assert len(actual_raw) <= maximum
        return actual_raw
    return original_regular(path, maximum)


with patch.object(Path, 'resolve', resolve), patch.object(Path, 'read_bytes', read_bytes), \
        patch.object(o, 'regular', regular):
    nd, frozen = o.bound_manifest(str(planned), packet['actual_manifest']['sha256'])
    diagnostic, backend = runner._runtime()
    backend.process_factory = forbidden
    backend.qmp_factory = forbidden
    assert diagnostic.__file__ == str(runner._HERE / 'native_diagnostic.py')
    assert backend.__file__ == str(runner._HERE / 'native_diagnostic_backend.py')
    manifest = diagnostic.load_manifest(str(planned))
    runner._bind_m05(diagnostic, manifest, planned)
    assert diagnostic._same_plan(diagnostic._freeze(diagnostic._thaw(manifest)),
                                 diagnostic._freeze(diagnostic._thaw(frozen)))
    assert diagnostic.evaluate.__name__ == 'case_evaluate'
    assert frozen['staging']['collector']['sha256'].startswith('f0435be1')
    assert frozen['payload']['oracle'] == adapter.ORACLE
    _, consumer, _ = adapter.binding(str(planned), packet['actual_manifest']['sha256'])
    for name, entry in (('workload', 'evaluate'), ('lifecycle', 'validate_lifecycle_capture'),
                        ('transport', 'decode'), ('resource', 'evaluate')):
        assert callable(getattr(consumer.bound(name), entry))
    print('PASS actual owner/qualified-default sibling runner/case/strict M05 decoder source join with real b836 artifacts and 62-member map')
# Reuse the accepted complete profile fixture's Config/HostConfig/inspect row
# construction, not a new owner model. Docker metadata is the explicit modeled
# live edge. Its CgroupnsMode is supplied; the old fixture omission is not replayed.
fixture = Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/native-runtime-ready-1/check_fsize_profile_correction1.py')
tree = ast.parse(fixture.read_text())
i = object.__new__(o.DiagnosticOwner)
i.parent = Path(packet['publication']['parent'])
i.name = 'fixture-M05-current68'
i.container = 'd' * 64
i.nonce = packet['publication']['nonce']
i.label = 'mckernel.native-diagnostic.owner=' + i.nonce
i.owner_sha = hashlib.sha256((D / 'native_diagnostic_container_owner.py').read_bytes()).hexdigest()
i.manifest_path = str(planned)
i.manifest_sha256 = packet['actual_manifest']['sha256']
argv = i._create_argv()
requested = []
for index, value in enumerate(argv):
    if value != '--mount':
        continue
    items = argv[index + 1].split(',')
    fields = dict(item.split('=', 1) for item in items if '=' in item)
    requested.append((fields['src'], fields['dst'], 'readonly' in items))
expected = [(r['source'], r['destination'], r['readonly'])
            for r in packet['readonly_mount_packet']['full_expected_mounts']]
assert requested == expected
pairs = requested
context = globals()
for name in ('config', 'h'):
    node = next(n for n in tree.body if isinstance(n, ast.Assign)
                and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(fixture), 'exec'), context)
# The affected SHORT32 M05 profile adds only exactfsize32; core0/nofile4096 stay exact.
assert any(row['Name'] == 'fsize' and row['Soft'] == row['Hard'] == 33554432 for row in h['Ulimits'])
node = next(n for n in tree.body if isinstance(n, ast.Assign)
            and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'row')
h['Mounts'] = [dict(Type='bind', Source=x, Target=y, ReadOnly=ro) for x, y, ro in pairs]
exec(compile(ast.Module(body=[node], type_ignores=[]), str(fixture), 'exec'), context)
i._profile(row, {'Config': {}})
print('PASS complete actual default M05 production profile and matching create/requested/actual five added readonly roots')
for label, change in [('missing', None), ('wrong_soft', dict(Hard=33554432, Name='fsize', Soft=33554431)), ('wrong_hard', dict(Hard=33554433, Name='fsize', Soft=33554432))]:
    bad = copy.deepcopy(row)
    bad['HostConfig']['Ulimits'] = [v for v in bad['HostConfig']['Ulimits'] if v['Name'] != 'fsize']
    if change is not None:
        bad['HostConfig']['Ulimits'].append(change)
    try:
        i._profile(bad, {'Config': {}})
    except o.OwnerError as error:
        assert type(error) is o.OwnerError and str(error) == 'ulimits'
    else:
        raise AssertionError('bad Dockerfilecap accepted: '+label)
    print('PASS actual complete Docker profile refuses', label, 'FSIZE')

# Reuse reviewed P12 exact soft/hard live-limit predicate. Getrlimit is the
# explicitly modeled OS-profile edge: the test's ordinary profile remains8MiB.
# The accepted P12 tiny OS EFBIG result is reused, never rerun here.
import resource
original_getrlimit = resource.getrlimit

def limits(value):
    return lambda kind: value if kind == resource.RLIMIT_FSIZE else original_getrlimit(kind)

with patch.object(resource, 'getrlimit', limits((33554432, 33554432))):
    for module in (o, runner, diagnostic, backend):
        module.require_short_fsize()
    spawn = backend.process_factory([backend.QEMU, '-qmp', 'unix:'+str(D/'qmp.sock')+',server=on,wait=off'], str(D), popen_factory=forbidden)
    assert callable(spawn)
print('PASS all four actual live-limit helpers and backend pre-file-acquisition accept exact SHORT32')

bare = object.__new__(o.DiagnosticOwner)
boundaries = [
    ('outer preflight', lambda: bare._preflight(), o.OwnerError),
    ('inside owner', lambda: o._inside('unavailable', 'a'*32, '0'*64, 'unavailable', '0'*64), o.OwnerError),
    ('runner before attempt', lambda: runner.run(str(planned), str(i.parent), 'attempt-'+i.nonce, 300), ValueError),
    ('diagnostic before attempt', lambda: diagnostic.prepare_attempt(None, 'unavailable', 'unavailable'), diagnostic.DiagnosticError),
    ('diagnostic before run', lambda: diagnostic.run_diagnostic(None, None), diagnostic.DiagnosticError),
    ('backend before factory files', lambda: backend.process_factory([], str(D)), ValueError),
    ('backend before spawn files/Popen', lambda: spawn(timeout=1), ValueError),
]
for value in [(-1, -1), (16777216, 16777216), (33554432, 33554433)]:
    with patch.object(resource, 'getrlimit', limits(value)):
        for label, action, expected in boundaries:
            try:
                action()
            except expected as error:
                assert type(error) is expected and str(error) == 'exact inherited SHORT32 FSIZE required'
            else:
                raise AssertionError('wrong livecap accepted at '+label)
    print('PASS seven actual pre-effect boundaries refuse livecap', value)
assert not (D/'qemu.stdout').exists() and not (D/'qemu.stderr').exists()
print(json.dumps(dict(status='PASS_AFFECTED_M05_SHORT32_PRODUCTION_GUARDS', Docker_profile_refusals=3,
    live_guard_refusals=21, actual_source_manifest_default_profile_join=True,
    root_publications=0, Docker=0, VM=0, compiler=0, native_apps=0, runtime_release=False)))
