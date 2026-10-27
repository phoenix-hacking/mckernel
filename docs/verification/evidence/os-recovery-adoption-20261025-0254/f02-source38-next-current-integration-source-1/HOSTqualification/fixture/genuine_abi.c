/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "actual_allocator_abi.c"
#include <ihk/mm.h>
_Static_assert(__builtin_types_compatible_p(__typeof__(&_ihk_mc_alloc_aligned_pages_node),
    void *(*)(int,int,ihk_mc_ap_flag,int,int,uintptr_t,char *,int)),
    "actual aligned tracked allocator signed page-count and full-width address ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&_ihk_mc_free_pages),
    void (*)(void *,int,int,char *,int)), "actual tracked page free ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_get_smaller_page_size),
    int (*)(void *,size_t,size_t *,int *)), "existing architecture geometry provider ABI");
_Static_assert(PAGE_SIZE==4096 && PAGE_P2ALIGN==0 && KERNEL_STACK_NR_PAGES==32,
    "same actual page geometry and stack count");
_Static_assert(IHK_MC_PG_KERNEL==0 && IHK_MC_PG_USER==1 && VR_AP_USER==4,
    "same actual accounting categories and user-allocation flag");
#define LINE_ABI(name) _Static_assert(sizeof(name)==4 && __alignof__(name)==4 && \
    __builtin_types_compatible_p(__typeof__(&(name)), const int *), #name " readonly signed C-int4 ABI")
LINE_ABI(process_mckfd_free_bridge_source_line);
LINE_ABI(process_policy_free_bridge_source_line);
LINE_ABI(process_optional_free_bridge_source_line);
LINE_ABI(process_alloc_bridge_source_line);
LINE_ABI(process_free_vm_bridge_source_line);
LINE_ABI(process_create_thread_alloc_pages_source_line);
LINE_ABI(process_split_range_alloc_source_line);
LINE_ABI(process_range_kfree_bridge_source_line);
LINE_ABI(process_free_range_pages_source_line);
LINE_ABI(process_add_range_alloc_bridge_source_line);
LINE_ABI(process_add_range_free_bridge_source_line);
LINE_ABI(process_page_fault_anon_alloc_line);
LINE_ABI(process_free_thread_pages_source_line);
