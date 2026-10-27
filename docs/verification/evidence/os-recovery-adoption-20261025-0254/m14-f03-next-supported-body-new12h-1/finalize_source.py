#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import hashlib,json,re
P=Path(__file__).resolve().parent
O=P/'future-host-output-2'  # Root runner must create fresh output after grant.
scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
cc=['/usr/bin/cc','-std=c11','-Wall','-Wextra','-Werror','-O2']
commands=[{'id':'rust-host-object','argv':['/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc','--edition=2021','--crate-name','f03_counter_control_fixture','--crate-type','lib','--emit=obj','-C','panic=abort','-C','opt-level=2','--cfg','enable_perf','--cfg','f03_perf_counter_control_bridges_selected_candidate',str(P/'lib.fixture.rs'),'-o',str(O/'providers.o')],'expected':'exit0;3 genuine Rust wrapper exports; no actual PMU provider'}]
profiles=[('selected',['-DMCKERNEL_RUST_SYSCALL_POLICY_HELPERS','-DMCKERNEL_RUST_F03_PERF_COUNTER_CONTROL_BRIDGES']),('fallback-none',[]),('fallback-helper',['-DMCKERNEL_RUST_SYSCALL_POLICY_HELPERS']),('fallback-callback',['-DMCKERNEL_RUST_F03_PERF_COUNTER_CONTROL_BRIDGES'])]
for name,defs in profiles:
 commands.append({'id':name+'-witness','argv':cc+defs+['-c',str(P/'selector-witness.c'),'-o',str(O/(name+'.o'))],'expected':'exit0; paired selector C ABI and static fallback compile'})
commands.append({'id':'host-parity-link','argv':cc+[str(P/'driver.c'),str(O/'selected.o'),str(O/'providers.o'),'-o',str(O/'parity')],'expected':'exit0; no actual architecture provider object'})
commands.append({'id':'host-parity-run','argv':[str(O/'parity')],'expected':'exit0; stdout exactly PASS counter-control 432 C/Rust pairs; 864 exact single-call traces; ABI6; selected3\n'})
for row in commands:
 row.update({'purpose':scope+' '+row['id'],'cwd':str(P),'timeout_seconds':30,'stdout_limit_bytes':16384,'stderr_limit_bytes':16384,'requires_fresh_Root_ordinary_grant':True})
plan={'scope':scope,'status':'SOURCE_ONLY_NOT_GRANTED','sequential':True,'compiler_jobs':1,'commands':commands,'requires':'Fresh Root current account/source/ownership ordinary admission and exact grant; no old nonce/lease reuse','no_actual_commands_run':True,'original_file_predicate':'F03 supported default McKernel runtime has no selected project-owned C implementation, matching complete Rust/C default artifacts and native proof'}
(P/'FUTURE-HOST-COMMAND-PLAN.NOT-GRANTED.json').write_text(json.dumps(plan,indent=2)+'\n')
# Pure source consistency only, not a compiler or fixture execution.
a=(P/'preimage.syscall.c').read_text();b=(P/'postimage.syscall.c').read_text()
def tracking(text):
 n=1;out=[]
 for line in text.splitlines():
  m=re.match(r'#line (\d+)',line)
  if m:n=int(m.group(1));continue
  if '__FILE__' in line or '__LINE__' in line:out.append([n,line])
  n+=1
 return out
assert tracking(a)==tracking(b)
rows=json.loads((P/'SOURCE-SLICES.json').read_text())
for row in rows:
 assert a.count(row['original'])==1 and b.count(row['selector'])==1
 assert row['name'] in (P/'selected-bridges.Rust.inc').read_text()
proof={'scope':scope,'status':'PASS_SOURCE_ONLY','compiler_runs':0,'fixture_runs':0,'original_tracking_expressions':len(tracking(a)),'postimage_tracking_expressions':len(tracking(b)),'all_original_file_line_token_locations_preserved':True,'selectors':3,'Root_confirmed_no_competing_owner':True}
(P/'SOURCE-CONSISTENCY.json').write_text(json.dumps(proof,indent=2)+'\n')
files={}
for p in sorted(P.iterdir()):
 if p.is_file() and p.name!='SOURCE-HANDOFF.NOT-GRANTED.json':
  data=p.read_bytes();files[p.name]={'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
handoff={'scope':scope,'status':'SOURCE_READY_NOT_GRANTED','owner':'/root/m14_f03_next_body','selected_C_names':[row['name'] for row in rows],'reused_Rust_providers':['crate::x86_perfctr::ihk_mc_perf_counter_mask_check','crate::x86_perfctr::ihk_mc_perfctr_start','crate::x86_perfctr::ihk_mc_perfctr_stop'],'existing_gates':['MCKERNEL_RUST_SYSCALL_POLICY_HELPERS','ENABLE_PERF/enable_perf','supported Linux6.12/x86/runtime/noUBSAN'],'proposed_C_define':'MCKERNEL_RUST_F03_PERF_COUNTER_CONTROL_BRIDGES','proposed_Rust_cfg':'f03_perf_counter_control_bridges_selected_candidate','new_C_algorithm_bodies':0,'new_Rust_callback_bodies':3,'actual_compiler_commands':0,'actual_behavioral_tests':0,'actual_default_builds':0,'actual_native_apps':0,'native_or_whole_file_acceptance':False,'expected_mock_C_Rust_pairs':432,'expected_exact_single_call_traces':864,'expected_ABI_words':6,'canonical_writes':0,'next':'Root independent source/ABI review and fresh ordinary seven-command HOST grant; then Root reconciles exact canonical source + CMake gates into next production cohort. No HOST19/current109 replay.','files':files}
(P/'SOURCE-HANDOFF.NOT-GRANTED.json').write_text(json.dumps(handoff,indent=2)+'\n')
print(json.dumps(proof))
