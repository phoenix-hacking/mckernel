"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Read-only actual build3 qualification; unchanged retained validator bodies, no workload.
"""
import ast,hashlib,json,os,re,shlex,stat,struct,subprocess,traceback
from pathlib import Path as HostPath, PurePosixPath
D=HostPath(__file__).resolve().parent;E=D.parent
B=E/'ROOT-CURRENT290-BUILD-ONLY-ADMISSION-3/OUTPUT/work/output/build'
A=E/'ROOT-CURRENT290-BUILD-ONLY-ADMISSION-3/OUTPUT/work/evidence'
DRIVER=E/'current290-driver-identity-repair-source-1/native_rust_exact_mckernel_image_offline.CURRENT290.VIEW-AND-FRESH-OBJECT-GATE.py'
P=json.loads((E/'current290-unprivileged-build-only-source-1/PROFILE.SOURCE-ONLY.json').read_text())
producer=json.loads((A/'producer-contract.json').read_text())
seed=HostPath(P['inputs']['retained_seed']);policy=next(r['postimage']['path'] for r in P['inputs']['postimages'] if r['relative']=='kernel/rust/syscall_policy.rs')

def ref(path):
 p=HostPath(path);raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def write(path,value):
 p=HostPath(path);assert p.parent==D or D in p.parents;p.write_text(json.dumps(value,indent=2)+'\n')
class PolicyPath:
 def read_text(self,*args,**kwargs):return HostPath(policy).read_text(*args,**kwargs)
 def __str__(self):return '/src/kernel/rust/syscall_policy.rs'
def mapped_path(value):
 text=str(value)
 if text=='/src/kernel/rust/syscall_policy.rs':return PolicyPath()
 if text.startswith('/seed-build/'):return seed/text.removeprefix('/seed-build/')
 return HostPath(value)
from profile_clone_witness import validate
profile_proof=json.loads((D/'CLONE-FINAL-POINTER-AND-WARNINGS.json').read_text())
source=DRIVER.read_bytes();assert hashlib.sha256(source).hexdigest()=='9d2d39a0f4a28dc15638fe2c1a01052e64886078d39c3b1e7bf57eccf68bbdfd'
tree=ast.parse(source)
names={'_fail','_sha256','_canonical','_regular','_artifact','_reuse_require','_reuse_elf_owning_relocations','_reuse_elf_object_bytes','_reuse_elf_cstring','_reuse_elf_descriptor','_reuse_elf_function','_reuse_elf_undefined','_reuse_elf_panic_targets','_reuse_validate_changed_rust_object','_no_core_panic_undefined'}
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names or isinstance(n,ast.ClassDef) and n.name=='_ReuseElf']
ns=dict(Path=mapped_path,hashlib=hashlib,json=json,os=os,stat=stat,struct=struct,ImageBuildError=RuntimeError,_check_signal=lambda:None,_atomic_json=write)
exec(compile(ast.Module(body=nodes,type_ignores=[]),str(DRIVER)+':UNCHANGED_READONLY_RUST_GATES','exec'),ns)
report=dict(scope=__doc__.splitlines()[0],producer=ref(A/'producer-contract.json'),worker_result=ref(A/'worker-result.json'),validator_source=ref(DRIVER),status='IN_PROGRESS',phases={})
try:
 assert producer['source_profile']==ref(E/'current290-unprivileged-build-only-source-1/PROFILE.SOURCE-ONLY.json')
 for index,row in enumerate(producer['commands']):
  assert row['returncode']==0 and row['argv']==P['exact_commands'][index]['argv']
  actual=B/'kernel'/['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/process.c.o','mckernel.img'][index]
  assert ref(actual)==dict(row['output'],path=str(actual))
 report['phases']['producer']='PASS_EXACT_THREE_ARGV_AND_FRESH_OUTPUT_IDENTITIES'
 proof=ns['_reuse_validate_changed_rust_object'](B,D)
 report['phases']['changed_Rust_unchanged_9d2d_gate']=dict(status=proof['status'],proof=str(D/'fresh-compiled-rust-ownership-proof.json'))
 Elf=ns['_ReuseElf'];rust=Elf(B/'kernel/rust/mckernel_rust.o');process=Elf(B/'kernel/CMakeFiles/mckernel.img.dir/process.c.o')
 storage={}
 for name,size,align in [('resource_set_list',16,16),('resource_set_lock',64,64),('runq_reservation_lock',4,4)]:
  owned=[s for s in rust.symbols if s['name']==name and s['shndx']!=0]
  assert len(owned)==1;v=owned[0];sec=rust.sections[v['shndx']]
  assert v['bind']==1 and v['type']==1 and v['size']==size and sec['align']>=align and v['value']%align==0
  assert ns['_reuse_elf_object_bytes'](rust,v)==bytes(size)
  assert not [s for s in process.symbols if s['name']==name and s['shndx']!=0]
  storage[name]=dict(Rust_symbol=v,section=sec,initial_hex=bytes(size).hex(),process_has_no_definition=True)
 report['phases']['three_Rust_data_providers']=storage
 undefined=subprocess.run(['/usr/bin/nm','--undefined-only','--demangle',str(B/'kernel/rust/mckernel_rust.o')],capture_output=True,text=True,check=True)
 assert not undefined.stderr;report['phases']['production_panic_gate']=validate(undefined.stdout,profile_proof)
 (D/'production-rust-undefined.nm').write_text(undefined.stdout)
 old=Elf(seed/'kernel/rust/mckernel_rust.o')
 for elf in (old,rust):
  clone=ns['_reuse_elf_function'](elf,'clone_thread')
  assert clone['bind']==1 and clone['type']==2 and clone['size']==27 and clone['shndx']!=0
 expected=(E/'current290-actual-build3-qualification-source-1/new-production-rust-undefined.nm').read_text()
 assert undefined.stdout==expected, 'all other provider witnesses must remain exact'
 report['phases']['current_profile_clone_source_object_final_proof']=profile_proof
 report['phases']['both_old_new_clone_global_defined_27B']=True
 report['phases']['all_other_undefined_provider_witnesses_exact']=True
 report['status']='PASS_ACTUAL_CURRENT290_PROFILE_PRODUCER_RUST_STORAGE_PANIC_LOGGER_CLONE_FINAL_GATES'
except BaseException as error:
 report['status']='FAIL_FIRST_ACTUAL_VALIDATOR_PRESERVED';report['first_failure']=repr(error);report['traceback']=traceback.format_exc()
write(D/'RESULT.json',report)
print(json.dumps(dict(status=report['status'],first_failure=report.get('first_failure'),phases=list(report['phases']))))
if report['status'].startswith('FAIL'):raise SystemExit(1)
