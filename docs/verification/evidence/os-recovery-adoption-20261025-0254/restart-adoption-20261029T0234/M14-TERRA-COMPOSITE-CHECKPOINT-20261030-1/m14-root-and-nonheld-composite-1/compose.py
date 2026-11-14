#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
import ast,hashlib,json,pathlib,shutil,subprocess
A=pathlib.Path(__file__).resolve().parent.parent; O=pathlib.Path(__file__).resolve().parent
P=O/'preimage'; S=O/'postimage'; P.mkdir(exist_ok=False);S.mkdir(exist_ok=False)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cp(src,dst,expected):
 assert sha(src)==expected,(str(src),sha(src));dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst);assert sha(dst)==expected
prior=A/'m14-nonheld-composition-1'; profile=A/'m14-f06-configure-admission-1/CONFIGURE-PROFILE.NOT-RELEASED.json'; assert sha(profile)=='a20a8bf81aaf632376a6a1b1c3d39189f227adce431e9cac01d6b27108902dcd'
j=json.loads(profile.read_text());base=pathlib.Path(j['readonly_source_mounts_candidate']['/src']);root=base/'CMakeLists.txt'
root_h='e60b304fd38bd2dcddd4f7f8c6217bf887bacfc997741e7aed321dd9222899da'
cm_h='812d1e5e016b9cde8fa71c211be93efdc5bfb49dd6b3685cded47d595f27dcf5';arch_h='b2db4dce35ce2da311b71de284bcbf7aa739536cf1f81742aae9fd41c41b5ef9'
for d in (P,S):
 cp(root,d/'CMakeLists.txt',root_h);cp(prior/'preimage/kernel/CMakeLists.txt',d/'kernel/CMakeLists.txt',cm_h);cp(prior/'preimage/arch/x86_64/kernel/syscall.c',d/'arch/x86_64/kernel/syscall.c',arch_h);(d/'scripts').mkdir(exist_ok=True)
for n in ('verify_m14_elf.py','verify_m14_configure_probe.py'):assert not (base/'scripts'/n).exists(),f'new-file conflict: {base}/scripts/{n}'
root_patch=A/'m14-cmake-probe-bound-successor-1/complete-original.patch';kernel_patch=prior/'composition.patch'
assert sha(root_patch)=='01f3d94dab8afb03b51de1723de1501e4e45845e439096538ed3a332f18508b4';assert sha(kernel_patch)=='604fb762d10b55c189cf294f7a0a4ff648295ab05306bc92cddf11013dd0e8aa'
patch=O/'composite.patch';patch.write_bytes(root_patch.read_bytes()+kernel_patch.read_bytes())
for d,dry in ((P,True),(S,False)):
 cmd=['patch','--batch','-p1','-d',str(d)];
 if dry:cmd.append('--dry-run')
 r=subprocess.run(cmd,input=patch.read_bytes(),capture_output=True);(O/('dry-run.stdout' if dry else 'apply.stdout')).write_bytes(r.stdout);(O/('dry-run.stderr' if dry else 'apply.stderr')).write_bytes(r.stderr);assert r.returncode==0,(cmd,r.stdout,r.stderr)
checks={'CMakeLists.txt':'439642a3215a05f9ace7a9e3443e1b5acfdcf6565e1342e28e8d254281706729','kernel/CMakeLists.txt':'f34958844cf2a16d25244a3acc7c9610f262bc9cc64aba2db9706cc64a2a2655','arch/x86_64/kernel/syscall.c':'9a356317ff621decba53a11fe0967ae9eee1bb5059d262e6b2402f90042a4a25','scripts/verify_m14_elf.py':'157e2bd952f07c70a867fa9bd78165ac364c21d87f7dc32e3ecc482c191f7ca7','scripts/verify_m14_configure_probe.py':'fa9bd547813bdad6848ff58fed7b48686af0fcf2cd50197a6866338d6ebe9902'}
for n,h in checks.items():assert sha(S/n)==h,(n,sha(S/n),h)
for n in ('kernel/CMakeLists.txt','arch/x86_64/kernel/syscall.c'):assert (S/n).read_bytes()==(prior/'postimage'/n).read_bytes()
for n in ('verify_m14_elf.py','verify_m14_configure_probe.py'):ast.parse((S/'scripts'/n).read_text())
r=(S/'CMakeLists.txt').read_text();k=(S/'kernel/CMakeLists.txt').read_text(); assert 'if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)' in r and 'if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)' in k
for n,h in [('verify_m14_elf.py',checks['scripts/verify_m14_elf.py']),('verify_m14_configure_probe.py',checks['scripts/verify_m14_configure_probe.py'])]:assert h in r and n in r
assert 'derive_f06_origin_e6a_guarded.py' in k and 'derive_f06_origin.py' in k
maps=dict(j['readonly_source_mounts_candidate']);maps['/src/CMakeLists.txt']=str(S/'CMakeLists.txt');maps['/src/kernel/CMakeLists.txt']=str(S/'kernel/CMakeLists.txt');maps['/src/arch/x86_64/kernel/syscall.c']=str(S/'arch/x86_64/kernel/syscall.c')
for n in ('verify_m14_elf.py','verify_m14_configure_probe.py'):maps['/src/scripts/'+n]=str(S/'scripts'/n)
for n in ('derive_f06_origin_e6a_guarded.py','f06_origin_command_profile_e6a_guarded.json','derive_f06_origin.py','f06_origin_command_profile.json'):maps['/src/scripts/'+n]=str(prior/'postimage/scripts'/n)
manifest={'scope':'Functional McKernel OS/apps and Rust/assembly migration only; no security testing','status':'SOURCE_ONLY_UNRELEASED','base_proposal':str(profile),'base_proposal_sha256':sha(profile),'prior_composition_manifest':str(prior/'MANIFEST.json'),'prior_composition_manifest_sha256':sha(prior/'MANIFEST.json'),'source_patch_components':{'root':{'path':str(root_patch),'sha256':sha(root_patch)},'kernel_arch':{'path':str(kernel_patch),'sha256':sha(kernel_patch)}},'composite_patch_sha256':sha(patch),'root_preimage':str(root),'preimage_sha256':{'CMakeLists.txt':root_h,'kernel/CMakeLists.txt':cm_h,'arch/x86_64/kernel/syscall.c':arch_h},'postimage_sha256':checks,'on_source_mount_proposal':maps,'off_source_pair':'Only predecessor producer/profile with exact predecessor architecture source sha256 d060dbf5b83e29b1d5f16e7504972f05cb53d553fb754de1a67566d2c0f06b37; select and rebind exact source separately; never use guarded ON source','unbound':['base mount membership and quiescence','full compile/header dependency closure','current actual compiler and configure flags','actual provider and held-path reachability','fresh operation admission, resource owner, kernel build tree isolation','default/link/native proof']}
(O/'MOUNT-MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n');print('PASS exact three preimages, two verifier new-file absence, composite dry-run/apply, expected final hashes, shared selector and origin routes')
