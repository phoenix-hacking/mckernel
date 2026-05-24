#include <types.h>
#include <affinity.h>
#include <syscall.h>
#include <llist.h>
#include <rbtree.h>
#include <rbtree_augmented.h>
#include <ihk/lock.h>
#include <ihk/page_alloc.h>
#include <ihk/context.h>
#include <waitq.h>
#include <page.h>
#include <shm.h>
#include <memobj.h>
#include <kref.h>
#include <lwk/compiler.h>
#include <process.h>
#include <timer.h>
#include <pager.h>
#include <elfcore.h>
#include <uio.h>
#include <sysfs.h>
#include <profile.h>
#include <ihk/mm.h>
#include <registers.h>
#include <cpulocal.h>
#include <sysfs_msg.h>
#include <ihk/ihk_monitor.h>
#include <ihk/ihk_rusage.h>
#include <rusage.h>
#include <cls.h>
#include <xpmem_private.h>
#include <futex.h>

#define ABI_ASSERT(cond, msg) _Static_assert(cond, msg)
#define ABI_OFFSET(type, member) __builtin_offsetof(type, member)

ABI_ASSERT(sizeof(struct user_desc) == 16,
	   "Rust/C user_desc size mismatch");
ABI_ASSERT(ABI_OFFSET(struct user_desc, base_addr) == 4,
	   "Rust/C user_desc base_addr offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct user_desc, limit) == 8,
	   "Rust/C user_desc limit offset mismatch");
ABI_ASSERT(sizeof(struct program_image_section) == 56,
	   "Rust/C program_image_section size mismatch");
ABI_ASSERT(sizeof(struct pager_create_result) == 4128,
	   "Rust/C pager_create_result size mismatch");
ABI_ASSERT(ABI_OFFSET(struct pager_create_result, maxprot) == 8,
	   "Rust/C pager_create_result maxprot offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct pager_create_result, flags) == 12,
	   "Rust/C pager_create_result flags offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct pager_create_result, size) == 16,
	   "Rust/C pager_create_result size offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct pager_create_result, pgshift) == 24,
	   "Rust/C pager_create_result pgshift offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct pager_create_result, path) == 28,
	   "Rust/C pager_create_result path offset mismatch");
ABI_ASSERT(sizeof(struct pager_map_result) == 4112,
	   "Rust/C pager_map_result size mismatch");
ABI_ASSERT(ABI_OFFSET(struct pager_map_result, maxprot) == 8,
	   "Rust/C pager_map_result maxprot offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct pager_map_result, padding) == 12,
	   "Rust/C pager_map_result padding offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct pager_map_result, path) == 16,
	   "Rust/C pager_map_result path offset mismatch");
#ifdef ENABLE_TOFU
ABI_ASSERT(ABI_OFFSET(struct program_load_desc, sections) == 784,
	   "Rust/C program_load_desc sections offset mismatch");
#else
ABI_ASSERT(ABI_OFFSET(struct program_load_desc, sections) == 776,
	   "Rust/C program_load_desc sections offset mismatch");
#endif
ABI_ASSERT(sizeof(struct ikc_scd_init_param) == 32,
	   "Rust/C ikc_scd_init_param size mismatch");
ABI_ASSERT(ABI_OFFSET(struct ikc_scd_init_param, response_page) == 8,
	   "Rust/C ikc_scd_init_param response_page offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ikc_scd_init_param, post_page) == 24,
	   "Rust/C ikc_scd_init_param post_page offset mismatch");
ABI_ASSERT(sizeof(struct syscall_request) == 72,
	   "Rust/C syscall_request size mismatch");
ABI_ASSERT(ABI_OFFSET(struct syscall_request, args) == 24,
	   "Rust/C syscall_request args offset mismatch");
ABI_ASSERT(sizeof(struct syscall_response) == 48,
	   "Rust/C syscall_response size mismatch");
ABI_ASSERT(sizeof(struct syscall_post) == 64,
	   "Rust/C syscall_post size mismatch");
ABI_ASSERT(sizeof(struct coretable) == 16,
	   "Rust/C coretable size mismatch");
ABI_ASSERT(ABI_OFFSET(struct coretable, addr) == 8,
	   "Rust/C coretable addr offset mismatch");
ABI_ASSERT(sizeof(Elf64_Ehdr) == 64,
	   "Rust/C Elf64_Ehdr size mismatch");
ABI_ASSERT(ABI_OFFSET(Elf64_Ehdr, e_phoff) == 32,
	   "Rust/C Elf64_Ehdr e_phoff offset mismatch");
ABI_ASSERT(ABI_OFFSET(Elf64_Ehdr, e_ehsize) == 52,
	   "Rust/C Elf64_Ehdr e_ehsize offset mismatch");
ABI_ASSERT(sizeof(Elf64_Phdr) == 56,
	   "Rust/C Elf64_Phdr size mismatch");
ABI_ASSERT(ABI_OFFSET(Elf64_Phdr, p_offset) == 8,
	   "Rust/C Elf64_Phdr p_offset offset mismatch");
