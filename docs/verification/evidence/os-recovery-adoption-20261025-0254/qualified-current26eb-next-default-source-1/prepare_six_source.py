"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private exact six-function source union; no timer acceptance or workload action.
"""
from pathlib import Path
import hashlib,json,difflib
D=Path(__file__).resolve().parent;E=D.parent;R=Path('/home/holden/mckernel');F3=E/'m14-f03-current26eb-three-selected-bridges-source-1';F6=E/'m14-f06-selected-residual-implementation-20261026-1/next-three-26eb-bridges-source-1'
def ref(p):
 raw=p.read_bytes();return dict(path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def read(p):return json.loads(p.read_text())
def save(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
def auth(row):
 p=Path(row['path']);assert ref(p)==row;return p
def once(s,a,b):
 assert s.count(a)==1,(a[:90],s.count(a));return s.replace(a,b,1)
assert ref(F3/'ACTUAL-HOST-HANDOFF.json')['sha256']=='13c162ca28351cd3724ca5acd6b858245bbaef484a73ed69f3db9acf140bc768'
assert ref(F6/'actual-three-host-1/HANDOFF.json')['sha256'].startswith('3ba78ed6')
f3=read(F3/'THREE-SOURCE-SLICES.json');selected={rel:auth(row).read_text() for rel,row in f3['source_postimages'].items()};pre=dict(f3['source_preimages']);arch='arch/x86_64/kernel/syscall.c';policy='kernel/rust/syscall_policy.rs';cmake='kernel/CMakeLists.txt';C=(R/arch).read_text();pre[arch]=ref(R/arch);cfgs=[];defs=[];modules={};bindings=[]
for leaf in ['copy-to-user','copy-from-user','forward-context']:
 P=F6/leaf;ready=read(P/'READY.json');b=read(auth(ready['bindings']))
 for row in b['canonical_before']:assert ref(Path(row['path']))==row
 auth(b['provider_source']);newfile=ready['central_module_filename_required'];rel='kernel/rust/'+newfile;assert not (R/rel).exists() and rel not in modules
 original=b['original_C'];wrapper=b['C_wrapper'];base=(R/arch).read_text();following=base[:base.index(original)+len(original)].count('\n')+1;wrapper+='#line '+str(following)+'\n';C=once(C,original,wrapper)
 suffix=b['rust_selection'];assert suffix.count('"bridge.rs"')==1;suffix=suffix.replace('"bridge.rs"','"'+newfile+'"');selected[policy]+=suffix
 selected[rel]=auth(ready['candidate_module']).read_text();modules[rel]=ready['candidate_module'];cfgs.append(b['selectors']['Rust']);defs.append(b['selectors']['C']);bindings.append(dict(leaf=leaf,source=ready['bindings'],qualified_module=ready['candidate_module'],canonical_module=rel,body_bytes_unchanged=True,original_C=original,selected_C=wrapper))
selected[arch]=C;cm=(R/cmake).read_text();newcfg=f3['CMake_Root_plan']['new_Rust_cfgs']+cfgs
anchor='\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f06_process_vm_entry_candidate")';cm=once(cm,anchor,anchor+''.join('\n\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "'+cfg+'")' for cfg in newcfg))
anchor='\t\t\t\tlist(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_process_vm_entry.rs")';cm=once(cm,anchor,anchor+''.join('\n\t\t\t\tlist(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/'+rel.removeprefix('kernel/')+'")' for rel in modules))
cm=once(cm,'MCKERNEL_RUST_F03_SYNC_CHILD_EVENT"','MCKERNEL_RUST_F03_SYNC_CHILD_EVENT;'+';'.join(f3['CMake_Root_plan']['kernel_C_defines'])+'"')
cm=once(cm,'MCKERNEL_RUST_F06_PROCESS_VM_ENTRY"','MCKERNEL_RUST_F06_PROCESS_VM_ENTRY;'+';'.join(defs)+'"');selected[cmake]=cm
for rel,text in selected.items():
 p=D/'candidate'/rel;p.parent.mkdir(mode=0o700,parents=True,exist_ok=True);p.write_text(text);p.chmod(0o400);patch=D/'patches'/(rel.replace('/','__')+'.patch');patch.parent.mkdir(mode=0o700,exist_ok=True);old=(R/rel).read_text() if (R/rel).exists() else '';patch.write_text(''.join(difflib.unified_diff(old.splitlines(True),text.splitlines(True),fromfile=rel if old else '/dev/null',tofile=rel)))
plan=dict(scope=__doc__.splitlines()[0],status='SIX_HOST_QUALIFIED_FUNCTION_SOURCE_UNION_READY_TIMER_SEPARATE',runtime_authority=None,preimages=pre,postimages={rel:ref(D/'candidate'/rel) for rel in selected},qualified_F03=ref(F3/'ACTUAL-HOST-HANDOFF.json'),qualified_F06=ref(F6/'actual-three-host-1/HANDOFF.json'),F03_source=ref(F3/'THREE-SOURCE-SLICES.json'),F06_exact_sources=bindings,new_Rust_cfgs=newcfg,new_C_defines=dict(kernel=f3['CMake_Root_plan']['kernel_C_defines'],arch=defs),new_module_paths=list(modules),new_algorithm_bodies=0,current_C_FUNC_counts=[75,31],expected_C_FUNC_counts=[72,28],new_public_Rust_function_exports=['f03_exit_notify_wake','arch_copy_to_user_bridge','arch_copy_from_user_bridge','arch_syscall_forward_context_bridge'],existing_public_Rust_function_exports_reused=['f03_ptrace_io_find','f03_ptrace_io_unlock'],expected_new_Rust_import_removals=['arch_copy_to_user_bridge','arch_copy_from_user_bridge','arch_syscall_forward_context_bridge'],timer_included=False,timer_actual_result=None,canonical_Git_compiler_Docker_runtime_actions=0,default_acceptance=False,native_acceptance=False,whole_file_retired=False)
save('SIX-FUNCTION-SOURCE-UNION.NOT-GRANTED.json',plan);print(json.dumps(dict(status=plan['status'],postimages=len(selected),new_modules=list(modules),new_public_function_exports=4,C_FUNC_expected=[72,28])))
