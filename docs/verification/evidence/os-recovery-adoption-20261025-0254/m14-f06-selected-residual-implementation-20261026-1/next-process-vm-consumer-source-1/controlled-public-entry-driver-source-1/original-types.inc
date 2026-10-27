typedef void (*arch_process_vm_rw_lock_fn_t)(void *vm);
typedef struct vm_range *(*arch_process_vm_rw_lookup_range_fn_t)(void *vm,
		unsigned long start, unsigned long end);
typedef struct process *(*arch_process_vm_rw_find_process_fn_t)(int pid,
		void *lock_node);
typedef void (*arch_process_vm_rw_process_unlock_fn_t)(void *proc,
		void *lock_node);
typedef void (*arch_process_vm_rw_process_lock_fn_t)(void *proc,
		void *lock_node);
typedef void (*arch_process_vm_rw_vm_void_fn_t)(void *vm);
typedef int (*arch_process_vm_rw_vtop_fn_t)(void *page_table,
		unsigned long virt, unsigned long *phys, unsigned long *psize);
typedef int (*arch_process_vm_rw_fault_fn_t)(void *vm, unsigned long addr,
		unsigned long reason);
typedef void *(*arch_process_vm_rw_phys_to_virt_fn_t)(unsigned long phys);
typedef void (*arch_process_vm_rw_memcpy_fn_t)(void *dst, const void *src,
		size_t bytes);
struct arch_process_vm_rw_log_record {
	int event;
	int x;
	int y;
	int z;
	unsigned long a;
	unsigned long b;
	unsigned long c;
	unsigned long d;
	unsigned long e;
};
typedef void (*arch_process_vm_rw_log_fn_t)(
		const struct arch_process_vm_rw_log_record *record);
struct arch_process_vm_rw_offsets {
	size_t thread_proc_offset;
	size_t thread_vm_offset;
	size_t proc_vm_offset;
	size_t proc_status_offset;
	size_t proc_ruid_offset;
	size_t proc_euid_offset;
	size_t proc_suid_offset;
	size_t proc_rgid_offset;
	size_t proc_egid_offset;
	size_t proc_sgid_offset;
	size_t process_vm_address_space_offset;
	size_t address_space_page_table_offset;
	size_t vm_range_flag_offset;
};
