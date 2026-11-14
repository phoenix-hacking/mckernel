#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Compose hash-bound source descriptions in memory. No materialization or execution.
"""
from pathlib import Path
import hashlib,json,re
E=Path('/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234')
D=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/WEEKLY-ONLY-20261029-1/MANUAL-RESUME-M14-20261030-2');O=Path(__file__).resolve().parent
rust=D/'nonheld-signal-perf-group-compositor-1/NONHELD-SIGNAL-PERF-GROUP.PRIVATE.patch'; cpatch=D/'perf-paired-selector-private-1/PERF-PAIRED-SELECTOR.PRIVATE.patch'; C=E/'M14-CONVERSION-FIRST-COMPOSITION-1/postimage/kernel/syscall.c';CM=E/'M14-CONVERSION-FIRST-COMPOSITION-1/postimage/kernel/CMakeLists.txt';P=E/'M14-CONVERSION-FIRST-ACTUAL-SNAPSHOT-1/rust-subtree/syscall_policy.rs'; profile=E/'M14-CONVERSION-FIRST-PRODUCER-BINDING-1/current-frontier-successor-1/PROFILE.SOURCE-ONLY.json'
expert=D/'perf-abi-provenance-expert-1/prepare.py'; expert_cmp=D/'perf-abi-provenance-expert-1/compare_elf.py'; expert_review=D/'perf-abi-provenance-independent-review-1/REVIEW.md'; c_witness=D/'perf-paired-selector-private-1/REAL-HEADER-ABI-WITNESS.c.inc'; rust_witness=D/'perf-abi-witness-coherent-correction-1/f03_perf_entry_abi_witness.rs'; witness_patch=D/'perf-abi-witness-coherent-correction-1/RUST-WITNESS-ONLY.PRIVATE.patch'
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
exp={rust:'595d137bcaba9b4ce85361623edd5a12c174dc3baa53670bda5352ce80dd1d1a',cpatch:'7aaa310aaa15d12b0ce3a4c49a48f40e3a0e23a2d14c134b264935fbed93f345',C:'3388adb79adff66eb85ae65a443af2c18e7b2057dd76d0ec99b531d62a36cab3',CM:'30e3a04bf48777d4891f7390804e574ca221e4234e9a8d7879bb068910a13fbd',P:'14881100a803a90b25950b0c56d6fff6642a4cc8614c895a87418c6b7540dc50',profile:'8ab49c299dfc9218ddcf8df3cf71474d51e87167abe4cd166841ea47c3a32e2d',expert:'ee56647fdf644437da331cdfad810de37b36ec919db63459819400b8251c1798',expert_cmp:'baa35735e39207dfc3772b88c82fc5b380695599003a01d709ef2bbe96d08d1a',c_witness:'212fbf03425ea1e883f01cd4132b3821cca224a015890cabeaf3fda95e80d8c0',rust_witness:'632d3ce6039f26c4995034798e30465f54ba36c1d5af0da2299bf98ff2021e0c',witness_patch:'cb71f19e839df9f039b0e816c8e34220055413586576fa81f0557f1fb02f7c1a'}
for p,v in exp.items():assert h(p)==v,(p,h(p))
def parse(p):
 raw=p.read_text().splitlines(keepends=True); files=[];i=0
 while i<len(raw):
  assert raw[i].startswith('--- ') and raw[i+1].startswith('+++ ');left=raw[i][4:].strip();right=raw[i+1][4:].strip();i+=2;hs=[]
  while i<len(raw) and raw[i].startswith('@@ '):
   i+=1;old=[];new=[]
   while i<len(raw) and not raw[i].startswith(('@@ ','--- ')):
    x=raw[i];assert x[0] in ' +-'
    if x[0]!='+':old.append(x[1:])
    if x[0]!='-':new.append(x[1:])
    i+=1
   hs.append((old,new))
  files.append((left,right,hs))
 return files
def apply(src,hs):
 lines=src.splitlines(keepends=True)
 for old,new in hs:
  if not old:assert not lines;lines=new[:];continue
  hits=[i for i in range(len(lines)-len(old)+1) if lines[i:i+len(old)]==old];assert len(hits)==1,(len(hits),old[:1]);i=hits[0];lines[i:i+len(old)]=new
 return ''.join(lines)
files={'kernel/rust/syscall_policy.rs':P.read_text(),'kernel/CMakeLists.txt':CM.read_text(),'kernel/syscall.c':C.read_text(),'kernel/rust/f06_signal_log_budget.rs':'','kernel/rust/f03_perf_entry_candidate.rs':'','kernel/rust/f03_perf_group_cleanup.rs':''}
before=files.copy()
for patch in [rust,cpatch]:
 for left,right,hs in parse(patch):
  key=right.removeprefix('b/');assert key in files;files[key]=apply(files[key],hs)
assert set(files)=={'kernel/rust/syscall_policy.rs','kernel/CMakeLists.txt','kernel/syscall.c','kernel/rust/f06_signal_log_budget.rs','kernel/rust/f03_perf_entry_candidate.rs','kernel/rust/f03_perf_group_cleanup.rs'}
assert files['kernel/rust/f03_perf_entry_candidate.rs'].encode()==(D/'perf-group-failure-source-1/f03_perf_entry_candidate.rs').read_bytes()
assert files['kernel/rust/f03_perf_group_cleanup.rs'].encode()==(D/'perf-group-failure-source-1/f03_perf_group_cleanup.rs').read_bytes()
# Neither source delta changes any execve or direct-TID/terminate_host region.
for patch in (rust,cpatch):
 for line in patch.read_text().splitlines():
  if line.startswith(('+','-')) and not line.startswith(('+++','---')):
   assert not re.search(r'\b(execve|execveat|terminate_host|direct.tid)\b',line,re.I),line
# Existing source macro coordinates and C original line directives checked by constituent source records.
def loc(s):return [(n,m.start(),m.group()) for n,line in enumerate(s.splitlines(),1) for m in re.finditer(r'\b(?:line|file|column)!\s*\(',line)]
assert loc(before['kernel/rust/syscall_policy.rs'])==loc(files['kernel/rust/syscall_policy.rs'])
assert 'MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL' not in before['kernel/syscall.c']
assert 'MCKERNEL_F03_PERF_ENTRY_ABI_WITNESS' not in before['kernel/syscall.c']
assert files['kernel/syscall.c'].count(c_witness.read_text())==1
p=json.loads(profile.read_text()); r=p['exact_commands'][0]['argv'][:];c=p['exact_commands'][1]['argv'][:];link=p['exact_commands'][2]['argv'][:]
assert r[-1]=='/src/kernel/rust/lib.rs' and c[-1]=='/src/kernel/syscall.c'
assert 'f03_perf_entry_candidate' not in r and '-DMCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL' not in c
r[-1:-1]=['--cfg','f03_perf_entry_candidate'];c[-1:-1]=['-DMCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL']
assert '-DMCKERNEL_F03_PERF_ENTRY_ABI_WITNESS' not in c and 'f03_perf_entry_abi_witness' not in r
assert all('witness' not in arg for arg in link)
review=expert_review.read_text();assert 'Source-only review' in review and 'does not' in review
selected={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PRIVATE_SELECTED_SOURCE_DESCRIPTION_NOT_RELEASED','input_hashes':{str(p):h(p) for p in list(exp)+[expert_review]},'source_overlay_recipe':[{'base':'qualified actual producer 149-source closed set','patch':str(rust),'sha256':h(rust)},{'base':'qualified generic C exact source','patch':str(cpatch),'sha256':h(cpatch)}],'source_deltas_sha256':{k:hashlib.sha256(v.encode()).hexdigest() for k,v in files.items() if v!=before[k]},'conditions':['experimental Rust and C selectors must both be emitted in exact command; source guards alone cannot detect one-sided selection','C ENABLE_PERF must be proven from generated config.h at exact resolved include path and ordered include closure; it is not a direct baseline C argv definition','default producer retains both selectors OFF and original C entry','SDK21/9 unaffected objects only reusable after fresh exact source, object, toolchain, flags and linker bindings','no witness object or witness-only Rust source patch is included in production commands or final link'], 'illustrative_command_deltas':{'rust_exact_argv_source_only':r,'C_exact_argv_source_only':c,'link_exact_argv_source_only':link}, 'separate_witness_source_only':{'C_witness_source':str(c_witness),'Rust_witness':str(rust_witness),'Rust_witness_only_patch':str(witness_patch),'expert_generator':str(expert),'expert_comparator':str(expert_cmp),'source_review':str(expert_review),'constraints':'Neither expert generator nor comparator executed. C and Rust witness objects are distinct and excluded from every final link; executed generator/comparator bytes and dependencies require independent binding.'},'checks':['exact patches applied uniquely in memory to exact baseline','Rust/C patches edit disjoint selected units and three new Rust modules; no held-region patch lines','106 existing Rust location macro coordinates preserved; C constituent independently checked unchanged logical line coordinates','production argv adds exactly one paired Rust cfg and one C macro; baseline provider pairs retained','witness options absent from production argv and link'], 'rebuilds':['one full Rust crate object rust/mckernel_rust.o','one generic kernel C object CMakeFiles/mckernel.img.dir/syscall.c.o','fresh matching raw link; retain nine unaffected inputs only after fresh exact validation','separate C and Rust witness objects exclusively for ABI investigation; never link'], 'next_executable_check':'After independent exact source/profile and operation-specific review, reconcile Root70 current ownership/resource; bind and verify generated config.h and include closure, SDK21/toolchain, then admit the paired production Rust/C compilation and separate witnesses in fresh outputs under reviewed resources. Compare 31 scalar words and audit 13 actual callback type/relocation targets before final matching link and original metadata/functional/native gates.', 'acceptance':None,'compiler_or_native_run':False,'authority':None}
out=O/'SELECTED-PROFILE.SOURCE-ONLY.json';assert not out.exists();out.write_text(json.dumps(selected,indent=2,sort_keys=True)+'\n')
print(json.dumps({'profile_sha256':h(out),'source_delta_sha256':selected['source_deltas_sha256'],'expert_review_sha256':h(expert_review)},indent=2))
