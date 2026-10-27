#include "genuine-prologue.inc"
#include "original-types.inc"
#include "original-body-prototype.inc"

struct cpu_local_var *fixture_cpu(void);
void fixture_range_lock(ihk_rwspinlock_t *);
void fixture_range_unlock(ihk_rwspinlock_t *);
struct vm_range *fixture_lookup(struct process_vm *, unsigned long, unsigned long);
struct process *fixture_find(int, struct mcs_rwlock_node_irqsave *);
void fixture_process_unlock(struct process *, struct mcs_rwlock_node_irqsave *);
void fixture_update_lock(struct mcs_rwlock_lock *, struct mcs_rwlock_node *);
void fixture_update_unlock(struct mcs_rwlock_lock *, struct mcs_rwlock_node *);
void fixture_hold(struct process_vm *);
void fixture_release(struct process_vm *);
int fixture_vtop(struct page_table *, const void *, unsigned long *, unsigned long *);
int fixture_fault(struct process_vm *, void *, unsigned long);
void *fixture_phys(unsigned long);
void *fixture_copy(void *, const void *, size_t);
extern void arch_process_vm_rw_log_bridge(const struct arch_process_vm_rw_log_record *);
extern const struct arch_process_vm_rw_offsets arch_process_vm_rw_kernel_offsets;
#undef get_this_cpu_local_var
#define get_this_cpu_local_var fixture_cpu
#undef ihk_rwspinlock_read_lock_noirq
#define ihk_rwspinlock_read_lock_noirq fixture_range_lock
#undef ihk_rwspinlock_read_unlock_noirq
#define ihk_rwspinlock_read_unlock_noirq fixture_range_unlock
#undef lookup_process_memory_range
#define lookup_process_memory_range fixture_lookup
#undef find_process
#define find_process fixture_find
#undef process_unlock
#define process_unlock fixture_process_unlock
#undef mcs_rwlock_reader_lock_noirq
#define mcs_rwlock_reader_lock_noirq fixture_update_lock
#undef mcs_rwlock_reader_unlock_noirq
#define mcs_rwlock_reader_unlock_noirq fixture_update_unlock
#undef hold_process_vm
#define hold_process_vm fixture_hold
#undef release_process_vm
#define release_process_vm fixture_release
#undef ihk_mc_pt_virt_to_phys_size
#define ihk_mc_pt_virt_to_phys_size fixture_vtop
#undef page_fault_process_vm
#define page_fault_process_vm fixture_fault
#undef phys_to_virt
#define phys_to_virt fixture_phys
#undef fast_memcpy
#define fast_memcpy fixture_copy
#undef do_process_vm_read_writev
#define do_process_vm_read_writev original_selected_process_vm_rw
#include "original-adapters.inc"
#include "original-entry.inc"
#undef get_this_cpu_local_var
#undef ihk_rwspinlock_read_lock_noirq
#undef ihk_rwspinlock_read_unlock_noirq
#undef lookup_process_memory_range
#undef find_process
#undef process_unlock
#undef mcs_rwlock_reader_lock_noirq
#undef mcs_rwlock_reader_unlock_noirq
#undef hold_process_vm
#undef release_process_vm
#undef ihk_mc_pt_virt_to_phys_size
#undef page_fault_process_vm
#undef phys_to_virt
#undef fast_memcpy
#undef do_process_vm_read_writev
#include "ABI-caller.inc"
#include "controlled-driver.inc"