ABI_ASSERT(ABI_OFFSET(Elf64_Phdr, p_filesz) == 32,
	   "Rust/C Elf64_Phdr p_filesz offset mismatch");
ABI_ASSERT(sizeof(struct note) == 12,
	   "Rust/C note size mismatch");
ABI_ASSERT(ABI_OFFSET(struct note, type) == 8,
	   "Rust/C note type offset mismatch");
ABI_ASSERT(sizeof(struct elf_siginfo) == 12,
	   "Rust/C elf_siginfo size mismatch");
ABI_ASSERT(ABI_OFFSET(struct elf_siginfo, si_code) == 4,
	   "Rust/C elf_siginfo si_code offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct elf_siginfo, si_errno) == 8,
	   "Rust/C elf_siginfo si_errno offset mismatch");
ABI_ASSERT(sizeof(struct prstatus64_timeval) == 16,
	   "Rust/C prstatus64_timeval size mismatch");
ABI_ASSERT(sizeof(struct elf_prstatus64) == 336,
	   "Rust/C elf_prstatus64 size mismatch");
ABI_ASSERT(ABI_OFFSET(struct elf_prstatus64, pr_sigpend) == 16,
	   "Rust/C elf_prstatus64 pr_sigpend offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct elf_prstatus64, pr_utime) == 48,
	   "Rust/C elf_prstatus64 pr_utime offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct elf_prstatus64, pr_reg) == 112,
	   "Rust/C elf_prstatus64 pr_reg offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct elf_prstatus64, pr_fpvalid) == 328,
	   "Rust/C elf_prstatus64 pr_fpvalid offset mismatch");
ABI_ASSERT(sizeof(struct elf_prpsinfo64) == 136,
	   "Rust/C elf_prpsinfo64 size mismatch");
ABI_ASSERT(ABI_OFFSET(struct elf_prpsinfo64, pr_flag) == 8,
	   "Rust/C elf_prpsinfo64 pr_flag offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct elf_prpsinfo64, pr_pid) == 24,
	   "Rust/C elf_prpsinfo64 pr_pid offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct elf_prpsinfo64, pr_fname) == 40,
	   "Rust/C elf_prpsinfo64 pr_fname offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct elf_prpsinfo64, pr_psargs) == 56,
	   "Rust/C elf_prpsinfo64 pr_psargs offset mismatch");
ABI_ASSERT(sizeof(struct iovec) == 16,
	   "Rust/C iovec size mismatch");
ABI_ASSERT(ABI_OFFSET(struct iovec, iov_len) == 8,
	   "Rust/C iovec iov_len offset mismatch");
ABI_ASSERT(sizeof(struct procfs_read) == 808,
	   "Rust/C procfs_read size mismatch");
ABI_ASSERT(ABI_OFFSET(struct procfs_read, offset) == 8,
	   "Rust/C procfs_read offset offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct procfs_read, count) == 16,
	   "Rust/C procfs_read count offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct procfs_read, fname) == 36,
	   "Rust/C procfs_read fname offset mismatch");
ABI_ASSERT(sizeof(struct procfs_file) == 776,
	   "Rust/C procfs_file size mismatch");
ABI_ASSERT(ABI_OFFSET(struct procfs_file, fname) == 8,
	   "Rust/C procfs_file fname offset mismatch");
ABI_ASSERT(sizeof(struct sysfs_req_create_param) == 1056,
	   "Rust/C sysfs_req_create_param size mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_req_create_param, client_ops) == 8,
	   "Rust/C sysfs_req_create_param client_ops offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_req_create_param, path) == 24,
	   "Rust/C sysfs_req_create_param path offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_req_create_param, busy) == 1052,
	   "Rust/C sysfs_req_create_param busy offset mismatch");
ABI_ASSERT(sizeof(struct sysfs_req_mkdir_param) == 1048,
	   "Rust/C sysfs_req_mkdir_param size mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_req_mkdir_param, handle) == 8,
	   "Rust/C sysfs_req_mkdir_param handle offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_req_mkdir_param, path) == 16,
	   "Rust/C sysfs_req_mkdir_param path offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_req_mkdir_param, busy) == 1044,
	   "Rust/C sysfs_req_mkdir_param busy offset mismatch");
ABI_ASSERT(sizeof(struct sysfs_req_symlink_param) == 1048,
	   "Rust/C sysfs_req_symlink_param size mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_req_symlink_param, target) == 8,
	   "Rust/C sysfs_req_symlink_param target offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_req_symlink_param, path) == 16,
	   "Rust/C sysfs_req_symlink_param path offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_req_symlink_param, busy) == 1044,
	   "Rust/C sysfs_req_symlink_param busy offset mismatch");
ABI_ASSERT(sizeof(struct sysfs_req_lookup_param) == 1048,
	   "Rust/C sysfs_req_lookup_param size mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_req_lookup_param, handle) == 8,
	   "Rust/C sysfs_req_lookup_param handle offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_req_lookup_param, path) == 16,
	   "Rust/C sysfs_req_lookup_param path offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_req_lookup_param, busy) == 1044,
	   "Rust/C sysfs_req_lookup_param busy offset mismatch");
