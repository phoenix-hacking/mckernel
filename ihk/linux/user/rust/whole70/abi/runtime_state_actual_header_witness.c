/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Nonshipped ABI/default witness; selected current profile only. */
#include <stddef.h>
#include <ihk/ihklib_private.h>
_Static_assert(sizeof(struct ihklib_reserve_mem_conf)==24,"config24");
_Static_assert(_Alignof(struct ihklib_reserve_mem_conf)==4,"configalign4");
_Static_assert(offsetof(struct ihklib_reserve_mem_conf,min_chunk_size)==12,"minchunk12");
_Static_assert(offsetof(struct ihklib_reserve_mem_conf,max_size_ratio_all)==16,"maxratio16");
_Static_assert(offsetof(struct ihklib_reserve_mem_conf,timeout)==20,"timeout20");
_Static_assert(IHKLIB_LOGLEVEL_ERR==1,"logdefault1");
_Static_assert(IHK_RESERVE_MEM_MAX_SIZE_RATIO_ALL_LIMIT==98,"selectednonFugaku98");
_Static_assert(IHK_RESERVE_MEM_BALANCED_ENABLE==0&&IHK_RESERVE_MEM_TIMEOUT==5,"keys0through5");
_Static_assert(__builtin_types_compatible_p(__typeof__(&ihk_reserve_mem_conf),
    int(*)(int,int,void*)),"publicsetterABI");
_Static_assert(sizeof(enum IHKLIB_LOGLEVEL)==4,"logenum32");
