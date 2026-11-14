"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Compose exact qualified source deltas privately; no compiler or canonical action.
"""
from pathlib import Path
import collections,copy,difflib,hashlib,json,os
R=Path('/home/holden/mckernel');E=R/'docs/verification/evidence/os-recovery-adoption-20261025-0254';D=Path(__file__).resolve().parent
F3=E/'m14-f03-selected-residual-implementation-20261026-1';F6=E/'m14-f06-selected-residual-implementation-20261026-1/coherent-f06-six-provider-batch-1';FOUR=F3/'next-execveat-selected-1/coherent-four-slice-plan-1';EXIT=F3/'next-do-exit-selected-1';BACK=F3/'next-selected-provider-backlog-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def write(p,value):p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);p.write_text(json.dumps(value,indent=2)+'\n')
proofs=[FOUR/'COHERENT-SOURCE-PLAN.NOT-GRANTED.json',EXIT/'ACTUAL-SCOPED-RESULT-HANDOFF.json',BACK/'ACTUAL-SCOPED-RESULT-HANDOFF.json',F6/'expert-complete-header-context-1/ACTUAL-EXPERT-HOST-HANDOFF.json']
assert ref(proofs[0])['sha256']=='f8f057a74627145cc40db687edaede42fc3e85d0059533c4640adec5042d0a61';assert ref(proofs[-1])['sha256']=='3f5b45d43d947cb1e0509d07f72305a8dd1cae907abea1a8faf1f334b800e49b'
for p in proofs[1:]:assert json.loads(p.read_text())['status'].startswith('PASS')
P=json.loads((E/'ROOT-F02-DATA-DEFAULT-BUILD-ADMISSION-1/PROFILE.SOURCE-ONLY.json').read_text());SRC=Path(P['inputs']['source6153']);expected={'kernel/syscall.c':'54a9b0a8c6b9e1077fa7830bbaecdc699e7f3414767f50a77d4e5def63bdc582','kernel/rust/syscall_policy.rs':'fefec3eb05be2f714dfeca34310901a566557f82ee08de9b9ad0ef0344f74d62','kernel/rust/lib.rs':'a05908f81b3ecd37d22fa75585525b8a4c8cf8cc9c52be57ea9a86e2ec580680','kernel/CMakeLists.txt':'f29336679e462746822d5ce9efe1a74491fbea1f0cbb46d56cfdc48ae082b3cc','arch/x86_64/kernel/syscall.c':'d6bf00d0a46755f37f511bff0c098487f04a155842f11a4ac64f2a1795faa8c1','kernel/process.c':'9692036c3aa2d580a2a134c2d4a8fc32ab5ff4215b44128668858d6fac131b12','kernel/rust/process_helpers.rs':'851acd51fab945456edd87c001a63b867634f51207fbf1900451edaa368b09ea'}
for rel,h in expected.items():assert ref(R/rel)['sha256']==h,(rel,'canonical frozen preimage drift')
preimages={rel:ref(R/rel) for rel in expected};origins={};merge_records=[]
def merge(relative,variants):
 base=(R/relative).read_text();a=base.splitlines(True);edits=[]
 for label,path in variants:
  raw=path.read_text();b=raw.splitlines(True)
  for tag,i,j,k,l in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
   if tag!='equal':edits.append(dict(owner=label,start=i,end=j,replacement=b[k:l],source=ref(path)))
 spans=sorted((e['start'],e['end'],e['owner']) for e in edits if e['start']!=e['end'])
 for left,right in zip(spans,spans[1:]):assert left[1]<=right[0],(relative,'source overlap',left,right)
 for e in edits:
  if e['start']==e['end']:assert e['start']==len(a) or not any(i<e['start']<j for i,j,_ in spans),(relative,'insertion overlap')
 # Same EOF append positions are concatenated in explicit source-owner order.
 by_position=collections.defaultdict(list)
 for e in edits:by_position[(e['start'],e['end'])].append(e)
 out=a[:]
 for (i,j),rows in sorted(by_position.items(),reverse=True):
  if i!=j:assert len(rows)==1
  out[i:j]=[line for e in rows for line in e['replacement']]
 result=''.join(out)
 for e in edits:
  if e['replacement']:assert ''.join(e['replacement']) in result,(relative,e['owner'],'lost exact delta')
 merge_records.append(dict(relative=relative,base=ref(R/relative),edits=[dict(owner=e['owner'],base_line_interval=[e['start'],e['end']],replacement_lines=len(e['replacement']),source=e['source']) for e in edits],overlaps=0))
 return result
selected={}
selected['kernel/syscall.c']=merge('kernel/syscall.c',[('F03-four',FOUR/'candidate/kernel/syscall.c'),('F03-do-exit',EXIT/'candidate/kernel/syscall.c'),('F03-qualified-five-backlog',BACK/'candidate/kernel/syscall.c')])
selected['kernel/rust/syscall_policy.rs']=merge('kernel/rust/syscall_policy.rs',[('F03-four',FOUR/'candidate/kernel/rust/syscall_policy.rs'),('F03-do-exit',EXIT/'candidate/kernel/rust/syscall_policy.rs'),('F03-qualified-five-backlog',BACK/'candidate/kernel/rust/syscall_policy.rs'),('F06-qualified-six',F6/'overlay/kernel/rust/syscall_policy.rs')])
selected['kernel/rust/lib.rs']=(FOUR/'candidate/kernel/rust/lib.rs').read_text();selected['arch/x86_64/kernel/syscall.c']=(F6/'overlay/arch/x86_64/kernel/syscall.c').read_text();selected['kernel/process.c']=(R/'kernel/process.c').read_text();selected['kernel/rust/process_helpers.rs']=(R/'kernel/rust/process_helpers.rs').read_text()
back=json.loads((BACK/'SLICES.json').read_text());f3defs=['MCKERNEL_RUST_F03_PERF_ATTR_CALLBACKS','MCKERNEL_RUST_F03_PRLIMIT_BODY','MCKERNEL_RUST_F03_EXEC_DEFINED_TAIL','MCKERNEL_RUST_F03_DO_EXIT_V2']+[s['cflag'] for s in back];f3cfg=['f03_prlimit_body_candidate','f03_do_exit_supported_candidate']+[s['cfg'] for s in back]
f6bind=json.loads((F6/'BATCH-SOURCE-BINDINGS.json').read_text());f6defs=f6bind['paired_C_defines'];f6cfg=f6bind['paired_Rust_cfgs'];assert f6bind['USE_NOCACHE_MMAP_defined'] is False and f6bind['Rust_f06_use_nocache_mmap'] is False
modules={}
for rel,row in json.loads((proofs[0]).read_text())['postimages'].items():
 if rel.startswith('kernel/rust/f03_'):modules[rel]=Path(row['path'])
for p in (F6/'overlay/kernel/rust').glob('f06_*.rs'):modules['kernel/rust/'+p.name]=p
assert len(modules)==7
# Bind new defaults only to the existing proven x86_64 Linux6.12/no-UBSAN branch.
cm=(R/'kernel/CMakeLists.txt').read_text();needle='\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_syscall_table_clone3")'
block='\n\t\t\t# Qualified next cohort: current native x86_64 Linux6.12, no UBSAN.\n\t\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n'+''.join('\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "'+c+'")\n' for c in f3cfg+f6cfg)+''.join('\t\t\t\tlist(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/'+rel.removeprefix('kernel/')+'")\n' for rel in modules)+'\t\t\tendif()'
assert cm.count(needle)==1;cm=cm.replace(needle,needle+block)
needle='\t\t\tCOMPILE_DEFINITIONS MCKERNEL_RUST_PROCESS_GLOBAL_STORAGE)'
block='\n\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n\t\t\tset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY\n\t\t\t\tCOMPILE_DEFINITIONS "'+';'.join(f3defs)+'")\n\t\t\tset_property(SOURCE "${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/syscall.c" APPEND PROPERTY\n\t\t\t\tCOMPILE_DEFINITIONS "'+';'.join(f6defs)+'")\n\t\tendif()'
assert cm.count(needle)==1;cm=cm.replace(needle,needle+block);selected['kernel/CMakeLists.txt']=cm
for rel,p in modules.items():selected[rel]=p.read_text();origins[rel]=ref(p)
for rel,text in selected.items():
 p=D/'candidate'/rel;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);p.write_text(text);p.chmod(0o400)
 old=(R/rel).read_text() if (R/rel).exists() else ''
 diff=''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile=rel if old else '/dev/null',tofile=rel))
 if diff:(D/'patches').mkdir(mode=0o700,exist_ok=True);(D/'patches'/(rel.replace('/','__')+'.patch')).write_text(diff)
# Freeze only the Rust subtree, including all unchanged ordinary files. One
# existing directory bind target avoids absent leaf mounts under the RO /src.
snapshot=D/'rust-subtree';snapshot.mkdir(mode=0o700);records=[]
for p in sorted((SRC/'kernel/rust').rglob('*')):
 assert not p.is_symlink(),p
 if p.is_dir():continue
 assert p.is_file();rel=p.relative_to(SRC/'kernel/rust');target=snapshot/rel;target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);target.write_bytes(p.read_bytes());target.chmod(0o400);records.append(dict(relative=rel.as_posix(),original=ref(p),snapshot=ref(target),kind='unchanged source6153 subtree'))
byrel={r['relative']:r for r in records}
for rel in [r for r in selected if r.startswith('kernel/rust/')]:
 short=rel.removeprefix('kernel/rust/');target=snapshot/short
 if target.exists():target.chmod(0o600)
 target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);target.write_bytes(selected[rel].encode());target.chmod(0o400)
 origin=origins.get(rel,ref(D/'candidate'/rel));entry=dict(relative=short,original=byrel.get(short,{}).get('original'),snapshot=ref(target),kind='qualified/coherent successor postimage',qualified_origin=origin)
 byrel[short]=entry
manifest=dict(scope=__doc__.splitlines()[0],runtime_authority=None,schema='mckernel.exact-kernel-rust-subtree-readonly.v1',base_source_root=str(SRC/'kernel/rust'),export_root=str(snapshot),container_destination='/src/kernel/rust',files=[byrel[k] for k in sorted(byrel)],new_leaf_files=sorted(set(byrel)-{r['relative'] for r in records}),total_bytes=sum(r['snapshot']['bytes'] for r in byrel.values()),no_symlinks=True,no_hardlinks=True,original_source_mutations=0)
write(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json',manifest)
plan=dict(scope=__doc__.splitlines()[0],status='PRIVATE_MERGED_QUALIFIED_NEXT_COHORT_SOURCE_ONLY_NO_COMPILER',runtime_authority=None,source_preimages=preimages,source_postimages={rel:ref(D/'candidate'/rel) for rel in selected},qualified_evidence=[ref(p) for p in proofs],merged_source_regions=merge_records,selection=dict(kernel_syscall_C_defines=f3defs,arch_syscall_C_defines=f6defs,Rust_cfg_additions=f3cfg+f6cfg,new_options=False,CMake_supported_scope='Existing linux-6.12 branch, ARCH=x86_64, ENABLE_UBSAN=OFF; actual DCFA undefined and retained spinlock ABI remain required before admission',USE_NOCACHE_MMAP=False,f06_use_nocache_mmap=False),held_OFF=['F03 next-termination-provider-backlog-1 (no actual qualified result at selection)','F06 source-only process_vm/other unqualified selectors','held whole do_mmap/do_fork/terminate implementations and unsupported configs'],rust_directory_export=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'),canonical_mutations=0,compiler_runs=0,default_native_acceptance=False,nonce=None,request_sha256=None,resource_authority=None,independent_execution_release=None)
write(D/'COHERENT-NEXT-SOURCE-PLAN.NOT-GRANTED.json',plan)
print(json.dumps(dict(status=plan['status'],postimages=len(selected),Rust_subtree_files=len(byrel),Rust_subtree_bytes=manifest['total_bytes'],new_Rust_leaves=manifest['new_leaf_files'],merge_overlaps=0)))
