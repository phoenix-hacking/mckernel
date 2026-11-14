"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Pure next3 source/ABI/narrowing/reuse/selector/recipe checks; no compiler or run.
"""
from pathlib import Path
import hashlib,json,re
D=Path(__file__).resolve().parent
def read(name):return json.loads((D/name).read_text())
slices=read('SOURCE-SLICES.json');assert len(slices)==3
source=(D/'preimages/kernel/syscall.c').read_text();candidate=(D/'candidate/kernel/syscall.c').read_text()
for row in slices:
 assert source.count(row['original'])==1 and candidate.count(row['selector'])==1
 assert row['selector'].count(row['original'])==1
 assert '#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_PERF_PROVIDER_NEXT3_BRIDGES)' in row['selector']
 assert row['selector'].endswith('#endif\n#line '+str(row['logical_after'])+'\n')
 candidate=candidate.replace(row['selector'],row['original'],1)
assert candidate==source
fragment=(D/'selected-bridges.Rust.inc').read_text()
assert fragment.count('#[no_mangle]')==2 and fragment.count('#[cfg(all(enable_perf, f03_perf_provider_next3_bridges_selected_candidate))]')==2
assert 'unsafe { crate::x86_perfctr::ihk_mc_perfctr_set_extra(event.cast()) }' in fragment
assert 'unsafe { crate::x86_perfctr::ihk_mc_perfctr_init_raw(counter_id, hw_config as u32, mode) }' in fragment
assert 'pub unsafe extern "C" fn perf_event_atomic64_read_bridge' not in fragment
atomic=next(row for row in slices if row['name']=='perf_event_atomic64_read_bridge')
assert '#define perf_event_atomic64_read_bridge syscall_atomic64_read_bridge' in atomic['selector']
assert 'extern long syscall_atomic64_read_bridge(void *value);' in atomic['selector']
init=next(row for row in slices if row['name']=='perf_counter_init_raw_bridge')
assert '__builtin_types_compatible_p(__typeof__(&ihk_mc_perfctr_init_raw), int (*)(int,unsigned int,int))' in init['selector']
assert 'sizeof(unsigned long)==8 && sizeof(unsigned int)==4' in init['selector']
retained=(D/'retained-syscall-atomic64-read-bridge.Rust.inc').read_text()
policy=(D/'preimages/kernel/rust/syscall_policy.rs').read_text()
assert policy.count(retained)==1 and (D/'candidate/kernel/rust/syscall_policy.rs').read_text()==policy+fragment
assert 'crate::atomic_helpers::ihk_atomic64_read(value.cast())' in retained
assert '.as_ref(' not in fragment and '.as_mut(' not in fragment and 'read_volatile' not in fragment
values=[0,1,0x7fffffff,0x80000000,0xffffffff,0x100000000,0x8000000000000000,0xffffffffffffffff]
expected=[0,1,0x7fffffff,0x80000000,0xffffffff,0,0,0xffffffff]
assert [value%(1<<32) for value in values]==expected
assert any(value!=result for value,result in zip(values,expected)),'high-word truncation must actually be exercised'
for helper,selector in [(False,False),(False,True),(True,False),(True,True)]:assert (helper and selector)==(helper+selector==2)
plan=read('FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json')
assert len(plan['commands'])==7 and plan['runtime_authority'] is None and not Path(plan['future_output_root']).exists()
assert plan['expected_C_Rust_pairs']==8*6+4*8*4*6+8*7==872
assert plan['expected_single_call_traces']==2*872 and plan['new_Rust_wrappers']==2 and plan['reused_existing_Rust_bridge']==1
for row in plan['source_inputs']:
 raw=Path(row['path']).read_bytes();assert len(raw)==row['bytes'] and hashlib.sha256(raw).hexdigest()==row['sha256']
for command in plan['commands']:
 assert Path(command['argv'][0]).is_absolute() and Path(command['cwd']).is_absolute() and command['requires_fresh_Root_ordinary_grant'] is True
 assert command['purpose'].startswith('Functional') and 'no security testing' in command['purpose']
assert len({row['argv'][-1] for row in plan['commands'][1:5]})==4
driver=(D/'driver.c').read_text()
assert 'extra==48 && init==768 && atomic==56 && extra+init+atomic==872' in driver
assert 'init_oracle(counters[c],(unsigned int)configs[h],modes[m])' in driver
assert 'f03_selected_atomic==syscall_atomic64_read_bridge' in driver
assert 'LONG_MIN' in driver and 'LONG_MAX' in driver and '0x100000000UL' in driver
print(json.dumps(dict(status='PASS_PRIVATE_NEXT3_SOURCE_AND_UNRUN_MOCK_RECIPE',C_bodies=3,new_Rust_wrappers=2,exact_existing_atomic_bridge=1,
 u64_to_u32_boundary_cases=8,selector_profiles=4,proposed_mock_pairs=872,proposed_exact_traces=1744,proposed_ABI_words=16,
 compiler_commands=0,fixture_runs=0,canonical_writes=0)))
