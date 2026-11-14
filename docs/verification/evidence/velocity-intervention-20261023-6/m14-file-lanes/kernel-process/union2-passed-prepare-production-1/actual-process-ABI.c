/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <process.h>
#include <process_helpers.h>
#include <page.h>
#include <ihk/debug.h>
extern int process_page_fault_prepare_body_result(struct process_vm *,struct vm_range *,uintptr_t,uint64_t,pte_t **,void **,size_t *,int *,int *);
extern long process_page_offset_bridge(void *);
extern off_t page_get_offset(const struct page *);
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_page_fault_prepare_body_result),int (*)(struct process_vm *,struct vm_range *,uintptr_t,uint64_t,pte_t **,void **,size_t *,int *,int *)),"exact prepare borrowed output ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_page_offset_bridge),long (*)(void *)),"unchanged offset callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct page *)0)->offset),off_t)&&__builtin_types_compatible_p(long,off_t),"actual signed field/return ABI");
_Static_assert(sizeof(struct page)==80&&__alignof__(struct page)==8&&__builtin_offsetof(struct page,offset)==64,"existing F01 Page layout, no new field layout");
_Static_assert(sizeof(struct ddebug)==32&&sizeof(size_t)==8&&sizeof(uintptr_t)==8&&sizeof(uint64_t)==8&&sizeof(int)==4,"actual supported metadata/output widths");
_Static_assert(PF_PROT==1&&PF_PATCH==(1UL<<29),"same fault reason masks");
