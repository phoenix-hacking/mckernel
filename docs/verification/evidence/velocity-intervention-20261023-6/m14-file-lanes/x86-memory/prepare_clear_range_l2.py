"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source/fixture preparation only. No compiler, test, root or runtime action.
"""
from pathlib import Path
import ast, difflib, hashlib, json, os

P = Path(__file__).resolve().parent
REPO = Path('/home/holden/mckernel')
OLD = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-memory-l3-next/bounded-product-correction-1')
PREIMAGES = {
    'arch/x86_64/kernel/memory.c': '28a435d862d1a52263c3bf7b08bd401b4a28be914c2f7f9bdd6fedc68283ec46',
    'kernel/rust/x86_memory_helpers.rs': '245faf1198d9b7715714d236238172330257f4291776aced4e7cee6c3c518ce2',
}

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def write(path, raw):
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if isinstance(raw, str):
        raw = raw.encode()
    with path.open('xb') as out:
        out.write(raw)
    return dict(path=str(path), sha256=sha(raw), bytes=len(raw))

def body(text, signature):
    start = text.index(signature)
    opening = text.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]

original = {}
for name, expected in PREIMAGES.items():
    raw = (REPO / name).read_bytes()
    assert sha(raw) == expected, ('canonical preimage mismatch', name)
    write(P / 'preimage' / name, raw)
    original[name] = raw.decode()
c = original['arch/x86_64/kernel/memory.c']
rust = original['kernel/rust/x86_memory_helpers.rs']
l2 = body(c, 'static int clear_range_l2(')
walker = body(c, 'static int x86_clear_range_walk_l2_bridge(')
assert c.count(l2) == 1
selection = '''#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
/* Synchronous existing L1 C walker identity; its lower chain remains C debt. */
x86_clear_child_walk_fn_t const x86_clear_l2_child_walk = &x86_clear_range_walk_l1_bridge;
extern int clear_range_l2(void *args0, pte_t *ptep, uint64_t base,
        uint64_t start, uint64_t end);
#else
''' + l2 + '\n#endif'
candidate_c = c.replace(l2, selection, 1)
needle = '    static x86_clear_l3_child_walk: X86ClearChildWalkFn;'
assert rust.count(needle) == 1
rust = rust.replace(needle, '    static x86_clear_l2_child_walk: X86ClearChildWalkFn;\n' + needle, 1)
entry = '''/// Complete former C L2 callback. Raw borrowed args/PTE/count storage is
/// reread only as in the original call; no Rust reference spans C callbacks.
/// L2 large pages are always enabled, independent of the live L3 1GB flag.
#[no_mangle]
pub unsafe extern "C" fn clear_range_l2(
    args0: *mut c_void,
    ptep: *mut CULong,
    base: CULong,
    start: CULong,
    end: CULong,
) -> CInt {
    let args = args0.cast::<X86ClearRangeArgs>();
    // Caller-valid args0 is evaluated even if the shared helper rejects ptep.
    unsafe {
        x86_clear_range_level_body_result(
            args0, ptep, base, start, end,
            PTL2_SHIFT, PTL2_SIZE, PFL2_SIZE, 1,
            (*args).vm, (*args).addr, core::ptr::addr_of_mut!((*args).nr_addr),
            (*args).max_nr_addr, ihk_mc_get_processor_id(),
            (*args).free_physical, (*args).memobj.cast(),
            Some(x86_clear_old_action_bridge), Some(x86_clear_phys_to_virt_bridge),
            Some(x86_clear_l2_child_walk), Some(remote_flush_tlb_array_cpumask),
            Some(x86_pt_free_pages_bridge), Some(x86_clear_l3_memobj_flush),
            Some(x86_clear_free_pages_user_bridge), Some(x86_clear_page_unmap_bridge),
            Some(x86_clear_l3_rss_sub), Some(x86_clear_l3_memobj_rss_sub),
            Some(x86_clear_l3_range_log), Some(x86_clear_l3_effect_log),
        )
    }
}

'''
insertion = '/// Complete former C L3 callback.'
assert rust.count(insertion) == 1
candidate_rust = rust.replace(insertion, entry + insertion, 1)
post = [write(P / 'candidate/arch/x86_64/kernel/memory.c', candidate_c),
        write(P / 'candidate/kernel/rust/x86_memory_helpers.rs', candidate_rust)]
patch = ''
for name, after in [('arch/x86_64/kernel/memory.c', candidate_c), ('kernel/rust/x86_memory_helpers.rs', candidate_rust)]:
    patch += ''.join(difflib.unified_diff(original[name].splitlines(True), after.splitlines(True), fromfile='a/' + name, tofile='b/' + name))
write(P / 'patch/clear-range-l2.patch', patch)
assert candidate_c.count(l2) == 1 and body(candidate_c, 'static int clear_range_l2(') == l2
assert body(candidate_c, 'static int x86_clear_range_walk_l2_bridge(') == walker
for name in ['abi.rs', 'page_helpers.rs']:
    raw = (REPO / 'kernel/rust' / name).read_bytes()
    assert raw == (OLD / 'sourcehandoff/baseline' / name).read_bytes()
    write(P / 'sourcehandoff/baseline' / name, raw)
write(P / 'fixture/original-body.inc', l2.replace('static int clear_range_l2(', 'static int original_clear_range_l2(', 1) + '\n')
write(P / 'fixture/original-walker.inc', walker.replace('x86_clear_range_walk_l2_bridge', 'original_walk_l2', 1).replace('&clear_range_l2', '&original_clear_range_l2') + '\n')
write(P / 'fixture/selected-walker.inc', walker.replace('x86_clear_range_walk_l2_bridge', 'selected_walk_l2', 1) + '\n')
write(P / 'fixture/actual-types-and-level-declaration.inc', (OLD / 'fixture/actual-types-and-level-declaration.inc').read_bytes())
rs = (OLD / 'fixture/fixture.rs').read_text().replace('L3', 'L2')
write(P / 'fixture/fixture.rs', rs)
fixture = (OLD / 'fixture/fixture.c').read_text()
fixture = fixture.replace('L3', 'L2').replace('PTL3', 'PTL2').replace('PFL3', 'PFL2').replace('#define PTL2_SHIFT 30', '#define PTL2_SHIFT 21').replace('#define PTL2_SIZE (1UL<<30)', '#define PTL2_SIZE (1UL<<21)')
fixture = fixture.replace('clear_range_l3', 'clear_range_l2').replace('original_walk_l3', 'original_walk_l2').replace('selected_walk_l3', 'selected_walk_l2').replace('walk_pte_l3', 'walk_pte_l2')
# The retained L3 callback identities already name these same original C providers.
# L2 adds exactly one distinct lower-walker identity; do not invent a C body import.
fixture = fixture.replace('x86_clear_range_walk_l2_bridge', 'x86_clear_range_walk_l1_bridge')
fixture = fixture.replace('x86_clear_child_walk_fn_t const x86_clear_l3_child_walk=&x86_clear_range_walk_l1_bridge;', 'x86_clear_child_walk_fn_t const x86_clear_l2_child_walk=&x86_clear_range_walk_l1_bridge;')
fixture = fixture.replace('static int use_1gb_page;\n', '').replace('const int *const x86_clear_l3_use_1gb_page=&use_1gb_page;\n', '')
fixture = fixture.replace(',enabled[]={0,1,-1}', '')
fixture = fixture.replace('for(unsigned u=0;u<3;u++)', '')
fixture = fixture.replace(';use_1gb_page=enabled[u]', '')
assert 'enabled[u]' not in fixture and 'for(unsigned u=' not in fixture
write(P / 'fixture/fixture.c', fixture)
abi = '''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "../candidate/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&clear_range_l2),int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"full L2 callback ABI");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l2_child_walk),x86_clear_child_walk_fn_t const),"exact retained L1 child walker ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_memobj_flush),x86_clear_flush_memobj_fn_t const),"reused memobj flush callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_rss_sub),x86_clear_rss_sub_fn_t const),"reused RSS callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_memobj_rss_sub),x86_clear_memobj_rss_sub_fn_t const),"reused memobj RSS callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_range_log),x86_clear_range_log_fn_t const),"reused range log callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_effect_log),x86_clear_effect_log_fn_t const),"reused effect log callback ABI");
#endif
_Static_assert(PTL2_SHIFT==21 && PTL2_SIZE==(1UL<<21) && PFL2_SIZE==((pte_t)0x80),"exact x86 L2 geometry");
_Static_assert(sizeof(pte_t)==sizeof(unsigned long) && sizeof(pte_t)==8,"actual x86 PTE width");
'''
write(P / 'fixture/real-header-ABI.c', abi)
plan = json.loads((OLD / 'sourcehandoff/EXECUTABLE-READY.GRANTED.json').read_bytes())
commands = plan['commands']
for row in commands:
    row['cwd'] = str(P / 'fixture')
    row['argv'] = [value.replace(str(OLD), str(P)).replace('m14_clear_range_l3_fixture', 'm14_clear_range_l2_fixture') for value in row['argv']]
    row['role'] = row['role'].replace('L3', 'L2')
    row['purpose'] = __doc__.splitlines()[0] + ' ' + row['role']
commands[2]['role'] = '1536 direct +192 actual PUBLIC walker =1728 original C/Rust L2 pairs, all14 provider/effect categories; expected counts unobserved'
commands[2]['purpose'] = __doc__.splitlines()[0] + ' ' + commands[2]['role']
sources = [dict(path=str(path), sha256=sha(path.read_bytes()), bytes=path.stat().st_size) for path in sorted(P.rglob('*')) if path.is_file()]
ready = dict(scope=__doc__.splitlines()[0], status='PRIVATE_IMPLEMENTATION_AND_FIXTURE_READY_NOT_EXECUTED', canonical_preimages=[dict(path=str(REPO / name), sha256=value) for name, value in PREIMAGES.items()], postimages=post, sources=sources, commands=commands, expected_stdout='PASS direct=1536 PUBLIC-walker=192 original-C/Rust L2 pairs; actual level/effects/oldaction/phys/walk bodies; retained lower-provider traces\n', expected_pairs=1728, expected_full_ABI='int(void*,pte_t*,uint64_t,uint64_t,uint64_t); public Rust export clear_range_l2, fallback original static C body', callback_ownership='Raw borrowed args/PTE/count; immutable synchronous L1 callback; original nr_addr/flush/free and helper ordering; reuse six exact existing L3 callback identities for same C providers; no exclusive Rust reference or new null policy', remaining_C_debt=['unchanged x86_clear_range_walk_l2_bridge C dispatcher selects now Rust L2 under PUBLIC', 'x86_clear_range_walk_l1_bridge and clear_range_l1 callback chain', 'existing memobj flush/RSS/memobjRSS/rangeLog/effectLog/PTfree external provider bodies'], fixture_scope='Actual complete candidate Rust x86memory/page modules and original exact C L2 callback/selected actual PUBLIC walker; existing external provider trace endpoints; no full kernel or native credit', old_family_history='Accepted L3 previous failure+bounded correction remain preserved and are reused as preparation basis; L2 has no actual attempt yet. First unexpected failure stop.', profile_proposal=dict(cpu=6, jobs=1, AS_bytes=2<<30, CPU_seconds=60, wall_seconds=90, retirement_seconds=6, FSIZE_bytes=32<<20, NOFILE=256, core=0, Rust_stack_bytes=2<<20, Rust_CGU=1, toolchains='Pinned Rust1.92 and GCC9 exactly as accepted L3 leaf profile', capture='Accepted990 owned_capture dict recipe + signal handlers + CWD binding', aggregate_bytes=19<<30, HOST_floor_bytes=16<<30, scratch_floor_bytes=12<<30, full_sparse_growth_required=True), CPU_grant=None, actual_compilers=None, actual_fixture_result=None, production_fullcrate_TU_partial_default_link_native='OPEN')
write(P / 'sourcehandoff/EXECUTABLE-READY.NOT-RELEASED.json', json.dumps(ready, indent=2, sort_keys=True) + '\n')
print(json.dumps(dict(postimages=post, ready_sha256=sha((P / 'sourcehandoff/EXECUTABLE-READY.NOT-RELEASED.json').read_bytes()), commands=len(commands), expected_pairs=1728, executed=False)))
