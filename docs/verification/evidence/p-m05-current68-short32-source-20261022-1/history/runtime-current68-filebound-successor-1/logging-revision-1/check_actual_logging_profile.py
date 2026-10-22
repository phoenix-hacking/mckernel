"""Affected actual M05 Docker logging predicates; no Docker execution.

Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
"""
from pathlib import Path
import ast, copy, hashlib, importlib.util, json

D = Path(__file__).resolve().parent
F = D.parent
S = F.parent
op = json.loads((F / 'EXACT-SHORT32-M05-RUNTIME-OPERATION-NOT-RELEASED.json').read_text())
spec = importlib.util.spec_from_file_location('actual_bounded_logging_owner', D / 'native_diagnostic_container_owner.py')
o = importlib.util.module_from_spec(spec)
spec.loader.exec_module(o)
i = object.__new__(o.DiagnosticOwner)
i.parent = Path(op['argv'][op['argv'].index('--attempt-parent') + 1])
i.name = 'fixture-M05-SHORT32-boundedlogs'
i.container = 'd' * 64
i.nonce = op['nonce']
i.label = 'mckernel.native-diagnostic.owner=' + i.nonce
i.owner_sha = hashlib.sha256(Path(o.SELF).read_bytes()).hexdigest()
i.manifest_path = op['argv'][op['argv'].index('--manifest') + 1]
i.manifest_sha256 = op['argv'][op['argv'].index('--manifest-sha256') + 1]
argv = i._create_argv()
for flag in ('--log-driver=json-file', '--log-opt=max-size=16m', '--log-opt=max-file=2'):
    assert argv.count(flag) == 1
assert len([v for v in argv if v.startswith('--log-driver=')]) == 1
assert len([v for v in argv if v.startswith('--log-opt=')]) == 2
assert 'fsize=33554432:33554432' in argv and '--pids-limit=512' in argv
assert '--memory=12g' in argv and '--memory-swap=12g' in argv
assert '--cpus=4' in argv and '--cpuset-cpus=2-5' in argv and '--network=none' in argv
assert i._inside_args()[1] == o.SELF

# Exact accepted complete Config/HostConfig/row fixture constructors, with
# Dockerinspect as the explicitly modeled live edge and only LogConfig data
# changed to this new exact requested per-container logger profile.
fixture = Path('/home/holden/mckernel-work/host-preparation/p-m06-current68-native-stage-binding-20261022-1/native-runtime-ready-1/check_fsize_profile_correction1.py')
tree = ast.parse(fixture.read_text())
pairs = []
for index, value in enumerate(argv):
    if value == '--mount':
        items = argv[index + 1].split(',')
        fields = dict(item.split('=', 1) for item in items if '=' in item)
        pairs.append((fields['src'], fields['dst'], 'readonly' in items))
for name in ('config', 'h'):
    node = next(n for n in tree.body if isinstance(n, ast.Assign)
                and isinstance(n.targets[0], ast.Name) and n.targets[0].id == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(fixture), 'exec'), globals())
h['LogConfig'] = dict(Type='json-file', Config={'max-size': '16m', 'max-file': '2'})
h['Mounts'] = [dict(Type='bind', Source=x, Target=y, ReadOnly=ro) for x, y, ro in pairs]
node = next(n for n in tree.body if isinstance(n, ast.Assign)
            and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'row')
exec(compile(ast.Module(body=[node], type_ignores=[]), str(fixture), 'exec'), globals())
i._profile(row, {'Config': {}})
print('PASS actual createargv and complete production profile exact json-file/16m/2 with SHORT32 preserved')
cases = [
    ('missing LogConfig', None),
    ('wrong driver', dict(Type='local', Config={'max-size': '16m', 'max-file': '2'})),
    ('missing options', dict(Type='json-file', Config={})),
    ('wrong max-size', dict(Type='json-file', Config={'max-size': '32m', 'max-file': '2'})),
    ('wrong max-file', dict(Type='json-file', Config={'max-size': '16m', 'max-file': '3'})),
    ('extra option', dict(Type='json-file', Config={'max-size': '16m', 'max-file': '2', 'compress': 'true'})),
]
for label, log in cases:
    bad = copy.deepcopy(row)
    if log is None:
        del bad['HostConfig']['LogConfig']
    else:
        bad['HostConfig']['LogConfig'] = log
    try:
        i._profile(bad, {'Config': {}})
    except o.OwnerError as error:
        assert type(error) is o.OwnerError and str(error) == 'exact bounded container log sink'
    else:
        raise AssertionError(label + ' accepted')
    print('PASS actual complete profile refuses', label)
print(json.dumps(dict(status='PASS_SEVEN_AFFECTED_LOGGING_PROFILE_CASES',
    missing_wrong_driver_or_options_refusals=6, actual_Docker_commands=0,
    daemon_configuration_changes=0, VM=0, native_apps=0, runtime_release=False)))
