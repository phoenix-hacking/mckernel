"""Compile complete F06 replacement modules, without fabricated providers.

All external provider declarations and shared structure definitions are extracted
from their genuine Rust sources. They remain unresolved in the resulting object:
this verifies complete module code generation, not provider linkage or native
execution. Production GS/XSAVE/XRSTOR instructions are emitted but never run.
"""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

from scripts.derive_f06_signal_metadata import write_signal_metadata

ROOT = Path(__file__).resolve().parents[2]
RUST = ROOT / 'kernel/rust'


def definition(source, name, kind='fn'):
    pattern = r'(?m)^(?:pub(?:\(crate\))?\s+)?(?:unsafe\s+)?(?:extern\s+"C"\s+)?' + kind + r'\s+' + re.escape(name) + r'\b'
    matches = list(re.finditer(pattern, source))
    if len(matches) != 1:
        raise ValueError(f'expected one genuine {kind} definition: {name}')
    start = matches[0].start()
    opening = source.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def provider(source, name):
    body = definition(source, name)
    signature = body[:body.index('{')].strip()
    if 'extern "C"' not in signature:
        raise ValueError('provider is not an existing C ABI entry: ' + name)
    signature = re.sub(r'^pub(?:\(crate\))?\s+', '', signature)
    signature = signature.replace('unsafe extern "C" fn ', 'pub fn ', 1)
    if signature.startswith('extern "C" fn '):
        signature = signature.replace('extern "C" fn ', 'pub fn ', 1)
    # Parameter binding mutability is an implementation pattern, not ABI. A
    # foreign declaration cannot contain patterns; pointer mutability is kept.
    signature = re.sub(r'\bmut\s+([A-Za-z_][A-Za-z_0-9]*\s*:)', r'\1', signature)
    return signature + ';'


def build_fixture(directory, native=True):
    policy = (RUST / 'syscall_policy.rs').read_text()
    output = directory / 'metadata'
    write_signal_metadata(ROOT / 'arch/x86_64/kernel/syscall.c',
                          '/src/arch/x86_64/kernel/syscall.c', output)
    pieces = ['#![no_std]\n#![allow(dead_code,unused_imports,unused_variables)]',
              'use core::{ffi::{c_char,c_void},mem::{size_of,offset_of},ptr::write_volatile};',
              f'#[path="{RUST / "abi.rs"}"] mod abi;', 'use abi::*;']
    for module, types, names in (
        ('cls', (), ('get_this_cpu_local_var',)),
        ('mem_helpers', (), ('kmalloc_tracked', 'kfree_tracked')),
        ('sched_helpers', (), ('check_need_resched',)),
        ('string', (), ('memcpy', '__inline_memset')),
        ('lock_helpers', ('McsRwlockNodeIrqsave',), ('__mcs_rwlock_writer_lock', '__mcs_rwlock_writer_unlock')),
        ('waitq', ('IhkSpinlock', 'ListHead', 'Waitq'), ('waitq_wakeup',)),
    ):
        source = (RUST / (module + '.rs')).read_text()
        declarations = []
        for name in types:
            body = definition(source, name, 'struct')
            marker = source.index(body)
            prefix = source[:marker].rstrip().splitlines()[-1]
            if not prefix.startswith('#[repr('):
                raise ValueError('missing genuine structure representation: ' + name)
            declarations.append(prefix + '\n' + body)
        declarations.extend(provider(source, name) for name in names)
        structures = '\n'.join(declarations[:len(types)])
        functions = '\n'.join(declarations[len(types):])
        pieces.append(f'mod {module} {{ use super::*;\ntype CUInt=u32;\n{structures}\nunsafe extern "C" {{\n{functions}\n}}\n}}')
    debug = (RUST / 'debug.rs').read_text()
    pieces.append('mod debug { use super::*;\n#[repr(C)]\n' + definition(debug, 'Ddebug', 'struct') + '\n}')
    cpu = (RUST / 'x86_cpu_helpers.rs').read_text()
    instructions = '\n'.join(definition(cpu, name) for name in ('x86_save_xstate', 'x86_restore_xstate'))
    declarations = '\n'.join(provider(cpu, name) for name in ('get_xsave_size', 'get_xsave_mask'))
    pieces.append('mod x86_cpu_helpers { use super::*; use core::arch::asm;\n'
                  + 'unsafe extern "C" {\n' + declarations + '\n}\n' + instructions + '\n}')
    constants = ('CLD_STOPPED EBUSY EFAULT ENOMEM IHK_MC_AP_NOWAIT PS_DELAY_STOPPED '
                 'PS_DELAY_TRACED PS_STOPPED PS_TRACED PT_TRACED RFLAGS_TF SIGCHLD '
                 'SIGCONT SIGKILL SIGNAL_STOP_STOPPED SIGSTOP SIGTRAP SIGTSTP SIGTTIN '
                 'SIGTTOU SIGURG TRAP_TRACE EINTR SYS_EPOLL_WAIT SYS_NANOSLEEP SYS_PPOLL SYS_PSELECT6').split()
    for name in constants:
        matches = re.findall(r'(?m)^const ' + name + r'\s*:[^;]+;', policy)
        if len(matches) != 1:
            raise ValueError('expected one actual policy constant: ' + name)
        pieces.append(matches[0])
    for name in ('rt_sigreturn_zero_siginfo', 'sigmask_to_signal_number'):
        pieces.append(definition(policy, name))
    foreign = []
    for name in ('arch_copy_from_user_bridge', 'arch_copy_to_user_bridge', 'kprintf',
                 'ptrace_report_signal', 'schedule'):
        matches = re.findall(r'(?m)^\s*(?:pub\s+)?fn\s+' + name + r'\([^;{}]*\)[^;{}]*;', policy)
        signatures = list(dict.fromkeys(match.strip() for match in matches))
        if len(signatures) == 1:
            foreign.append(signatures[0])
        elif not signatures:
            foreign.append(provider(policy, name))
        else:
            raise ValueError('ambiguous genuine policy provider: ' + name)
    pieces.append('unsafe extern "C" {\n' + '\n'.join(foreign) + '\n}')
    if native:
        pieces.append(f'#[path="{RUST / "native_signal.rs"}"] mod native_signal;')
    pieces.append(f'#[path="{RUST / "f06_signal_trap_info.rs"}"] mod f06_signal_trap_info;')
    pieces.append(f'#[path="{RUST / "f06_rt_sigreturn_xrstor.rs"}"] mod f06_rt_sigreturn_xrstor;')
    pieces.append(f'#[path="{RUST / "f06_signal_tail.rs"}"] mod f06_signal_tail;')
    fixture = directory / 'f06.rs'
    fixture.write_text('\n'.join(pieces) + '\n')
    return fixture, output / 'f06_signal_metadata.rs'


