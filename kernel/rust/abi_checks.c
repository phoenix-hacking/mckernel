#include <types.h>
#include <affinity.h>
#include <syscall.h>
#include <llist.h>
#include <rbtree.h>
#include <ihk/lock.h>
#include <ihk/page_alloc.h>
#include <ihk/context.h>
#include <waitq.h>
#include <page.h>
#include <shm.h>
#include <process.h>
#include <timer.h>
#include <ihk/ihk_monitor.h>
#include <ihk/ihk_rusage.h>

#define ABI_ASSERT(cond, msg) _Static_assert(cond, msg)
#define ABI_OFFSET(type, member) __builtin_offsetof(type, member)

ABI_ASSERT(sizeof(struct program_image_section) == 56,
	   "Rust/C program_image_section size mismatch");
#ifdef ENABLE_TOFU
ABI_ASSERT(ABI_OFFSET(struct program_load_desc, sections) == 784,
	   "Rust/C program_load_desc sections offset mismatch");
#else
ABI_ASSERT(ABI_OFFSET(struct program_load_desc, sections) == 776,
	   "Rust/C program_load_desc sections offset mismatch");
#endif
ABI_ASSERT(sizeof(struct syscall_request) == 72,
	   "Rust/C syscall_request size mismatch");
ABI_ASSERT(ABI_OFFSET(struct syscall_request, args) == 24,
	   "Rust/C syscall_request args offset mismatch");
ABI_ASSERT(sizeof(struct syscall_response) == 48,
	   "Rust/C syscall_response size mismatch");
ABI_ASSERT(sizeof(struct ihk_ikc_packet_header) == 8,
	   "Rust/C ihk_ikc_packet_header size mismatch");
ABI_ASSERT(sizeof(struct ikc_scd_packet) == 128,
	   "Rust/C ikc_scd_packet size mismatch");
ABI_ASSERT(sizeof(struct x86_basic_regs) == 168,
	   "Rust/C x86_basic_regs size mismatch");
ABI_ASSERT(sizeof(struct x86_sregs) == 48,
	   "Rust/C x86_sregs size mismatch");
ABI_ASSERT(sizeof(ihk_mc_user_context_t) == 224,
	   "Rust/C ihk_mc_user_context_t size mismatch");
ABI_ASSERT(ABI_OFFSET(ihk_mc_user_context_t, gpr) == 56,
	   "Rust/C ihk_mc_user_context_t gpr offset mismatch");
ABI_ASSERT(sizeof(struct llist_head) == 8,
	   "Rust/C llist_head size mismatch");
ABI_ASSERT(ABI_OFFSET(struct llist_head, first) == 0,
	   "Rust/C llist_head first offset mismatch");
ABI_ASSERT(sizeof(struct llist_node) == 8,
	   "Rust/C llist_node size mismatch");
ABI_ASSERT(ABI_OFFSET(struct llist_node, next) == 0,
	   "Rust/C llist_node next offset mismatch");
ABI_ASSERT(sizeof(struct rb_node) == 24,
	   "Rust/C rb_node size mismatch");
ABI_ASSERT(ABI_OFFSET(struct rb_node, rb_right) == 8,
	   "Rust/C rb_node rb_right offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct rb_node, rb_left) == 16,
	   "Rust/C rb_node rb_left offset mismatch");
ABI_ASSERT(sizeof(struct rb_root) == 8,
	   "Rust/C rb_root size mismatch");
ABI_ASSERT(sizeof(struct free_chunk) == 48,
	   "Rust/C free_chunk size mismatch");
ABI_ASSERT(ABI_OFFSET(struct free_chunk, addr) == 0,
	   "Rust/C free_chunk addr offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct free_chunk, size) == 8,
	   "Rust/C free_chunk size offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct free_chunk, node) == 16,
	   "Rust/C free_chunk node offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct free_chunk, list) == 40,
	   "Rust/C free_chunk list offset mismatch");
ABI_ASSERT(sizeof(struct list_head) == 16,
	   "Rust/C list_head size mismatch");
ABI_ASSERT(ABI_OFFSET(struct list_head, prev) == 8,
	   "Rust/C list_head prev offset mismatch");
ABI_ASSERT(sizeof(ihk_spinlock_t) == 4,
	   "Rust/C ihk_spinlock_t size mismatch");
