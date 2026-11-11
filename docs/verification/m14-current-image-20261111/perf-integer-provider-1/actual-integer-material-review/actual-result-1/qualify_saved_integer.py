#!/usr/bin/env python3
"""Pure stdlib qualification of already saved integer-provider bytes; runs no tools."""
import collections
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import struct

M = Path('/home/holden/mckernel-work/m14-blocker-resolution-20261110')
H = M / 'perf-freestanding-panic-provider-sdk-max-1/integer-builtins-1'
OUT = H / 'output-1'
Q = Path(__file__).parent


def sha(b):
    return hashlib.sha256(b).hexdigest()


def ref(p):
    p = Path(p)
    b = p.read_bytes()
    return {'path': str(p), 'bytes': len(b), 'sha256': sha(b)}


def save(name, data):
    p = Q / name
    b = (json.dumps(data, sort_keys=True, indent=2) + '\n').encode()
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(b)
        f.flush()
        os.fsync(f.fileno())
    return ref(p)


result = json.loads((H / 'execution-1/RESULT.json').read_text())
request = json.loads((H / 'REQUEST.json').read_text())
contract = json.loads((H / 'INTEGER-SOURCE-CONTRACT.json').read_text())
assert result['request_sha256'] == ref(H / 'REQUEST.json')['sha256']
assert result['core_metadata_sha256'] == request['core_metadata_input']['sha256']
assert result['all_waits_streams_joined'] and result['remaining_owned_children'] == []
assert len(result['phases']) == 1 and result['phases'][0]['exit'] == 0
artifact_refs = []
for r in result['actual_artifacts']:
    p = Path(r['path'])
    a = ref(p)
    assert a == {k: r[k] for k in ['path', 'bytes', 'sha256']}
    artifact_refs.append(a)
assert len(artifact_refs) == 6
b = (OUT / 'compiler_builtins.o').read_bytes()
e = struct.unpack_from('<16sHHIQQQIHHHHHH', b)
assert e[0][:7] == b'\x7fELF\x02\x01\x01'
assert (e[1], e[2], e[10], e[11]) == (1, 62, 0, 64)
raw_sh = [struct.unpack_from('<IIQQQQIIQQ', b, e[6] + i * e[11]) for i in range(e[12])]
shstr = b[raw_sh[e[13]][4]:raw_sh[e[13]][4] + raw_sh[e[13]][5]]


def cstr(data, off):
    return data[off:data.index(b'\0', off)].decode('ascii')


secs = []
for i, s in enumerate(raw_sh):
    secs.append(dict(zip(['index', 'name', 'type', 'flags', 'address', 'offset', 'size', 'link', 'info', 'align', 'entsize'],
                         [i, cstr(shstr, s[0]), *s[1:]])))
sec_by_name = {s['name']: s for s in secs}
symtabs = {}
symbols = []
for s in secs:
    if s['type'] != 2:
        continue
    st = secs[s['link']]
    strings = b[st['offset']:st['offset'] + st['size']]
    table = []
    for off in range(s['offset'], s['offset'] + s['size'], s['entsize']):
        name, info, other, ndx, value, size = struct.unpack_from('<IBBHQQ', b, off)
        row = {'index': len(table), 'name': cstr(strings, name), 'bind': info >> 4,
               'type': info & 15, 'visibility': other & 3, 'section_index': ndx,
               'value': value, 'size': size}
        table.append(row)
    symtabs[s['index']] = table
    symbols.extend(table)
assert len(symtabs) == 1
binds = {0: 'LOCAL', 1: 'GLOBAL', 2: 'WEAK'}
types = {0: 'NOTYPE', 1: 'OBJECT', 2: 'FUNC', 3: 'SECTION', 4: 'FILE'}
vis = {0: 'DEFAULT', 1: 'INTERNAL', 2: 'HIDDEN', 3: 'PROTECTED'}
raw_symbols = {}
raw_text = (OUT / 'builtins-symbols-relocations.stdout').read_text()
for line in raw_text.splitlines():
    m = re.match(r'^\s*(\d+):\s+([0-9a-f]+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*(.*)$', line)
    if m:
        raw_symbols[int(m[1])] = (int(m[2], 16), int(m[3]), m[4], m[5], m[6], m[7], m[8])