ABI_ASSERT(sizeof(struct sysfs_req_unlink_param) == 1040,
	   "Rust/C sysfs_req_unlink_param size mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_req_unlink_param, path) == 8,
	   "Rust/C sysfs_req_unlink_param path offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_req_unlink_param, busy) == 1036,
	   "Rust/C sysfs_req_unlink_param busy offset mismatch");
ABI_ASSERT(sizeof(struct sysfs_req_setup_param) == 1056,
	   "Rust/C sysfs_req_setup_param size mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_req_setup_param, buf_rpa) == 8,
	   "Rust/C sysfs_req_setup_param buf_rpa offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_req_setup_param, padding3) == 24,
	   "Rust/C sysfs_req_setup_param padding3 offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_req_setup_param, busy) == 1052,
	   "Rust/C sysfs_req_setup_param busy offset mismatch");
ABI_ASSERT(sizeof(struct sysfs_ops) == 24,
	   "Rust/C sysfs_ops size mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_ops, show) == 0,
	   "Rust/C sysfs_ops show offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_ops, store) == 8,
	   "Rust/C sysfs_ops store offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_ops, release) == 16,
	   "Rust/C sysfs_ops release offset mismatch");
ABI_ASSERT(sizeof(sysfs_handle_t) == 8,
	   "Rust/C sysfs_handle_t size mismatch");
ABI_ASSERT(sizeof(struct sysfs_bitmap_param) == 16,
	   "Rust/C sysfs_bitmap_param size mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysfs_bitmap_param, ptr) == 8,
	   "Rust/C sysfs_bitmap_param ptr offset mismatch");
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
ABI_ASSERT(sizeof(ihk_mc_kernel_context_t) == 88,
	   "Rust/C ihk_mc_kernel_context_t size mismatch");
ABI_ASSERT(ABI_OFFSET(ihk_mc_kernel_context_t, rflags) == 72,
	   "Rust/C ihk_mc_kernel_context_t rflags offset mismatch");
ABI_ASSERT(ABI_OFFSET(ihk_mc_kernel_context_t, rsp0) == 80,
	   "Rust/C ihk_mc_kernel_context_t rsp0 offset mismatch");
ABI_ASSERT(sizeof(struct x86_desc_ptr) == 10,
	   "Rust/C x86_desc_ptr size mismatch");
ABI_ASSERT(__alignof__(struct x86_desc_ptr) == 1,
	   "Rust/C x86_desc_ptr alignment mismatch");
ABI_ASSERT(ABI_OFFSET(struct x86_desc_ptr, address) == 2,
	   "Rust/C x86_desc_ptr address offset mismatch");
ABI_ASSERT(sizeof(struct tss64) == 104,
	   "Rust/C tss64 size mismatch");
ABI_ASSERT(__alignof__(struct tss64) == 1,
	   "Rust/C tss64 alignment mismatch");
ABI_ASSERT(ABI_OFFSET(struct tss64, rsp0) == 4,
	   "Rust/C tss64 rsp0 offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct tss64, ist) == 36,
	   "Rust/C tss64 ist offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct tss64, iomap_address) == 102,
	   "Rust/C tss64 iomap_address offset mismatch");
ABI_ASSERT(sizeof(struct x86_cpu_local_variables) == 456,
	   "Rust/C x86_cpu_local_variables size mismatch");
ABI_ASSERT(__alignof__(struct x86_cpu_local_variables) == 1,
	   "Rust/C x86_cpu_local_variables alignment mismatch");
ABI_ASSERT(ABI_OFFSET(struct x86_cpu_local_variables, kernel_stack) == 16,
	   "Rust/C x86_cpu_local_variables kernel_stack offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct x86_cpu_local_variables, gdt_ptr) == 32,
	   "Rust/C x86_cpu_local_variables gdt_ptr offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct x86_cpu_local_variables, gdt) == 48,
	   "Rust/C x86_cpu_local_variables gdt offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct x86_cpu_local_variables, tss) == 176,
	   "Rust/C x86_cpu_local_variables tss offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct x86_cpu_local_variables, paniced) == 280,
	   "Rust/C x86_cpu_local_variables paniced offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct x86_cpu_local_variables, panic_regs) == 288,
	   "Rust/C x86_cpu_local_variables panic_regs offset mismatch");
ABI_ASSERT(sizeof(struct i387_fxsave_struct) == 512,
	   "Rust/C i387_fxsave_struct size mismatch");
ABI_ASSERT(__alignof__(struct i387_fxsave_struct) == 16,
	   "Rust/C i387_fxsave_struct alignment mismatch");
ABI_ASSERT(ABI_OFFSET(struct i387_fxsave_struct, rip) == 8,
	   "Rust/C i387_fxsave_struct rip offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct i387_fxsave_struct, mxcsr) == 24,
	   "Rust/C i387_fxsave_struct mxcsr offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct i387_fxsave_struct, st_space) == 32,
	   "Rust/C i387_fxsave_struct st_space offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct i387_fxsave_struct, xmm_space) == 160,
	   "Rust/C i387_fxsave_struct xmm_space offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct i387_fxsave_struct, sw_reserved) == 464,
	   "Rust/C i387_fxsave_struct sw_reserved offset mismatch");
