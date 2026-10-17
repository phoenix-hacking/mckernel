"""Bounded AVX state payload and Linux oracle, never guest acceptance."""
from pathlib import Path
import hashlib
import json
import os
import re
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[2]
C = ROOT / 'scripts/application-tests/native-vector-enabled-state.c'
ASM = ROOT / 'scripts/application-tests/native-vector-enabled-state.S'
FLAGS = ['-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror', '-static', '-fno-pie', '-no-pie',
         '-march=x86-64', '-mtune=generic', '-mno-avx', '-Wl,-z,noexecstack', '-pthread']
PASS = b'ENABLED_SYSCALL_PASS\nENABLED_FUTEX_PASS\nENABLED_SIGNAL_PASS\nENABLED_PROFILE_PASS\n'

class EnabledState(unittest.TestCase):
    def test_linux_and_negatives(self):
        out = Path(os.environ['NATIVE_ENABLED_OUTPUT'])
        out.mkdir(exist_ok=False)
        commands = []
        def run(label, argv, timeout=30):
            commands.append({'label': label, 'argv': argv})
            (out / 'commands.json').write_text(json.dumps(commands, indent=2)+'\n')
            try:
                p = subprocess.run(argv, cwd=out, capture_output=True, timeout=timeout)
            except subprocess.TimeoutExpired as error:
                (out / (label+'.stdout')).write_bytes(error.stdout or b'')
                (out / (label+'.stderr')).write_bytes(error.stderr or b'')
                (out / (label+'.status')).write_text('TIMEOUT\n')
                raise
            for ext, data in [('stdout',p.stdout),('stderr',p.stderr),('status',str(p.returncode).encode()+b'\n')]:
                (out / (label+'.'+ext)).write_bytes(data)
            return p
        # Oracle freezes behavior and negative expectations before compilation.
        variants = [('reference', None, PASS),
                    ('upper-clobber', '    vzeroupper', b'ENABLED_FAIL stage=syscall code=1\n'),
                    ('helper-clobber-detected', None, b'ENABLED_SYSCALL_PASS\nENABLED_FAIL stage=futex-wake code=-98\n'),
                    ('signal-marker-missing', None, b'ENABLED_SYSCALL_PASS\nENABLED_FUTEX_PASS\nENABLED_FAIL stage=signal-state code=92\n'),
                    ('wrong-mask', None, b'ENABLED_FAIL stage=xcr0-avx code=1\n')]
        (out/'frozen-oracle.json').write_text(json.dumps({name:{'exit':0 if name=='reference' else 1,'suffix':expected.decode(),'stderr':''} for name,_,expected in variants},indent=2)+'\n')
        for source in (C,ASM,Path(__file__)):
            (out/source.name).write_bytes(source.read_bytes())
        for name, injection, expected in variants:
            c, asm = C.read_text(), ASM.read_text()
            if name == 'signal-marker-missing':
                marker = '    movl $1, native_enabled_signal_seen(%rip)'
                self.assertEqual(asm.count(marker), 1)
                asm = asm.replace(marker, '    movl $0, native_enabled_signal_seen(%rip)')
                injection = '    cmpl $2, %r13d\n    jne 99f\n    vzeroupper\n99:'
            if name == 'helper-clobber-detected':
                marker = '    /* ENABLED_HELPER_TEST_INJECTION */'
                self.assertEqual(asm.count(marker), 1)
                asm = asm.replace(marker, '    vmovdqu enabled_ymm+224(%rip), %ymm7')
            if name == 'wrong-mask':
                self.assertEqual(c.count('if ((lo & 7u) != 7u)'), 1)
                c = c.replace('if ((lo & 7u) != 7u)', 'if (((lo & ~4u) & 7u) != 7u)')
            if injection:
                self.assertEqual(asm.count('    /* ENABLED_TEST_INJECTION */'), 1)
                asm = asm.replace('    /* ENABLED_TEST_INJECTION */', injection)
            cp, ap, binary = out/(name+'.c'), out/(name+'.S'), out/name
            cp.write_text(c); ap.write_text(asm)
            p = run(name+'.compile', ['/usr/bin/gcc', *FLAGS, str(cp),str(ap),'-o',str(binary)])
            self.assertEqual(p.returncode,0,p.stderr)
            p = run(name+'.run', [str(binary)],12)
            self.assertEqual(p.returncode,0 if name=='reference' else 1,p.stderr)
            self.assertEqual(p.stderr,b'')
            lines = p.stdout.splitlines(keepends=True)
            if name == 'wrong-mask':
                self.assertEqual(len(lines),3)
                self.assertEqual(lines[-1],expected)
                continue
            patterns = [rb'ENABLED_CPUID1 ecx=[0-9a-f]{8} edx=[0-9a-f]{8}\n',
                        rb'ENABLED_XCR0 hi=[0-9a-f]{8} lo=[0-9a-f]{8}\n',
                        rb'ENABLED_CPUIDD0 eax=[0-9a-f]{8} ebx=[0-9a-f]{8} ecx=[0-9a-f]{8} edx=[0-9a-f]{8}\n',
                        rb'ENABLED_CPUID7 ebx=[0-9a-f]{8} ecx=[0-9a-f]{8} edx=[0-9a-f]{8}\n',
                        rb'ENABLED_AUXV hwcap=[0-9a-f]{16} hwcap2=[0-9a-f]{16}\n',
                        rb'ENABLED_REQUIRED_XCR0=0000000000000007\n']
            self.assertEqual(len(lines),6+len(expected.splitlines()))
            for line,pattern in zip(lines,patterns): self.assertIsNotNone(re.fullmatch(pattern,line),line)
            self.assertEqual(b''.join(lines[6:]),expected)
            if name == 'reference':
                p = run('reference.disassembly',['/usr/bin/objdump','-d','--disassemble=native_enabled_probe',str(binary)])
                self.assertEqual(p.returncode,0); self.assertIn(b'%ymm15',p.stdout)
                p = run('reference.elf',['/usr/bin/readelf','-W','-l',str(binary)])
                self.assertEqual(p.returncode,0); self.assertNotIn(b'INTERP',p.stdout)
        (out/'input-hashes.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (C,ASM,Path(__file__))},indent=2)+'\n')