assert len(raw_symbols) == len(symbols)
for s in symbols:
    ndx = 'UND' if s['section_index'] == 0 else 'ABS' if s['section_index'] == 0xfff1 else str(s['section_index'])
    name = secs[s['section_index']]['name'] if s['type'] == 3 else s['name']
    assert raw_symbols[s['index']] == (s['value'], s['size'], types[s['type']], binds[s['bind']], vis[s['visibility']], ndx, name)
relocs = []
for s in secs:
    if s['type'] != 4:
        continue
    for off in range(s['offset'], s['offset'] + s['size'], s['entsize']):
        offset, info, addend = struct.unpack_from('<QQq', b, off)
        target = symtabs[s['link']][info >> 32]
        name = secs[target['section_index']]['name'] if target['type'] == 3 else target['name']
        relocs.append({'relocation_section': s['name'], 'section': secs[s['info']]['name'],
                       'offset': offset, 'info': info, 'type': info & 0xffffffff,
                       'symbol': name, 'symbol_section_index': target['section_index'], 'addend': addend})
raw_relocs = []
current = None
for line in raw_text.splitlines():
    m = re.match(r"Relocation section '([^']+)'", line)
    if m:
        current = m[1]
    m = re.match(r'^([0-9a-f]{16})\s+([0-9a-f]{16})\s+(R_X86_64_\S+)\s+', line)
    if m:
        raw_relocs.append((current, int(m[1], 16), int(m[2], 16)))
assert raw_relocs == [(r['relocation_section'], r['offset'], r['info']) for r in relocs]
exec_secs = [s for s in secs if s['flags'] & 4 and s['size']]
disasm = (OUT / 'builtins-disassembly.stdout').read_text()
instructions = collections.defaultdict(list)
hist = collections.Counter()
current = None
simd_or_fpu = []
privileged = []
bad_decode = []
for line in disasm.splitlines():
    m = re.match(r'Disassembly of section (.+):$', line)
    if m:
        current = m[1]
        continue
    m = re.match(r'^\s*([0-9a-f]+):\s*((?:[0-9a-f]{2}(?:\s+|$))+)(.*)$', line)
    if not m:
        continue
    offset = int(m[1], 16)
    code = bytes.fromhex(m[2])
    text = m[3].split('\t')[0].strip()
    assert current in sec_by_name and text
    s = sec_by_name[current]
    assert code == b[s['offset'] + offset:s['offset'] + offset + len(code)]
    instructions[current].append((offset, len(code)))
    mnemonic = text.split()[0]
    hist[mnemonic] += 1
    if re.search(r'%(?:[xyz]mm\d+|mm[0-7]|st(?:\(\d\))?|k[0-7])\b', text) or re.match(r'^(?:f[a-z]|v[a-z]|[xfls](?:rstor|save)|ldmxcsr|stmxcsr|emms|femms)', mnemonic):
        simd_or_fpu.append({'section': current, 'offset': offset, 'instruction': text})
    if mnemonic in {'cli', 'sti', 'hlt', 'rdmsr', 'wrmsr', 'in', 'inb', 'inw', 'inl', 'out', 'outb', 'outw', 'outl', 'invlpg', 'syscall', 'sysenter', 'iret', 'iretq', 'swapgs', 'lgdt', 'lidt', 'lldt', 'ltr'} or re.search(r'%(?:cr[0-9]+|dr[0-9]+)\b', text):
        privileged.append({'section': current, 'offset': offset, 'instruction': text})
    if any(x in text for x in ['(bad)', '(unknown)', '.byte', '.word']):
        bad_decode.append({'section': current, 'offset': offset, 'instruction': text})
assert set(instructions) == {s['name'] for s in exec_secs}
for s in exec_secs:
    cursor = 0
    for offset, length in instructions[s['name']]:
        assert offset == cursor
        cursor += length
    assert cursor == s['size']