ABI_ASSERT(sizeof(struct ymmh_struct) == 256,
	   "Rust/C ymmh_struct size mismatch");
ABI_ASSERT(sizeof(struct lwp_struct) == 128,
	   "Rust/C lwp_struct size mismatch");
ABI_ASSERT(sizeof(struct bndreg) == 16,
	   "Rust/C bndreg size mismatch");
ABI_ASSERT(__alignof__(struct bndreg) == 1,
	   "Rust/C bndreg alignment mismatch");
ABI_ASSERT(ABI_OFFSET(struct bndreg, upper_bound) == 8,
	   "Rust/C bndreg upper_bound offset mismatch");
ABI_ASSERT(sizeof(struct bndcsr) == 16,
	   "Rust/C bndcsr size mismatch");
ABI_ASSERT(ABI_OFFSET(struct bndcsr, bndstatus) == 8,
	   "Rust/C bndcsr bndstatus offset mismatch");
ABI_ASSERT(sizeof(struct xsave_hdr_struct) == 64,
	   "Rust/C xsave_hdr_struct size mismatch");
ABI_ASSERT(ABI_OFFSET(struct xsave_hdr_struct, xcomp_bv) == 8,
	   "Rust/C xsave_hdr_struct xcomp_bv offset mismatch");
ABI_ASSERT(sizeof(struct xsave_struct) == 1088,
	   "Rust/C xsave_struct size mismatch");
ABI_ASSERT(__alignof__(struct xsave_struct) == 64,
	   "Rust/C xsave_struct alignment mismatch");
ABI_ASSERT(ABI_OFFSET(struct xsave_struct, xsave_hdr) == 512,
	   "Rust/C xsave_struct xsave_hdr offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xsave_struct, ymmh) == 576,
	   "Rust/C xsave_struct ymmh offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xsave_struct, lwp) == 832,
	   "Rust/C xsave_struct lwp offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xsave_struct, bndreg) == 960,
	   "Rust/C xsave_struct bndreg offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xsave_struct, bndcsr) == 1024,
	   "Rust/C xsave_struct bndcsr offset mismatch");
ABI_ASSERT(sizeof(struct user_regs_struct) == 216,
	   "Rust/C user_regs_struct size mismatch");
ABI_ASSERT(ABI_OFFSET(struct user_regs_struct, rip) == 128,
	   "Rust/C user_regs_struct rip offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct user_regs_struct, fs_base) == 168,
	   "Rust/C user_regs_struct fs_base offset mismatch");
ABI_ASSERT(sizeof(struct user_fpregs_struct) == 512,
	   "Rust/C user_fpregs_struct size mismatch");
ABI_ASSERT(ABI_OFFSET(struct user_fpregs_struct, rip) == 8,
	   "Rust/C user_fpregs_struct rip offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct user_fpregs_struct, st_space) == 32,
	   "Rust/C user_fpregs_struct st_space offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct user_fpregs_struct, xmm_space) == 160,
	   "Rust/C user_fpregs_struct xmm_space offset mismatch");
ABI_ASSERT(sizeof(struct user) == 912,
	   "Rust/C user size mismatch");
ABI_ASSERT(ABI_OFFSET(struct user, i387) == 224,
	   "Rust/C user i387 offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct user, u_ar0) == 792,
	   "Rust/C user u_ar0 offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct user, u_debugreg) == 848,
	   "Rust/C user u_debugreg offset mismatch");
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
ABI_ASSERT(sizeof(struct sysinfo) == 112,
	   "Rust/C sysinfo size mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysinfo, loads) == 8,
	   "Rust/C sysinfo loads offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysinfo, procs) == 80,
	   "Rust/C sysinfo procs offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysinfo, totalhigh) == 88,
	   "Rust/C sysinfo totalhigh offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sysinfo, mem_unit) == 104,
	   "Rust/C sysinfo mem_unit offset mismatch");
ABI_ASSERT(sizeof(struct tod_data_s) == 40,
	   "Rust/C tod_data_s size mismatch");
ABI_ASSERT(ABI_OFFSET(struct tod_data_s, version) == 8,
	   "Rust/C tod_data_s version offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct tod_data_s, clocks_per_sec) == 16,
	   "Rust/C tod_data_s clocks_per_sec offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct tod_data_s, origin) == 24,
	   "Rust/C tod_data_s origin offset mismatch");
ABI_ASSERT(sizeof(struct itimerval) == 32,
	   "Rust/C itimerval size mismatch");
ABI_ASSERT(ABI_OFFSET(struct itimerval, it_value) == 16,
	   "Rust/C itimerval it_value offset mismatch");
#ifdef PROFILE_ENABLE
ABI_ASSERT(sizeof(struct profile_event) == 16,
	   "Rust/C profile_event size mismatch");
