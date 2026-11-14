"""Affected real M05 binding/default-profile checks; root publication modeled.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
from pathlib import Path
from unittest.mock import patch
import ast, copy, hashlib, importlib.util, json, os, socket, subprocess

D = Path(__file__).resolve().parent
S = D.parent
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
adapter = load('actual_private_M05_case', D / 'case_evaluator.py')
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
    for label, path, digest in (
            ('wrong manifest', str(actual_path), packet['actual_manifest']['sha256']),
            ('wrong hash', str(planned), '0' * 64)):
        try:
            adapter.binding(path, digest)
        except Exception as error:
            # The real adapter wraps its exact path/hash refusal in the real
            # diagnostic error class loaded for that invocation.
            assert type(error).__name__ == 'DiagnosticError'
            assert str(error) == 'M05 binding: M05 exact normalized manifest'
        else:
            raise AssertionError(label + ' accepted')
        print('PASS', label, 'refused by actual M05 adapter')

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
# The selected unchanged M05 profile has core0/nofile4096, without the separate
# 199 fsize32 extension. Preserve that exact qualified default; do not widen it.
h['Ulimits'] = [row for row in h['Ulimits'] if row['Name'] != 'fsize']
node = next(n for n in tree.body if isinstance(n, ast.Assign)
            and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'row')
h['Mounts'] = [dict(Type='bind', Source=x, Target=y, ReadOnly=ro) for x, y, ro in pairs]
exec(compile(ast.Module(body=[node], type_ignores=[]), str(fixture), 'exec'), context)
i._profile(row, {'Config': {}})
print('PASS complete actual default M05 production profile and matching create/requested/actual five added readonly roots')
for label, section, reason in (
        ('missing requested extra readonly root', 'HostConfig', 'requested mount identities'),
        ('missing actual extra readonly root', 'actual', 'actual mount identities')):
    bad = copy.deepcopy(row)
    if section == 'HostConfig':
        bad['HostConfig']['Mounts'] = [m for m in bad['HostConfig']['Mounts'] if m['Source'] != str(S)]
    else:
        bad['Mounts'] = [m for m in bad['Mounts'] if m['Source'] != str(S)]
    try:
        i._profile(bad, {'Config': {}})
    except o.OwnerError as error:
        assert type(error) is o.OwnerError and str(error) == reason
    else:
        raise AssertionError(label + ' accepted')
    print('PASS', label, 'refused by complete actual profile guard')

print(json.dumps(dict(status='PASS_SIX_AFFECTED_ACTUAL_M05_RUNTIME_BINDING_CHECKS',
    projected_edges=['absent root scratch manifest canonical path/read transport',
                     'modeled Docker image/default profile/inspect metadata'],
    real_manifest_sha256=packet['actual_manifest']['sha256'],
    actual_source_and_artifact_guards=True, root_publications=0,
    stages=0, Docker=0, VM=0, native_apps=0, runtime_release=False)))
