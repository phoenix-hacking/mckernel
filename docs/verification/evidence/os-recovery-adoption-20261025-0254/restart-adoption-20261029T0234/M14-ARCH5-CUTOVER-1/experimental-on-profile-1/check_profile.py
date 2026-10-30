"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing."""
from pathlib import Path
import json,hashlib,re
D=Path(__file__).parent
pre=(D/'preimage/kernel/CMakeLists.txt').read_text()
post=(D/'postimage/kernel/CMakeLists.txt').read_text()
profile=(D/'ARCH5-EXPERIMENTAL-ON.cmake').read_text()
assert post.replace('option(MCKERNEL_ARCH5_CUTOVER_CANDIDATE "Select reviewed ARCH5 source candidate" ON)','option(MCKERNEL_ARCH5_CUTOVER_CANDIDATE "Select reviewed ARCH5 source candidate" OFF)',1)==pre
cfgs=['f06_regset_defined_diagnostic_candidate','f06_signal_leaf_adapters_candidate','f06_signal_context_candidate','f06_do_signal_whole_candidate','f06_do_signal_reuse_qualified_context']
macros=['MCKERNEL_RUST_F06_REGSET_DEFINED_DIAGNOSTIC','MCKERNEL_RUST_F06_XRSTOR_LEAF','MCKERNEL_RUST_F06_BAD_FRAME_LEAF','MCKERNEL_RUST_F06_SIGNAL_CONTEXT','MCKERNEL_RUST_F06_DO_SIGNAL_WHOLE']
def pairs(text,cache):
 assert 'option(MCKERNEL_ARCH5_CUTOVER_CANDIDATE "Select reviewed ARCH5 source candidate" ON)' in text
 assert 'set(MCKERNEL_ARCH5_CUTOVER_CANDIDATE ON CACHE BOOL' in cache
 assert 'set(MCKERNEL_ARCH5_ABI_WITNESS OFF CACHE BOOL' in cache
 assert 'option(MCKERNEL_ARCH5_ABI_WITNESS "Emit compile-only ARCH5 ABI witness arrays" OFF)' in text
 for x in cfgs:assert text.count('"--cfg" "'+x+'"')==1
 for x in macros:assert text.count(x)==1
 assert 'if (MCKERNEL_ARCH5_ABI_WITNESS)' in text
 assert text.index('if (MCKERNEL_ARCH5_ABI_WITNESS)')<text.index('"--cfg" "arch5_abi_witness_candidate"')
pairs(post,profile)
mutations=[('missing_rust_cfg',post.replace('"--cfg" "f06_do_signal_whole_candidate"','',1),profile),('missing_C_selector',post.replace('MCKERNEL_RUST_F06_SIGNAL_CONTEXT;','',1),profile),('probe_accidentally_enabled',post,profile.replace('set(MCKERNEL_ARCH5_ABI_WITNESS OFF','set(MCKERNEL_ARCH5_ABI_WITNESS ON',1))]
for name,text,cache in mutations:
 try:pairs(text,cache)
 except AssertionError:continue
 raise AssertionError('mutation missed:'+name)
# Exact single-file patch application in memory.
source=pre.splitlines(True);patch=(D/'EXPERIMENTAL-ON.PRIVATE-NOT-APPLIED.patch').read_text().splitlines(True);i=2;cursor=0;result=[]
while i<len(patch):
 m=re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@',patch[i]);assert m
 start=int(m[1])-1;result+=source[cursor:start];cursor=start;i+=1
 while i<len(patch) and not patch[i].startswith('@@'):
  line=patch[i]
  if line[0] in ' -':assert source[cursor]==line[1:];cursor+=1
  if line[0] in ' +':result.append(line[1:])
  i+=1
result+=source[cursor:];assert ''.join(result)==post
mapping=json.loads((D/'COMPOSITOR-OVERLAY.json').read_text())
for row in mapping['files']:
 p=Path(row['source']['path']);assert hashlib.sha256(p.read_bytes()).hexdigest()==row['source']['sha256']
status=json.loads((D/'ARCH5-STATUS.json').read_text())
assert len(status['rows'])==5
for row in status['rows']:assert row['implemented'] and row['selected_in_candidate'] and not row['compiled'] and not row['validated']
report={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PASS_EXPERIMENTAL_PROFILE_SOURCE_ONLY','all_five_implemented_and_selected_in_candidate':True,'all_five_compiled_and_validated':False,'paired_C_selectors':5,'paired_Rust_cohort_cfgs':5,'ABI_probe_full_link_profile':'OFF; separate compile-only artifact only','seven_other_parent_targets_reused_exact':True,'single_line_CMake_change':True,'exact_patch_applicability':True,'mutations_rejected':[x[0]for x in mutations],'compiler_native_runtime':False}
(D/'SOURCE-CHECKS.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