assert not simd_or_fpu and not privileged and not bad_decode
undefined = [s for s in symbols if s['section_index'] == 0 and s['name']]
globals_ = [s for s in symbols if s['bind'] in (1, 2) and s['section_index'] != 0]
assert not undefined
assert len(globals_) == 18 and all(s['type'] == 2 and s['size'] > 0 and s['visibility'] == 2 for s in globals_)
expected = {'__udivsi3', '__umodsi3', '__udivmodsi4', '__udivdi3', '__umoddi3', '__udivmoddi4', '__udivti3', '__umodti3', '__udivmodti4'}
assert {s['name'] for s in globals_ if s['bind'] == 2} == expected
code_relocs = [r for r in relocs if sec_by_name[r['section']]['flags'] & 4]
assert len(code_relocs) == 6 and all(r['type'] == 1 and r['addend'] == 0 and r['symbol_section_index'] == 3 for r in code_relocs)
exports = []
for s in globals_:
    sec = secs[s['section_index']]
    code = b[sec['offset'] + s['value']:sec['offset'] + s['value'] + s['size']]
    exports.append(dict(s, binding=binds[s['bind']], visibility_name=vis[s['visibility']], section=sec['name'], code_sha256=sha(code), relocations=[r for r in code_relocs if r['section'] == sec['name']]))
deps = []
for line in (OUT / 'compiler_builtins.raw.d').read_text().splitlines():
    if ': ' in line:
        target, rest = line.split(': ', 1)
        deps.append((target, shlex.split(rest)))
