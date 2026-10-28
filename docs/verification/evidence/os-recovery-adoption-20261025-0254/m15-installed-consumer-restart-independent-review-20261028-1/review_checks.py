"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Independent read-only byte comparisons and pure parser controls; no real guard entry.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path('/home/holden/mckernel')
PACKET = ROOT / 'docs/verification/evidence/os-recovery-adoption-20261025-0254/m15-installed-consumer-restart-20261028-1'
HERE = Path(__file__).resolve().parent
contract = json.loads((PACKET / 'PRELINK-CONTRACT.json').read_bytes())
spec = importlib.util.spec_from_file_location('reviewed_guard', PACKET / 'prelink_reuse_guard.py')
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)

def ref(path):
    data = path.read_bytes()
    return dict(path=str(path), bytes=len(data), sha256=hashlib.sha256(data).hexdigest())

bindings = {}
for name in ['SOURCE-READY.json', 'RESULT.md', 'PRELINK-CONTRACT.json',
             'GUARDED-CURRENT-CONSUMER-RECIPE.json', 'prelink_reuse_guard.py',
             'CMakeLists.txt.candidate', 'ihkconfig-runtime-component.ihk-relative.patch']:
    bindings[name] = ref(PACKET / name)
assert bindings['SOURCE-READY.json']['sha256'] == '31413165357bb231f8ee1ebf4437b97c6e9d0fc497183ffa532f0a2dc78cb7f8'
accepted_source = Path(contract['accepted_source_host_root'])
accepted_sdk = Path(contract['accepted_sdk_host_root'])
unchanged = 0
for relative, expected in contract['current_source_files'].items():
    path = PACKET / 'CMakeLists.txt.candidate' if relative == 'ihk/linux/user/CMakeLists.txt' else ROOT / relative
    actual = ref(path)
    assert actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256'], relative
    if relative != 'ihk/linux/user/CMakeLists.txt':
        assert path.read_bytes() == (accepted_source / relative).read_bytes(), relative
        unchanged += 1
for relative, expected in contract['accepted_sdk_files'].items():
    actual = ref(accepted_sdk / relative)
    assert actual['bytes'] == expected['bytes'] and actual['sha256'] == expected['sha256'], relative
assert sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'ihk/linux/include').rglob('*.h')) == contract['header_paths']
assert sorted(str(p.relative_to(accepted_sdk)) for p in (accepted_sdk / 'ihk/linux/include').rglob('*.h')) == contract['generated_header_paths']

# Independently reconstruct the sole selector edit: unchanged target paths and
# full-install target membership, plus one named CLI runtime component.
old = (ROOT / 'ihk/linux/user/CMakeLists.txt').read_text()
before = 'install(TARGETS "ihkconfig" "ihkosctl"\n'
after = '''# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Select the already-built management CLI alone without unrelated user targets.
# An unqualified install still includes both runtime components.
install(TARGETS "ihkconfig"
\tRUNTIME DESTINATION "${CMAKE_INSTALL_SBINDIR}" COMPONENT ihkconfig_runtime
\tLIBRARY DESTINATION "${CMAKE_INSTALL_LIBDIR}"
\tARCHIVE DESTINATION "${CMAKE_INSTALL_LIBDIR}")
install(TARGETS "ihkosctl"
'''
assert old.count(before) == 1
assert old.replace(before, after) == (PACKET / 'CMakeLists.txt.candidate').read_text()

rust = (ROOT / 'ihk/linux/user/rust/ihkconfig.rs').read_text()
assert rust.count('env!("IHKCONFIG_BUILDID")') == 1
assert 'const BUILDID_CAPACITY: usize = env!("IHKCONFIG_BUILDID").len() + 1;' in rust
assert rust.count('BUILDID_CAPACITY') == 3
for relative in contract['current_source_files']:
    if relative.endswith('.rs') and 'whole70/' in relative:
        assert 'BUILDID' not in (ROOT / relative).read_text(), relative

old_config = (accepted_sdk / 'ihk/config.h').read_bytes()
assert b'#define BUILDID "3114d9e"' in old_config
controls = []
def positive(name, data, expected_mode):
    actual = guard.config_compatibility(old_config, data)
    assert actual['capacity'] == 8 and actual['mode'] == expected_mode
    controls.append(dict(name=name, expected='ACCEPT', result='PASS', configuration=actual))
def negative(name, data):
    try:
        guard.config_compatibility(old_config, data)
    except ValueError as error:
        controls.append(dict(name=name, expected='REJECT', result='PASS', reason=str(error)))
    else:
        raise AssertionError('unexpected acceptance: ' + name)

positive('identical-real-accepted-config', old_config, 'IDENTICAL')
positive('seven-character-current-abbreviation', old_config.replace(b'3114d9e', b'a7ddca2'), 'ONLY_EQUAL_CAPACITY_BUILDID')
negative('eight-character-current-abbreviation-is-incompatible', old_config.replace(b'3114d9e', b'a7ddca26'))
negative('real-CMake-version-fallback-is-incompatible', old_config.replace(b'3114d9e', b'1.7.0rc4'))
negative('same-width-feature-drift', old_config.replace(b'ENABLE_PERF 1', b'ENABLE_PERF 0').replace(b'3114d9e', b'a7ddca2'))
negative('C-string-escape-is-not-an-ASCII-literal', old_config.replace(b'3114d9e', b'12345\\n'))
negative('duplicate-whitespace-directive', old_config + b'\n # define BUILDID "a7ddca2"\n')
negative('non-ASCII-seven-byte-ID', old_config.replace(b'3114d9e', b'123456\xff'))

result = dict(scope=__doc__.splitlines()[0], status='PASS_INDEPENDENT_BYTE_AND_PURE_BUILDID_CONTROLS',
              source_files=len(contract['current_source_files']), unchanged_accepted_source_files=unchanged,
              accepted_sdk_files=len(contract['accepted_sdk_files']), public_headers=len(contract['header_paths']),
              generated_headers=len(contract['generated_header_paths']), exact_selector_edit=True,
              bindings=bindings, controls=controls, positive_controls=2, negative_controls=6,
              actual_configure=0, actual_compiler=0, actual_link=0, actual_install=0,
              actual_guard=0, actual_cli=0, actual_native=0, default_compiler_credit=False,
              file_closure=False)
(HERE / 'CHECKS.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
print(json.dumps({k: result[k] for k in ['status', 'source_files', 'unchanged_accepted_source_files',
                                      'accepted_sdk_files', 'positive_controls', 'negative_controls']}, sort_keys=True))
