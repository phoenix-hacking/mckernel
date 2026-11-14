from pathlib import Path
import re
s=Path('postimage/kernel/CMakeLists.txt').read_text()
mark='if (MCKERNEL_M14_NONHELD13_DATA32_EXPERIMENTAL)'
idx=s.index(mark,s.index('set_source_files_properties("${CMAKE_CURRENT_SOURCE_DIR}/syscall.c"'))
end=s.index('endif()',idx);b=s[idx:end]
assert s.count('MCKERNEL_M14_F06_ORIGIN_GUARD')==1
for x in ['MCKERNEL_M14_F06_ORIGIN_GUARD','MCKERNEL_RUST_F06_XRSTOR_LEAF','MCKERNEL_RUST_F06_DO_SIGNAL_WHOLE','MCKERNEL_RUST_F06_DEBUG_CONSTANTS']:
 assert x in b
c=Path('postimage/arch/x86_64/kernel/syscall.c').read_text()
debug=c.index('#ifdef DEBUG_PRINT_SC'); guard=c.index('/* Compile-time binding for the explicitly selected M14 origin successor. */'); selected=c.index('#if defined(MCKERNEL_RUST_SYSCALL_POLICY_HELPERS) && defined(MCKERNEL_RUST_F06_OBTAIN_CLONE_CPUID)',guard)
assert debug<guard<selected
assert '#include' not in c[guard:selected] and '#undef DDEBUG_DEFAULT' not in c[guard:selected]
print('PASS: single combined-only CMake guard selection, after actual DEBUG_PRINT_SC block and immediately before clone selection')
