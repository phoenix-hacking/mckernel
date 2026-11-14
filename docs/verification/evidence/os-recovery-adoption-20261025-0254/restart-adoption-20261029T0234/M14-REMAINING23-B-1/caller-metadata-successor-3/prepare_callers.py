"""Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
Private named-slot patches; no compiler, preprocessor or runtime.
"""
from pathlib import Path
import difflib
D=Path(__file__).resolve().parent;B=D.parent;A=B.parent;S=A/'M14-CONVERSION-FIRST-LARGE-COMPOSITION-2';snapshot=A/'M14-CONVERSION-FIRST-ACTUAL-SNAPSHOT-1/rust-subtree';items=[]
def patch(rel,old,new):
 out=D/'postimage'/rel;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(new)
 items.extend(difflib.unified_diff(old.splitlines(keepends=True),new.splitlines(keepends=True),fromfile='a/'+rel,tofile='b/'+rel))
old=(S/'postimage/kernel/syscall.c').read_text();marker='}\n#endif\n#line 7721\n';assert old.count(marker)==1
header='''}\n#endif
#ifdef MCKERNEL_RUST_F03_CLONE_REQUEST_DEFINED
extern void f03_clone_request_define_unused45(struct syscall_request *);
#define F03_CLONE_REQUEST_DEFINED(request) f03_clone_request_define_unused45(request)
#else
#define F03_CLONE_REQUEST_DEFINED(request) ((void)0)
#endif
#line 7721
'''
new=old.replace(marker,header,1);line='\t\tnewproc->pid = do_syscall(&request1, ihk_mc_get_processor_id());';assert new.count(line)==1;new=new.replace(line,'\t\tF03_CLONE_REQUEST_DEFINED(&request1); newproc->pid = do_syscall(&request1, ihk_mc_get_processor_id());',1);patch('kernel/syscall.c',old,new)
old=(S/'postimage/kernel/rust/syscall_policy.rs').read_text();fragment=(D/'f03_clone_request_defined.rs.inc').read_text();assert 'f03_clone_request_define_unused45' not in old;patch('kernel/rust/syscall_policy.rs',old,old+'\n'+fragment)
old=(snapshot/'mem_helpers.rs').read_text();line='                    args.add(3).write((*(*thread).proc).saved_cmdline_len as CULong);';assert old.count(line)==1;new=old.replace(line,line+' args.add(4).write(0); args.add(5).write(0);',1);patch('kernel/rust/mem_helpers.rs',old,new)
old=(B/'postimage/kernel/CMakeLists.txt').read_text();rust='''\t\t\t\tif (MCKERNEL_F03_CLONE_REQUEST_DEFINED_EXPERIMENTAL)
\t\t\t\t\tlist(APPEND RUST_KERNEL_CFG "--cfg" "f03_clone_request_defined_candidate")
\t\t\t\tendif()
''';c='''\t\t\tif (MCKERNEL_F03_CLONE_REQUEST_DEFINED_EXPERIMENTAL)
\t\t\t\tset_property(SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/syscall.c" APPEND PROPERTY COMPILE_DEFINITIONS MCKERNEL_RUST_F03_CLONE_REQUEST_DEFINED)
\t\t\tendif()
''';rmark='\t\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n';assert old.count(rmark)==1;new=old.replace(rmark,rmark+rust,1);cmark='\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n\t\t\tif (MCKERNEL_F03_DO_SYSCALL_SUPPORTED_EXPERIMENTAL)';assert new.count(cmark)==1;new=new.replace(cmark,'\t\tif (ARCH STREQUAL "x86_64" AND NOT ENABLE_UBSAN)\n'+c+'\t\t\tif (MCKERNEL_F03_DO_SYSCALL_SUPPORTED_EXPERIMENTAL)',1);patch('kernel/CMakeLists.txt',old,new)
(D/'CALLERS.ON-SOURCE2-PLUS-WIRING.patch').write_text(''.join(items));print('Prepared private caller slot corrections and opt-in wiring; no compile or runtime')
