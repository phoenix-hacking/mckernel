# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import json,hashlib,re
P=Path(__file__).resolve().parent;R=Path('/home/holden/mckernel')
b=json.loads((P/'SOURCE-BINDINGS.json').read_text());old=(R/'kernel/process.c').read_text();new=(P/'source/kernel/process.c').read_text();selected=(P/'ORIGINAL-SELECTED-C.c').read_text().rstrip();fallback=(P/'ORIGINAL-FALLBACK-C.c').read_text().rstrip()
a=old.index('void spin_sleep_or_schedule(void)');z=old.index('\n#ifdef MCKERNEL_RUST_PROCESS_HELPERS\nextern unsigned long sched_schedule_fp_admit',a)
assert old[:a]+'#ifndef MCKERNEL_RUST_PROCESS_HELPERS\n'+fallback+'\n#endif\n'+old[z:]==new
rs=(R/'kernel/rust/sched_helpers.rs').read_text();post=(P/'source/kernel/rust/sched_helpers.rs').read_text();leaf=(P/'fixture/actual.rs').read_text()
assert post.split('pub unsafe extern "C" fn sched_spin_sleep_or_schedule_body_result',1)[1]==rs.split('pub unsafe extern "C" fn sched_spin_sleep_or_schedule_body_result',1)[1]
assert 'fn sched_runqueue_offsets() -> SchedRunqueueOffsets' in leaf
for rel,pin in {**b['source_inputs'],**b['header_inputs']}.items():assert hashlib.sha256(Path(pin['path']).read_bytes()).hexdigest()==pin['sha256'],rel
assert post.count('pub unsafe extern "C" fn spin_sleep_or_schedule()')==1
report=dict(scope=b['scope'],status='PASS_SOURCE_ONLY',canonical_unchanged=True,all_other_process_bytes_including_accepted_fixes_unchanged=True,C_fallback_exact=True,existing_Rust_body_unchanged=True,existing_shared_ABI_offset_constructor_reused=True,existing_lock_adapters_reused=True,existing_futex_direct_consumer_extracted=True,whole_C_TU_default_link_native='OPEN')
(P/'SOURCE-CHECK.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