ABI_ASSERT(ABI_OFFSET(ihk_spinlock_t, head_tail) == 0,
	   "Rust/C ihk_spinlock_t head_tail offset mismatch");
ABI_ASSERT(sizeof(waitq_t) == 24,
	   "Rust/C waitq_t size mismatch");
ABI_ASSERT(ABI_OFFSET(waitq_t, waitq) == 8,
	   "Rust/C waitq_t waitq offset mismatch");
ABI_ASSERT(sizeof(waitq_entry_t) == 40,
	   "Rust/C waitq_entry_t size mismatch");
ABI_ASSERT(ABI_OFFSET(waitq_entry_t, private) == 16,
	   "Rust/C waitq_entry_t private offset mismatch");
ABI_ASSERT(ABI_OFFSET(waitq_entry_t, flags) == 24,
	   "Rust/C waitq_entry_t flags offset mismatch");
ABI_ASSERT(ABI_OFFSET(waitq_entry_t, func) == 32,
	   "Rust/C waitq_entry_t func offset mismatch");
ABI_ASSERT(sizeof(struct timer) == 56,
	   "Rust/C timer size mismatch");
ABI_ASSERT(ABI_OFFSET(struct timer, processes) == 8,
	   "Rust/C timer processes offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct timer, list) == 32,
	   "Rust/C timer list offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct timer, thread) == 48,
	   "Rust/C timer thread offset mismatch");
ABI_ASSERT(sizeof(struct rusage) == 144,
	   "Rust/C rusage size mismatch");
ABI_ASSERT(ABI_OFFSET(struct rusage, ru_stime) == 16,
	   "Rust/C rusage ru_stime offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct rusage, ru_maxrss) == 32,
	   "Rust/C rusage ru_maxrss offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct rusage, ru_nivcsw) == 136,
	   "Rust/C rusage ru_nivcsw offset mismatch");
ABI_ASSERT(sizeof(struct page) == 80,
	   "Rust/C page size mismatch");
ABI_ASSERT(ABI_OFFSET(struct page, list) == 0,
	   "Rust/C page list offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct page, hash) == 16,
	   "Rust/C page hash offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct page, mode) == 32,
	   "Rust/C page mode offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct page, phys) == 40,
	   "Rust/C page phys offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct page, count) == 48,
	   "Rust/C page count offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct page, mapped) == 56,
	   "Rust/C page mapped offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct page, offset) == 64,
	   "Rust/C page offset offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct page, pgshift) == 72,
	   "Rust/C page pgshift offset mismatch");
ABI_ASSERT(sizeof(mcs_lock_node_t) == 64,
	   "Rust/C mcs_lock_node_t size mismatch");
ABI_ASSERT(ABI_OFFSET(mcs_lock_node_t, locked) == 0,
	   "Rust/C mcs_lock_node_t locked offset mismatch");
ABI_ASSERT(ABI_OFFSET(mcs_lock_node_t, next) == 8,
	   "Rust/C mcs_lock_node_t next offset mismatch");
ABI_ASSERT(ABI_OFFSET(mcs_lock_node_t, irqsave) == 16,
	   "Rust/C mcs_lock_node_t irqsave offset mismatch");
ABI_ASSERT(sizeof(struct ihk_page_allocator_desc) == 192,
	   "Rust/C ihk_page_allocator_desc size mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_page_allocator_desc, start) == 0,
	   "Rust/C ihk_page_allocator_desc start offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_page_allocator_desc, end) == 8,
	   "Rust/C ihk_page_allocator_desc end offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_page_allocator_desc, last) == 16,
	   "Rust/C ihk_page_allocator_desc last offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_page_allocator_desc, count) == 20,
	   "Rust/C ihk_page_allocator_desc count offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_page_allocator_desc, flag) == 24,
	   "Rust/C ihk_page_allocator_desc flag offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_page_allocator_desc, shift) == 28,
	   "Rust/C ihk_page_allocator_desc shift offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_page_allocator_desc, lock) == 64,
	   "Rust/C ihk_page_allocator_desc lock offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_page_allocator_desc, list) == 128,
	   "Rust/C ihk_page_allocator_desc list offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_page_allocator_desc, map) == 144,
	   "Rust/C ihk_page_allocator_desc map offset mismatch");
