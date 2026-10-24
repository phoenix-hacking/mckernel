/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <process.h>
#include <cls.h>
#include <syscall.h>
extern int move_pages_smp_handler(int,int,void *);
_Static_assert(sizeof(long)==8 && sizeof(int)==4 && sizeof(void *)==8,"x86 LP64");
_Static_assert(sizeof(struct move_pages_smp_req)==104,"request ABI104");
_Static_assert(__alignof__(struct move_pages_smp_req)==8,"request alignment8");
_Static_assert(sizeof(ihk_atomic_t)==4 && __alignof__(ihk_atomic_t)==4,"atomic field4");
_Static_assert(__builtin_offsetof(ihk_atomic_t,counter)==0,"counter ABI0");
_Static_assert(__builtin_types_compatible_p(__typeof__(&move_pages_smp_handler),int (*)(int,int,void *)),"public handler signature");
_Static_assert(__builtin_offsetof(struct move_pages_smp_req,count)==0,"request count");
_Static_assert(__builtin_offsetof(struct move_pages_smp_req,user_virt_addr)==8,"request user_virt_addr");
_Static_assert(__builtin_offsetof(struct move_pages_smp_req,user_status)==16,"request user_status");
_Static_assert(__builtin_offsetof(struct move_pages_smp_req,user_nodes)==24,"request user_nodes");
_Static_assert(__builtin_offsetof(struct move_pages_smp_req,virt_addr)==32,"request virt_addr");
_Static_assert(__builtin_offsetof(struct move_pages_smp_req,status)==40,"request status");
_Static_assert(__builtin_offsetof(struct move_pages_smp_req,ptep)==48,"request ptep");
_Static_assert(__builtin_offsetof(struct move_pages_smp_req,nodes)==56,"request nodes");
_Static_assert(__builtin_offsetof(struct move_pages_smp_req,nodes_ready)==64,"request nodes_ready");
_Static_assert(__builtin_offsetof(struct move_pages_smp_req,nr_pages)==72,"request nr_pages");
_Static_assert(__builtin_offsetof(struct move_pages_smp_req,dst_phys)==80,"request dst_phys");
_Static_assert(__builtin_offsetof(struct move_pages_smp_req,proc)==88,"request proc");
_Static_assert(__builtin_offsetof(struct move_pages_smp_req,phase_done)==96,"request phase_done");
_Static_assert(__builtin_offsetof(struct move_pages_smp_req,phase_ret)==100,"request phase_ret");
/* Compare these actual real-header dependent offsets with Rust abi/offset_of,
 * not separately invented local process/CPU/context structures. */
unsigned long f06_move_pages_actual_dependent_abi[] = {
 sizeof(struct process),sizeof(struct process_vm),sizeof(struct thread),sizeof(struct cpu_local_var),
 __builtin_offsetof(struct process,vm),__builtin_offsetof(struct process_vm,address_space),
 __builtin_offsetof(struct process_vm,numa_mask),__builtin_offsetof(struct address_space,page_table),
 __builtin_offsetof(struct thread,vm),__builtin_offsetof(struct thread,proc),
 __builtin_offsetof(struct cpu_local_var,idle),__builtin_offsetof(struct cpu_local_var,current)
};
