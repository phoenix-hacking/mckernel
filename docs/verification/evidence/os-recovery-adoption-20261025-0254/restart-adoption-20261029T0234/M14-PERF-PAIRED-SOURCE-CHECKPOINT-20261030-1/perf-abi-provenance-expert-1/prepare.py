#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source-only generator: no compiler, tests, final link, guest or native work.
Not reviewed or admitted for execution.
"""
import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import stat

ROOT = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/MANUAL-RESUME-M14-20261030-2')
PREDECESSOR = ROOT / 'perf-abi-witness-coherent-correction-1'
TEMPLATE = PREDECESSOR / 'TARGET-CONTRACT.json'
TEMPLATE_SHA = '248c016333908972adb21538e5d2daf4a6b8705783da3d4a2fce7f29ae8c4dc1'
COMPARATOR = Path(__file__).resolve().parent / 'compare_elf.py'
COMPARATOR_SHA = 'baa35735e39207dfc3772b88c82fc5b380695599003a01d709ef2bbe96d08d1a'
EXPECTED_WITNESS = '632d3ce6039f26c4995034798e30465f54ba36c1d5af0da2299bf98ff2021e0c'
EXPECTED_PATCH = 'cb71f19e839df9f039b0e816c8e34220055413586576fa81f0557f1fb02f7c1a'
SOURCES = {
    ROOT / 'perf-group-failure-source-1/f03_perf_entry_candidate.rs': 'd542c9f0a1793c8140f38c3d4439a9176742c420f94f792f76eafeb3981f82a5',
    ROOT / 'perf-paired-selector-private-1/REAL-HEADER-ABI-WITNESS.c.inc': '212fbf03425ea1e883f01cd4132b3821cca224a015890cabeaf3fda95e80d8c0',
    ROOT / 'perf-selector-independent-review-1/REVIEW.md': 'daaa6ff29143c886683d0519ead33ec84724cb54cc4208707f8a3f5b486cfee3',
    ROOT / 'nonheld-signal-perf-group-compositor-1/NONHELD-SIGNAL-PERF-GROUP.PRIVATE.patch': '595d137bcaba9b4ce85361623edd5a12c174dc3baa53670bda5352ce80dd1d1a',
    ROOT / 'perf-paired-selector-private-1/PERF-PAIRED-SELECTOR.PRIVATE.patch': '7aaa310aaa15d12b0ce3a4c49a48f40e3a0e23a2d14c134b264935fbed93f345',
}
NAMES = ['copy_from', 'attr_freq', 'event_alloc', 'counter_alloc', 'syscall', 'allocate',
         'read', 'ioctl', 'mmap', 'close', 'fcntl', 'lock', 'unlock']
TYPES = ['SyscallCopyFromUserFn', 'PerfAttrFreqFn', 'PerfOpenAllocEventFn', 'PerfCounterAllocFn',
         'PerfOpenSyscallFn', 'SyscallPolicyAllocFn', 'SyscallMckfdLongFn', 'SyscallMckfdIntFn',
         'SyscallMckfdLongFn', 'SyscallMckfdIntFn', 'SyscallMckfdIntFn', 'SyscallMckfdLockFn',
         'SyscallMckfdUnlockFn']
LIMIT = 16 * 1024 * 1024


def sha(data):
    return hashlib.sha256(data).hexdigest()


def capture(path, expected=None):
    with open(path, 'rb') as file:
        before = os.fstat(file.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > LIMIT:
            raise ValueError('input must be a bounded regular file: ' + str(path))
        data = file.read(LIMIT + 1)
        after = os.fstat(file.fileno())
    fields = lambda v: (v.st_dev, v.st_ino, v.st_size, v.st_mtime_ns, v.st_ctime_ns)
    if fields(before) != fields(after) or len(data) != before.st_size:
        raise ValueError('input changed during capture: ' + str(path))
    if expected is not None and sha(data) != expected:
        raise ValueError('input hash mismatch: ' + str(path))
    return data, (before.st_dev, before.st_ino)


def make_witness(entry, contract):
    text = entry.decode('utf-8')
    matches = list(re.finditer(r'pub\(super\) static f03_perf_entry_binding_v1: PerfEntryBinding = PerfEntryBinding \{\n(.*?)\n\};', text, re.S))
    if len(matches) != 1:
        raise ValueError('binding occurrence count is not one')
    fields = re.findall(r'^\s*(\w+):\s*(.*),\s*$', matches[0].group(1), re.M)
    if len(fields) != 44:
        raise ValueError('binding must have 31 scalars and 13 callbacks')
    scalars, callbacks = fields[:31], fields[31:]
    if not all(value.endswith('as CULong') for _, value in scalars):
        raise ValueError('unexpected scalar type')
    if [key for key, _ in callbacks] != NAMES:
        raise ValueError('callback slot order mismatch')
    if scalars[11] != ('allocation_flags', '(super::IHK_MC_AP_NOWAIT) as CULong'):
        raise ValueError('unexpected policy constant expression')
    actual_fields = [{'index': i, 'name': key, 'rust_expression': value,
                      **({'rust_witness_expression': value.replace('super::IHK_MC_AP_NOWAIT', 'super::super::IHK_MC_AP_NOWAIT')}
                         if key == 'allocation_flags' else {})}
                     for i, (key, value) in enumerate(scalars)]
    if contract.get('fields') != actual_fields:
        raise ValueError('corrected contract scalar provenance mismatch')
    supplied = contract.get('callbacks')
    if not isinstance(supplied, list) or len(supplied) != 13:
        raise ValueError('corrected contract callback count mismatch')
    for (key, value), typ, row in zip(callbacks, TYPES, supplied):
        if (row.get('slot'), row.get('rust_type_alias'), row.get('rust_binding_expression')) != (key, typ, value):
            raise ValueError('corrected contract callback provenance mismatch: ' + key)
    lines = ['//! Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
             '//! Witness-only module; compile only in a separate object excluded from every image link.',
             'use super::*;', '#[used]', '#[no_mangle]',
             'pub static f03_perf_entry_rust_scalar_witness_v1: [CULong; 31] = [']
    lines += ['    ' + (v.replace('super::IHK_MC_AP_NOWAIT', 'super::super::IHK_MC_AP_NOWAIT')
                        if k == 'allocation_flags' else v) + ', // ' + k for k, v in scalars]
    lines += ['];', 'const _: () = { assert!(size_of::<[CULong; 31]>() == 248); };']
    for (key, value), typ in zip(callbacks, TYPES):
        match = re.fullmatch(r'Some\((\w+)\)', value)
        if not match:
            raise ValueError('unexpected callback expression: ' + key)
        lines.append('const _: ' + typ + ' = ' + match.group(1) + '; // ' + key)
    lines.append('const _: unsafe extern "C" fn(CInt, *mut X86UserContext) -> CLong = sys_perf_event_open;')
    witness = ('\n'.join(lines) + '\n').encode()
    append = ('\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n'
              '// Witness-only: use only in separate, excluded Rust witness object.\n'
              '#[cfg(f03_perf_entry_abi_witness)]\n#[path = "f03_perf_entry_abi_witness.rs"]\n'
              'mod f03_perf_entry_abi_witness;\n')
    patch = ''.join(difflib.unified_diff(text.splitlines(keepends=True), (text + append).splitlines(keepends=True),
                                        fromfile='a/kernel/rust/f03_perf_entry_candidate.rs',
                                        tofile='b/kernel/rust/f03_perf_entry_candidate.rs')).encode()
    if sha(witness) != EXPECTED_WITNESS or sha(patch) != EXPECTED_PATCH:
        raise ValueError('witness output does not reproduce corrected artifacts')
    return witness, patch


def put_new(path, data):
    with open(path, 'xb') as file:
        file.write(data)
        file.flush()
        os.fsync(file.fileno())


def generate(out_dir):
    out_dir = Path(out_dir)
    if not out_dir.is_absolute() or out_dir.exists() or out_dir.is_symlink():
        raise ValueError('output must be a new absolute directory')
    parent = out_dir.parent.resolve(strict=True)
    if not parent.is_dir():
        raise ValueError('output parent must be a directory')
    out_dir = parent / out_dir.name
    template_bytes, template_id = capture(TEMPLATE, TEMPLATE_SHA)
    comparator_bytes, comparator_id = capture(COMPARATOR, COMPARATOR_SHA)
    generator_bytes, generator_id = capture(Path(__file__).resolve())
    captured = {}
    identities = [template_id, comparator_id, generator_id]
    for path, expected in SOURCES.items():
        data, identity = capture(path, expected)
        captured[path] = data
        identities.append(identity)
    if len(set(identities)) != len(identities):
        raise ValueError('source inputs alias by device and inode')
    contract = json.loads(template_bytes)
    if contract.get('inputs') != {str(path): expected for path, expected in SOURCES.items()}:
        raise ValueError('corrected contract source-input provenance mismatch')
    if (contract.get('structure', {}).get('scalar_count') != 31 or
            contract.get('structure', {}).get('callback_count') != 13 or
            contract.get('structure', {}).get('scalar_bytes') != 248 or
            contract.get('structure', {}).get('total_bytes') != 352):
        raise ValueError('corrected contract ABI dimensions mismatch')
    if sha(comparator_bytes) != contract['outputs']['comparator']['sha256']:
        raise ValueError('corrected contract comparator provenance mismatch')
    witness, patch = make_witness(captured[next(iter(SOURCES))], contract)
    if (contract['outputs']['rust_witness']['sha256'] != sha(witness) or
            contract['outputs']['witness_only_entry_patch']['sha256'] != sha(patch)):
        raise ValueError('corrected contract artifact provenance mismatch')
    contract['outputs']['rust_witness'] = {'path': str(out_dir / 'f03_perf_entry_abi_witness.rs'), 'sha256': sha(witness)}
    contract['outputs']['witness_only_entry_patch'] = {'path': str(out_dir / 'RUST-WITNESS-ONLY.PRIVATE.patch'), 'sha256': sha(patch)}
    contract['outputs']['comparator']['path'] = str(COMPARATOR.resolve())
    contract['outputs']['generator'] = {'path': str(Path(__file__).resolve()), 'sha256': sha(generator_bytes),
                                        'status': 'EXPERT_SUCCESSOR_UNREVIEWED_UNEXECUTED'}
    contract['provenance'] = {'corrected_contract': {'path': str(TEMPLATE), 'sha256': sha(template_bytes)},
                              'comparator_capture_sha256': sha(comparator_bytes),
                              'generator_capture_sha256': sha(generator_bytes),
                              'note': 'Derived from exact corrected contract; paths and generator provenance rebound. Source-only; no acceptance.'}
    contract['status'] = 'PRIVATE_EXPERT_SUCCESSOR_SOURCE_ONLY_NOT_EXECUTED_OR_RELEASED'
    out_dir.mkdir(mode=0o700)  # exclusive reservation; never reuse or overwrite
    put_new(out_dir / 'f03_perf_entry_abi_witness.rs', witness)
    put_new(out_dir / 'RUST-WITNESS-ONLY.PRIVATE.patch', patch)
    put_new(out_dir / 'TARGET-CONTRACT.json', (json.dumps(contract, indent=2, sort_keys=True) + '\n').encode())
    return contract


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    result = generate(args.output_dir)
    print(json.dumps({'status': result['status'], 'output_dir': str(Path(args.output_dir).resolve())}))


if __name__ == '__main__':
    main()
