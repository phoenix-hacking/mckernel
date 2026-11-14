"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private selective current115 integration of the accepted 12B shmget adapter.
"""
from pathlib import Path
import ast,copy,difflib,hashlib,json,re
D=Path(__file__).resolve().parent;E=D.parent;R=Path('/home/holden/mckernel');N=Path('/home/holden/mckernel-work/host-preparation/velocity-intervention-20261026-1/restart-20261027-1717/f06-second-family-qualification-source-1');A=E/'ROOT-CURRENT115-LOCAL31-CPUID-BUILD-ADMISSION-1';HOST=E/'foreground-f06-shmget-current114-abi-source-1/local-target-identity-reader-correction-source-1/independent-actual-host-review-1/REVIEW.json'
def ref(p):
 p=Path(p);b=p.read_bytes();return dict(path=str(p),bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
def read(p):return json.loads(Path(p).read_text())
def put(n,x):(D/n).write_text(json.dumps(x,indent=2)+'\n')
assert ref(HOST)['sha256'].startswith('67fadd26');accepted=read(HOST);assert accepted['actual_acceptance']['Rust_adapter_bytes']==12 and accepted['actual_acceptance']['existing_Rust_do_shmget_bytes']==2993
arch=R/'arch/x86_64/kernel/syscall.c';lib=R/'kernel/rust/lib.rs';cmake=R/'kernel/CMakeLists.txt';origin=R/'scripts/f06_origin_command_profile.json';derive=R/'scripts/derive_f06_origin.py';policy=R/'kernel/rust/syscall_policy.rs'
assert ref(arch)['sha256']=='d060dbf5b83e29b1d5f16e7504972f05cb53d553fb754de1a67566d2c0f06b37'
archold=arch.read_text();old='''int
arch_do_shmget_bridge(long key, size_t size, int shmflg)
{
\treturn do_shmget((key_t)key, size, shmflg);
}''';new='''#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F06_SHMGET_DISPATCH)
extern int arch_do_shmget_bridge(long key, size_t size, int shmflg);
#else
#line 687
'''+old+'''
#endif
#line 692''';assert archold.count(old)==1;archnew=archold.replace(old,new,1)
# Exact frozen old114 selector body, only composition base is newer115.
assert (N/'syscall.c.diff').read_text().count('MCKERNEL_RUST_F06_SHMGET_DISPATCH')==1
libold=lib.read_text();libanchor='mod shmid_helpers;';libpost=libanchor+'\n#[cfg(f06_shmget_dispatch_candidate)]\nmod f06_shmget_dispatch;';assert libold.count(libanchor)==1;libnew=libold.replace(libanchor,libpost,1)
cmold=cmake.read_text();cmanchor='''\t\t\t\tset_property(SOURCE "${MCKERNEL_F06_C_SOURCE}" APPEND PROPERTY
\t\t\t\t    COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_OBTAIN_CLONE_CPUID")''';cmadd='''
\t\t\t\t# Existing genuine-ABI shmget adapter; same supported profile/provider.
\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f06_shmget_dispatch_candidate")
\t\t\t\tlist(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_shmget_dispatch.rs")
\t\t\t\tset_property(SOURCE "${MCKERNEL_F06_C_SOURCE}" APPEND PROPERTY
\t\t\t\t    COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_SHMGET_DISPATCH")''';assert cmold.count(cmanchor)==1;cmnew=cmold.replace(cmanchor,cmanchor+cmadd,1)
leaf=(N/'f06_shmget_dispatch.rs').read_text();originalorigin=read(origin);neworigin=copy.deepcopy(originalorigin);neworigin['composed_arch_source_sha256']=hashlib.sha256(archnew.encode()).hexdigest();selected=[x for x in neworigin['exact_commands'] if x['stage']=='selected x86 syscall object'];assert len(selected)==1;assert '-DMCKERNEL_RUST_F06_OBTAIN_CLONE_CPUID' in selected[0]['argv'];selected[0]['argv'].insert(1,'-DMCKERNEL_RUST_F06_SHMGET_DISPATCH')
originnew=json.dumps(neworigin,sort_keys=True,indent=2)+'\n';deriveold=derive.read_text();assert hashlib.sha256(origin.read_bytes()).hexdigest() in deriveold;derivenew=deriveold.replace(hashlib.sha256(origin.read_bytes()).hexdigest(),hashlib.sha256(originnew.encode()).hexdigest(),1);ast.parse(derivenew)
values={'arch/x86_64/kernel/syscall.c':(archold,archnew),'kernel/rust/lib.rs':(libold,libnew),'kernel/CMakeLists.txt':(cmold,cmnew),'kernel/rust/f06_shmget_dispatch.rs':(None,leaf),'scripts/f06_origin_command_profile.json':(origin.read_text(),originnew),'scripts/derive_f06_origin.py':(deriveold,derivenew)};writes=[]
for relative,(before,after) in values.items():
 out=D/'candidate'/relative;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(after)
 if before is not None:
  pre=D/'preimages'/relative;pre.parent.mkdir(parents=True,exist_ok=True);pre.write_text(before)
  patch=D/'patches'/(relative.replace('/','__')+'.patch');patch.parent.mkdir(exist_ok=True);patch.write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative)))
 writes.append(dict(relative=relative,preimage=ref(R/relative) if before is not None else None,postimage=ref(out)))
assert archnew.replace(new,old,1)==archold and libnew.replace(libpost,libanchor,1)==libold and cmnew.replace(cmanchor+cmadd,cmanchor,1)==cmold
# No algorithm change in immutable origin producer; only exact profile SHA literal.
assert re.sub(r'PROFILE_SHA256 = "[0-9a-f]{64}"','PROFILE_SHA256 = "BOUND"',deriveold)==re.sub(r'PROFILE_SHA256 = "[0-9a-f]{64}"','PROFILE_SHA256 = "BOUND"',derivenew)
bodyold=copy.deepcopy(originalorigin);bodynew=copy.deepcopy(neworigin);bodyold.pop('composed_arch_source_sha256');bodynew.pop('composed_arch_source_sha256');next(x for x in bodynew['exact_commands'] if x['stage']=='selected x86 syscall object')['argv'].remove('-DMCKERNEL_RUST_F06_SHMGET_DISPATCH');assert bodyold==bodynew
put('SIX-PATH-SELECTIVE-INTEGRATION.NOT-AUTHORITY.json',dict(scope=__doc__.splitlines()[0],status='READY_PRIVATE_SHM12_SELECTIVE_CURRENT115_SOURCE_NOT_ADOPTED',writes=writes,qualified_HOST=ref(HOST),frozen_leaf=ref(N/'f06_shmget_dispatch.rs'),frozen_C_selector=ref(N/'syscall.c.diff'),existing_provider_policy_unchanged=ref(policy),generic_F03_trio_and_WAKE4_policy_writes=0,root_lib_CMake_edit_sites=[dict(path='kernel/rust/lib.rs',anchor=libanchor,after=libpost),dict(path='kernel/CMakeLists.txt',anchor=cmanchor,after=cmanchor+cmadd)],preserved_CPUID_arch_source=True,origin_producer_algorithm_unchanged=True,origin_profile_changes_only=['composed_arch_source_sha256','selected arch argv adds paired SHM selector'],default_selected_within_existing_supported_CPUID_branch=True,new_optional_runtime_profiles=0,all_original_C_fallback_and_logical_line_anchors_preserved=True,actual_source_adoption=None,compiler_or_workload_execution=0))
profile=read(A/'PROFILE.SOURCE-ONLY.json');rustcmd=copy.deepcopy(profile['exact_commands'][0]);rustcmd['argv'][-1:-1]=['--cfg','f06_shmget_dispatch_candidate'];archcmd=copy.deepcopy(profile['exact_commands'][2]);archcmd['argv'].insert(1,'-DMCKERNEL_RUST_F06_SHMGET_DISPATCH');rawcmd=copy.deepcopy(profile['exact_commands'][3]);commands=[rustcmd,archcmd,rawcmd]
put('EXACT-SHM-ONLY-PRODUCTION-PROPOSAL.NOT-GRANTED.json',dict(scope=__doc__.splitlines()[0],status='THREE_SHM_DELTA_OPERATIONS_SOURCE_ONLY_NOT_UNION_OR_EXECUTION_PROFILE',base_production_profile=ref(A/'PROFILE.SOURCE-ONLY.json'),exact_commands=commands,additional_sourceonly_origin_prerequisite={'producer':'/src/scripts/derive_f06_origin.py','profile':'/src/scripts/f06_origin_command_profile.json','actual_source':'/src/arch/x86_64/kernel/syscall.c','output':'/work/output/build/kernel/f06-origin','action':'Root reuse existing CMake/origin materializer against sixfile successor; fresh genuine origin outputs required, no old115 origin receipt reuse'},new_compile_objects=['rust/mckernel_rust.o','CMakeFiles/mckernel.img.dir/__/arch/x86_64/kernel/syscall.c.o'],retained_process115_object_requires_actual_accepted_custody_ref=None,remaining_eight_rawlink_inputs='Reuse exact current115 accepted actual refs only after actual artifact acceptance; no source-only provenance substitution',prospective_Rust_closed_source_manifest='Current115120-file exact manifest plus one exact f06_shmget_dispatch.rs and localizedlib replacement; Rootclosedsourcecomposer owns actualmap',combined_generic7body_batch='Root merges additional generic syscallC flags/object and sharedlib/CMake inserts from f05_adapter_export; no three-command union claim',new_native_quota=0,grant=None,current_ledger=None,source_publication=None,actual_artifact_acceptance=None))
put('PRODUCTION-ABI-LINK-CURRENT-CONSUMER-REQUIREMENTS.json',dict(scope=__doc__.splitlines()[0],qualified_HOST=ref(HOST),new_current_production_artifacts_unrun=True,requirements=['Use genuine current wholeRust abi::CInt/CLong/SizeT; exact frozenadapter source, signed long→CInt narrowing, existing do_shmget public C ABI/key_t width; no ABI mirrors','Actual wholeRust unique GLOBAL FUNC arch_do_shmget_bridge in executable storage; new selected archC has no same defined function; final rawimage unique same Rustprovider','Actual new sys_shmget338B retains callback R_X86_64_64 at owningbodyoffset104/addend0 to new Rustleaf, provider currentdo_shmget2993B remains genuine existingimplementation','Reprove actual12B adapter complete nonrelocationbytes/directtailcall relocation to do_shmget2993B and final binding; preserve all currentconsumers/providerbytes at exact compiler/default flags','ArchCPUID selected Rustowner and its generated FILE/FUNC/lineflags metadata persist; original Cfallback logicalcoordinates/pointerorigins remain exact under helperOFF/selectorOFF','Currentproduction non-targetarch C/storage invariants require current115→newobject proof with sourceboundlocalidentity handling, not extrapolation of old11418bodyfixturecounts','Use unchanged existing production rawlink/ABI/registry/import witness machinery; existing SDK/3640semantic/4HOSTproducer outputs/reader acceptance reused without replay'],retained_HOST_counts_only=accepted['actual_acceptance'],native_IPC_context_frame_holds=['do_shmget resource_set/IPC locking/lifetime/allocation semantics still require matching native case context','No nativeIPC/cancellation/actualframe or completefile retirement acceptance from leafcompile/link alone','No new native allowance; Root may integrate batch under existing current ownership/resource/time/account controls'],wholefile_default_native_credit=0))
print('PASS private sixpath SHM12 integration; current115 CPUID preserved; originalgorithm unchanged/profile sourceandargv minimally rebound; threeoperation SHMonly future recipe unrun')