ABI_ASSERT(ABI_OFFSET(struct profile_event, tsc) == 8,
	   "Rust/C profile_event tsc offset mismatch");
#endif
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
ABI_ASSERT(sizeof(ihk_atomic64_t) == 8,
	   "Rust/C ihk_atomic64_t size mismatch");
ABI_ASSERT(ABI_OFFSET(ihk_atomic64_t, counter64) == 0,
	   "Rust/C ihk_atomic64_t counter64 offset mismatch");
ABI_ASSERT(sizeof(struct ihk_rwlock) == 8,
	   "Rust/C ihk_rwlock size mismatch");
ABI_ASSERT(__alignof__(struct ihk_rwlock) == 8,
	   "Rust/C ihk_rwlock alignment mismatch");
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
ABI_ASSERT(sizeof(struct memobj_ops) == 56,
	   "Rust/C memobj_ops size mismatch");
ABI_ASSERT(ABI_OFFSET(struct memobj_ops, get_page) == 8,
	   "Rust/C memobj_ops get_page offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct memobj_ops, update_page) == 48,
	   "Rust/C memobj_ops update_page offset mismatch");
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
ABI_ASSERT(sizeof(struct shminfo) == 72,
	   "Rust/C shminfo size mismatch");
ABI_ASSERT(ABI_OFFSET(struct shminfo, padding) == 40,
	   "Rust/C shminfo padding offset mismatch");
ABI_ASSERT(sizeof(struct shm_info) == 48,
	   "Rust/C shm_info size mismatch");
ABI_ASSERT(ABI_OFFSET(struct shm_info, shm_tot) == 8,
	   "Rust/C shm_info shm_tot offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct shm_info, swap_successes) == 40,
	   "Rust/C shm_info swap_successes offset mismatch");
ABI_ASSERT(sizeof(struct shmlock_user) == 32,
	   "Rust/C shmlock_user size mismatch");
ABI_ASSERT(ABI_OFFSET(struct shmlock_user, locked) == 8,
	   "Rust/C shmlock_user locked offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct shmlock_user, chain) == 16,
	   "Rust/C shmlock_user chain offset mismatch");
ABI_ASSERT(sizeof(struct kref) == 4,
	   "Rust/C kref size mismatch");
ABI_ASSERT(sizeof(struct rb_augment_callbacks) == 24,
	   "Rust/C rb_augment_callbacks size mismatch");
ABI_ASSERT(ABI_OFFSET(struct rb_augment_callbacks, copy) == 8,
	   "Rust/C rb_augment_callbacks copy offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct rb_augment_callbacks, rotate) == 16,
	   "Rust/C rb_augment_callbacks rotate offset mismatch");
ABI_ASSERT(sizeof(struct ftrace_branch_data) == 40,
	   "Rust/C ftrace_branch_data size mismatch");
ABI_ASSERT(ABI_OFFSET(struct ftrace_branch_data, line) == 16,
	   "Rust/C ftrace_branch_data line offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ftrace_branch_data, miss_hit) == 24,
	   "Rust/C ftrace_branch_data miss_hit offset mismatch");
ABI_ASSERT(sizeof(struct ftrace_likely_data) == 48,
	   "Rust/C ftrace_likely_data size mismatch");
ABI_ASSERT(ABI_OFFSET(struct ftrace_likely_data, constant) == 40,
	   "Rust/C ftrace_likely_data constant offset mismatch");
ABI_ASSERT(sizeof(struct xpmem_id) == 8,
	   "Rust/C xpmem_id size mismatch");
ABI_ASSERT(sizeof(xpmem_id_t) == 8,
	   "Rust/C xpmem_id_t size mismatch");
ABI_ASSERT(__alignof__(xpmem_id_t) == 8,
	   "Rust/C xpmem_id_t alignment mismatch");
ABI_ASSERT(sizeof(struct xpmem_hashlist) == 128,
	   "Rust/C xpmem_hashlist size mismatch");
ABI_ASSERT(__alignof__(struct xpmem_hashlist) == 64,
	   "Rust/C xpmem_hashlist alignment mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_hashlist, list) == 64,
	   "Rust/C xpmem_hashlist list offset mismatch");
ABI_ASSERT(sizeof(struct xpmem_thread_group) == 192,
	   "Rust/C xpmem_thread_group prefix size mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_thread_group, seg_list_lock) == 64,
	   "Rust/C xpmem_thread_group seg_list_lock offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_thread_group, seg_list) == 128,
	   "Rust/C xpmem_thread_group seg_list offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_thread_group, refcnt) == 144,
	   "Rust/C xpmem_thread_group refcnt offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_thread_group, tg_hashlist) == 152,
	   "Rust/C xpmem_thread_group tg_hashlist offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_thread_group, group_leader) == 168,
	   "Rust/C xpmem_thread_group group_leader offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_thread_group, vm) == 176,
	   "Rust/C xpmem_thread_group vm offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_thread_group, ap_hashtable) == 192,
	   "Rust/C xpmem_thread_group ap_hashtable offset mismatch");
