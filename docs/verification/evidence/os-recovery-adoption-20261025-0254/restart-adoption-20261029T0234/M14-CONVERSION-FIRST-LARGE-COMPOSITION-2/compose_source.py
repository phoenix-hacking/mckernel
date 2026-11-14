"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private source composition only; no compiler/preprocessor/runtime operation.
"""
from pathlib import Path
import json,hashlib,difflib,subprocess,os
D=Path(__file__).resolve().parent; A=D.parent; B=A/'M14-CONVERSION-FIRST-COMPOSITION-1'
S=A/'M14-LARGE-DO-SYSCALL-REUSE-1';U=A/'M14-LARGE-UTIL-THREAD-REUSE-1';R=A/'M14-UPGRADED-F03-REQUEST-CONSTRUCTORS-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(p.read_text())
def replace(s,a,b):
 assert s.count(a)==1,a[:80];return s.replace(a,b)
def main():
 assert not (D/'FILEMAP.SOURCE-ONLY.json').exists()
 rows=read(B/'FILEMAP.SOURCE-ONLY.json')['files'];out={};pre={};leaves={}
 for row in rows:
  n=row['target'];p=Path(row['source']['path']);assert ref(p)==row['source']
  if row['reused_leaf']:leaves[n]=row['source'];continue
  out[n]=p.read_text();pre[n]=Path(row['frozen119_preimage']['path']).read_text()
  q=D/'postimage'/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(out[n])
 # Apply only original, reviewed-scope C hunks. Shared Rust EOF and CMake are merged separately.
 commands=[]
 for p in [S/'CURRENT119-PRIVATE-REBASE.patch',U/'CURRENT119-PRIVATE-REBASE.patch',R/'REQUEST-CONSTRUCTORS.ON-TEN.PRIVATE-NOT-APPLIED.patch']:
  argv=['git','apply','--no-index','--include=kernel/syscall.c',str(p)]
  r=subprocess.run(argv,cwd=D/'postimage',capture_output=True,text=True,env=dict(os.environ,GIT_CEILING_DIRECTORIES=str(D)));commands.append(dict(argv=argv,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr));assert r.returncode==0,commands[-1]
 out['kernel/syscall.c']=(D/'postimage/kernel/syscall.c').read_text()
 policy='kernel/rust/syscall_policy.rs'
 for folder in [S,U]:
  text=(folder/'syscall_policy.PRIVATE.rs').read_text();assert text.startswith(pre[policy]);tail=text[len(pre[policy]):];assert tail and (folder/'RUST-BODY.REUSED.rs.inc').read_text() in tail;out[policy]+=tail
 base=(R/'preimage'/policy).read_text();text=(R/'postimage'/policy).read_text();assert text.startswith(base);out[policy]+=text[len(base):]
 leaf='kernel/rust/f03_request_constructors.rs';leaves[leaf]=ref(R/'natural-alignment-correction-1/postimage'/leaf)
 cm=out['kernel/CMakeLists.txt'];anchor='\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/syscall_policy.rs"\n';cm=replace(cm,anchor,anchor+'\t\t"${CMAKE_CURRENT_SOURCE_DIR}/rust/f03_request_constructors.rs"\n')
 anchor='\t\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n';cm=replace(cm,anchor,anchor+'\t\t\t\tif (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL)\n\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_request_constructors_candidate")\n\t\t\t\tendif()\n')
 anchor='\n\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n';cm=replace(cm,anchor,anchor+'\t\t\tif (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL)\n\t\t\t\tset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS MCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS)\n\t\t\tendif()\n');out['kernel/CMakeLists.txt']=cm
 patch='';newrows=[]
 for n,t in out.items():
  p=D/'postimage'/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(t);q=D/'preimage'/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(pre[n]);newrows.append(dict(target=n,source=ref(p),frozen119_preimage=ref(q),reused_leaf=False));patch+=''.join(difflib.unified_diff(pre[n].splitlines(True),t.splitlines(True),fromfile='a/'+n,tofile='b/'+n))
 for n,r in leaves.items():
  newrows.append(dict(target=n,source=r,frozen119_preimage=None,reused_leaf=True));patch+=''.join(difflib.unified_diff([],Path(r['path']).read_text().splitlines(True),fromfile='/dev/null',tofile='b/'+n))
 p=D/'LARGE-COMPOSITION.PRIVATE-NOT-APPLIED.patch';p.write_text(patch)
 inputs={k:ref(v)for k,v in dict(first20=B/'SOURCE-READY.json',dispatch=S/'SOURCE-STATE.json',util=U/'SOURCE-STATE.json',constructors=R/'SOURCE-READY.json',constructors_natural_alignment=R/'natural-alignment-correction-1/SOURCE-READY.json',Root_defined_contract=A/'M14-F03-REQUEST-CONSTRUCTOR-CONTRACT-1/ROOT-CONTRACT.REFINED-APPROVED.json').items()}
 for name,value in [('INPUTS.json',inputs),('COMPOSITION-APPLY.json',commands),('FILEMAP.SOURCE-ONLY.json',dict(status='PRIVATE_UNSELECTED_LARGE_SOURCE_COMPOSITION',files=newrows,patch=ref(p),first20_immutable=True,source_targets=len(newrows),new_large_selectors='OFF',runtime_authority=None))]:(D/name).write_text(json.dumps(value,indent=2)+'\n')
 print(json.dumps(dict(patch=ref(p),targets=len(newrows))))
if __name__=='__main__':main()
