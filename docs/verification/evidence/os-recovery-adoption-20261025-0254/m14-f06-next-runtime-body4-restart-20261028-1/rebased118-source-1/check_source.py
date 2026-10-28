#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source/preimage/patch checks only, without compiler, fixture or subprocess.
"""
import ast
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
checks = []
current_preimage_drift = []


def check(name, condition):
    assert condition, name
    checks.append(name)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(binding):
    p = Path(binding['path'])
    return p.is_file() and p.stat().st_size == binding['bytes'] and digest(p) == binding['sha256']


def apply_exact(before, patch):
    source = before.splitlines(True)
    lines = patch.splitlines(True)
    assert lines[0].startswith('--- a/') and lines[1].startswith('+++ b/')
    output = []
    source_at = 0
    at = 2
    while at < len(lines):
        hunk = re.fullmatch(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@.*\n', lines[at])
        assert hunk, lines[at]
        old_start, old_count, new_start, new_count = hunk.groups()
        old_count = int(old_count or '1')
        new_count = int(new_count or '1')
        old_at = int(old_start) - 1
        assert old_at >= source_at
        output.extend(source[source_at:old_at])
        source_at = old_at
        assert len(output) == int(new_start) - 1
        removed = added = 0
        at += 1
        while at < len(lines) and not lines[at].startswith('@@ '):
            line = lines[at]
            if line[0] in ' -':
                assert source[source_at] == line[1:]
                source_at += 1
                removed += 1
            if line[0] in ' +':
                output.append(line[1:])
                added += 1
            assert line[0] in ' +-'
            at += 1
        assert removed == old_count and added == new_count
    output.extend(source[source_at:])
    return ''.join(output)


pre = json.loads((HERE / 'PREIMAGES.json').read_text())
check('actual Root118 source receipt exact', verify(pre['source_adoption118']))
check('retained accepted116 artifact source receipt exact', verify(pre['accepted_artifact_source_adoption116']))
for relative, entry in pre['snapshots'].items():
    if not verify(entry['canonical']):
        current_preimage_drift.append(relative)
    check('exact private snapshot ' + relative, verify(entry['snapshot']))
for row in pre['real_header_inputs']:
    check('exact selected dependency ' + row['path'], verify(row))
check('verbatim original C body binding', verify(pre['original_body']))

base = (HERE / 'BASE.syscall.c').read_text()
original = (HERE / 'original-xstate-copy-from.c.inc').read_text()
check('original body occurs once in real preimage', base.count(original) == 1)
for patch_file, relative, snapshot in [
    ('arch-selection.patch', 'arch/x86_64/kernel/syscall.c', 'BASE.syscall.c'),
    ('rust-module-selection.patch', 'kernel/rust/lib.rs', 'BASE.lib.rs'),
    ('cmake-selection.PROPOSAL.patch', 'kernel/CMakeLists.txt', 'BASE.CMakeLists.txt'),
]:
    after = apply_exact((HERE / snapshot).read_text(), (HERE / patch_file).read_text())
    check('exact patch postimage ' + relative,
          hashlib.sha256(after.encode()).hexdigest() == pre['snapshots'][relative]['proposed_postimage_sha256'])
    if patch_file == 'arch-selection.patch':
        check('fallback C body unchanged exactly once', after.count(original) == 1)
        check('arch selector declaration pairs original provider',
              '#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F06_PTRACE_XSTATE_COPY_FROM)\n'
              'extern long arch_ptrace_xstate_copy_from_bridge(unsigned long thread_addr,\n'
              '\t\tunsigned long user_addr, size_t bytes);\n#else\n' + original + '#endif\n' in after)

candidate = (HERE / 'f06_ptrace_xstate_copy_from.rs').read_text()
check('one complete public candidate provider',
      candidate.count('pub unsafe extern "C" fn arch_ptrace_xstate_copy_from_bridge(') == 1)
check('original field read through real ABI', candidate.count('read(addr_of!((*thread).fp_regs))') == 1)
check('original null-FP ENOMEM branch', 'if fp_regs.is_null() {\n        return -12;' in candidate)
check('existing Rust user-copy provider retained exactly once',
      candidate.count('crate::x86_memory_helpers::copy_from_user(') == 1)
check('exact raw arguments and signed result widening',
      'fp_regs,\n            user_addr as *const core::ffi::c_void,\n            bytes,\n        ) as CLong' in candidate)
check('no test-only exclusion of production wrapper', '#[cfg(' not in candidate)

oracle = (HERE / 'oracle.c').read_text()
check('untouched original C included with names-only redirection',
      '#define arch_ptrace_xstate_copy_from_bridge original_arch_ptrace_xstate_copy_from_bridge\n'
      '#define copy_from_user fixture_copy_from_user\n#include "original-xstate-copy-from.c.inc"\n'
      '#undef copy_from_user\n#undef arch_ptrace_xstate_copy_from_bridge\n' in oracle)
fixture = (HERE / 'fixture.rs').read_text()
check('fixture includes exact entire candidate module',
      '#[path = "f06_ptrace_xstate_copy_from.rs"]\nmod candidate;' in fixture)
check('fixture uses actual ABI snapshot', '#[path = "abi.snapshot.rs"]\nmod abi;' in fixture)
check('fixture asserts original domain and independent result/effect/canary oracles',
      all(s in fixture for s in ['offset_of!(abi::Thread, fp_regs), 4784',
                                'let expected_result = if present { result as i64 } else { -12 };',
                                'assert_eq!(rust_trace, expected_trace,',
                                'assert_eq!(destination.0, expected_destination,',
                                'assert_eq!(thread_storage.0, thread_before,',
                                'assert_eq!(source.0, source_before,',
                                'assert_eq!(pairs, 1944);']))
check('planned grid cardinality', 2 * 9 * 9 * 3 * 4 == 1944)
plan = json.loads((HERE / 'FUTURE-HOST-COMMANDS.NOT-GRANTED.json').read_text())
check('four future commands all explicitly functional scope',
      len(plan['commands']) == 4 and all(x['purpose'].startswith(SCOPE) for x in plan['commands']))
check('no compile/fixture output exists', not Path(plan['fresh_output']).exists())
check('future header profile is retained exactly', verify(plan['header_profile_argv_source']))
frontier = json.loads((HERE / 'SELECTED-CURRENT116-ARCH-FRONTIER.json').read_text())
check('selected retained actual ELF exact', verify(frontier['object']))
check('target retained in 17-function accepted arch frontier',
      len(frontier['selected_functions']) == 17 and frontier['target']['name'] == 'arch_ptrace_xstate_copy_from_bridge'
      and frontier['target']['size'] == 40)
for script in ['rebase_source.py', 'check_source.py']:
    ast.parse((HERE / script).read_text())
    check('Python source syntax only ' + script, True)
for row in pre['immutable_body4_inputs']:
    check('sealed original body4 input exact ' + row['original']['path'], verify(row['original']))
    check('rebased immutable input exact ' + row['rebased_copy']['path'], verify(row['rebased_copy']))
    check('immutable body4 bytes retained ' + row['rebased_copy']['path'],
          row['original']['sha256'] == row['rebased_copy']['sha256'])
for relative, row in pre['all_nine_root118_canonical_postimages'].items():
    check('actual Root118 canonical postimage still exact ' + relative, verify(row))
check('new rebase preserves original source-ready packet', verify(pre['original_body4_source_ready']))
check('canonical preimages still exact118', not current_preimage_drift)
old_plan = json.loads(Path(plan['rebased_from_original_body4_plan']['path']).read_text())
check('original body4 command plan remains exact', verify(plan['rebased_from_original_body4_plan']))
for old_command, new_command in zip(old_plan['commands'], plan['commands']):
    expected = [arg.replace(str(HERE.parent) + '/', str(HERE) + '/') for arg in old_command['argv']]
    check('future argv differs only by owned source/output path', new_command['argv'] == expected)
for relative, snapshot, patch in [('arch/x86_64/kernel/syscall.c', 'BASE.syscall.c', 'arch-selection.patch'),
                                  ('kernel/CMakeLists.txt', 'BASE.CMakeLists.txt', 'cmake-selection.PROPOSAL.patch'),
                                  ('kernel/rust/lib.rs', 'BASE.lib.rs', 'rust-module-selection.patch')]:
    before = (HERE / snapshot).read_text()
    after = apply_exact(before, (HERE / patch).read_text())
    for selector in ['f06_native_signal_restore_fp_candidate', 'f06_vdso_info_candidate',
                     'MCKERNEL_RUST_F06_NATIVE_SIGNAL_RESTORE_FP', 'MCKERNEL_RUST_F06_VDSO_INFO']:
        check('preserved118 selector ' + relative + ':' + selector,
              before.count(selector) == after.count(selector))
    check('future body3 copy-to selector not introduced ' + relative,
          'f06_ptrace_xstate_copy_to_candidate' not in after and 'MCKERNEL_RUST_F06_PTRACE_XSTATE_COPY_TO' not in after)
result = {'scope': SCOPE, 'status': 'PURE_SOURCE_CHECKS_PASS_NOT_COMPILER_OR_FIXTURE_ACCEPTANCE',
          'checks': checks, 'count': len(checks), 'current_preimage_drift': current_preimage_drift, 'compiler_runs': 0, 'fixture_runs': 0, 'native_runs': 0}
(HERE / 'SOURCE-CHECK.RESULT.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({k: v for k, v in result.items() if k != 'checks'}))
