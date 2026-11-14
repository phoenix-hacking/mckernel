"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Mechanical private source compositor. No compiler/preprocessor/runtime operations.
"""
from pathlib import Path
import json,hashlib,difflib,re,os,subprocess
D=Path(__file__).resolve().parent;A=D.parent;B=A/'M14-CONVERSION-FIRST-LARGE-COMPOSITION-2';FIRST=A/'M14-CONVERSION-FIRST-COMPOSITION-1';ARCH=A/'M14-ARCH5-CUTOVER-1';NINE=A/'M14-PRIVATE-NINE-LEAF-BATCH-1';T=A/'M14-TERMINATION-FAMILY-COMPOSITION-1';C=A/'M14-REMAINING23-C-1';CC=C/'defined-callers-correction-1';QD=A/'M14-REMAINING23-D-1';DD=QD/'defined-callers-correction-1';QB=A/'M14-REMAINING23-B-1';QA=A/'M14-REMAINING23-A-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(p.read_text())
def write(n,v):(D/n).write_text(json.dumps(v,indent=2)+'\n')
log=[]
def merge(pre,post,current,name):
 a=pre.splitlines(True);b=post.splitlines(True);ops=difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes()
 for tag,i,j,k,l in reversed(ops):
  if tag=='equal':continue
  old=''.join(a[i:j]);new=''.join(b[k:l])
  # Existing line-neutral kfree selected declaration/fallback is authoritative;
  # both incoming insertions would duplicate it and perturb original origins.
  if name=='C-kill-free-interrupt' and 4670<i<4710:
   log.append(dict(input=name,kind='reuse_existing_line_neutral_kfree',old_lines=[i,j]));continue
  if name.startswith('D-') and name.endswith('-CMake') and not old and 'list(APPEND RUST_KERNEL_CFG' in new:
   anchor='\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_wakeup_writer_pair_candidate")\n'
   assert current.count(anchor)==1
   current=current.replace(anchor,new+anchor,1);log.append(dict(input=name,kind='Root_confirmed_inherited_Rust_cohort_anchor',old_lines=[i,j]));continue
  if name.startswith('D-') and name.endswith('-CMake') and not old and 'set_property(SOURCE' in new:
   lines=current.splitlines(True);indices=[q for q,line in enumerate(lines)if 'COMPILE_DEFINITIONS "MCKERNEL_RUST_F03_WAKEUP_WRITER_PAIR;'in line];assert len(indices)==1
   q=indices[0]-1;assert 'set_property(SOURCE' in lines[q]
   lines[q:q]=new.splitlines(True);current=''.join(lines);log.append(dict(input=name,kind='Root_confirmed_inherited_C_cohort_anchor',old_lines=[i,j]));continue
  if old and current.count(old)==1:
   current=current.replace(old,new,1)
  else:
   lines=current.splitlines(True);scores=[]
   for p in range(len(lines)+1):
    if old and lines[p:p+(j-i)]!=a[i:j]:continue
    before=0;after=0
    for t in range(1,min(16,i,p)+1):
     if lines[p-t]!=a[i-t]:break
     before=t
    for t in range(min(16,len(a)-j,len(lines)-p-(j-i))):
     if lines[p+(j-i)+t]!=a[j+t]:break
     after=t+1
    score=before+after
    if score>=3:scores.append((score,p))
   assert scores,(name,'insertion anchor',i)
   top=max(s[0]for s in scores);pos=[p for score,p in scores if score==top];assert len(pos)==1,(name,'ambiguous anchor',i,pos)
   p=pos[0];lines[p:p+(j-i)]=b[k:l];current=''.join(lines)
  log.append(dict(input=name,kind=tag,old_lines=[i,j],new_lines=[k,l]))
 return current

def main():
 assert not (D/'SOURCE-READY.json').exists()
 fm=read(B/'FILEMAP.SOURCE-ONLY.json');rows={r['target']:dict(r)for r in fm['files']};out={};pre={}
 for n,r in rows.items():
  assert ref(Path(r['source']['path']))==r['source']
  if not r['reused_leaf']:out[n]=Path(r['source']['path']).read_text();pre[n]=Path(r['frozen119_preimage']['path']).read_text()
 # ARCH5 supplied coherent8target overlay includes corrected line placement and
 # SIGTRAP; earlier F06 fragments must not be replayed.
 for r in read(ARCH/'FILEMAP.json'):
  n=r['target'];p=ARCH/'postimage'/n;assert ref(p)['sha256']==r['postimage_sha256']
  if r['preimage_sha256']is None:rows[n]=dict(target=n,source=ref(p),frozen119_preimage=None,reused_leaf=True)
  else:
   q=ARCH/'preimage'/n;assert ref(q)['sha256']==r['preimage_sha256']
   if n in out:assert hashlib.sha256(out[n].encode()).hexdigest()==r['preimage_sha256']
   else:pre[n]=q.read_text()
   out[n]=p.read_text()
 # C patch A only has three narrowly rebased bridge/linkage hunks. Apply to
 # private current C after isolating git discovery; assert actual bytes changed.
 n='kernel/syscall.c';p=D/'apply-A'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(out[n]);patch=QA/'bridge-selection-first20.patch';assert ref(patch)['sha256']=='92080c09f79cc09cd62af782a89ef9be89bea006b3936353d34e611c0d7283a5'
 argv=['git','apply','--no-index',str(patch)];r=subprocess.run(argv,cwd=D/'apply-A',env=dict(os.environ,GIT_CEILING_DIRECTORIES=str(D)),capture_output=True,text=True);assert r.returncode==0,r.stderr;assert p.read_text()!=out[n];out[n]=p.read_text()
 # Remaining changed C bodies do not overlap. Exact incoming insertions are
 # mechanically anchored to original surrounding source, no line math invented.
 specs=[(NINE,T,'C-termination-family'),(T,C,'C-kill-free-interrupt'),(C,CC,'C-approved-interrupt-logger'),(FIRST,DD,'D-approved-signal'),(FIRST,DD/'perf-abi-correction-1','D-perf'),(FIRST,QD/'credential-pair-1','D-credentials')]
 for base,folder,label in specs:
  out[n]=merge((base/'postimage'/n).read_text(),(folder/'postimage'/n).read_text(),out[n],label)
 # Reuse exact module tails, omitting the one already included kfree module.
 policy='kernel/rust/syscall_policy.rs'
 for base,folder,label in specs:
  aux=folder if (folder/'postimage'/policy).exists()else QD
  a=(base/'postimage'/policy).read_text();b=(aux/'postimage'/policy).read_text();assert b.startswith(a),label;tail=b[len(a):]
  blocks=re.split(r'(?=\n// Functional McKernel)',tail)
  for block in blocks:
   if not block:continue
   if 'mod syscall_ptrace_detach_kfree;'in block:
    assert out[policy].count('mod syscall_ptrace_detach_kfree;')==1;continue
   out[policy]+=block
  for leaf in (folder/'postimage/kernel/rust').iterdir():
   if leaf.name=='syscall_policy.rs':continue
   target='kernel/rust/'+leaf.name
   if target in rows:assert rows[target]['source']['sha256']==ref(leaf)['sha256'],target
   else:rows[target]=dict(target=target,source=ref(leaf),frozen119_preimage=None,reused_leaf=True)
 # Independent bridge leaf/module supplied as fragment, with selected ABI exact.
 leaf=QA/'syscall_execveat_bridge.PRIVATE.rs.inc';target='kernel/rust/f03_execveat_bridge_candidate.rs';rows[target]=dict(target=target,source=ref(leaf),frozen119_preimage=None,reused_leaf=True)
 out[policy]+='\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(f03_execveat_bridge_candidate, target_arch = "x86_64"))]\n#[path = "f03_execveat_bridge_candidate.rs"]\nmod f03_execveat_bridge_candidate;\n'
 # Approved exec request-field correction remains exact but whole selector OFF.
 out[policy]+='\n'+(QA/'defined-callers-correction-1/do_execveat.defined-arity.PRIVATE.rs.inc').read_text()
 write('DRAFT-MERGED-STATE.json',dict(out=out,pre=pre,rows=rows,log=log))
 # Merge supplied CMake edits, dependencies are de-duplicated by target.
 cm='kernel/CMakeLists.txt'
 for base,folder,label in [(B,QB,'B-whole-wiring')]+specs:
  aux=folder if (folder/'postimage'/cm).exists()else QD
  out[cm]=merge((base/'postimage'/cm).read_text(),(aux/'postimage'/cm).read_text(),out[cm],label+'-CMake')
 # The existing kfree dependency occurs once in base and QueueC.
 dep='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_ptrace_detach_kfree.rs"\n'
 assert out[cm].count(dep)==2;out[cm]=out[cm].replace(dep,'',1)
 anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_policy.rs"\n';assert out[cm].count(anchor)==1;out[cm]=out[cm].replace(anchor,anchor+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_execveat_bridge_candidate.rs"\n')
 # Bridge paired opt-in in existing supported cohort, OFF by default.
 # C option is appended in the later C property cohort, after the baseline
 # set_source_files_properties assignment; putting it in early Rust cfg setup
 # would be overwritten. Exact existing C cohort anchor is Root confirmed.
 cl=out[cm].splitlines(True);ids=[i for i,l in enumerate(cl)if 'COMPILE_DEFINITIONS "MCKERNEL_RUST_F03_WAKEUP_WRITER_PAIR;'in l];assert len(ids)==1
 pos=ids[0]-1;cl[pos:pos]='\t\t\tif (MCKERNEL_F03_EXECVEAT_BRIDGE_EXPERIMENTAL)\n\t\t\t\tset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS MCKERNEL_RUST_F03_EXECVEAT_BRIDGE)\n\t\t\tendif()\n'.splitlines(True);out[cm]=''.join(cl)
 anchor='\t\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n';assert out[cm].count(anchor)==1;out[cm]=out[cm].replace(anchor,anchor+'\t\t\t\tif (MCKERNEL_F03_EXECVEAT_BRIDGE_EXPERIMENTAL)\n\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_execveat_bridge_candidate")\n\t\t\t\tendif()\n')
 patch=''
 for n,text in out.items():
  p=D/'postimage'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text);q=D/'preimage'/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(pre[n]);rows[n]=dict(target=n,source=ref(p),frozen119_preimage=ref(q),reused_leaf=False)
 for n,r in rows.items():
  old=''if r['reused_leaf']else pre[n];text=Path(r['source']['path']).read_text();patch+=''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile='/dev/null'if r['reused_leaf']else 'a/'+n,tofile='b/'+n))
 f=D/'COMBINED.PRIVATE-NOT-APPLIED.patch';f.write_text(patch);write('FILEMAP.SOURCE-ONLY.json',dict(files=list(rows.values()),patch=ref(f),status='DRAFT_PRIVATE_COMBINED_SOURCE_NOT_EXECUTION'));write('MERGE-LOG.json',log);print(json.dumps(dict(patch=ref(f),targets=len(rows))))
if __name__=='__main__':main()
