#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare only this private vDSO logger candidate and its exact ordinary HOST plan.
"""
import difflib,hashlib,json,re
from pathlib import Path
ROOT=Path('/home/holden/mckernel');HERE=Path(__file__).resolve().parent
E=ROOT/'docs/verification/evidence/os-recovery-adoption-20261025-0254'
BODY11=E/'m14-f06-next-runtime-body11-restart-20261028-1'
BODY7=E/'m14-f06-next-runtime-body7-restart-20261028-1'
BODY6=E/'m14-f06-next-runtime-body6-restart-20261028-1'
SOURCE116=E/'m14-f06-next-runtime-body4-restart-20261028-1/BASE.syscall.c'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def bind(path):
 data=path.read_bytes();return {'path':str(path),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
def verify(row):assert bind(Path(row['path']))==row,row['path']
def dump(name,value):(HERE/name).write_text(json.dumps(value,indent=2)+'\n')
def lines(source):
 result={};at=0;logical=1
 for line in source.splitlines(True):
  result[at]=logical;match=re.fullmatch(r'\s*#line\s+(\d+)\s*\n?',line);logical=int(match.group(1))if match else logical+1;at+=len(line)
 result[at]=logical;return result
pre11=json.loads((BODY11/'PREIMAGES.json').read_text())
for row in pre11['all_nine_root118_canonical_postimages'].values():verify(row)
snapshots={}
for relative,name in [('arch/x86_64/kernel/syscall.c','BASE.syscall.c'),('kernel/rust/lib.rs','BASE.lib.rs'),('kernel/CMakeLists.txt','BASE.CMakeLists.txt'),('kernel/rust/abi.rs','abi.snapshot.rs')]:
 (HERE/name).write_bytes((ROOT/relative).read_bytes());snapshots[relative]={'canonical':bind(ROOT/relative),'snapshot':bind(HERE/name)}
marker='void\narch_vdso_map_log_bridge('
c=(HERE/'BASE.syscall.c').read_text();start=c.index(marker);end=c.index('\n}\n',start)+3;original=c[start:end]
c116=SOURCE116.read_text();s116=c116.index(marker);e116=c116.index('\n}\n',s116)+3;assert original==c116[s116:e116]
original_lines=lines(c116);current_lines=lines(c)
assert original_lines[s116]==3077and current_lines[start]==3079
site116=s116+original.index('\t\tdkprintf(');site116=c116.rfind('\n',0,site116)+1
assert original_lines[site116]==3084
(HERE/'original-vdso-map-log.c.inc').write_text(original)
registry_path=E/'F03-cumulative-next-source-1/CURRENT116-REGISTRY-REFERENCE.json';registry=json.loads(registry_path.read_text());assert registry['count']==389
records=[row for row in registry['records']if row['function']=='arch_vdso_map_log_bridge'];assert len(records)==1
expected={'file':'/src/arch/x86_64/kernel/syscall.c','function':'arch_vdso_map_log_bridge','fmt':None,'line':3084,'flags':0,'padding':0};assert records[0]==expected
decl='extern void arch_vdso_map_log_bridge(int event, int error, struct process_vm *vm,\n\t\tunsigned long a, unsigned long b, unsigned long c,\n\t\tunsigned long d, int pages);\n'
selected='#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F06_VDSO_MAP_LOG)\n'+decl+'#else\n#line 3077\n'+original+'#endif\n'+f'#line {current_lines[end]}\n'
result=c[:start]+selected+c[end:]
stack=[];frames=[];at=0
for line in c.splitlines(True):
 directive=re.match(r'^\s*#\s*(if|ifdef|ifndef|endif)\b',line)
 if directive:
  if directive.group(1)=='endif':frames.append((stack.pop(),at+len(line)))
  else:stack.append(at)
 at+=len(line)
exits=sorted(finish for begin,finish in frames if begin<start<end<finish)
for finish in sorted(exits,reverse=True):
 shifted=finish+len(selected)-len(original);result=result[:shifted]+f'#line {current_lines[finish]}\n'+result[shifted:]
lib=(HERE/'BASE.lib.rs').read_text();lib_after=lib+'\n#[cfg(f06_vdso_map_log_candidate)]\nmod f06_vdso_map_log;\n'
cmake=(HERE/'BASE.CMakeLists.txt').read_text();anchor='\t\t\t\t    COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_VDSO_INFO")\n';assert cmake.count(anchor)==1
addition='''
\t\t\t\t# Exact original vDSO map diagnostics, Rust descriptor and existing state provider.
\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f06_vdso_map_log_candidate")
\t\t\t\tlist(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_vdso_map_log.rs")
\t\t\t\tset_property(SOURCE "${MCKERNEL_F06_C_SOURCE}" APPEND PROPERTY
\t\t\t\t    COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_VDSO_MAP_LOG")
'''
cmake_after=cmake.replace(anchor,anchor+addition)
for relative,name,patchname,before,after in [('arch/x86_64/kernel/syscall.c','candidate.syscall.c','arch-selection.patch',c,result),('kernel/rust/lib.rs','candidate.lib.rs','rust-module-selection.patch',lib,lib_after),('kernel/CMakeLists.txt','candidate.CMakeLists.txt','cmake-selection.PROPOSAL.patch',cmake,cmake_after)]:
 (HERE/name).write_text(after);(HERE/patchname).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+relative,tofile='b/'+relative)));snapshots[relative]['proposed_postimage_sha256']=hashlib.sha256(after.encode()).hexdigest()
for source,name in [(BODY11/'debug.type.snapshot.rs','debug.type.snapshot.rs'),(BODY7/'syscall_policy.type.snapshot.rs','syscall_policy.type.snapshot.rs'),(BODY7/'f06_vdso_storage.rs','f06_vdso_storage.rs'),(BODY6/'f06_vdso_state.rs','f06_vdso_state.rs')]:
 (HERE/name).write_bytes(source.read_bytes())
(HERE/'runtime_vdso_map_log.rs').write_text('''// Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
// New exact logger, real descriptor and byte-identical banked state/storage providers.
#![no_std]
#![allow(dead_code,unexpected_cfgs)]
#[path="abi.snapshot.rs"]mod abi;
#[path="debug.type.snapshot.rs"]mod debug;
#[path="syscall_policy.type.snapshot.rs"]mod syscall_policy;
#[path="f06_vdso_storage.rs"]mod storage;
#[path="f06_vdso_state.rs"]mod state;
#[path="f06_vdso_map_log.rs"]mod candidate;
''')
suffix='''
extern struct ddebug selected_map_debug __asm__("mckernel_f06_vdso_map_debug");
extern struct ddebug __start___verbose[],__stop___verbose[];
struct ddebug *fixture_original_descriptor(void){struct ddebug *found=0;for(unsigned long address=(unsigned long)__start___verbose;address<(unsigned long)__stop___verbose;address+=sizeof(struct ddebug)){struct ddebug *row=(struct ddebug *)address;if(row==&selected_map_debug)continue;if(found)return 0;found=row;}return found;}
size_t fixture_descriptor_count(void){return ((unsigned long)__stop___verbose-(unsigned long)__start___verbose)/sizeof(struct ddebug);}
'''
(HERE/'oracle-suffix.c.inc').write_text(suffix)
oracle=(HERE/'oracle-prefix.c.inc').read_text()+'\nvoid arch_vdso_map_log_bridge(int,int,struct process_vm *,unsigned long,unsigned long,unsigned long,unsigned long,int) __asm__("original_arch_vdso_map_log_bridge");\n#line 3077 "/src/arch/x86_64/kernel/syscall.c"\n'+original+'\n'+suffix
(HERE/'oracle.c').write_text(oracle)
policy=(ROOT/'kernel/rust/syscall_policy.rs').read_text();caller_start=policy.index('unsafe fn arch_map_vdso_with_pages(');caller_end=policy.index('\n    let attr = PTATTR_ACTIVE | PTATTR_USER;',caller_start)
(HERE/'original-Rust-map-caller.rs.inc').write_text(policy[caller_start:caller_end])
public_start=policy.index('    fn arch_vdso_map_log_bridge(');public_end=policy.index('\n    );',public_start)+7
(HERE/'original-Rust-log-declaration.rs.inc').write_text(policy[public_start:public_end])
dump('ORIGINAL-DESCRIPTOR-IDENTITY.json',{'scope':SCOPE,'registry_reference':bind(registry_path),'accepted_registry_count':389,'selected_record':expected,'record_bytes':32,'alignment':8,'line_flags_offset':24,'flag_byte_offset':27,'actual116_source':bind(SOURCE116),'actual116_original_start':3077,'actual116_original_site':3084,'canonical118_start':current_lines[start],'canonical118_site':3086,'canonical118_site_drift_preexisting':2,'candidate_fallback_original_line_restore':3077,'candidate_Rust_descriptor_line':3084,'after_function_restores_canonical118_line':current_lines[end],'outer_exit_restores':[current_lines[x]for x in exits],'unrelated_source_not_rewritten':True,'oracle_function_identifier':'arch_vdso_map_log_bridge unchanged via asm-label alias, preserving __func__; only HOST #line sets original filename.'})
frontier=json.loads((BODY11/'SELECTED-CURRENT116-ARCH-FRONTIER.json').read_text());frontier.pop('target',None);targets=[row for row in frontier['selected_functions']if row['name']=='arch_vdso_map_log_bridge'];assert len(targets)==1and targets[0]['size']==255;frontier['target']=targets[0];dump('SELECTED-CURRENT116-ARCH-FRONTIER.json',frontier)
plan11=json.loads((BODY11/'FUTURE-HOST-COMMANDS.json').read_text());plan10=json.loads((E/'m14-f06-next-runtime-body10-restart-20261028-1/FUTURE-HOST-COMMANDS.json').read_text());flags=plan10['commands'][0]['argv'][:-4];out=HERE/'future-host-output-1';rustc=plan11['commands'][0]['argv'][0]
commands=[
 {'purpose':SCOPE+' Compile new Rust vDSO map logger/descriptor and byte-identical banked real Rust state/storage providers into one no_std object.','argv':[rustc,'--edition=2021','--crate-type=lib','--emit=obj','-C','opt-level=2','-C','panic=abort',str(HERE/'runtime_vdso_map_log.rs'),'-o',str(out/'runtime_vdso_map_log.o')]},
 {'purpose':SCOPE+' Compile genuine process/Ddebug/caller ABI, unchanged original C oracle and extern-only consumer; partial-link with actual Rust object, all storage/output HOST-mocked.','argv':flags+['-std=gnu11','-fno-builtin','-save-temps','-r','-nostdlib','-no-pie','-I',str(HERE),'-x','c',str(HERE/'oracle.c'),str(HERE/'consumer.c'),'-x','none',str(out/'runtime_vdso_map_log.o'),'-o',str(out/'joined.o')]},
 {'purpose':SCOPE+' Compile independent original C/Rust exact metadata, VM/PID/offset/argument/render/ownership fixture against actual partial link.','argv':[rustc,'--edition=2021','--test','-C','opt-level=2','-C','link-arg='+str(out/'joined.o'),'-C','link-arg=-no-pie',str(HERE/'fixture.rs'),'-o',str(out/'fixture')]},
 {'purpose':SCOPE+' Run56250 defined-domain original C/Rust map-log cases and7 ignored-VM cases, exact metadata and no-state-change checks; no mapping/provider/hardware effects.','argv':[str(out/'fixture'),'--exact','original_c_and_rust_vdso_map_log','--test-threads=1','--nocapture']},
]
dump('FUTURE-HOST-COMMANDS.json',{'scope':SCOPE,'status':'EXACT4NEW_ORDINARY_HOST_COMMANDS_UNRUN','cwd':str(HERE),'fresh_output':str(out),'commands':commands,'header_profile_argv_source':bind(E/'m14-f06-next-runtime-body10-restart-20261028-1/FUTURE-HOST-COMMANDS.json'),'expected_pairs':56250,'ignored_VM_cases':7,'environment':{'TMPDIR':str(out/'tmp'),'MCKERNEL_F06_RT_SIGRETURN_ORIGIN':expected['file']},'domain':'Mapped event: null vm, null proc, or correctly aligned live original ProcessVm/Process objects. Other events ignore vm. Exact typed int/unsigned-long formats; original signed offset converts modulo2^64. All storage/output own HOST mock.','future_default_checks':['Root compose this disjoint body/descriptor with frozen cumulative and BODY10/11, preserving accepted389-record metadata and all existing selectors.','Fullcrate/genuine selected+fallback C TU/defaultlink require one Rust map logger, one32B Rust __verbose target3084, no selected C definition, matching exact ProcessVm/Process layouts and no constructor.','Native matching-current ordinary map diagnostics/configuration proof before default/native/data/file credit.']})
pre=dict(pre11);pre.update(scope=SCOPE,status='PRIVATE118_VDSO_MAP_LOGGER_RUST_DESCRIPTOR_AND_REUSED_PROVIDER_SOURCE_READY',snapshots=snapshots,original_body=bind(HERE/'original-vdso-map-log.c.inc'),retained_object_frontier=bind(HERE/'SELECTED-CURRENT116-ARCH-FRONTIER.json'),descriptor_identity=bind(HERE/'ORIGINAL-DESCRIPTOR-IDENTITY.json'),real_header_inputs=[bind(ROOT/x)for x in ['lib/include/ihk/debug.h','kernel/include/process.h','kernel/rust/abi.rs','kernel/rust/debug.rs','kernel/rust/syscall_policy.rs']],retained_C_storage_owners=0,retained_C_storage_bytes=0,private_proposed_Rust_storage_owners=1,private_proposed_Rust_storage_bytes=32,data_retirement_claim=False)
dump('PREIMAGES.json',pre)
dump('EXACT-REUSED-PROVIDERS.json',{'scope':SCOPE,'banked_state':{'original':bind(BODY6/'f06_vdso_state.rs'),'private_copy':bind(HERE/'f06_vdso_state.rs'),'byte_identical':True},'banked_storage':{'original':bind(BODY7/'f06_vdso_storage.rs'),'private_copy':bind(HERE/'f06_vdso_storage.rs'),'byte_identical':True},'banked_nominal_ArchVdso':{'original':bind(BODY7/'syscall_policy.type.snapshot.rs'),'private_copy':bind(HERE/'syscall_policy.type.snapshot.rs'),'byte_identical':True},'production_state_provider':'Existing canonical C bridge or banked BODY6 Rust equivalent both always publish the same stable offset address; candidate adds no new owner/provider. HOST uses actual banked Rust bodies.','original_callback_declaration':bind(HERE/'original-Rust-log-declaration.rs.inc'),'original_map_caller':bind(HERE/'original-Rust-map-caller.rs.inc'),'actual_original_C_body':bind(HERE/'original-vdso-map-log.c.inc'),'no_duplicate_banked_port':True})
dump('PARENT-FOLLOWUP-AUTHORITY.RECORDED.json',{'scope':SCOPE,'author':'/root/f06_next','record_kind':'Worker record of actual parent followup, never Root-authored grant','authority':'Next private BODY12: implement remaining arch_vdso_map_log_bridge original dynamic descriptor/offset/pid contract only if defined original behavior can be preserved with genuine caller/types/oracle. Existing CPU6/7 jobs1/AS2GiB/CPU60/wall90+actualguard ordinary HOST only.','inherited_fixed_command_limit':4,'one_obvious_fixture_infrastructure_correction_within4_only':True,'stop_semantic_or_second_failure':True,'default_native_data_file_credit':0,'current_boundary_correction':'BFD retirement/current-free/Root63 completed21:50, historical freee13/ledger6b/bindingsbe0 never replay. Current pending boundary is failed-unlaunched A2 custody supplement/A3 narrow source fix; model/native clearances separate.'})
print(json.dumps({'status':'BODY12_PRIVATE_SOURCE_PREPARED','target':targets[0],'record':expected,'new_commands':len(commands),'new_compiler_runs':0}))
