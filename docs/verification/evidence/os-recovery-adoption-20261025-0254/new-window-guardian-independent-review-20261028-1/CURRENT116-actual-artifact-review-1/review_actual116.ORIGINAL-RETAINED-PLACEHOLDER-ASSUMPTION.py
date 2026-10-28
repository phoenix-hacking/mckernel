"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Finite offline actual116 artifacts/readback. No compiler/runtime/control operation.
"""
from pathlib import Path
import ast,collections,hashlib,json,struct,datetime,re,subprocess
D=Path(__file__).resolve().parent;E=D.parent.parent;P=E/'ROOT-CURRENT116-F03SEVEN-SHM-BUILD-ADMISSION-1';B=P/'OUTPUT/work/output/build/kernel'
OD=E/'ROOT-CURRENT115-LOCAL31-CPUID-BUILD-PREPARATION-1/independent-artifact-review-preparation-1'
def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def auth(r):assert ref(r['path'])==r,r['path'];return Path(r['path'])
def extract(p,names):
 raw=Path(p).read_bytes();nodes=[n for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names];assert {n.name for n in nodes}==names
 exec(compile(ast.Module(body=nodes,type_ignores=[]),str(p)+':SELECTED_OFFLINE_READERS','exec'),globals())
accepted=read(OD/'INDEPENDENT-ACTUAL-CURRENT115-ARTIFACT-ACCEPTANCE.json');contract=read(auth(accepted['proofs']['FINITE-ARTIFACT-REVIEW-PREPARATION.json']))
extract(auth(contract['elf_reader']),{'_ReuseElf','_reuse_elf_function','_reuse_elf_owning_relocations','_reuse_elf_object_bytes'})
extract(auth(contract['final_reader']),{'Final'})
Elf=_ReuseElf;rels=_reuse_elf_owning_relocations;data=_reuse_elf_object_bytes

def elf(p):e=Elf(Path(p));e.path=Path(p);return e
def own(e,n):
 ss=[s for s in e.symbols if s['name']==n and s['shndx']];assert len(ss)==1,(n,len(ss));return ss[0]
def allocated(e,t):return {s['name']:s for s in e.symbols if s['type']==t and 0<s['shndx']<len(e.sections) and e.sections[s['shndx']]['flags']&2}
profile=read(P/'PROFILE.SOURCE-ONLY.json');worker=read(P/'OUTPUT/work/evidence/worker-result.json');producer=read(P/'OUTPUT/work/evidence/producer-contract.json')
assert len(worker['commands'])==4 and producer['commands']==worker['commands'] and producer['contract']==profile['producer_contract']
for w,c in zip(worker['commands'],profile['exact_commands']):
 assert w['argv']==c['argv'] and w['cwd']==c['cwd'] and w['returncode']==0
 r=w['output'];actual=ref(P/'OUTPUT/work'/Path(r['path']).relative_to('/work'));assert (actual['bytes'],actual['sha256'])==(r['bytes'],r['sha256'])
objects=[]
for r in profile['inputs']['objects']:
 p=B/r['link_token']
 if not r['replace']:assert ref(p)['sha256']==r['source']['sha256'] and ref(p)['bytes']==r['source']['bytes']
 objects.append((r,elf(p)))
bytoken={r['link_token']:e for r,e in objects};new=bytoken['rust/mckernel_rust.o'];kc=bytoken['CMakeFiles/mckernel.img.dir/syscall.c.o'];ac=bytoken['CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o'];pc=bytoken['CMakeFiles/mckernel.img.dir/process.c.o'];old=elf(accepted['tuple']['Rust']['path']);oldkc=elf(accepted['tuple']['retained_kernel_C']['path']);oldac=elf(accepted['tuple']['arch_C']['path']);image=Final(B/'mckernel.img');oldimage=Final(accepted['tuple']['image']['path'])
assert len(objects)==11 and sum(r['replace'] for r,e in objects)==3
assert [s for s in worker['commands'][-1]['argv'] if s.endswith('.o')]==[r['link_token'] for r,e in objects]
assert all(r['link_token'] in (B/'CMakeFiles/mckernel.img.dir/link.d').read_text() for r,e in objects)
removed={key:sorted(set(allocated(a,2))-set(allocated(b,2))) for key,a,b in [('generic',oldkc,kc),('arch',oldac,ac)]};added={key:sorted(set(allocated(b,2))-set(allocated(a,2))) for key,a,b in [('generic',oldkc,kc),('arch',oldac,ac)]}
expected=['ptrace_report_signal_bridge','ptrace_syscall_event','ptrace_wakeup_clear_saved_bridge','ptrace_wakeup_set_single_step_bridge','ptrace_wakeup_trace_syscall_bridge','ptrace_wakeup_pending_take_bridge','ptrace_setsiginfo']
assert set(removed['generic'])==set(expected) and removed['arch']==['arch_do_shmget_bridge'] and not added['generic'] and not added['arch'],(removed,added)
providers=['f03_exec_report_signal_v1','ptrace_syscall_event','ptrace_wakeup_clear_saved_bridge','ptrace_wakeup_set_single_step_bridge','ptrace_wakeup_trace_syscall_bridge','ptrace_wakeup_pending_take_bridge','f03_ptrace_setsiginfo_v1','arch_do_shmget_bridge']
for n in providers:
 s=own(new,n);f=image.sym(n);assert s['type']==f['type']==2 and s['bind']==f['bind']==1 and s['size']==f['size']
 assert not any(q['name']==n and q['shndx'] for r,e in objects if e is not new for q in e.symbols),n
inventory=dict(scope=__doc__.splitlines()[0],actual_profile=ref(P/'PROFILE.SOURCE-ONLY.json'),actual_worker=ref(P/'OUTPUT/work/evidence/worker-result.json'),tuple=dict(Rust=ref(new.path),generic_C=ref(kc.path),arch_C=ref(ac.path),process_C=ref(pc.path),image=ref(image.path)),removed_C_functions=removed,added_C_functions=added,counts=dict(generic_C_functions=len(allocated(kc,2)),arch_C_functions=len(allocated(ac,2)),selected_C_functions=len(allocated(kc,2))+len(allocated(ac,2)),process_FUNCTIONs=len(allocated(pc,2)),process_OBJECTs=len(allocated(pc,1)),new_Rust_selected_providers=len(providers)),new_providers=[dict(name=n,input=own(new,n),final=image.sym(n)) for n in providers],native_acceptance=False,wholefile_acceptance=False)
(D/'ACTUAL-INVENTORY.json').write_text(json.dumps(inventory,indent=2)+'\n')
if __name__=='__main__':print(json.dumps({'inventory':ref(D/'ACTUAL-INVENTORY.json'),'counts':inventory['counts'],'removed':removed}))
