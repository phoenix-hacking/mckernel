"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One six-provider batch fixture preparation; source writes only, no compiler/test.
"""
from pathlib import Path
import copy, hashlib, json, re

P = Path(__file__).resolve().parent
B = P.parent
REPO = Path('/home/holden/mckernel')
PROD = B / 'combined-l2-l1-production-preparation-1/bounded-current-canonical-binding-correction-1'
CANDIDATE = B / 'next-memobj-flush-source-only-1/candidate'

def ref(path):
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))

def write(path, value):
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    raw = value.encode() if isinstance(value, str) else (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    with path.open('xb') as out:
        out.write(raw)
    return ref(path)

def body(text, signature):
    a = text.index(signature)
    end = text.index('{', a) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[a:end]

products = [ref(CANDIDATE / 'arch/x86_64/kernel/memory.c'), ref(CANDIDATE / 'kernel/rust/x86_memory_helpers.rs')]
assert products[0]['sha256'] == 'ceed123214cd293f5afefd21dd071e39aa824cf3424cc6355a841c1ae5467f39'
assert products[1]['sha256'] == '087240006b3f1b99c844c77c1c645118710bf34f53546637eb12d54215822092'
modules = ['abi', 'page_helpers', 'mem_helpers', 'object_helpers', 'llist', 'rbtree', 'string']
inputs = []
for name in modules:
    source = PROD / 'source/kernel/rust' / (name + '.rs')
    inputs.append(ref(source))
    write(P / 'rust' / (name + '.rs'), source.read_text())
write(P / 'rust/x86_memory_helpers.rs', Path(products[1]['path']).read_text())
debug = (PROD / 'source/kernel/rust/debug.rs').read_text()
debug_type = '#[repr(C)]\n' + body(debug, 'pub struct Ddebug {')
write(P / 'rust/actual-debug-type.inc', debug_type + '\n')
write(P / 'fixture.rs', '''#![no_std]
#![allow(dead_code)]
#[path="rust/abi.rs"] mod abi;
#[path="rust/page_helpers.rs"] mod page_helpers;
#[path="rust/llist.rs"] mod llist;
#[path="rust/rbtree.rs"] mod rbtree;
#[path="rust/string.rs"] mod string;
#[path="rust/mem_helpers.rs"] mod mem_helpers;
#[path="rust/object_helpers.rs"] mod object_helpers;
mod debug { include!("rust/actual-debug-type.inc"); }
// Unreachable boot hooks only; no tested accounting/dispatch body is replaced.
mod x86_setup { pub fn early_phase(_tag:u8) {} pub fn early_panic() { loop {} } }
#[path="rust/x86_memory_helpers.rs"] mod x86_memory_helpers;
#[no_mangle] pub extern "C" fn fixture_rusage_enabled()->i32 { cfg!(enable_rusage) as i32 }
#[no_mangle] pub extern "C" fn fixture_geometry(which:i32)->usize {
 match which {0=>core::mem::size_of::<mem_helpers::RusageGlobal>(),1=>core::mem::align_of::<mem_helpers::RusageGlobal>(),2=>core::mem::size_of::<abi::Memobj>(),3=>core::mem::size_of::<abi::MemobjOps>(),_=>0}
}
''')
header = REPO / 'arch/x86_64/kernel/include/arch-memory-helpers.h'
clear_types = (B / 'next-l1-source-1/observer-leaf-declaration-correction-1/fixture/actual-types-and-level-declaration.inc').read_text()
write(P / 'actual-clear-types.inc', clear_types)
c = (B / 'preimage/arch/x86_64/kernel/memory.c').read_text()
write(P / 'actual-clear-args.inc', body(c, 'struct clear_range_args {') + ';\n')
ihk = (REPO / 'ihk/linux/include/ihk/ihk_rusage.h').read_text()
geometry = ''.join(re.findall(r'^#define IHK_MAX_NUM_(?:NUMA_NODES|CPUS)\s+\d+\s*$', ihk, re.M))
geometry = '\n'.join(re.findall(r'^#define IHK_MAX_NUM_(?:NUMA_NODES|CPUS)\s+\d+\s*$', ihk, re.M)) + '\n'
geometry += body(ihk, 'enum ihk_os_pgsize {') + ';\n'
usage = (REPO / 'kernel/include/rusage.h').read_text()
geometry += body(usage, 'struct rusage_percpu {') + ';\n' + body(usage, 'struct rusage_global {') + ';\n'
atomic = (REPO / 'arch/x86_64/kernel/include/ihk/atomic.h').read_text()
a = atomic.index('typedef struct {')
atomic_decl = atomic[a:atomic.index('} ihk_atomic_t;', a) + len('} ihk_atomic_t;')]
memobj = (REPO / 'kernel/include/memobj.h').read_text()
memobj_start = memobj.index('struct memobj {')
memobj_end = memobj.index('};', memobj.index('struct memobj_ops {')) + 2
mm = (REPO / 'lib/include/ihk/mm.h').read_text()
table_decl = re.search(r'^typedef void \*page_table_t;$', mm, re.M).group()
geometry += '\nstruct page;\n' + table_decl + '\n' + atomic_decl + '\n' + memobj[memobj_start:memobj_end] + '\n'
write(P / 'actual-object-accounting-types.inc', geometry)
renames = {'x86_clear_memobj_flush_bridge': 'original_memobj_flush', 'x86_clear_rss_sub_bridge': 'original_rss', 'x86_clear_memobj_rss_sub_bridge': 'original_memobj_rss', 'clear_range_l1': 'original_clear_range_l1', 'clear_range_l2': 'original_clear_range_l2', 'clear_range_l3': 'original_clear_range_l3'}
oracles = []
for name in ['x86_clear_memobj_flush_bridge', 'x86_clear_rss_sub_bridge', 'x86_clear_memobj_rss_sub_bridge', 'clear_range_l1', 'clear_range_l2', 'clear_range_l3']:
    signature = ('static int ' if name.startswith('clear_range') else 'static void ') + name + '('
    actual = body(c, signature)
    for old, new in renames.items():
        actual = re.sub(r'\b' + old + r'\b', new, actual)
    oracles.append(actual)
for level in [1,2,3]:
    actual = body(c, 'static int x86_clear_range_walk_l' + str(level) + '_bridge(')
    actual = actual.replace('x86_clear_range_walk_l' + str(level) + '_bridge', 'original_walk_l' + str(level), 1)
    actual = actual.replace('&clear_range_l' + str(level), '&original_clear_range_l' + str(level))
    oracles.append(actual)
write(P / 'original-providers-and-callbacks.inc', '\n\n'.join(oracles) + '\n')
abi = '''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "''' + products[0]['path'] + '''"
#include <rusage_private.h>
'''
for level in [1,2,3]:
    abi += '_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_walk_l' + str(level) + '_bridge),int(*)(void*,unsigned long,unsigned long,unsigned long,void*)),"complete walker ABI");\n'
abi += '''_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_rss_sub_bridge),void(*)(size_t,size_t)),"RSS callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_memobj_rss_sub_bridge),void(*)(void*,size_t,size_t)),"memobj RSS callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_memobj_flush_bridge),void(*)(void*,unsigned long,size_t)),"memobj flush callback ABI");
_Static_assert(sizeof(size_t)==8 && sizeof(unsigned long)==8 && sizeof(int)==4,"accounting argument conversion ABI");
_Static_assert(sizeof(struct memobj)==56 && __builtin_offsetof(struct memobj,flags)==8 && __builtin_offsetof(struct memobj_ops,flush_page)==24,"actual object dispatch ABI");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l2_child_walk),x86_clear_child_walk_fn_t const),"L1 child identity");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_child_walk),x86_clear_child_walk_fn_t const),"L2 child identity");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_range_l3_callback),x86_clear_child_walk_fn_t const),"L3 child identity");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_rss_sub),x86_clear_rss_sub_fn_t const),"RSS immutable identity");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_memobj_rss_sub),x86_clear_memobj_rss_sub_fn_t const),"memobj RSS immutable identity");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_memobj_flush),x86_clear_flush_memobj_fn_t const),"flush immutable identity");
#endif
'''
write(P / 'real-header-ABI.c', abi)
prior = json.loads((B / 'next-l1-source-1/sourcehandoff/EXECUTABLE-READY.NOT-RELEASED.json').read_bytes())
rust = prior['commands'][0]['argv']
commands = []
providers = ['x86_clear_range_walk_l1_bridge','x86_clear_range_walk_l2_bridge','x86_clear_range_walk_l3_bridge','x86_clear_rss_sub_bridge','x86_clear_memobj_rss_sub_bridge','x86_clear_memobj_flush_bridge','memory_stat_rss_sub','rusage_memory_stat_sub','memobj_flush_page']
for enabled, tag in [(1,'on'),(0,'off')]:
    cmd = [x.replace('m14_clear_range_l1_fixture','m14_clear_batch_' + tag).replace('fixture-rust.o','fixture-' + tag + '.o') for x in rust]
    if enabled:
        cmd += ['--cfg','enable_rusage']
    commands += [dict(label='Rust-' + tag, argv=cmd), dict(label='GCC-link-' + tag, argv=['/usr/bin/gcc-9','-std=c11','-O2','-Wall','-Wextra','-Werror','-ffunction-sections','-fdata-sections','-DTEST_RUSAGE_ENABLED='+str(enabled),'fixture.c','fixture-'+tag+'.o','-Wl,--gc-sections','-o','fixture-'+tag]), dict(label='execute-' + tag, argv=[str(P / ('fixture-' + tag))]), dict(label='symbols-' + tag, argv=['/usr/bin/nm','-a','fixture-'+tag])]
for old in prior['commands'][3:5]:
    commands.append(dict(label='real-ABI-' + ('PUBLIC' if '-DMCKERNEL_RUST_X86_MEMORY_PUBLIC' in old['argv'] else 'fallback'), argv=old['argv'][:-1] + [str(P / 'real-header-ABI.c')]))
for row in commands:
    row.update(cwd=str(P), purpose=__doc__.splitlines()[0] + ' ' + row['label'])
headers = ['arch/x86_64/kernel/include/arch-memory-helpers.h','arch/x86_64/kernel/include/ihk/atomic.h','lib/include/ihk/mm.h','kernel/include/memobj.h','kernel/include/rusage.h','kernel/include/rusage_private.h','ihk/linux/include/ihk/ihk_rusage.h']
plan = dict(scope=__doc__.splitlines()[0], status='ONE_BATCH_FIXTURE_SOURCE_PREPARATION_ONLY_PENDING_FROZEN_DRIVER', product_sources=products, actual_module_inputs=inputs, actual_header_inputs=[ref(REPO / name) for name in headers], sources=[ref(f) for f in sorted(P.rglob('*')) if f.is_file()], commands=commands, profiles_existing_rusage_on_off=True, exact_oracle_identifier_renames=renames, expected_stdout={'execute-on':'PASS batch rusage=1 walkers=192 rss=180 flush=96 actual-C/Rust pairs; real accounting/ops; remaining providers controlled\n','execute-off':'PASS batch rusage=0 walkers=192 rss=181 flush=96 actual-C/Rust pairs; real accounting/ops; remaining providers controlled\n'}, expected_unique_ELF_Rust_T=providers, expected_actual_pairs={'on':468,'off':469}, actual_L1_L2_evidence='Existing accepted L2_1728 +L1_432 reused; no old suites repeated. Original L1/L2/L3 callbacks are consumer context for new walker vectors only.', actual_provider_scope='All three new walker dispatchers, RSS/memobjRSS narrowing+real atomic state with cfg on/off, memobj flush real ops dispatch/mutation/error discard. Exact C oracles with provider/callback identifier renames only.', remaining_C_providers='CPU/phys-to-page/remote-flush/page-unmap hooks/free/PTfree/range/effect logger endpoints are controlled and not claimed retired. Walker vectors use zero or large entries; no child-table allocation/physical-page ownership proof.', no_fake_accounting_or_memobj_dispatch=True, profile=prior['profile_proposal'], CPU_grant=None, CPU_reservation=None, actual_results=None, canonical_default_image_native_acceptance=None, failure_history='L1 implicit-prototype failure and sole declaration correction preserved; actual L1/L2 pass reused. This batch has no actual attempt; first unexpected result STOP/root decision.')
rr = write(P / 'BATCH-FIXTURE-SOURCES-AND-COMMANDS.NOT-RELEASED.json', plan)
print(json.dumps(dict(recipe=rr, commands=len(commands), jobs=0)))
