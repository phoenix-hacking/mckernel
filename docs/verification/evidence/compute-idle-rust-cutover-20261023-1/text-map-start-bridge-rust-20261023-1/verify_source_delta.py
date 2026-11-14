"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Proposed finite source comparison; not run by the source-only preparation."""
from pathlib import Path
import json,re
D=Path(__file__).resolve().parent
p=json.loads((D/'source-pins.json').read_text())
oldc=(D/'preimage/arch/x86_64/kernel/memory.c').read_text();newc=(D/'postimage/arch/x86_64/kernel/memory.c').read_text()
assert newc.replace(p['new_C_fragment'],p['original_C_body'])==oldc
oldrs=(D/'preimage/kernel/rust/x86_memory_helpers.rs').read_text();newrs=(D/'postimage/kernel/rust/x86_memory_helpers.rs').read_text()
restored=newrs.replace(p['new_Rust_body']+'\n','')
added='    #[link_name = "x86_map_kernel_start_geometry"]\n    static X86_MAP_KERNEL_START_GEOMETRY: CULong;\n'
assert restored.count(added)==1;restored=restored.replace(added,'')
a='    fn x86_init_text_end_bridge() -> CULong;';assert restored.count(a)==1;restored=restored.replace(a,'    fn x86_init_text_map_kernel_start_bridge() -> CULong;\n'+a)
assert restored==oldrs
oldh=(D/'preimage/kernel/rust/tests/run_equivalence.sh').read_text();newh=(D/'postimage/kernel/rust/tests/run_equivalence.sh').read_text()
restored=newh.replace((D/'harness_declaration.c.inc').read_text(),'').replace((D/'harness_check.c.inc').read_text(),'')
restored=restored.replace('const unsigned long x86_map_kernel_start_geometry = 0xfffffe0000000000UL;\n',p['old_harness_stub'])
a="grep -Eq ' T x86_init_text_map_kernel_start_bridge$' \"${tmpdir}/out/rust.global\"\ngrep -Eq 'U x86_map_kernel_start_geometry$' \"${tmpdir}/out/rust.undefined\"\n! grep -Eq 'U x86_init_text_map_kernel_start_bridge$' \"${tmpdir}/out/rust.undefined\""
b="grep -Eq 'U x86_init_text_map_kernel_start_bridge' \"${tmpdir}/out/rust.undefined\""
assert restored.count(a)==1;assert restored.replace(a,b)==oldh
assert '"MCKERNEL_RUST_X86_USER_COPY_PUBLIC;MCKERNEL_RUST_X86_MEMORY_PUBLIC"' in (D/'preimage/kernel/CMakeLists.txt').read_text()
assert 'mod x86_memory_helpers;' in (D/'preimage/kernel/rust/lib.rs').read_text()
assert re.findall(r'^test .*rust.undefined.* -eq (\d+)$',oldh,re.M)==re.findall(r'^test .*rust.undefined.* -eq (\d+)$',newh,re.M)
print('PASS finite exact reversal: only getter/data-witness/PUBLIC fallback/harness expectations; existing default consumer and all other bytes preserved')
