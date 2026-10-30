#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import hashlib,json,pathlib,shutil,subprocess
A=pathlib.Path(__file__).resolve().parent.parent; O=pathlib.Path(__file__).resolve().parent; B=A.parent; P=O/'preimage'; S=O/'postimage'; P.mkdir(exist_ok=False); S.mkdir(exist_ok=False)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def copy(src,dst,expected=None):
 if expected: assert sha(src)==expected,(str(src),sha(src),expected)
 dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst);assert sha(dst)==sha(src)
e6a=B/'sdk21-nonheld13-data32-compile-preparation-1/SDK21-COMPILE.SOURCE-ONLY.json';assert sha(e6a)=='e6a8462b10b409e86a7192d34328de33307cccd5c8e53d75b6312c85042c1ec3'
profile=json.loads(e6a.read_text());mounts={x['container']:pathlib.Path(x['host']) for x in profile['readonly_shared_inputs']}
cm=mounts['/src/kernel/CMakeLists.txt'];arch=mounts['/src/arch/x86_64/kernel/syscall.c'];generic=mounts['/src/kernel/syscall.c'];rust=mounts['/src/kernel/rust']
for dst in [P,S]:
 copy(cm,dst/'kernel/CMakeLists.txt','812d1e5e016b9cde8fa71c211be93efdc5bfb49dd6b3685cded47d595f27dcf5')
 copy(arch,dst/'arch/x86_64/kernel/syscall.c','b2db4dce35ce2da311b71de284bcbf7aa739536cf1f81742aae9fd41c41b5ef9')
copy(generic,S/'kernel/syscall.c','4af4524be701ecdbaae09fba906c99bd065364c4caefdcf007820f463773eaf4')
assert sha(rust/'syscall_policy.rs')=='11d9d9e14c6c4ee3d593083ce18137414a7780c23507a44fb0834937fa9618e4';shutil.copytree(rust,S/'kernel/rust',symlinks=True)
patches=[]
for f,h in [('m14-nonheld13-data32-integration-1/integration.patch','85fc474fd94beb230d2756c584679573f7c9c3ad1c1fa25657c652e785f1784b'),('m14-f06-origin-guard-successor-1/origin-guard-cmake.patch','819e63a78173b54bc1f03221cb365eb5f3b8c40c27204d8a44b956a962119056'),('m14-f06-origin-route-successor-1/route.patch','0b9e8b6b4005d16a205d5f90c0606f7854606b28d7c531ff81733486513ff7b6'),('m14-f06-origin-guard-successor-1/origin-guard.patch','6875c3d318aa3da1d805eb008ca8620ce448f14448f68b49603a7f803b7b612f')]:
 p=A/f;assert sha(p)==h;r=subprocess.run(['patch','--batch','-p1','-d',str(S)],input=p.read_text(),text=True,capture_output=True);assert r.returncode==0,(str(p),r.stdout,r.stderr);patches.append({'file':str(p),'sha256':h,'stdout':r.stdout})
assert sha(S/'kernel/CMakeLists.txt')=='f34958844cf2a16d25244a3acc7c9610f262bc9cc64aba2db9706cc64a2a2655';assert sha(S/'arch/x86_64/kernel/syscall.c')=='9a356317ff621decba53a11fe0967ae9eee1bb5059d262e6b2402f90042a4a25'
for name,h in [('derive_f06_origin_e6a_guarded.py','0eecb12a434415523b744b73f1704f7cc68693ab3a28a328a3e354bf43c83f3c'),('f06_origin_command_profile_e6a_guarded.json','7b60afe60f069bb863e7c38ca8c28abe8ea682814d0207e54663572adfde7dca')]: copy(A/'m14-f06-origin-route-successor-1/postimage/scripts'/name,S/'scripts'/name,h)
for name in ['derive_f06_origin.py','f06_origin_command_profile.json']:copy(A/'m14-f06-origin-e6a-successor-1/predecessor'/name,S/'scripts'/name)
result=[]
for rel in ('kernel/CMakeLists.txt','arch/x86_64/kernel/syscall.c'):
 r=subprocess.run(['diff','-u','--label','a/'+rel,'--label','b/'+rel,str(P/rel),str(S/rel)],capture_output=True,text=True);assert r.returncode==1;result.append(r.stdout)
(O/'composition.patch').write_text(''.join(result))
m={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing','status':'SOURCE_ONLY_NO_EXECUTION_RELEASE','e6a_profile':str(e6a),'e6a_sha256':sha(e6a),'source_mounts':{k:str(v) for k,v in mounts.items() if k in ['/src/kernel/CMakeLists.txt','/src/arch/x86_64/kernel/syscall.c','/src/kernel/syscall.c','/src/kernel/rust']},'ordered_patches':patches,'postimage_sha256':{str(x.relative_to(S)):sha(x) for x in [S/'kernel/CMakeLists.txt',S/'arch/x86_64/kernel/syscall.c',S/'kernel/syscall.c',*sorted((S/'scripts').iterdir())]},'rust_regular_file_hashes':{str(x.relative_to(S/'kernel/rust')):sha(x) for x in sorted((S/'kernel/rust').rglob('*')) if x.is_file() and not x.is_symlink()},'rust_symlinks':{str(x.relative_to(S/'kernel/rust')):str(x.readlink()) for x in sorted((S/'kernel/rust').rglob('*')) if x.is_symlink()},'limitations':['partial overlay, not whole source tree','ON uses guarded arch source; OFF must mount original predecessor arch source, not this ON postimage','no configure, compiler, linked/default/native evidence','no execution or release authority']}
(O/'MANIFEST.json').write_text(json.dumps(m,indent=2)+'\n');print('PASS exact e6a preimages, ordered paired patches, copied source and guarded route')
