#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare selective retained HOST19 postimages. Does not mutate canonical sources.
"""
from pathlib import Path
import difflib
import hashlib
import json

HERE = Path(__file__).resolve().parent
E = HERE.parent
ROOT = E.parents[3]
F03 = E / 'm14-f03-selected-residual-implementation-20261026-1/next-perf-alloc-three-bridges-1'
F06 = E / 'm14-f06-selected-residual-implementation-20261026-1/next-rt-sigreturn-three-source-1'
F02 = E / 'f02-idle-layout-values-next-current-source-1'
outputs = {}

def source(path):
    if path not in outputs:
        outputs[path] = (ROOT / path).read_bytes()
    return outputs[path]

def replace(path, old, new):
    data = source(path)
    assert old and data.count(old) == 1, (path, old[:100], data.count(old))
    outputs[path] = data.replace(old, new, 1)

def ref(p):
    b = p.read_bytes()
    return dict(path=str(p), bytes=len(b), sha256=hashlib.sha256(b).hexdigest())

# Reuse exact qualified three selectors and Rust provider bodies.
for item in json.loads((F03 / 'SOURCE-SLICES.json').read_bytes())['selected_functions']:
    replace('kernel/syscall.c', Path(item['original']['path']).read_bytes(),
            Path(item['selector']['path']).read_bytes())
outputs['kernel/rust/syscall_policy.rs'] = source('kernel/rust/syscall_policy.rs') + (F03 / 'selected-bridges.Rust.inc').read_bytes()

# Each original fallback and following source keep their logical source lines.
# The retained HOST forwarding fixtures did not qualify this tracking property.
for lane, suffix, ret, args, first, after in [
    ('syscall', 'SYSCALL', 'long', 'int num, void *regs', 364, 369),
    ('set-signal', 'SET_SIGNAL', 'void', 'int sig, void *regs, const void *info', 370, 375),
    ('check-signal', 'CHECK_SIGNAL', 'void', 'int signum, void *regs, int num', 376, 381),
]:
    name = 'arch_rt_sigreturn_' + lane.replace('-', '_') + '_bridge'
    original = (F06 / lane / 'original-bridge.inc').read_bytes().lstrip(b'\n')
    selector = (f'#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F06_RT_SIGRETURN_{suffix})\n'
                f'extern {ret}\n{name}({args});\n#else\n#line {first}\n').encode()
    selector += original + f'#endif\n#line {after}\n'.encode()
    replace('arch/x86_64/kernel/syscall.c', original, selector)
    module = f'arch_rt_sigreturn_{lane.replace("-", "_")}_bridge.rs'
    dest = 'kernel/rust/' + module
    assert not (ROOT / dest).exists(), dest
    outputs[dest] = (F06 / lane / module).read_bytes()
    cfg = 'f06_rt_sigreturn_' + lane.replace('-', '_') + '_candidate'
    outputs['kernel/rust/syscall_policy.rs'] += (f'\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n'
        f'#[cfg({cfg})]\n#[path = "{module}"]\nmod {cfg};\n').encode()

# Apply only exact localized F02 changes; preserve the later timer owner.
for path in ['kernel/process.c', 'kernel/rust/process_helpers.rs']:
    before = (F02 / 'preimages' / path).read_bytes().splitlines(keepends=True)
    after = (F02 / 'candidate' / path).read_bytes().splitlines(keepends=True)
    edits = []
    for op, i, j, k, l in difflib.SequenceMatcher(None, before, after, autojunk=False).get_opcodes():
        if op == 'equal':
            continue
        # Anchor insertions with a genuine unchanged preceding source line.
        if i == j:
            assert i > 0
            prefix = b''.join(before[max(0, i-6):i])
            suffix = b''.join(before[i:i+6])
            old, new = prefix + suffix, prefix + b''.join(after[k:l]) + suffix
        else:
            old, new = b''.join(before[i:j]), b''.join(after[k:l])
        edits.append((old, new))
    for old, new in edits:
        replace(path, old, new)

# Select paired C/Rust gates under the existing supported production branch.
cm = 'kernel/CMakeLists.txt'
anchor = b'\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f06_forward_context_candidate")\n'
extra = b''.join((f'\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f06_rt_sigreturn_{s}_candidate")\n').encode() for s in ['syscall', 'set_signal', 'check_signal'])
replace(cm, anchor, anchor + extra + b'\t\t\t\tif (ENABLE_PERF)\n\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_perf_alloc_bridges_selected_candidate")\n\t\t\t\tendif()\n')
anchor = b'\t\t\t\tlist(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/arch_syscall_forward_context_bridge.rs")\n'
extra = b''.join((f'\t\t\t\tlist(APPEND RUST_KERNEL_SRCS "${{CMAKE_CURRENT_SOURCE_DIR}}/rust/arch_rt_sigreturn_{s}_bridge.rs")\n').encode() for s in ['syscall', 'set_signal', 'check_signal'])
replace(cm, anchor, anchor + extra)
replace(cm, b';MCKERNEL_RUST_F06_FORWARD_CONTEXT")', b';MCKERNEL_RUST_F06_FORWARD_CONTEXT;MCKERNEL_RUST_F06_RT_SIGRETURN_SYSCALL;MCKERNEL_RUST_F06_RT_SIGRETURN_SET_SIGNAL;MCKERNEL_RUST_F06_RT_SIGRETURN_CHECK_SIGNAL")')
anchor = b'\t\t\tset_property(SOURCE "${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/syscall.c" APPEND PROPERTY\n'
replace(cm, anchor, b'\t\t\tif (ENABLE_PERF)\n\t\t\t\tset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY\n\t\t\t\t\tCOMPILE_DEFINITIONS MCKERNEL_RUST_F03_PERF_ALLOC_BRIDGES)\n\t\t\tendif()\n' + anchor)

manifest = dict(scope=__doc__, status='PREPARED_NOT_ADOPTED_NOT_COMPILED', files=[])
for path, data in outputs.items():
    src, dst, pre = ROOT / path, HERE / 'candidate' / path, HERE / 'preimages' / path
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(data)
    old = src.read_bytes() if src.exists() else b''
    if src.exists():
        pre.parent.mkdir(parents=True, exist_ok=True)
        pre.write_bytes(old)
    diff = ''.join(difflib.unified_diff(old.decode().splitlines(keepends=True), data.decode().splitlines(keepends=True), fromfile='a/'+path, tofile='b/'+path))
    target = HERE / 'diffs' / (path + '.diff')
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(diff)
    manifest['files'].append(dict(destination=str(src), preimage=ref(src) if src.exists() else None, candidate=ref(dst), diff=ref(target)))
(HERE / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2)+'\n')
print(json.dumps(dict(status=manifest['status'], files=len(outputs), canonical_mutations=0)))
