#!/usr/bin/env python3
"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare private exact source and at most four future mocked HOST commands.
"""
import difflib
import hashlib
import json
from pathlib import Path

ROOT=Path('/home/holden/mckernel')
HERE=Path(__file__).resolve().parent
E=ROOT/'docs/verification/evidence/os-recovery-adoption-20261025-0254'
SCOPE='Functional McKernel OS/apps and Rust/assembly migration only; no security testing.'
def bind(p):
    b=p.read_bytes();return {'path':str(p),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}
def verify(row,p=None):
    got=bind(p or Path(row['path']));assert (got['bytes'],got['sha256'])==(row['bytes'],row['sha256']),got['path'];return got
def dump(name,value): (HERE/name).write_text(json.dumps(value,indent=2)+'\n')

adoption_path=E/'restart-adoption-20261028T1911/M14-CANONICAL118-SOURCE-ADOPTION-1/ROOT-SOURCE-ADOPTION.json'
assert bind(adoption_path)['sha256']=='c161d7b6732d6d48ad73083c4bc95ff0c665528bb241d16ac71cc54d75533e7e'
adoption=json.loads(adoption_path.read_text())
postimages={row['relative']:verify(row['expected_postimage'],ROOT/row['relative']) for row in adoption['rows']}
assert len(postimages)==9
snapshots={}
for rel,name in [('arch/x86_64/kernel/syscall.c','BASE.syscall.c'),('kernel/CMakeLists.txt','BASE.CMakeLists.txt'),('kernel/rust/lib.rs','BASE.lib.rs'),('kernel/rust/abi.rs','abi.snapshot.rs')]:
    if (HERE/name).exists():
        assert (HERE/name).read_bytes()==(ROOT/rel).read_bytes(), 'existing snapshot drift'
    else:
        (HERE/name).write_bytes((ROOT/rel).read_bytes())
    snapshots[rel]={'canonical':bind(ROOT/rel),'snapshot':bind(HERE/name)}
    if rel in postimages:verify(postimages[rel],HERE/name)
c=(HERE/'BASE.syscall.c').read_text()
marker='void\narch_vdso_setup_log_bridge(int event, int error)\n'
assert c.count(marker)==1
start=c.index(marker);end=c.index('\n}\n',start)+3;original=c[start:end]
assert original.count('case ARCH_VDSO_SETUP_LOG_')==4
(HERE/'original-vdso-setup-log.c.inc').write_text(original)
defines=''.join(line+'\n' for line in c.splitlines() if line.startswith('#define ARCH_VDSO_SETUP_LOG_'))
assert len(defines.splitlines())==4
(HERE/'original-event-defines.c.inc').write_text(defines)
selected='''#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F06_VDSO_SETUP_LOG)
extern void arch_vdso_setup_log_bridge(int event, int error);
#else
'''+original+'#endif\n'
c_after=c[:start]+selected+c[end:]
lib=(HERE/'BASE.lib.rs').read_text();lib_after=lib+'\n#[cfg(f06_vdso_setup_log_candidate)]\nmod f06_vdso_setup_log;\n'
cmake=(HERE/'BASE.CMakeLists.txt').read_text()
anchor='''\t\t\t\tset_property(SOURCE "${MCKERNEL_F06_C_SOURCE}" APPEND PROPERTY
\t\t\t\t    COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_VDSO_INFO")
'''
assert cmake.count(anchor)==1
addition='''
\t\t\t\t# Complete existing four-event VDSO setup logger with unchanged kprintf.
\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f06_vdso_setup_log_candidate")
\t\t\t\tlist(APPEND RUST_KERNEL_SRCS "${CMAKE_CURRENT_SOURCE_DIR}/rust/f06_vdso_setup_log.rs")
\t\t\t\tset_property(SOURCE "${MCKERNEL_F06_C_SOURCE}" APPEND PROPERTY
\t\t\t\t    COMPILE_DEFINITIONS "MCKERNEL_RUST_F06_VDSO_SETUP_LOG")
'''
cmake_after=cmake.replace(anchor,anchor+addition)
for name,rel,before,after in [('arch-selection.patch','arch/x86_64/kernel/syscall.c',c,c_after),('rust-module-selection.patch','kernel/rust/lib.rs',lib,lib_after),('cmake-selection.PROPOSAL.patch','kernel/CMakeLists.txt',cmake,cmake_after)]:
    (HERE/name).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)))
    snapshots[rel]['proposed_postimage_sha256']=hashlib.sha256(after.encode()).hexdigest()
frontier_path=E/'m14-f06-next-runtime-body4-restart-20261028-1/SELECTED-CURRENT116-ARCH-FRONTIER.json'
frontier=json.loads(frontier_path.read_text());verify(frontier['object'])
target=[row for row in frontier['selected_functions'] if row['name']=='arch_vdso_setup_log_bridge'];assert len(target)==1 and target[0]['size']==153
frontier['target']=target[0]
frontier['already_banked_excluded']=['vdso_get_vdso_info','arch_native_signal_restore_fp_bridge','arch_ptrace_xstate_copy_to_bridge','arch_ptrace_xstate_copy_from_bridge']
dump('SELECTED-CURRENT116-ARCH-FRONTIER.json',frontier)
prior=E/'m14-f06-next-runtime-body4-restart-20261028-1/rebased118-source-1'
prior_plan=json.loads((prior/'FUTURE-HOST-COMMANDS.NOT-GRANTED.json').read_text())
flags=prior_plan['commands'][0]['argv'][:-4];assert prior_plan['commands'][0]['argv'][-4]=='-c'
out=HERE/'future-host-output-1'
commands=[
 {'purpose':SCOPE+' Compile genuine debug-header variadic printer/public logger ABI witness only.','argv':flags+['-c',str(HERE/'abi_probe.c'),'-o',str(out/'abi_probe.o')]},
 {'purpose':SCOPE+' Compile verbatim original C event logger with actual ekprintf macro and mock output.','argv':flags+['-std=gnu11','-fno-builtin','-I',str(HERE),'-c',str(HERE/'oracle.c'),'-o',str(out/'oracle.o')]},
 {'purpose':SCOPE+' Compile unchanged entire Rust module/actualABI fixture linked to HOST mock logger only.','argv':['/home/holden/mckernel-work/toolchains/rustup/toolchains/1.92.0-x86_64-unknown-linux-gnu/bin/rustc','--edition=2021','--test','-C','opt-level=2','-C','link-arg='+str(out/'oracle.o'),'-C','link-arg=-no-pie',str(HERE/'fixture.rs'),'-o',str(out/'fixture')]},
 {'purpose':SCOPE+' Run585 deterministic C/Rust exact-message/variadic-int32/output-canary pairs and one mixed event sequence.','argv':[str(out/'fixture'),'--exact','exact_original_c_and_rust_vdso_setup_log','--test-threads=1','--nocapture']},
]
dump('FUTURE-HOST-COMMANDS.json',{'scope':SCOPE,'status':'EXACT_FIXED_NEW_COMMANDS_UNDER_ACTUAL_PARENT_STANDING_AUTHORIZATION_NOT_YET_RUN','cwd':str(HERE),'fresh_output':str(out),'commands':commands,'header_profile_argv_source':bind(prior/'FUTURE-HOST-COMMANDS.NOT-GRANTED.json'),'expected_pairs':585,'expected_mixed_sequence_calls':5,'compiler_or_fixture_invocations':0,'requires':'Bind and validate exact source/header/tool/plan before first command; current guardian/account/caps before each command. Actual parent followup permits at most4new commands and one obvious bounded fixture/compiler infrastructure correction, never semantic-oracle weakening or unchanged retry.','future_default_checks':['Root compose disjoint source/lib/CMake hunks only with actual adopted118 or reviewed successor; preserve all118selectors and body3/body4 separately.','Rebind genuine origin/profile, fullcrate, selected/fallback full arch TU and actual default link; require selected C target absent and exactly one Rust provider resolving unchanged setup_vdso callbacks.','Retain exact event constants/messages and genuine int32 variadic kprintf ABI/provider; no dynamic-debug descriptors arise in this body.','Matching-current setup/error logging observations remain separate from HOST qualification/native/file acceptance.']})
prior_pre=json.loads((prior/'PREIMAGES.json').read_text())
dump('PREIMAGES.json',{'scope':SCOPE,'status':'EXACT118PRIVATE_SOURCE_PREPARATION_NOT_DEFAULT_ACCEPTANCE','source_adoption118':bind(adoption_path),'accepted_artifact_source_adoption116':prior_pre['accepted_artifact_source_adoption116'],'snapshots':snapshots,'original_body':bind(HERE/'original-vdso-setup-log.c.inc'),'original_event_defines':bind(HERE/'original-event-defines.c.inc'),'all_nine_root118_canonical_postimages':postimages,'real_header_inputs':[bind(ROOT/p) for p in ['lib/include/ihk/debug.h','kernel/include/lwk/compiler.h','kernel/rust/abi.rs','kernel/rust/syscall_policy.rs']],'retained_object_frontier':bind(HERE/'SELECTED-CURRENT116-ARCH-FRONTIER.json'),'no_shared_writes':True,'compiler_runs':0,'fixture_runs':0,'native_runs':0})
print(json.dumps({'scope':SCOPE,'status':'BODY5_SOURCE_AND_EXACT4COMMAND_PLAN_PREPARED','target':target[0],'compiler_runs':0}))
