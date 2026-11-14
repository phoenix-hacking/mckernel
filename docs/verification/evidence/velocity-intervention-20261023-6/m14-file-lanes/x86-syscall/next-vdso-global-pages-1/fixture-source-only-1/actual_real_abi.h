/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <arch-memory.h>
#include <ihk/debug.h>
#include "actual_vdso_layout.inc"
_Static_assert(sizeof(long)==8 && sizeof(void*)==8 && sizeof(int)==4, "LP64");
_Static_assert(sizeof(struct vdso)==88, "actual vdso");
_Static_assert(__builtin_offsetof(struct vdso,vvar_virt)==32, "vvar slot");
_Static_assert(__builtin_offsetof(struct vdso,hpet_virt)==48, "hpet slot");
_Static_assert(__builtin_offsetof(struct vdso,pvti_virt)==64, "pvti slot");
_Static_assert(sizeof(enum ihk_mc_pt_attribute)==8, "real PTattribute ABI");
_Static_assert(PTATTR_ACTIVE==1 && PTATTR_USER==4 && PTATTR_NO_EXECUTE==0x8000000000000000UL && PTATTR_UNCACHABLE==0x10000, "real attrs");
_Static_assert(sizeof(struct ddebug)==32 && __alignof__(struct ddebug)==8, "real debug ABI");
