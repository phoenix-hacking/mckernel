"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private fixed seven-leaf source composition; no compiler/preprocessor/runtime.
"""
from pathlib import Path
import difflib,hashlib,json
D=Path(__file__).resolve().parent;A=D.parent;ROOT=Path('/home/holden/mckernel');B=A/'M14-PRIVATE-SIX-LEAF-BATCH-1';U=A/'M14-PRIVATE-EXIT-GROUP-CURRENT-PID-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def replace(text,a,b):
 assert text.count(a)==1;return text.replace(a,b)
def main():
 assert not (D/'FILEMAP.SOURCE-ONLY.json').exists()
 br=json.loads((B/'SOURCE-READY.json').read_text());ur=json.loads((U/'SOURCE-READY.json').read_text());assert br['patch']['sha256']=='606cbbd20a318a7b0693151efafe4d4cb83d246aed0e79a357c5cd546f2e8dd9';assert ur['files']['CURRENT-PID.PRIVATE-NOT-APPLIED.patch']['sha256']=='cc05835e38bfb3ce02d58908db0f19c480d55093557786ca936a28c5dab3c92e'
 for r in [br['filemap'],br['patch'],ur['files']['FILEMAP.SOURCE-ONLY.json'],ur['leaf']]:assert ref(Path(r['path']))==r
 bm=json.loads((B/'FILEMAP.SOURCE-ONLY.json').read_text());um=json.loads((U/'FILEMAP.SOURCE-ONLY.json').read_text());before={};out={}
 for row in bm['files']:
  name=row['proposed_path'];assert ref(Path(row['postimage']['path']))==row['postimage'];out[name]=Path(row['postimage']['path']).read_text()
  if row['canonical_preimage']is not None:
   assert ref(ROOT/name)==row['canonical_preimage'];before[name]=(ROOT/name).read_text()
 for name,row in um['preimages'].items():assert row['sha256']==hashlib.sha256(before[name].encode()).hexdigest()
 name='kernel/syscall.c';up=(U/'preimage'/name).read_text();uq=(U/'postimage'/name).read_text();start=up.index('int\nexit_group_current_pid_bridge(void)\n');end=up.index('\n#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS',start);old=up[start:end];new=uq[start:uq.index('\n#ifdef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS',start)];assert old.count('\n')==new.count('\n');out[name]=replace(out[name],old,new)
 name='kernel/rust/syscall_policy.rs';anchor='use core::ffi::c_void;\n';uold=(U/'preimage'/name).read_text();unew=(U/'postimage'/name).read_text();assert uold.startswith(anchor);extra=unew[len(anchor):len(unew)-len(uold)+len(anchor)];assert anchor+extra+uold[len(anchor):]==unew;assert out[name].startswith(anchor);out[name]=anchor+extra+out[name][len(anchor):]
 name='kernel/CMakeLists.txt';anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_policy.rs"\n';extra='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_exit_group_current_pid.rs"\n';assert (U/'preimage'/name).read_text().replace(anchor,anchor+extra)==(U/'postimage'/name).read_text();out[name]=replace(out[name],anchor,anchor+extra)
 leaf='kernel/rust/syscall_exit_group_current_pid.rs';out[leaf]=(U/'postimage'/leaf).read_text()
 rows=[];patch=''
 for name,text in out.items():
  p=D/'postimage'/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text)
  if name in before:
   q=D/'preimage'/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(before[name])
  patch+=''.join(difflib.unified_diff(before.get(name,'').splitlines(True),text.splitlines(True),fromfile='a/'+name if name in before else '/dev/null',tofile='b/'+name))
  rows.append(dict(proposed_path=name,postimage=ref(p),canonical_preimage=ref(ROOT/name)if name in before else None,reused_leaf_exact=name.endswith('.rs')and name not in ['kernel/rust/syscall_policy.rs','kernel/rust/lib.rs']))
 p=D/'SEVEN-LEAF-BATCH.PRIVATE-NOT-APPLIED.patch';p.write_text(patch)
 (D/'FILEMAP.SOURCE-ONLY.json').write_text(json.dumps(dict(scope='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.',status='PRIVATE_SEVEN_LEAF_SOURCE_COMPOSITION_ONLY',inputs=dict(six_leaf=ref(B/'SOURCE-READY.json'),pid_getter=ref(U/'SOURCE-READY.json')),files=rows,patch=ref(p),runtime_authority=None),indent=2)+'\n')
 print(json.dumps(ref(p)))
if __name__=='__main__':main()
