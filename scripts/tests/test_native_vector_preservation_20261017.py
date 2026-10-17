"""Compile/run real selected-profile vector app against its frozen Linux oracle.

No guest runs or production changes. All artifacts and negative controls retained.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
C_SOURCE = ROOT / 'scripts/application-tests/native-vector-preservation.c'
ASM_SOURCE = ROOT / 'scripts/application-tests/native-vector-preservation.S'
ORACLE = ROOT / 'docs/verification/native-vector-preservation-linux-oracle-20261017-1.json'
FLAGS = ['-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror', '-static', '-fno-pie', '-no-pie',
         '-march=x86-64', '-mtune=generic', '-mno-avx', '-Wl,-z,noexecstack', '-pthread']


class NativeVectorPreservationTests(unittest.TestCase):
    def test_linux_reference_and_state_corruption_controls(self):
        directory = Path(os.environ['NATIVE_VECTOR_PRESERVATION_OUTPUT'])
        directory.mkdir(exist_ok=False)
        oracle = json.loads(ORACLE.read_text())
        commands = []

        def capture(label, command, timeout=30):
            commands.append({'label': label, 'argv': command, 'cwd': str(directory)})
            (directory / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
            try:
                result = subprocess.run(command, cwd=directory, capture_output=True, timeout=timeout)
            except subprocess.TimeoutExpired as error:
                (directory / f'{label}.stdout').write_bytes(error.stdout or b'')
                (directory / f'{label}.stderr').write_bytes(error.stderr or b'')
                (directory / f'{label}.status').write_text('TIMEOUT\n')
                raise
            (directory / f'{label}.stdout').write_bytes(result.stdout)
            (directory / f'{label}.stderr').write_bytes(result.stderr)
            (directory / f'{label}.status').write_text(str(result.returncode) + '\n')
            commands[-1]['status'] = result.returncode
            (directory / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
            return result

        for path in (C_SOURCE, ASM_SOURCE, ORACLE):
            (directory / path.name).write_bytes(path.read_bytes())
        version = capture('compiler-version', ['/usr/bin/gcc', '--version'])
        self.assertEqual(version.returncode, 0, version.stderr)
        variants = [
            ('reference', None, oracle['expected_stdout'].encode()),
            ('xmm-corruption', '    pxor %xmm7, %xmm7', b'VECTOR_FAIL stage=syscall code=8\n'),
            ('mxcsr-corruption', '    ldmxcsr 4(%rsp)', b'VECTOR_FAIL stage=syscall code=18\n'),
            ('signal-marker-missing', '    cmpl $2, %r13d\n    jne 99f\n    pxor %xmm7, %xmm7\n99:',
             b'VECTOR_SYSCALL_PASS\nVECTOR_FUTEX_PASS\nVECTOR_FAIL stage=signal-state code=92\n'),
        ]
        selected = set(os.environ.get('NATIVE_VECTOR_PRESERVATION_VARIANTS',
                                      ','.join(item[0] for item in variants)).split(','))
        self.assertTrue(selected <= {item[0] for item in variants})
        for name, injection, stdout in variants:
            if name not in selected:
                continue
            asm = ASM_SOURCE.read_text()
            if name == 'signal-marker-missing':
                # The real tgkill handler runs but withholds its completion
                # marker. Also corrupt XMM7 only at the signal comparison
                # boundary: code92 must win before code8, testing gate order.
                marker = '    movl $1, native_vector_signal_seen(%rip)'
                self.assertEqual(asm.count(marker), 1)
                asm = asm.replace(marker, '    movl $0, native_vector_signal_seen(%rip)', 1)
            if injection:
                self.assertEqual(asm.count('    /* VECTOR_TEST_INJECTION */'), 1)
                asm = asm.replace('    /* VECTOR_TEST_INJECTION */', injection, 1)
            path = directory / f'{name}.S'
            path.write_text(asm)
            binary = directory / name
            result = capture(f'{name}.compile', ['/usr/bin/gcc', *FLAGS, str(directory / C_SOURCE.name),
                                                 str(path), '-o', str(binary)])
            self.assertEqual(result.returncode, 0, result.stderr.decode())
            result = capture(f'{name}.run', [str(binary)], 12)
            self.assertEqual(result.returncode, 0 if injection is None else 1, result.stderr)
            self.assertEqual(result.stdout, stdout)
            self.assertEqual(result.stderr, oracle['expected_stderr'].encode())
            print(name, 'exit=', result.returncode, result.stdout.decode(), sep='\n')
            if injection is None:
                headers = capture('reference.readelf', ['/usr/bin/readelf', '-W', '-l', str(binary)])
                self.assertEqual(headers.returncode, 0, headers.stderr)
                stack = [line for line in headers.stdout.decode().splitlines() if 'GNU_STACK' in line]
                self.assertEqual(len(stack), 1)
                self.assertRegex(stack[0], r'\bRW\s+0x')
                self.assertNotIn('INTERP', headers.stdout.decode())
                disassembly = capture('reference.probe-disassembly', ['/usr/bin/objdump', '-d',
                                       '--disassemble=native_vector_probe', str(binary)])
                self.assertEqual(disassembly.returncode, 0, disassembly.stderr)
                self.assertIn(b'syscall', disassembly.stdout)
                self.assertIn(b'pcmpeqb', disassembly.stdout)
                self.assertFalse(re.search(rb'\b[yz]mm\d', disassembly.stdout))
        (directory / 'input-hashes.json').write_text(json.dumps({
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (C_SOURCE, ASM_SOURCE, ORACLE, Path(__file__))}, indent=2) + '\n')


if __name__ == '__main__':
    unittest.main()
