/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Compile only real selected whole-TU ABI; never execute. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/next-stack-output-callbacks-source-only-1/candidate/arch/x86_64/kernel/cpu.c"
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/x86-cpu/next-exception-stop-batch-source-1/bounded-error-alias-correction-1/source/kernel/include/kmsg.h"

typedef void(*LogFn)(unsigned long,unsigned long,unsigned long);
typedef void(*PrintFn)(void*,unsigned long);
typedef int(*KprintfFn)(const char*,...);
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_stack_frame_log_bridge),LogFn),"actual log ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_print_stack_bridge),PrintFn),"actual forward ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&kprintf),KprintfFn),"real existing logger ABI");
_Static_assert(sizeof(unsigned long)==8&&sizeof(void*)==8&&sizeof(int)==4,"real existing widths");
const unsigned long M14_C_STACK_OUTPUT_ABI[8]={sizeof(unsigned long),__alignof__(unsigned long),sizeof(void*),__alignof__(void*),sizeof(LogFn),__alignof__(LogFn),sizeof(PrintFn),__alignof__(PrintFn)};
