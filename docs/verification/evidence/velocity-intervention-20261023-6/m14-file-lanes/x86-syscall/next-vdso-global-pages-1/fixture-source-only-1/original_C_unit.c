/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "actual_real_abi.h"
extern struct vdso vdso;
extern void *pvti;
extern int pvti_npages;
extern int arch_setup_pvclock(void);
extern unsigned long virt_to_phys(void *);
extern int ihk_mc_pt_set_page(void *,void *,unsigned long,enum ihk_mc_pt_attribute);
#define vdso_map_global_pages original_C_vdso_map_global_pages
#include "actual_original_vdso_map_global_pages.inc"