class F06TailCodegenTests(unittest.TestCase):
    def checked(self, command, **kwargs):
        result = subprocess.run(command, capture_output=True, text=True, timeout=90, **kwargs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result.stdout

    def test_complete_native_and_legacy_modules_emit_required_owners(self):
        compiler = os.environ.get('RUSTC') or shutil.which('rustc')
        if not compiler:
            self.skipTest('rustc required')
        for native in (False, True):
            with self.subTest(native=native), tempfile.TemporaryDirectory(prefix='f06-codegen-') as tmp:
                directory = Path(tmp)
                source, metadata = build_fixture(directory, native)
                obj = directory / 'f06.o'
                cfgs = ['f06_signal_context_candidate', 'f06_do_signal_whole_candidate',
                        'f06_do_signal_reuse_qualified_context', 'f06_signal_trap_info_candidate',
                        'f06_rt_sigreturn_xrstor_candidate', 'f06_debug_constants_candidate']
                if native:
                    cfgs.append('native_linux_irq_work_v6_12')
                command = [compiler, '--edition=2021', '--crate-type=lib', '-Awarnings',
                           '-C', 'panic=abort', '-C', 'opt-level=2', '-C', 'code-model=large',
                           '-C', 'relocation-model=static', '-C', 'no-redzone=yes',
                           '-C', 'no-vectorize-loops', '-C', 'no-vectorize-slp',
                           '-C', 'target-feature=-sse,-sse2,-avx,-avx2', '--emit=obj',
                           '-o', str(obj), str(source)]
                for cfg in cfgs:
                    command.extend(['--cfg', cfg])
                env = dict(os.environ, MCKERNEL_F06_SIGNAL_METADATA_RS=str(metadata))
                self.checked(command, env=env)
                symbols = self.checked(['nm', '--defined-only', '--format=posix', str(obj)])
                for name in ('do_signal', 'arch_rt_sigreturn_context_bridge',
                             'arch_signal_restart_result', 'arch_rt_sigreturn_xrstor_bridge',
                             'debug_constants'):
                    self.assertEqual(sum(line.startswith(name + ' ') for line in symbols.splitlines()), 1, name)
                disassembly = self.checked(['objdump', '-d', str(obj)])
                self.assertIn('xsave', disassembly)
                self.assertIn('xrstor', disassembly)
                self.assertIn('%gs:', disassembly)
                unresolved = self.checked(['nm', '--undefined-only', '--format=posix', str(obj)])
                self.assertIn('kmalloc_tracked ', unresolved)
                self.assertIn('terminate ', unresolved)
                print('F06 complete module codegen PASS; genuine providers remain unresolved; native=', native)


if __name__ == '__main__':
    unittest.main()
