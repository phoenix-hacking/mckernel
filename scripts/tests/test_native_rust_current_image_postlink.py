import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import struct
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_rust_current_image_postlink as tool


class PostLinkTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.d = Path(self.t.name)
        self.image, self.map, self.obj = (self.d / n for n in ('image', 'image.map', 'rust.o'))
        self.map.write_text('map\n')
        self.obj.write_bytes(b'object')
        self.readelf = self.fake('readelf', "import sys\nprint('There are no relocations in this file.' if '-rW' in sys.argv else 'headers and note')")
        self.nm = self.fake('nm', f"import sys\nprint('' if '-u' in sys.argv else '{tool.BASE + 0x100:016x} T arch_start')")
        self.objdump = self.fake('objdump', "import sys\nprint('  100: ret' if '-d' in sys.argv else '')")
        self.output = self.d / 'report.json'
        self.write_image()
        # Every negative below starts from an executable, verified positive.
        self.assertEqual(self.check()['elf']['note'], [4, 0x60c00, 7616, 1])

    def fake(self, name, body):
        path = self.d / name
        path.write_text('#!/usr/bin/python3\n' + body + '\n')
        path.chmod(0o755)
        return path

    def write_image(self):
        note = struct.pack('<III', 9, 16, tool.NOTE_TYPE) + tool.NOTE_NAME + b'\0' * 3 + tool.NOTE_DESC
        data = bytearray(0x400)
        tool.EH.pack_into(data, 0, b'\x7fELF\x02\x01\x01' + b'\0' * 9,
                          2, 62, 1, tool.BASE + 0x100, 64, 0, 0, 64, 56, 2, 0, 0, 0)
        tool.PH.pack_into(data, 64, 1, 5, 0x100, tool.BASE + 0x100, 0, 0x200, 0x300, 0x1000)
        tool.PH.pack_into(data, 120, 4, 0, 0x300, 0, 0, len(note), len(note), 4)
        data[0x300:0x300 + len(note)] = note
        self.image.write_bytes(data)

    def patch(self, offset, fmt, value):
        data = bytearray(self.image.read_bytes())
        struct.pack_into(fmt, data, offset, value)
        self.image.write_bytes(data)

    def check(self, publish=False):
        return tool.build_report(self.image, self.map, self.obj, 'a' * 40,
                                 self.readelf, self.nm, self.objdump,
                                 self.output if publish else None)

    def reject(self, message):
        with self.assertRaisesRegex((ValueError, OSError), message):
            self.check(True)
        self.assertFalse(self.output.exists())

    def test_valid_published_bindings_and_diagnostic_scope(self):
        result = self.check(True)
        self.assertEqual(json.loads(self.output.read_text()), result)
        for field in ('runtime', 'application', 'production'):
            self.assertIs(result[field], False)
        self.assertEqual(result['ownership']['status'], 'mandatory-outstanding')
        for name in ('readelf', 'nm', 'objdump'):
            self.assertEqual(result['tools'][name]['sha256'], hashlib.sha256(getattr(self, name).read_bytes()).hexdigest())
        for name, output in result['tools']['outputs'].items():
            self.assertTrue(output['argv'][0].startswith('/proc/self/fd/'))
            self.assertEqual(output['environment'], tool.ENV)
            self.assertEqual(output['target']['path'], str(self.obj if name == 'disassembly' else self.image))
        self.assertEqual(result['tools']['outputs']['all_relocations']['argv'][1], '-rW')
        self.assertEqual(result['tools']['outputs']['undefined_symbols']['argv'][1], '-u')

    def test_note_after_first_page_is_loader_legal(self):
        data = bytearray(self.image.read_bytes())
        note = data[0x300:0x328]
        data.extend(b'\0' * (8192 - len(data)))
        data.extend(note)
        struct.pack_into('<Q', data, 128, 8192)
        self.image.write_bytes(data)
        self.check(True)

    def test_overlap(self):
        data = bytearray(self.image.read_bytes())
        struct.pack_into('<H', data, 56, 3)
        tool.PH.pack_into(data, 176, 1, 5, 0x100, tool.BASE + 0x100, 0, 0x100, 0x100, 1)
        self.image.write_bytes(data)
        self.reject('overlapping PT_LOAD spans')

    def test_duplicate_note(self):
        data = bytearray(self.image.read_bytes())
        data[0x328:0x350] = data[0x300:0x328]
        struct.pack_into('<Q', data, 152, 80)
        self.image.write_bytes(data)
        self.reject('expected MCKERNEL boot note mismatch')

    def test_truncated_header(self):
        self.image.write_bytes(self.image.read_bytes()[:63])
        self.reject('truncated ELF header')

    def test_truncated_program_headers(self):
        self.image.write_bytes(self.image.read_bytes()[:175])
        self.reject('program headers exceed loader bounds')

    def test_unresolved_ordinary_nm_output(self):
        self.nm = self.fake('nm', f"import sys\nprint('                 U missing' if '-u' in sys.argv else '{tool.BASE + 0x100:016x} T arch_start')")
        self.reject('linked image has unresolved symbols')

    def test_weak_undefined_function_rejected(self):
        self.nm = self.fake('nm', f"import sys\nprint('                 w weak_function' if '-u' in sys.argv else '{tool.BASE + 0x100:016x} T arch_start')")
        self.reject('linked image has unresolved symbols')

    def test_weak_undefined_object_rejected(self):
        self.nm = self.fake('nm', f"import sys\nprint('                 v weak_object' if '-u' in sys.argv else '{tool.BASE + 0x100:016x} T arch_start')")
        self.reject('linked image has unresolved symbols')

    def test_defined_gnu_unique_symbol_passes(self):
        listing = f'{tool.BASE + 0x100:016x} T arch_start\n{tool.BASE + 0x180:016x} u unique_object'
        self.nm = self.fake('nm', f"import sys\nprint('' if '-u' in sys.argv else {listing!r})")
        self.check(True)

    def test_static_readelf_relocation_rejected(self):
        listing = "Relocation section '.rela.text' at offset 0x1000 contains 1 entry:\n    Offset             Info             Type               Symbol's Value  Symbol's Name + Addend\nfffffffffe800100  0000000100000001 R_X86_64_64            0000000000000000 missing + 0"
        self.readelf = self.fake('readelf', f"import sys\nprint({listing!r} if '-rW' in sys.argv else 'headers and note')")
        self.reject('linked image has relocations')

    def test_dynamic_readelf_relocation_rejected(self):
        listing = "Relocation section '.rela.dyn' at offset 0x1000 contains 1 entry:\n    Offset             Info             Type               Symbol's Value  Symbol's Name + Addend\nfffffffffe800100  0000000000000008 R_X86_64_RELATIVE                         fe800100"
        self.readelf = self.fake('readelf', f"import sys\nprint({listing!r} if '-rW' in sys.argv else 'headers and note')")
        self.reject('linked image has relocations')

    def test_empty_readelf_relocation_listing_rejected(self):
        self.readelf = self.fake('readelf', "import sys\nprint('' if '-rW' in sys.argv else 'headers and note')")
        self.reject('unrecognized linked image relocation listing')

    def test_linked_image_relocation(self):
        self.objdump = self.fake('objdump', "import sys\nprint('  100: ret' if '-d' in sys.argv else '0000000000000010 R_X86_64_64 bad')")
        self.reject('linked image has relocations')

    def test_arch_start_mismatch(self):
        self.nm = self.fake('nm', f"import sys\nprint('' if '-u' in sys.argv else '{tool.BASE + 0x101:016x} T arch_start')")
        self.reject('nm arch_start does not match ELF entry')

    def test_object_empty_disassembly(self):
        self.objdump = self.fake('objdump', "print('')")
        self.reject('Rust object disassembly has no instructions')

    def test_scalar_instructions_and_symbol_names(self):
        instructions = ('push %rbp', 'mov %rsp,%rbp', 'xor %eax,%eax', 'rep movsq',
                        'movsd', 'cmpsd', 'verr %ax', 'verw %ax', 'pause', 'pext %eax,%ebx,%ecx',
                        'pdep %eax,%ebx,%ecx', 'ptwrite %rax', 'pconfig',
                        'lea 0x0(%rip),%rax # 108 <xmm0>', 'call 0 <ymm1>',
                        'lfence', 'mfence', 'sfence', 'ret')
        dis = '\n'.join(f' {i:x}: {item}' for i, item in enumerate(instructions))
        dis += '\n0000 <vzeroupper_fninit_xmm0>:\n'
        self.objdump = self.fake('objdump', f"import sys\nprint({dis!r} if '-d' in sys.argv else '')")
        self.assertEqual(self.check()['tools']['disassembled_instructions'], len(instructions))

    def test_disassembly_retention_is_bounded_and_hashed(self):
        dis = ' 100: ret\n' * 1000
        self.objdump = self.fake('objdump', f"import sys\nprint({dis!r}, end='') if '-d' in sys.argv else None")
        output = self.check()['tools']['outputs']['disassembly']
        self.assertEqual(output['stdout_bytes'], len(dis))
        self.assertEqual(output['stdout_sha256'], hashlib.sha256(dis.encode()).hexdigest())
        self.assertEqual(len(output['stdout']), 4096)
        self.assertTrue(output['stdout_truncated'])

    def test_real_binutils_accept_open_fd_arguments(self):
        # No compilation: validate each exact installed executable and target
        # descriptor using a retained copy of an existing ELF in both roles.
        binary = Path('/usr/bin/true').read_bytes()
        self.image.write_bytes(binary)
        self.obj.write_bytes(binary)
        calls = (('readelf', ['-l', '-n'], self.image), ('readelf', ['-rW'], self.image),
                 ('nm', ['-an'], self.image), ('nm', ['-u'], self.image),
                 ('objdump', ['-r'], self.image), ('objdump', ['-d', '--no-show-raw-insn'], self.obj))
        for name, args, path in calls:
            with self.subTest(tool=name, args=args):
                executable = Path(shutil.which(name)).resolve()
                snap, target = tool.Snapshot(executable, name), tool.Snapshot(path, 'target')
                try:
                    result = tool.run_tool(snap, args, target)
                    self.assertEqual(result['exit_status'], 0)
                    if '-d' in args:
                        self.assertIn('ret', result['stdout'])
                    if args == ['-rW']:
                        with self.assertRaisesRegex(ValueError, 'linked image has relocations'):
                            tool.check_relocations(result['stdout'])
                finally:
                    snap.close()
                    target.close()

    def test_real_readelf_no_relocation_baseline(self):
        snap = tool.Snapshot(Path(shutil.which('readelf')).resolve(), 'readelf')
        target = tool.Snapshot(self.image, 'image')
        try:
            result = tool.run_tool(snap, ['-rW'], target)
            self.assertEqual(result['stdout'].strip(), 'There are no relocations in this file.')
            tool.check_relocations(result['stdout'])
        finally:
            snap.close()
            target.close()

    def producer_failure(self, stream=None):
        body = 'import os, time\n'
        body += 'time.sleep(10)' if stream is None else f"while True: os.write({1 if stream == 'stdout' else 2}, b'x' * 65536)"
        self.readelf = self.fake('readelf', body)
        children = []
        original = tool.subprocess.Popen
        def capture(*args, **kwargs):
            p = original(*args, **kwargs)
            children.append(p)
            return p
        start = time.monotonic()
        with mock.patch.object(tool, 'TOOL_TIMEOUT', 0.25), mock.patch.object(tool.subprocess, 'Popen', capture):
            self.reject('tool timeout' if stream is None else f'tool {stream} output exceeds bound')
        self.assertLess(time.monotonic() - start, 3)
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0].returncode, -9)
        self.assertFalse(Path(f'/proc/{children[0].pid}').exists())
        with self.assertRaises(ChildProcessError):
            os.waitpid(children[0].pid, os.WNOHANG)

    def test_stdout_limit_kills_and_reaps(self):
        self.producer_failure('stdout')

    def test_stderr_limit_kills_and_reaps(self):
        self.producer_failure('stderr')

    def test_timeout_kills_and_reaps(self):
        self.producer_failure()

    def test_nonzero_tool(self):
        self.readelf = self.fake('readelf', 'raise SystemExit(7)')
        self.reject('tool returned nonzero: .*: 7')

    def mutate(self, attr, replacement):
        path = getattr(self, attr)
        data = path.read_bytes()
        if replacement:
            other = path.with_suffix('.replacement')
            other.write_bytes(data)
            other.chmod(path.stat().st_mode)
            other.replace(path)
        else:
            path.write_bytes(data[:-1] + bytes((data[-1] ^ 1,)))

    def drift_case(self, attr, replacement, stage):
        original = getattr(tool, stage)
        fired = False
        def intercept(*args, **kwargs):
            nonlocal fired
            result = original(*args, **kwargs)
            if not fired:
                fired = True
                self.mutate(attr, replacement)
            return result
        label = {'map': 'link map', 'obj': 'Rust object'}.get(attr, attr)
        with mock.patch.object(tool, stage, intercept):
            self.reject(label + ' changed during admission')
        self.assertTrue(fired)

    def test_output_collision(self):
        self.check(True)
        original = self.output.read_bytes()
        with self.assertRaises(FileExistsError):
            self.check(True)
        self.assertEqual(self.output.read_bytes(), original)
        self.assertEqual(list(self.d.glob('.*.tmp-*')), [])

    def test_output_parent_symlink(self):
        real = self.d / 'real'
        real.mkdir()
        link = self.d / 'link'
        link.symlink_to(real)
        self.output = link / 'report.json'
        self.reject('Not a directory|Too many levels')

    def test_output_parent_drift(self):
        parent = self.d / 'parent'
        parent.mkdir()
        self.output = parent / 'report.json'
        original = tool.os.fsync
        moved = self.d / 'moved'
        def drift(fd):
            original(fd)
            if stat.S_ISREG(os.fstat(fd).st_mode):
                parent.rename(moved)
                parent.mkdir()
        with mock.patch.object(tool.os, 'fsync', drift):
            self.reject('output parent changed during publication')
        self.assertEqual(list(moved.iterdir()), [])

    def test_short_writes_are_completed(self):
        original = tool.os.write
        calls = []
        def short(fd, data):
            calls.append(len(data))
            return original(fd, data[:19])
        with mock.patch.object(tool.os, 'write', short):
            result = self.check(True)
        self.assertGreater(len(calls), 10)
        self.assertEqual(json.loads(self.output.read_text()), result)

    def test_zero_write_removes_temp_and_no_final(self):
        with mock.patch.object(tool.os, 'write', return_value=0):
            self.reject('short report write')
        self.assertEqual(list(self.d.glob('.*.tmp-*')), [])

    def test_file_fsync_failure_removes_temp_and_no_final(self):
        with mock.patch.object(tool.os, 'fsync', side_effect=OSError('injected file fsync')):
            self.reject('injected file fsync')
        self.assertEqual(list(self.d.glob('.*.tmp-*')), [])

    def test_parent_fsync_failure_retains_complete_final(self):
        original = tool.os.fsync
        def fail(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                raise OSError('injected parent fsync')
            original(fd)
        with mock.patch.object(tool.os, 'fsync', fail):
            with self.assertRaisesRegex(OSError, 'injected parent fsync'):
                self.check(True)
        result = json.loads(self.output.read_text())
        self.assertIs(result['runtime'], False)
        self.assertEqual(list(self.d.glob('.*.tmp-*')), [])

    def test_temp_create_failure_preserves_preexisting_files(self):
        blocker = self.d / '.report.json.tmp-fixed'
        blocker.write_bytes(b'keep')
        with mock.patch.object(tool.uuid, 'uuid4', return_value=mock.Mock(hex='fixed')):
            self.reject('File exists')
        self.assertEqual(blocker.read_bytes(), b'keep')

    def test_bad_instruction_decode_rejected(self):
        self.objdump = self.fake('objdump', "import sys\nprint(' 100: ret\\n 101: (bad)' if '-d' in sys.argv else '')")
        self.reject('Rust object disassembly has undecoded instruction')

    def test_prefixed_operand_free_x87_rejected(self):
        self.objdump = self.fake('objdump', "import sys\nprint(' 100: data16 fninit' if '-d' in sys.argv else '')")
        self.reject('forbidden vector/x87/MMX instruction: fninit')

    def test_short_input_reads_complete(self):
        original = tool.os.pread
        with mock.patch.object(tool.os, 'pread', side_effect=lambda fd, n, offset: original(fd, min(n, 19), offset)):
            self.check(True)

    def test_input_read_failure_closes_prior_descriptors(self):
        before = set(os.listdir('/proc/self/fd'))
        original = tool.os.pread
        def fail(fd, n, offset):
            if os.fstat(fd).st_ino == self.obj.stat().st_ino:
                raise OSError('injected input read')
            return original(fd, n, offset)
        with mock.patch.object(tool.os, 'pread', fail):
            self.reject('injected input read')
        self.assertEqual(set(os.listdir('/proc/self/fd')), before)

    def test_fifo_input_does_not_block(self):
        fifo = self.d / 'fifo'
        os.mkfifo(fifo)
        self.map = fifo
        self.reject('link map is not a regular file')

    def test_partial_write_failure_cleans_temp(self):
        original = tool.os.write
        calls = 0
        def fail(fd, data):
            nonlocal calls
            calls += 1
            if calls == 1:
                return original(fd, data[:19])
            raise OSError('injected partial write')
        with mock.patch.object(tool.os, 'write', fail):
            self.reject('injected partial write')
        self.assertEqual(list(self.d.glob('.*.tmp-*')), [])


# Named cases retain individual unittest outcomes, rather than hiding the
# coverage count inside a loop with one generic exception assertion.
HEADER_CASES = {
    'magic': (0, '<B', 0, 'ELF version'),
    'class': (4, '<B', 1, 'ELF version'),
    'endian': (5, '<B', 2, 'ELF version'),
    'ident_version': (6, '<B', 0, 'ELF version'),
    'type': (16, '<H', 3, 'ELF version'),
    'machine': (18, '<H', 3, 'ELF version'),
    'version': (20, '<I', 2, 'ELF version'),
    'flags': (48, '<I', 1, 'ELF version'),
    'ehsize': (52, '<H', 63, 'ELF version'),
    'phentsize': (54, '<H', 55, 'ELF version'),
    'zero_phnum': (56, '<H', 0, 'program headers'),
    'excess_phnum': (56, '<H', 65, 'program headers'),
    'early_phoff': (32, '<Q', 63, 'program headers'),
    'late_phoff': (32, '<Q', 4090, 'program headers'),
    'overflow_phoff': (32, '<Q', (1 << 64) - 1, 'program headers'),
    'dynamic': (64, '<I', 2, 'unsupported program header'),
    'interp': (64, '<I', 3, 'unsupported program header'),
    'unknown_ph': (64, '<I', 7, 'unsupported program header'),
    'load_flags': (68, '<I', 8, 'invalid PT_LOAD'),
    'load_no_memory': (104, '<Q', 0, 'invalid PT_LOAD'),
    'load_file_gt_memory': (96, '<Q', 0x301, 'invalid PT_LOAD'),
    'load_file_outside': (72, '<Q', 0x1000, 'invalid PT_LOAD'),
    'load_file_overflow': (72, '<Q', (1 << 64) - 1, 'invalid PT_LOAD'),
    'load_alignment_power': (112, '<Q', 3, 'invalid PT_LOAD alignment'),
    'load_alignment_congruence': (112, '<Q', 0x100000000, 'invalid PT_LOAD alignment'),
    'load_below_window': (80, '<Q', tool.BASE - 0xf00, 'PT_LOAD outside'),
    'load_above_window': (104, '<Q', 8 * 1024 * 1024, 'PT_LOAD outside'),
    'load_virtual_overflow': (104, '<Q', (1 << 64) - 1, 'PT_LOAD outside'),
    'entry_bss': (24, '<Q', tool.BASE + 0x300, 'entry outside'),
    'entry_below': (24, '<Q', tool.BASE - 1, 'entry outside'),
    'entry_nonexec': (68, '<I', 6, 'entry outside'),
    'note_size': (152, '<Q', 4097, 'note exceeds'),
    'note_outside': (128, '<Q', 0x1000, 'note exceeds'),
    'note_overflow': (128, '<Q', (1 << 64) - 1, 'note exceeds'),
    'note_tail': (152, '<Q', 41, 'malformed note tail'),
    'note_name_bounds': (0x300, '<I', 0xffffffff, 'malformed note'),
    'note_desc_bounds': (0x304, '<I', 0xffffffff, 'malformed note'),
    'note_missing': (152, '<Q', 0, 'expected MCKERNEL'),
    'note_wrong_name': (0x30c, '<B', 88, 'expected MCKERNEL'),
    'note_wrong_type': (0x308, '<I', 1, 'expected MCKERNEL'),
    'note_wrong_version': (0x318, '<I', 3, 'expected MCKERNEL'),
    'note_wrong_linux': (0x31c, '<I', 0x60b00, 'expected MCKERNEL'),
    'note_wrong_header': (0x320, '<I', 6656, 'expected MCKERNEL'),
    'note_wrong_flags': (0x324, '<I', 0, 'expected MCKERNEL'),
}


def header_case(offset, fmt, value, message):
    def case(self):
        self.patch(offset, fmt, value)
        self.reject(message)
    return case


for name, values in HEADER_CASES.items():
    setattr(PostLinkTests, 'test_loader_' + name, header_case(*values))

for attr in ('image', 'map', 'obj', 'readelf', 'nm', 'objdump'):
    for replacement in (False, True):
        def digest_drift(self, attr=attr, replacement=replacement):
            original = tool.hashlib.sha256
            target_bytes = getattr(self, attr).read_bytes()
            fired = False
            def digest(data):
                nonlocal fired
                result = original(data)
                if data == target_bytes and not fired:
                    fired = True
                    self.mutate(attr, replacement)
                return result
            label = {'map': 'link map', 'obj': 'Rust object'}.get(attr, attr)
            with mock.patch.object(tool.hashlib, 'sha256', digest):
                self.reject(label + ' changed during admission')
            self.assertTrue(fired)
        setattr(PostLinkTests, f'test_digest_drift_{attr}_{replacement}', digest_drift)
        for stage in ('parse_elf', 'run_tool', 'output_evidence', 'publish'):
            def drift(self, attr=attr, replacement=replacement, stage=stage):
                if stage == 'publish':
                    # Mutate after report serialization/file fsync, before the
                    # live snapshots' pre-publication verification callback.
                    original = tool.os.fsync
                    fired = False
                    def injected(fd):
                        nonlocal fired
                        original(fd)
                        if not fired:
                            fired = True
                            self.mutate(attr, replacement)
                    label = {'map': 'link map', 'obj': 'Rust object'}.get(attr, attr)
                    with mock.patch.object(tool.os, 'fsync', injected):
                        self.reject(label + ' changed during admission')
                else:
                    self.drift_case(attr, replacement, stage)
            setattr(PostLinkTests, f'test_drift_{attr}_{replacement}_{stage}', drift)

    for kind in ('relative', 'symlink', 'parent_symlink'):
        def bad_path(self, attr=attr, kind=kind):
            original = getattr(self, attr)
            if kind == 'relative':
                setattr(self, attr, Path('relative'))
                message = 'path must be absolute'
            elif kind == 'symlink':
                link = self.d / 'alias'
                link.symlink_to(original)
                setattr(self, attr, link)
                message = 'Too many levels'
            else:
                link = self.d / 'alias'
                link.symlink_to(self.d)
                setattr(self, attr, link / original.name)
                message = 'Not a directory|Too many levels'
            self.reject(message)
        setattr(PostLinkTests, f'test_path_{attr}_{kind}', bad_path)

for instruction in ('fld1', 'fninit', 'fnop', 'fwait', 'fsin', 'fcompp', 'emms',
                    'paddb %mm0,%mm1', 'pand %xmm0,%xmm1 # <scalar_name>',
                    'movaps %xmm0,%xmm1 # <scalar_name>', 'addss %xmm0,%xmm1',
                    'vxorps %ymm0,%ymm0,%ymm0', 'vzeroupper', 'vzeroall',
                    'vaddps %zmm0,%zmm1,%zmm2', 'kmovw %eax,%k1', 'kortestw %k1,%k1',
                    'xsave (%rax)', 'fxrstor (%rax)', 'ldmxcsr (%rax)', 'stmxcsr (%rax)'):
    def forbidden(self, instruction=instruction):
        self.objdump = self.fake('objdump', f"import sys\nprint({' 100: ' + instruction!r} if '-d' in sys.argv else '')")
        self.reject('Rust object contains forbidden vector/x87/MMX instruction')
    setattr(PostLinkTests, 'test_forbidden_' + instruction.split()[0], forbidden)


if __name__ == '__main__':
    unittest.main()
