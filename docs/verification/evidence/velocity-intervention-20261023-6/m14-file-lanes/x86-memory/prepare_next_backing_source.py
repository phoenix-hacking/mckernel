"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only qualification and one backing-provider port; no fixture execution.
"""
from pathlib import Path
import difflib
import hashlib
import json
import re

B = Path(__file__).resolve().parent
R = Path('/home/holden/mckernel')
F = B / 'batch-walkers-rss-flush-fixture-preparation-1'
S = B / 'next-memobj-flush-source-only-1/candidate'
O = B / 'next-pt-phys-to-virt-source-only-1'
U = B.parents[1] / 'root-union-preparation-1/CANONICAL-INTEGRATION.json'

def ident(p):
    b = p.read_bytes()
    return dict(path=str(p), bytes=len(b), sha256=hashlib.sha256(b).hexdigest())

def write(p, b):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as out:
        out.write(b if isinstance(b, bytes) else b.encode())

def record(p, data):
    write(p, json.dumps(data, indent=2, sort_keys=True) + '\n')

def body(text, name):
    m = re.search(r'(?m)^(?:static |pub unsafe extern "C" |X86_MEMORY_PUBLIC_BRIDGE )[^;\n]*\b' + re.escape(name) + r'\s*\([^;]*?\)\s*(?:->[^\n{]+)?\s*\{', text)
    assert m, name
    a = text.index('{', m.start())
    depth = 1
    i = a + 1
    while depth:
        depth += (text[i] == '{') - (text[i] == '}')
        i += 1
    return text[m.start():i]

assert not O.exists()
union = json.loads(U.read_bytes())
expected = {
    'arch/x86_64/kernel/memory.c': '93df0ac24de8163cc5a7e2cce277d3a46c89a607b924c1937f2413e12edf0f66',
    'kernel/rust/x86_memory_helpers.rs': '800a18bb4db0e28bf76441fca783b3f8d47066260240fb5107967c23775aa494',
}
canonical = []
for rel, sha in expected.items():
    assert next(row['after'] for row in union['written'] if row['path'] == str(R / rel)) == sha
    row = ident(R / rel)
    assert row['sha256'] == sha
    canonical.append(row)

ct = (R / 'arch/x86_64/kernel/memory.c').read_text()
rt = (R / 'kernel/rust/x86_memory_helpers.rs').read_text()
private_c = (S / 'arch/x86_64/kernel/memory.c').read_text()
private_r = (S / 'kernel/rust/x86_memory_helpers.rs').read_text()
old_c = (B / 'preimage/arch/x86_64/kernel/memory.c').read_text()
names = ['x86_clear_range_walk_l1_bridge', 'x86_clear_range_walk_l2_bridge', 'x86_clear_range_walk_l3_bridge', 'x86_clear_rss_sub_bridge', 'x86_clear_memobj_rss_sub_bridge', 'x86_clear_memobj_flush_bridge']
oracle_rows = []
for name in names:
    original = body(old_c, name)
    assert original == body(ct, name) == body(private_c, name), name
    oracle_rows.append(dict(symbol=name, current_C_body_equals_historical_oracle_and_private_fallback=True, body_sha256=hashlib.sha256(original.encode()).hexdigest()))
for name in ['clear_range_l1', 'clear_range_l2']:
    assert body(rt, name) == body(private_r, name), name

recipe = json.loads((F / 'BATCH-FIXTURE-FINAL-RECIPE.NOT-EXECUTED.json').read_bytes())
pins = recipe['sources'] + recipe['product_sources'] + recipe['actual_module_inputs'] + recipe['actual_header_inputs'] + list(recipe['reused67_header_pins'].values()) + [recipe['actual_debug_type_input']]
assert not any(row['path'] in {str(R / rel) for rel in expected} for row in pins)
qualification = dict(scope=__doc__, status='SOURCE_RELATION_QUALIFIED_ONLY_NO_EXECUTION', canonical_authority=ident(U), canonical=canonical, historical_oracle=ident(B / 'preimage/arch/x86_64/kernel/memory.c'), exact_reference_provider_relations=oracle_rows, integrated_Rust_clear_L1_L2_bodies_equal_private=True, frozen_recipe=ident(F / 'BATCH-FIXTURE-FINAL-RECIPE.NOT-EXECUTED.json'), frozen_driver=ident(F / 'run_actual_once.NOT-RELEASED.py'), old_canonical_source_precheck_present=False, driver_or_recipe_modified=False, independent_current_full78_proof=False, qualification='Frozen batch uses immutable historical modules; root-union changes to other Rust modules are not retroactive proof of this cohort. No source refresh or new queue.', actual_fixture=None, CPU_grant=None)
record(O / 'FROZEN-937-BATCH-CURRENT-CANONICAL-QUALIFICATION.json', qualification)

relc = 'arch/x86_64/kernel/memory.c'
relr = 'kernel/rust/x86_memory_helpers.rs'
original = body(private_c, 'x86_pt_phys_to_virt_bridge')
assert original == body(ct, 'x86_pt_phys_to_virt_bridge')
selection = '#ifndef MCKERNEL_RUST_X86_MEMORY_PUBLIC\n' + original + '\n#endif'
new_c = private_c.replace(original, selection, 1)
foreign = '    fn x86_pt_phys_to_virt_bridge(phys: CULong) -> *mut c_void;\n'
assert private_r.count(foreign) == 1
port = '''
// The existing translator samples init_pt_loaded and performs the established
// wrapping direct-map calculation. This provider takes no page ownership.
#[no_mangle]
pub unsafe extern "C" fn x86_pt_phys_to_virt_bridge(phys: CULong) -> *mut c_void {
    unsafe { phys_to_virt(phys) }
}
'''
new_r = private_r.replace(foreign, '', 1) + port
assert new_r.count('fn x86_pt_phys_to_virt_bridge(') == 1
for rel, old, new in [(relc, private_c, new_c), (relr, private_r, new_r)]:
    write(O / 'candidate' / rel, new)
    patch = ''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), fromfile='a/' + rel, tofile='b/' + rel))
    write(O / 'patch' / (Path(rel).name + '.diff'), patch)
write(O / 'EXACT-ORIGINAL-C-PROVIDER.inc', original + '\n')
write(O / 'FUTURE-FIXTURE-FRAGMENT.NOT-QUEUED.c', '''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Fragment only: no driver/argv/second executable cohort. Existing translator
 * init-state callback must be recorded, not replaced by constant arithmetic.
 */
extern void *x86_pt_phys_to_virt_bridge(unsigned long);
static void future_pt_translation_case(unsigned long physical)
{
    reset_existing_init_state_callback_trace();
    void *old = original_x86_pt_phys_to_virt_bridge(physical);
    struct init_state_trace expected = take_existing_init_state_callback_trace();
    reset_existing_init_state_callback_trace();
    void *actual = x86_pt_phys_to_virt_bridge(physical);
    assert(old == actual);
    assert_existing_init_state_callback_trace_equal(expected);
}
/* Future cases: both init states; zero/page-mask/boundary/high/MAX physical
 * bits; wrapped result zero; exactly one state sample, no dereference/free.
 */
''')
record(O / 'SOURCE-PROVIDER-AND-CONSUMER-INVARIANTS.NOT-EXECUTED.json', dict(scope=__doc__, chosen_complete_body='x86_pt_phys_to_virt_bridge', preimages=[ident(S / relc), ident(S / relr)], postimages=[ident(O / 'candidate' / relc), ident(O / 'candidate' / relr)], patch=[ident(O / 'patch' / 'memory.c.diff'), ident(O / 'patch' / 'x86_memory_helpers.rs.diff')], canonical_relation=ident(O / 'FROZEN-937-BATCH-CURRENT-CANONICAL-QUALIFICATION.json'), complete_Rust_body='Uses existing actual phys_to_virt -> x86_phys_to_virt_body_result; no arithmetic model or new callback.', provider_ownership='PUBLIC C definition excluded; existing forward C declaration unchanged; global Rust provider replaces its foreign import. Actual unique T/no self-U and real selected C partial provider resolution remain future.', callback_state='Exactly one existing x86_addr_init_pt_loaded_bridge state sample; same MAP_ST_START/LINUX_PAGE_OFFSET_BASE and wrapping unsigned64 addition. No new null policy: wrapped zero remains zero.', page_lock_lifetime='Only raw address translation. No dereference, allocation/free, page reference, lock, retained borrow, callback retention, or state publication; existing page-table callers and callback ordering unchanged.', fallback_C_body_byte_identical=True, tracing_and_error_semantics='No tracing, return-code or panic added; PTfree source-file/line tracking is untouched and remains C debt.', remaining_C_debt=['x86_pt_free_pages_bridge and allocator backing callbacks', 'range/effect logging providers', 'physical initialization-state provider', 'other live memory bodies and backing object operations'], new_driver_queue_or_reservation=None, actual_fixture_TU_partial_default_native=None, future_fragment=ident(O / 'FUTURE-FIXTURE-FRAGMENT.NOT-QUEUED.c')))
print(json.dumps(dict(qualification=ident(O / 'FROZEN-937-BATCH-CURRENT-CANONICAL-QUALIFICATION.json'), handoff=ident(O / 'SOURCE-PROVIDER-AND-CONSUMER-INVARIANTS.NOT-EXECUTED.json'), postimages=[ident(O / 'candidate' / relc), ident(O / 'candidate' / relr)])))
