"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private fixed source composition. No compiler, preprocessor, host or native work.
"""
from pathlib import Path
import difflib,hashlib,json
D=Path(__file__).resolve().parent;A=D.parent;R=Path('/home/holden/mckernel');FOUR=A/'M14-PRIVATE-FOUR-LOGGER-BATCH-1';LOCK=A/'M14-PRIVATE-PTRACE-CLONE-LOCK-BRIDGE-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def replace(s,a,b):
 assert s.count(a)==1;return s.replace(a,b)
def main():
 assert not (D/'FILEMAP.SOURCE-ONLY.json').exists()
 fm=json.loads((FOUR/'FILEMAP.SOURCE-ONLY.json').read_text());lr=json.loads((LOCK/'SOURCE-READY.json').read_text());assert fm['patch']['sha256']=='bfa62f4ef88317ee49c3e116fb37c588e4b12939db6e33cd4184f2eaae0951b5';assert lr['patch']['sha256']=='e731d058ffcec16508dd37c2b732943a9455f428bbcd91773981c4c5ff4842a2'
 for r in (fm['patch'],lr['patch'],lr['source']):assert ref(Path(r['path']))==r
 before={};out={}
 for row in fm['files']:
  name=row['proposed_path'];assert ref(Path(row['postimage']['path']))==row['postimage'];out[name]=Path(row['postimage']['path']).read_text()
  if row['canonical_preimage'] is not None:
   assert ref(R/name)==row['canonical_preimage'];before[name]=(R/name).read_text()
 # The original lib.rs and lock leaf are the additional private inputs.
 assert not (R/'kernel/rust/ptrace_clone_noirq.rs').exists();before['kernel/rust/lib.rs']=(R/'kernel/rust/lib.rs').read_text();out['kernel/rust/lib.rs']=replace(before['kernel/rust/lib.rs'],'mod lock_helpers;\n','mod lock_helpers;\n#[cfg(all(f03_ptrace_clone_noirq_candidate, target_arch = "x86_64"))]\nmod ptrace_clone_noirq;\n')
 out['kernel/rust/ptrace_clone_noirq.rs']=Path(lr['source']['path']).read_text()
 name='kernel/CMakeLists.txt';s=out[name];s=replace(s,'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/lock_helpers.rs"\n','\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/lock_helpers.rs"\n\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/ptrace_clone_noirq.rs"\n');s=replace(s,'\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_prlimit_body_candidate")','\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_ptrace_clone_noirq_candidate")\n\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_prlimit_body_candidate")');s=replace(s,'COMPILE_DEFINITIONS "MCKERNEL_RUST_F03_PERF_ATTR_CALLBACKS;MCKERNEL_RUST_F03_PRLIMIT_BODY;','COMPILE_DEFINITIONS "MCKERNEL_RUST_F03_PTRACE_CLONE_NOIRQ;MCKERNEL_RUST_F03_PERF_ATTR_CALLBACKS;MCKERNEL_RUST_F03_PRLIMIT_BODY;');out[name]=s
 old='''static void
ptrace_report_clone_noirq_lock_bridge(unsigned long lock_addr, void *node)
{
\tmcs_rwlock_writer_lock_noirq((struct mcs_rwlock_lock *)lock_addr,
\t\t\t(struct mcs_rwlock_node *)node);
}

static void
ptrace_report_clone_noirq_unlock_bridge(unsigned long lock_addr, void *node)
{
\tmcs_rwlock_writer_unlock_noirq((struct mcs_rwlock_lock *)lock_addr,
\t\t\t(struct mcs_rwlock_node *)node);
}'''
 pieces=old.split('\n\n');assert len(pieces)==2
 compact=[' '.join(x.strip() for x in v.splitlines()) for v in pieces]
 new='\n'.join(['#if defined(MCKERNEL_RUST_F03_PTRACE_CLONE_NOIRQ)','extern void ptrace_report_clone_noirq_lock_bridge(unsigned long lock_addr, void *node);','extern void ptrace_report_clone_noirq_unlock_bridge(unsigned long lock_addr, void *node);','#else',*compact,'','','','','','','#endif'])
 assert old.count('\n')==new.count('\n')==12
 c=out['kernel/syscall.c'];i=c.index(old);out['kernel/syscall.c']=replace(c,old,new);line=c.count('\n',0,i)+1
 rows=[];patch=[]
 for name,text in out.items():
  p=D/'postimage'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);oldtext=before.get(name,'')
  if name in before:
   q=D/'preimage'/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(oldtext)
  patch.extend(difflib.unified_diff(oldtext.splitlines(True),text.splitlines(True),fromfile='a/'+name if name in before else '/dev/null',tofile='b/'+name))
  rows.append(dict(proposed_path=name,postimage=ref(p),canonical_preimage=ref(R/name) if name in before else None,reused_leaf_exact=name.startswith('kernel/rust/syscall_') and name!='kernel/rust/syscall_policy.rs' or name=='kernel/rust/ptrace_clone_noirq.rs'))
 patchfile=D/'LOGGER-LOCK-BATCH.PRIVATE-NOT-APPLIED.patch';patchfile.write_text(''.join(patch))
 (D/'FILEMAP.SOURCE-ONLY.json').write_text(json.dumps(dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PRIVATE_COMPOSED_SOURCE_ONLY',runtime_authority=None,four_logger=ref(FOUR/'SOURCE_READY.json'),lock_pair=ref(LOCK/'SOURCE-READY.json'),four_logger_filemap=ref(FOUR/'FILEMAP.SOURCE-ONLY.json'),files=rows,patch=ref(patchfile),lock_first_line=line,lock_lines=13,prior_packets_unchanged=True),indent=2)+'\n');print(json.dumps(ref(patchfile)))
if __name__=='__main__':main()
