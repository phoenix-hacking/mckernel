#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Strict selected-C/coherent-Rust partial-link observer. No artifact execution.
"""
import ast
import hashlib
import json
from pathlib import Path
import shlex
import struct
ROOT = Path(__file__).resolve().parent
recipe = json.loads((ROOT / 'EXACT-SOURCE38-SELECTED-C-ABI-PARTIAL-LINK.NOT-GRANTED.json').read_text())
def need(condition, message):
    if not condition:
        raise ValueError(message)
def auth(row):
    raw = Path(row['path']).read_bytes()
    need(len(raw) == row['bytes'] and hashlib.sha256(raw).hexdigest() == row['sha256'], 'exact source/object/header changed: ' + row['path'])
    return raw
m = json.loads(auth(recipe['input_map']))
for row in recipe['pinned_inputs']:
    auth(row)
source = auth(m['qualified_Elf_source'])
nodes = [node for node in ast.parse(source).body if isinstance(node, ast.ClassDef) and node.name == 'Elf' or isinstance(node, ast.FunctionDef) and node.name in {'owning_relocations', 'object_bytes'}]
ns = dict(Path=Path, struct=struct)
exec(compile(ast.Module(body=nodes, type_ignores=[]), '<qualified-ELF-object-reader-only>', 'exec'), ns)
Elf, owning, object_bytes = ns['Elf'], ns['owning_relocations'], ns['object_bytes']
out = ROOT / 'output-1'
process, syscall = Elf(out / 'process.selected.o'), Elf(out / 'syscall.selected.o')
partial, rust = Elf(out / 'coherent-selected.partial.o'), Elf(Path(m['Source37_Rust']['path']))
def undefined(elf):
    return {row['name'] for row in elf.symbols if row['name'] and row['shndx'] == 0}
def defined(elf):
    return {row['name'] for row in elf.symbols if row['name'] and row['shndx'] != 0 and row['bind'] in (1, 2)}
def rows(elf, name):
    return [row for row in elf.symbols if row['name'] == name and row['shndx'] != 0]
def function(elf, name):
    found = rows(elf, name)
    need(len(found) == 1 and found[0]['bind'] == 1 and found[0]['type'] == 2 and found[0]['size'] > 0, 'unique Rust function owner missing: ' + name)
    need(elf.sections[found[0]['shndx']]['flags'] & 6 == 6, 'function is not allocated executable storage')
    return found[0]
for name, elf in [('process',process),('syscall',syscall)]:
    need(defined(elf) == set(m['old_' + name + '_D']), 'selected C definitions changed outside declaration selectors: ' + name)
    need(undefined(elf) == set(m['old_' + name + '_U']), 'selected C imports changed outside declaration selectors: ' + name)
    need(not set(m['new_helper_providers']) & defined(elf), 'C object supplies a new Rust helper')
    need(not set(m['shared_storage']) & defined(elf), 'C still defines/common-owns Rust shared storage')
need(undefined(partial) == set(m['strict_expected_remaining_C_imports']), 'unexpected unresolved import; no new helper/debt allowance')
need(not set(m['new_helper_providers']) & undefined(partial), 'new helper unresolved')
need('process_destroy_thread_hash_detach_bridge' not in defined(partial) | undefined(partial), 'old detach provider remains in ON cohort')
providers = {name:function(partial,name) for name in m['new_helper_providers']}
data = {}
for name, expected in m['shared_storage'].items():
    found = rows(partial,name)
    need(len(found) == 1 and found[0]['bind'] == 1 and found[0]['type'] == 1 and found[0]['size'] == expected['size'], 'unique shared data shape differs: ' + name)
    symbol = found[0]
    need(0 < symbol['shndx'] < len(partial.sections), 'shared storage is unresolved/common')
    need(partial.sections[symbol['shndx']]['align'] >= expected['minimum_alignment'] and symbol['value'] % expected['minimum_alignment'] == 0, 'shared storage alignment differs')
    need(object_bytes(partial,symbol).hex() == expected['initial_hex'], 'shared storage initializer differs')
    need(not owning(partial,symbol), 'unexpected shared storage pointer relocation')
    data[name] = symbol

# Validate the original exact-object machine contract without altering it.
need(__debug__, 'accepted inline helper assertions must remain enabled')
contract = json.loads(auth(m['accepted_inline_machine']['contract']))
accepted_ownership = json.loads(auth(m['accepted_inline_machine']['ownership']))
need(contract['accepted_object_only'] == m['Source37_Rust'] == accepted_ownership['object'], 'exact accepted Rust object/machine proof binding differs')
inline_ns = {}
helper = m['accepted_inline_machine']['helper']
exec(compile(auth(helper), helper['path'], 'exec'), inline_ns)
check_inline = inline_ns['check_inline_machine_body']

# ELF table/section indices can move in ld -r. Normalize their meanings while
# retaining every function-relative relocation, exact allocation contribution,
# symbol alias and machine byte. This is specific to the fixed six callers.
def overlapping_aliases(elf, symbol):
    return sorted((item['name'], item['bind'], item['type'], item['size'], item['value'] - symbol['value'])
                  for item in elf.symbols
                  if item['shndx'] == symbol['shndx'] and item['type'] in (1, 2) and item['size']
                  and max(item['value'], symbol['value']) < min(item['value'] + item['size'], symbol['value'] + symbol['size']))

def semantic_relocation(reference_row, linked_row):
    need(reference_row['offset'] == linked_row['offset'] and reference_row['type'] == linked_row['type'], 'caller-relative relocation offset/type changed')
    reference_target, linked_target = reference_row['target'], linked_row['target']
    if reference_target['type'] == 3:
        need(reference_target['bind'] == linked_target['bind'] == 0 and linked_target['type'] == 3
             and reference_target['name'] == linked_target['name'] == '' and reference_target['size'] == linked_target['size'] == 0,
             'anonymous section relocation replaced by a symbol/alias')
        old_section = rust.sections[reference_target['shndx']]
        new_section = partial.sections[linked_target['shndx']]
        need(old_section['name'] == new_section['name'] and old_section['type'] == new_section['type']
             and old_section['flags'] == new_section['flags'] and old_section['type'] != 8,
             'section-owned relocation allocation identity changed')
        fragment = rust.payload(old_section)
        payload = partial.payload(new_section)
        need(bool(fragment), 'empty allocation cannot identify a section contribution')
        offset = payload.find(fragment)
        need(offset >= 0 and payload.find(fragment, offset + 1) == -1, 'Rust section contribution missing or ambiguous in partial')
        need(linked_target['value'] + linked_row['addend'] == offset + reference_target['value'] + reference_row['addend'],
             'anonymous allocation-relative relocation address changed')
        return dict(offset=reference_row['offset'], type=reference_row['type'], target_kind='exact_Rust_section_contribution',
                    section=old_section['name'], section_type=old_section['type'], section_flags=old_section['flags'],
                    Rust_contribution_sha256=hashlib.sha256(fragment).hexdigest(), contribution_offset_in_partial=offset,
                    address_within_Rust_contribution=reference_target['value'] + reference_row['addend'])
    name = reference_target['name']
    need(bool(name) and reference_target['bind'] == linked_target['bind'] == 1 and name == linked_target['name'], 'named relocation target/binding changed')
    if reference_target['shndx']:
        owner, owner_symbol, owner_role = rust, reference_target, 'exact_Source37_Rust_input'
        need(rows(rust,name) == [reference_target], 'reference named target is ambiguous')
    else:
        need(name == 'process_remaining_range_scheduler_debug', 'unreviewed undefined reference target')
        owner, owner_role = process, 'actual_selected_process_C_input'
        found = rows(owner,name)
        need(len(found) == 1, 'existing C debug provider not uniquely resolved')
        owner_symbol = found[0]
    found = rows(partial,name)
    need(found == [linked_target], 'partial named relocation uses a different section alias')
    need((linked_target['bind'],linked_target['type'],linked_target['size']) == (owner_symbol['bind'],owner_symbol['type'],owner_symbol['size']),
         'partial named symbol shape differs from exact input owner')
    old_section, new_section = owner.sections[owner_symbol['shndx']], partial.sections[linked_target['shndx']]
    need((old_section['name'],old_section['type'],old_section['flags']) == (new_section['name'],new_section['type'],new_section['flags']),
         'named target allocation identity changed')
    owner_bytes, linked_bytes = object_bytes(owner,owner_symbol), object_bytes(partial,linked_target)
    need(owner_bytes == linked_bytes and overlapping_aliases(owner,owner_symbol) == overlapping_aliases(partial,linked_target),
         'named target bytes or overlapping aliases changed')
    need(linked_row['addend'] == reference_row['addend'], 'named target-relative addend changed')
    return dict(offset=reference_row['offset'],type=reference_row['type'],target_kind='exact_named_input_owner',target=name,
                owner_role=owner_role,type_and_size=[owner_symbol['type'],owner_symbol['size']],addend=reference_row['addend'],
                owner_bytes_sha256=hashlib.sha256(owner_bytes).hexdigest(),aliases=overlapping_aliases(owner,owner_symbol))

def bind_partial_Rust_caller(caller):
    original, linked = function(rust,caller), function(partial,caller)
    old_section, new_section = rust.sections[original['shndx']], partial.sections[linked['shndx']]
    need((original['bind'],original['type'],original['size']) == (linked['bind'],linked['type'],linked['size']), 'Rust caller shape changed')
    need(old_section['name'] == new_section['name'] and old_section['flags'] == new_section['flags']
         and old_section['type'] == new_section['type'] and original['value'] == linked['value'] == 0
         and old_section['size'] == new_section['size'] == original['size'], 'exact standalone caller section extent changed')
    need(overlapping_aliases(rust,original) == overlapping_aliases(partial,linked) == [(caller,1,2,original['size'],0)], 'Rust caller gained or substituted an alias')
    code, linked_code = object_bytes(rust,original), object_bytes(partial,linked)
    need(code == linked_code, 'partial Rust caller bytes differ from exact accepted6e54 input')
    before, after = owning(rust,original), owning(partial,linked)
    need(all(row['owning_section'] == original['shndx'] for row in before)
         and all(row['owning_section'] == linked['shndx'] for row in after), 'foreign section relocation used as caller evidence')
    key = lambda row:(row['offset'],row['type'])
    need(len({key(row) for row in before}) == len(before) and len({key(row) for row in after}) == len(after)
         and len(before) == len(after), 'caller relocation membership ambiguous or changed')
    semantic = [semantic_relocation(left,right) for left,right in zip(sorted(before,key=key),sorted(after,key=key))]
    return dict(caller=caller,code_sha256=hashlib.sha256(code).hexdigest(),standalone_section=new_section['name'],
                aliases=overlapping_aliases(partial,linked),semantic_relocations=semantic), original, before, after

strict_named = {'destroy_thread':['process_destroy_thread_hash_detach_candidate_v3'],
                'sys_sched_setaffinity':['sched_setaffinity_retained_v2','sched_affinity_hold_warning_v2']}
need(contract['unchanged_strict_named_edges'] == strict_named, 'three direct named-edge contract changed')
expected_inline = {'find_thread':['process_find_thread_live_body_result_v2','process_try_hold_thread_live_v2'],
                   'process_destroy_thread_hash_detach_candidate_v3':['process_thread_hash_detach_live_body_v3'],
                   'sys_sched_getaffinity':['sched_getaffinity_retained_v2','sched_affinity_hold_warning_v2'],
                   'sched_do_migrate_public':['sched_do_migrate_mask_serialized_v3']}
need(set(contract['contracts']) == set(expected_inline), 'four exact inline caller set changed')
edge_proof = {}
for caller in list(expected_inline) + list(strict_named):
    binding, original, reference_relocations, linked_relocations = bind_partial_Rust_caller(caller)
    if caller in expected_inline:
        selected = contract['contracts'][caller]
        need(selected['inlined_callees'] == expected_inline[caller], 'inline callee contract changed')
        original_proof = check_inline(rust,original,reference_relocations,selected,object_bytes)
        need(original_proof == accepted_ownership['production_consumer_edges'][caller], 'accepted source37 machine ownership proof changed')
        need(not set(expected_inline[caller]) & {row['target']['name'] for row in linked_relocations}, 'partial inline absence changed without exact proof')
        binding['accepted_machine_proof'] = original_proof
    else:
        names = {row['target']['name'] for row in linked_relocations}
        need(set(strict_named[caller]) <= names, 'actual direct named edge missing: ' + caller)
        binding['strict_named_edges'] = strict_named[caller]
    edge_proof[caller] = binding

# A single changed header adds a prototype only. All consumed headers must still
# match the exact selected HOST profile, with this one explicit overlay.
allowed = {row['path']:row for row in recipe['pinned_inputs']}
dependencies = {}
for unit in ('process','syscall'):
    text = (out / (unit + '.selected.d')).read_text().replace(chr(92) + chr(10), ' ')
    need(':' in text, 'compiler dependency file missing')
    paths = shlex.split(text.split(':',1)[1])
    need(paths, 'empty actual C dependency set')
    for value in paths:
        need(value in allowed, 'unbound actual C source/header dependency: ' + value)
        auth(allowed[value])
    dependencies[unit] = paths
for row in recipe['pinned_inputs']:
    auth(row)
C_debt = {name: sorted(row['name'] for row in elf.symbols if row['name'] and row['bind'] == 1 and row['type'] == 2 and row['shndx'] != 0) for name,elf in [('changed_process',process),('changed_syscall',syscall)]}
result = dict(scope=recipe['scope'],status='PASS_SOURCE38_SELECTED_C_ABI_AND_COHERENT_PARTIAL_OWNERSHIP_ONLY',providers=providers,production_consumer_edges=edge_proof,shared_data=data,remaining_unresolved=sorted(undefined(partial)),remaining_unresolved_count=len(undefined(partial)),existing_C_runtime_function_debt=C_debt,actual_dependencies=dependencies,compiler_profile='Reviewed HOST GCC9 selected-C profile; distinct from Docker default GCC14.',unchanged_CPU_VM_reused=True,ASM_recompiled=False,whole_Rust_recompiled=False,C_runtime_body_expansion=False,default_image=False,native=False,Process_VM_lifetimes_and_whole_C_retirement='OPEN')
with (ROOT/'ACTUAL-SOURCE38-SELECTED-C-PARTIAL-OWNERSHIP.json').open('x') as stream:
    json.dump(result,stream,indent=2)
    stream.write('\n')
print(json.dumps(dict(status=result['status'],new_Rust_providers=len(providers),production_caller_rows=len(edge_proof),shared_data_sizes={name:row['size'] for name,row in data.items()},remaining_unresolved=result['remaining_unresolved'],default_image=False,native=False),sort_keys=True))
