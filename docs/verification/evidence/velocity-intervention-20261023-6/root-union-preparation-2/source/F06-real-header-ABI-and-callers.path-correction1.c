/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual complete selected TU, real headers and allocated public C callers.
 * Do not link this witness together with the plain whole-TU object.
 */
#include "arch/x86_64/kernel/syscall.c"
_Static_assert(sizeof(long)==8 && sizeof(int)==4 && sizeof(void *)==8,"x86LP64");
_Static_assert(sizeof(struct vdso)==88,"real ArchVdso size");
_Static_assert(__builtin_offsetof(struct vdso,vdso_npages)==8,"ArchVdso npages");
_Static_assert(__builtin_offsetof(struct vdso,vvar_virt)==32,"ArchVdso vvar");
_Static_assert(__builtin_offsetof(struct vdso,hpet_virt)==48,"ArchVdso hpet");
_Static_assert(__builtin_offsetof(struct vdso,pvti_virt)==64,"ArchVdso pvti");
_Static_assert(sizeof(struct ddebug)==32,"real Ddebug");
_Static_assert(sizeof(struct mcs_rwlock_node_irqsave)==64,"actual stack lock node");
_Static_assert(__alignof__(struct mcs_rwlock_node_irqsave)==64,"actual stack node alignment");
_Static_assert(sizeof(struct ptrace_report_signal_offsets)==14*sizeof(unsigned long),"real14offset ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&vdso_map_global_pages),int (*)(void)),"VDSO public ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ptrace_report_signal),void (*)(struct thread *,int)),"ptrace signal public ABI");
__attribute__((noinline,used)) int f06_actual_vdso_C_caller(void) {return vdso_map_global_pages();}
__attribute__((noinline,used)) void f06_actual_signal_C_caller(struct thread *t,int sig) {ptrace_report_signal(t,sig);}
