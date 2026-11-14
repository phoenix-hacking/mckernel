#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Generate only a private source patch and proposed argv vectors; execute no build.
"""
import copy, difflib, hashlib, json, re, shlex
from pathlib import Path
here=Path(__file__).resolve().parent
root=Path('/home/holden/mckernel')
e=root/'docs/verification/evidence/os-recovery-adoption-20261025-0254/restart-adoption-20261029T0234'
w=e/'M14-ARCH5-SIGRETURN-ABI-WITNESS-20261030-2'
csrc=root/'arch/x86_64/kernel/syscall.c'
rsrc=e/'M14-CONVERSION-FIRST-ACTUAL-SNAPSHOT-1/rust-subtree/lib.rs'
ccworker=e/'ROOT-CURRENT119-BUILD-ADMISSION-1/OUTPUT/work/evidence/worker-result.json'
rworker=e/'ROOT-CONVERSION-FIRST-BUILD-ADMISSION-1/OUTPUT/work/evidence/worker-result.json'
def sha(b): return hashlib.sha256(b).hexdigest()
def read(path, expected):
    b=path.read_bytes(); assert sha(b)==expected, str(path); return b.decode()
c=read(csrc,'b5e9a382491d0f6dc4b71a55f54f76f3d4ca610fa9f81adc60e70ec97a194669')
r=read(rsrc,'f05fb08c6ebc33fccb6071a4b965f3f33da01e0b0cc9a68f7ffb7ce47ec72a68')
ci=read(w/'sigreturn-extra-abi.inc','5c560e42682c7e6bb180908b3bfde6dddd2a6288a936e38b5c5f257835e0af64')
ri=read(w/'sigreturn_extra_abi.rs','5fa1e835f4c937993323bd6490f1c805fd3ce6f874f73f01c8397dd171860ccc')
g=read(w/'GEOMETRY.json','5b3ef073c45b3e4f7e170f725025c3c5f5375555318cae3264736068f934c50b')
rows=json.loads(g)
assert len(rows)==46 and len({x['key'] for x in rows})==46
assert [(int(n),key.strip()) for n,key in re.findall(r'/\* (\d+): (.*?) \*/',ci)] == [(i,x['key']) for i,x in enumerate(rows)]
assert [(int(n),key.strip()) for n,key in re.findall(r'// (\d+): (.*)',ri)] == [(i,x['key']) for i,x in enumerate(rows)]
for i,row in enumerate(rows):
    assert f"    {row['c']}, /* {i}: {row['key']} */" in ci
    assert f"    ({row['rust']}) as u64, // {i}: {row['key']}" in ri
assert [x['key'] for x in rows[-6:]]==['thread.sigmask','sigset.size','sigset.align','sigset.first.offset','thread.sigmask.first.offset','sigset.first.width']
assert 'sigreturn-extra-abi.inc' not in c and 'mod sigreturn_extra_abi;' not in r
assert 'struct sigsp {' in c and 'mod native_signal;' in r
assert c.endswith('\n') and r.endswith('\n')
c2=c+'\n/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */\n#ifdef MCKERNEL_SIGRETURN_ABI_WITNESS_ONLY\n#include <sigreturn-extra-abi.inc>\n#endif\n'
r2=r+'\n// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.\n#[cfg(all(sigreturn_abi_witness_only, not(native_linux_irq_work_v6_12)))]\ncompile_error!("sigreturn ABI witness requires native Linux 6.12 signal layout");\n#[cfg(sigreturn_abi_witness_only)]\nmod sigreturn_extra_abi;\n'
def loc(s):
    return [(n,m.start(),line) for n,line in enumerate(s.splitlines(),1) for m in re.finditer(r'\b(?:line|file|column)!\s*\(',line)]
assert loc(c)==loc(c2) and loc(r)==loc(r2)
def diff(a,b,path,new=False):
    return ''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='/dev/null' if new else 'a/'+path,tofile='b/'+path))
patch=(diff(c,c2,'arch/x86_64/kernel/syscall.c')+diff(r,r2,'kernel/rust/lib.rs')+
       diff('',ci,'arch/x86_64/kernel/include/sigreturn-extra-abi.inc',True)+
       diff('',ri,'kernel/rust/sigreturn_extra_abi.rs',True))
(here/'ARCH46-HOOKS.PRIVATE.patch').write_text(patch)
actualc=json.loads(ccworker.read_text())['commands']; actualr=json.loads(rworker.read_text())['commands']
basec=copy.deepcopy(actualc[2]['argv']); baser=copy.deepcopy(actualr[0]['argv']); link=copy.deepcopy(actualr[2]['argv'])
assert basec[-1]=='/src/arch/x86_64/kernel/syscall.c' and baser[-1]=='/src/kernel/rust/lib.rs'
assert not any('FULL28' in arg or 'MCKERNEL_SIGRETURN_ABI_WITNESS_ONLY' in arg or 'sigreturn_abi_witness_only' in arg or 'f06_do_signal_whole_candidate' in arg or 'MCKERNEL_RUST_F06_DO_SIGNAL_WHOLE' in arg for arg in basec+baser)
def ccmd(on):
    v=copy.deepcopy(basec); ix=v.index('-o'); assert v[ix+1]=='CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o'
    v[ix+1]='/work/witness/arch46/syscall.o' if on else '/work/production/arch46/syscall.o'
    v[-1:-1]=['-MD','-MF','/work/witness/arch46/syscall.d' if on else '/work/production/arch46/syscall.d']
    if on: v[-1:-1]=['-DMCKERNEL_SIGRETURN_ABI_WITNESS_ONLY']
    return v
def rcmd(on):
    v=copy.deepcopy(baser); emit=[i for i,x in enumerate(v) if x.startswith('--emit=obj=')]; assert len(emit)==1
    output_root='/work/witness/arch46' if on else '/work/production/arch46'
    v[emit[0]]='--emit=obj='+output_root+'/mckernel_rust.o,dep-info='+output_root+'/mckernel_rust.d'
    if on: v[-1:-1]=['--cfg','sigreturn_abi_witness_only']
    return v
witness=[{'id':'c','argv':ccmd(True)},{'id':'rust','argv':rcmd(True)}]
production=[{'id':'c','argv':ccmd(False)},{'id':'rust','argv':rcmd(False)}]
# Historical eleven input link with only these two gate-off object substitutions.
arch='CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o'; rust='rust/mckernel_rust.o'
assert link.count(arch)==1 and link.count(rust)==1
link[link.index(arch)]='/work/production/arch46/syscall.o'; link[link.index(rust)]='/work/production/arch46/mckernel_rust.o'
link[link.index('-Map=/work/output/build/kernel/mckernel.img.map')]='-Map=/work/production/arch46/mckernel.img.map'
link[link.index('--dependency-file=CMakeFiles/mckernel.img.dir/link.d')]='--dependency-file=/work/production/arch46/link.d'
assert link[-2:]==['-o','mckernel.img']; link[-1]='/work/production/arch46/mckernel.img'
assert not any('/work/witness/' in x for x in link)
out={'status':'SOURCE_ONLY_PROPOSED_NOT_EXECUTED_NOT_AUTHORIZED','scope':__doc__.splitlines()[0],
     'cwd':'/work/output/build/kernel','witness_pair':witness,'production_pair':production,'proposed_raw_link_argv':link,
     'source_bindings':{'arch_preimage_sha256':sha(c.encode()),'rust_lib_preimage_sha256':sha(r.encode()),'arch_postimage_sha256':sha(c2.encode()),'rust_lib_postimage_sha256':sha(r2.encode()),'witness_c_sha256':sha(ci.encode()),'witness_rust_sha256':sha(ri.encode()),'witness_manifest_sha256':sha(g.encode()),'private_patch_sha256':sha(patch.encode())},
     'recipe_bindings':{'C_current119_worker':str(ccworker),'C_current119_worker_sha256':sha(ccworker.read_bytes()),'Rust_and_link_qualified19_worker':str(rworker),'Rust_and_link_qualified19_worker_sha256':sha(rworker.read_bytes())},
     'required_actual_inputs':{'final_selected_source_tuple':None,'genuine_f06_origin_for_changed_arch':None,'configuration_header_live_hash':None,'compiler_versions_and_sdk21_identity':None,'native_and_nonheld_selector_readback':None,'witness_and_production_roots_unique':None,'physical_release_and_aggregate_share':None,'production_witness_exclusion_and_actual_raw_link_binding':None},
     'limits':['46 geometry only; no selector/provider ownership, machine code or native proof','raw XRSTOR candidate is nonnative; native return uses checked FP provider','proposed link is not a review or execution release','never link witness-enabled objects'],
     'runtime_authority':False}
(here/'SOURCE-AND-ARGV.json').write_text(json.dumps(out,indent=2)+'\n')
for name,items in [('WITNESS-ARGV.sh.txt',witness),('PRODUCTION-ARGV.sh.txt',production)]:
    (here/name).write_text('\n'.join(shlex.join(x['argv']) for x in items)+'\n')
(here/'PROPOSED-RAW-LINK.sh.txt').write_text(shlex.join(link)+'\n')
print('Source-only: 4-target patch, matching 46 ordered keys, two argv pairs, proposed gate-off 11-input raw link. No compiler/test/link execution.')