ABI_ASSERT(sizeof(ihk_atomic_t) == 4,
	   "Rust/C ihk_atomic_t size mismatch");
ABI_ASSERT(ABI_OFFSET(ihk_atomic_t, counter) == 0,
	   "Rust/C ihk_atomic_t counter offset mismatch");
ABI_ASSERT(sizeof(struct ihk_mc_numa_node) == 256,
	   "Rust/C ihk_mc_numa_node size mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_numa_node, id) == 0,
	   "Rust/C ihk_mc_numa_node id offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_numa_node, linux_numa_id) == 4,
	   "Rust/C ihk_mc_numa_node linux_numa_id offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_numa_node, type) == 8,
	   "Rust/C ihk_mc_numa_node type offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_numa_node, allocators) == 16,
	   "Rust/C ihk_mc_numa_node allocators offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_numa_node, nodes_by_distance) == 32,
	   "Rust/C ihk_mc_numa_node nodes_by_distance offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_numa_node, zeroing_workers) == 40,
	   "Rust/C ihk_mc_numa_node zeroing_workers offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_numa_node, nr_to_zero_pages) == 44,
	   "Rust/C ihk_mc_numa_node nr_to_zero_pages offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_numa_node, zeroed_list) == 48,
	   "Rust/C ihk_mc_numa_node zeroed_list offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_numa_node, to_zero_list) == 56,
	   "Rust/C ihk_mc_numa_node to_zero_list offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_numa_node, free_chunks) == 64,
	   "Rust/C ihk_mc_numa_node free_chunks offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_numa_node, lock) == 128,
	   "Rust/C ihk_mc_numa_node lock offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_numa_node, nr_pages) == 192,
	   "Rust/C ihk_mc_numa_node nr_pages offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_numa_node, nr_free_pages) == 200,
	   "Rust/C ihk_mc_numa_node nr_free_pages offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_numa_node, min_addr) == 208,
	   "Rust/C ihk_mc_numa_node min_addr offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_numa_node, max_addr) == 216,
	   "Rust/C ihk_mc_numa_node max_addr offset mismatch");
ABI_ASSERT(sizeof(struct memobj) == 56,
	   "Rust/C memobj size mismatch");
ABI_ASSERT(ABI_OFFSET(struct memobj, flags) == 8,
	   "Rust/C memobj flags offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct memobj, refcnt) == 24,
	   "Rust/C memobj refcnt offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct memobj, pages) == 32,
	   "Rust/C memobj pages offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct memobj, path) == 48,
	   "Rust/C memobj path offset mismatch");
ABI_ASSERT(sizeof(struct ipc_perm) == 48,
	   "Rust/C ipc_perm size mismatch");
ABI_ASSERT(ABI_OFFSET(struct ipc_perm, seq) == 24,
	   "Rust/C ipc_perm seq offset mismatch");
ABI_ASSERT(sizeof(struct shmid_ds) == 112,
	   "Rust/C shmid_ds size mismatch");
ABI_ASSERT(ABI_OFFSET(struct shmid_ds, init_pgshift) == 108,
	   "Rust/C shmid_ds init_pgshift offset mismatch");
ABI_ASSERT(sizeof(struct shmobj) == 232,
	   "Rust/C shmobj size mismatch");
ABI_ASSERT(ABI_OFFSET(struct shmobj, index) == 56,
	   "Rust/C shmobj index offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct shmobj, ds) == 80,
	   "Rust/C shmobj ds offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct shmobj, chain) == 216,
	   "Rust/C shmobj chain offset mismatch");

ABI_ASSERT(sizeof(cpu_set_t) == 128,
	   "Rust/C cpu_set_t size mismatch");
ABI_ASSERT(sizeof(mcs_rwlock_lock_t) == 64,
	   "Rust/C mcs_rwlock_lock_t size mismatch");
ABI_ASSERT(ABI_OFFSET(mcs_rwlock_lock_t, slock) == 0,
	   "Rust/C mcs_rwlock_lock_t slock offset mismatch");
ABI_ASSERT(sizeof(struct process_hash) == 5888,
	   "Rust/C process_hash size mismatch");
