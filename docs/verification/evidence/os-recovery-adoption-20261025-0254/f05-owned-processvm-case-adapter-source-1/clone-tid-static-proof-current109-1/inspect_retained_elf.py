"""Functional OS read-only ELF binding inspection; no workload execution."""
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254')
BUILD = ROOT / 'ROOT-CURRENT109-NEXT-DEFAULT-BUILD-ADMISSION-1/OUTPUT/work/output/build'
OUT = Path(__file__).resolve().parent

class Elf:
    def __init__(self, path):
        self.path = path
        self.data = path.read_bytes()
        assert self.data[:6] == b'\x7fELF\x02\x01'
        h = struct.unpack_from('<16sHHIQQQIHHHHHH', self.data)
        self.kind = h[1]
        self.sections = [struct.unpack_from('<IIQQQQIIQQ', self.data, h[6] + i*h[11]) for i in range(h[12])]
        self.symtabs = {}
        self.symbols = []
        for i,s in enumerate(self.sections):
            if s[1] != 2:
                continue
            st = self.sections[s[6]]
            strings = self.data[st[4]:st[4]+st[5]]
            syms = []
            for pos in range(s[4], s[4]+s[5], s[9]):
                v = struct.unpack_from('<IBBHQQ', self.data, pos)
                name = strings[v[0]:].split(b'\0', 1)[0].decode()
                syms.append({'name':name, 'section':v[3], 'value':v[4], 'size':v[5]})
            self.symtabs[i] = syms
            self.symbols.extend(syms)

    def symbol(self, name):
        found = [s for s in self.symbols if s['name'] == name and s['section'] != 0]
        assert len(found) == 1, (name, len(found))
        return found[0]

    def body(self, sym):
        sec = self.sections[sym['section']]
        start = sec[4] + sym['value'] - sec[3]
        return self.data[start:start+sym['size']]

    def relocations(self, sym):
        result = []
        for sec in self.sections:
            if sec[1] != 4 or sec[7] != sym['section']:
                continue
            for pos in range(sec[4], sec[4]+sec[5], sec[9]):
                offset, info, addend = struct.unpack_from('<QQq', self.data, pos)
                if sym['value'] <= offset < sym['value']+sym['size']:
                    target = self.symtabs[sec[6]][info >> 32]
                    result.append({'offset':offset-sym['value'], 'type':info & 0xffffffff,
                                   'symbol':target['name'], 'symbol_section':target['section'],
                                   'symbol_value':target['value'], 'addend':addend})
        return result

image = Elf(BUILD / 'kernel/mckernel.img')
rust = Elf(BUILD / 'kernel/rust/mckernel_rust.o')
caller = Elf(BUILD / 'kernel/CMakeFiles/mckernel.img.dir/syscall.c.o')
results = []
for name in ['write_process_vm','read_process_vm','patch_process_vm','clone_child_tid_store_needed_result',
             'f03_ptrace_peektext_v1','f03_ptrace_poketext_v1','sys_clone','sys_ptrace']:
    objsym = rust.symbol(name)
    finalsym = image.symbol(name)
    patched = bytearray(rust.body(objsym))
    relocs = rust.relocations(objsym)
    for rel in relocs:
        assert rel['type'] == 1, rel  # R_X86_64_64 only; no generic unresolved tolerance.
        resolved_name = rel['symbol']
        if not resolved_name:
            aliases = [s for s in rust.symbols if s['section'] == rel['symbol_section']
                       and s['value'] == rel['symbol_value'] and s['name'] and s['size']]
            if len(aliases) == 1:
                resolved_name = aliases[0]['name']
                rel['resolved_section_symbol_name'] = resolved_name
        if resolved_name:
            target = image.symbol(resolved_name)
            value = (target['value'] + rel['addend']) & ((1 << 64)-1)
        else:
            # GNU ld may merge anonymous C strings. Positively compare the full
            # source string at the real final pointer; never ignore that operand.
            source_sec = rust.sections[rel['symbol_section']]
            assert source_sec[2] & 2 and not source_sec[2] & 1 and not source_sec[2] & 4
            begin = source_sec[4] + rel['symbol_value'] + rel['addend']
            end = rust.data.index(b'\0', begin, source_sec[4]+source_sec[5])+1
            literal = rust.data[begin:end]
            assert len(literal) > 1
            value = struct.unpack_from('<Q', image.body(finalsym), rel['offset'])[0]
            matches = [s for s in image.sections if s[2] & 2 and s[3] <= value < s[3]+s[5]]
            assert len(matches) == 1
            dest = matches[0]
            fileoff = dest[4]+value-dest[3]
            assert image.data[fileoff:fileoff+len(literal)] == literal
            rel['exact_anonymous_C_string_hex'] = literal.hex()
        struct.pack_into('<Q', patched, rel['offset'], value)
        rel['resolved_final_value'] = hex(value)
    final = image.body(finalsym)
    results.append({'symbol':name, 'size':objsym['size'], 'image_address':hex(finalsym['value']),
                    'exact_final_bytes_equal_after_all_relocations':bytes(patched) == final,
                    'relocations':relocs})
    assert bytes(patched) == final, name

