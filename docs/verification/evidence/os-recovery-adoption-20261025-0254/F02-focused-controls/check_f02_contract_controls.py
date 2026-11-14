#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.

Focused ordinary read-only artifact/pure-predicate controls. No subprocess,
compiler, linker, Docker, root, guest or retained-input mutation. Run only after
the coordinator supplies actual physical clearance and an ordinary CPU grant.
"""
import argparse
import ast
import copy
import hashlib
import json
from pathlib import Path
import re
import struct
import time

B = Path(__file__).resolve().parent


def require(ok, message):
    if not ok:
        raise AssertionError(message)


def fixture(ok, message):
    # Invalid mutation setup must fail the harness, never count as the expected
    # production-predicate rejection of a negative control.
    if not ok:
        raise RuntimeError(('invalid control fixture', message))


def literal(tree, name):
    return next(ast.literal_eval(n.value) for n in tree.body
                if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name)
                and t.id == name for t in n.targets))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main(output):
    start = time.monotonic()
    loc = json.loads((B / 'SOURCE-LOCATORS.json').read_text())
    contract = json.loads((B / 'F02-DATA-PROFILE.CONTRACT.json').read_text())
    frozen_path = B / 'native_rust_exact_mckernel_image_offline.F02-PROFILE.SOURCE-ONLY.py'
    frozen_text = frozen_path.read_text()
    require(digest(frozen_path) == 'adb7003a47e99ddfb1d1496c07de702a5da59b3481df7ea8860f2afeb0b40830',
            'unchanged independently reviewed F02 candidate')
    require(digest(B / 'f02_data_contract.py') == 'f747b6fe08b0b0ee47f91199905815fcb11748e7af6015ccfd1ef93fc71a27d0',
            'unchanged independently reviewed F02 helper')
    require(digest(B / 'F02-DATA-PROFILE.CONTRACT.json') == 'e069f867c75e97b6497343d33c60f53f181c94bcae1545b77304904619e93893',
            'unchanged independently reviewed F02 profile')
    frozen_tree = ast.parse(frozen_text)
    source_check = next(n for n in frozen_tree.body if isinstance(n, ast.FunctionDef)
                        and n.name == '_m14_current81_f02_data_check').body[1]
    graph = next(n for n in frozen_tree.body if isinstance(n, ast.FunctionDef)
                 and n.name == '_m14_current81_actual_graph')
    abi_loop = next(n for n in graph.body if isinstance(n, ast.For)
                    and isinstance(n.target, ast.Tuple)
                    and [getattr(x, 'id', '') for x in n.target.elts] == ['label', 'row'])
    abi_identity_check = abi_loop.body[2]
    abi_template_assign, abi_template_check = abi_loop.body[-3:-1]
    # Compile the exact reviewed guard AST statements; no copied approximation
    # of their boolean expressions and no operation/driver entry-point import.
    guard_nodes = dict(source=[source_check], ABI_identity=[abi_identity_check],
                       ABI_template=[abi_template_assign, abi_template_check])
    guards = {name: compile(ast.Module(body=nodes, type_ignores=[]),
                           str(frozen_path), 'exec') for name, nodes in guard_nodes.items()}
    tree = ast.parse(Path(loc['driver']).read_text())
    original = literal(tree, 'M14_CURRENT81_CONTRACT')
    helper_path = Path(original['helpers']['F05']['path'])
    require(digest(helper_path) == original['helpers']['F05']['sha256'],
            'unchanged admitted ELF helper')
    nodes = [n for n in ast.parse(helper_path.read_text()).body
             if isinstance(n, ast.ClassDef) and n.name == 'Elf'
             or isinstance(n, ast.FunctionDef) and n.name in
             {'owning_relocations', 'object_bytes', 'relocated_location'}]
    ns = dict(struct=struct)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(helper_path), 'exec'), ns)
    exec(compile((B / 'f02_data_contract.py').read_text(),
                 str(B / 'f02_data_contract.py'), 'exec'), ns)
    build = Path(loc['build_root'])
    process = build / 'kernel/CMakeFiles/mckernel.img.dir/process.c.o'
    rust_path = build / 'kernel/rust/mckernel_rust.o'
    image = build / 'kernel/mckernel.img'
    map_path = build / 'kernel/mckernel.img.map'
    old_path = Path(loc['old_F02'])
    source_path = Path(loc['source_root']) / 'kernel/process.c'
    inputs = [process, rust_path, image, map_path, old_path, source_path,
              helper_path, B / 'f02_data_contract.py',
              B / 'F02-DATA-PROFILE.CONTRACT.json', frozen_path]
    for row in contract['retained_actual_ABI'].values():
        inputs.extend([build / row['relative_source'], build / row['relative_object']])
    before = {str(p): digest(p) for p in inputs}
    elf, old, rust = (ns['Elf'](p) for p in (process, old_path, rust_path))
    final = ns['_f02_final_view'](image)
    link_map = map_path.read_text()
    aliases = contract['source_aliases']
    results = []
    guard_source_sha256 = {name: hashlib.sha256('\n'.join(
        ast.get_source_segment(frozen_text, node) for node in nodes).encode()).hexdigest()
        for name, nodes in guard_nodes.items()}

    def passed(name, action, negative=False):
        try:
            action()
        except (AssertionError, ValueError) as error:
            if not negative:
                raise
            results.append(dict(name=name, expected='REJECT', actual='REJECT',
                                rejection=str(error)[:300]))
        else:
            require(not negative, ('negative control unexpectedly accepted', name))
            results.append(dict(name=name, expected='PASS', actual='PASS'))

    def check(e=None, h=None, f=None, m=None):
        actual = ns['_f02_collect'](elf if e is None else e,
                    ns if h is None else h, aliases,
                    final if f is None else f, link_map if m is None else m)
        return ns['_f02_require_profile'](actual, contract['profiles']['GCC14'])

    def named(e, name):
        rows = [r for r in e.symbols if r['name'] == name]
        fixture(len(rows) == 1, ('unique symbol', name))
        return rows[0]

    def mutate_symbol(name, field, value):
        e = copy.deepcopy(elf)
        named(e, name)[field] = value
        check(e=e)

    def mutate_section(field, value):
        e = copy.deepcopy(elf)
        e.sections[named(e, 'resource_set_lock')['shndx']][field] = value
        check(e=e)

    def altered_helpers(name, byte_offset=None, refs=None):
        h = dict(ns)
        if byte_offset is not None:
            base = ns['object_bytes']
            def changed(e, row):
                raw = bytearray(base(e, row))
                if row['name'] == name:
                    raw[byte_offset] ^= 1
                return bytes(raw)
            h['object_bytes'] = changed
        if refs is not None:
            base_refs = ns['owning_relocations']
            def changed_refs(e, row):
                rows = copy.deepcopy(base_refs(e, row))
                if row['name'] == name:
                    refs(rows)
                return rows
            h['owning_relocations'] = changed_refs
        return h

    def final_symbols(name, field, value):
        f = dict(final, symbols=copy.deepcopy(final['symbols']))
        rows = [r for r in f['symbols'] if r['name'] == name]
        fixture(len(rows) == 1, 'unique final mutation target')
        rows[0][field] = value
        check(f=f)

    def final_byte(address):
        f = dict(final)
        original_read = final['read']
        def changed_read(start, count):
            raw = bytearray(original_read(start, count))
            if start <= address < start + count:
                raw[address-start] ^= 1
            return bytes(raw)
        f['read'] = changed_read
        check(f=f)

    def imports(r=None):
        edges = ns['_f02_rust_edges'](rust if r is None else r, ns,
                                      contract['explicit_C_globals'])
        require(edges == contract['Rust_allocated_relocations_to_C_globals'],
                'exact ten allocated Rust-to-C imports')

    def rust_relocation(change):
        r = copy.deepcopy(rust)
        raw = bytearray(r.raw)
        candidates = []
        for section in r.sections:
            if section['type'] != 4 or not r.sections[section['info']]['flags'] & 2:
                continue
            for i in range(section['size'] // 24):
                pos = section['offset'] + 24*i
                offset, info, addend = struct.unpack_from('<QQq', raw, pos)
                if r.symbols[info >> 32]['name'] in contract['explicit_C_globals']:
                    candidates.append((section, pos, offset, info, addend))
        fixture(candidates, 'real allocated Rust C-data relocations')
        change(r, raw, candidates)
        r.raw = bytes(raw)
        imports(r)

    def exact_guard(name, memory=None, variables=None):
        # A byte overlay models read-only source/object drift. Hashing consumes
        # those bytes; the exact reviewed production guard decides acceptance.
        # All path/stat identities otherwise stay those of retained actual files.
        memory = {} if memory is None else memory
        env = dict(hashlib=hashlib, contract=contract, _fail=require,
                   _sha256=lambda path: hashlib.sha256(memory.get(str(path),
                       Path(path).read_bytes())).hexdigest(),
                   # Physical hashes use retained host files; the original
                   # compiler produced witness text inside its exact /src
                   # namespace. Only template reconstruction uses that root.
                   source_root=Path('/src') if name == 'ABI_template'
                               else Path(loc['source_root']),
                   M14_CURRENT81_C_FILES=literal(frozen_tree, 'M14_CURRENT81_C_FILES'),
                   M14_CURRENT81_ABI_WITNESSES=literal(frozen_tree, 'M14_CURRENT81_ABI_WITNESSES'))
        if variables:
            env.update(variables)
        exec(guards[name], env)

    def changed_bytes(path):
        raw = bytearray(path.read_bytes())
        fixture(raw, 'nonempty actual source/object control')
        raw[len(raw)//2] ^= 1
        return bytes(raw)

    passed('exact current 119 owners/whole bytes/RELA/final map', check)
    def historical():
        actual = ns['_f02_collect'](old, ns, aliases)
        ns['_f02_require_profile'](actual, contract['profiles']['GCC9'])
        require(actual['semantics'] == contract['profiles']['GCC14']['semantics'],
                'exact historical/current semantic join')
        require(len(actual['common_names']) == 3, 'three genuine historical C COMMON owners')
    passed('GCC9 COMMON3 plus allocated116 equals GCC14 semantic119', historical)
    passed('exact ten actual allocated Rust imports retain C-data debt', imports)
    passed('exact current source SHA through reviewed guard', lambda: exact_guard('source'))
    def abi():
        for label, row in contract['retained_actual_ABI'].items():
            variables = dict(label=label, row=row, witness=build / row['relative_source'],
                             target=build / row['relative_object'])
            exact_guard('ABI_identity', variables=variables)
            relative = literal(frozen_tree, 'M14_CURRENT81_C_FILES')[
                literal(frozen_tree, 'M14_CURRENT81_ABI_WITNESSES')[label][0]][0]
            fixture('#include "/src/%s"' % relative in variables['witness'].read_text(),
                    'exact retained producer include namespace')
            exact_guard('ABI_template', variables=dict(variables, relative=relative))
    passed('three retained successful actual ABI source/object identities', abi)

    def historical_missing_common():
        e = copy.deepcopy(old)
        common = named(e, 'runq_reservation_lock')
        fixture(common['shndx'] == 0xfff2, 'actual historical COMMON fixture')
        e.symbols.remove(common)
        actual = ns['_f02_collect'](e, ns, aliases)
        ns['_f02_require_profile'](actual, contract['profiles']['GCC9'])
    passed('historical COMMON owner removed', historical_missing_common, True)
    passed('current source byte drift through reviewed source guard',
           lambda: exact_guard('source', {str(source_path): changed_bytes(source_path)}), True)
    for label, row in contract['retained_actual_ABI'].items():
        witness, target = build / row['relative_source'], build / row['relative_object']
        variables = dict(label=label, row=row, witness=witness, target=target)
        for role, path in [('source', witness), ('object', target)]:
            passed('retained ABI %s %s byte drift' % (label, role),
                   lambda p=path, v=variables: exact_guard('ABI_identity',
                       {str(p): changed_bytes(p)}, v), True)
        templates = copy.deepcopy(literal(frozen_tree, 'M14_CURRENT81_ABI_WITNESSES'))
        template = templates[label][1]
        fixture('_Static_assert(' in template, 'actual compiled static ABI assertions')
        changed = template.replace('_Static_assert(', '_Static_assert(0 && ', 1)
        templates[label] = (templates[label][0], changed)
        relative = literal(frozen_tree, 'M14_CURRENT81_C_FILES')[templates[label][0]][0]
        passed('retained ABI %s producer namespace drift' % label,
               lambda v=variables, r=relative: exact_guard('ABI_template',
                   variables=dict(v, relative=r, source_root=Path(loc['source_root']))), True)
        passed('retained ABI %s assertion/template drift' % label,
               lambda v=variables, t=templates, r=relative: exact_guard('ABI_template',
                   variables=dict(v, relative=r, M14_CURRENT81_ABI_WITNESSES=t)), True)
        type_templates = copy.deepcopy(literal(frozen_tree, 'M14_CURRENT81_ABI_WITNESSES'))
        fixture('__builtin_types_compatible_p' in template, 'actual compiled ABI type assertions')
        type_templates[label] = (type_templates[label][0], template.replace(
            '__builtin_types_compatible_p', '__builtin_types_compatible_p_CHANGED', 1))
        passed('retained ABI %s type-assertion source drift' % label,
               lambda v=variables, t=type_templates, r=relative: exact_guard('ABI_template',
                   variables=dict(v, relative=r, M14_CURRENT81_ABI_WITNESSES=t)), True)

    def removed():
        e = copy.deepcopy(elf)
        e.symbols.remove(named(e, 'resource_set_list'))
        check(e=e)
    passed('missing owner', removed, True)
    def extra(duplicate):
        e = copy.deepcopy(elf)
        row = copy.deepcopy(named(e, 'resource_set_list'))
        if not duplicate:
            row['name'] = 'unadmitted_C_data_owner'
        e.symbols.append(row)
        check(e=e)
    passed('extra owner', lambda: extra(False), True)
    passed('duplicate owner name', lambda: extra(True), True)
    def hide_bss_as_common():
        e = copy.deepcopy(elf)
        row = named(e, 'resource_set_lock')
        fixture(row['shndx'] != 0xfff2, 'actual allocated current C lock')
        row['shndx'] = 0xfff2
        # COMMON is an ordinary ET_REL storage class, not an allocated final
        # section index. Recollect its storage inventory through the existing
        # COMMON-aware collector without the allocated-only final-image view.
        # The exact current profile must reject its allocated/common name sets
        # before comparing fingerprints. Do not count an IndexError as proof.
        actual = ns['_f02_collect'](e, ns, aliases)
        ns['_f02_require_profile'](actual, contract['profiles']['GCC14'])
    passed('current allocated C lock hidden as COMMON storage', hide_bss_as_common, True)
    for name, field, value in [
            ('resource_set_lock', 'size', 32),
            ('resource_set_list', 'size', 8),
            ('runq_reservation_lock', 'size', 8),
            ('resource_set_list', 'bind', 0),
            ('resource_set_lock', 'type', 0),
            ('resource_set_list', 'value', 136)]:
        passed('symbol %s %s=%s' % (name, field, value),
               lambda n=name, k=field, v=value: mutate_symbol(n, k, v), True)
    def visibility():
        e = copy.deepcopy(elf)
        raw = bytearray(e.raw)
        raw[e.table['offset'] + 24*named(e, 'resource_set_lock')['index'] + 5] = 2
        e.raw = bytes(raw)
        check(e=e)
    passed('hidden C lock visibility', visibility, True)
    section = elf.sections[named(elf, 'resource_set_lock')['shndx']]
    for field, value in [('flags', section['flags'] & ~1),
                         ('flags', section['flags'] | 4), ('type', 1), ('align', 32)]:
        passed('section %s=%s' % (field, value),
               lambda k=field, v=value: mutate_section(k, v), True)
    local = next(r['name'] for r in elf.symbols if r['name'].startswith('ddebug.'))
    function = next(r['name'] for r in elf.symbols if r['name'].startswith('__func__.'))
    passed('arbitrary compiler-local ID', lambda: mutate_symbol(local, 'name', 'ddebug.999999'), True)
    for label, name, offset in [('descriptor line', local, 24),
                               ('descriptor flags', local, 27),
                               ('descriptor format field', local, 16),
                               ('function string byte', function, 0)]:
        passed(label, lambda n=name, o=offset: check(h=altered_helpers(n, byte_offset=o)), True)
    def drop(rows):
        fixture(rows, 'real pointer relocation')
        rows.pop()
    def duplicate(rows):
        fixture(rows, 'real pointer relocation')
        rows.append(copy.deepcopy(rows[0]))
    def ref_field(rows, field, value):
        fixture(rows, 'real pointer relocation')
        rows[0][field] = value
    for label, change in [('missing pointer RELA', drop), ('duplicate pointer RELA', duplicate),
                          ('wrong RELA width', lambda rows: ref_field(rows, 'type', 10)),
                          ('wrong RELA addend', lambda rows: ref_field(rows, 'addend', rows[0]['addend']+1))]:
        passed(label, lambda c=change: check(h=altered_helpers(local, refs=c)), True)
    def target(rows):
        fixture(rows, 'real pointer relocation')
        rows[0]['target'] = copy.deepcopy(named(elf, 'resource_set_lock'))
    passed('wrong RELA target', lambda: check(h=altered_helpers(local, refs=target)), True)
    def unadmitted_source_alias():
        e = copy.deepcopy(elf)
        candidates = []
        for row in ns['_f02_data_symbols'](e):
            for ref in ns['owning_relocations'](e, row):
                decoded = ns['_f02_target'](e, ref, ns, aliases)
                if decoded['kind'] == 'source':
                    candidates.append(ref)
        fixture(candidates, 'real source alias relocation')
        ref = candidates[0]
        target = ref['target']
        offset = e.sections[target['shndx']]['offset'] + target['value'] + ref['addend']
        raw = bytearray(e.raw)
        fixture(raw[offset] == ord('/'), 'actual absolute process.c source alias')
        # Preserve size and basename, changing one exact admitted prefix byte.
        raw[offset] = ord('X')
        e.raw = bytes(raw)
        check(e=e)
    passed('unadmitted source alias with same process.c basename', unadmitted_source_alias, True)
    lock_final = next(r for r in final['symbols'] if r['name'] == 'resource_set_lock')
    for field, value in [('bind', 0), ('type', 0), ('size', 32),
                         ('value', lock_final['value']+8), ('visibility', 2)]:
        passed('final lock %s=%s' % (field, value),
               lambda k=field, v=value: final_symbols('resource_set_lock', k, v), True)
    passed('final BSS nonpointer byte', lambda: final_byte(lock_final['value']), True)
    # Compiler-local names repeat across input objects. Bind the mutation to
    # this exact process.c.o contribution and complete ET_REL symbol identity,
    # matching the reviewed final-owner observer rather than the first name.
    local_row = named(elf, local)
    process_contributions = ns['_f02_map_contributions'](link_map, elf)
    local_address = process_contributions[elf.sections[local_row['shndx']]['name']]['address'] + local_row['value']
    local_visibility = elf.raw[elf.table['offset'] + 24*local_row['index'] + 5]
    local_final_rows = [r for r in final['symbols'] if r['name'] == local and
                        r['value'] == local_address and r['size'] == local_row['size'] and
                        r['bind'] == local_row['bind'] and r['type'] == local_row['type'] and
                        r['visibility'] == local_visibility and
                        0 < r['shndx'] < len(final['sections'])]
    fixture(len(local_final_rows) == 1, 'unique exact process contribution descriptor owner')
    local_final = local_final_rows[0]
    local_refs = ns['owning_relocations'](elf, local_row)
    fixture(local_refs, 'descriptor actual pointer slots')
    passed('final descriptor pointer value', lambda: final_byte(local_final['value']+local_refs[0]['offset']), True)
    def identical_string_pointer_drift():
        # Model a second same-content string extent and change only the stored
        # pointer. The original pointer observer accepts those equal bytes; the
        # reviewed complete owner fingerprint must still reject pointer drift.
        ref = next(r for r in local_refs
                   if ns['_f02_target'](elf, r, ns, aliases)['kind'] in ('source', 'string'))
        decoded = ns['_f02_target'](elf, ref, ns, aliases)
        content = bytes.fromhex(decoded.get('literal', decoded['bytes']))
        pointer_slot = local_final['value'] + ref['offset']
        original_pointer = int.from_bytes(final['read'](pointer_slot, 8), 'little')
        fixture(final['read'](original_pointer, len(content)) == content, 'real original string pointee')
        duplicate_address = max(s['addr'] + s['size'] for s in final['sections']) + 4096
        duplicate_section = dict(type=1, flags=2, addr=duplicate_address, size=len(content))
        f = dict(final, sections=copy.deepcopy(final['sections']) + [duplicate_section])
        def changed_read(address, count):
            if duplicate_address <= address and address + count <= duplicate_address + len(content):
                return content[address-duplicate_address:address-duplicate_address+count]
            raw = bytearray(final['read'](address, count))
            pointer = duplicate_address.to_bytes(8, 'little')
            for i in range(8):
                if address <= pointer_slot+i < address+count:
                    raw[pointer_slot+i-address] = pointer[i]
            return bytes(raw)
        f['read'] = changed_read
        check(f=f)
    passed('same-content string at different final stored pointer', identical_string_pointer_drift, True)
    passed('wrong exact process map contributor', lambda: check(m=link_map.replace(
        'CMakeFiles/mckernel.img.dir/process.c.o', 'CMakeFiles/mckernel.img.dir/processXcXo')), True)
    def changed_map_extent(field):
        pattern = re.compile(r'^(\s+)(\S+)(\s+)(0x[0-9a-f]+)(\s+)(0x[0-9a-f]+)( CMakeFiles/mckernel\.img\.dir/process\.c\.o)$', re.M)
        contributions = ns['_f02_map_contributions'](link_map, elf)
        matches = [m for m in pattern.finditer(link_map) if m[2] in contributions]
        fixture(matches, 'actual exact process input map contribution')
        match = matches[0]
        group = 4 if field == 'address' else 6
        begin, end = match.span(group)
        changed = link_map[:begin] + hex(int(match[group], 16)+8) + link_map[end:]
        check(m=changed)
    passed('exact process map contribution extent drift', lambda: changed_map_extent('size'), True)
    passed('exact process map contribution base drift', lambda: changed_map_extent('address'), True)
    def rust_offset(r, raw, candidates):
        sec, pos, offset, info, addend = candidates[0]
        struct.pack_into('<QQq', raw, pos, offset+1, info, addend)
    passed('Rust imported C-data relocation offset', lambda: rust_relocation(rust_offset), True)
    def rust_missing(r, raw, candidates):
        for sec, pos, offset, info, addend in candidates:
            struct.pack_into('<QQq', raw, pos, offset, info & 0xffffffff, addend)
    passed('missing actual Rust imports', lambda: rust_relocation(rust_missing), True)
    def rust_duplicate(r, raw, candidates):
        # Extend a real relocation section in an in-memory copied raw view.
        # Keep original rows and append one genuine C-import row, preserving
        # symbol/link/info/stride geometry so only the extra edge differs.
        sec, pos, offset, info, addend = candidates[0]
        fixture(sec['size'] % 24 == 0, 'actual relocation section geometry')
        copied = bytes(raw[sec['offset']:sec['offset']+sec['size']])
        sec['offset'] = len(raw)
        raw.extend(copied + struct.pack('<QQq', offset, info, addend))
        sec['size'] += 24
    passed('duplicate allocated Rust C-data import', lambda: rust_relocation(rust_duplicate), True)
    def rust_defined():
        r = copy.deepcopy(rust)
        named(r, 'resource_set_lock')['shndx'] = 1
        imports(r)
    passed('C data falsely defined as Rust', rust_defined, True)
    require(all(digest(p) == before[str(p)] for p in inputs), 'all retained inputs unchanged')
    report = dict(scope=__doc__.splitlines()[0], status='PASS_FOCUSED_ARTIFACT_PREDICATE_CONTROLS',
                  positives=sum(r['expected']=='PASS' for r in results),
                  negatives=sum(r['expected']=='REJECT' for r in results), results=results,
                  input_sha256=before, retained_inputs_unchanged=True,
                  exact_reviewed_guard_AST_sha256=guard_source_sha256,
                  physical_source_root=loc['source_root'], ABI_template_producer_source_root='/src',
                  seconds=time.monotonic()-start, compiler_invocations=0,
                  subprocesses=0, guest_apps=0, image_builds=0,
                  C_data_debt=True, native=False, full_validator=False,
                  limits='Focused contract/source/ABI identity controls only. Assertion/template drift is detected by exact reviewed witness-text checks, not newly compiled ABI evaluation. Future three-global type/alignment ABI witness and full-validator/native proof remain open.')
    with output.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k:report[k] for k in ('status','positives','negatives','seconds')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    main(args.output)