ABI_ASSERT(ABI_OFFSET(struct process_hash, list) == 0,
	   "Rust/C process_hash list offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process_hash, lock) == 1216,
	   "Rust/C process_hash lock offset mismatch");
ABI_ASSERT(sizeof(struct thread_hash) == 5888,
	   "Rust/C thread_hash size mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread_hash, lock) == 1216,
	   "Rust/C thread_hash lock offset mismatch");
ABI_ASSERT(sizeof(struct resource_set) == 384,
	   "Rust/C resource_set size mismatch");
ABI_ASSERT(ABI_OFFSET(struct resource_set, path) == 16,
	   "Rust/C resource_set path offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct resource_set, process_hash) == 24,
	   "Rust/C resource_set process_hash offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct resource_set, phys_mem_lock) == 64,
	   "Rust/C resource_set phys_mem_lock offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct resource_set, cpu_set) == 128,
	   "Rust/C resource_set cpu_set offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct resource_set, pid1) == 320,
	   "Rust/C resource_set pid1 offset mismatch");
ABI_ASSERT(sizeof(struct address_space) == 168,
	   "Rust/C address_space size mismatch");
ABI_ASSERT(ABI_OFFSET(struct address_space, free_cb) == 16,
	   "Rust/C address_space free_cb offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct address_space, refcount) == 24,
	   "Rust/C address_space refcount offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct address_space, cpu_set) == 32,
	   "Rust/C address_space cpu_set offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct address_space, cpu_set_lock) == 160,
	   "Rust/C address_space cpu_set_lock offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct address_space, nslots) == 164,
	   "Rust/C address_space nslots offset mismatch");
#ifdef ENABLE_TOFU
ABI_ASSERT(sizeof(struct vm_range) == 104,
	   "Rust/C vm_range size mismatch");
ABI_ASSERT(ABI_OFFSET(struct vm_range, tofu_stag_list) == 80,
	   "Rust/C vm_range tofu_stag_list offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct vm_range, private_data) == 96,
	   "Rust/C vm_range private_data offset mismatch");
#else
ABI_ASSERT(sizeof(struct vm_range) == 88,
	   "Rust/C vm_range size mismatch");
ABI_ASSERT(ABI_OFFSET(struct vm_range, private_data) == 80,
	   "Rust/C vm_range private_data offset mismatch");
#endif
ABI_ASSERT(ABI_OFFSET(struct vm_range, vm_rb_node) == 0,
	   "Rust/C vm_range vm_rb_node offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct vm_range, start) == 24,
	   "Rust/C vm_range start offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct vm_range, straight_start) == 48,
	   "Rust/C vm_range straight_start offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct vm_range, memobj) == 56,
	   "Rust/C vm_range memobj offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct vm_range, objoff) == 64,
	   "Rust/C vm_range objoff offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct vm_range, pgshift) == 72,
	   "Rust/C vm_range pgshift offset mismatch");
ABI_ASSERT(sizeof(struct vm_range_numa_policy) == 80,
	   "Rust/C vm_range_numa_policy size mismatch");
ABI_ASSERT(ABI_OFFSET(struct vm_range_numa_policy, policy_rb_node) == 0,
	   "Rust/C vm_range_numa_policy policy_rb_node offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct vm_range_numa_policy, start) == 24,
	   "Rust/C vm_range_numa_policy start offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct vm_range_numa_policy, numa_mask) == 40,
	   "Rust/C vm_range_numa_policy numa_mask offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct vm_range_numa_policy, numa_mem_policy) == 72,
	   "Rust/C vm_range_numa_policy numa_mem_policy offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct vm_range_numa_policy, il_prev) == 76,
	   "Rust/C vm_range_numa_policy il_prev offset mismatch");
ABI_ASSERT(sizeof(struct vm_regions) == 120,
	   "Rust/C vm_regions size mismatch");
ABI_ASSERT(ABI_OFFSET(struct vm_regions, brk_start) == 48,
	   "Rust/C vm_regions brk_start offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct vm_regions, brk_end_allocated) == 64,
	   "Rust/C vm_regions brk_end_allocated offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct vm_regions, map_start) == 72,
	   "Rust/C vm_regions map_start offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct vm_regions, stack_start) == 88,
	   "Rust/C vm_regions stack_start offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct vm_regions, user_start) == 104,
	   "Rust/C vm_regions user_start offset mismatch");
