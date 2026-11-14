# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json
R=Path(__file__).resolve().parent.parent;A=R/'actual-owned-capture-1'
def rows(name):return [x.split() for x in (A/name/'stdout').read_text().splitlines() if x.split()]
def named(rs,n):return [x for x in rs if x[-1]==n]
def unique(rs,n,kind):
 x=named(rs,n);assert len(x)==1 and x[0][-2]==kind,(n,x)
target='x86_cpu_ulong_log_bridge'
r=rows('06-Rust-symbols');s=rows('07-selected-C-symbols');f=rows('08-fallback-C-symbols');p=rows('11-partial-symbols')
unique(r,target,'T');unique(r,'kprintf','U')
unique(s,target,'U');unique(s,'M14_CPU_LOG_CONSUMER','D')
unique(f,target,'t');unique(f,'kprintf','U')
unique(p,target,'T');unique(p,'kprintf','U')
assert target in (A/'09-selected-C-relocations/stdout').read_text()
assert not named(p,target)[0][-2]=='U'
out=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_LEAF_CPU_LOG_EXPORT_REAL_HEADER_SELECTED_FALLBACK_VARIADIC_RELOCATION_PARTIAL_ONLY',Rust_one_T=True,selected_C_U=True,fallback_C_static_t=True,kprintf_U_expected_leaf_only=True,full_production_Rust=False,whole_current_cpu_C_TU=False,default_kernel_link=False,native=False)
(R/'ACTUAL-LEAF-SYMBOL-OBSERVATION.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
