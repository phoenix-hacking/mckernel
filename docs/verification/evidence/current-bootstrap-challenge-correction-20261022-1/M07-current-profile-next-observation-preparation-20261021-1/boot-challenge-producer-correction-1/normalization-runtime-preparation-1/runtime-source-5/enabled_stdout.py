"""Exact AVX/YMM diagnostic stdout consumer; numeric exposure is observed.

This accepts no host feature constants and grants no guest authority. The
caller must preserve the full original stream and separately bind image/profile,
exit status, collector EOF, kernel logs and ownership retirement.
"""
import re

LIMIT = 1024
FIELDS = (
    (b'ENABLED_CPUID1', ('ecx', 'edx'), 8),
    (b'ENABLED_XCR0', ('hi', 'lo'), 8),
    (b'ENABLED_CPUIDD0', ('eax', 'ebx', 'ecx', 'edx'), 8),
    (b'ENABLED_CPUID7', ('ebx', 'ecx', 'edx'), 8),
    (b'ENABLED_AUXV', ('hwcap', 'hwcap2'), 16),
)
SUFFIX = (b'ENABLED_REQUIRED_XCR0=0000000000000007\n'
          b'ENABLED_SYSCALL_PASS\nENABLED_FUTEX_PASS\n'
          b'ENABLED_SIGNAL_PASS\nENABLED_PROFILE_PASS\n')


def validate_stdout(data):
    if type(data) is not bytes or len(data) > LIMIT:
        raise ValueError('stdout bytes/limit')
    lines = data.splitlines(keepends=True)
    if len(lines) != 10 or b''.join(lines[5:]) != SUFFIX:
        raise ValueError('exact line count/order/fixed PASS suffix')
    result = {}
    for line, (name, keys, width) in zip(lines[:5], FIELDS):
        pattern = re.escape(name) + b' ' + b' '.join(
            key.encode() + rb'=([0-9a-f]{' + str(width).encode() + b'})'
            for key in keys) + b'\n'
        match = re.fullmatch(pattern, line)
        if match is None:
            raise ValueError('feature record grammar/order')
        result[name.decode()] = {key: int(value, 16)
                                 for key, value in zip(keys, match.groups())}
    features = result['ENABLED_CPUID1']['ecx']
    if features & 0x1c000000 != 0x1c000000:
        raise ValueError('CPUID XSAVE/OSXSAVE/AVX gate')
    xcr0 = result['ENABLED_XCR0']['lo'] | result['ENABLED_XCR0']['hi'] << 32
    supported = (result['ENABLED_CPUIDD0']['eax'] |
                 result['ENABLED_CPUIDD0']['edx'] << 32)
    if xcr0 & 7 != 7 or xcr0 & ~supported:
        raise ValueError('XCR0 required/supported state gate')
    size = result['ENABLED_CPUIDD0']
    if not 832 <= size['ebx'] <= size['ecx']:
        raise ValueError('CPUIDD0 enabled/max standard XSAVE geometry')
    result['required_xcr0'] = 7
    result['observed_xcr0'] = xcr0
    result['supported_xcr0'] = supported
    result['scope'] = 'Observed process exposure plus explicit x87/SSE/YMM boundary checks; no whole ISA/IFUNC closure'
    return result


def validate_capture(data, stderr, exit_code, *, stdout_eof, stderr_eof,
                     stdout_discarded, stderr_discarded,
                     stdout_truncated, stderr_truncated):
    if (type(exit_code) is not int or exit_code != 0 or stderr != b'' or
            stdout_eof is not True or stderr_eof is not True or
            type(stdout_discarded) is not int or stdout_discarded != 0 or
            type(stderr_discarded) is not int or stderr_discarded != 0 or
            stdout_truncated is not False or stderr_truncated is not False):
        raise ValueError('exit/stderr/EOF/discard/truncation contract')
    return validate_stdout(data)
