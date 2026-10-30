"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Prepare only private default-off source wiring on the retained large composition.
"""
from pathlib import Path
import difflib,hashlib,json
D=Path(__file__).resolve().parent;A=D.parent;S=A/'M14-CONVERSION-FIRST-LARGE-COMPOSITION-2';p=S/'postimage/kernel/CMakeLists.txt';src=p.read_text();rust_mark='\t\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n';c_mark='\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n';assert src.count(rust_mark)==1 and src.count(c_mark)==2
rust='''\t\t\t\t# Queue B is opt-in and remains subject to the documented source contracts.
\t\t\t\tif (MCKERNEL_F03_DO_SYSCALL_SUPPORTED_EXPERIMENTAL)
\t\t\t\t\tif (NOT MCKERNEL_F03_DEFINED_ALL_REQUEST_CALLERS_REVIEWED)
\t\t\t\t\t\tmessage(FATAL_ERROR "F03 do_syscall requires reviewed initialization of all selected callers")
\t\t\t\t\tendif()
\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_do_syscall_supported_candidate")
\t\t\t\tendif()
\t\t\t\tif (MCKERNEL_F03_UTIL_THREAD_WHOLE_EXPERIMENTAL)
\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_util_thread_whole_candidate" "--cfg" "f03_util_thread_arg5_zero_candidate")
\t\t\t\tendif()
'''
c='''\t\t\tif (MCKERNEL_F03_DO_SYSCALL_SUPPORTED_EXPERIMENTAL)
\t\t\t\tset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS MCKERNEL_RUST_F03_DO_SYSCALL_SUPPORTED)
\t\t\tendif()
\t\t\tif (MCKERNEL_F03_UTIL_THREAD_WHOLE_EXPERIMENTAL)
\t\t\t\tset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS "MCKERNEL_RUST_F03_UTIL_THREAD_WHOLE;MCKERNEL_RUST_F03_UTIL_REQUEST_ARG5_ZERO")
\t\t\tendif()
'''
new=src.replace(rust_mark,rust_mark+rust,1);needle=c_mark+'\t\t\tif (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL)';assert new.count(needle)==1;new=new.replace(needle,c_mark+c+'\t\t\tif (MCKERNEL_F03_REQUEST_CONSTRUCTORS_EXPERIMENTAL)',1)
out=D/'postimage/kernel/CMakeLists.txt';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(new)
patch=''.join(difflib.unified_diff(src.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/kernel/CMakeLists.txt',tofile='b/kernel/CMakeLists.txt'));(D/'QUEUE-B-WIRING.ON-LARGE-COMPOSITION.patch').write_text(patch)
print('wiring generated; no compiler or source selection executed')
