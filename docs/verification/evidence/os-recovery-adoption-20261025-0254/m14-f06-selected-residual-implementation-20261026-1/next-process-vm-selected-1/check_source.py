"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Focused source proof for the next one-provider selector, no compiler or new oracle.
"""
import json
from pathlib import Path
import prepare_source as s

D=Path(__file__).resolve().parent
binding=json.loads((D/'SOURCE-BINDINGS.json').read_text())
for reference in binding['before']+[binding['reused_fragment'],binding['selected_frontier'],
                                     binding['existing_cpu_provider'],binding['genuine_header']]:
    assert s.ref(Path(reference['path']))==reference,'source/proof changed'
cpath,rpath=[Path(r['path']) for r in binding['before']]
c,r,module,original,wrapped,selection,reused=s.compose(cpath.read_text(),rpath.read_text(),s.OLD_FRAGMENT.read_text())
assert c==(D/'syscall.c').read_text()
assert r==(D/'syscall_policy.rs').read_text()
assert module==(D/'f06_prctl_set_register.rs').read_text()
assert original==(D/'original_bridge.inc').read_text()
assert c.replace(wrapped,original,1)==cpath.read_text()
assert r.removesuffix(selection)==rpath.read_text()
assert reused in module
assert module.count('#[no_mangle]')==1
assert module.count('pub unsafe extern "C" fn ')==1
assert 'arch_prctl_get_register_bridge' not in module
assert 'arch_mmap' not in module and 'log_bridge' not in module
assert 'crate::x86_cpu_helpers::ihk_mc_arch_set_special_register(type_, value)' in module
assert '#[cfg(f06_prctl_set_register_candidate)]' in selection
frontier=json.loads(s.FRONTIER.read_text())
assert 'arch_prctl_set_register_bridge' in frontier['F06_examples']
header=Path(binding['genuine_header']['path']).read_text()
assert 'int ihk_mc_arch_set_special_register(enum ihk_asr_type, unsigned long value);' in header
provider=Path(binding['existing_cpu_provider']['path']).read_text()
assert 'pub unsafe extern "C" fn ihk_mc_arch_set_special_register(reg_type: CInt, value: CULong) -> CInt {' in provider
fixture=(D/'fixture.c').read_text()
assert '#include <ihk/cpu.h>' in fixture and '#include "original_bridge.inc"' in fixture
assert 'int ihk_mc_arch_set_special_register(enum ihk_asr_type type, unsigned long value)' in fixture
assert 'original_calls != 1 || calls != 1' in fixture
assert 'seen_value != values[j]' in fixture and 'rust_result != results[k]' in fixture
packet=json.loads((D/'FUTURE-COMPILER-ARGV.json').read_text())
assert packet['actual'] is None and packet['resources']['heavy_owner_granted'] is False
assert len(packet['commands'])==3
assert packet['expected']['parity_cases']==13*8*7==728
print(json.dumps(dict(status='PASS_ONE_PROVIDER_SOURCE_SELECTION',
 checks='frozen bindings/exact reuse/inverse reversibility/single provider/current helper and header ABI/fixture scope',
 compiler=None,parity_execution=None,link=None,native=None),sort_keys=True))
