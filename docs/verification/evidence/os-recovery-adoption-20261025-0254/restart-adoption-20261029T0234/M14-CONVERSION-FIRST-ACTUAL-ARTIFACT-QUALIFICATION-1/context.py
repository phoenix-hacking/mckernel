"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only actual119 artifact facts using frozen accepted validator functions.
No compiler, HOST payload, Docker, native or cleanup operation.
"""
from pathlib import Path
import ast,collections,hashlib,json,struct,re,time
D=Path(__file__).resolve().parent;A=D.parent;E=A.parent;R=A/'ROOT-CONVERSION-FIRST-BUILD-ADMISSION-1';W=R/'OUTPUT/work';B=W/'output/build/kernel';AD=A/'M14-ORIGINAL-CLOSURE-AND-POST119-REMAINING-1/CURRENT119-ARTIFACT-CONSUMER-READINESS-1/FULL-ARTIFACT-DATA-ADAPTER-1'

def read(p):return json.loads(Path(p).read_bytes())
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def auth(r):assert ref(r['path'])==r,r['path'];return Path(r['path'])
template=read(AD/'FULL-ARTIFACT-INPUT.TEMPLATE.NOT-AUTHORITY.json')
for row in template['validator_nodes']:
 p=auth(row['source']);raw=p.read_text();node=next(n for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))and n.name==row['name'])
 assert hashlib.sha256(ast.get_source_segment(raw,node).encode()).hexdigest()==row['source_segment_sha256']
 assert hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest()==row['AST_sha256']
 exec(compile(ast.Module(body=[node],type_ignores=[]),str(p)+':EXACT_ACCEPTED_VALIDATOR','exec'),globals())
# own/allocated/relocated_function are the exact accepted functions. Only context changes.
rels=_reuse_elf_owning_relocations;data=_reuse_elf_object_bytes;host=None;HOST_FILE=PROD_FILE=HOST_X86_FILE=PROD_X86_FILE=b''
finite_sections={'.lrodata.'+n for n in ['process_add_range_log_bridge','process_init_stack_log_bridge','process_range_public_log_bridge','process_remove_range_log_bridge','process_sched_runq_log_bridge']}

def elf(p):
 e=_ReuseElf(Path(p));e.path=Path(p);return e

def defined(e,n):return[s for s in e.symbols if s['name']==n and s['shndx']]

grant=read(R/'ROOT-ACTUAL-ONE-BUILD-ONLY-GRANT.json');profile=read(auth(grant['profile']));worker=read(W/'evidence/worker-result.json');producer=read(W/'evidence/producer-contract.json');assert len(worker['commands'])==3 and producer['commands']==worker['commands']and producer['contract']==profile['producer_contract']
for actual,planned in zip(worker['commands'],profile['exact_commands']):
 assert actual['argv']==planned['argv']and actual['cwd']==planned['cwd']and actual['returncode']==0
 p=W/Path(actual['output']['path']).relative_to('/work');r=ref(p);assert (r['bytes'],r['sha256'])==(actual['output']['bytes'],actual['output']['sha256'])
objects=[(r,elf(B/r['link_token']if r['replace']else auth(r['source'])))for r in profile['inputs']['objects']];bytoken={r['link_token']:e for r,e in objects};new=bytoken['rust/mckernel_rust.o'];kc=bytoken['CMakeFiles/mckernel.img.dir/syscall.c.o'];ac=bytoken['CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o'];pc=bytoken['CMakeFiles/mckernel.img.dir/process.c.o'];image=Final(B/'mckernel.img')
accept=read(auth(template['historical_accepted116']));old=elf(auth(accept['tuple']['Rust']));oldkc=elf(auth(accept['tuple']['generic_C']));oldac=elf(auth(accept['tuple']['arch_C']));oldimage=Final(auth(accept['tuple']['image']))
assert len(objects)==11 and sum(r['replace']for r,e in objects)==2
assert[s for s in worker['commands'][-1]['argv']if s.endswith('.o')]==[r['link_token']for r,e in objects]
assert not [s for s in image.symbols if s['shndx']==0 and s['bind']==1 and s['name']]
inputs=template['source_facts']['source_qualified_ABI_and_declared_providers'];f03=read(auth(inputs['F03']));f06=read(auth(inputs['F06']));providers=sorted(set(f03['exported_functions_once'])|set(f06['ten_function_providers'])|{'clear_host_pte','f03_perf_mmap_v1','vdso_get_vdso_info','arch_native_signal_restore_fp_bridge'})

# Frozen original389 comparator, no expected-field/count changes.
registry_before=registry(oldimage);registry_after=registry(image);compare(registry_before,registry_after)
print('ORIGINAL389',len(registry_after),'PASS')
