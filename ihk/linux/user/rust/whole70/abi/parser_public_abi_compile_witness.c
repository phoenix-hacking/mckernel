/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Nonshipped real-header ABI witness; not another executable queue. */
#include <stddef.h>
#include <ihk/ihklib_private.h>
_Static_assert(sizeof(struct ihk_cpu_req)==16,"CPU16");
_Static_assert(offsetof(struct ihk_cpu_req,num_cpus)==8,"CPUcount8");
_Static_assert(sizeof(struct ihk_mem_req)==32,"MEM32");
_Static_assert(offsetof(struct ihk_mem_req,num_chunks)==16,"MEMcount16");
_Static_assert(offsetof(struct ihk_mem_req,timeout)==28,"MEMtimeout28");
_Static_assert(sizeof(struct ihk_ikc_req)==24,"IKC24");
_Static_assert(offsetof(struct ihk_ikc_req,num_cpus)==16,"IKCcount16");
#define SAME(f,t) _Static_assert(__builtin_types_compatible_p(__typeof__(&f),t),#f)
SAME(cpu_str2count,int(*)(char*));
SAME(cpu_str2req,int(*)(char*,int,struct ihk_cpu_req*));
SAME(cpu_req2str,char*(*)(struct ihk_cpu_req*));
SAME(mem_str2count,int(*)(char*));
SAME(mem_str2req,int(*)(char*,struct ihk_mem_req*));
SAME(mem_req2str,char*(*)(struct ihk_mem_req*));
SAME(ikc_str2count,int(*)(char*));
SAME(ikc_str2req,int(*)(char*,int,struct ihk_ikc_req*));
SAME(ikc_req2str,char*(*)(struct ihk_ikc_req*));
