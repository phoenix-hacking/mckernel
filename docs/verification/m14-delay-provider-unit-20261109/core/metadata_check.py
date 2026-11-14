"""Finite three-delay-function object capture; qualified ELF reader, no execution."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys


def record_and_check(request):
    reader = request['qualified_ELF_reader']
    assert hashlib.sha256(Path(reader['path']).read_bytes()).hexdigest() == reader['sha256']
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('qualified_reader_for_delay_unit', reader['path'])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    image = module.Image(request['provider_object'])
    definitions, imports = module.parse_nm(Path(request['actual_nm']).read_text())
    sections = []
    for section in image.sections:
        item = dict(section)
        if section['type'] == 8:
            item['NOBITS_declaration_only'] = True
        elif section['flags'] & 2:
            raw = image.contents(section)
            item['actual_allocated_file_bytes_hex'] = raw.hex()
            item['actual_allocated_file_bytes_sha256'] = hashlib.sha256(raw).hexdigest()
        sections.append(item)
    capture = {'status': 'ACTUAL_ALL_EMISSION_CAPTURED_BEFORE_DELAY_SOURCE_OWNER_CHECKS',
               'object_sha256': hashlib.sha256(image.raw).hexdigest(),
               'object_bytes': len(image.raw), 'all_actual_symbols': image.symbols,
               'all_actual_sections': sections, 'all_actual_relocations': image.relocations,
               'all_actual_genuine_U': sorted(image.undefined),
               'no_RDTSC_function_timing_or_native_execution': True}
    with Path(request['actual_metadata_capture']).open('x') as output:
        json.dump(capture, output, indent=2)
        output.write('\n')
    assert set(definitions) == set(image.defined) and imports == image.undefined
    assert set(image.defined) == set(request['required3_C_exports'])
    owner_bytes = {}
    for name, symbol in image.defined.items():
        assert image.kind(symbol) == 'T' and symbol['type'] == 2 and symbol['size'] > 0 and symbol['other'] & 3 == 0, name
        assert definitions[name] == {'kind': 'T', 'size': symbol['size']}
        owner_bytes[name] = {'bytes': symbol['size'], 'sha256': hashlib.sha256(image.symbol_bytes(symbol)).hexdigest()}
    assert image.undefined == {'cpu_pause'}, ('unplanned import, stop before futurejoin', image.undefined)
    data = [symbol for symbol in image.symbols if symbol['type'] == 1 and symbol['section'] != 0]
    assert not data, ('unplanned source/data owner; actual capture retained', data)
    private = [symbol for symbol in image.symbols if symbol['type'] == 2 and symbol['bind'] == 0]
    assert not private, ('unplanned private/core provider; actual capture retained', private)
    rdtsc = image.symbol_bytes(image.defined['rdtsc'])
    assert b'\x0f\x31' in rdtsc, 'Actual emittedrdtsc retainsnative opcode; no hardwareexecution'
    pause_refs = [relocation for relocation in image.relocations if relocation['symbol']['name'] == 'cpu_pause']
    assert pause_refs, 'Genuine pause provider relocation must remain'
    return {'status': 'PASS_CALLED_EXACT3_DELAY_SOURCE_OWNERS_AND_NATIVE_CODEGEN_ONLY',
            'object_sha256': capture['object_sha256'], 'actual3_global_C_T_bytes': owner_bytes,
            'genuine_remaining_U': ['cpu_pause'], 'source_owned_data_or_private_helpers': [],
            'actual_pause_relocations': pause_refs, 'native_rdtsc_opcode_retained_not_executed': True,
            'actual_all_emission_capture': request['actual_metadata_capture'],
            'no_join_or_function_or_counter_timing_native_acceptance': True}
