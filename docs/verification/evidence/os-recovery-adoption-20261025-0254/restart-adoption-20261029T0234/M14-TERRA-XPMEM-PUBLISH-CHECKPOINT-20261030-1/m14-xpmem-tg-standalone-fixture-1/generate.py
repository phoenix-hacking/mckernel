#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Future source generation only. This program does not compile or execute a fixture.
Run solely in an admitted light-test profile with a fresh owned output directory.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re

ROOT = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/DISPATCHER-SOL-MAX-20261030-1')
BASE = ROOT / 'f06-debug-constants-align32-host-1/src/kernel/rust/xpmem_helpers.rs'
ABI = ROOT / 'f06-debug-constants-align32-host-1/src/kernel/rust/abi.rs'
PATCHED = ROOT / 'attempt-0002/m14-xpmem-tg-publish-order-1/xpmem_helpers.rs'
EXPECTED = {BASE: 'e8c7970b672c724f14da2eb0a12fdbcd11df62f824422a5f8a98da4364328255',
            ABI: 'ff48bc2e7c8fe00abf19572a3fe75661dd464a7a475fec91a0ac7d870f6fdd3e',
            PATCHED: '8a88864073aec2d288297893da072bc26ba34773405bedb09f7c981a0c398892'}

def read_bound(path):
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != EXPECTED[path]:
        raise RuntimeError('source digest mismatch: ' + str(path))
    return data.decode('utf-8')

def one_line(source, pattern):
    matches = list(re.finditer(pattern, source, re.MULTILINE))
    if len(matches) != 1:
        raise RuntimeError('expected exactly one match: ' + pattern)
    return matches[0].group(0)

def braced(source, marker, attributes=False):
    if source.count(marker) != 1:
        raise RuntimeError('expected exactly one marker: ' + marker)
    pos = source.index(marker)
    start = source.rfind('#[repr(', 0, pos) if attributes else pos
    if start < 0:
        raise RuntimeError('missing repr: ' + marker)
    open_pos = source.index('{', pos)
    depth = 0
    for i in range(open_pos, len(source)):
        if source[i] == '{': depth += 1
        elif source[i] == '}':
            depth -= 1
            if depth == 0: return source[start:i + 1]
    raise RuntimeError('unclosed body: ' + marker)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path,
                        help='fresh existing private directory for generated sources')
    args = parser.parse_args()
    out = args.output.resolve(strict=True)
    if not out.is_dir() or any((out / name).exists() for name in ('fixture.rs', 'BODY-BINDINGS.json')):
        raise RuntimeError('output must be an existing directory with fresh output names')
    original, patched, abi = read_bound(BASE), read_bound(PATCHED), read_bound(ABI)
    definition_markers = ['unsafe fn field_ptr<T>', 'fn ptr_is_err',
                          'pub extern "C" fn xpmem_tg_hashtable_index_result',
                          'pub struct XpmemOpenTgOffsets']
    defs = []
    for marker in definition_markers:
        old = braced(original, marker, marker.startswith('pub struct '))
        new = braced(patched, marker, marker.startswith('pub struct '))
        if old != new:
            raise RuntimeError('shared production definition differs: ' + marker)
        defs.append(old)
    for name in ('XpmemAllocFn', 'XpmemAtomicSetFn', 'XpmemTgRefFn', 'XpmemRwlockFn',
                 'XpmemObjectVoidFn', 'XpmemListAddTailFn'):
        pattern = r'^type ' + name + r' = [^\n]+;$'
        old = one_line(original, pattern)
        if old != one_line(patched, pattern): raise RuntimeError('callback ABI differs: ' + name)
        defs.append(old)
    for name in ('EINVAL', 'ENOMEM', 'XPMEM_AP_HASHTABLE_SIZE', 'XPMEM_TG_HASHTABLE_SIZE'):
        pattern = r'^const ' + name + r': [^\n]+;$'
        old = one_line(original, pattern)
        if old != one_line(patched, pattern): raise RuntimeError('constant differs: ' + name)
        defs.append(old)
    for name in ('CInt', 'SizeT'):
        defs.append(one_line(abi, r'^pub type ' + name + r' = [^\n]+;$'))
    for name in ('AbiListHead', 'IhkAtomic', 'IhkSpinlock', 'McsRwlockLock',
                 'XpmemHashlist', 'XpmemThreadGroupPrefix', 'XpmemPartitionPrefix'):
        defs.append(braced(abi, 'pub struct ' + name + ' {', True))
    marker = 'pub unsafe extern "C" fn xpmem_open_tg_body_result('
    bodies = [braced(original, marker), braced(patched, marker)]
    if bodies[0] == bodies[1]: raise RuntimeError('original and candidate bodies unexpectedly equal')
    harness_bytes = (Path(__file__).parent / 'fixture-tail.rs').read_bytes()
    harness_sha = hashlib.sha256(harness_bytes).hexdigest()
    if harness_sha != '7d0ae66207d453e452c03c6bc789b6880042db6530264d304a695c51e82dc9a2':
        raise RuntimeError('fixture-tail digest mismatch')
    harness = harness_bytes.decode('utf-8')
    source = ('#![allow(dead_code)]\nuse std::ffi::c_void;\nuse std::ptr::write_bytes;\n'
              + '#[repr(C)] pub struct Thread { _opaque: [u8; 0] }\n'
              + '#[repr(C)] pub struct ProcessVm { _opaque: [u8; 0] }\n'
              + '\n\n'.join(defs) + '\nmod original { use super::*;\n' + bodies[0] + '\n}\n'
              + 'mod patched { use super::*;\n' + bodies[1] + '\n}\n' + harness)
    (out / 'fixture.rs').write_text(source)
    bindings = {'sources': {str(k): v for k, v in EXPECTED.items()},
                'original_body_sha256': hashlib.sha256(bodies[0].encode()).hexdigest(),
                'patched_body_sha256': hashlib.sha256(bodies[1].encode()).hexdigest(),
                'generated_source_sha256': hashlib.sha256(source.encode()).hexdigest(),
                'fixture_tail_sha256': harness_sha,
                'scope': 'actual body; mocked providers; no kernel lifetime or runtime claim'}
    (out / 'BODY-BINDINGS.json').write_text(json.dumps(bindings, indent=2) + '\n')

if __name__ == '__main__': main()