do_fork = caller.symbol('do_fork')
final_do_fork = image.symbol('do_fork')
cb, fb = caller.body(do_fork), image.body(final_do_fork)
relevant = []
for rel in caller.relocations(do_fork):
    if rel['symbol'] not in ['write_process_vm','clone_child_tid_store_needed_result']:
        continue
    assert rel['type'] == 1
    target = image.symbol(rel['symbol'])
    observed = struct.unpack_from('<Q', fb, rel['offset'])[0]
    expected = (target['value']+rel['addend']) & ((1<<64)-1)
    assert observed == expected
    # Both operands are movabs imm64 into RAX, followed by call *RAX.
    assert cb[rel['offset']-2:rel['offset']] == b'\x48\xb8'
    call_at = rel['offset']+8
    # clone predicate loads EDI after movabs; write call is immediate.
    if rel['symbol'] == 'write_process_vm':
        assert cb[call_at:call_at+2] == fb[call_at:call_at+2] == b'\xff\xd0'
    relevant.append({**rel, 'final_value':hex(observed), 'final_operand_address':hex(final_do_fork['value']+rel['offset'])})
assert {r['symbol'] for r in relevant} == {'write_process_vm','clone_child_tid_store_needed_result'}
ops = caller.symbol('f03_ptrace_entry_ops_v1')
final_ops = image.symbol('f03_ptrace_entry_ops_v1')
ops_bindings = []
for rel in caller.relocations(ops):
    if rel['symbol'] not in ['f03_ptrace_peektext_v1','f03_ptrace_poketext_v1']:
        continue
    assert rel['type'] == 1
    value = struct.unpack_from('<Q', image.body(final_ops), rel['offset'])[0]
    assert value == image.symbol(rel['symbol'])['value'] + rel['addend']
    ops_bindings.append({**rel, 'final_value':hex(value)})
assert len(ops_bindings) == 2
refs = []
for e in [image,rust,caller]:
    refs.append({'path':str(e.path), 'size':len(e.data), 'sha256':hashlib.sha256(e.data).hexdigest()})
assert refs[0]['sha256'] == 'e87f5155eb82c13ab268e8a35fb13bf1560ffd5a5f97c8fd2af78f0281fc3d78'
record = {'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',
          'status':'PASS_READONLY_CURRENT109_STATIC_BINDING_NOT_NATIVE_ACCEPTANCE',
          'artifacts':refs, 'Rust_provider_bindings':results, 'do_fork_relevant_relocations':relevant,
          'ptrace_ops_peek_poke_relocations':ops_bindings}
(OUT/'ELF-BINDINGS.json').write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps({'status':record['status'], 'Rust_functions':len(results), 'caller_relocations':len(relevant)}))