ABI_ASSERT(sizeof(struct xpmem_segment) == 96,
	   "Rust/C xpmem_segment size mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_segment, segid) == 8,
	   "Rust/C xpmem_segment segid offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_segment, permit_value) == 40,
	   "Rust/C xpmem_segment permit_value offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_segment, tg) == 56,
	   "Rust/C xpmem_segment tg offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_segment, seg_list) == 80,
	   "Rust/C xpmem_segment seg_list offset mismatch");
ABI_ASSERT(sizeof(struct xpmem_access_permit) == 96,
	   "Rust/C xpmem_access_permit size mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_access_permit, apid) == 8,
	   "Rust/C xpmem_access_permit apid offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_access_permit, seg) == 32,
	   "Rust/C xpmem_access_permit seg offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_access_permit, att_list) == 48,
	   "Rust/C xpmem_access_permit att_list offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_access_permit, ap_hashlist) == 80,
	   "Rust/C xpmem_access_permit ap_hashlist offset mismatch");
ABI_ASSERT(sizeof(struct xpmem_partition) == 64,
	   "Rust/C xpmem_partition prefix size mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_partition, tg_hashtable) == 64,
	   "Rust/C xpmem_partition tg_hashtable offset mismatch");
ABI_ASSERT(sizeof(struct xpmem_perm) == 16,
	   "Rust/C xpmem_perm size mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_perm, mode) == 8,
	   "Rust/C xpmem_perm mode offset mismatch");
ABI_ASSERT(sizeof(struct xpmem_attachment) == 80,
	   "Rust/C xpmem_attachment size mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_attachment, vaddr) == 8,
	   "Rust/C xpmem_attachment vaddr offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_attachment, at_vmr) == 32,
	   "Rust/C xpmem_attachment at_vmr offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_attachment, refcnt) == 44,
	   "Rust/C xpmem_attachment refcnt offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_attachment, att_list) == 56,
	   "Rust/C xpmem_attachment att_list offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct xpmem_attachment, vm) == 72,
	   "Rust/C xpmem_attachment vm offset mismatch");

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
ABI_ASSERT(sizeof(sigset_t) == 8,
	   "Rust/C sigset_t size mismatch");
ABI_ASSERT(sizeof(struct sigaction) == 32,
	   "Rust/C sigaction size mismatch");
ABI_ASSERT(ABI_OFFSET(struct sigaction, sa_flags) == 8,
	   "Rust/C sigaction sa_flags offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sigaction, sa_restorer) == 16,
	   "Rust/C sigaction sa_restorer offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct sigaction, sa_mask) == 24,
	   "Rust/C sigaction sa_mask offset mismatch");
ABI_ASSERT(sizeof(struct k_sigaction) == 32,
	   "Rust/C k_sigaction size mismatch");
ABI_ASSERT(ABI_OFFSET(struct k_sigaction, sa) == 0,
	   "Rust/C k_sigaction sa offset mismatch");
ABI_ASSERT(sizeof(stack_t) == 24,
	   "Rust/C stack_t size mismatch");
ABI_ASSERT(ABI_OFFSET(stack_t, ss_flags) == 8,
	   "Rust/C stack_t ss_flags offset mismatch");
ABI_ASSERT(ABI_OFFSET(stack_t, ss_size) == 16,
	   "Rust/C stack_t ss_size offset mismatch");
ABI_ASSERT(sizeof(sigval_t) == 8,
	   "Rust/C sigval_t size mismatch");
ABI_ASSERT(sizeof(siginfo_t) == 128,
	   "Rust/C siginfo_t size mismatch");
ABI_ASSERT(ABI_OFFSET(siginfo_t, si_errno) == 4,
	   "Rust/C siginfo_t si_errno offset mismatch");
ABI_ASSERT(ABI_OFFSET(siginfo_t, si_code) == 8,
	   "Rust/C siginfo_t si_code offset mismatch");
ABI_ASSERT(ABI_OFFSET(siginfo_t, _sifields) == 16,
	   "Rust/C siginfo_t _sifields offset mismatch");
ABI_ASSERT(sizeof(struct signalfd_siginfo) == 128,
	   "Rust/C signalfd_siginfo size mismatch");
ABI_ASSERT(ABI_OFFSET(struct signalfd_siginfo, ssi_ptr) == 48,
	   "Rust/C signalfd_siginfo ssi_ptr offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct signalfd_siginfo, ssi_addr_lsb) == 80,
	   "Rust/C signalfd_siginfo ssi_addr_lsb offset mismatch");
ABI_ASSERT(sizeof(struct futex_hash_bucket) == 40,
	   "Rust/C futex_hash_bucket size mismatch");
ABI_ASSERT(ABI_OFFSET(struct futex_hash_bucket, chain) == 8,
	   "Rust/C futex_hash_bucket chain offset mismatch");
ABI_ASSERT(sizeof(union futex_key) == 24,
	   "Rust/C futex_key size mismatch");
