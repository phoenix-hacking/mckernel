"""Record current Rust consumers; source selection is not runtime acceptance."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

repo = Path('/workspace')
out = Path('/work/rust-consumers-20260907.json')
baseline_path = 'docs/verification/rust-reuse-baseline-24a151fe.json'
baseline = json.loads((repo / baseline_path).read_text())
old = {row['path']: row for row in baseline['files']}
paths = subprocess.check_output(
    ['git', '-C', str(repo), 'ls-files', '--cached', '--others',
     '--exclude-standard', '-z', '--', '*.rs']).decode().split('\0')
paths = sorted(set(path for path in paths if path))

def identity(path):
    data = path.read_bytes()
    return dict(sha256=hashlib.sha256(data).hexdigest(), size=len(data))

def modules(root):
    result = set()
    pending = [root]
    while pending:
        path = pending.pop()
        if path in result:
            continue
        result.add(path)
        source = (repo / path).read_text()
        for match in re.finditer(
            r'(?:#\[path\s*=\s*"([^"\n]+)"\]\s*)?'
            r'^(?:pub(?:\([^)]*\))?\s+)?mod\s+(\w+)\s*;',
            source, re.MULTILINE):
            child = match.group(1) or match.group(2) + '.rs'
            pending.append(str(Path(path).parent / child))
    return result

kernel = modules('kernel/rust/lib.rs')
kernel_files = {path for path in paths if path.startswith('kernel/rust/')}
if kernel != kernel_files:
    raise SystemExit('McKernel module inventory differs: ' + repr(kernel ^ kernel_files))
cmake = (repo / 'kernel/CMakeLists.txt').read_text()
source_block = cmake.split('set(RUST_KERNEL_SRCS', 1)[1].split('\n\t)', 1)[0]
dependencies = {'kernel/' + path for path in re.findall(
    r'\$\{CMAKE_CURRENT_SOURCE_DIR\}/(rust/[^"\n]+\.rs)', source_block)}
missing_dependencies = sorted(kernel - dependencies)
extra_dependencies = sorted(dependencies - kernel)

manifest_path = 'host-kernel/kbuild/stage-manifest.json'
manifest = json.loads((repo / manifest_path).read_text())
native_roots = [row['source']['repository_path'] for row in manifest['modules']]
native_graph = {root: sorted(modules(root)) for root in native_roots}
native = set().union(*(set(values) for values in native_graph.values()))
staged = {row['repository_path'] for row in manifest['inputs']
          if row['repository_path'].endswith('.rs')} | set(native_roots)
if native != staged:
    raise SystemExit('Native module graph differs from staged inputs: ' + repr(native ^ staged))

common_tools = {'mcexec_helpers', 'mcinspect_helpers', 'eclair_helpers',
                'arch_eclair_x86_64', 'libsched_yield', 'ldump2mcdump_helpers'}
qlmpi_tools = {'qlmpilib', 'qlfort', 'ql_server', 'ql_talker'}
uti_tools = {'syscall_intercept', 'archdep_uti_x86_64'}
rows = []
for path in paths:
    source = repo / path
    if source.is_symlink() or not source.is_file():
        raise SystemExit('Unexpected source: ' + path)
    build = []
    pending = None
    if path in kernel:
        disposition = 'compatibility_mckernel_crate'
        build = ['kernel/rust/lib.rs', 'kernel/CMakeLists.txt']
        pending = 'Native Linux 6.12 McKernel boot and retirement of remaining C implementation.'
    elif path in native:
        disposition = 'native_kbuild_module_graph'
        build = [manifest_path] + [root for root, members in native_graph.items() if path in members]
        pending = 'Per-capability native runtime acceptance; staging does not prove every function is used.'
    elif path == 'host-kernel/native-rust/ihk_mapping.rs':
        disposition = 'native_foundation_pending_adapter'
        build = ['scripts/ihk_mapping_check.py', 'scripts/tests/test_ihk_mapping_check.py']
        pending = 'Connect the existing mapping model to native mappings and OS resource ownership.'
    elif path == 'executer/kernel/mcctrl/rust/mcctrl_helpers.rs':
        disposition = 'compatibility_mcctrl_pending_native_adaptation'
        build = ['executer/kernel/mcctrl/CMakeLists.txt']
        pending = 'Adapt existing Rust bodies to native Linux services and remove project C bridge dependencies.'
    elif path.startswith('executer/user/rust/'):
        build = ['executer/user/CMakeLists.txt']
        name = source.stem
        if name in common_tools:
            disposition = 'compatibility_default_user_tool'
            pending = 'Use preserved tools in native end-to-end workload tests.'
        elif name in qlmpi_tools:
            disposition = 'optional_qlmpi_disabled'
            pending = 'Build and validate with ENABLE_QLMPI=ON before claiming this configuration.'
        elif name in uti_tools:
            disposition = 'optional_uti_disabled'
            pending = 'Build and validate with ENABLE_UTI=ON before claiming this configuration.'
        else:
            raise SystemExit('Unclassified user source: ' + path)
        if '/rust/' + source.name not in (repo / build[0]).read_text():
            raise SystemExit('Missing tool build source: ' + path)
    elif path == 'tools/mcstat/rust/mcstat.rs':
        disposition = 'compatibility_default_user_tool'
        build = ['tools/mcstat/CMakeLists.txt']
        pending = 'Compare duplicated policy with mcstat_helpers.rs and retain relevant regression cases.'
    elif path == 'tools/mcstat/rust/runtest.rs':
        disposition = 'explicit_tool_test_target_excluded_from_all'
        build = ['tools/mcstat/CMakeLists.txt']
        pending = 'Invoke mcstat_runtest explicitly; the default build does not select it.'
    elif path == 'tools/mcstat/rust/mcstat_helpers.rs':
        disposition = 'historical_tool_helper_comparison_consumer'
        build = ['kernel/rust/tests/run_equivalence.sh']
        pending = 'Compare parser, formatting and control policy against active mcstat.rs; consolidate proven common bodies.'
    elif path == 'tools/crash/rust/mckernel_crash_helpers.rs':
        disposition = 'separate_crash_extension_build'
        build = ['tools/crash/CMakeLists.txt', 'tools/crash/mckernel.mk.in']
        pending = 'Validate the separate extension with its crash headers; source copying alone is not a build.'
    elif path.startswith('scripts/tests/'):
        disposition = 'verification_fixture'
        build = ['scripts/tests']
    else:
        raise SystemExit('Unclassified Rust source: ' + path)
    for consumer in build:
        if not (repo / consumer).exists():
            raise SystemExit('Missing consumer: ' + consumer)
    digest = identity(source)
    state = 'added' if path not in old else (
        'unchanged' if digest['sha256'] == old[path]['sha256'] else 'modified')
    rows.append(dict(path=path, **digest, raw_lines=len(source.read_bytes().splitlines()),
                     disposition=disposition, source_consumers=build,
                     baseline_state=state, pending=pending))

removed = sorted(set(old) - set(paths))
if removed:
    raise SystemExit('Baseline Rust source removed: ' + repr(removed))
inputs = sorted({baseline_path, manifest_path, 'kernel/rust/lib.rs', 'kernel/CMakeLists.txt',
                 'executer/kernel/mcctrl/CMakeLists.txt', 'executer/user/CMakeLists.txt',
                 'tools/mcstat/CMakeLists.txt', 'tools/crash/CMakeLists.txt',
                 'tools/crash/mckernel.mk.in', 'kernel/rust/tests/run_equivalence.sh'})
cache_path = Path('/work/compat-build-pageattrs-20260907/CMakeCache.txt')
cache = dict(re.findall(r'^(ENABLE_\w+):BOOL=(ON|OFF)$', cache_path.read_text(), re.MULTILINE))
configuration = {name: cache[name] == 'ON' for name in (
    'ENABLE_RUST_KERNEL', 'ENABLE_RUST_IHK_MODULE_HELPERS',
    'ENABLE_RUST_USER_TOOLS', 'ENABLE_QLMPI', 'ENABLE_UTI')}
if configuration != dict(ENABLE_RUST_KERNEL=True, ENABLE_RUST_IHK_MODULE_HELPERS=True,
                         ENABLE_RUST_USER_TOOLS=True, ENABLE_QLMPI=False, ENABLE_UTI=False):
    raise SystemExit('Update the consumer dispositions for the changed build configuration')
record = dict(schema='mckernel-rust-consumer-inventory-v1',
              created_utc=datetime.now(timezone.utc).isoformat(),
              source_parent=subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD']).decode().strip(),
              scope='Main repository Rust source selection; x86_64 compatibility configuration and current native staging.',
              caveat='File/crate inclusion is not per-function execution, native integration, absence of C, or whole-OS completion.',
              configuration=configuration,
              configuration_input=dict(path=str(cache_path), **identity(cache_path)),
              baseline_revision=baseline['source_revision'], removed_baseline_files=removed,
              preservation_counts=dict(Counter(row['baseline_state'] for row in rows)),
              disposition_counts=dict(Counter(row['disposition'] for row in rows)),
              kernel_crate_files=len(kernel), cmake_missing_dependencies=missing_dependencies,
              cmake_extra_dependencies=extra_dependencies, native_module_graph=native_graph,
              input_identities=[dict(path=path, **identity(repo / path)) for path in inputs],
              files=rows, production_gate_credit=False, complete_unification_claimed=False)
out.write_text(json.dumps(record, indent=2, sort_keys=True) + '\n')
print(json.dumps({key:record[key] for key in ('kernel_crate_files', 'cmake_missing_dependencies',
                 'preservation_counts', 'disposition_counts')}, indent=2))
