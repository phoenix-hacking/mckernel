#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Create private source proposals only; no compiler/fixture/subprocess invocation.
"""
import difflib
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path('/home/holden/mckernel')
HERE = Path(__file__).resolve().parent
EVIDENCE = ROOT / 'docs/verification/evidence/os-recovery-adoption-20261025-0254'
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'


def binding(path):
    data = path.read_bytes()
    return {'path': str(path), 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}


def dump(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2) + '\n')


adoption_path = EVIDENCE / 'next116-f03-seven-f06-shmget-selective-composition-source-1/ROOT-ACTUAL-SOURCE-ADOPTION.json'
adoption = json.loads(adoption_path.read_text())
adopted = {row['relative']: row['after'] for row in adoption['source_changes']}
snapshots = {}
for relative, snapshot in [
    ('arch/x86_64/kernel/syscall.c', 'BASE.syscall.c'),
    ('kernel/CMakeLists.txt', 'BASE.CMakeLists.txt'),
    ('kernel/rust/lib.rs', 'BASE.lib.rs'),
    ('kernel/rust/abi.rs', 'abi.snapshot.rs'),
]:
    original = ROOT / relative
    if relative in adopted:
        assert binding(original)['sha256'] == adopted[relative]['sha256'], (relative, 'current no longer adopted116')
    (HERE / snapshot).write_bytes(original.read_bytes())
    snapshots[relative] = {'canonical': binding(original), 'snapshot': binding(HERE / snapshot)}

c = (HERE / 'BASE.syscall.c').read_text()
start_marker = 'long\narch_ptrace_xstate_copy_to_bridge(unsigned long thread_addr,\n'
assert c.count(start_marker) == 1
start = c.index(start_marker)
end = c.index('\n}\n', start) + len('\n}\n')
original = c[start:end]
assert original == '''long
arch_ptrace_xstate_copy_to_bridge(unsigned long thread_addr,
\t\tunsigned long user_addr, size_t bytes)
{
\tstruct thread *thread = (struct thread *)thread_addr;

\tif (thread->fp_regs == NULL) {
\t\treturn -ENOMEM;
\t}
\treturn copy_to_user((void *)user_addr, thread->fp_regs, bytes);
}
'''
(HERE / 'original-xstate-copy-to.c.inc').write_text(original)
selected = '''#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F06_PTRACE_XSTATE_COPY_TO)
extern long arch_ptrace_xstate_copy_to_bridge(unsigned long thread_addr,
\t\tunsigned long user_addr, size_t bytes);
#else
''' + original + '#endif\n'
arch_after = c[:start] + selected + c[end:]

lib = (HERE / 'BASE.lib.rs').read_text()
lib_after = lib + '\n#[cfg(f06_ptrace_xstate_copy_to_candidate)]\nmod f06_ptrace_xstate_copy_to;\n'
cmake = (HERE / 'BASE.CMakeLists.txt').read_text()
anchor = '''\t\t\t\tset_property(SOURCE "${MCKERNEL_F06_C_SOURCE}" APPEND PROPERTY
\t\t\t\t    COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_SHMGET_DISPATCH")
'''
assert cmake.count(anchor) == 1
addition = '''
\t\t\t\t# Complete existing borrowed ptrace xstate-read callback; same Rust usercopy.
\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f06_ptrace_xstate_copy_to_candidate")
\t\t\t\tlist(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_ptrace_xstate_copy_to.rs")
\t\t\t\tset_property(SOURCE "${MCKERNEL_F06_C_SOURCE}" APPEND PROPERTY
\t\t\t\t    COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_PTRACE_XSTATE_COPY_TO")
'''
cmake_after = cmake.replace(anchor, anchor + addition)
for name, relative, before, after in [
    ('arch-selection.patch', 'arch/x86_64/kernel/syscall.c', c, arch_after),
    ('rust-module-selection.patch', 'kernel/rust/lib.rs', lib, lib_after),
    ('cmake-selection.PROPOSAL.patch', 'kernel/CMakeLists.txt', cmake, cmake_after),
]:
    patch = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                      fromfile='a/' + relative, tofile='b/' + relative))
    (HERE / name).write_text(patch)
    snapshots[relative]['proposed_postimage_sha256'] = hashlib.sha256(after.encode()).hexdigest()

# Read only the retained accepted ELF, not a current process/runtime clearance.
obj = EVIDENCE / 'ROOT-CURRENT116-F03SEVEN-SHM-BUILD-ADMISSION-1/OUTPUT/work/output/build/kernel/CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o'
obj_bind = binding(obj)
assert obj_bind['sha256'] == '77db1a40cdf69e5d8689d8d93f5ab8710c554bbf73dd8dc4b585cae018cdb31d'
raw = obj.read_bytes()
assert raw[:6] == b'\x7fELF\x02\x01'
eh = struct.unpack_from('<16sHHIQQQIHHHHHH', raw)
sections = [struct.unpack_from('<IIQQQQIIQQ', raw, eh[6] + i * eh[11]) for i in range(eh[12])]
functions = []
for section in sections:
    if section[1] != 2:
        continue
    strings_section = sections[section[6]]
    strings = raw[strings_section[4]:strings_section[4] + strings_section[5]]
    for at in range(section[4], section[4] + section[5], section[9]):
        name, info, other, ndx, value, size = struct.unpack_from('<IBBHQQ', raw, at)
        if info & 15 == 2 and ndx != 0:
            text = strings[name:strings.index(b'\0', name)].decode()
            functions.append({'name': text, 'size': size, 'value': value, 'section_index': ndx,
                              'bind': info >> 4, 'visibility': other})
assert len(functions) == 17
target = [x for x in functions if x['name'] == 'arch_ptrace_xstate_copy_to_bridge']
assert len(target) == 1 and target[0]['size'] == 46 and target[0]['bind'] == 1
dump('SELECTED-CURRENT116-ARCH-FRONTIER.json', {
    'scope': SCOPE, 'status': 'RETAINED_ACCEPTED_OBJECT_READ_ONLY_NOT_LIVE_CLEARANCE',
    'object': obj_bind, 'selected_functions': functions, 'target': target[0],
    'already_banked_excluded': ['vdso_get_vdso_info', 'arch_native_signal_restore_fp_bridge'],
})

retained_plan = EVIDENCE / 'm14-f06-next-runtime-body2-source-20261028-1/FUTURE-HOST-COMMANDS.NOT-GRANTED.json'
old_plan = json.loads(retained_plan.read_text())
abi_flags = old_plan['commands'][0]['argv'][:-4]
assert old_plan['commands'][0]['argv'][-4] == '-c'
out = HERE / 'future-host-output-1'
commands = [
    {'purpose': SCOPE + ' Compile actual current kernel-header thread/pointer/result ABI witness only.',
     'argv': abi_flags + ['-c', str(HERE / 'abi_probe.c'), '-o', str(out / 'abi_probe.o')]},
    {'purpose': SCOPE + ' Compile verbatim original C callback with genuine kernel headers and mocked usercopy effects.',
     'argv': abi_flags + ['-std=gnu11', '-fno-builtin', '-I', str(HERE), '-c', str(HERE / 'oracle.c'), '-o', str(out / 'oracle.o')]},
    {'purpose': SCOPE + ' Compile entire Rust candidate unchanged with exact current ABI snapshot and mocked existing Rust usercopy provider.',
     'argv': ['/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc',
              '--edition=2021', '--test', '-C', 'opt-level=2', '-C', 'link-arg=' + str(out / 'oracle.o'),
              '-C', 'link-arg=-no-pie', str(HERE / 'fixture.rs'), '-o', str(out / 'fixture')]},
    {'purpose': SCOPE + ' Run 1944 original-C/Rust return/argument/partial-copy/borrow/canary pairs; no actual usercopy or hardware.',
     'argv': [str(out / 'fixture'), '--exact', 'exact_original_c_and_rust_xstate_copy_to', '--test-threads=1', '--nocapture']},
]
dump('FUTURE-HOST-COMMANDS.NOT-GRANTED.json', {
    'scope': SCOPE, 'status': 'PREPARED_NOT_GRANTED_NOT_RUN',
    'cwd': str(HERE), 'fresh_output': str(out), 'commands': commands,
    'header_profile_argv_source': binding(retained_plan),
    'expected_pairs': 1944, 'compiler_or_fixture_invocations': 0,
    'requires': 'Fresh Root ordinary grant and current source/header/profile/CPU/resource bindings; this proposal is no release. Root creates fresh output once after grant.',
    'domain': 'Live aligned target Thread with borrowed fp_regs. Null FP state is defined; null/invalid thread is excluded as in original C. High user/count bits use mocked effects only, not real provider acceptance.',
    'future_default_checks': [
        'Integrate only these disjoint hunks with actually adopted117/118; use a fresh genuine origin/profile binding after all source edits.',
        'Compile full Rust crate including this complete production wrapper and real Thread ABI, selected full arch TU, unchanged fallback TU and final default image.',
        'Require target absent from selected C defined FUNCs and present exactly once as a Rust global provider, resolving existing ptrace_read_regset call graph. Retain all unrelated callbacks/data/389 registry rows.',
        'Verify same Rust copy_to_user provider and genuine signed-int32 to signed-long64 result ABI; no C callback reintroduction or new undefined domain handling.',
        'Run applicable matching-current ptrace xstate-read, null-FP/error/partial-copy and target-lifetime native checks before runtime/file credit.',
    ],
})

dump('PREIMAGES.json', {
    'scope': SCOPE, 'status': 'EXACT_PRIVATE_SOURCE_PROPOSAL_NOT_COMPILER_ACCEPTANCE',
    'source_adoption116': binding(adoption_path), 'snapshots': snapshots,
    'original_body': binding(HERE / 'original-xstate-copy-to.c.inc'),
    'real_header_inputs': [binding(ROOT / p) for p in [
        'kernel/include/process.h', 'lib/include/memory.h', 'arch/x86_64/kernel/include/registers.h',
        'kernel/rust/x86_memory_helpers.rs', 'kernel/rust/syscall_policy.rs']],
    'retained_object_frontier': binding(HERE / 'SELECTED-CURRENT116-ARCH-FRONTIER.json'),
    'no_shared_writes': True, 'compiler_runs': 0, 'fixture_runs': 0, 'native_runs': 0,
})
print(json.dumps({'scope': SCOPE, 'status': 'PRIVATE_SOURCE_PREPARED', 'target': target[0],
                  'compiler_runs': 0, 'fixture_runs': 0, 'native_runs': 0}))