ABI_ASSERT(ABI_OFFSET(union futex_key, shared.phys) == 8,
	   "Rust/C futex_key shared.phys offset mismatch");
ABI_ASSERT(ABI_OFFSET(union futex_key, both.offset) == 16,
	   "Rust/C futex_key both.offset offset mismatch");
ABI_ASSERT(sizeof(struct futex_q) == 232,
	   "Rust/C futex_q size mismatch");
ABI_ASSERT(ABI_OFFSET(struct futex_q, task) == 40,
	   "Rust/C futex_q task offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct futex_q, key) == 56,
	   "Rust/C futex_q key offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct futex_q, bitset) == 88,
	   "Rust/C futex_q bitset offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct futex_q, th_spin_sleep) == 112,
	   "Rust/C futex_q th_spin_sleep offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct futex_q, intr_id) == 168,
	   "Rust/C futex_q intr_id offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct futex_q, th_spin_sleep_pa) == 176,
	   "Rust/C futex_q th_spin_sleep_pa offset mismatch");
ABI_ASSERT(sizeof(struct cpu_mapping) == 8,
	   "Rust/C cpu_mapping size mismatch");
ABI_ASSERT(ABI_OFFSET(struct cpu_mapping, hw_id) == 4,
	   "Rust/C cpu_mapping hw_id offset mismatch");
ABI_ASSERT(sizeof(struct get_cpu_mapping_req) == 24,
	   "Rust/C get_cpu_mapping_req size mismatch");
ABI_ASSERT(ABI_OFFSET(struct get_cpu_mapping_req, buf_rpa) == 8,
	   "Rust/C get_cpu_mapping_req buf_rpa offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct get_cpu_mapping_req, buf_elems) == 16,
	   "Rust/C get_cpu_mapping_req buf_elems offset mismatch");
ABI_ASSERT(sizeof(struct perf_ctrl_desc) == 40,
	   "Rust/C perf_ctrl_desc size mismatch");
ABI_ASSERT(ABI_OFFSET(struct perf_ctrl_desc, target_cntr) == 8,
	   "Rust/C perf_ctrl_desc target_cntr offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct perf_ctrl_desc, config) == 16,
	   "Rust/C perf_ctrl_desc config offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct perf_ctrl_desc, read_value) == 24,
	   "Rust/C perf_ctrl_desc read_value offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct perf_ctrl_desc, target_cntr_mask) == 8,
	   "Rust/C perf_ctrl_desc target_cntr_mask offset mismatch");
ABI_ASSERT(sizeof(uti_attr_t) == 136,
	   "Rust/C uti_attr_t size mismatch");
ABI_ASSERT(ABI_OFFSET(uti_attr_t, flags) == 128,
	   "Rust/C uti_attr_t flags offset mismatch");
ABI_ASSERT(sizeof(struct uti_ctx) == 4096,
	   "Rust/C uti_ctx size mismatch");
ABI_ASSERT(sizeof(struct move_pages_smp_req) == 104,
	   "Rust/C move_pages_smp_req size mismatch");
ABI_ASSERT(ABI_OFFSET(struct move_pages_smp_req, user_virt_addr) == 8,
	   "Rust/C move_pages_smp_req user_virt_addr offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct move_pages_smp_req, ptep) == 48,
	   "Rust/C move_pages_smp_req ptep offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct move_pages_smp_req, nodes_ready) == 64,
	   "Rust/C move_pages_smp_req nodes_ready offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct move_pages_smp_req, nr_pages) == 72,
	   "Rust/C move_pages_smp_req nr_pages offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct move_pages_smp_req, proc) == 88,
	   "Rust/C move_pages_smp_req proc offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct move_pages_smp_req, phase_done) == 96,
	   "Rust/C move_pages_smp_req phase_done offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct move_pages_smp_req, phase_ret) == 100,
	   "Rust/C move_pages_smp_req phase_ret offset mismatch");
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
ABI_ASSERT(sizeof(struct rusage_percpu) == 16,
	   "Rust/C rusage_percpu size mismatch");
ABI_ASSERT(ABI_OFFSET(struct rusage_percpu, system_tsc) == 8,
	   "Rust/C rusage_percpu system_tsc offset mismatch");
ABI_ASSERT(sizeof(struct ihk_mc_memory_area) == 24,
	   "Rust/C ihk_mc_memory_area size mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_memory_area, type) == 16,
	   "Rust/C ihk_mc_memory_area type offset mismatch");
ABI_ASSERT(sizeof(struct ihk_mc_memory_node) == 16,
	   "Rust/C ihk_mc_memory_node size mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_memory_node, areas) == 8,
	   "Rust/C ihk_mc_memory_node areas offset mismatch");
ABI_ASSERT(sizeof(struct ihk_mc_pa_ops) == 32,
	   "Rust/C ihk_mc_pa_ops size mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_pa_ops, free_page) == 8,
	   "Rust/C ihk_mc_pa_ops free_page offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_pa_ops, alloc) == 16,
	   "Rust/C ihk_mc_pa_ops alloc offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_pa_ops, free) == 24,
	   "Rust/C ihk_mc_pa_ops free offset mismatch");
