/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE ONLY. */
#include <process.h>
#include <process_helpers.h>
#include <ihk/debug.h>
extern int process_page_fault_prepare_body_result(struct process_vm *,struct vm_range *,uintptr_t,uint64_t,pte_t **,void **,size_t *,int *,int *);
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_page_fault_prepare_body_result),int (*)(struct process_vm *,struct vm_range *,uintptr_t,uint64_t,pte_t **,void **,size_t *,int *,int *)),"exact borrowed preparation out-pointer ABI");
_Static_assert(sizeof(uintptr_t)==8&&sizeof(uint64_t)==8&&sizeof(size_t)==8&&sizeof(pte_t)==8&&sizeof(int)==4,"actual supported scalar/output widths");
_Static_assert(PF_PROT==1&&PF_PATCH==(1UL<<29),"original fault reason masks");
_Static_assert(sizeof(struct ddebug)==32,"original static bounds selector ABI");
