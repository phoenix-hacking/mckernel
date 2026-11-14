#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import re, json, hashlib, difflib
P=Path(__file__).resolve().parent
R=Path('/home/holden/mckernel')
s=(R/'kernel/syscall.c').read_text()
rows=[]
post=s
for name,args,call in [
 ('perf_counter_mask_check_bridge','unsigned long counter_mask','ihk_mc_perf_counter_mask_check(counter_mask)'),
 ('perf_counter_start_bridge','unsigned long counter_mask','ihk_mc_perfctr_start(counter_mask)'),
 ('perf_counter_stop_bridge','unsigned long counter_mask, int flags','ihk_mc_perfctr_stop(counter_mask, flags)')]:
 old=f'static int\n{name}({args})\n{{\n\treturn {call};\n}}\n'
 assert s.count(old)==1
 offset=s.index(old)
 physical=s[:offset].count('\n')+1
 logical=1
 for line in s[:offset].splitlines():
  m=re.match(r'#line (\d+)',line)
  logical=int(m.group(1)) if m else logical+1
 end=logical+old.count('\n')
 selector=f'#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_PERF_COUNTER_CONTROL_BRIDGES)\nextern int {name}({args});\n#else\n#line {logical}\n{old}#endif\n#line {end}\n'
 post=post.replace(old,selector,1)
 (P/f'{name}.original.C.inc').write_text(old)
 (P/f'{name}.paired-selector.C.inc').write_text(selector)
 rows.append({'name':name,'physical_line':physical,'logical_line':logical,'logical_next_line':end,'original':old,'selector':selector,'provider':call})
(P/'original.C.inc').write_text('\n'.join(x['original'] for x in rows))
(P/'paired-selectors.C.inc').write_text('\n'.join(x['selector'] for x in rows))
(P/'syscall.c.patch').write_text(''.join(difflib.unified_diff(s.splitlines(True),post.splitlines(True),fromfile='a/kernel/syscall.c',tofile='b/kernel/syscall.c')))
(P/'preimage.syscall.c').write_text(s)
(P/'postimage.syscall.c').write_text(post)
(P/'SOURCE-SLICES.json').write_text(json.dumps(rows,indent=2)+'\n')
abi=(R/'kernel/rust/abi.rs').read_text()
(P/'retained-abi-types.Rust.inc').write_text('\n'.join(re.findall(r'^pub type (?:CInt|CULong) = .*?;$',abi,re.M))+'\n')
pre=(R/'kernel/rust/syscall_policy.rs').read_text()
frag=(P/'selected-bridges.Rust.inc').read_text()
assert not any(re.search(r'pub (?:unsafe )?extern "C" fn '+x['name']+r'\b',pre) for x in rows)
(P/'syscall_policy.rs.patch').write_text(''.join(difflib.unified_diff(pre.splitlines(True),(pre+frag).splitlines(True),fromfile='a/kernel/rust/syscall_policy.rs',tofile='b/kernel/rust/syscall_policy.rs')))
cm=(R/'kernel/CMakeLists.txt').read_text()
old='list(APPEND RUST_KERNEL_CFG "--cfg" "f03_perf_alloc_bridges_selected_candidate")'
new=old+'\n\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_perf_counter_control_bridges_selected_candidate")'
oldc='COMPILE_DEFINITIONS MCKERNEL_RUST_F03_PERF_ALLOC_BRIDGES)'
newc='COMPILE_DEFINITIONS "MCKERNEL_RUST_F03_PERF_ALLOC_BRIDGES;MCKERNEL_RUST_F03_PERF_COUNTER_CONTROL_BRIDGES")'
assert cm.count(old)==cm.count(oldc)==1
cmpost=cm.replace(old,new).replace(oldc,newc)
(P/'CMakeLists.txt.proposal.patch').write_text(''.join(difflib.unified_diff(cm.splitlines(True),cmpost.splitlines(True),fromfile='a/kernel/CMakeLists.txt',tofile='b/kernel/CMakeLists.txt')))
inputs={}
for f in ['kernel/syscall.c','kernel/rust/syscall_policy.rs','kernel/rust/abi.rs','kernel/rust/x86_perfctr.rs','kernel/CMakeLists.txt','docs/verification/evidence/os-recovery-adoption-20261025-0254/CURRENT26EB-SELECTED-F03-F06-REMAINING-SOURCE-CURSOR.json']:
 b=(R/f).read_bytes();inputs[f]={'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b)}
(P/'EXACT-PREIMAGES.json').write_text(json.dumps(inputs,indent=2)+'\n')