assert len(deps) == 2 and deps[0][1] == deps[1][1]
expected_deps = {'/producer/compiler_builtins_integer.rs', '/core-output/libcore.rmeta'} | {r['path'] for r in contract['unchanged_source_closure'].values()}
assert len(deps[0][1]) == len(expected_deps) == 10 and set(deps[0][1]) == expected_deps
no_allocated_data = [s['name'] for s in secs if s['flags'] & 2 and not s['flags'] & 4 and s['size']]
assert not no_allocated_data
eh_tls = [s['name'] for s in secs if s['name'].startswith(('.eh_frame', '.gcc_except', '.tdata', '.tbss'))]
assert not eh_tls
provider = save('ELF-PROVIDERS-IMPORTS.json', {
    'object': ref(OUT / 'compiler_builtins.o'), 'elf64_little_endian_ET_REL_machine62': True,
    'section_count': len(secs), 'symbol_count': len(symbols), 'raw_symbol_rows_match_all': True,
    'raw_relocation_rows_match_all': True, 'relocation_count': len(relocs),
    'defined_global_functions': exports, 'undefined_symbols': undefined,
    'compiler_builtins_crate_identity': 'Cs2uLDHyDyFrz_17compiler_builtins',
    'code_relocations': code_relocs, 'allocated_nonexec_data_sections': no_allocated_data,
    'eh_or_tls_sections': eh_tls,
    'udivti3_source_ABI': 'Unchanged genuine upstream extern C (u128,u128)->u128; WEAK HIDDEN FUNC50 bytes. Saved code accepts four integer arg halves in RDI/RSI/RDX/RCX, passes original helper input with stack result, returns quotient halves in RAX/RDX. One R_X86_64_64 relocation at+0x16 resolves to genuine local u128_div_rem1018B. No hand-extern ABI or fabricated mangled name.',
    'domain': 'Source-grounded complete original nonzero u128 divisor domain. This saved-byte qualification executes no division and claims no runtime arithmetic tests.'
})
isa = save('ISA-SCAN.json', {
    'object': ref(OUT / 'compiler_builtins.o'), 'saved_disassembly': ref(OUT / 'builtins-disassembly.stdout'),
    'method': 'Every saved instruction byte matched corresponding ELF executable section; contiguous full-section coverage, no skipped code or bad decode. Integer/prefix mnemonic histogram plus SIMD/FPU/privileged register/instruction scan; no tool invocation.',
    'nonempty_executable_sections': len(exec_secs), 'executable_bytes': sum(s['size'] for s in exec_secs),
    'instructions': sum(hist.values()), 'mnemonic_histogram': dict(hist),
    'SIMD_MMX_x87_observations': simd_or_fpu, 'privileged_native_IO_observations': privileged,
    'bad_or_unknown_decode': bad_decode, 'all_executable_section_bytes_covered': True,
    'sections': [{'name': s['name'], 'size': s['size'], 'sha256': sha(b[s['offset']:s['offset'] + s['size']])} for s in exec_secs],
    'warning': ref(H / 'execution-1/builtins-build-payload.stderr'),
    'warning_disposition': 'One actual SSE2 target ABI warning retained, not waived; no universal floating ABI/new compiler/native claim.'
})
tuple_ref = save('INTEGER-BUILTINS-OUTPUT-TUPLE.json', {
    'request': ref(H / 'REQUEST.json'), 'actual_result': ref(H / 'execution-1/RESULT.json'),
    'full_Root_completion': ref(H / 'execution-1/ROOT-EXEC-COMPLETION.json'),
    'actual_artifacts': artifact_refs, 'core_metadata_input': request['core_metadata_input'],
    'depfile_object_and_metadata_lists_identical': True, 'depfile_exact_dependencies': deps[0][1],
    'compiler_builtins_metadata_seed': request['metadata_identity'],
    'actual_crate_identity': 'Cs2uLDHyDyFrz_17compiler_builtins',
    'new_kernel_consumer_must_use_this_actual_metadata_and_same7ec5core': True,
    'provider': provider, 'ISA': isa,
    'remaining_core_frontier_after_actual_udivti3_definition': [x for x in contract['actual_core_frontier']['six_strong_imports'] if x != '__udivti3'],
    'future_consumer_and_image_import_frontier': 'UNOBSERVED; every new actual required root remains an obligation.',
    'acceptance': 'Qualified emitted integer dependency only; no final link/image/native/original acceptance.'
})
qual = save('QUALIFICATION.json', {
    'schema': 1, 'at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'decision': 'GO', 'status': 'GO_ACTUAL_INTEGER_BUILTINS_PROVIDER_ISA_METADATA_AT_DEPENDENCY_SCOPE',
    'reviewer': '/root/public_abi_join_max; actual Sol/MAX',
    'material_source_GO': ref(Q.parent / 'REVIEW.json'),
    'actual_result': ref(H / 'execution-1/RESULT.json'), 'full_Root_completion': ref(H / 'execution-1/ROOT-EXEC-COMPLETION.json'),
    'tuple': tuple_ref, 'provider': provider, 'ISA': isa,
    'facts': {'ELF': 'ELF64LE ET_REL X86_64;45sections/47symbols, no program headers',
              'exports': 'Nine genuine WEAK HIDDEN unsigned C-ABI functions plus nine strong HIDDEN mangled source functions; all nonempty. Real __udivti3 is50B and its real u128_div_rem helper is1018B.',
              'imports': 'Zero named UND of any binding; all six code relocations resolve within this object to the local genuine helper.',
              'ISA': str(len(exec_secs)) + ' nonempty executable sections/' + str(sum(s['size'] for s in exec_secs)) + 'bytes/' + str(sum(hist.values())) + 'instructions, all saved bytes matched; no SIMD/MMX/x87/privileged/native-IO observations or EH/TLS.',
              'metadata': 'Actual new76400B metadata7068131f is paired with134528B object8cf38cfa. Exact7ec5 input is bound by actual compiler result/request and both identical10dependency lists (facade+8upstream+coremetadata). No old failed metadata adopted.'},
    'reused_core_material_ISA': ref(M / 'perf-freestanding-panic-provider-review-publicabi-max-1/first-core-compile-1/actual-result-1/QUALIFICATION.json'),
    'limits': ['SSE2 ABI warning retained and not waived.', 'No arithmetic execution/fatal test/whole consumer type+link/new image/native acceptance from this producer.', 'Five remaining real core memory/handler roots and any new consumer imports still require actual link/provider joins.', 'SourceAcq independently qualifies saved source-custody and current process retirement; this material review releases no resource or UNKNOWN hold.'],
    'effects': 'Pure saved-byte/ELF/text parser only. No compiler/readelf/objdump/helper/source/test/runtime/native/canonical replay or action.',
    'original_acceptance': False
})
print(json.dumps({'qualification': qual, 'tuple': tuple_ref, 'provider': provider, 'ISA': isa}, sort_keys=True))
