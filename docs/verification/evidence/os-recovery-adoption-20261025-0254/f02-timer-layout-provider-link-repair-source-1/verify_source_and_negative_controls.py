"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure source binding and checker controls. No compiler, linker, test ELF or oracle execution.
"""
import copy
import json
from pathlib import Path
import struct
from types import SimpleNamespace

import check_provider_closure as check

Q = Path(__file__).resolve().parent


def fake_provider():
    data = bytearray(80)
    data[:6] = b'\x7fELF\x02\x01'
    struct.pack_into('<HH', data, 16, 1, 62)
    data[64:68] = b'ABCD'
    symbol = dict(name=check.NAME, kind=2, bind=1, ndx=1, value=0, size=4)
    elf = SimpleNamespace(path=Path('/exact/provider.o'), data=bytes(data), symbols=[symbol], tables={},
        sections=[dict(name='', flags=0, type=0),
                  dict(name='.text.__inline_memset', flags=6, type=1, off=64, addr=0, size=4)])
    elf.definitions = lambda name: [s for s in elf.symbols if s['name'] == name and s['ndx']]
    return elf


def negative_controls():
    provider = fake_provider()
    final = copy.deepcopy(provider)
    final.path = Path('/exact/timer')
    final.sections[1]['addr'] = 0x400000
    final.symbols[0]['value'] = 0x400000
    final.definitions = lambda name: [s for s in final.symbols if s['name'] == name and s['ndx']]
    entries = [('.text.__inline_memset', 0x400000, 4, '/exact/provider.o')]
    check.final_provider(provider, final, entries)
    mutations = [
        ('undefined_import', lambda e: e.symbols.append(dict(name='memset', ndx=0, bind=1, kind=2))),
        ('extra_provider', lambda e: e.symbols.append(dict(name='extra', ndx=1, bind=1, kind=2))),
        ('wrong_ABI_machine', lambda e: setattr(e, 'data', e.data[:18] + b'\x03\x00' + e.data[20:])),
        ('writable_code', lambda e: e.sections[1].update(flags=7)),
        ('weak_provider', lambda e: e.symbols[0].update(bind=2)),
        ('relocated_code', lambda e: e.sections.append(dict(type=4, info=1, size=24))),
    ]
    rejected = []
    for name, mutate in mutations:
        candidate = copy.deepcopy(provider)
        mutate(candidate)
        try:
            check.provider_definition(candidate)
        except AssertionError:
            rejected.append(name)
        else:
            raise AssertionError(('negative control accepted', name))
    for name, candidate, origins in [
        ('wrong_final_origin', final, [('.text.__inline_memset', 0x400000, 4, '/wrong/provider.o')]),
        ('wrong_final_bytes', copy.deepcopy(final), entries),
    ]:
        if name == 'wrong_final_bytes':
            candidate.data = candidate.data[:64] + b'WXYZ' + candidate.data[68:]
            candidate.definitions = lambda name: [s for s in candidate.symbols if s['name'] == name and s['ndx']]
        try:
            check.final_provider(provider, candidate, origins)
        except AssertionError:
            rejected.append(name)
        else:
            raise AssertionError(('negative control accepted', name))
    return rejected


def main():
    manifest = json.loads((Q / 'SOURCE-BINDING.json').read_text())
    for key in ['canonical_provider', 'canonical_aliases', 'provider_body', 'provider_crate',
                'architecture_header', 'string_header', 'corrected_main', 'expert_handoff']:
        row = manifest[key]
        assert check.ref(row['path']) == row, row['path']
    for row in manifest['retained_objects']:
        assert check.ref(row['path']) == row
    canonical = Path(manifest['canonical_provider']['path']).read_text()
    begin = canonical.index('#[no_mangle]\npub unsafe extern "C" fn __inline_memset(')
    end = canonical.index('\n#[no_mangle]', begin + 1)
    body = (Q / 'inline_memset.CURRENT.rs.inc').read_text()
    assert body == canonical[begin:end]
    aliases = Path(manifest['canonical_aliases']['path']).read_text()
    assert 'pub type CULong = u64;' in aliases and 'pub type SizeT = usize;' in aliases
    expected = ('// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n'
        '#![no_std]\nuse core::ffi::c_void;\nuse core::ptr::write_volatile;\n'
        'pub type CULong = u64;\npub type SizeT = usize;\n\n'
        'include!("inline_memset.CURRENT.rs.inc");\n')
    assert (Q / 'provider.rs').read_text() == expected
    assert manifest['C_prototype'] in Path(manifest['architecture_header']['path']).read_text()
    assert '#define memset __inline_memset' in Path(manifest['string_header']['path']).read_text()
    assert Path(manifest['corrected_main']['path']).read_text().count('memset(') == 3
    assert body.replace('while count >= 4', 'while count >= 8') != canonical[begin:end]
    rejected = negative_controls()
    report = dict(scope=__doc__.splitlines()[0], status='PASS_SOURCE_BINDING_AND_PURE_NEGATIVE_CONTROLS',
        exact_existing_provider=True, original_corrected_oracle_unchanged=True,
        retained_objects_unchanged=True, rejected_negative_controls=rejected,
        compiler_linker_or_oracle_executions=0, production_or_native_credit=False)
    (Q / 'SOURCE-ONLY-CHECKS.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
