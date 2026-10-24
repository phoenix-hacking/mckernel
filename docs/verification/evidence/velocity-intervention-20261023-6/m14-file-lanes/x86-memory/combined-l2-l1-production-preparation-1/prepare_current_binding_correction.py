"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One bounded source-only CURRENT canonical binding correction; no compiler/test/copy job.
"""
from pathlib import Path
import copy, hashlib, json

B = Path(__file__).resolve().parents[1]
P = Path(__file__).resolve().parent / 'bounded-current-canonical-binding-correction-1'
P.mkdir(mode=0o700)
OLD = Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-5/m14-memory-l3-next/production-consumer-preparation-1')
REPO = Path('/home/holden/mckernel')
SRC = B / 'next-l1-source-1/candidate'
SCOPE = __doc__.splitlines()[0]

def ref(path):
    raw = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))

def write(path, value):
    raw = value.encode() if isinstance(value, str) else (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()
    with path.open('xb') as out:
        out.write(raw)
    return ref(path)

r0 = json.loads((OLD / 'EXACT-PRODUCTION-RUST-RECIPE.NOT-EXECUTED.json').read_bytes())
c0 = json.loads((OLD / 'EXACT-SELECTED-GCC9-ARCHMEMORY-CONSUMER.NOT-EXECUTED.json').read_bytes())
r, c = copy.deepcopy(r0), copy.deepcopy(c0)
rows, delta = {}, []
expected_delta = {'kernel/rust/process_helpers.rs': 'd04b48c887c834edd6380e3ae06fccdef7dfafaf67196fd28af7f9571993bd6d', 'kernel/rust/x86_cpu_helpers.rs': '26180e00c1d6673aa600f0ec9afed5d100ca6e0c39af803c3328e58f8cc88fb9'}
for name, prior in r0['source_inputs'].items():
    canonical = ref(REPO / name)
    chosen = ref(SRC / name) if name == 'kernel/rust/x86_memory_helpers.rs' else canonical
    rows[name] = dict(canonical_before=canonical, source_to_copy=chosen, private=dict(path=str(P / 'source' / name), sha256=chosen['sha256'], bytes=chosen['bytes']), baseline=prior['private'])
    if canonical['sha256'] != prior['private']['sha256']:
        delta.append(dict(name=name, baseline=prior['private'], current=canonical))
assert len(rows) == 78 and {x['name']: x['current']['sha256'] for x in delta} == expected_delta
for name, prior in c0['reused67_header_pins'].items():
    assert ref(Path(prior['path'])) == prior, ('real header drift', name)
private_c = ref(SRC / 'arch/x86_64/kernel/memory.c')
private_rust = ref(SRC / 'kernel/rust/x86_memory_helpers.rs')
assert private_c['sha256'] == '93df0ac24de8163cc5a7e2cce277d3a46c89a607b924c1937f2413e12edf0f66'
assert private_rust['sha256'] == '800a18bb4db0e28bf76441fca783b3f8d47066260240fb5107967c23775aa494'
r.update(scope=SCOPE, status='RECIPE_BLOCKED_REAL_L1_FIXTURE_AND_ACTUAL78_STAGING_NO_GRANT', source_inputs=rows, source_identity_rows=[[name, row['private']['sha256'], row['private']['bytes']] for name, row in sorted(rows.items())], source_count=78, candidate_source=private_rust, only_private_override=['kernel/rust/x86_memory_helpers.rs'], other77_currentcanonical_equal_accepted_baseline=False, current_canonical_delta_from_accepted_L3=delta, actual_leaf=ref(B / 'sourcehandoff/ACTUAL-CLEAR-RANGE-L2-FIXTURE-RECEIPT.json'), actual_L1_fixture_receipt=None, actual_source78_materialization=None, object_until_actual_compile=None, compiler_jobs=0, patch=ref(B / 'next-l1-source-1/patch/clear-range-l1.patch'))
r['argv'] = [x.replace(str(OLD), str(P)) for x in r0['argv']]
r['expected_all_prior_T'] = r0['expected_all_prior_T'] + r0['expected_T_added']
r['expected_T_added'] = ['clear_range_l1', 'clear_range_l2', 'vm_range_insert_log_bridge', 'x86_cpu_ulong_log_bridge']
undefined = set(r0['expected_U'])
assert 'vm_range_insert_log_bridge' in undefined
undefined.remove('vm_range_insert_log_bridge')
undefined.update(['process_vm_range_insert_debug', 'x86_clear_l2_child_walk'])
assert len(undefined) == 585
r['expected_U'] = sorted(undefined)
r['expected_U_delta'] = dict(basis='Source-derived prediction from accepted L3 actual584U, current process logger replacement and privateL2 data; current CPU ulong logger adds T only/no new U. Actual values NULL until compiled.', before=584, after=585, added=['process_vm_range_insert_debug', 'x86_clear_l2_child_walk'], removed=['vm_range_insert_log_bridge'])
rust_ref = write(P / 'EXACT-PRODUCTION-RUST-RECIPE.BLOCKED-L1.NOT-EXECUTED.json', r)
abi = (OLD / 'actual-memory-header-ABI.c').read_text().replace(c0['private_memory_source']['path'], private_c['path'])
abi += '''
/* Additive full L2/L1 and retained L1 walker identity real-header witnesses. */
_Static_assert(__builtin_types_compatible_p(__typeof__(&clear_range_l2),int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"full L2 callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&clear_range_l1),int(*)(void*,pte_t*,uint64_t,uint64_t,uint64_t)),"full L1 callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(x86_clear_l2_child_walk),x86_clear_child_walk_fn_t const),"immutable L1 walker identity ABI");
_Static_assert(PTL2_SHIFT==21 && PTL2_SIZE==(1UL<<21) && PFL2_SIZE==((pte_t)0x80),"L2 geometry");
_Static_assert(PTL1_SHIFT==12 && PTL1_SIZE==(1UL<<12),"L1 geometry");
'''
abi_ref = write(P / 'actual-memory-header-ABI.c', abi)
for row in c['commands']:
    row['argv'] = [x.replace(c0['private_memory_source']['path'], private_c['path']).replace(str(OLD), str(P)) for x in row['argv']]
    row['cwd'] = row['cwd'].replace(str(OLD), str(P))
    row['purpose'] = SCOPE + ' Combined private L2/L1 selected actual GCC9 ' + row['label']
c.update(scope=SCOPE, status='SELECTED_WHOLE_TU_RECIPE_BLOCKED_ACTUAL_L1_FIXTURE_NO_GRANT', Rust_recipe=rust_ref, private_memory_source=private_c, canonical_memory_preimage=ref(REPO / 'arch/x86_64/kernel/memory.c'), ABI_witness=abi_ref, expected_C_import=['clear_range_l1', 'clear_range_l2', 'clear_range_l3'], expected_C_no_definition=sorted(set(c0['expected_C_no_definition'] + ['clear_range_l1', 'clear_range_l2'])), expected_partial_unique_Rust_T=c0['expected_partial_unique_Rust_T'] + r['expected_T_added'], current_canonical_mem_source=ref(REPO / 'kernel/mem.c'), actual_L1_fixture_receipt=None, Rust_object_until_actual_compile=None, artifact_hashes_until_actualrun=None)
c['expected_new_immutable_callback_data']['x86_clear_l2_child_walk'] = 'x86_clear_range_walk_l1_bridge'
c['callback_relocation_rule'] = c0['callback_relocation_rule'] + ' Add x86_clear_l2_child_walk global OBJECT size8/alignment>=8; match its own SHT_RELA.sh_info and symbol offset to one R_X86_64_64 targeting exact private C walk_l1 function or owning section+offset. Preserve existing9 mappings, require10 total. Never compare offsets across target sections.'
c['retained_C_debt'] = ['C walk L1/L2/L3 dispatchers; separate next-walk-L1 SOURCE patch not included here', 'Existing memobj flush/RSS/memobjRSS/range/effect log/PTfree providers', 'process_vm_range_insert_debug descriptor is external C data; selected partial link does not claim all-kernel unresolved closure']
c_ref = write(P / 'EXACT-SELECTED-GCC9-MEMORY-CONSUMER.BLOCKED-L1.NOT-EXECUTED.json', c)
preflight = '''# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
# Required addition to accepted run_actual_once.py before any compiler.
assert ready['actual_L1_fixture_receipt'] is not None, 'L1 fixture missing: refuse compile'
leaf_ref = ready['actual_L1_fixture_receipt']
assert sha(Path(leaf_ref['path'])) == leaf_ref['sha256']
leaf = json.loads(Path(leaf_ref['path']).read_bytes())
assert leaf['status'] == 'PASS_ACTUAL_COMPLETE_CLEAR_RANGE_L1_432_PAIRS_AND_REAL_PUBLIC_FALLBACK_HEADER_ABI'
assert leaf['actual_pairs'] == 432 and leaf['CPU6_released'] is True
assert all(row['returncode'] == 0 and row['direct_child_joined'] and row['group_absent'] and row['closed_streams'] and row['error'] is None and row['retirement_error'] is None for row in leaf['captures'])
assert ready['actual_source78_materialization'] is not None, 'Actual78 staging missing: refuse compile'
# Unchanged sources() then verifies all canonical/private SHA and actual67 header pins.
'''
preflight_ref = write(P / 'REQUIRED-EXISTING-RUNNER-L1-PREFLIGHT.py.inc', preflight)
ready = dict(scope=SCOPE, status='COHERENT_CURRENT78_L2_L1_PRODUCTION_RECIPE_NOT_SECOND_EXECUTABLE_QUEUE', Rust_recipe=rust_ref, C_recipe=c_ref, required_existing_runner_preflight=preflight_ref, accepted_runner=ref(OLD / 'run_actual_once.py'), accepted_actual_L3_receipt=ref(OLD / 'ACTUAL-PRODUCTION-CONSUMER-RECEIPT.json'), actual_L2_fixture_receipt=ref(B / 'sourcehandoff/ACTUAL-CLEAR-RANGE-L2-FIXTURE-RECEIPT.json'), actual_L1_fixture_receipt=None, actual_source78_materialization=None, source78_copy_recipe='Existing finite source_inputs78 relative-path copy only after ordinary grant; verify source_to_copy SHA before copy; no recursive repo/evidence copying. Actual staging manifest/receipt NULL.', current_canonical_delta=delta, private_memory_overrides=[private_c, private_rust], source_preparation_failure_retained=ref(Path(__file__).resolve().parent / 'SOURCE-PREPARATION-STOP-1.json'), bounded_source_correction='CURRENT CPU26180 integrated between initial closure lookup and first recipe generation. Exactly processd04 + CPU26180 canonical refresh, all67headers unchanged; no compiler/test failure/replay.', expected_Rust_U_delta=r['expected_U_delta'], expected_prior_Rust_T=len(r['expected_all_prior_T']), expected_added_Rust_T=r['expected_T_added'], expected_selected_partial_unique_Rust_T=len(c['expected_partial_unique_Rust_T']), expected_section_specific_callback_data=10, actual_output_hashes=None, actual_T_U_relocations_partial_link=None, needed_existing_runner_witness_data_delta=['Use new source/recipe pins and required realL1 preflight; never presume L1 PASS', 'Preserve prior3044 T, require4 additions, exact585U set; source-derived predictions only', 'Require exact3 C imports L1/L2/L3/no selected C definitions and actual symbol-token relocations', 'Preserve real-header ABI and add5 assertions with unchanged GCC9 cfg/includes/flags', 'Existing section-aware ELF parser plus one typed pointer target; no fixed section offsets/numbers', 'Require42 named unique Rust T in actual partial output, no U for these providers; unrelated fullkernel U remains separate'], profile=r0['profile'], ordinary_grant=None, CPU_reservation=None, compiler_test_jobs=0, future_GCC14_default_image_native='OPEN', next_body_source_not_included=ref(B / 'next-walk-l1-source-only-1/SOURCE-BODY-AND-OWNERSHIP.NOT-EXECUTED.json'))
handoff = write(P / 'COMBINED-PRODUCTION-RECIPE.BLOCKED-L1-HANDOFF.json', ready)
print(json.dumps(dict(Rust=rust_ref, C=c_ref, handoff=handoff, source78_copied=False, compiler_test_jobs=0)))
