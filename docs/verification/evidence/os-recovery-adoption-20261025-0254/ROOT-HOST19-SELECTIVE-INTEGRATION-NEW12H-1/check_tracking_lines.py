"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Exhaust all eight selector combinations in the actual changed source region.
This checks source line semantics only; no compiler/runtime acceptance.
"""
from pathlib import Path
import itertools
import json
import re
import time

HERE = Path(__file__).resolve().parent

def region(data):
    start = data.index('#line 363\n')
    end = data.index('\nstatic unsigned long', start) if '\nstatic unsigned long' in data[start:] else start + 4000
    # Stop immediately after the tracked free wrapper, before unrelated selectors.
    end = data.index('\n}', data.index('arch_rt_sigreturn_free_bridge(', start)) + 2
    return data[start:end]

def mapped(text, choices):
    logical, active, result = 1, True, []
    stack = []
    for line in text.splitlines():
        if line.startswith('#if '):
            match = re.fullmatch(r'#if defined\(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\) && defined\(MCKERNEL_RUST_F06_RT_SIGRETURN_(SYSCALL|SET_SIGNAL|CHECK_SIGNAL)\)', line)
            assert match, line
            stack.append((active, choices[match[1]]))
            active = active and choices[match[1]]
        elif line == '#else':
            parent, selected = stack[-1]
            active = parent and not selected
        elif line == '#endif':
            active = stack.pop()[0]
        elif line.startswith('#line '):
            assert re.fullmatch(r'#line [0-9]+', line), line
            if active:
                logical = int(line.split()[1])
                continue
        elif active and line.strip():
            result.append((logical, line))
        logical += 1
    assert not stack
    return result

def verify(text, original):
    baseline = mapped(original, {})
    alloc_free = [(n, line) for n, line in baseline if '__LINE__' in line]
    assert [n for n, _ in alloc_free] == [385, 391], alloc_free
    names = ['SYSCALL', 'SET_SIGNAL', 'CHECK_SIGNAL']
    for bits in itertools.product([False, True], repeat=3):
        actual = mapped(text, dict(zip(names, bits)))
        assert [(n, line) for n, line in actual if '__LINE__' in line] == alloc_free, bits
        # Every unchanged original body line present in this selection retains
        # its exact logical location; skip ubiquitous braces and blank lines.
        for n, line in baseline:
            if ('return syscall(' in line and not bits[0]
                or '\tset_signal(' in line and not bits[1]
                or '\tcheck_signal(' in line and not bits[2]):
                assert (n, line) in actual, (bits, n, line)

started = time.monotonic()
original = region((HERE / 'preimages/arch/x86_64/kernel/syscall.c').read_text())
candidate = region((HERE / 'candidate/arch/x86_64/kernel/syscall.c').read_text())
verify(candidate, original)
# Preserve the concrete failing retained proposal as a negative control: removing
# all six restoration directives must fail allocation/free tracking invariance.
bad = re.sub(r'^#line (364|369|370|375|376|381)\n', '', candidate, flags=re.M)
try:
    verify(bad, original)
except AssertionError:
    pass
else:
    raise AssertionError('original tracking-line defect was not rejected')
result = dict(status='PASS_EIGHT_SELECTOR_COMBINATIONS_AND_ORIGINAL_DEFECT_REJECTION',
              original_tracking_lines=[385,391], compiler_invocations=0,
              seconds=time.monotonic()-started)
(HERE / 'TRACKING-LINE-REGRESSION.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