#ifdef ENABLE_TOFU
ABI_ASSERT(sizeof(struct process_vm) == 376,
	   "Rust/C process_vm size mismatch");
ABI_ASSERT(ABI_OFFSET(struct process_vm, tofu_stag_lock) == 304,
	   "Rust/C process_vm tofu_stag_lock offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process_vm, tofu_stag_hash) == 312,
	   "Rust/C process_vm tofu_stag_hash offset mismatch");
#else
ABI_ASSERT(sizeof(struct process_vm) == 304,
	   "Rust/C process_vm size mismatch");
#endif
ABI_ASSERT(ABI_OFFSET(struct process_vm, address_space) == 0,
	   "Rust/C process_vm address_space offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process_vm, vm_range_tree) == 8,
	   "Rust/C process_vm vm_range_tree offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process_vm, region) == 16,
	   "Rust/C process_vm region offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process_vm, proc) == 136,
	   "Rust/C process_vm proc offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process_vm, free_cb) == 152,
	   "Rust/C process_vm free_cb offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process_vm, vdso_addr) == 160,
	   "Rust/C process_vm vdso_addr offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process_vm, page_table_lock) == 176,
	   "Rust/C process_vm page_table_lock offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process_vm, memory_range_lock) == 180,
	   "Rust/C process_vm memory_range_lock offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process_vm, refcount) == 188,
	   "Rust/C process_vm refcount offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process_vm, currss) == 200,
	   "Rust/C process_vm currss offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process_vm, numa_mask) == 208,
	   "Rust/C process_vm numa_mask offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process_vm, vm_range_numa_policy_tree) == 248,
	   "Rust/C process_vm vm_range_numa_policy_tree offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process_vm, range_cache) == 256,
	   "Rust/C process_vm range_cache offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process_vm, range_cache_ind) == 288,
	   "Rust/C process_vm range_cache_ind offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process_vm, swapinfo) == 296,
	   "Rust/C process_vm swapinfo offset mismatch");

ABI_ASSERT(sizeof(struct process) == 1728,
	   "Rust/C process size mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, vm) == 128,
	   "Rust/C process vm offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, threads_list) == 136,
	   "Rust/C process threads_list offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, main_thread) == 168,
	   "Rust/C process main_thread offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, parent) == 272,
	   "Rust/C process parent offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, refcount) == 416,
	   "Rust/C process refcount offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, status) == 420,
	   "Rust/C process status offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, group_exit_status) == 424,
	   "Rust/C process group_exit_status offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, waitpid_q) == 432,
	   "Rust/C process waitpid_q offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, pid) == 456,
	   "Rust/C process pid offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, rlimit) == 512,
	   "Rust/C process rlimit offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, cpu_set) == 1152,
	   "Rust/C process cpu_set offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, mckfd_lock) == 1284,
	   "Rust/C process mckfd_lock offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, stime) == 1296,
	   "Rust/C process stime offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, maxrss) == 1360,
	   "Rust/C process maxrss offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, straight_map) == 1432,
	   "Rust/C process straight_map offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, perf_status) == 1456,
	   "Rust/C process perf_status offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, monitoring_event) == 1464,
	   "Rust/C process monitoring_event offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, profile) == 1472,
	   "Rust/C process profile offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, nr_processes) == 1616,
	   "Rust/C process nr_processes offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, straight_va) == 1624,
	   "Rust/C process straight_va offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct process, coredump_lock) == 1664,
	   "Rust/C process coredump_lock offset mismatch");

