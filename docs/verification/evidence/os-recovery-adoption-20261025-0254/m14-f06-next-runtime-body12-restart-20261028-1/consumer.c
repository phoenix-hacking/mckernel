/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <types.h>
#include <process.h>
#include <ihk/debug.h>
extern struct ddebug vdso_map_debug __asm__("mckernel_f06_vdso_map_debug");
extern ptrdiff_t selected_offset __asm__("mckernel_f06_vdso_offset");
extern void arch_vdso_map_log_bridge(int,int,struct process_vm *,unsigned long,unsigned long,unsigned long,unsigned long,int);
typedef void (*log_abi)(int,int,struct process_vm *,unsigned long,unsigned long,unsigned long,unsigned long,int);
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_vdso_map_log_bridge),log_abi),"actual original callback ABI");
_Static_assert(sizeof(int)==4 && sizeof(unsigned long)==8 && sizeof(ptrdiff_t)==8 && (ptrdiff_t)-1<0,"int32/unsigned LP64/signed ptrdiff_t");
_Static_assert(sizeof(struct process_vm)==304 && __alignof__(struct process_vm)==8 && __builtin_offsetof(struct process_vm,proc)==136,"actual ProcessVm and proc field");
_Static_assert(sizeof(struct process)==1728 && __alignof__(struct process)==64 && __builtin_offsetof(struct process,pid)==456,"actual Process and pid field");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct process *)0)->pid),int),"original pid is int32");
_Static_assert(sizeof(struct ddebug)==32 && __alignof__(struct ddebug)==8,"actual Ddebug storage shape");
struct ddebug *fixture_selected_descriptor(void){return &vdso_map_debug;}
void fixture_set_flags(struct ddebug *descriptor,unsigned int flags){descriptor->flags=flags;}
unsigned int fixture_read_flags(struct ddebug *descriptor){return descriptor->flags;}
void fixture_set_selected_offset(ptrdiff_t offset){selected_offset=offset;}
ptrdiff_t fixture_read_selected_offset(void){return selected_offset;}
void fixture_consumer_call(int event,int error,struct process_vm *vm,unsigned long a,unsigned long b,unsigned long c,unsigned long d,int pages){arch_vdso_map_log_bridge(event,error,vm,a,b,c,d,pages);}
