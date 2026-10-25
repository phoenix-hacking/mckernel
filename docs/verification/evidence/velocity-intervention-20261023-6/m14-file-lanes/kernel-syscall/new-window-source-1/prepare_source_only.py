"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read and prepare exact private source replacements; no compiler or runtime invocation.
"""
from pathlib import Path
import difflib
import hashlib
import json
import re

D = Path(__file__).resolve().parent
R = Path('/home/holden/mckernel')
SCOPE = 'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'

def pin(path):
    raw = path.read_bytes()
    return {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}

def put(name, data):
    with (D / name).open('x') as stream:
        stream.write(data)
    return pin(D / name)

base = R / 'kernel/syscall.c'
original = base.read_text()
private = original
replacements = []
for name, args in [
    ('syscall_swapout_log_bridge', 'const void *fname, void *buf, size_t size, int flag'),
    ('syscall_linux_mlock_log_bridge', 'unsigned long addr, unsigned long len'),
]:
    pattern = r'void\n' + name + r'\(' + re.escape(args) + r'\)\n\{[^{}]*\n\}'
    matches = list(re.finditer(pattern, original))
    if len(matches) != 1:
        raise RuntimeError('Exact single original body required: ' + name)
    body = matches[0].group()
    prefix = '#ifdef MCKERNEL_RUST_F03_IO_DIAGNOSTICS\n'
    if name == 'syscall_swapout_log_bridge':
        line = original[:matches[0].start() + body.index('dkprintf(')].count('\n') + 1
        prefix += (
            'struct ddebug __attribute__((aligned(8),section("__verbose"))) '
            'f03_swapout_callback_debug_v1 = {\n'
            ' .file=__FILE__, .func="syscall_swapout_log_bridge", '
            '.line=' + str(line) + ', .flags=DDEBUG_DEFAULT\n};\n'
        )
    replacement = (prefix + 'extern void ' + name + '(' + args + ');\n#else\n'
                   + body + '\n#endif /* MCKERNEL_RUST_F03_IO_DIAGNOSTICS */')
    private = private.replace(body, replacement, 1)
    replacements.append({'symbol': name, 'original': body, 'replacement': replacement})

put('syscall.PRIVATE-IO-DIAGNOSTICS.c', private)
put('ACTUAL-ORIGINAL-C.inc', '\n\n'.join(row['original'] for row in replacements) + '\n')
put('EXACT-GUARDED-REPLACEMENTS.json', json.dumps(replacements, indent=2) + '\n')
put('EXACT-IO-DIAGNOSTIC-CLOSURES.patch', ''.join(difflib.unified_diff(
    original.splitlines(keepends=True), private.splitlines(keepends=True),
    fromfile='a/kernel/syscall.c', tofile='b/kernel/syscall.c')))
put('REAL-HEADER-ABI-WITNESS.c.inc', '''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
_Static_assert(__builtin_types_compatible_p(__typeof__(&syscall_swapout_log_bridge),void (*)(const void *,void *,size_t,int)),"swapout callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&syscall_linux_mlock_log_bridge),void (*)(unsigned long,unsigned long)),"mlock callback ABI");
_Static_assert(sizeof(size_t)==sizeof(unsigned long),"size_t formatter slot");
_Static_assert(sizeof(long)==8,"signed long formatter slot");
_Static_assert(sizeof(struct ddebug)==32,"actual debug record size");
_Static_assert(__alignof__(struct ddebug)==8,"actual debug alignment");
_Static_assert(__builtin_offsetof(struct ddebug,file)==0,"actual debug file offset");
_Static_assert(__builtin_offsetof(struct ddebug,func)==8,"actual debug function offset");
_Static_assert(__builtin_offsetof(struct ddebug,fmt)==16,"actual debug format offset");
''')
manifest = {
    'scope': SCOPE,
    'status': 'TWO_LIVE_IO_DIAGNOSTIC_BODIES_SOURCE_PREPARED_UNCOMPILED',
    'base_C': pin(base),
    'base_policy': pin(R / 'kernel/rust/syscall_policy.rs'),
    'actual_debug_header': pin(R / 'lib/include/ihk/debug.h'),
    'actual_debug_Rust': pin(R / 'kernel/rust/debug.rs'),
    'outputs': [pin(path) for path in sorted(D.iterdir()) if path.is_file()],
    'C_selector': 'MCKERNEL_RUST_F03_IO_DIAGNOSTICS',
    'Rust_cfg': 'f03_io_diagnostic_callbacks_candidate',
    'unchanged_genuine_callers': ['sys_swapout -> syscall_swapout_log_bridge -> swapout_body_result',
                                 'sys_linux_mlock -> syscall_linux_mlock_log_bridge -> linux_mlock_body_result'],
    'actual_bodies': ['conditional flags read / CPU lookup / exact swapout formatter',
                      'unconditional address and signed-length Linux-mlock formatter'],
    'new_C_compute': False,
    'C_data_only': 'one actual lexical aligned __verbose ddebug datum; fmt remains null',
    'canonical_edits': False,
    'compiler_jobs': 0,
    'actual_result': None,
    'root_execution_grant': None,
    'native': False,
    'default_selected': False,
    'whole_file_retired': False,
    'excluded': ['service-held fork/ACK work', 'other candidate activation', 'pointer dereferences'],
    'next_executable_check': 'After actual coordinator clearance/grant: real-header ABI witness; full selected/fallback C TU; genuine Rust caller/export partial link; controlled original-C/Rust formatter equivalence.',
    'vectors': ['debug flags0 suppresses CPU lookup/output; flags1 and128 emit exactly once',
                'flag0,-1,INT_MIN,INT_MAX retain signed long output',
                'address0/high-bit/all-bits and length0,LONG_MAX,LONG_MAX+1,ULONG_MAX',
                'unchanged body-call sequence and untouched pointer values'],
    'holds': ['Original dynamic-debug flags synchronization and genuine formatter provider qualification remain open.',
              'No behavior/build/link/native acceptance or whole-operation closure claimed.'],
    'downstream_unlock': 'Retires two existing C diagnostic callback implementations after actual consumer qualification; helps whole syscall.c closure without duplicating whole transactions.',
}
put('SOURCE-HANDOFF.HOLD.json', json.dumps(manifest, indent=2, sort_keys=True) + '\n')
print(json.dumps(pin(D / 'SOURCE-HANDOFF.HOLD.json'), sort_keys=True))
