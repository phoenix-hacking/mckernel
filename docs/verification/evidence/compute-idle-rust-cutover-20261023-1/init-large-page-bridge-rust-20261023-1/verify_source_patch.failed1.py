"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
import hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent
old=(D/'preimage/kernel/rust/tests/run_equivalence.sh').read_text();new=(D/'postimage/kernel/rust/tests/run_equivalence.sh').read_text()
oldU=re.findall(r"grep -Eq 'U ([^']+)'",old);newU=re.findall(r"grep -Eq 'U ([^']+)'",new)
# Negative no-U assertion still names bridge; compare positive requirements only.
newPositiveU=re.findall(r"^grep -Eq 'U ([^']+)'",new,re.M)
assert [x for x in oldU if x!='x86_init_normal_set_large_bridge']==newPositiveU
assert old.count("' T x86_init_normal_set_large_bridge$'")==0 and new.count("' T x86_init_normal_set_large_bridge$'")==1
assert '-eq 594\n' in old and '-eq 593\n' in new
restored=new.replace((D/'harness_declaration.c.inc').read_text(),'').replace((D/'harness_bridge_test.c.inc').read_text(),'')
a='int x86_init_normal_set_large_bridge(void *pt, unsigned long virt,\n';start=old.index(a);end=old.index('\n}',start)+3;stub=old[start:end]
marker='void x86_init_normal_log_bridge(int event, unsigned long a,\n';assert restored.count(marker)==1;restored=restored.replace(marker,stub+marker)
a="grep -Eq ' T x86_init_normal_set_large_bridge$' \"${tmpdir}/out/rust.global\"\n! grep -Eq 'U x86_init_normal_set_large_bridge$' \"${tmpdir}/out/rust.undefined\""
b="grep -Eq 'U x86_init_normal_set_large_bridge' \"${tmpdir}/out/rust.undefined\""
assert restored.count(a)==1;restored=restored.replace(a,b).replace('-eq 593\n','-eq 594\n');assert restored==old,'unrelated harness bytes changed'
oldc=(D/'preimage/arch/x86_64/kernel/memory.c').read_text();newc=(D/'postimage/arch/x86_64/kernel/memory.c').read_text();assert newc.replace((D/'selected_bridge.c.inc').read_text().rstrip('\n'),(D/'original_bridge.c.inc').read_text().rstrip('\n'))==oldc
oldrs=(D/'preimage/kernel/rust/x86_memory_helpers.rs').read_text();newrs=(D/'postimage/kernel/rust/x86_memory_helpers.rs').read_text();pins=json.loads((D/'source-pins.json').read_text())
bridge=pins['rust_bridge_body'];assert newrs.count(bridge)==1 and newrs.count('fn x86_init_normal_set_large_bridge(')==1
assert newrs.count(pins['rust_existing_provider_body'])==1
extern='''    fn x86_init_normal_set_large_bridge(
        pt: *mut c_void,
        virt: CULong,
        phys: CULong,
        attr: CULong,
    ) -> CInt;
'''
restored=newrs.replace(bridge+'\n','');marker='    fn x86_init_normal_log_bridge(';assert restored.count(marker)==1;restored=restored.replace(marker,extern+marker);assert restored==oldrs,'unrelated production Rust bytes changed'
# Actual default consumers remain the existing CMake PUBLIC define and Rust lib module.
assert '"MCKERNEL_RUST_X86_USER_COPY_PUBLIC;MCKERNEL_RUST_X86_MEMORY_PUBLIC"' in (D/'preimage/kernel/CMakeLists.txt').read_text()
assert 'mod x86_memory_helpers;' in (D/'preimage/kernel/rust/lib.rs').read_text()
print('PASS exact finite patch reversal: only C selection, one Rust forwarding export/import replacement, duplicate harness stub removal/new bridge-provider check/U-to-T/594-to593; all other harness and production bytes identical')
