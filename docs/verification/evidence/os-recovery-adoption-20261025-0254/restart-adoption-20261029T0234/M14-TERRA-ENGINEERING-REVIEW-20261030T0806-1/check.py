#!/usr/bin/env python3
# Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
from pathlib import Path
import hashlib, json, subprocess
s=Path('postimage/CMakeLists.txt').read_text()
def block(start, index=0):
 lines=s.splitlines(keepends=True); idx=[i for i,l in enumerate(lines) if l.strip()==start][index]; depth=0
 for j in range(idx,len(lines)):
  x=lines[j].strip().lower()
  if x.startswith('if ('): depth+=1
  elif x.startswith('endif('):
   depth-=1
   if depth==0: return ''.join(lines[idx:j+1])
 raise Exception(start)
req=block('if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL AND')
flags=block('if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)',0)
request_r=block('if (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL OR MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)',0)
signal_r=block('if (MCKERNEL_F03_SIGNAL_FORWARD_EXPERIMENTAL OR MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)',0)
request_c=block('if (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL OR MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)',1)
signal_c=block('if (MCKERNEL_F03_SIGNAL_FORWARD_EXPERIMENTAL OR MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)',1)
paired=block('if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)',1)
late=block('if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)',2)
root=Path('matrix'); root.mkdir(exist_ok=True)
cmake='''cmake_minimum_required(VERSION 3.16)
project(m14_fixture NONE)
set(MCKERNEL_HOST_IRQ_ABI "${TEST_HOST}")
set(ARCH "${TEST_ARCH}")
set(BUILD_TARGET "${TEST_TARGET}")
set(ENABLE_RUST_KERNEL "${TEST_RUST}")
set(ENABLE_PERF "${TEST_PERF}")
set(ENABLE_UBSAN "${TEST_UBSAN}")
'''+req+'''
set_property(SOURCE "${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS F06_SENTINEL)
set_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS GENERIC_SENTINEL)
'''+flags+request_r+signal_r+request_c+signal_c+paired+late+'''
get_source_file_property(ARCH_FLAGS "${PROJECT_SOURCE_DIR}/arch/${ARCH}/kernel/syscall.c" COMPILE_DEFINITIONS)
get_source_file_property(GENERIC_FLAGS "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" COMPILE_DEFINITIONS)
file(WRITE "${CMAKE_BINARY_DIR}/observed" "${RUST_KERNEL_CFG}|${RUST_KERNEL_SRCS}|${ARCH_FLAGS}|${GENERIC_FLAGS}")
'''
(root/'CMakeLists.txt').write_text(cmake)
arch=['MCKERNEL_RUST_F06_XRSTOR_LEAF','MCKERNEL_RUST_F06_BAD_FRAME_LEAF','MCKERNEL_RUST_F06_SIGNAL_CONTEXT','MCKERNEL_RUST_F06_REGSET_DEFINED_DIAGNOSTIC','MCKERNEL_RUST_F06_DO_SIGNAL_WHOLE','MCKERNEL_RUST_F06_DEBUG_CONSTANTS']
generic=['MCKERNEL_RUST_F03_PERF_ENTRY_EXPERIMENTAL','MCKERNEL_RUST_F03_SIGNAL_FORWARD_EXPERIMENTAL','MCKERNEL_RUST_F03_REQUEST_CONSTRUCTORS']
cfg=['f03_perf_entry_candidate','f03_signal_forward_defined_candidate','f03_request_constructors_candidate','f06_signal_leaf_adapters_candidate','f06_signal_context_candidate','f06_regset_defined_diagnostic_candidate','f06_do_signal_whole_candidate','f06_do_signal_reuse_qualified_context','f06_debug_constants_candidate']
base={'TEST_RUST':'ON','TEST_ARCH':'x86_64','TEST_TARGET':'smp-x86','TEST_HOST':'linux-6.12','TEST_PERF':'ON','TEST_UBSAN':'OFF'}
def invoke(name, opts, expect):
 values=base|opts
 cmd=['cmake','-S',str(root),'-B',str(root/name)]+[f'-D{k}={v}' for k,v in values.items()]
 r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
 (root/(name+'.log')).write_text(r.stdout)
 assert (r.returncode==0)==expect,(name,r.returncode,r.stdout)
 return (root/name/'observed').read_text().split('|') if expect else None
cfg0,src0,arch0,gen0=invoke('off',{},True)
assert all(x not in cfg0 for x in cfg) and all(x not in arch0 for x in arch) and all(x not in gen0 for x in generic)
assert 'F06_SENTINEL' not in arch0 and 'MCKERNEL_RUST_SYSCALL_POLICY_HELPERS' in arch0
cfg1,src1,arch1,gen1=invoke('on',{'MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL':'ON'},True)
assert all(x in cfg1 for x in cfg) and all(x in arch1 for x in arch) and all(x in gen1 for x in generic)
assert 'F06_SENTINEL' in arch1 and 'MCKERNEL_RUST_SYSCALL_POLICY_HELPERS' in arch1 and 'f06_debug_constants.rs' in src1
for forbidden in ['PTRACE_WAKEUP_LOG','DIRECT_TID','TERMINATE_HOST','EXECVE']:
 assert forbidden not in arch1+gen1
cfg2,_,arch2,gen2=invoke('oldoptions',{'MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL':'ON','MCKERNEL_F03_SIGNAL_FORWARD_EXPERIMENTAL':'ON'},True)
assert all(x in cfg2 for x in cfg[1:3]) and all(x in gen2 for x in generic[1:3])
assert all(x not in arch2 for x in arch) and generic[0] not in gen2
for name,k,v in [('norust','TEST_RUST','OFF'),('wrongarch','TEST_ARCH','arm64'),('wrongtarget','TEST_TARGET','other'),('wronghost','TEST_HOST','legacy'),('noperf','TEST_PERF','OFF'),('ubsan','TEST_UBSAN','ON')]:
 invoke(name,{'MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL':'ON',k:v},False)
print('PASS: off, combined on, previous standalone options, 6 unsupported profile rejections')
print('Scope: extracted actual CMake fragments and simulated preexisting source property; not full project configure/build/link')
