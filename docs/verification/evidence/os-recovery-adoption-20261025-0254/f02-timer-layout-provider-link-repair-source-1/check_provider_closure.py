"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only ELF/map gate for the exact existing Rust __inline_memset provider.
"""
import importlib.util
import json
from pathlib import Path
import struct
import sys

Q = Path(__file__).resolve().parent
P = Q.parent / 'f02-timer-layout-storage-next-current-source-1'
spec = importlib.util.spec_from_file_location('retained_timer_ownership', P / 'check_table_ownership.py')
retained = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retained)
Elf, ref = retained.module.Elf, retained.module.ref
NAME = '__inline_memset'


def provider_definition(elf):
    assert elf.data[:6] == b'\x7fELF\x02\x01'
    assert struct.unpack_from('<HH', elf.data, 16) == (1, 62), 'Require x86_64 relocatable provider'
    undefined = [s['name'] for s in elf.symbols if s['name'] and s['ndx'] == 0]
    assert not undefined, ('Provider imports another implementation', undefined)
    exports = [s for s in elf.symbols if s['name'] and s['bind'] in (1, 2)
               and 0 < s['ndx'] < len(elf.sections) and elf.sections[s['ndx']]['flags'] & 2]
    assert len(exports) == 1 and exports[0]['name'] == NAME, ('Unexpected provider exports', exports)
    symbol = exports[0]
    assert symbol['kind'] == 2 and symbol['bind'] == 1 and symbol['size'] > 0
    section = elf.sections[symbol['ndx']]
    assert section['flags'] & 6 == 6 and not section['flags'] & 1, 'Provider must be executable and nonwritable'
    for relocations in elf.sections:
        if relocations['type'] != 4:
            continue
        assert relocations['info'] != symbol['ndx'] or relocations['size'] == 0, 'Provider code has relocations'
        if not elf.sections[relocations['info']]['flags'] & 2:
            continue
        symbols = elf.tables[relocations['link']]
        for off in range(0, relocations['size'], relocations['entsize']):
            _, info, _ = struct.unpack_from('<QQq', elf.data, relocations['off'] + off)
            target = symbols[info >> 32]
            assert target['ndx'] != 0, ('Allocated relocation imports external provider', target)
    return symbol


def function_bytes(elf, symbol):
    section = elf.sections[symbol['ndx']]
    begin = section['off'] + symbol['value'] - section['addr']
    result = elf.data[begin:begin + symbol['size']]
    assert len(result) == symbol['size']
    return result


def final_provider(provider, final, entries):
    symbol = provider_definition(provider)
    linked = final.definitions(NAME)
    assert len(linked) == 1, 'Final executable must have exactly one defined __inline_memset'
    linked = linked[0]
    assert linked['kind'] == 2 and linked['bind'] == 1 and linked['size'] == symbol['size']
    section = final.sections[linked['ndx']]
    assert section['flags'] & 6 == 6 and not section['flags'] & 1
    origin = retained.origin(provider, final, entries, NAME)
    assert function_bytes(provider, symbol) == function_bytes(final, linked), 'Final provider bytes changed'
    return dict(origin=origin, function_bytes=symbol['size'], undefined_provider_symbols=[],
                code_relocations=[], exact_provider_bytes=True)


def main():
    provider_path, final_path, map_path, output_path = map(Path, sys.argv[1:])
    provider, final = Elf(provider_path), Elf(final_path)
    result = final_provider(provider, final, retained.map_entries(map_path))
    result.update(scope=__doc__.splitlines()[0],
        status='PASS_EXACT_EXISTING_RUST_INLINE_MEMSET_PRODUCER_CLOSURE_AND_FINAL_ORIGIN',
        provider=ref(provider_path), executable=ref(final_path), linker_map=ref(map_path),
        production_or_native_credit=False)
    output_path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(status=result['status'], function_bytes=result['function_bytes'])))


if __name__ == '__main__':
    main()
