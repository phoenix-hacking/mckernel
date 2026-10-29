"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Sole private source compositor. Exact existing leaves reused by BYTEref, not copied.
No canonical/compile/native/guard/process/cleanup/controller operation.
"""
from pathlib import Path
import json,re,hashlib,difflib
D=Path(__file__).resolve().parent;A=D.parent;TEN=A/'M14-PRIVATE-TEN-LEAF-BATCH-1';NINE=A/'M14-PRIVATE-NINE-LEAF-BATCH-1';CTX=A/'M14-UPGRADED-F03-CONTEXT-FORWARD-PAIR-1';KF=A/'M14-UPGRADED-F03-PTRACE-KFREE-1/Rust-owned-metadata-correction-1';TERM=A/'M14-UPGRADED-F03-EXIT-GROUP-TERMINATE-1';IRQ=A/'M14-UPGRADED-F03-WAKEUP-WRITER-PAIR-1';RAW=A/'M14-UPGRADED-F03-RAW-CALLBACK-QUEUE-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(p.read_text())
def replace(s,old,new):
 assert s.count(old)==1,old[:90];return s.replace(old,new)
def delta_tail(folder,base,name):
 pre=(base/'postimage'/name).read_text();post=(folder/'postimage'/name).read_text();assert post.startswith(pre),str(folder);return post[len(pre):]
def main():
 assert not (D/'FILEMAP.SOURCE-ONLY.json').exists()
 tm=read(TEN/'SOURCE-CHECKS.json');cm=read(CTX/'SOURCE-CHECKS.json');assert ref(TEN/'SOURCE-READY.json')['sha256'].startswith('958afc6');assert ref(KF/'RUST-METADATA.PRIVATE-NOT-APPLIED.patch')['sha256'].startswith('7777f386')
 output={};pre={};leafrefs={};inputs={'ten':ref(TEN/'SOURCE-READY.json'),'context':ref(CTX/'SOURCE-READY.json'),'kfree_Rust_owned':ref(KF/'SOURCE-CHECKS.json'),'exitgroup':ref(TERM/'SOURCE-CHECKS.json'),'wakeup_IRQ_pair':ref(IRQ/'SOURCE-READY.json')}
 for r in tm['files']:
  name=r['proposed_path'];source=TEN/'postimage'/name;assert ref(source)==r['postimage']
  if r['preimage']is not None:pre[name]=Path(r['preimage']['path']).read_text();output[name]=source.read_text()
  else:leafrefs[name]=ref(source)
 # Full context pair delta was already composed on ten; no source algorithm change.
 for name in ['kernel/syscall.c','kernel/rust/syscall_policy.rs','kernel/CMakeLists.txt']:
  r=next(x for x in cm['files']if x['path']==name);assert ref(CTX/'postimage'/name)==r['postimage'];output[name]=(CTX/'postimage'/name).read_text()
 leafrefs['kernel/rust/f03_context_forward_pair.rs']=ref(CTX/'postimage/kernel/rust/f03_context_forward_pair.rs')
 c=output['kernel/syscall.c'];wiring=[]
 specs=[(KF,'ptrace_detach_kfree_bridge','static void\nptrace_detach_kfree_bridge(void *ptr)\n{\n\tkfree_tracked(ptr, __FILE__, __LINE__);\n}\n','extern void ptrace_detach_kfree_bridge(void *ptr);','#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__) && defined(MCKERNEL_RUST_F03_PTRACE_KFREE_PROFILE_119)','syscall_ptrace_detach_kfree.rs'),(TERM,'exit_group_terminate_bridge','void\nexit_group_terminate_bridge(int status, int group)\n{\n\tterminate(status, group);\n}\n','extern void exit_group_terminate_bridge(int status, int group);','#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)','syscall_exit_group_terminate.rs')]
 for sub,symbol,old,proto,selector,leaf in specs:
  # Minimal neutral wrapper retains fallback tokens. For kfree specifically its
  # __LINE__ call remains the exact original fourth physical line (offset3).
  compact=' '.join(x.strip()for x in old.splitlines());new='\n'.join([selector,proto,'#else',compact,'#endif'])+'\n';assert old.count('\n')==new.count('\n')==5;c=replace(c,old,new);wiring.append(dict(symbol=symbol,old=old,new=new,source_input=str(sub),line_neutral=True,body_reused_exact=True));leafrefs['kernel/rust/'+leaf]=ref(sub/'postimage/kernel/rust'/leaf)
 for action in ['lock','unlock']:
  symbol='ptrace_wakeup_update_'+action+'_bridge';old=f'static void\n{symbol}(unsigned long lock_addr, void *node)\n{{\n\tmcs_rwlock_writer_{action}((struct mcs_rwlock_lock *)lock_addr,\n\t\t\t(struct mcs_rwlock_node_irqsave *)node);\n}}';oldsource=(IRQ/'preimage/kernel/syscall.c').read_text();newsource=(IRQ/'postimage/kernel/syscall.c').read_text();assert oldsource.count(old)==1
  start=newsource.index('#if defined(MCKERNEL_RUST_F03_WAKEUP_WRITER_PAIR)\nextern void '+symbol);stop=newsource.index('#endif',start)+len('#endif');new=newsource[start:stop];assert old.count('\n')==new.count('\n');c=replace(c,old,new);wiring.append(dict(symbol=symbol,old=old,new=new,source_input=str(IRQ),line_neutral=True,body_reused_exact=True))
 leafrefs['kernel/rust/f03_wakeup_writer_pair.rs']=ref(IRQ/'postimage/kernel/rust/f03_wakeup_writer_pair.rs')
 rawspecs=[('wakeup','ptrace_detach_wakeup_bridge','static void\nptrace_detach_wakeup_bridge(void *thread, int valid_states)\n{\n\tsched_wakeup_thread((struct thread *)thread, valid_states);\n}\n','extern void ptrace_detach_wakeup_bridge(void *thread, int valid_states);','syscall_ptrace_detach_wakeup.rs'),('terminate_mcexec','terminate_mcexec_do_syscall_bridge','static long\nterminate_mcexec_do_syscall_bridge(struct syscall_request *request, int cpu)\n{\n\treturn do_syscall(request, cpu);\n}\n','extern long terminate_mcexec_do_syscall_bridge(struct syscall_request *request, int cpu);','syscall_terminate_mcexec_forward.rs'),('perf_open','perf_event_open_do_syscall_bridge','static long\nperf_event_open_do_syscall_bridge(struct syscall_request *request, int cpu)\n{\n\treturn do_syscall(request, cpu);\n}\n','extern long perf_event_open_do_syscall_bridge(struct syscall_request *request, int cpu);','syscall_perf_open_forward.rs')]
 for sub,symbol,old,proto,leaf in rawspecs:
  folder=RAW/sub;ready=read(folder/'SOURCE-READY.json');assert ref(Path(ready['leaf']['path']))==ready['leaf'];inputs['raw_'+sub]=ref(folder/'SOURCE-READY.json');compact=' '.join(x.strip()for x in old.splitlines());new='\n'.join(['#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)',proto,'#else',compact,'#endif'])+'\n';assert old.count('\n')==new.count('\n')==5;c=replace(c,old,new);wiring.append(dict(symbol=symbol,old=old,new=new,source_input=str(folder),line_neutral=True,body_reused_exact=True));leafrefs['kernel/rust/'+leaf]=ready['leaf']
 output['kernel/syscall.c']=c
 policy='kernel/rust/syscall_policy.rs'
 for folder,base in [(KF,NINE),(TERM,NINE)]+[(RAW/s,NINE)for s,*_ in rawspecs]:output[policy]+=delta_tail(folder,base,policy)
 lib='kernel/rust/lib.rs';base=(IRQ/'preimage'/lib).read_text();post=(IRQ/'postimage'/lib).read_text();assert post.startswith(base);output[lib]+=post[len(base):]
 cmake=output['kernel/CMakeLists.txt']
 for name in leafrefs:
  if name in [r['proposed_path']for r in tm['files']]or name.endswith('f03_context_forward_pair.rs'):continue
  dep='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/'+name[len('kernel/'):]+'"\n';anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_policy.rs"\n';assert dep not in cmake;cmake=replace(cmake,anchor,anchor+dep)
 anchor='\t\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n';cmake=replace(cmake,anchor,anchor+'\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_wakeup_writer_pair_candidate")\n');anchor='COMPILE_DEFINITIONS "MCKERNEL_RUST_F03_CONTEXT_FORWARD_PAIR;';cmake=replace(cmake,anchor,'COMPILE_DEFINITIONS "MCKERNEL_RUST_F03_WAKEUP_WRITER_PAIR;MCKERNEL_RUST_F03_CONTEXT_FORWARD_PAIR;');output['kernel/CMakeLists.txt']=cmake
 # Keep kfree profile and origin flags deliberately OFF; no activation inferred.
 assert 'list(APPEND RUST_KERNEL_CFG "--cfg" "f03_ptrace_kfree_profile_119")'not in cmake and 'MCKERNEL_RUST_F03_PTRACE_KFREE_PROFILE_119'not in cmake
 rows=[];patch=''
 for name,text in output.items():
  path=D/'postimage'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text);q=D/'preimage'/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(pre[name]);rows.append(dict(target=name,source=ref(path),frozen119_preimage=ref(q),reused_leaf=False));patch+=''.join(difflib.unified_diff(pre[name].splitlines(True),text.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
 for name,r in leafrefs.items():
  rows.append(dict(target=name,source=r,frozen119_preimage=None,reused_leaf=True));patch+=''.join(difflib.unified_diff([],Path(r['path']).read_text().splitlines(True),fromfile='/dev/null',tofile='b/'+name))
 p=D/'CONVERSION-FIRST.PRIVATE-NOT-APPLIED.patch';p.write_text(patch)
 for name,value in [('INPUT-CANDIDATES.json',inputs),('C-WIRING-DELTAS.json',wiring),('FILEMAP.SOURCE-ONLY.json',dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PRIVATE_CONVERSION_FIRST_COMPOSITION_ONLY',files=rows,patch=ref(p),kfree_activation='OFF_AWAIT_SOURCE_FLAGS_AND_PREPROCESS_BINDING',leaf_bodies_copied=False,runtime_authority=None))]:(D/name).write_text(json.dumps(value,indent=2)+'\n')
 print(json.dumps(dict(patch=ref(p),source_targets=len(rows),reused_external_leaf_refs=len(leafrefs))))
if __name__=='__main__':main()
