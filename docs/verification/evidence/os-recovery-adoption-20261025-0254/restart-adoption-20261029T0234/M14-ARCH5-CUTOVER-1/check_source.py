"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Source-only checks, never a compiler/native or provider execution.
"""
from pathlib import Path
import hashlib,json,re
D=Path(__file__).parent
A=D.parent
files=json.loads((D/'FILEMAP.json').read_text())
def load(kind,target):return (D/kind/target).read_text()
for row in files:
 assert hashlib.sha256((D/'postimage'/row['target']).read_bytes()).hexdigest()==row['postimage_sha256']
 if row['preimage_sha256']:assert hashlib.sha256((D/'preimage'/row['target']).read_bytes()).hexdigest()==row['preimage_sha256']
policy=load('postimage','kernel/rust/syscall_policy.rs')
placed=(A/'M14-F06-CONTEXT-DOSIGNAL-COMPOSITION-1/line-neutral-placement-correction-1/bounded-correction-1/postimage/kernel/rust/syscall_policy.rs').read_text()
assert policy.startswith(placed)
def sites(s,kind):return [(i,m.start(),line) for i,line in enumerate(s.splitlines(),1) for m in re.finditer(r'\b'+kind+r'!\s*\(',line)]
for k in ['line','file','column']:assert sites(policy,k)==sites(placed,k)
assert len(sites(policy,'line'))==47
# Malformed import placement must be rejected by exact coordinates.
mutated=policy.replace('mod f06_signal_context_candidate {','mod f06_signal_context_candidate {\n',1)
assert sites(mutated,'line')!=sites(policy,'line')
# Reused bodies/approved constructor not reimplemented.
for target,source in [('kernel/rust/syscall_regset_defined_logger.rs','regset-defined-1'),('kernel/rust/syscall_signal_leaf_adapters.rs','signal-leaves-reuse-1')]:
 assert (D/'postimage'/target).read_bytes()==(A/'M14-F06-CONVERSION-SOURCE-QUEUE-1'/source/'postimage'/target).read_bytes()
provider=load('postimage','kernel/rust/x86_cpu_helpers.rs')
assert provider.replace('pub(crate) unsafe fn x86_restore_xstate','unsafe fn x86_restore_xstate',1)==load('preimage','kernel/rust/x86_cpu_helpers.rs')
# C source logical location macros retain original identity despite selector gates.
def csites(text):
 n=1;result=[]
 for line in text.splitlines():
  match=re.match(r'#line (\d+)',line)
  if match:n=int(match[1]);continue
  if 'dkprintf(' in line or '__LINE__' in line:result.append((n,line))
  n+=1
 return result
arch=load('postimage','arch/x86_64/kernel/syscall.c')
assert csites(arch)==csites(load('preimage','arch/x86_64/kernel/syscall.c'))
cm=load('postimage','kernel/CMakeLists.txt')
flags=['f06_regset_defined_diagnostic_candidate','f06_signal_leaf_adapters_candidate','f06_signal_context_candidate','f06_do_signal_whole_candidate','f06_do_signal_reuse_qualified_context']
macros=['MCKERNEL_RUST_F06_REGSET_DEFINED_DIAGNOSTIC','MCKERNEL_RUST_F06_XRSTOR_LEAF','MCKERNEL_RUST_F06_BAD_FRAME_LEAF','MCKERNEL_RUST_F06_SIGNAL_CONTEXT','MCKERNEL_RUST_F06_DO_SIGNAL_WHOLE']
for cfg in flags:assert cm.count('"--cfg" "'+cfg+'"')==1
for macro in macros:assert cm.count(macro)==1 and macro in arch
assert 'option(MCKERNEL_ARCH5_CUTOVER_CANDIDATE "Select reviewed ARCH5 source candidate" OFF)' in cm
assert 'option(MCKERNEL_ARCH5_ABI_WITNESS "Emit compile-only ARCH5 ABI witness arrays" OFF)' in cm
assert cm.index('set(MCKERNEL_HOST_IRQ_ABI')<cm.index('if (MCKERNEL_ARCH5_CUTOVER_CANDIDATE AND')
assert 'if (MCKERNEL_ARCH5_ABI_WITNESS AND NOT MCKERNEL_ARCH5_CUTOVER_CANDIDATE)' in cm
# Exact five C fallback bodies remain present when their macros are OFF.
for name in ['arch_rt_sigreturn_xrstor_bridge','arch_native_signal_bad_frame_bridge','arch_rt_sigreturn_context_bridge','do_signal','arch_ptrace_regset_log_bridge']:
 assert name+'(' in arch or name+' (' in arch
 assert name in load('postimage','arch/x86_64/kernel/include/arch5-abi-witness.inc')
 assert name in load('postimage','kernel/rust/arch5_abi_witness.rs')
# Actual-expression witness sources: identical ordered keys, no executed layout claim.
geometry=json.loads((D/'ABI-GEOMETRY-KEYS.json').read_text())
assert len(geometry)==61 and len({x['key'] for x in geometry})==61
cw=load('postimage','arch/x86_64/kernel/include/arch5-abi-witness.inc');rw=load('postimage','kernel/rust/arch5_abi_witness.rs')
for i,row in enumerate(geometry):
 assert row['C']+', /* '+str(i)+' '+row['key']+' */' in cw
 assert '('+row['Rust']+') as u64, // '+str(i)+' '+row['key'] in rw
assert 'MCKERNEL_ARCH5_ABI_WITNESS' in arch and '.arch5_abi_c' in cw and '.arch5_abi_rust' in rw
# Apply all saved unified file hunks in memory against exact retained preimages.
patch=(D/'ARCH5.PRIVATE-NOT-APPLIED.patch').read_text().splitlines(True)
i=0;applied=[]
while i<len(patch):
 assert patch[i].startswith('--- ');oldname=patch[i][4:].strip();i+=1
 assert patch[i].startswith('+++ b/');target=patch[i][6:].strip();i+=1
 src=[] if oldname=='/dev/null' else load('preimage',target).splitlines(True)
 result=[];cursor=0
 while i<len(patch) and not patch[i].startswith('--- '):
  match=re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@',patch[i]);assert match,patch[i]
  start=max(0,int(match[1])-1);assert start>=cursor
  result+=src[cursor:start];cursor=start;i+=1
  while i<len(patch) and not patch[i].startswith(('@@','--- ')):
   line=patch[i]
   if line[0] in ' -':assert src[cursor]==line[1:];cursor+=1
   if line[0] in ' +':result.append(line[1:])
   i+=1
 result+=src[cursor:];assert ''.join(result)==load('postimage',target);applied.append(target)
assert set(applied)=={x['target'] for x in files}
report={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing.','status':'PASS_SOURCE_ONLY','checks':{'exact_retained_line_file_macro_sites':47,'bad_import_placement_rejected':True,'both_leaf_sources_reused_byte_exact':True,'provider_visibility_only':True,'C_logical_dkprintf_and_LINE_identity':True,'paired_arch5_C_and_Rust_selectors':True,'fallback_bodies_retained_and_default_option_OFF':True,'all_five_actual_function_signature_witnesses':True,'paired_actual_expression_geometry_slots':61,'private_multi_file_patch_exact_applicability':len(applied)},'compiler':0,'native':0,'actual_ABI_geometry_result':None,'metadata389_artifact_result':None,'limitations':'Witness source and selector consistency only; Root must run admitted actual compiler/layout/link/codegen/provider and native checks before acceptance.'}
(D/'SOURCE-CHECKS.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
