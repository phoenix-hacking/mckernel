"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Three exact selected26eb residuals, reusing existing private Rust bodies.
No compiler, canonical writes, provider implementation or new dispatch policy.
"""
import difflib
import hashlib
import json
from pathlib import Path

D = Path(__file__).resolve().parent
ROOT = Path('/home/holden/mckernel')
P = D.parent
E = P.parent
OLD = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-syscall')

def ref(p):
    b = p.read_bytes()
    return dict(path=str(p), bytes=len(b), sha256=hashlib.sha256(b).hexdigest())

def put(d, name, data):
    with (d / name).open('x') as f:
        f.write(data)

def rust_body(text, name):
    index = text.index('pub unsafe extern "C" fn ' + name + '(')
    begin = text.rfind('/// # Safety', 0, index)
    end = text.find('\n/// # Safety', index)
    return text[begin:end if end >= 0 else len(text)].rstrip() + '\n'

cursor_path = E / 'CURRENT26EB-SELECTED-F03-F06-REMAINING-SOURCE-CURSOR.json'
cursor = json.loads(cursor_path.read_text())
assert cursor['image'] == '26eb201a' and cursor['rows']['F06']['count'] == 31
assert ref(Path(cursor['rows']['F06']['object']['path'])) == cursor['rows']['F06']['object']
c_path = ROOT / 'arch/x86_64/kernel/syscall.c'
r_path = ROOT / 'kernel/rust/syscall_policy.rs'
c, policy = c_path.read_text(), r_path.read_text()
copy_fragment = OLD / 'next-usercopy-entry-bridges-source-1/candidate/syscall_policy.usercopy_entry_bridges.EXPLICIT-RESULT.FRAGMENT.rs'
forward_fragment = OLD / 'next-signal-runtime-adapters-source-1/candidate/syscall_policy.signal_runtime_adapters.FRAGMENT.rs'
assert ref(copy_fragment)['sha256'] == 'b2d73c99c9150de0a8afb5b040a08ebe32e9fb961da550bf9597c1a699458cb7'
assert ref(forward_fragment)['sha256'] == '8bdc144795df245cfbae5731880906bba50215b61dfc2df0468ff1f6321c0ad0'
plan_template = json.loads((P / 'next-process-vm-consumer-source-1/NEXT-ABI-FACTS-COMMAND.json').read_text())
rustc = Path('/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc')
leaves = [
    ('copy-to-user', 'arch_copy_to_user_bridge', copy_fragment, 'COPY_TO_USER'),
    ('copy-from-user', 'arch_copy_from_user_bridge', copy_fragment, 'COPY_FROM_USER'),
    ('forward-context', 'arch_syscall_forward_context_bridge', forward_fragment, 'FORWARD_CONTEXT'),
]
for label, symbol, fragment, gate in leaves:
    assert symbol in cursor['rows']['F06']['defined_FUNC_names']
    d = D / label
    d.mkdir()
    source = fragment.read_text()
    reused = rust_body(source, symbol)
    imports = ('use core::ffi::c_void;\nuse crate::abi::{CInt, CLong};\n\n'
               if gate == 'FORWARD_CONTEXT' else
               'use core::ffi::c_void;\nuse crate::abi::{CLong, CULong, SizeT};\n\n')
    leaf = '// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n' + imports + reused
    begin = c.index('\nlong\n' + symbol + '(')
    end = c.index('\n}\n', begin) + 3
    original = c[begin:end]
    signature = original[:original.index('\n{')].strip()
    condition = 'defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F06_' + gate + ')'
    wrapper = '\n#if ' + condition + '\nextern ' + signature + ';\n#else\n' + original + '\n#endif\n'
    selected_c = c[:begin] + wrapper + c[end:]
    cfg = 'f06_' + label.replace('-', '_') + '_candidate'
    selection = '\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(' + cfg + ')]\n#[path = "bridge.rs"]\nmod ' + cfg + ';\n'
    assert symbol not in policy
    put(d, 'bridge.rs', leaf)
    put(d, 'BASE.syscall.c', c)
    put(d, 'BASE.syscall_policy.rs', policy)
    put(d, 'syscall.c', selected_c)
    put(d, 'syscall_policy.rs', policy + selection)
    put(d, 'original-bridge.inc', original)
    for name, before, after in [('syscall.c', c, selected_c), ('syscall_policy.rs', policy, policy + selection)]:
        put(d, name + '.diff', ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile=name, tofile=name)))
    # Standalone fixture only: external effects resolve to a distinctive inert symbol.
    rust = '''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
#![no_std]
#![allow(dead_code)]
#[path = "abi.rs"] mod abi;
#[path = "bridge.rs"] mod bridge;
#[panic_handler] fn panic(_: &core::panic::PanicInfo<'_>) -> ! { loop {} }
'''
    if gate == 'FORWARD_CONTEXT':
        provider = 'syscall_generic_forwarding'
        rust += '''extern "C" {
    #[link_name = "fixture_provider"]
    fn syscall_generic_forwarding(number: abi::CInt, context: *mut abi::X86UserContext) -> abi::CLong;
}
'''
        c_proto = 'long fixture_provider(int, ihk_mc_user_context_t *);'
        public_proto = 'long ' + symbol + '(int, void *);'
        typedef = 'typedef long (*public_abi)(int, void *);'
        fixture = '''
static int calls, expected_number;
static unsigned long got_number, got_context;
static long response;
long fixture_provider(int number, ihk_mc_user_context_t *context)
{ calls++; got_number = (unsigned long)(long)number; got_context = (unsigned long)context; return response; }
int main(void)
{
    const int numbers[] = {0, -1, 0x7fffffff, (-0x7fffffff - 1)};
    const unsigned long pointers[] = {0, 1, 0x8000000000000000UL, ~0UL, 0x12345000UL};
    const long results[] = {0, 1, -1, (-0x7fffffffffffffffL - 1), 0x7fffffffffffffffL, -14, 0x123456789abcdefL};
    unsigned long cases = 0;
    for (unsigned long n = 0; n < 4; n++) for (unsigned long p = 0; p < 5; p++)
    for (unsigned long r = 0; r < 7; r++) {
        response = results[r];
        calls = 0;
        long old = original_bridge(numbers[n], (void *)pointers[p]);
        CHECK(calls == 1 && got_number == (unsigned long)(long)numbers[n] && got_context == pointers[p]);
        calls = 0;
        long now = TARGET(numbers[n], (void *)pointers[p]);
        CHECK(calls == 1 && got_number == (unsigned long)(long)numbers[n] && got_context == pointers[p]);
        CHECK(now == old && now == response);
        cases++;
    }
    CHECK(cases == 140);
    puts("PASS TARGET controlled forwarding pairs140");
    return 0;
}
'''
        expected = 'PASS ' + symbol + ' controlled forwarding pairs140\n'
        cases = 140
    else:
        provider = 'copy_to_user' if gate == 'COPY_TO_USER' else 'copy_from_user'
        rust += '''mod x86_memory_helpers {
    use core::ffi::c_void;
    use crate::abi::{CInt, SizeT};
    extern "C" {
        #[link_name = "fixture_provider"]
        pub fn PROVIDER(dst: *mut c_void, src: *const c_void, size: SizeT) -> CInt;
    }
}
'''.replace('PROVIDER', provider)
        c_proto = 'int fixture_provider(void *, const void *, size_t);'
        public_proto = ('long ' + symbol + '(unsigned long, const void *, size_t);'
                        if gate == 'COPY_TO_USER' else 'long ' + symbol + '(void *, unsigned long, size_t);')
        typedef = ('typedef long (*public_abi)(unsigned long, const void *, size_t);'
                   if gate == 'COPY_TO_USER' else 'typedef long (*public_abi)(void *, unsigned long, size_t);')
        fixture = '''
static int calls, response;
static unsigned long got_destination, got_source, got_bytes;
int fixture_provider(void *dst, const void *src, size_t size)
{ calls++; got_destination = (unsigned long)dst; got_source = (unsigned long)src; got_bytes = size; return response; }
int main(void)
{
    const unsigned long pointers[] = {0, 1, 0x8000000000000000UL, ~0UL, 0x12345000UL};
    const unsigned long lengths[] = {0, 1, 4096, ~0UL, 0x8000000000000000UL};
    const int results[] = {0, 1, -1, (-0x7fffffff - 1), 0x7fffffff, -14, 0x12345678};
    unsigned long cases = 0;
    for (unsigned long p = 0; p < 5; p++) for (unsigned long l = 0; l < 5; l++)
    for (unsigned long r = 0; r < 7; r++) {
        unsigned long dst = pointers[p], src = pointers[(p + 1) % 5];
        response = results[r]; calls = 0;
        long old = original_bridge(DEST, SOURCE, lengths[l]);
        CHECK(calls == 1 && got_destination == dst && got_source == src && got_bytes == lengths[l]);
        calls = 0;
        long now = TARGET(DEST, SOURCE, lengths[l]);
        CHECK(calls == 1 && got_destination == dst && got_source == src && got_bytes == lengths[l]);
        CHECK(now == old && now == (long)response);
        cases++;
    }
    CHECK(cases == 175);
    puts("PASS TARGET controlled usercopy pairs175");
    return 0;
}
'''
        fixture = fixture.replace('DEST', 'dst' if gate == 'COPY_TO_USER' else '(void *)dst')
        fixture = fixture.replace('SOURCE', '(const void *)src' if gate == 'COPY_TO_USER' else 'src')
        expected = 'PASS ' + symbol + ' controlled usercopy pairs175\n'
        cases = 175
    fixture = fixture.replace('TARGET', symbol)
    put(d, 'abi.rs', (ROOT / 'kernel/rust/abi.rs').read_text())
    put(d, 'fixture.rs', rust)
    # Genuine complete prologue and explicit memory.h provide the real copy ABI.
    prologue = c.split('\nvoid terminate_mcexec(int, int);', 1)[0] + '\n#include <memory.h>\n'
    fixture_c = (prologue + '\nextern void abort(void);\nextern int puts(const char *);\n'
        '#define CHECK(x) do { if (!(x)) abort(); } while (0)\n' + c_proto + '\n' +
        '#define ' + provider + ' fixture_provider\n#define ' + symbol + ' original_bridge\n' +
        '#include "original-bridge.inc"\n#undef ' + symbol + '\n#undef ' + provider + '\n' +
        public_proto + '\n' + typedef + '\n_Static_assert(__builtin_types_compatible_p(__typeof__(&' +
        symbol + '), public_abi), "genuine public ABI");\n' + fixture)
    put(d, 'fixture.c', fixture_c)
    out = d / 'future-output-1'
    gcc = list(plan_template['argv'])
    gcc[gcc.index('-o') + 1] = str(out / 'driver')
    i = gcc.index('-c')
    gcc[i:i + 2] = ['-no-pie', str(d / 'fixture.c'), str(out / 'libfixture.a')]
    commands = [[str(rustc), '--edition=2021', '--crate-type', 'staticlib', '--crate-name',
                 'f06_' + label.replace('-', '_'), '-C', 'panic=abort', '-C', 'opt-level=1',
                 '-C', 'code-model=large', '-C', 'relocation-model=static', str(d / 'fixture.rs'),
                 '-o', str(out / 'libfixture.a')], gcc, [str(out / 'driver')]]
    binding = dict(symbol=symbol, selected_cursor=ref(cursor_path), selected_object=cursor['rows']['F06']['object'],
        canonical_before=[ref(c_path), ref(r_path)], reused_fragment=ref(fragment),
        reused_exact_body_sha256=hashlib.sha256(reused.encode()).hexdigest(),
        original_C=original, C_wrapper=wrapper, rust_selection=selection,
        selectors=dict(C='MCKERNEL_RUST_F06_' + gate, Rust=cfg),
        real_provider=provider, provider_source=ref(ROOT / ('kernel/rust/syscall_policy.rs'
            if gate == 'FORWARD_CONTEXT' else 'kernel/rust/x86_memory_helpers.rs')))
    put(d, 'SOURCE-BINDINGS.json', json.dumps(binding, indent=2) + '\n')
    plan = dict(status='SOURCE_ONLY_ROOT_GRANT_REQUIRED', scope=__doc__,
        purpose='Functional selected C/Rust adapter ABI parity at one controlled external provider; no actual usercopy or kernel dispatch.',
        symbol=symbol, expected_cases=cases, expected_stdout=expected, commands=commands,
        fresh_output=str(out), cwd=str(d), limits=plan_template['limits'],
        tools=[ref(Path('/usr/bin/gcc-9')), ref(rustc)],
        inputs=[ref(q) for q in sorted(d.iterdir()) if q.is_file()],
        genuine_configuration=ref(P / 'GENUINE-NOCACHE-CONFIGURATION.json'),
        admission='Reviewed e8b84de3.admission()/04b5/adf, actual fixed cutoffs and resource floors; fresh Root grant required.',
        actual_compile=None, actual_runtime=None,
        holds=['real usercopy/fault fixups', 'real forwarding/kernel context lifetime', 'default link/native selection'])
    put(d, 'FUTURE-HOST-COMMAND-PLAN.json', json.dumps(plan, indent=2) + '\n')
    print(json.dumps(dict(symbol=symbol, module=ref(d / 'bridge.rs'), plan=ref(d / 'FUTURE-HOST-COMMAND-PLAN.json'))))
