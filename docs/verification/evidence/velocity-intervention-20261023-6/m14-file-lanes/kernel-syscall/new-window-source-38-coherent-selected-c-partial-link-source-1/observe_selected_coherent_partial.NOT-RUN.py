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
edges = {'find_thread':['process_find_thread_live_body_result_v2','process_try_hold_thread_live_v2'], 'destroy_thread':['process_destroy_thread_hash_detach_candidate_v3'], 'process_destroy_thread_hash_detach_candidate_v3':['process_thread_hash_detach_live_body_v3'], 'sys_sched_getaffinity':['sched_getaffinity_retained_v2','sched_affinity_hold_warning_v2'], 'sys_sched_setaffinity':['sched_setaffinity_retained_v2','sched_affinity_hold_warning_v2'], 'sched_do_migrate_public':['sched_do_migrate_mask_serialized_v3']}
edge_proof = {}
for caller, callees in edges.items():
    relas = owning(partial,function(partial,caller))
    names = {row['target']['name'] for row in relas}
    need(set(callees) <= names, 'actual selected production consumer edge missing: ' + caller)
    edge_proof[caller] = [row for row in relas if row['target']['name'] in callees]
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
