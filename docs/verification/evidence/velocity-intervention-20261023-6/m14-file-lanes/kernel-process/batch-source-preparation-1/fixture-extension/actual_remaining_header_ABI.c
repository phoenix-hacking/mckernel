/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. SOURCE ONLY. */
#include <process.h>
#include <process_helpers.h>
#include <memobj.h>
#include <rusage_private.h>
#include <ihk/debug.h>
struct rfp_args {
	off_t off;
	uintptr_t start;
	struct memobj *memobj;
};

extern int remap_one_page(void *,page_table_t,pte_t *,void *,int);
extern void process_sync_range_log_bridge(struct process_vm *,struct vm_range *,unsigned long,unsigned long,int);
typedef int (*original_visit_t)(void *,page_table_t,pte_t *,void *,int);
_Static_assert(__builtin_types_compatible_p(__typeof__(&remap_one_page),original_visit_t),"unchanged remap callback ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&process_sync_range_log_bridge),void (*)(struct process_vm *,struct vm_range *,unsigned long,unsigned long,int)),"unchanged range logger ABI");
_Static_assert(sizeof(struct rfp_args)==24&&__alignof__(struct rfp_args)==8&&__builtin_offsetof(struct rfp_args,off)==0&&__builtin_offsetof(struct rfp_args,start)==8&&__builtin_offsetof(struct rfp_args,memobj)==16,"actual ProcessRemapArgs ABI");
_Static_assert(sizeof(struct page)==80&&__alignof__(struct page)==8,"actual existing Page ABI; no remap field access");
_Static_assert(sizeof(struct ddebug)==32&&sizeof(pte_t)==8&&sizeof(unsigned long)==8&&sizeof(int)==4,"supported diagnostic/PTE/vararg widths");
_Static_assert(__builtin_types_compatible_p(__typeof__(&phys_to_page),struct page *(*)(uintptr_t)),"named existing C provider ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&_ihk_mc_free_pages),void (*)(void *,int,int,char *,int)),"tracked free ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&rusage_memory_stat_sub),void (*)(struct memobj *,unsigned long,int)),"RSS CInt narrowing ABI");
_Static_assert(IHK_MC_PG_USER==1,"same original user page accounting mode");
