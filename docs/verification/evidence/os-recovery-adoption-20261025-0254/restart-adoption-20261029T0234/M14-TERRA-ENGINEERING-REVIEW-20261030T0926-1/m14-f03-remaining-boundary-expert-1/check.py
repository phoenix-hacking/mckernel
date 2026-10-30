#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Bounded source analysis: no compiler, physical workload, or release authority.
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ATTEMPT = Path(__file__).resolve().parents[1]
INPUTS = {
    "c": (ROOT / "nonheld-generic-arch-host-preparation-1/src/kernel/syscall.c", "4af4524be701ecdbaae09fba906c99bd065364c4caefdcf007820f463773eaf4"),
    "vma": (ROOT / "f06-debug-constants-align32-host-1/src/kernel/rust/syscall_mprotect_host_vma.rs", "11a6131f8f8e826912602bf89fdd32bad7675d184f4e43c16b6375f54d17b881"),
    "policy": (ROOT / "f06-debug-constants-align32-host-1/src/kernel/rust/syscall_policy.rs", "11d9d9e14c6c4ee3d593083ce18137414a7780c23507a44fb0834937fa9618e4"),
    "kfree": (ROOT / "f06-debug-constants-align32-host-1/src/kernel/rust/syscall_ptrace_detach_kfree.rs", "b5793ef0ee2b837e356917c070a8931de5f893463190deea469641dd1e38e0f0"),
    "cmake": (ATTEMPT / "m14-root-and-nonheld-composite-1/postimage/kernel/CMakeLists.txt", "f34958844cf2a16d25244a3acc7c9610f262bc9cc64aba2db9706cc64a2a2655"),
}

def mask_c(text):
    """Mask C comments/literals but retain offsets and newlines for bounded analysis."""
    pattern = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.S)
    return pattern.sub(lambda m: ''.join('\n' if c == '\n' else ' ' for c in m.group()), text)

def c_function(text, name, signature):
    masked = mask_c(text)
    matches = list(re.finditer(signature, masked))
    if len(matches) != 1:
        raise ValueError(f"{name}: expected one definition, got {len(matches)}")
    start = matches[0].start()
    opening = masked.find('{', matches[0].end())
    if opening < 0:
        raise ValueError(f"{name}: missing body")
    depth = 0
    for i in range(opening, len(masked)):
        if masked[i] == '{':
            depth += 1
        elif masked[i] == '}':
            depth -= 1
            if depth == 0:
                return masked[start:i + 1], start
    raise ValueError(f"{name}: unbalanced body")

def mmap_calls(body):
    calls = list(re.finditer(r'\bset_host_vma\s*\(', body))
    if len(calls) != 3:
        raise ValueError(f"expected three direct do_mmap calls, got {len(calls)}")
    forms = re.findall(r'(?:\berror\s*=\s*|\(\s*void\s*\)\s*)set_host_vma\s*\(', body)
    if len(forms) != 3 or sum(x.lstrip().startswith('error') for x in forms) != 2:
        raise ValueError("unexpected do_mmap call forms")
    return [x.start() for x in calls]

def main():
    data = {}
    for name, (path, expected) in INPUTS.items():
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f"source digest differs: {name}")
        data[name] = raw.decode()
    c, v, q, k, m = (data[x] for x in ("c", "vma", "policy", "kfree", "cmake"))
    body, start = c_function(c, 'do_mmap', r'\bintptr_t\s+do_mmap\s*\([^;{}]*\)\s*(?=\{)')
    calls = mmap_calls(body)
    # Capture physical source lines; these are not compiler logical __LINE__ values.
    lines = [c.count('\n', 0, start + x) + 1 for x in calls]
    wrapper, _ = c_function(c, 'set_host_vma', r'\bstatic\s+int\s+set_host_vma\s*\([^;{}]*\)\s*(?=\{)')
    forward = wrapper.index('syscall_generic_forwarding')
    ret = wrapper.index('return set_host_vma_body_result')
    if ret >= forward:
        raise ValueError('C wrapper no longer returns before legacy forwarding')
    if not all(x in v for x in ('mprotect_set_host_vma_bridge', 'ihk_mc_syscall_set_arg0', 'ihk_mc_syscall_set_arg1', 'ihk_mc_syscall_set_arg2', 'set_host_vma_body_result(start, len, prot, holding_lock)')):
        raise ValueError('Rust adapter chain differs')
    startq = q.index('pub extern "C" fn set_host_vma_body_result(')
    endq = q.index('\n#[no_mangle]', startq)
    selected = q[startq:endq]
    if not all(x in selected for x in ('#[cfg(native_linux_irq_work_v6_12)]', 'clear_host_pte_body_result(', 'Some(syscall_policy_do_syscall3_bridge)', '#[cfg(not(native_linux_irq_work_v6_12))]')):
        raise ValueError('selected/fallback host VMA path differs')
    if 'ptrace_detach_kfree_bridge' not in c or 'f03_ptrace_kfree_profile_119' not in q or 'crate::mem_helpers::kfree_tracked' not in k:
        raise ValueError('kfree candidate binding differs')
    if any(x in m for x in ('MCKERNEL_F03_PTRACE_KFREE_PROFILE_119_EXPERIMENTAL',
                            'MCKERNEL_RUST_F03_PTRACE_KFREE_PROFILE_119',
                            'f03_ptrace_kfree_profile_119', 'f03_ptrace_kfree_dispatch_origin')):
        raise ValueError('kfree selector present in this composite')
    # Regression checks: whitespace and inert literals do not count; a missing or
    # extra real call is rejected. These are syntax checks, not path reachability.
    altered = body.replace('error = set_host_vma', 'error   =\n set_host_vma', 1)
    mmap_calls(altered)
    mmap_calls(mask_c(body + '\n/* set_host_vma(1) */ "set_host_vma(2)"\n'))
    for bad in (body.replace('set_host_vma(', 'not_the_call(', 1), body + '\nset_host_vma(0);\n'):
        try:
            mmap_calls(bad)
        except ValueError:
            pass
        else:
            raise ValueError('negative regression did not reject drift')
    print(json.dumps({"status": "PASS_EXPERT_SOURCE_BOUNDARY_ONLY", "physical_c_call_lines": lines,
        "direct_mmap_calls": len(calls), "kfree_selector_in_composite": False,
        "limits": "No cfg execution, C parser, full caller coverage, ABI, forwarding equivalence, ownership, link, or native proof.",
        "source_hashes": {str(p): h for p, h in INPUTS.values()}}, indent=2))

if __name__ == '__main__':
    main()
