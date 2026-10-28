"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only exact source composition checks; no compiler, guard or workload.
"""
from pathlib import Path
import hashlib,json
D=Path(__file__).resolve().parent
proof=json.loads((D/'SELECTIVE-SEVEN-COMPOSITION-PROOF.json').read_text())
closed=json.loads((D/'CLOSED-CURRENT115-PLUS-SEVEN-SOURCE-MAP.json').read_text())
def checked(r):
 raw=Path(r['path']).read_bytes();assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256'];return raw
for key in ['Root115_source_adoption','frozen115_ready','frozen115_source_map','canonical115_C_preimage','frozen115_policy_preimage','candidate_C','candidate_policy','trio_production_source_reused','WAKE3_reused','step_source_reused']:checked(proof[key])
for row in closed['private120_Rust_files']:
 checked(row['frozen115']);checked(row['new_snapshot'])
 if row['relative']!='syscall_policy.rs':assert row['frozen115']['sha256']==row['new_snapshot']['sha256']
for row in closed['external_relative_modules']:
 checked(row['genuine']);checked(row['snapshot']);assert row['genuine']['sha256']==row['snapshot']['sha256']
c=checked(proof['candidate_C']).decode();r=checked(proof['candidate_policy']).decode();assert (D/'context-root/kernel/rust/syscall_policy.rs').read_text()==r
for s in ['#line 21118\n','#line 21150\n','#line 24477\n','#line 24491\n']:assert c.count(s)==1
for module in ['ptrace_setsiginfo_entry','ptrace_syscall_event_entry','ptrace_wakeup_state_callbacks','ptrace_wakeup_step_callback']:assert r.count('mod '+module+' {')==1
assert 'mod f06_obtain_clone_cpuid;' in r
assert checked(proof['WAKE3_reused']).decode() in r and checked(proof['step_source_reused']).decode() in r
# The bounded wakeup block is exactly the previously checked bank+step block.
anchor='#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS\nstatic const struct ptrace_io_offsets ptrace_wakeup_io_offsets = {'
end='static int ptrace_wakeup_sig(int pid, long request, long data) {\n'
def interval(text):
 start=text.index(anchor);stop=text.index(end,start)+len(end);return text[start:stop]
old=(D.parent/'current114-perf-restore-correction-source-1/candidate/kernel/syscall.c').read_text();assert interval(c)==interval(old)
assert len(closed['private120_Rust_files'])==120 and len(closed['external_relative_modules'])==3
assert proof['Root115_cpuid_suffix_byteexact'] and proof['Root115_processhelpers_snapshot_byteexact']
print(json.dumps(dict(status='PASS_PRIVATE115_PLUS_SEVEN_SOURCE_ONLY',frozen_Rust_files=120,external_modules=3,changed_Rust_files=1,shared_wakeup_restore=1,compiler_runtime_query_calls=0)))
