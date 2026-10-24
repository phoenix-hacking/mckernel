# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json
P=Path(__file__).resolve().parent.parent;A=P/'actual-owned-capture-1'
def rows(n):return [x.split() for x in (A/n/'stdout').read_text().splitlines() if x.split()]
def unique(rs,n,k):
 a=[x for x in rs if x[-1]==n];assert len(a)==1 and a[0][-2]==k,(n,a)
target='x86_context_line_log_bridge'
r=rows('06-Rust-symbols');s=rows('07-selected-C-symbols');f=rows('08-fallback-C-symbols');p=rows('11-partial-symbols')
unique(r,target,'T');unique(r,'kprintf','U');unique(r,'__kprintf','U')
unique(s,target,'U');unique(f,target,'T');unique(f,'kprintf','U');unique(f,'__kprintf','U')
unique(p,target,'T');unique(p,'kprintf','U');unique(p,'__kprintf','U')
assert target in (A/'09-selected-C-relocations/stdout').read_text()
out=dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PASS_COMPLETE_CONTEXT_LOG_LEAF_REAL_HEADER_SELECTED_FALLBACK_PROVIDER_CHANNELS_AND_PARTIAL_ONLY',Rust_unique_T=True,C_selected_U=True,C_fallback_original_T=True,actual_formatters_executed=False,production_fullcrate_wholeCPU_TU_defaultlink_native=False)
(P/'ACTUAL-LEAF-SYMBOL-OBSERVATION.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
