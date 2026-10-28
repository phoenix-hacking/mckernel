#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source rebase only; no compiler, fixture, guard or subprocess invocation.
"""
import difflib
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OLD = HERE.parent
ROOT = Path('/home/holden/mckernel')
EVIDENCE = ROOT / 'docs/verification/evidence/os-recovery-adoption-20261025-0254'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'


def binding(path):
    b = path.read_bytes()
    return {'path': str(path), 'bytes': len(b), 'sha256': hashlib.sha256(b).hexdigest()}


def verify(row, actual=None):
    path = actual or Path(row['path'])
    got = binding(path)
    assert (got['bytes'], got['sha256']) == (row['bytes'], row['sha256']), str(path)
    return got


def dump(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + '\n')


adoption_path = EVIDENCE / 'restart-adoption-20261028T1911/M14-CANONICAL118-SOURCE-ADOPTION-1/ROOT-SOURCE-ADOPTION.json'
adoption_binding = binding(adoption_path)
assert adoption_binding['sha256'].startswith('c161d7b6')
adoption = json.loads(adoption_path.read_text())
assert adoption['phase'] == 'EXACT_NINE_PATH_CANONICAL_SOURCE_ADOPTED'
assert adoption['default_artifact_current'] == 116 and adoption['runtime_authority'] is None
assert len(adoption['rows']) == 9
postimages = {}
for row in adoption['rows']:
    canonical = ROOT / row['relative']
    verify(row['expected_postimage'])
    postimages[row['relative']] = verify(row['expected_postimage'], canonical)

old_ready = json.loads((OLD / 'SOURCE-READY.json').read_text())
old_files = {Path(row['path']).name: row for row in old_ready['files']}
immutable_names = ['f06_ptrace_xstate_copy_from.rs', 'abi_probe.c', 'oracle.c', 'fixture.rs',
                   'abi.snapshot.rs', 'original-xstate-copy-from.c.inc',
                   'SELECTED-CURRENT116-ARCH-FRONTIER.json']
immutable = []
for name in immutable_names:
    assert not (HERE / name).exists(), 'never overwrite rebased source inputs'
    verify(old_files[name])
    (HERE / name).write_bytes((OLD / name).read_bytes())
    immutable.append({'original': old_files[name], 'rebased_copy': binding(HERE / name)})

snapshots = {}
for relative, name in [('arch/x86_64/kernel/syscall.c', 'BASE.syscall.c'),
                       ('kernel/CMakeLists.txt', 'BASE.CMakeLists.txt'),
                       ('kernel/rust/lib.rs', 'BASE.lib.rs')]:
    assert not (HERE / name).exists()
    (HERE / name).write_bytes((ROOT / relative).read_bytes())
    verify(postimages[relative], HERE / name)
    snapshots[relative] = {'canonical': postimages[relative], 'snapshot': binding(HERE / name)}
abi = binding(ROOT / 'kernel/rust/abi.rs')
verify(abi, HERE / 'abi.snapshot.rs')
snapshots['kernel/rust/abi.rs'] = {'canonical': abi, 'snapshot': binding(HERE / 'abi.snapshot.rs')}

c = (HERE / 'BASE.syscall.c').read_text()
original = (HERE / 'original-xstate-copy-from.c.inc').read_text()
assert c.count(original) == 1
selected = '''#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F06_PTRACE_XSTATE_COPY_FROM)
extern long arch_ptrace_xstate_copy_from_bridge(unsigned long thread_addr,
\t\tunsigned long user_addr, size_t bytes);
#else
''' + original + '#endif\n'
c_after = c.replace(original, selected)
lib = (HERE / 'BASE.lib.rs').read_text()
lib_after = lib + '\n#[cfg(f06_ptrace_xstate_copy_from_candidate)]\nmod f06_ptrace_xstate_copy_from;\n'
cmake = (HERE / 'BASE.CMakeLists.txt').read_text()
anchor = '''\t\t\t\tset_property(SOURCE "${MCKERNEL_F06_C_SOURCE}" APPEND PROPERTY
\t\t\t\t    COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_VDSO_INFO")
'''
assert cmake.count(anchor) == 1
addition = '''
\t\t\t\t# Complete existing borrowed ptrace xstate-write callback; same Rust usercopy.
\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f06_ptrace_xstate_copy_from_candidate")
\t\t\t\tlist(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_ptrace_xstate_copy_from.rs")
\t\t\t\tset_property(SOURCE "${MCKERNEL_F06_C_SOURCE}" APPEND PROPERTY
\t\t\t\t    COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_PTRACE_XSTATE_COPY_FROM")
'''
cmake_after = cmake.replace(anchor, anchor + addition)
for patch, relative, before, after in [
    ('arch-selection.patch', 'arch/x86_64/kernel/syscall.c', c, c_after),
    ('rust-module-selection.patch', 'kernel/rust/lib.rs', lib, lib_after),
    ('cmake-selection.PROPOSAL.patch', 'kernel/CMakeLists.txt', cmake, cmake_after),
]:
    (HERE / patch).write_text(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                                       fromfile='a/' + relative, tofile='b/' + relative)))
    snapshots[relative]['proposed_postimage_sha256'] = hashlib.sha256(after.encode()).hexdigest()

plan_path = OLD / 'FUTURE-HOST-COMMANDS.NOT-GRANTED.json'
plan = json.loads(plan_path.read_text())
old_prefix, new_prefix = str(OLD) + '/', str(HERE) + '/'
plan['cwd'] = str(HERE)
plan['fresh_output'] = str(HERE / 'future-host-output-1')
for command in plan['commands']:
    command['argv'] = [arg.replace(old_prefix, new_prefix) for arg in command['argv']]
plan['status'] = 'SOURCE118_REBASED_PREPARED_NOT_GRANTED_NOT_RUN'
plan['rebase_source_adoption118'] = adoption_binding
plan['rebased_from_original_body4_plan'] = binding(plan_path)
plan['future_default_checks'][0] = 'Root integrates these additive hunks only with exact adopted118 or explicit reviewed successor; preserve all118selectors and separately coordinate body3 copy-to. Rebind real origin/profile after source changes.'
dump('FUTURE-HOST-COMMANDS.NOT-GRANTED.json', plan)

old_pre = json.loads((OLD / 'PREIMAGES.json').read_text())
dump('PREIMAGES.json', {
    'scope': SCOPE, 'status': 'EXACT_ROOT118_SOURCE_REBASE_NOT_DEFAULT_ARTIFACT_ACCEPTANCE',
    'source_adoption118': adoption_binding,
    'accepted_artifact_source_adoption116': old_pre['source_adoption116'],
    'snapshots': snapshots,
    'original_body': binding(HERE / 'original-xstate-copy-from.c.inc'),
    'immutable_body4_inputs': immutable,
    'original_body4_source_ready': binding(OLD / 'SOURCE-READY.json'),
    'all_nine_root118_canonical_postimages': postimages,
    'real_header_inputs': [binding(ROOT / p) for p in [
        'kernel/include/process.h', 'lib/include/memory.h', 'arch/x86_64/kernel/include/registers.h',
        'kernel/rust/x86_memory_helpers.rs', 'kernel/rust/syscall_policy.rs']],
    'retained_object_frontier': binding(HERE / 'SELECTED-CURRENT116-ARCH-FRONTIER.json'),
    'no_shared_writes': True, 'compiler_runs': 0, 'fixture_runs': 0, 'native_runs': 0,
    'artifact_scope': 'Accepted actual116 arch77db1a40 still defines target40B/0x2f0. Root118 is adopted SOURCE only, no matching118 artifact/native claim.',
})
print(json.dumps({'scope': SCOPE, 'status': 'PRIVATE_SOURCE_REBASED_TO_EXACT_ROOT118',
                  'source_adoption_sha256': adoption_binding['sha256'],
                  'immutable_original_body4_inputs': len(immutable), 'compiler_runs': 0, 'fixture_runs': 0}))
