"""Finite lock/init/preempt object capture/check; reuse qualified ELF reader, no loader/runtime."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys


def record_and_check(request):
    reader = request['qualified_ELF_reader']
    path = Path(reader['path'])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == reader['sha256']
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('qualified_reader_for_kmsg_lock', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    image = module.Image(request['provider_object'])
    definitions, imports = module.parse_nm(Path(request['actual_nm']).read_text())
    assert set(definitions) == set(image.defined) and imports == image.undefined
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
    # Persist all actual emission before narrower source-owner assertions.
    capture = {
        'status': 'ACTUAL_ELF_EMISSION_RECORDED_BEFORE_SOURCE_OWNER_CHECKS',
        'object': request['provider_object'],
        'object_sha256': hashlib.sha256(image.raw).hexdigest(),
        'object_bytes': len(image.raw),
        'all_actual_symbols': image.symbols,
        'all_actual_sections': sections,
        'all_actual_relocations': image.relocations,
        'all_actual_genuine_U': sorted(image.undefined),
        'no_runtime_or_initialized_kernel_claim': True,
    }
    target = Path(request['actual_metadata_capture'])
    with target.open('x') as output:
        json.dump(capture, output, indent=2)
        output.write('\n')
    for name, fields in definitions.items():
        symbol = image.defined[name]
        assert fields == {'kind': image.kind(symbol), 'size': symbol['size']}, name
    required = set(request['required14_C_exports'])
    actual_functions = {name for name, symbol in image.defined.items() if symbol['type'] == 2}
    assert actual_functions == required, ('unexpected global function owner', actual_functions)
    for name in required:
        symbol = image.defined[name]
        assert image.kind(symbol) == 'T' and symbol['size'] > 0 and symbol['other'] & 3 == 0, name
    assert image.undefined == {'get_cpu_local_var', 'ihk_mc_get_processor_id'}, ('unplanned genuine import, stop before any join', image.undefined)
    buf = image.defined['kmsg_buf']
    assert buf['type'] == 1 and buf['size'] == 8 and buf['other'] & 3 == 0
    assert image.kind(buf) == 'B' and image.sections[buf['section']]['align'] >= 8
    singletons = [symbol for symbol in image.symbols
                  if symbol['type'] == 1 and symbol['section'] != 0 and 'KMSG_LOCK' in symbol['name']]
    assert len(singletons) == 1, ('one original private lock owner required', singletons)
    lock = singletons[0]
    assert lock['size'] == 4 and lock['bind'] in (0, 1)
    assert image.kind(lock) == 'B' and image.sections[lock['section']]['align'] >= 4
    flag = image.defined['cpu_local_var_initialized']
    assert flag['type'] == 1 and flag['size'] == 4 and flag['other'] & 3 == 0
    assert image.kind(flag) == 'B' and image.sections[flag['section']]['align'] >= 4
    objects = [symbol for symbol in image.symbols if symbol['type'] == 1 and symbol['section'] != 0]
    assert len(objects) == 3 and {symbol['name'] for symbol in objects} == {'kmsg_buf', lock['name'], 'cpu_local_var_initialized'}, ('unplanned data owner, stop for source reconciliation', objects)
    globals_expected = required | {'kmsg_buf', 'cpu_local_var_initialized'} | ({lock['name']} if lock['bind'] == 1 else set())
    assert set(image.defined) == globals_expected
    local_functions = [symbol for symbol in image.symbols if symbol['bind'] == 0 and symbol['type'] == 2]
    for function in local_functions:
        assert any(name in function['name'] for name in request['selected_source_private_helper_names']), ('unplanned emitted private/core function, retained actual capture requires reconciliation', function)
        assert image.kind(function) == 'T' and function['size'] > 0
    # Current selected wrappers must use this one actual 4-byte singleton.
    lock_section = image.sections[lock['section']]
    lock_references = {}
    for name in ['kprintf_lock', 'kprintf_unlock', 'kmsg_init']:
        function = image.defined[name]
        refs = [relocation for relocation in image.relocations
                if relocation['section'] == function['section']
                and function['value'] <= relocation['offset'] < function['value'] + function['size']
                and relocation['symbol']['section'] == lock['section']
                and relocation['symbol']['value'] + relocation['addend'] == lock['value']]
        assert refs, ('wrapper must reference original singleton', name)
        lock_references[name] = refs
    return {
        'status': 'PASS_ACTUAL_FINITE_LOCK_INIT_NATIVE_IRQ_PREEMPT_OBJECT_SOURCE_OWNERS',
        'object_sha256': capture['object_sha256'],
        'original_C_function_T': sorted(required),
        'actual_all_global_strong_owners': {name: {'kind': image.kind(symbol), 'size': symbol['size']} for name, symbol in image.defined.items()},
        'actual_original_singleton_symbol': lock,
        'actual_singleton_binding_class': 'GLOBAL_source_private_compiler_mangled' if lock['bind'] == 1 else 'LOCAL_source_private',
        'original_kmsg_buf_NULL_NOBITS_pointer_declaration': buf,
        'original_KMSG_LOCK_zero_NOBITS_declaration': lock,
        'all_three_debug_wrappers_reference_one_original_singleton': lock_references,
        'actual_selected_source_owned_local_helpers': local_functions,
        'original_cpu_local_var_initialized_zero_NOBITS_declaration': flag,
        'genuine_existing_CPU_getter_U': sorted(image.undefined),
        'all_actual_metadata_retained': str(target),
        'source_private_visibility_not_rewritten': True,
        'join_not_admitted_or_executed': True,
        'no_privileged_function_boot_buffer_init_or_runtime_claim': True,
    }