ABI_ASSERT(sizeof(struct tlb_flush_entry) == 64,
	   "Rust/C tlb_flush_entry size mismatch");
ABI_ASSERT(__alignof__(struct tlb_flush_entry) == 64,
	   "Rust/C tlb_flush_entry alignment mismatch");
ABI_ASSERT(ABI_OFFSET(struct tlb_flush_entry, addr) == 8,
	   "Rust/C tlb_flush_entry addr offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct tlb_flush_entry, nr_addr) == 16,
	   "Rust/C tlb_flush_entry nr_addr offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct tlb_flush_entry, pending) == 20,
	   "Rust/C tlb_flush_entry pending offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct tlb_flush_entry, lock) == 24,
	   "Rust/C tlb_flush_entry lock offset mismatch");
ABI_ASSERT(sizeof(struct ihk_mc_page_cache_header) == 8,
	   "Rust/C ihk_mc_page_cache_header size mismatch");
ABI_ASSERT(ABI_OFFSET(struct ihk_mc_page_cache_header, next) == 0,
	   "Rust/C ihk_mc_page_cache_header next offset mismatch");
ABI_ASSERT(sizeof(struct kmalloc_cache_header) == 8,
	   "Rust/C kmalloc_cache_header size mismatch");
ABI_ASSERT(sizeof(struct kmalloc_header) == 32,
	   "Rust/C kmalloc_header size mismatch");
ABI_ASSERT(ABI_OFFSET(struct kmalloc_header, cpu_id) == 4,
	   "Rust/C kmalloc_header cpu_id offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct kmalloc_header, size) == 24,
	   "Rust/C kmalloc_header size offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct kmalloc_header, end_magic) == 28,
	   "Rust/C kmalloc_header end_magic offset mismatch");
ABI_ASSERT(sizeof(struct smp_func_call_data) == 24,
	   "Rust/C smp_func_call_data size mismatch");
ABI_ASSERT(ABI_OFFSET(struct smp_func_call_data, cpus_left) == 4,
	   "Rust/C smp_func_call_data cpus_left offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct smp_func_call_data, func) == 8,
	   "Rust/C smp_func_call_data func offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct smp_func_call_data, arg) == 16,
	   "Rust/C smp_func_call_data arg offset mismatch");
ABI_ASSERT(sizeof(struct smp_func_call_request) == 32,
	   "Rust/C smp_func_call_request size mismatch");
ABI_ASSERT(ABI_OFFSET(struct smp_func_call_request, cpu_index) == 8,
	   "Rust/C smp_func_call_request cpu_index offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct smp_func_call_request, list) == 16,
	   "Rust/C smp_func_call_request list offset mismatch");
ABI_ASSERT(sizeof(struct backlog) == 32,
	   "Rust/C backlog size mismatch");
ABI_ASSERT(ABI_OFFSET(struct backlog, func) == 16,
	   "Rust/C backlog func offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct backlog, arg) == 24,
	   "Rust/C backlog arg offset mismatch");
ABI_ASSERT(sizeof(struct cpu_local_var) == 8128,
	   "Rust/C cpu_local_var size mismatch");
ABI_ASSERT(__alignof__(struct cpu_local_var) == 64,
	   "Rust/C cpu_local_var alignment mismatch");
ABI_ASSERT(ABI_OFFSET(struct cpu_local_var, idle) == 64,
	   "Rust/C cpu_local_var idle offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct cpu_local_var, idle_proc) == 5632,
	   "Rust/C cpu_local_var idle_proc offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct cpu_local_var, idle_vm) == 7360,
	   "Rust/C cpu_local_var idle_vm offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct cpu_local_var, idle_asp) == 7664,
	   "Rust/C cpu_local_var idle_asp offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct cpu_local_var, current) == 7848,
	   "Rust/C cpu_local_var current offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct cpu_local_var, runq) == 7872,
	   "Rust/C cpu_local_var runq offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct cpu_local_var, status) == 7920,
	   "Rust/C cpu_local_var status offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct cpu_local_var, pending_free_pages) == 7928,
	   "Rust/C cpu_local_var pending_free_pages offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct cpu_local_var, migq) == 7952,
	   "Rust/C cpu_local_var migq offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct cpu_local_var, no_preempt) == 7976,
	   "Rust/C cpu_local_var no_preempt offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct cpu_local_var, monitor) == 8000,
	   "Rust/C cpu_local_var monitor offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct cpu_local_var, rusage) == 8008,
	   "Rust/C cpu_local_var rusage offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct cpu_local_var, smp_func_req_list) == 8024,
	   "Rust/C cpu_local_var smp_func_req_list offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct cpu_local_var, backlog_list) == 8056,
	   "Rust/C cpu_local_var backlog_list offset mismatch");
ABI_ASSERT(ABI_OFFSET(struct cpu_local_var, uti_futex_resp) == 8072,
	   "Rust/C cpu_local_var uti_futex_resp offset mismatch");
