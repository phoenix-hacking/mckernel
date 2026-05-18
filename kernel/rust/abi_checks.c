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
