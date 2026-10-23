"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import json
D=Path(__file__).resolve().parent;p=json.loads((D/'source-pins.json').read_text())
oldc=(D/'preimage/arch/x86_64/kernel/memory.c').read_text();newc=(D/'postimage/arch/x86_64/kernel/memory.c').read_text();assert newc.replace(p['selected_C_body'],p['original_C_body'])==oldc
old=(D/'preimage/kernel/rust/x86_memory_helpers.rs').read_text();new=(D/'postimage/kernel/rust/x86_memory_helpers.rs').read_text();restored=new.replace(p['new_Rust_body']+'\n','').replace(p['Rust_linker_declaration'],'');a='    fn x86_init_text_panic_bridge();';assert restored.count(a)==1;restored=restored.replace(a,'    fn x86_init_text_end_bridge() -> CULong;\n'+a);assert restored==old
assert (D/'fixture.rs').read_text().endswith(p['new_Rust_body'])
assert (D/'original_bridge.c.inc').read_text()==p['original_C_body']+'\n'
assert (D/'selected_bridge.c.inc').read_text()==p['selected_C_body']+'\n'
old=(D/'preimage/kernel/rust/tests/run_equivalence.sh').read_text();new=(D/'postimage/kernel/rust/tests/run_equivalence.sh').read_text();restored=new.replace((D/'harness_declaration.c.inc').read_text(),'').replace((D/'harness_check.c.inc').read_text(),'');a='void x86_init_text_panic_bridge(void)\n';assert restored.count(a)==1;restored=restored.replace(a,p['old_harness_stub']+a)
a="grep -Eq ' T x86_init_text_end_bridge$' \"${tmpdir}/out/rust.global\"\ngrep -Eq 'U _end$' \"${tmpdir}/out/rust.undefined\"\n! grep -Eq 'U x86_init_text_end_bridge$' \"${tmpdir}/out/rust.undefined\"";b="grep -Eq 'U x86_init_text_end_bridge' \"${tmpdir}/out/rust.undefined\"";assert restored.count(a)==1;assert restored.replace(a,b)==old
assert '"MCKERNEL_RUST_X86_USER_COPY_PUBLIC;MCKERNEL_RUST_X86_MEMORY_PUBLIC"' in (D/'preimage/kernel/CMakeLists.txt').read_text()
assert 'mod x86_memory_helpers;' in (D/'preimage/kernel/rust/lib.rs').read_text()
print('PASS exact production/harness reversal; only getter/address-linker declaration/C selection and own harness checks differ; no C data/functionality added')
