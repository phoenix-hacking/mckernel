"""Finite actual3primitive object/disassembly gate; no runtime or linker."""
from pathlib import Path
import hashlib
import importlib.util
import json
import re
import sys


def actual_object_gate(q):
    for path, digest in q['source_bindings'].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path
    item = q['qualified_ELF_reader']
    assert hashlib.sha256(Path(item['path']).read_bytes()).hexdigest() == item['sha256']
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location('qualified_ELF_reader_for_scheduler_primitives', item['path'])
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    image = reader.Image(q['compiled_input']['path'])
    definitions, imports = reader.parse_nm(Path(q['actual_nm']).read_text())
    assert Path(q['actual_elf']).read_bytes()
    disassembly = Path(q['actual_disassembly']).read_text()
    assert disassembly
    sections = []
    for section in image.sections:
        item = dict(section)
        if section['type'] == 8:
            item['NOBITS_declaration_only'] = True
        elif section['flags'] & 2:
            item['actual_file_bytes_hex'] = image.contents(section).hex()
        sections.append(item)
    capture = dict(object_sha256=hashlib.sha256(image.raw).hexdigest(), object_bytes=len(image.raw),
                   symbols=image.symbols, sections=sections, relocations=image.relocations,
                   genuine_U=sorted(image.undefined), disassembly_sha256=hashlib.sha256(disassembly.encode()).hexdigest(),
                   no_atomic_or_lock_function_execution=True)
    with Path(q['actual_metadata_capture']).open('x') as stream:
        json.dump(capture, stream, indent=2)
        stream.write('\n')
    expected = set(q['expected3_C_exports'])
    assert capture['object_sha256'] == q['compiled_input']['sha256']
    assert set(definitions) == set(image.defined) == expected and imports == image.undefined == set(q['expected2_genuine_U'])
    actual_functions = [symbol for symbol in image.symbols if symbol['type'] == 2 and symbol['section'] != 0]
    assert {symbol['name'] for symbol in actual_functions} == expected and len(actual_functions) == 3
    for name, symbol in image.defined.items():
        assert image.kind(symbol) == 'T' and symbol['bind'] == 1 and symbol['type'] == 2 and symbol['size'] > 0 and symbol['other'] & 3 == 0
        assert definitions[name] == {'kind': 'T', 'size': symbol['size']}
    assert not [symbol for symbol in image.symbols if symbol['type'] == 1 and symbol['section'] != 0], 'No data/private object source owner selected'
    assert not [section for section in image.sections if section['flags'] & 3 == 3 and section['size']], 'No writable source state'
    unwind = []
    for section in image.sections:
        if not section['size'] or not section['flags'] & 2 or section['flags'] & 5:
            continue
        assert section['name'] == '.eh_frame' and section['type'] == 0x70000001 and section['align'] == 8 and section['flags'] == 2, ('Unreviewed readonly emission', section['name'])
        refs = [row for row in image.relocations if row['section'] == section['index']]
        assert refs
        for row in refs:
            symbol = row['symbol']
            position = symbol['value'] + row['addend']
            owners = [function['name'] for function in actual_functions if function['section'] == symbol['section'] and function['value'] <= position < function['value'] + function['size']]
            assert owners and set(owners) <= expected
        unwind.append(dict(section=section['name'], bytes=section['size'], source_function_references=refs))
    # Reuse the qualified string predicate's bounded objdump row/header parsing.
    current = None
    decoded = {name: [] for name in expected}
    for line in disassembly.splitlines():
        header = re.match(r'^([0-9a-f]+) <([^>]+)>:$', line.strip())
        if header:
            current = header.group(2)
            assert current in expected, ('Unexpected decoded function', current)
            continue
        row = re.match(r'^\s*([0-9a-f]+):\s+([a-z][a-z0-9_.]*)\s*(.*?)\s*$', line)
        if not row:
            continue
        assert current is not None
        address = int(row.group(1),16)
        symbol = image.defined[current]
        if not symbol['value'] <= address < symbol['value'] + symbol['size']:
            continue
        decoded[current].append(dict(address=address, mnemonic=row.group(2), operand=row.group(3), raw_line=line))
    assert all(decoded.values())
    delegates = {}
    for name, target in q['source_delegate_imports'].items():
        symbol = image.defined[name]
        refs = [row for row in image.relocations if row['section'] == symbol['section'] and symbol['value'] <= row['offset'] < symbol['value'] + symbol['size']]
        assert len(refs) == 1 and refs[0]['symbol']['name'] == target and refs[0]['symbol']['section'] == 0 and refs[0]['type'] == 1 and refs[0]['addend'] == 0, ('Actual genuine slock delegate', name, refs)
        ops = [(row['mnemonic'], row['operand'].replace(' ', '').lower()) for row in decoded[name]]
        assert ops == [('movabs','rax,0x0'),('jmp','rax')], ('Unreviewed wrapper lowering; retain actual instructions for review', name, ops)
        assert refs[0]['offset'] == decoded[name][0]['address'] + 2
        delegates[name] = dict(actual_instruction_rows=decoded[name], exact_genuine_import=target, actual_relocation=refs[0], original_RDI_pointer_unchanged_slock_offset0=True, original_node_argument_ignored=True)
    xchg = image.defined['xchg4']
    assert not [row for row in image.relocations if row['section'] == xchg['section'] and xchg['value'] <= row['offset'] < xchg['value'] + xchg['size']], 'No compiler/helper provider may implement atomic operation'
    ops = []
    explicit_lock = False
    for row in decoded['xchg4']:
        mnemonic, operand = row['mnemonic'], row['operand'].replace(' ','').lower()
        if mnemonic == 'lock':
            assert operand.startswith('xchg')
            mnemonic, operand = 'xchg', operand[len('xchg'):]
            explicit_lock = True
        if mnemonic == 'xchg':
            assert operand in ('dwordptr[rdi],eax','eax,dwordptr[rdi]','dwordptr[rdi],esi','esi,dwordptr[rdi]'), 'Actual32bit same-pointer exchange required'
            operand = 'mem32,eax' if 'eax' in operand else 'mem32,esi'
        ops.append((mnemonic,operand))
    allowed = {
        (('mov','eax,esi'),('xchg','mem32,eax'),('ret','')): 'new_ESI_to_EAX_then_memory_exchange_returns_old_EAX',
        (('xchg','mem32,esi'),('mov','eax,esi'),('ret','')): 'memory_exchange_ESI_then_old_ESI_to_return_EAX',
    }
    assert tuple(ops) in allowed, ('Unreviewed atomic lowering; stop before future join', ops)
    assert b'\x87' in image.symbol_bytes(xchg)
    return dict(status='PASS_CALLED_ACTUAL_THREE_PRIMITIVES_ATOMIC_AND_DELEGATE_METADATA',
                object_sha256=capture['object_sha256'], actual3T={name:image.defined[name]['size'] for name in sorted(expected)}, genuine2U=sorted(image.undefined),
                actual_wrapper_delegation=delegates, actual_xchg4_instruction_rows=decoded['xchg4'],
                xchg4_atomic_lowering=dict(accepted_dataflow=allowed[tuple(ops)], memory_operand_bits=32, new_value_CInt_input='esi', old_value_CInt_return='eax', memory_pointer='rdi', explicit_lock_prefix=explicit_lock, memory_XCHG_is_implicitly_atomic_without_explicit_lock=True, source_Ordering='SeqCst'),
                data_or_private_helper_owners=[], source_owned_unwind=unwind,
                actual_metadata_capture=q['actual_metadata_capture'], future_partial_join_unbound=True,
                no_atomic_lock_scheduler_IRQ_native_function_execution=True)
