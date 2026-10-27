"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private exact-source composition; no compiler, runtime, Git or canonical writes.
"""
from pathlib import Path
import copy,difflib,hashlib,json,stat
D=Path(__file__).resolve().parent;E=D.parent;R=Path('/home/holden/mckernel')
B=E/'ROOT-NEXT10-DEFAULT-BUILD-ADMISSION-1'
F3=E/'m14-f03-selected-residual-implementation-20261026-1/next-selected-residual-backlog-1/current-next10-context-successor-1'
F6=E/'m14-f06-selected-residual-implementation-20261026-1/next-process-vm-consumer-source-1'
def ref(p):
 b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def save(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
def auth(x):
 p=Path(x['path']);assert ref(p)==x,('changed input',x);return p
def once(text,old,new):
 assert text.count(old)==1,('exact integration context',old[:120],text.count(old));return text.replace(old,new,1)
prehash={'kernel/syscall.c':'8b8037ce23d364847fbdfdce2bc67bfea66668bd8574e752d8c0848ea6d0da8c','kernel/rust/syscall_policy.rs':'5bc789e1a842a93d64047a7b97e888cdff3ee429de394006d8d522ab3951833c','kernel/CMakeLists.txt':'edbd78df1f50bc3e9d1bcdf5e06712be3902d3ec2b5d754f4ef584835cedd51e','arch/x86_64/kernel/syscall.c':'d3cd4d9a9bb1a604dfa5da28b02aef033fb78510a4aed24905b3dedec10ed96c'}
pre={rel:ref(R/rel) for rel in prehash}
assert all(pre[rel]['sha256']==sha for rel,sha in prehash.items()),'canonical context differs'
f3=json.loads((F3/'SOURCE-HANDOFF.NOT-GRANTED.json').read_text());h3=json.loads((F3/'ACTUAL-SCOPED-RESULT-HANDOFF.json').read_text());h6=json.loads((F6/'controlled-public-entry-driver-source-1/future-output-2/HANDOFF.json').read_text())
assert ref(F3/'SOURCE-HANDOFF.NOT-GRANTED.json')['sha256']=='a640afabdcb6fca3fa621ab1353e4df44c3e339de87f8e4847402ac432bb7ec3'
assert ref(F6/'controlled-public-entry-driver-source-1/future-output-2/HANDOFF.json')['sha256'].startswith('a252a9c4')
assert h3['all_returncodes']==[0,0,0] and h3['actual_checks']['original_C_Rust_graph_pairs']==3072
assert h6['actual_scope']['C_Rust_ABI_facts']==22 and h6['actual_scope']['controlled_READ_WRITE_pairs']==40 and all(x['rc']==0 for x in h6['children'])
selected={}
for row in f3['private_selector_postimages']:
 rel=row['relative'];assert auth(row['preimage']).read_bytes()==(R/rel).read_bytes();selected[rel]=auth(row['postimage']).read_text()
policy='kernel/rust/syscall_policy.rs';arch='arch/x86_64/kernel/syscall.c';cmake='kernel/CMakeLists.txt'
old=(F6/'BASE.syscall_policy.rs').read_text();post=(F6/'syscall_policy.rs').read_text();assert post.startswith(old);suffix=post[len(old):]
assert suffix.count('mod f06_process_vm_entry;')==1 and 'mod f06_process_vm_entry;' not in selected[policy]
selected[policy]+=suffix
# The F06 guard-only edits are applied by exact old-text contexts, preserving all
# four later NEXT10 selectors in the current architecture C source.
old=(F6/'BASE.syscall.c').read_text().splitlines(True);new=(F6/'syscall.c').read_text().splitlines(True);current=(R/arch).read_text();edits=[]
for tag,i,j,k,l in difflib.SequenceMatcher(None,old,new,autojunk=False).get_opcodes():
 if tag=='equal':continue
 # Include three lines either side so insertion-only edits have exact authority.
 lo=max(0,i-3);hi=min(len(old),j+3);before=''.join(old[lo:hi]);after=''.join(old[lo:i]+new[k:l]+old[j:hi]);current=once(current,before,after);edits.append(dict(old_line_start=i,old_line_end=j,old_context_sha256=hashlib.sha256(before.encode()).hexdigest()))
selected[arch]=current
cm=(R/cmake).read_text()
for cfg in ['f03_sync_child_event_candidate','f06_process_vm_entry_candidate']:
 needle='\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f06_vdso_set_range_candidate")';cm=once(cm,needle,needle+'\n\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "'+cfg+'")')
needle='\t\t\t\tlist(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_vdso_set_range.rs")';cm=once(cm,needle,needle+'\n\t\t\t\tlist(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_process_vm_entry.rs")')
for old,new in [('MCKERNEL_RUST_F03_PTRACE_IO_COPY_FROM"','MCKERNEL_RUST_F03_PTRACE_IO_COPY_FROM;MCKERNEL_RUST_F03_SYNC_CHILD_EVENT"'),('MCKERNEL_RUST_F06_VDSO_SET_RANGE"','MCKERNEL_RUST_F06_VDSO_SET_RANGE;MCKERNEL_RUST_F06_PROCESS_VM_ENTRY"')]:cm=once(cm,old,new)
selected[cmake]=cm;leaf='kernel/rust/f06_process_vm_entry.rs';assert not (R/leaf).exists();selected[leaf]=(F6/'f06_process_vm_entry.rs').read_text()
assert hashlib.sha256(selected[leaf].encode()).hexdigest()=='0e9d9d23db1a376f38757fba98c6b34d0aed4f4b6c45398b0b9372d7624c3d2e'
for rel,text in selected.items():
 p=D/'candidate'/rel;p.parent.mkdir(parents=True,exist_ok=True,mode=0o700);p.write_text(text);p.chmod(0o400)
 p=D/'patches'/(rel.replace('/','__')+'.patch');p.parent.mkdir(exist_ok=True,mode=0o700);p.write_text(''.join(difflib.unified_diff((R/rel).read_text().splitlines(True) if (R/rel).exists() else [],text.splitlines(True),fromfile=rel if (R/rel).exists() else '/dev/null',tofile=rel)))
P=json.loads((B/'PROFILE.SOURCE-ONLY.json').read_text());oldexport=P['inputs']['source_directory_exports'][0];oldmap=json.loads(auth(oldexport['manifest']).read_text());snapshot=D/'rust-subtree';snapshot.mkdir(mode=0o700);rows={}
for row in oldmap['files']:
 src=auth(row['snapshot']);target=snapshot/row['relative'];target.parent.mkdir(mode=0o700,parents=True,exist_ok=True);target.write_bytes(src.read_bytes());target.chmod(0o400);rows[row['relative']]=dict(row,predecessor_snapshot=row['snapshot'],snapshot=ref(target))
for rel in [policy,leaf]:
 short=rel.removeprefix('kernel/rust/');p=snapshot/short
 if p.exists():p.chmod(0o600)
 p.write_bytes((D/'candidate'/rel).read_bytes());p.chmod(0o400);rows[short]=dict(rows.get(short,{}),relative=short,snapshot=ref(p),qualified_origin=ref(D/'candidate'/rel),kind='qualified sync/processVM successor')
manifest=dict(oldmap,export_root=str(snapshot),files=[rows[k] for k in sorted(rows)],new_leaf_files=['f06_process_vm_entry.rs'],changed_predecessor_files=['syscall_policy.rs'],predecessor_manifest=oldexport['manifest'],total_bytes=sum(x['snapshot']['bytes'] for x in rows.values()),original_source_mutations=0);save('RUST-SUBTREE-CLOSED-SOURCE-MAP.json',manifest)
P.update(status='STATIC_QUALIFIED_SYNC_PROCESSVM_ON_ACCEPTED_F42_NOT_GRANTED',runtime_authority=None,request_sha256=None,native_custody_clearance=None)
P['inputs']['source_directory_exports']=[dict(oldexport,host_path=str(snapshot),manifest=ref(D/'RUST-SUBTREE-CLOSED-SOURCE-MAP.json'))]
for row in P['inputs']['postimages']:
 if row['relative'] in selected:row['postimage']=ref(D/'candidate'/row['relative']);row['postimage_mode']=0o400
for index,cfgs in [(0,['f03_sync_child_event_candidate','f06_process_vm_entry_candidate']),(1,['MCKERNEL_RUST_F03_SYNC_CHILD_EVENT']),(2,['MCKERNEL_RUST_F06_PROCESS_VM_ENTRY'])]:
 argv=P['exact_commands'][index]['argv'];pos=next(i for i,a in enumerate(argv) if a.startswith('--emit=obj=')) if index==0 else next(i for i,a in enumerate(argv) if a.startswith('-I'));argv[pos:pos]=[t for cfg in cfgs for t in ['--cfg',cfg]] if index==0 else ['-D'+x for x in cfgs]
for row in P['inputs']['objects']:
 if row['replace']:
  p=B/'OUTPUT/work/output/build'/row['build_relative'];row.update(source=ref(p),retained_archive_member=str(p),action='new qualified sync/processVM object; accepted F42 predecessor provenance')
P['cohort_source_bindings']=[dict(relative=x['relative'],postimage=x['postimage']) for x in P['inputs']['postimages']]+[dict(relative='kernel/rust/'+x['relative'],postimage=x['snapshot']) for x in manifest['files']]
P['reuse_descriptor']=str(D/'FROZEN-SYNC-PROCESSVM-EIGHT-OBJECT-REUSE-INPUTS.json');P['producer_contract']['source']='Accepted F42 plus exact HOST-qualified sync child/processVM selectors; unchanged eight C prefixes, closed106-fileRust directory';save('PROFILE.SOURCE-ONLY.json',P)
reuse=json.loads(Path(json.loads((B/'PROFILE.SOURCE-ONLY.json').read_text())['reuse_descriptor']).read_text());reuse.update(schema='mckernel.qualified-sync-processvm-four-command-eight-object-reuse.v1',objects=P['inputs']['objects'],postimages=P['inputs']['postimages'],source_directory_exports=P['inputs']['source_directory_exports'],runtime_authority=None,future_nonce=None,future_pid=None);reuse['commands']['exact_four_literal_argv']=P['exact_commands'];save('FROZEN-SYNC-PROCESSVM-EIGHT-OBJECT-REUSE-INPUTS.json',reuse)
export=json.loads((B/'ROOT-ACTUAL-READONLY-INPUT-EXPORT-AUTHORITY.json').read_text());export.update(author=None,decision=None,status='STATIC_SYNC_PROCESSVM_EXPORT_DRAFT_NOT_AUTHORITY',request_sha256=None,runtime_authority=None);export['qualified_readonly_files']=[x['source'] for x in P['inputs']['configuration']]+[x['source'] for x in P['inputs']['objects'] if not x['replace']]+[x['postimage'] for x in P['inputs']['postimages']]+[x['snapshot'] for x in manifest['files']];save('INPUT-EXPORT.DRAFT.NOT-AUTHORITY.json',export)
plan=dict(scope=__doc__.splitlines()[0],status='PRIVATE_HOST_QUALIFIED_SYNC_PROCESSVM_SOURCE_NOT_DEFAULT_ACCEPTANCE',runtime_authority=None,preimages=pre,postimages={rel:ref(D/'candidate'/rel) for rel in selected},qualified_F03_source=ref(F3/'SOURCE-HANDOFF.NOT-GRANTED.json'),qualified_F03_actual=ref(F3/'ACTUAL-SCOPED-RESULT-HANDOFF.json'),qualified_F06_source=ref(F6/'SOURCE-BINDINGS.json'),qualified_F06_actual=ref(F6/'controlled-public-entry-driver-source-1/future-output-2/HANDOFF.json'),baseline_profile=ref(B/'PROFILE.SOURCE-ONLY.json'),baseline_actual_producer=ref(B/'OUTPUT/work/evidence/producer-contract.json'),new_Rust_cfgs=['f03_sync_child_event_candidate','f06_process_vm_entry_candidate'],new_C_defines=dict(kernel=['MCKERNEL_RUST_F03_SYNC_CHILD_EVENT'],arch=['MCKERNEL_RUST_F06_PROCESS_VM_ENTRY']),new_Rust_algorithm_bodies=0,new_leaf_files=[leaf],shared_policy_merge='Exact F03 current5bc789e1 suffix plus F06 unchanged module declaration; no existing body edits',F06_exact_context_edits=edits,prior_NEXT10_preserved=True,closed_Rust_files=len(rows),retained_C_inputs=8,new_objects=3,commands=4,USE_NOCACHE_MMAP_defined=False,holds=['real MM/usercopy/fault/concurrency','VMlock192/ABI6 direct receipt unresolved','final-reference/current-stack ownership','real event initialization/list/PMU concurrency ownership','matching default/native proof'],actual_Root_admission=None,actual_request_sha256=None,actual_nonce=None,actual_resource_authority=None,independent_execution_release=None,default_acceptance=False,native_acceptance=False,whole_file_retirement=False)
save('COHERENT-SOURCE-PLAN.NOT-GRANTED.json',plan);print(json.dumps(dict(status=plan['status'],canonical_postimages=len(selected),Rust_files=len(rows),commands=4,retained_C_inputs=8)))