ABI_ASSERT(sizeof(struct thread) == 5568,
	   "Rust/C thread size mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, cpu_id) == 16,
	   "Rust/C thread cpu_id offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, status) == 4184,
	   "Rust/C thread status offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, vm) == 4200,
	   "Rust/C thread vm offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, ctx) == 4208,
	   "Rust/C thread ctx offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, proc) == 4304,
	   "Rust/C thread proc offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, sched_list) == 4328,
	   "Rust/C thread sched_list offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, sched_policy) == 4344,
	   "Rust/C thread sched_policy offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, spin_sleep_lock) == 4352,
	   "Rust/C thread spin_sleep_lock offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, report_proc) == 4360,
	   "Rust/C thread report_proc offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, ptrace) == 4384,
	   "Rust/C thread ptrace offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, ptrace_saved_uctx) == 4400,
	   "Rust/C thread ptrace_saved_uctx offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, refcount) == 4628,
	   "Rust/C thread refcount offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, clear_child_tid) == 4632,
	   "Rust/C thread clear_child_tid offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, cpu_set) == 4656,
	   "Rust/C thread cpu_set offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, sigcommon) == 4824,
	   "Rust/C thread sigcommon offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, sigmask) == 4832,
	   "Rust/C thread sigmask offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, sigstack) == 4840,
	   "Rust/C thread sigstack offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, sigpending) == 4864,
	   "Rust/C thread sigpending offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, scd_wq) == 5176,
	   "Rust/C thread scd_wq offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, futex_q) == 5232,
	   "Rust/C thread futex_q offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, pmc_alloc_map) == 5464,
	   "Rust/C thread pmc_alloc_map offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, coredump_regs) == 5480,
	   "Rust/C thread coredump_regs offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct thread, rpf_backlog) == 5520,
	   "Rust/C thread rpf_backlog offset mismatch");

ABI_ASSERT(sizeof(struct mckfd) == 80,
	   "Rust/C mckfd size mismatch");
ABI_ASSERT(ABI_OFFSET(struct mckfd, fd) == 8,
	   "Rust/C mckfd fd offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct mckfd, data) == 16,
	   "Rust/C mckfd data offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct mckfd, read_cb) == 32,
	   "Rust/C mckfd read_cb offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct mckfd, dup_cb) == 72,
	   "Rust/C mckfd dup_cb offset mismatch");
ABI_ASSERT(sizeof(struct sig_common) == 2176,
	   "Rust/C sig_common size mismatch");
ABI_ASSERT(ABI_OFFSET(struct sig_common, use) == 64,
	   "Rust/C sig_common use offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sig_common, action) == 72,
	   "Rust/C sig_common action offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sig_common, sigpending) == 2120,
	   "Rust/C sig_common sigpending offset mismatch");
ABI_ASSERT(sizeof(struct sig_pending) == 160,
	   "Rust/C sig_pending size mismatch");
ABI_ASSERT(ABI_OFFSET(struct sig_pending, sigmask) == 16,
	   "Rust/C sig_pending sigmask offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sig_pending, info) == 24,
	   "Rust/C sig_pending info offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sig_pending, ptracecont) == 152,
	   "Rust/C sig_pending ptracecont offset mismatch");
ABI_ASSERT(sizeof(struct mcexec_tid) == 16,
	   "Rust/C mcexec_tid size mismatch");
ABI_ASSERT(ABI_OFFSET(struct mcexec_tid, thread) == 8,
	   "Rust/C mcexec_tid thread offset mismatch");

ABI_ASSERT(sizeof(struct ihk_os_cpu_register) == 32,
	   "Rust/C ihk_os_cpu_register size mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_os_cpu_register, val) == 8,
	   "Rust/C ihk_os_cpu_register val offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_os_cpu_register, sync) == 24,
	   "Rust/C ihk_os_cpu_register sync offset mismatch");
ABI_ASSERT(sizeof(struct ihk_os_cpu_monitor) == 24,
	   "Rust/C ihk_os_cpu_monitor size mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_os_cpu_monitor, counter) == 8,
	   "Rust/C ihk_os_cpu_monitor counter offset mismatch");
ABI_ASSERT(sizeof(struct ihk_os_monitor) == 1032,
	   "Rust/C ihk_os_monitor size mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_os_monitor, cpu) == 1032,
	   "Rust/C ihk_os_monitor cpu offset mismatch");
ABI_ASSERT(sizeof(struct ihk_os_rusage) == 16568,
	   "Rust/C ihk_os_rusage size mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_os_rusage, memory_max_usage) == 128,
	   "Rust/C ihk_os_rusage memory_max_usage offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_os_rusage, cpuacct_usage_percpu) == 8368,
	   "Rust/C ihk_os_rusage cpuacct_usage_percpu offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_os_rusage, num_threads) == 16560,
	   "Rust/C ihk_os_rusage num_threads offset mismatch");
