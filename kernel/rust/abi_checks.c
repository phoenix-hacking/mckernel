#include <types.h>
#include <affinity.h>
#include <syscall.h>
#include <llist.h>
#include <ihk/context.h>

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
