/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE ONLY. Future actual body fixture must provide its controlled CPU-local
 * state/callbacks before linking either entry. No driver or executable queue.
 */
#include <process.h>
#include <cls.h>
#include <errno.h>
#include <uio.h>
extern int do_process_vm_read_writev(int,const struct iovec *,unsigned long,
        const struct iovec *,unsigned long,unsigned long,int);
extern int original_selected_process_vm_rw(int,const struct iovec *,unsigned long,
        const struct iovec *,unsigned long,unsigned long,int);
extern unsigned long f06_process_vm_rw_Rust_ABI_fact(unsigned long);
typedef int (*real_process_vm_rw_entry)(int,const struct iovec *,unsigned long,
        const struct iovec *,unsigned long,unsigned long,int);
_Static_assert(__builtin_types_compatible_p(__typeof__(&do_process_vm_read_writev),real_process_vm_rw_entry),"actual C public ABI");
_Static_assert(sizeof(struct mcs_rwlock_node)==64 && __alignof__(struct mcs_rwlock_node)==64,"exact update node");
_Static_assert(sizeof(struct mcs_rwlock_node_irqsave)==64 && __alignof__(struct mcs_rwlock_node_irqsave)==64,"exact find node");
int f06_process_vm_rw_compare_ABI(void)
{
 const unsigned long facts[]={sizeof(struct thread),sizeof(struct process),sizeof(struct process_vm),sizeof(struct address_space),sizeof(struct iovec),sizeof(struct mcs_rwlock_node_irqsave),__alignof__(struct mcs_rwlock_node_irqsave),sizeof(struct mcs_rwlock_node),__alignof__(struct mcs_rwlock_node),
  __builtin_offsetof(struct thread,proc),__builtin_offsetof(struct thread,vm),
  __builtin_offsetof(struct process,vm),__builtin_offsetof(struct process,status),
  __builtin_offsetof(struct process,ruid),__builtin_offsetof(struct process,euid),__builtin_offsetof(struct process,suid),
  __builtin_offsetof(struct process,rgid),__builtin_offsetof(struct process,egid),__builtin_offsetof(struct process,sgid),
  __builtin_offsetof(struct process_vm,address_space),__builtin_offsetof(struct address_space,page_table),__builtin_offsetof(struct vm_range,flag)};
 for(unsigned long i=0;i<sizeof facts/sizeof facts[0];i++)if(facts[i]!=f06_process_vm_rw_Rust_ABI_fact(i))return 1;
 return 0;
}
int f06_process_vm_rw_validation_entry_comparison(void)
{
 /* Full unchanged Rust body must execute. These early rejects use neither IOV
  * bytes nor process/VM callbacks, but both wrappers still fetch current first.
  * A later fixture must retain CPU-current capture and callback absence facts.
  */
 const unsigned long bad_flags[]={1UL,2UL,0x8000000000000000UL,~0UL};
 for(unsigned long i=0;i<sizeof bad_flags/sizeof bad_flags[0];i++) {
  int old=original_selected_process_vm_rw(31,NULL,0,NULL,0,bad_flags[i],0);
  int rust=do_process_vm_read_writev(31,NULL,0,NULL,0,bad_flags[i],0);
  if(old!=-EINVAL || rust!=old)return 2;
 }
 return 0;
}
