"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
One private coherent eight-leaf source composition; no compiler/runtime work.
"""
from pathlib import Path
import json,hashlib,difflib
D=Path(__file__).resolve().parent;A=D.parent;ROOT=Path('/home/holden/mckernel');B=A/'M14-PRIVATE-SEVEN-LEAF-BATCH-1/line-preserving-composition-correction-1';N=A/'M14-PRIVATE-NEXT-GENERIC-BODY-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def main():
 assert not (D/'FILEMAP.SOURCE-ONLY.json').exists();br=json.loads((B/'SOURCE-READY.json').read_text());nr=json.loads((N/'SOURCE-READY.json').read_text());assert br['patch']['sha256']=='22feacf6221bd16c9b08a41e30e2c91f1fe5f5427009e8e5455dda9fea965634';assert nr['files']['MUNMAP-CLEAR-HOST.PRIVATE-NOT-APPLIED.patch']['sha256']=='02d8f1c0e4ee89f56a78849eba914f36663d78352490f1dc9e293de3874f036b'
 before={};post={};m=json.loads((B/'FILEMAP.SOURCE-ONLY.json').read_text());nm=json.loads((N/'FILEMAP.SOURCE-ONLY.json').read_text())
 for r in m['files']:
  f=r['proposed_path'];assert ref(Path(r['postimage']['path']))==r['postimage'];post[f]=Path(r['postimage']['path']).read_text()
  if r['canonical_preimage']is not None:assert ref(ROOT/f)==r['canonical_preimage'];before[f]=(ROOT/f).read_text()
 for f,r in nm['preimages'].items():assert ref(B/'preimage'/f)['sha256']==r['sha256']
 f='kernel/syscall.c';old=(N/'preimage'/f).read_text();new=(N/'postimage'/f).read_text();start=old.index('static long\ndo_munmap_clear_host_bridge(');end=old.index('\nstatic int\ndo_munmap_set_host_bridge',start);oldpart=old[start:end];newstart=new.index('#if defined(MCKERNEL_RUST_F03_LEAF_CALLBACKS) && defined(__x86_64__)\nextern long do_munmap_clear_host_bridge');newend=new.index('\nstatic int\ndo_munmap_set_host_bridge',newstart);newpart=new[newstart:newend];assert oldpart.count('\n')==newpart.count('\n')and post[f].count(oldpart)==1;post[f]=post[f].replace(oldpart,newpart)
 f='kernel/rust/syscall_policy.rs';base=(N/'preimage'/f).read_text();new=(N/'postimage'/f).read_text();assert new.startswith(base);extra=new[len(base):];assert post[f].startswith(base);post[f]+=extra
 f='kernel/CMakeLists.txt';anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_policy.rs"\n';dep='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_munmap_clear_host_forward.rs"\n';assert post[f].count(anchor)==1;assert (N/'preimage'/f).read_text().replace(anchor,anchor+dep)==(N/'postimage'/f).read_text();post[f]=post[f].replace(anchor,anchor+dep)
 f='kernel/rust/syscall_munmap_clear_host_forward.rs';post[f]=(N/'postimage'/f).read_text();assert ref(N/'postimage'/f)==nr['leaf']
 rows=[];patch=''
 for f,text in post.items():
  p=D/'postimage'/f;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
  if f in before:q=D/'preimage'/f;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(before[f])
  patch+=''.join(difflib.unified_diff(before.get(f,'').splitlines(True),text.splitlines(True),fromfile='a/'+f if f in before else '/dev/null',tofile='b/'+f));rows.append(dict(proposed_path=f,postimage=ref(p),canonical_preimage=ref(ROOT/f)if f in before else None,reused_leaf_exact=f.endswith('.rs')and f not in ['kernel/rust/syscall_policy.rs','kernel/rust/lib.rs']))
 pf=D/'EIGHT-LEAF-BATCH.PRIVATE-NOT-APPLIED.patch';pf.write_text(patch);(D/'FILEMAP.SOURCE-ONLY.json').write_text(json.dumps(dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PRIVATE_EIGHT_LEAF_SOURCE_COMPOSITION_ONLY',seven_leaf=ref(B/'SOURCE-READY.json'),new_forwarding_body=ref(N/'SOURCE-READY.json'),files=rows,patch=ref(pf),runtime_authority=None),indent=2)+'\n');print(json.dumps(ref(pf)))
if __name__=='__main__':main()
