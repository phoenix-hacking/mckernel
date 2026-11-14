"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Single next private L1 source/fixture successor atop actual tested private L2.
No compiler, test, root, canonical or runtime action.
"""
from pathlib import Path
import hashlib, json, difflib

BASE = Path(__file__).resolve().parent
P = BASE / 'next-l1-source-1'
assert not P.exists()
P.mkdir(mode=0o700)

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
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]

pins = {'arch/x86_64/kernel/memory.c': '19391dff7a1103e6805bd4c6120a3d58a8d9154f442c71dd1b8fb4e84fe61a9f', 'kernel/rust/x86_memory_helpers.rs': '316d7c827dd5b712ac0bdfd075f72da3683771f70716c2646f1c57595191bd38'}
before = {}
for name, expected in pins.items():
    raw = (BASE / 'candidate' / name).read_bytes()
    assert sha(raw) == expected
    write(P / 'preimage' / name, raw)
    before[name] = raw.decode()
c = before['arch/x86_64/kernel/memory.c']
rust = before['kernel/rust/x86_memory_helpers.rs']
l1 = body(c, 'static int clear_range_l1(')
walker = body(c, 'static int x86_clear_range_walk_l1_bridge(')
selected = '''#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
extern int clear_range_l1(void *args0, pte_t *ptep, uint64_t base,
        uint64_t start, uint64_t end);
#else
''' + l1 + '\n#endif'
c = c.replace(l1, selected, 1)
entry = '''/// Complete former C L1 callback. The existing leaf helper owns old-entry,
/// flush/free/page-unmap/RSS effects; raw args and count pointers remain borrowed.
#[no_mangle]
pub unsafe extern "C" fn clear_range_l1(
    args0: *mut c_void,
    ptep: *mut CULong,
    base: CULong,
    start: CULong,
    end: CULong,
) -> CInt {
    let args = args0.cast::<X86ClearRangeArgs>();
    unsafe {
        x86_clear_range_leaf_body_result(
            args0, ptep, base, start, end,
            (*args).vm, (*args).addr, core::ptr::addr_of_mut!((*args).nr_addr),
            (*args).max_nr_addr, ihk_mc_get_processor_id(),
            (*args).free_physical, (*args).memobj.cast(),
            Some(x86_clear_old_action_bridge), Some(remote_flush_tlb_array_cpumask),
            Some(x86_clear_l3_memobj_flush), Some(x86_clear_phys_to_virt_bridge),
            Some(x86_clear_free_pages_user_bridge), Some(x86_clear_page_unmap_bridge),
            Some(x86_clear_l3_rss_sub), Some(x86_clear_l3_memobj_rss_sub),
            Some(x86_clear_l3_effect_log),
        )
    }
}

'''
needle = '/// Complete former C L2 callback.'
assert rust.count(needle) == 1
rust = rust.replace(needle, entry + needle, 1)
post = [write(P / 'candidate/arch/x86_64/kernel/memory.c', c), write(P / 'candidate/kernel/rust/x86_memory_helpers.rs', rust)]
assert body(c, 'static int clear_range_l1(') == l1
assert body(c, 'static int x86_clear_range_walk_l1_bridge(') == walker
patch = ''
for name, after in [('arch/x86_64/kernel/memory.c', c), ('kernel/rust/x86_memory_helpers.rs', rust)]:
    patch += ''.join(difflib.unified_diff(before[name].splitlines(True), after.splitlines(True), fromfile='a/' + name, tofile='b/' + name))
write(P / 'patch/clear-range-l1.patch', patch)
for name in ('abi.rs', 'page_helpers.rs'):
    write(P / 'sourcehandoff/baseline' / name, (BASE / 'sourcehandoff/baseline' / name).read_bytes())
write(P / 'fixture/fixture.rs', (BASE / 'fixture/fixture.rs').read_text().replace('L2', 'L1'))
write(P / 'fixture/actual-types-and-level-declaration.inc', (BASE / 'fixture/actual-types-and-level-declaration.inc').read_bytes())
write(P / 'fixture/original-body.inc', l1.replace('static int clear_range_l1(', 'static int original_clear_range_l1(', 1) + '\n')
write(P / 'fixture/original-walker.inc', walker.replace('x86_clear_range_walk_l1_bridge', 'original_walk_l1', 1).replace('&clear_range_l1', '&original_clear_range_l1') + '\n')
write(P / 'fixture/selected-walker.inc', walker.replace('x86_clear_range_walk_l1_bridge', 'selected_walk_l1', 1) + '\n')
fixture = (BASE / 'fixture/fixture.c').read_text().replace('L2', 'L1').replace('PTL2', 'PTL1')
fixture = fixture.replace('#define PTL1_SHIFT 21', '#define PTL1_SHIFT 12').replace('#define PTL1_SIZE (1UL<<21)', '#define PTL1_SIZE (1UL<<12)').replace('#define PFL1_SIZE 0x80\n', '')
fixture = fixture.replace('clear_range_l2', 'clear_range_l1').replace('walk_pte_l2', 'walk_pte_l1').replace('original_walk_l2', 'original_walk_l1').replace('selected_walk_l2', 'selected_walk_l1')
fixture = fixture.replace('const int child_results[]={0,-2,-5,7},nrvalues[]={-1,0,2};', 'const int nrvalues[]={-1,0,2};')
fixture = fixture.replace('for(unsigned q=0;q<4;q++)', '').replace(';child_ret=child_results[q]', '')
first = '  else if((entries[e]&0x80)'
last = '  active=NULL;direct++;'
start = fixture.index(first)
end = fixture.index(last, start)
fixture = fixture[:start] + fixture[end:]
fixture = fixture.replace('require((coverage&0x7ffe)==0x7ffe,"all14provider/effect trace categories observed");', 'require((coverage&0x65fe)==0x65fe,"all11leaf provider/effect trace categories observed");\n require(!(coverage&((1UL<<9)|(1UL<<11)|(1UL<<12))),"leaf has no range log/child walk/child PTfree");')
fixture = fixture.replace('real Rust level/effect/oldaction/phys/walk/page-mode bodies', 'real Rust leaf/effect/oldaction/phys/walk/page-unmap bodies')
fixture = fixture.replace('actual level/effects/oldaction/phys/walk bodies', 'actual leaf/effects/oldaction/phys/walk bodies')
write(P / 'fixture/fixture.c', fixture)
abi = '''/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "../candidate/arch/x86_64/kernel/memory.c"
_Static_assert(__builtin_types_compatible_p(__typeof__(&clear_range_l1),int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"full L1 callback ABI");
#ifdef MCKERNEL_RUST_X86_MEMORY_PUBLIC
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_memobj_flush),x86_clear_flush_memobj_fn_t const),"reused memobj flush ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_rss_sub),x86_clear_rss_sub_fn_t const),"reused RSS ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_memobj_rss_sub),x86_clear_memobj_rss_sub_fn_t const),"reused memobj RSS ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l3_effect_log),x86_clear_effect_log_fn_t const),"reused effect log ABI");
#endif
_Static_assert(PTL1_SHIFT==12 && PTL1_SIZE==(1UL<<12),"exact L1 geometry");
_Static_assert(sizeof(pte_t)==sizeof(unsigned long) && sizeof(pte_t)==8,"actual x86 PTE width");
'''
write(P / 'fixture/real-header-ABI.c', abi)
prior = json.loads((BASE / 'sourcehandoff/EXECUTABLE-READY.L2-LABEL-SUCCESSOR.NOT-RELEASED.json').read_bytes())
commands = prior['commands']
for row in commands:
    row['cwd'] = str(P / 'fixture')
    row['argv'] = [value.replace(str(BASE), str(P)).replace('m14_clear_range_l2_fixture', 'm14_clear_range_l1_fixture') for value in row['argv']]
    row['role'] = row['role'].replace('L2', 'L1').replace('level/effects', 'leaf/effects')
    row['purpose'] = __doc__.splitlines()[0] + ' ' + row['role']
commands[2]['role'] = '384 direct +48 actual PUBLIC L1 walker =432 original C/Rust leaf pairs; all11leaf effect categories and no child teardown callbacks'
commands[2]['purpose'] = __doc__.splitlines()[0] + ' ' + commands[2]['role']
ready = dict(scope=__doc__.splitlines()[0], status='SINGLE_QUEUED_PRIVATE_L1_SUCCESSOR_SOURCE_AND_FIXTURE_NOT_EXECUTED', source_preimages=[dict(path=str(BASE / 'candidate' / k), sha256=v) for k, v in pins.items()], postimages=post, sources=[dict(path=str(f), sha256=sha(f.read_bytes()), bytes=f.stat().st_size) for f in sorted(P.rglob('*')) if f.is_file()], commands=commands, expected_pairs=432, expected_stdout='PASS direct=384 PUBLIC-walker=48 original-C/Rust L1 pairs; actual leaf/effects/oldaction/phys/walk bodies; retained lower-provider traces\n', actual_private_L2_predecessor_receipt=dict(path=str(BASE / 'sourcehandoff/ACTUAL-CLEAR-RANGE-L2-FIXTURE-RECEIPT.json'), sha256=sha((BASE / 'sourcehandoff/ACTUAL-CLEAR-RANGE-L2-FIXTURE-RECEIPT.json').read_bytes())), callback_contract='No new C provider or data object; uses same4 existing memobjflush/RSS/memobjRSS/effectlog callback identities. Raw args/count/PTE pointers borrowed, exact leaf null policy; lower C walker and external provider bodies remain debt.', profile_proposal=prior['profile_proposal'], remaining_C_debt=['unchanged C walk L1/L2/L3 dispatch wrappers and callbacks', 'existing memobj flush/RSS/memobjRSS/range/effect logging/PTfree external bodies'], CPU_grant=None, actual_fixture_result=None, production_fullcrate_TU_partial_default_link_native='OPEN', canonical_integration=False)
write(P / 'sourcehandoff/EXECUTABLE-READY.NOT-RELEASED.json', json.dumps(ready, sort_keys=True, indent=2) + '\n')
print(json.dumps(dict(postimages=post, ready_sha256=sha((P / 'sourcehandoff/EXECUTABLE-READY.NOT-RELEASED.json').read_bytes()), expected_pairs=432, commands=len(commands), compiler_test_root_runtime=False)))
