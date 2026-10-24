/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source-only real ABI witness; no runnable driver/second executable queue.
 */
#include <process.h>
#include <cls.h>
#include <affinity.h>
extern int obtain_clone_cpuid(cpu_set_t *,int);
typedef int (*actual_clone_cpu_entry)(cpu_set_t *,int);
_Static_assert(__builtin_types_compatible_p(__typeof__(&obtain_clone_cpuid),actual_clone_cpu_entry),"actual public signature");
_Static_assert(sizeof(((struct cpu_local_var *)0)->runq_len)==8,"unsigned size_t runq length");
_Static_assert(sizeof(((struct cpu_local_var *)0)->runq_reserved)==8,"atomic64 reservation slot");
_Static_assert(__builtin_offsetof(struct cpu_local_var,runq_reserved)%8==0,"atomic alignment");
_Static_assert(CPU_STATUS_RESERVED==3,"same reservation state");
unsigned long f06_clone_cpu_C_ABI_fact(unsigned int i)
{
 const unsigned long x[]={sizeof(cpu_set_t),sizeof(struct cpu_local_var),__alignof__(struct cpu_local_var),sizeof(ihk_spinlock_t),__builtin_offsetof(struct cpu_local_var,runq_lock),__builtin_offsetof(struct cpu_local_var,runq_len),__builtin_offsetof(struct cpu_local_var,runq_reserved),__builtin_offsetof(struct cpu_local_var,status)};
 return i<sizeof x/sizeof x[0]?x[i]:~0UL;
}
