/* Functional OS/apps and Rust migration only; no security testing.
 * Nonshipped combined real-header ABI checks, no runtime providers. */
#include <linux/version.h>
#include <linux/sched.h>
#include "rusage_actual_header_witness.c"
#include "selected_target_stat_dirent_ABI.c"
#include "runtime_state_actual_header_witness.c"
#include "parser_public_abi_compile_witness.c"
#include "mem_map_public_abi_witness.c"
#include "public_export_signatures_witness.c"
#include "private_export_signatures_witness.c"
_Static_assert(LINUX_VERSION_CODE >= KERNEL_VERSION(4,6,0), "selected namespace table8");
_Static_assert(sizeof(struct namespace_file)==24, "namespace24");
_Static_assert(offsetof(struct namespace_file,name)==8, "namespace name8");
_Static_assert(offsetof(struct namespace_file,fd)==16, "namespace fd16");
_Static_assert(CLONE_NEWUSER==0x10000000 && CLONE_NEWCGROUP==0x02000000 &&
 CLONE_NEWIPC==0x08000000 && CLONE_NEWUTS==0x04000000 && CLONE_NEWNET==0x40000000 &&
 CLONE_NEWPID==0x20000000 && CLONE_NEWNS==0x20000, "selected namespace flags");
_Static_assert(sizeof(struct ihk_mem_chunk)==16 &&
 offsetof(struct ihk_mem_chunk,numa_node_number)==8, "public memory chunk16/8");
_Static_assert(sizeof(struct ihk_ikc_cpu_map)==8 &&
 offsetof(struct ihk_ikc_cpu_map,dst_cpu)==4, "public IKC pair8/4");
_Static_assert(IHK_OS_FREEZE==0x112a30 && IHK_OS_THAW==0x112a31, "freeze/thaw");
_Static_assert(IHK_OS_SHUTDOWN==0x112a02 && IHK_OS_SET_KARGS==0x112a04, "shutdown/kargs");
_Static_assert(IHK_OS_SET_IKC_MAP==0x112a28 && IHK_OS_GET_IKC_MAP==0x112a29, "IKCmap");
_Static_assert(IHKLIB_MAX_NUM_ENV==1024 && IHKLIB_MAX_SIZE_ENV==(1UL<<20) &&
 IHKLIB_MAX_SIZE_KARGS==(1UL<<20), "existing public environment bounds");

/* The public POSIX stat branch is selected only after this actual header/link witness passes. */
int main(void) { puts("ihklib_stat_abi_stat"); return 0; }
