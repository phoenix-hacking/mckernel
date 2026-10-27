__attribute__((weak)) int ihk_mc_chk_page_address(unsigned long mem_addr) { (void)mem_addr; return 0; }
__attribute__((weak)) unsigned long virt_to_phys(void *v) { return (unsigned long)v; }
__attribute__((weak)) void *phys_to_virt(unsigned long p) { return (void *)p; }
__attribute__((weak)) unsigned long linux_page_offset_base = 0xffff880000000000UL;
__attribute__((weak)) unsigned long x86_kernel_phys_base = 0x200000UL;
__attribute__((weak)) int x86_addr_init_pt_loaded_bridge(void) { return 1; }
__attribute__((weak)) unsigned long x86_user_map_kernel_start_bridge(void)
{
	return 0xfffffffffe800000UL;
}
__attribute__((weak)) void x86_addr_log_bridge(int event, unsigned long value)
{
	(void)event;
	(void)value;
}
struct rust_stub_mem_list_head {
	struct rust_stub_mem_list_head *next;
	struct rust_stub_mem_list_head *prev;
};
__attribute__((weak)) char *memdebug;
__attribute__((weak)) struct rust_stub_mem_list_head pagealloc_track_hash[256];
__attribute__((weak)) unsigned int pagealloc_track_hash_locks[256];
__attribute__((weak)) struct rust_stub_mem_list_head pagealloc_addr_hash[256];
__attribute__((weak)) unsigned int pagealloc_addr_hash_locks[256];
__attribute__((weak)) int pagealloc_track_initialized;
__attribute__((weak)) int pagealloc_runcount;
__attribute__((weak)) struct rust_stub_mem_list_head kmalloc_track_hash[256];
__attribute__((weak)) unsigned int kmalloc_track_hash_locks[256];
__attribute__((weak)) struct rust_stub_mem_list_head kmalloc_addr_hash[256];
__attribute__((weak)) unsigned int kmalloc_addr_hash_locks[256];
__attribute__((weak)) int kmalloc_runcount;
__attribute__((weak)) void mem_pagealloc_track_spin_init_bridge(unsigned long lock_addr)
{
	(void)lock_addr;
}
__attribute__((weak)) void mem_kmalloc_track_spin_init_bridge(unsigned long lock_addr)
{
	(void)lock_addr;
}
extern int rust_stub_page_alloc_calls;
extern int rust_stub_page_alloc_npages[8];
extern int rust_stub_page_alloc_p2align[8];
extern unsigned long rust_stub_page_alloc_flags[8];
extern int rust_stub_page_alloc_node[8];
extern int rust_stub_page_alloc_is_user[8];
extern unsigned long rust_stub_page_alloc_virt[8];
extern void *rust_stub_page_alloc_result[8];
__attribute__((weak)) void *mem_pagealloc_track_base_alloc_bridge(
		int npages, int p2align, unsigned long flag, int node,
		int is_user, unsigned long virt_addr)
{
	int idx = rust_stub_page_alloc_calls++;
	void *result = __builtin_malloc((unsigned long)npages * 4096UL);

	if (idx >= 0 && idx < 8) {
		rust_stub_page_alloc_npages[idx] = npages;
		rust_stub_page_alloc_p2align[idx] = p2align;
		rust_stub_page_alloc_flags[idx] = flag;
		rust_stub_page_alloc_node[idx] = node;
		rust_stub_page_alloc_is_user[idx] = is_user;
		rust_stub_page_alloc_virt[idx] = virt_addr;
		rust_stub_page_alloc_result[idx] = result;
	}
	return result;
}
__attribute__((weak)) void mem_pagealloc_track_base_free_bridge(
		void *ptr, int npages, int is_user)
{
	(void)npages;
	(void)is_user;
	__builtin_free(ptr);
}
__attribute__((weak)) void *mem_pagealloc_track_meta_alloc_bridge(
		int size, unsigned long flag)
{
	(void)flag;
	return __builtin_malloc((unsigned long)size);
}
__attribute__((weak)) void mem_pagealloc_track_meta_free_bridge(void *ptr)
{
	__builtin_free(ptr);
}
__attribute__((weak)) unsigned long mem_pagealloc_track_lock_bridge(
		unsigned long lock_addr)
{
	(void)lock_addr;
	return 0;
}
__attribute__((weak)) void mem_pagealloc_track_unlock_bridge(
		unsigned long lock_addr, unsigned long irqflags)
{
	(void)lock_addr;
	(void)irqflags;
}
__attribute__((weak)) void mem_pagealloc_track_noirq_lock_bridge(
		unsigned long lock_addr)
{
	(void)lock_addr;
}
__attribute__((weak)) void mem_pagealloc_track_noirq_unlock_bridge(
		unsigned long lock_addr)
{
	(void)lock_addr;
}
__attribute__((weak)) void mem_pagealloc_track_log_bridge(
		int event, void *ptr, char *file, int line, int npages)
{
	(void)event;
	(void)ptr;
	(void)file;
	(void)line;
	(void)npages;
}
__attribute__((weak)) void mem_pagealloc_invalid_free_bridge(
		void *ptr, char *file, int line)
{
	(void)ptr;
	(void)file;
	(void)line;
}
__attribute__((weak)) void mem_pagealloc_invalid_size_bridge(
		void *ptr, int npages, int alloc_npages, char *file, int line)
{
	(void)ptr;
	(void)npages;
	(void)alloc_npages;
	(void)file;
	(void)line;
}
__attribute__((weak)) void mem_pagealloc_leak_log_bridge(
		int event, void *ptr, char *file, int line, int size,
		int count, int runcount)
{
	(void)event;
	(void)ptr;
	(void)file;
	(void)line;
	(void)size;
	(void)count;
	(void)runcount;
}
extern int rust_stub_kmalloc_calls;
extern int rust_stub_kmalloc_size;
extern int rust_stub_kmalloc_flags;
extern char *rust_stub_kmalloc_file;
extern int rust_stub_kmalloc_line;
__attribute__((weak)) void *mem_kmalloc_track_base_alloc_bridge(
		int size, unsigned long flag)
{
	rust_stub_kmalloc_calls++;
	rust_stub_kmalloc_size = size;
	rust_stub_kmalloc_flags = (int)flag;
	rust_stub_kmalloc_file = 0;
	rust_stub_kmalloc_line = 0;
	return __builtin_malloc((unsigned long)size);
}
__attribute__((weak)) void mem_kmalloc_track_base_free_bridge(void *ptr)
{
	__builtin_free(ptr);
}
__attribute__((weak)) unsigned long mem_kmalloc_track_lock_bridge(
		unsigned long lock_addr)
{
	(void)lock_addr;
	return 0;
}
__attribute__((weak)) void mem_kmalloc_track_unlock_bridge(
		unsigned long lock_addr, unsigned long irqflags)
{
	(void)lock_addr;
	(void)irqflags;
}
__attribute__((weak)) void mem_kmalloc_track_log_bridge(
		int event, void *ptr, char *file, int line, int size)
{
	(void)event;
	(void)ptr;
	(void)file;
	(void)line;
	(void)size;
}
__attribute__((weak)) void mem_kmalloc_invalid_free_bridge(
		void *ptr, char *file, int line)
{
	(void)ptr;
	(void)file;
	(void)line;
}
__attribute__((weak)) void mem_kmalloc_leak_log_bridge(
		int event, void *ptr, char *file, int line, int size,
		int count, int runcount)
{
	(void)event;
	(void)ptr;
	(void)file;
	(void)line;
	(void)size;
	(void)count;
	(void)runcount;
}
__attribute__((weak)) long arch_syscall_forward_context_bridge(int syscall_nr,
		void *ctx)
{
	(void)syscall_nr;
	(void)ctx;
	return -38;
}
__attribute__((weak)) int arch_prctl_set_register_bridge(int type,
		unsigned long value)
{
	(void)type;
	(void)value;
	return 0;
}
__attribute__((weak)) int arch_prctl_get_register_bridge(int type,
		unsigned long *addr)
{
	(void)type;
	if (addr)
		*addr = 0;
	return 0;
}
__attribute__((weak)) void arch_prctl_log_bridge(int event, int cpu,
		unsigned long value)
{
	(void)event;
	(void)cpu;
	(void)value;
}
__attribute__((weak)) int arch_do_shmget_bridge(long key, unsigned long size,
		int shmflg)
{
	(void)key;
	(void)size;
	(void)shmflg;
	return -38;
}
__attribute__((weak)) void arch_shmget_log_bridge(int event, long key,
		unsigned long size, int shmflg, int shift, int result)
{
	(void)event;
	(void)key;
	(void)size;
	(void)shmflg;
	(void)shift;
	(void)result;
}
__attribute__((weak)) unsigned int tod_data_lock;
__attribute__((weak)) void syscall_settimeofday_lock_bridge(void *lock)
{
	(void)lock;
}
__attribute__((weak)) void syscall_settimeofday_unlock_bridge(void *lock)
{
	(void)lock;
}
__attribute__((weak)) long syscall_atomic64_read_bridge(void *value)
{
	(void)value;
	return 0;
}
__attribute__((weak)) void syscall_atomic64_inc_bridge(void *value)
{
	(void)value;
}
__attribute__((weak)) void syscall_wmb_bridge(void)
{
}
__attribute__((weak)) void syscall_settimeofday_panic_bridge(void)
{
}
__attribute__((weak)) void syscall_settimeofday_log_bridge(int event,
		unsigned long utv, unsigned long utz, long sec, long nsec,
		long error)
{
	(void)event;
	(void)utv;
	(void)utz;
	(void)sec;
	(void)nsec;
	(void)error;
}
__attribute__((weak)) void syscall_swapout_log_bridge(const void *fname,
		void *buf, unsigned long size, int flag)
{
	(void)fname;
	(void)buf;
	(void)size;
	(void)flag;
}
__attribute__((weak)) long syscall_util_thread_bridge(void *arg)
{
	(void)arg;
	return 0;
}
__attribute__((weak)) void syscall_util_indicate_clone_disabled_bridge(void)
{
}
__attribute__((weak)) void syscall_mbind_entry_log_bridge(
		unsigned long addr, unsigned long len, int mode,
		unsigned long nodemask_addr, unsigned long flags)
{
	(void)addr;
	(void)len;
	(void)mode;
	(void)nodemask_addr;
	(void)flags;
}
__attribute__((weak)) void syscall_mbind_write_lock_bridge(void *lock)
{
	(void)lock;
}
__attribute__((weak)) void syscall_mbind_write_unlock_bridge(void *lock)
{
	(void)lock;
}
__attribute__((weak)) void *syscall_mbind_lookup_range_bridge(
		void *vm, unsigned long start, unsigned long end)
{
	(void)vm;
	(void)start;
	(void)end;
	return 0;
}
__attribute__((weak)) void *syscall_mbind_policy_search_bridge(
		void *vm, unsigned long addr)
{
	(void)vm;
	(void)addr;
	return 0;
}
__attribute__((weak)) int syscall_mbind_clear_range_bridge(
		void *vm, unsigned long start, unsigned long end)
{
	(void)vm;
	(void)start;
	(void)end;
	return 0;
}
__attribute__((weak)) void *syscall_mbind_policy_alloc_bridge(
		unsigned long size, unsigned long flags)
{
	(void)flags;
	return __builtin_malloc(size ? size : 1);
}
__attribute__((weak)) void syscall_mbind_policy_rb_clear_bridge(
		void *range_policy)
{
	(void)range_policy;
}
__attribute__((weak)) int syscall_mbind_policy_insert_bridge(
		void *vm, void *range_policy)
{
	(void)vm;
	(void)range_policy;
	return 0;
}
__attribute__((weak)) void syscall_mbind_log_bridge(int event,
		unsigned long arg0, unsigned long arg1, int arg2)
{
	(void)event;
	(void)arg0;
	(void)arg1;
	(void)arg2;
}
__attribute__((weak)) void mprotect_flush_nfo_bridge(void)
{
}
__attribute__((weak)) int remap_file_pages_callable_bridge(void *memobj)
{
	(void)memobj;
	return 0;
}
__attribute__((weak)) int remap_file_pages_remap_bridge(void *vm,
		void *range, unsigned long start, unsigned long end, long off)
{
	(void)vm;
	(void)range;
	(void)start;
	(void)end;
	(void)off;
	return 0;
}
__attribute__((weak)) void remap_file_pages_clear_host_bridge(
		unsigned long start, unsigned long size, int holding_lock)
{
	(void)start;
	(void)size;
	(void)holding_lock;
}
__attribute__((weak)) void remap_file_pages_log_bridge(const void *record)
{
	(void)record;
}
__attribute__((weak)) int mremap_extend_bridge(void *vm, void *range,
		unsigned long newend)
{
	(void)vm;
	(void)range;
	(void)newend;
	return 0;
}
__attribute__((weak)) int mremap_search_bridge(unsigned long size,
		unsigned long pgshift, unsigned long *newstartp)
{
	(void)size;
	(void)pgshift;
	if (newstartp)
		*newstartp = 0x30000UL;
	return 0;
}
__attribute__((weak)) void mremap_memobj_ref_bridge(void *memobj)
{
	(void)memobj;
}
__attribute__((weak)) void mremap_memobj_unref_bridge(void *memobj)
{
	(void)memobj;
}
__attribute__((weak)) int mremap_add_range_bridge(void *vm,
		unsigned long start, unsigned long end, long pgshift,
		unsigned long flags, void *memobj, unsigned long objoff)
{
	(void)vm;
	(void)start;
	(void)end;
	(void)pgshift;
	(void)flags;
	(void)memobj;
	(void)objoff;
	return 0;
}
__attribute__((weak)) void mremap_pte_lock_bridge(void *lock)
{
	(void)lock;
}
__attribute__((weak)) void mremap_pte_unlock_bridge(void *lock)
{
	(void)lock;
}
__attribute__((weak)) int mremap_move_pte_bridge(void *page_table,
		void *vm, void *oldstart, void *newstart, unsigned long size,
		void *range)
{
	(void)page_table;
	(void)vm;
	(void)oldstart;
	(void)newstart;
	(void)size;
	(void)range;
	return 0;
}
__attribute__((weak)) void mremap_log_bridge(const void *record)
{
	(void)record;
}
__attribute__((weak)) void msync_read_lock_bridge(void *lock)
{
	(void)lock;
}
__attribute__((weak)) void msync_read_unlock_bridge(void *lock)
{
	(void)lock;
}
__attribute__((weak)) void *msync_lookup_range_bridge(void *vm,
		unsigned long start, unsigned long end)
{
	(void)vm;
	(void)start;
	(void)end;
	return 0;
}
__attribute__((weak)) void *msync_next_range_bridge(void *vm, void *range)
{
	(void)vm;
	(void)range;
	return 0;
}
__attribute__((weak)) int msync_has_pager_bridge(void *memobj)
{
	(void)memobj;
	return 0;
}
__attribute__((weak)) int msync_sync_range_bridge(void *vm, void *range,
		unsigned long start, unsigned long end)
{
	(void)vm;
	(void)range;
	(void)start;
	(void)end;
	return 0;
}
__attribute__((weak)) int msync_invalidate_range_bridge(void *vm,
		void *range, unsigned long start, unsigned long end)
{
	(void)vm;
	(void)range;
	(void)start;
	(void)end;
	return 0;
}
__attribute__((weak)) void msync_log_bridge(int event, unsigned long start,
		unsigned long len, int flags, int error)
{
	(void)event;
	(void)start;
	(void)len;
	(void)flags;
	(void)error;
}
__attribute__((weak)) unsigned long process_spin_lock_bridge(
		unsigned long lock_addr)
{
	(void)lock_addr;
	return 0;
}
__attribute__((weak)) void process_spin_unlock_bridge(
		unsigned long lock_addr, unsigned long irqstate)
{
	(void)lock_addr;
	(void)irqstate;
}
__attribute__((weak)) void process_sched_noirq_lock_bridge(
		unsigned long lock_addr)
{
	(void)lock_addr;
}
__attribute__((weak)) void process_sched_noirq_unlock_bridge(
		unsigned long lock_addr)
{
	(void)lock_addr;
}
__attribute__((weak)) unsigned long process_sched_cpu_local_bridge(int cpu_id)
{
	(void)cpu_id;
	return 0;
}
__attribute__((weak)) int process_sched_vector_bridge(int vector_key)
{
	return vector_key;
}
__attribute__((weak)) void process_sched_interrupt_bridge(int cpu, int vector)
{
	(void)cpu;
	(void)vector;
}
__attribute__((weak)) void process_sched_runq_log_bridge(int event,
		unsigned long arg0, unsigned long arg1, int arg2, int arg3)
{
	(void)event;
	(void)arg0;
	(void)arg1;
	(void)arg2;
	(void)arg3;
}
__attribute__((weak)) void process_sched_rwlock_bridge(
		unsigned long lock_addr, unsigned long node_addr)
{
	(void)lock_addr;
	(void)node_addr;
}
__attribute__((weak)) void process_sched_rwunlock_bridge(
		unsigned long lock_addr, unsigned long node_addr)
{
	(void)lock_addr;
	(void)node_addr;
}
__attribute__((weak)) void process_sched_status_set_bridge(
		unsigned long status_addr, int status)
{
	if (status_addr)
		*(int *)status_addr = status;
}
__attribute__((weak)) void process_sched_set_timer_bridge(int runq_locked)
{
	(void)runq_locked;
}
__attribute__((weak)) void process_sched_procfs_create_thread_bridge(
		unsigned long thread_addr)
{
	(void)thread_addr;
}
__attribute__((weak)) int process_sched_counter_inc_bridge(
		unsigned long counter_addr)
{
	if (!counter_addr)
		return 0;
	return __sync_add_and_fetch((int *)counter_addr, 1);
}
__attribute__((weak)) void process_sched_counter_dec_bridge(
		unsigned long counter_addr)
{
	if (counter_addr)
		__sync_fetch_and_sub((unsigned long *)counter_addr, 1);
}
__attribute__((weak)) void process_sched_rusage_threads_inc_bridge(void) {}
__attribute__((weak)) void process_sched_rusage_debug_bridge(void) {}
__attribute__((weak)) int waitq_sched_wakeup_thread_bridge(
		void *thread, int state)
{
	return ((unsigned long)thread ^ (unsigned int)state) & 0x7fffffff;
}
__attribute__((weak)) int waitq_sched_wakeup_thread_locked_bridge(
		void *thread, int state)
{
	return ((((unsigned long)thread) << 1) ^ (unsigned int)state) &
	       0x7fffffff;
}
__attribute__((weak)) int copy_to_user(void *dst, const void *src,
		unsigned long size)
{
	if (!dst || (!src && size))
		return -14;
	__builtin_memcpy(dst, src, size);
	return 0;
}
__attribute__((weak)) int copy_from_user(void *dst, const void *src,
		unsigned long size)
{
	if (!dst || (!src && size))
		return -14;
	__builtin_memcpy(dst, src, size);
	return 0;
}
__attribute__((weak)) void preempt_disable(void) {}
__attribute__((weak)) void preempt_enable(void) {}
__attribute__((weak)) void cpu_pause(void) {}
__attribute__((weak)) int cpu_interrupt_disabled(void) { return 1; }
__attribute__((weak)) unsigned long cpu_enable_interrupt_save(void) { return 0; }
__attribute__((weak)) void arch_barrier(void) { __asm__ __volatile__("" : : : "memory"); }
__attribute__((weak)) unsigned long smp_load_acquire_ulong(const unsigned long *p)
{
	unsigned long value = *(const volatile unsigned long *)p;

	arch_barrier();
	return value;
}
__attribute__((weak)) unsigned int smp_load_acquire_uint(const unsigned int *p)
{
	unsigned int value = *(const volatile unsigned int *)p;

	arch_barrier();
	return value;
}
__attribute__((weak)) int smp_load_acquire_int(const int *p)
{
	int value = *(const volatile int *)p;

	arch_barrier();
	return value;
}
__attribute__((weak)) void *smp_load_acquire_ptr(void *const *p)
{
	void *value = *(void *const volatile *)p;

	arch_barrier();
	return value;
}
__attribute__((weak)) void smp_store_release_ulong(unsigned long *p,
		unsigned long value)
{
	arch_barrier();
	*(volatile unsigned long *)p = value;
}
__attribute__((weak)) void smp_store_release_uint(unsigned int *p,
		unsigned int value)
{
	arch_barrier();
	*(volatile unsigned int *)p = value;
}
__attribute__((weak)) void smp_store_release_int(int *p, int value)
{
	arch_barrier();
	*(volatile int *)p = value;
}
__attribute__((weak)) void arch_delay(int us) { (void)us; }
__attribute__((weak)) void ihk_mc_delay_us(int us) { (void)us; }
struct timer_runtime_offsets {
	unsigned long thread_status_offset;
	unsigned long thread_sched_list_offset;
	unsigned long thread_spin_sleep_lock_offset;
	unsigned long thread_spin_sleep_offset;
	unsigned long thread_itimer_enabled_offset;
	unsigned long cpu_runq_lock_offset;
	unsigned long cpu_runq_offset;
	unsigned long cpu_runq_len_offset;
	unsigned long cpu_current_offset;
	unsigned long cpu_timer_enabled_offset;
	unsigned long cpu_backlog_list_offset;
	unsigned long timer_timeout_offset;
	unsigned long timer_waitq_offset;
	unsigned long timer_list_offset;
	unsigned long timer_thread_offset;
};
/* Only host equivalence bindings; production providers remain process.c. */
__attribute__((weak)) const struct timer_runtime_offsets process_timer_runtime_offsets;
__attribute__((weak)) unsigned long process_timer_spin_lock_bridge(unsigned long p)
{ (void)p; return 0; }
__attribute__((weak)) void process_timer_spin_unlock_bridge(unsigned long p, unsigned long s)
{ (void)p; (void)s; }
__attribute__((weak)) void process_timer_lapic_enable_bridge(unsigned int c) { (void)c; }
__attribute__((weak)) void process_timer_lapic_disable_bridge(void) {}

__attribute__((weak)) int ihk_ikc_send(void *channel, void *packet, int opt)
{
	(void)channel;
	(void)packet;
	(void)opt;
	return 0;
}
struct rust_stub_ikc_listen_param {
	int (*handler)(void *);
	int port;
	int ikc_direction;
	int pkt_size;
	int queue_size;
	int magic;
};
int rust_stub_ikc_listen_port_calls;
void *rust_stub_ikc_listen_port_os;
int rust_stub_ikc_listen_port_port;
int rust_stub_ikc_listen_port_pkt_size;
int rust_stub_ikc_listen_port_queue_size;
int rust_stub_ikc_listen_port_magic;
__attribute__((weak)) int ihk_ikc_listen_port(void *os,
		struct rust_stub_ikc_listen_param *param)
{
	rust_stub_ikc_listen_port_calls++;
	rust_stub_ikc_listen_port_os = os;
	if (param) {
		rust_stub_ikc_listen_port_port = param->port;
		rust_stub_ikc_listen_port_pkt_size = param->pkt_size;
		rust_stub_ikc_listen_port_queue_size = param->queue_size;
		rust_stub_ikc_listen_port_magic = param->magic;
	}
	return 0;
}
__attribute__((weak)) int num_processors;
__attribute__((weak)) int sysctl_overcommit_memory;
__attribute__((weak)) void eventfd(int type) { (void)type; }
int rust_stub_ikc_system_init_calls;
void *rust_stub_ikc_system_init_os;
__attribute__((weak)) void ihk_ikc_system_init(void *os)
{
	rust_stub_ikc_system_init_calls++;
	rust_stub_ikc_system_init_os = os;
}
int rust_stub_ikc_init_queue_calls;
void *rust_stub_ikc_init_queue_q[4];
int rust_stub_ikc_init_queue_id[4];
int rust_stub_ikc_init_queue_type[4];
int rust_stub_ikc_init_queue_size[4];
int rust_stub_ikc_init_queue_packetsize[4];
__attribute__((weak)) int ihk_ikc_init_queue(void *q, int id, int type,
		int size, int packetsize)
{
	int idx = rust_stub_ikc_init_queue_calls++;

	if (idx >= 0 && idx < 4) {
		rust_stub_ikc_init_queue_q[idx] = q;
		rust_stub_ikc_init_queue_id[idx] = id;
		rust_stub_ikc_init_queue_type[idx] = type;
		rust_stub_ikc_init_queue_size[idx] = size;
		rust_stub_ikc_init_queue_packetsize[idx] = packetsize;
	}
	return 0;
}
int rust_stub_ikc_init_desc_calls;
void *rust_stub_ikc_init_desc_channel;
void *rust_stub_ikc_init_desc_remote_os;
int rust_stub_ikc_init_desc_channel_id;
void *rust_stub_ikc_init_desc_recv;
void *rust_stub_ikc_init_desc_send;
int (*rust_stub_ikc_init_desc_handler)(void *, void *, void *);
void *rust_stub_ikc_init_desc_master;
__attribute__((weak)) void ihk_ikc_init_desc(void *channel, void *remote_os,
		int channel_id, void *recv_queue, void *send_queue,
		int (*packet_handler)(void *, void *, void *), void *master)
{
	rust_stub_ikc_init_desc_calls++;
	rust_stub_ikc_init_desc_channel = channel;
	rust_stub_ikc_init_desc_remote_os = remote_os;
	rust_stub_ikc_init_desc_channel_id = channel_id;
	rust_stub_ikc_init_desc_recv = recv_queue;
	rust_stub_ikc_init_desc_send = send_queue;
	rust_stub_ikc_init_desc_handler = packet_handler;
	rust_stub_ikc_init_desc_master = master;
}
int rust_stub_ikc_enable_calls;
void *rust_stub_ikc_enable_channel;
__attribute__((weak)) void ihk_ikc_enable_channel(void *channel)
{
	rust_stub_ikc_enable_calls++;
	rust_stub_ikc_enable_channel = channel;
}
int rust_stub_arch_set_mikc_queue_calls;
void *rust_stub_arch_set_mikc_queue_recv;
void *rust_stub_arch_set_mikc_queue_send;
__attribute__((weak)) void arch_set_mikc_queue(void *recv_queue,
		void *send_queue)
{
	rust_stub_arch_set_mikc_queue_calls++;
	rust_stub_arch_set_mikc_queue_recv = recv_queue;
	rust_stub_arch_set_mikc_queue_send = send_queue;
}
__attribute__((weak)) int ihk_ikc_master_channel_packet_handler(
		void *channel, void *packet, void *arg)
{
	(void)channel;
	(void)packet;
	(void)arg;
	return 0;
}
__attribute__((weak)) void cpu_disable_interrupt(void) {}
__attribute__((weak)) void cpu_halt(void) {}
__attribute__((weak)) unsigned long cpu_disable_interrupt_save(void) { return 0; }
__attribute__((weak)) void cpu_restore_interrupt(unsigned long flags) { (void)flags; }
__attribute__((weak)) int kprintf(const char *format, ...)
{
	(void)format;
	return 0;
}
__attribute__((weak)) int __kprintf(const char *format, ...)
{
	(void)format;
	return 0;
}
__attribute__((weak)) unsigned long kprintf_lock(void) { return 0; }
__attribute__((weak)) void kprintf_unlock(unsigned long flags) { (void)flags; }
struct rust_stub_ddebug {
	const char *file;
	const char *func;
	const char *fmt;
	unsigned int line_flags;
};
__attribute__((weak)) struct rust_stub_ddebug __start___verbose[1];
__attribute__((weak)) struct rust_stub_ddebug __stop___verbose[1];
__attribute__((weak)) int host_ikc_inited;
int rust_stub_ikc_init_calls;
void *rust_stub_ikc_init_channel;
int (*rust_stub_ikc_init_handler)(void *, void *, void *);
__attribute__((weak)) int ihk_mc_ikc_init_first(void *channel,
		int (*handler)(void *, void *, void *))
{
	rust_stub_ikc_init_calls++;
	rust_stub_ikc_init_channel = channel;
	rust_stub_ikc_init_handler = handler;
	return 0;
}
__attribute__((weak)) void *boot_param;
__attribute__((weak)) void *map_fixed_area(unsigned long phys,
		unsigned long size, unsigned long flags)
{
	(void)size;
	(void)flags;
	return (void *)phys;
}
__attribute__((weak)) int ihk_mc_ikc_arch_issue_host_ipi(int cpu, int vector)
{
	(void)cpu;
	(void)vector;
	return 0;
}
__attribute__((weak)) void (*x86_issue_ipi)(int, int);
__attribute__((weak)) int running_on_kvm(void)
{
	return 0;
}
__attribute__((weak)) int ihk_mc_get_processor_id_equiv(void)
{
	return 0;
}
__attribute__((weak)) void init_tick(void) {}
__attribute__((weak)) void sync_tick(void) {}
extern int cpu_log_count __attribute__((weak));
extern int cpu_log_events[] __attribute__((weak));
__attribute__((weak)) void x86_tick_log_bridge(int event)
{
	if (&cpu_log_count && cpu_log_events) {
		cpu_log_events[cpu_log_count] = event;
		cpu_log_count++;
	}
}
__attribute__((weak)) void kmalloc_init(void) {}
__attribute__((weak)) void sched_init(void) {}
__attribute__((weak)) int arch_setup_pvclock(void) { return 0; }
__attribute__((weak)) void arch_start_pvclock(void) {}
__attribute__((weak)) void *pvti;
__attribute__((weak)) int pvti_npages;
__attribute__((weak)) long pvti_msr;
__attribute__((weak)) int x86_current_cpu_bridge(void)
{
	return 0;
}
__attribute__((weak)) unsigned long x86_virt_to_phys_bridge(void *addr)
{
	return (unsigned long)addr;
}
__attribute__((weak)) void x86_lapic_write_bridge(int reg,
		unsigned int value)
{
	(void)reg;
	(void)value;
}
__attribute__((weak)) unsigned long x86_read_msr_bridge(int reg)
{
	(void)reg;
	return 0;
}
__attribute__((weak)) void x86_write_msr_bridge(int reg, unsigned long value)
{
	(void)reg;
	(void)value;
}
__attribute__((weak)) void x86_cpuid_leaf_bridge(unsigned long op,
		unsigned long *eaxp, unsigned long *ebxp,
		unsigned long *ecxp, unsigned long *edxp)
{
	(void)op;
	if (eaxp)
		*eaxp = 0;
	if (ebxp)
		*ebxp = 0;
	if (ecxp)
		*ecxp = 0;
	if (edxp)
		*edxp = 0;
}
__attribute__((weak)) void *x86_alloc_aligned_pages_node_bridge(int npages,
		int p2align, unsigned long flag, int node, int is_user,
		unsigned long virt_addr, char *file, int line)
{
	(void)npages;
	(void)p2align;
	(void)flag;
	(void)node;
	(void)is_user;
	(void)virt_addr;
	(void)file;
	(void)line;
	return (void *)0;
}
__attribute__((weak)) void x86_pvclock_log_bridge(int event)
{
	if (&cpu_log_count && cpu_log_events) {
		cpu_log_events[cpu_log_count] = event;
		cpu_log_count++;
	}
}
__attribute__((weak)) void arch_init(void) {}
__attribute__((weak)) void arch_ready(void) {}
__attribute__((weak)) void arch_setup_vdso(void) {}
__attribute__((weak)) void cpu_enable_interrupt(void) {}
__attribute__((weak)) void mem_init(void) {}
__attribute__((weak)) void proc_init(void) {}
__attribute__((weak)) int futex_init(void) { return 0; }
__attribute__((weak)) void done_init(void) {}
__attribute__((weak)) void numa_sysfs_setup(void) {}
__attribute__((weak)) int idle_halt;
__attribute__((weak)) int allow_oversubscribe;
__attribute__((weak)) int time_sharing;
__attribute__((weak)) int gettime_local_support;
struct rust_stub_timespec {
	long tv_sec;
	long tv_nsec;
};
__attribute__((weak)) void syscall_gettime_bridge(void *ts)
{
	struct rust_stub_timespec *wts = ts;

	if (wts) {
		wts->tv_sec = 0;
		wts->tv_nsec = 0;
	}
}
__attribute__((weak)) long syscall_policy_do_syscall2_bridge(int syscall_nr,
		unsigned long arg0, unsigned long arg1)
{
	(void)syscall_nr;
	(void)arg0;
	(void)arg1;
	return -38;
}
__attribute__((weak)) void ihk_mc_set_syscall_handler(void *handler)
{
	(void)handler;
}
__attribute__((weak)) void ihk_mc_set_dump_level(unsigned long level)
{
	(void)level;
}
__attribute__((weak)) void ihk_mc_get_boot_time(unsigned long *tv_sec,
		unsigned long *tv_nsec, unsigned long *tsc)
{
	if (tv_sec)
		*tv_sec = 1;
	if (tv_nsec)
		*tv_nsec = 2;
	if (tsc)
		*tsc = 3;
}
__attribute__((weak)) unsigned long ihk_mc_get_ns_per_tsc(void)
{
	return 1000;
}
__attribute__((weak)) int ihk_set_monitor(unsigned long addr,
		unsigned long size)
{
	(void)addr;
	(void)size;
	return 0;
}
__attribute__((weak)) int ihk_set_multi_intr_mode_addr(unsigned long addr)
{
	(void)addr;
	return 0;
}
__attribute__((weak)) int ihk_set_nmi_mode_addr(unsigned long addr)
{
	(void)addr;
	return 0;
}
__attribute__((weak)) void init_delay(void) {}
__attribute__((weak)) void ihk_mc_init_ap(void) {}
__attribute__((weak)) int ihk_mc_get_ikc_cpu(int id)
{
	(void)id;
	return 0;
}
__attribute__((weak)) void init_host_ikc2mckernel(void) {}
__attribute__((weak)) void init_host_ikc2linux(int ikc_cpu)
{
	(void)ikc_cpu;
}
struct rust_stub_ihk_mc_cpu_info {
	int ncpus;
	int *hw_ids;
	int *nodes;
	int *linux_cpu_ids;
	int *ikc_cpus;
};
__attribute__((weak)) struct rust_stub_ihk_mc_cpu_info *ihk_mc_get_cpu_info(void)
{
	return 0;
}
__attribute__((weak)) void ihk_mc_boot_cpu(int cpuid, unsigned long pc)
{
	(void)cpuid;
	(void)pc;
}
__attribute__((weak)) int ihk_mc_get_smp_handler_irq(void)
{
	return 0xf1;
}
__attribute__((weak)) int ihk_mc_interrupt_cpu(int cpu, int vector)
{
	(void)cpu;
	(void)vector;
	return 0;
}
__attribute__((weak)) void x86_issue_ipi_bridge(unsigned long apic_id,
		int vector)
{
	(void)apic_id;
	(void)vector;
}
__attribute__((weak)) void x86_interrupt_log_bridge(int event, int cpu,
		int vector)
{
	(void)event;
	(void)cpu;
	(void)vector;
}
static unsigned char rust_stub_alloc_buf[1048576];
static unsigned long rust_stub_alloc_off;
static void *rust_stub_alloc(int size)
{
	unsigned long need;
	unsigned long start;
	unsigned long i;

	if (size <= 0)
		return 0;
	need = (unsigned long)size;
	start = (rust_stub_alloc_off + 7UL) & ~7UL;
	if (start + need > sizeof(rust_stub_alloc_buf))
		return 0;
	for (i = 0; i < need; ++i)
		rust_stub_alloc_buf[start + i] = 0;
	rust_stub_alloc_off = start + need;
	return rust_stub_alloc_buf + start;
}
__attribute__((weak)) void *ihk_mc_allocate(int size, int flag)
{
	(void)flag;
	return rust_stub_alloc(size);
}
__attribute__((weak)) void ihk_mc_free(void *ptr)
{
	(void)ptr;
}
void *x86_kmalloc_bridge(int size, int flag)
{
	(void)flag;
	return rust_stub_alloc(size);
}
int x86_kmalloc_initialized_bridge(void)
{
	return 1;
}
void x86_kfree_bridge(void *ptr)
{
	(void)ptr;
}
void x86_mem_log_bridge(int event)
{
	(void)event;
}
__attribute__((weak)) int ihk_mc_get_vector(int type)
{
	return type;
}
__attribute__((weak)) int ihk_mc_register_interrupt_handler(int vector,
		void *handler)
{
	(void)vector;
	(void)handler;
	return 0;
}
__attribute__((weak)) int ihk_mc_unregister_interrupt_handler(int vector,
		void *handler)
{
	(void)vector;
	(void)handler;
	return 0;
}
__attribute__((weak)) void arch_print_stack(void) {}
__attribute__((weak)) void arch_cpu_stop(void) {}
__attribute__((weak)) void arch_show_interrupt_context(const void *reg)
{
	(void)reg;
}
__attribute__((weak)) void arch_print_pre_interrupt_stack(
		const struct x86_basic_regs *regs)
{
	(void)regs;
}
__attribute__((weak)) unsigned long x86_kprintf_lock_bridge(void)
{
	return 0;
}
__attribute__((weak)) void x86_kprintf_unlock_bridge(unsigned long flags)
{
	(void)flags;
}
__attribute__((weak)) void x86_context_line_log_bridge(int event,
		unsigned long a, unsigned long b, unsigned long c,
		unsigned long d)
{
	(void)event;
	(void)a;
	(void)b;
	(void)c;
	(void)d;
}
__attribute__((weak)) void x86_stack_frame_log_bridge(unsigned long ip,
		unsigned long sp, unsigned long fp)
{
	(void)ip;
	(void)sp;
	(void)fp;
}
__attribute__((weak)) void x86_print_stack_bridge(void *rbp,
		unsigned long first)
{
	(void)rbp;
	(void)first;
}
__attribute__((weak)) int *x86_cpu_boot_status_slot_bridge(void)
{
	static int status;

	return &status;
}
__attribute__((weak)) void *x86_boot_trampoline_va_bridge(void)
{
	return 0;
}
__attribute__((weak)) const void *x86_boot_trampoline_code_data_bridge(void)
{
	return 0;
}
__attribute__((weak)) unsigned long x86_boot_trampoline_code_size_bridge(void)
{
	return 0;
}
__attribute__((weak)) unsigned long x86_boot_ap_trampoline_bridge(void)
{
	return 0;
}
__attribute__((weak)) void *x86_boot_setup_ap_bridge(void)
{
	return 0;
}
__attribute__((weak)) unsigned long x86_boot_page_table_phys_bridge(void)
{
	return 0;
}
__attribute__((weak)) unsigned long x86_cpu_kstack_bridge(int cpuid)
{
	(void)cpuid;
	return 0;
}
__attribute__((weak)) unsigned long x86_transit_page_table_bridge(void)
{
	return 0;
}
__attribute__((weak)) void x86_wakeup_bridge(int cpuid,
		unsigned long trampoline)
{
	(void)cpuid;
	(void)trampoline;
}
__attribute__((weak)) void x86_cpu_pause_bridge(void) {}
__attribute__((weak)) void *x86_current_thread_bridge(void)
{
	return 0;
}
__attribute__((weak)) const void *x86_trace_enter_user_offsets_bridge(void)
{
	return 0;
}
__attribute__((weak)) void x86_mcexec_v10_trace_log_bridge(int cpu,
		int pid, int tid, unsigned long rip, unsigned long sp,
		unsigned long cs, unsigned long ss, unsigned long rflags,
		int status)
{
	(void)cpu;
	(void)pid;
	(void)tid;
	(void)rip;
	(void)sp;
	(void)cs;
	(void)ss;
	(void)rflags;
	(void)status;
}
__attribute__((weak)) void *x86_this_cpu_local_var_bridge(void)
{
	return 0;
}
__attribute__((weak)) unsigned long x86_runq_lock_offset_bridge(void)
{
	return 0;
}
__attribute__((weak)) unsigned long x86_runq_irqstate_offset_bridge(void)
{
	return 0;
}
__attribute__((weak)) void x86_runq_unlock_bridge(void *lock,
		unsigned long irqstate)
{
	(void)lock;
	(void)irqstate;
}
__attribute__((weak)) long getlong_user(long *dest, const long *src)
{
	if (dest)
		*dest = src ? *src : 0;
	return 0;
}
__attribute__((weak)) int strlen_user(const char *src)
{
	int len = 0;
	if (!src)
		return -14;
	while (src[len])
		len++;
	return len;
}
__attribute__((weak)) int strcpy_from_user(char *dst, const char *src)
{
	char *head = dst;
	if (!dst || !src)
		return -14;
	while ((*dst++ = *src++))
		;
	return (int)(dst - head - 1);
}
int rust_stub_kmalloc_calls;
int rust_stub_kmalloc_size;
int rust_stub_kmalloc_flags;
char *rust_stub_kmalloc_file;
int rust_stub_kmalloc_line;
__attribute__((weak)) void *_kmalloc(int size, int flags, char *file, int line)
{
	rust_stub_kmalloc_calls++;
	rust_stub_kmalloc_size = size;
	rust_stub_kmalloc_flags = flags;
	rust_stub_kmalloc_file = file;
	rust_stub_kmalloc_line = line;
	return __builtin_malloc((unsigned long)size);
}
__attribute__((weak)) void *kmalloc_cache_alloc_bridge(unsigned long size,
		unsigned long flag)
{
	(void)size;
	(void)flag;
	return 0;
}
__attribute__((weak)) void kmalloc_cache_log(int event, void *ptr)
{
	(void)event;
	(void)ptr;
}
__attribute__((weak)) void _kfree(void *ptr, char *file, int line)
{
	(void)file;
	(void)line;
	__builtin_free(ptr);
}
int rust_stub_page_alloc_calls;
int rust_stub_page_alloc_npages[8];
int rust_stub_page_alloc_p2align[8];
unsigned long rust_stub_page_alloc_flags[8];
int rust_stub_page_alloc_node[8];
int rust_stub_page_alloc_is_user[8];
unsigned long rust_stub_page_alloc_virt[8];
void *rust_stub_page_alloc_result[8];
__attribute__((weak)) void *_ihk_mc_alloc_aligned_pages_node(int npages,
		int p2align, unsigned long flag, int node, int is_user,
		unsigned long virt_addr, char *file, int line)
{
	int idx = rust_stub_page_alloc_calls++;
	void *result = __builtin_malloc((unsigned long)npages * 4096UL);

	(void)file;
	(void)line;
	if (idx >= 0 && idx < 8) {
		rust_stub_page_alloc_npages[idx] = npages;
		rust_stub_page_alloc_p2align[idx] = p2align;
		rust_stub_page_alloc_flags[idx] = flag;
		rust_stub_page_alloc_node[idx] = node;
		rust_stub_page_alloc_is_user[idx] = is_user;
		rust_stub_page_alloc_virt[idx] = virt_addr;
		rust_stub_page_alloc_result[idx] = result;
	}
	return result;
}
__attribute__((weak)) void _ihk_mc_free_pages(void *ptr, int npages,
		int is_user, char *file, int line)
{
	(void)npages;
	(void)is_user;
	(void)file;
	(void)line;
	__builtin_free(ptr);
}
struct rust_stub_list_head {
	struct rust_stub_list_head *next;
	struct rust_stub_list_head *prev;
};
struct rust_stub_atomic {
	int counter;
};
struct rust_stub_atomic64 {
	long counter64;
};
__attribute__((weak)) int ihk_atomic_read(const struct rust_stub_atomic *v)
{
	return v->counter;
}
__attribute__((weak)) void ihk_atomic_set(struct rust_stub_atomic *v, int i)
{
	v->counter = i;
}
__attribute__((weak)) void ihk_atomic_add(int i, struct rust_stub_atomic *v)
{
	__sync_add_and_fetch(&v->counter, i);
}
__attribute__((weak)) void ihk_atomic_sub(int i, struct rust_stub_atomic *v)
{
	__sync_sub_and_fetch(&v->counter, i);
}
__attribute__((weak)) void ihk_atomic_inc(struct rust_stub_atomic *v)
{
	__sync_add_and_fetch(&v->counter, 1);
}
__attribute__((weak)) void ihk_atomic_dec(struct rust_stub_atomic *v)
{
	__sync_sub_and_fetch(&v->counter, 1);
}
__attribute__((weak)) int ihk_atomic_dec_and_test(struct rust_stub_atomic *v)
{
	return __sync_sub_and_fetch(&v->counter, 1) == 0;
}
__attribute__((weak)) int ihk_atomic_inc_and_test(struct rust_stub_atomic *v)
{
	return __sync_add_and_fetch(&v->counter, 1) == 0;
}
__attribute__((weak)) int ihk_atomic_add_return(int i,
		struct rust_stub_atomic *v)
{
	return __sync_add_and_fetch(&v->counter, i);
}
__attribute__((weak)) int ihk_atomic_sub_return(int i,
		struct rust_stub_atomic *v)
{
	return __sync_sub_and_fetch(&v->counter, i);
}
__attribute__((weak)) int ihk_atomic_inc_return(struct rust_stub_atomic *v)
{
	return ihk_atomic_add_return(1, v);
}
__attribute__((weak)) int ihk_atomic_dec_return(struct rust_stub_atomic *v)
{
	return ihk_atomic_sub_return(1, v);
}
__attribute__((weak)) long ihk_atomic64_read(
		const struct rust_stub_atomic64 *v)
{
	return v->counter64;
}
__attribute__((weak)) void ihk_atomic64_set(struct rust_stub_atomic64 *v,
		long i)
{
	v->counter64 = i;
}
__attribute__((weak)) void ihk_atomic64_inc(struct rust_stub_atomic64 *v)
{
	__sync_add_and_fetch(&v->counter64, 1);
}
__attribute__((weak)) long ihk_atomic64_add_return(long i,
		struct rust_stub_atomic64 *v)
{
	return __sync_add_and_fetch(&v->counter64, i);
}
__attribute__((weak)) long ihk_atomic64_sub_return(long i,
		struct rust_stub_atomic64 *v)
{
	return __sync_sub_and_fetch(&v->counter64, i);
}
__attribute__((weak)) unsigned long xchg8(unsigned long *ptr,
		unsigned long x)
{
	return __sync_lock_test_and_set(ptr, x);
}
__attribute__((weak)) int xchg4(int *ptr, int x)
{
	return __sync_lock_test_and_set(ptr, x);
}
__attribute__((weak)) unsigned long atomic_xchg_ulong(unsigned long *ptr,
		unsigned long x)
{
	return __sync_lock_test_and_set(ptr, x);
}
__attribute__((weak)) void *atomic_xchg_ptr(void **ptr, void *x)
{
	return __sync_lock_test_and_set(ptr, x);
}
__attribute__((weak)) unsigned long atomic_cmpxchg8(unsigned long *addr,
		unsigned long oldval, unsigned long newval)
{
	return __sync_val_compare_and_swap(addr, oldval, newval);
}
__attribute__((weak)) unsigned long atomic_cmpxchg4(unsigned int *addr,
		unsigned int oldval, unsigned int newval)
{
	return __sync_val_compare_and_swap(addr, oldval, newval);
}
__attribute__((weak)) int atomic_cmpxchg_int(int *addr, int oldval,
		int newval)
{
	return __sync_val_compare_and_swap(addr, oldval, newval);
}
__attribute__((weak)) unsigned long atomic_cmpxchg_ulong(unsigned long *addr,
		unsigned long oldval, unsigned long newval)
{
	return __sync_val_compare_and_swap(addr, oldval, newval);
}
__attribute__((weak)) void *atomic_cmpxchg_ptr(void **addr, void *oldval,
		void *newval)
{
	return __sync_val_compare_and_swap(addr, oldval, newval);
}
__attribute__((weak)) int compare_and_swap(void *addr, unsigned long olddata,
		unsigned long newdata)
{
	return __sync_bool_compare_and_swap((unsigned long *)addr, olddata,
			newdata);
}
__attribute__((weak)) void ihk_atomic_add_long(long i, long *v)
{
	__sync_add_and_fetch(v, i);
}
__attribute__((weak)) void ihk_atomic_add_ulong(long i, unsigned long *v)
{
	__sync_add_and_fetch(v, i);
}
__attribute__((weak)) unsigned long ihk_atomic_add_long_return(long i,
		long *v)
{
	return __sync_add_and_fetch(v, i);
}
struct rust_stub_page {
	struct rust_stub_list_head list;
	struct rust_stub_list_head hash;
	unsigned char mode;
	unsigned long phys;
	struct rust_stub_atomic count;
	struct rust_stub_atomic64 mapped;
	long offset;
	int pgshift;
};
struct rust_stub_user_context;
struct rust_stub_rusage_global {
	long memory_stat_rss[8];
	long memory_stat_mapped_file[8];
};
struct rust_stub_shm_info {
	int used_ids;
	char padding[4];
	unsigned long shm_tot;
	unsigned long shm_rss;
	unsigned long shm_swp;
	unsigned long swap_attempts;
	unsigned long swap_successes;
};
__attribute__((weak)) struct rust_stub_page *phys_to_page_insert_hash(
		unsigned long phys)
{
	static struct rust_stub_page page;
	page.phys = phys;
	return &page;
}
__attribute__((weak)) struct rust_stub_page *phys_to_page(unsigned long phys)
{
	static struct rust_stub_page page;
	page.phys = phys;
	return &page;
}
__attribute__((weak)) int ihk_mc_pt_virt_to_phys(void *pt, void *virt,
		unsigned long *phys)
{
	(void)pt;
	if (phys)
		*phys = (unsigned long)virt;
	return 0;
}
__attribute__((weak)) unsigned long ihk_mc_pt_virt_to_pagemap(void *pt,
		unsigned long addr)
{
	(void)pt;
	return addr >> 12;
}
__attribute__((weak)) int ihk_mc_pt_virt_to_phys_size(void *pt, void *virt,
		unsigned long *phys, unsigned long *psize)
{
	(void)pt;
	if (phys)
		*phys = (unsigned long)virt;
	if (psize)
		*psize = 4096;
	return 0;
}
__attribute__((weak)) int ihk_mc_pt_free_range(void *pt, void *vm,
		void *start, void *end, void *opt)
{
	(void)pt;
	(void)vm;
	(void)start;
	(void)end;
	(void)opt;
	return 0;
}
__attribute__((weak)) int page_fault_process_vm(void *vm, void *addr,
		unsigned long reason)
{
	(void)vm;
	(void)addr;
	(void)reason;
	return 0;
}
__attribute__((weak)) void *lookup_process_memory_range(void *vm,
		unsigned long start, unsigned long end)
{
	(void)vm;
	(void)start;
	(void)end;
	return 0;
}
__attribute__((weak)) void *next_process_memory_range(void *vm, void *range)
{
	(void)vm;
	(void)range;
	return 0;
}
__attribute__((weak)) void *find_process(int pid, void *lock)
{
	(void)pid;
	(void)lock;
	return 0;
}
__attribute__((weak)) void process_unlock(void *proc, void *lock)
{
	(void)proc;
	(void)lock;
}
__attribute__((weak)) int hold_thread(void *thread)
{
	(void)thread;
	return 0;
}
__attribute__((weak)) void hold_process(void *proc)
{
	(void)proc;
}
__attribute__((weak)) void hold_process_vm(void *vm)
{
	(void)vm;
}
__attribute__((weak)) void release_thread(void *thread)
{
	(void)thread;
}
__attribute__((weak)) void release_process(void *proc)
{
	(void)proc;
}
__attribute__((weak)) void release_process_vm(void *vm)
{
	(void)vm;
}
__attribute__((weak)) void send_procfs_answer(void *packet, int err)
{
	(void)packet;
	(void)err;
}
__attribute__((weak)) int do_process_vm_read_writev(int pid,
		const void *local_iov, unsigned long liovcnt,
		const void *remote_iov, unsigned long riovcnt,
		unsigned long flags, int op)
{
	(void)local_iov;
	(void)remote_iov;
	return pid + (int)liovcnt + (int)riovcnt + (int)flags + op;
}
__attribute__((weak)) long sys_mlock(int n, struct rust_stub_user_context *ctx)
{
	(void)n;
	(void)ctx;
	return 0;
}
__attribute__((weak)) long sys_munlock(int n, struct rust_stub_user_context *ctx)
{
	(void)n;
	(void)ctx;
	return 0;
}
__attribute__((weak)) int page_unmap(struct rust_stub_page *page)
{
	(void)page;
	return 1;
}
__attribute__((weak)) struct rust_stub_rusage_global rusage;
__attribute__((weak)) struct rust_stub_shm_info the_shm_info;
__attribute__((weak)) void *ihk_mc_pt_lookup_pte(void *pt, void *virt,
		int pgshift, void **pgbasep, unsigned long *pgsizep,
		int *p2alignp)
{
	static unsigned long pte;
	(void)pt;
	(void)virt;
	(void)pgshift;
	if (pgbasep)
		*pgbasep = 0;
	if (pgsizep)
		*pgsizep = 4096;
	if (p2alignp)
		*p2alignp = 0;
	return &pte;
}
struct rust_stub_basic_regs {
	unsigned long r15, r14, r13, r12, rbp, rbx, r11, r10, r9, r8;
	unsigned long rax, rcx, rdx, rsi, rdi, orig_rax, rip, cs, rflags, rsp, ss;
};
struct rust_stub_sregs {
	unsigned long fs_base, gs_base, ds, es, fs, gs;
};
struct rust_stub_user_context {
	struct rust_stub_sregs sr;
	unsigned char flags[8];
	struct rust_stub_basic_regs gpr;
};
struct rust_stub_pager_map_result {
	unsigned long handle;
	int maxprot;
	char padding[4];
	char path[4096];
};
struct rust_stub_syscall_request {
	int rtid;
	int ttid;
	unsigned long valid;
	unsigned long number;
	unsigned long args[6];
};
__attribute__((weak)) long do_syscall(struct rust_stub_syscall_request *req,
		int cpu)
{
	(void)cpu;
	if (!req)
		return -22;
	if (req->args[0] == 5) {
		struct rust_stub_pager_map_result *result =
			(struct rust_stub_pager_map_result *)req->args[4];
		if (result) {
			result->handle = 0x12345000UL;
			result->maxprot = (int)req->args[5];
			result->path[0] = 0;
		}
	}
	else if (req->args[0] == 6) {
		unsigned long *pfn = (unsigned long *)req->args[3];
		if (pfn)
			*pfn = (1UL << 63) | 1UL | 0x2000UL;
	}
	return 0;
}
__attribute__((weak)) long syscall_generic_forwarding(int n,
		struct rust_stub_user_context *ctx)
{
	(void)n;
	if (!ctx)
		return -22;
	if (ctx->gpr.rdi == 5) {
		struct rust_stub_pager_map_result *result =
			(struct rust_stub_pager_map_result *)ctx->gpr.r8;
		if (result) {
			result->handle = 0x12345000UL;
			result->maxprot = (int)ctx->gpr.r9;
			result->path[0] = 0;
		}
	}
	else if (ctx->gpr.rdi == 6) {
		unsigned long *pfn = (unsigned long *)ctx->gpr.r10;
		if (pfn)
			*pfn = (1UL << 63) | 1UL | 0x2000UL;
	}
	return 0;
}
__attribute__((weak)) unsigned long ihk_mc_map_memory(void *os,
		unsigned long phys, unsigned long size)
{
	(void)os;
	(void)size;
	return phys;
}
static unsigned char rust_stub_map_virtual_arena[4 * 1024 * 1024];
__attribute__((weak)) void *mem_pending_free_pages_bridge(void)
{
	static unsigned long pending_free_pages[2];

	return pending_free_pages;
}
__attribute__((weak)) void mem_begin_free_pages_pending_panic_bridge(void) {}
__attribute__((weak)) void mem_pending_free_bridge(unsigned long phys,
		int npages, int is_user)
{
	(void)phys;
	(void)npages;
	(void)is_user;
}
__attribute__((weak)) void mem_finish_free_pages_pending_panic_bridge(void) {}
__attribute__((weak)) void *mem_vmap_allocator_bridge(void)
{
	return rust_stub_map_virtual_arena;
}
__attribute__((weak)) unsigned long mem_vmap_alloc_bridge(void *desc,
		int npages, int p2align)
{
	(void)desc;
	(void)npages;
	(void)p2align;
	return (unsigned long)rust_stub_map_virtual_arena;
}
__attribute__((weak)) void mem_vmap_free_bridge(void *desc,
		unsigned long address, int npages)
{
	(void)desc;
	(void)address;
	(void)npages;
}
__attribute__((weak)) int mem_pt_set_page_bridge(void *pt, void *virt,
		unsigned long phys, unsigned long attr)
{
	(void)pt;
	(void)virt;
	(void)phys;
	(void)attr;
	return 0;
}
__attribute__((weak)) int mem_pt_clear_page_bridge(void *pt, void *virt)
{
	(void)pt;
	(void)virt;
	return 0;
}
__attribute__((weak)) void mem_flush_tlb_single_bridge(unsigned long addr)
{
	(void)addr;
}
__attribute__((weak)) void mem_barrier_bridge(void) {}
__attribute__((weak)) void *ihk_mc_map_virtual(unsigned long phys,
		unsigned long size, unsigned long attr)
{
	(void)phys;
	(void)size;
	(void)attr;
	return rust_stub_map_virtual_arena;
}
__attribute__((weak)) void ihk_mc_unmap_virtual(void *virt,
		unsigned long size)
{
	(void)virt;
	(void)size;
}
__attribute__((weak)) void ihk_mc_unmap_memory(void *os, unsigned long phys,
		unsigned long size)
{
	(void)os;
	(void)phys;
	(void)size;
}
__attribute__((weak)) int ihk_mc_get_nr_memory_chunks(void) { return 1; }
__attribute__((weak)) int ihk_mc_get_memory_chunk(int id, unsigned long *start,
		unsigned long *end, int *numa_id)
{
	(void)id;
	if (start)
		*start = 0;
	if (end)
		*end = ~0UL;
	if (numa_id)
		*numa_id = 0;
	return 0;
}
__attribute__((weak)) char *ihk_get_kargs(void) { return 0; }
struct cpu_local_var;
__attribute__((weak)) struct cpu_local_var *clv;
__attribute__((weak)) int cpu_local_var_initialized;
__attribute__((weak)) struct cpu_local_var *get_this_cpu_local_var(void)
{
	return clv;
}
__attribute__((weak)) int ihk_mc_get_processor_id(void) { return 0; }
__attribute__((weak)) int ihk_mc_get_osnum(void) { return 0; }
__attribute__((weak)) void *monitor;
__attribute__((weak)) int multi_intr_mode;
__attribute__((weak)) void __freeze(void) {}
__attribute__((weak)) void mod_nmi_ctx(void *ctx, void (*handler)(void))
{
	(void)ctx;
	(void)handler;
}
__attribute__((weak)) void *early_alloc_pages(int nr_pages)
{
	(void)nr_pages;
	return 0;
}
__attribute__((weak)) void early_alloc_invalidate(void) {}
static void *rust_stub_early_last_page;
void **x86_early_alloc_last_page_slot_bridge(void)
{
	return &rust_stub_early_last_page;
}
unsigned long x86_early_alloc_end_bridge(void)
{
	return 0x100000UL;
}
unsigned long x86_bootstrap_mem_end_bridge(void)
{
	return 0x200000UL;
}
unsigned long x86_arch_mem_virt_to_phys_bridge(void *addr)
{
	return (unsigned long)addr;
}
void *x86_rust_stub_init_pt_override;
void *(*x86_rust_stub_phys_to_virt_override)(unsigned long);
void *x86_arch_mem_phys_to_virt_bridge(unsigned long phys)
{
	if (x86_rust_stub_phys_to_virt_override)
		return x86_rust_stub_phys_to_virt_override(phys);
	return (void *)phys;
}
void x86_early_alloc_panic_bridge(int reason)
{
	(void)reason;
}
__attribute__((weak)) void x86_early_alloc_invalidate_bridge(void) {}
static unsigned char rust_stub_init_pt_pages[2][4096];
static void *rust_stub_init_pt;
static void *rust_stub_boot_pt;
static int rust_stub_init_loaded;
static int rust_stub_init_lock;
static int rust_stub_init_alloc_calls;
static unsigned char rust_stub_map_fixed_pt[4096];
static unsigned long rust_stub_map_fixed_virt = 0x10000000UL;
static unsigned char rust_stub_vsyscall_page[4096];
void **x86_init_page_table_init_pt_slot_bridge(void)
{
	return &rust_stub_init_pt;
}
void *x86_page_table_init_pt_bridge(void)
{
	return x86_rust_stub_init_pt_override ?
		x86_rust_stub_init_pt_override : rust_stub_init_pt;
}
void **x86_init_page_table_boot_pt_slot_bridge(void)
{
	return &rust_stub_boot_pt;
}
void *x86_page_table_boot_pt_bridge(void)
{
	return rust_stub_boot_pt;
}
int *x86_init_page_table_loaded_slot_bridge(void)
{
	return &rust_stub_init_loaded;
}
void *x86_init_page_table_lock_bridge(void)
{
	return &rust_stub_init_lock;
}
unsigned long x86_init_page_table_size_bridge(void)
{
	return 4096;
}
void x86_check_available_page_size_bridge(int event)
{
	(void)event;
}
void *x86_init_page_table_alloc_bridge(int nr_pages, int flag)
{
	int index = rust_stub_init_alloc_calls % 2;
	(void)flag;
	rust_stub_init_alloc_calls++;
	if (nr_pages != 1)
		return 0;
	return rust_stub_init_pt_pages[index];
}
void x86_init_page_table_spin_init_bridge(void *lock)
{
	(void)lock;
}
void x86_init_page_table_normal_bridge(void *pt)
{
	((unsigned char *)pt)[0] = 0x11;
}
void x86_init_page_table_linux_bridge(void *pt)
{
	((unsigned char *)pt)[1] = 0x22;
}
void x86_init_page_table_fixed_bridge(void *pt)
{
	((unsigned char *)pt)[2] = 0x33;
}
void x86_init_page_table_text_bridge(void *pt)
{
	((unsigned char *)pt)[3] = 0x44;
}
void x86_init_page_table_vsyscall_bridge(void *pt)
{
	((unsigned char *)pt)[4] = 0x55;
}
void x86_init_page_table_low_bridge(void *pt)
{
	((unsigned char *)pt)[7] ^= 0x7f;
}
void x86_init_page_table_load_bridge(void *pt)
{
	(void)pt;
}
void x86_init_page_table_log_bridge(int event, void *pt)
{
	(void)event;
	(void)pt;
}
void x86_init_page_table_panic_bridge(int reason)
{
	(void)reason;
}
unsigned long x86_init_normal_get_memory_address_bridge(int type, int arg)
{
	(void)arg;
	return type ? 0x400000UL : 0x200000UL;
}
void x86_init_normal_log_bridge(int event, unsigned long a,
		unsigned long b, unsigned long c)
{
	(void)event;
	(void)a;
	(void)b;
	(void)c;
}
void x86_init_normal_panic_bridge(void)
{
}
char *x86_init_linux_find_command_line_bridge(char *name)
{
	(void)name;
	return 0;
}
int x86_init_linux_get_nr_memory_chunks_bridge(void)
{
	return 0;
}
int x86_init_linux_get_memory_chunk_bridge(int id, unsigned long *start,
		unsigned long *end, int *numa_id)
{
	(void)id;
	(void)start;
	(void)end;
	(void)numa_id;
	return -1;
}
void x86_init_linux_log_bridge(int event, unsigned long a,
		unsigned long b, unsigned long c, unsigned long d, int error)
{
	(void)event;
	(void)a;
	(void)b;
	(void)c;
	(void)d;
	(void)error;
}
void x86_init_linux_panic_bridge(void)
{
}
void x86_init_text_log_bridge(int event, unsigned long a,
		unsigned long b, unsigned long c)
{
	(void)event;
	(void)a;
	(void)b;
	(void)c;
}
const unsigned long x86_map_kernel_start_geometry = 0xfffffe0000000000UL;
void x86_init_text_panic_bridge(void)
{
}
void x86_init_low_panic_bridge(void)
{
}
void x86_init_fixed_panic_bridge(void)
{
}
void *x86_init_vsyscall_page_bridge(void)
{
	return rust_stub_vsyscall_page;
}
void x86_init_vsyscall_panic_bridge(void)
{
}
void *x86_map_fixed_area_init_pt_bridge(void)
{
	return rust_stub_map_fixed_pt;
}
unsigned long *x86_map_fixed_area_fixed_virt_slot_bridge(void)
{
	return &rust_stub_map_fixed_virt;
}
void x86_map_fixed_area_log_bridge(unsigned long phys,
		unsigned long size, unsigned long virt)
{
	(void)phys;
	(void)size;
	(void)virt;
}
unsigned long x86_pt_virt_to_phys_bridge(void *addr)
{
	return (unsigned long)addr;
}
void *(*x86_rust_stub_pt_phys_to_virt_override)(unsigned long);
void *x86_pt_phys_to_virt_bridge(unsigned long phys)
{
	if (x86_rust_stub_pt_phys_to_virt_override)
		return x86_rust_stub_pt_phys_to_virt_override(phys);
	return (void *)phys;
}
int x86_rust_stub_pt_print_log_count;
int x86_rust_stub_pt_print_last_event;
int x86_rust_stub_pt_print_last_level;
void x86_pt_print_log_bridge(int event, int level,
		unsigned long value, int index)
{
	(void)value;
	(void)index;
	x86_rust_stub_pt_print_log_count++;
	x86_rust_stub_pt_print_last_event = event;
	x86_rust_stub_pt_print_last_level = level;
}
int x86_rust_stub_pt_set_page_calls;
int x86_rust_stub_pt_set_page_rc;
void *x86_rust_stub_pt_set_page_pt;
unsigned long x86_rust_stub_pt_set_page_virt;
unsigned long x86_rust_stub_pt_set_page_phys;
unsigned long x86_rust_stub_pt_set_page_attr;
int x86_pt_set_page_bridge(void *pt, unsigned long virt,
		unsigned long phys, unsigned long attr)
{
	x86_rust_stub_pt_set_page_calls++;
	x86_rust_stub_pt_set_page_pt = pt;
	x86_rust_stub_pt_set_page_virt = virt;
	x86_rust_stub_pt_set_page_phys = phys;
	x86_rust_stub_pt_set_page_attr = attr;
	return x86_rust_stub_pt_set_page_rc;
}
void x86_move_flush_tlb_bridge(void)
{
}
__attribute__((weak)) void pagealloc_track_init(void) {}
struct ihk_mc_numa_node;
__attribute__((weak)) int ihk_mc_get_nr_numa_nodes(void) { return 0; }
__attribute__((weak)) struct ihk_mc_numa_node *
ihk_mc_get_numa_node_by_distance(int i)
{
	(void)i;
	return 0;
}
__attribute__((weak)) void ihk_numa_zero_free_pages(
		struct ihk_mc_numa_node *node)
{
	(void)node;
}
__attribute__((weak)) unsigned long ihk_mc_get_extra_reg_event(int id)
{
	return (unsigned long)(0x100 + id);
}
__attribute__((weak)) void calculate_time_from_tsc(void *ts)
{
	long *words = (long *)ts;
	if (words) {
		words[0] = 1;
		words[1] = 2000;
	}
}
struct waitq_entry;
__attribute__((weak)) int default_wake_function(struct waitq_entry *entry,
		unsigned mode, int flags, void *key)
{
	(void)entry;
	(void)mode;
	(void)flags;
	(void)key;
	return 0;
}
struct thread;
__attribute__((weak)) int sched_wakeup_thread(struct thread *thread, int state)
{
	return ((unsigned long)thread ^ (unsigned int)state) & 0x7fffffff;
}
__attribute__((weak)) int sched_wakeup_thread_locked(struct thread *thread,
		int state)
{
	return (((unsigned long)thread << 1) ^ (unsigned int)state) & 0x7fffffff;
}
__attribute__((weak)) int ihk_mc_get_interrupt_id(int cpu)
{
	return cpu + 0x40;
}
/* spin_sleep_or_schedule is supplied by the actual Rust scheduler object. */
struct sig_pending;
__attribute__((weak)) struct sig_pending *hassigpending(struct thread *thread)
{
	(void)thread;
	return 0;
}
__attribute__((weak)) int futex_atomic_access_ok_bridge(int *uaddr,
		unsigned long size)
{
	(void)size;
	return uaddr != 0;
}
__attribute__((weak)) int futex_atomic_cmpxchg_inatomic_bridge(int *uaddr,
		int oldval, int newval)
{
	int current;

	if (!uaddr)
		return -14;
	current = *uaddr;
	if (current == oldval)
		*uaddr = newval;
	return current;
}
__attribute__((weak)) int futex_atomic_op_inuser_bridge(int op, int *uaddr,
		int oparg, int *oldval)
{
	int old;

	if (!uaddr)
		return -14;
	old = *uaddr;
	switch (op) {
	case 0:
		*uaddr = oparg;
		break;
	case 1:
		*uaddr = old + oparg;
		break;
	case 2:
		*uaddr = old | oparg;
		break;
	case 3:
		*uaddr = old & oparg;
		break;
	case 4:
		*uaddr = old ^ oparg;
		break;
	default:
		return -38;
	}
	*oldval = old;
	return 0;
}
static void *rust_stub_ikc2linux_entries[8];
__attribute__((weak)) void **ikc2linuxs = rust_stub_ikc2linux_entries;
__attribute__((weak)) void check_sig_pending(void) {}
__attribute__((weak)) long syscall_dispatch_context_bridge(int num, void *ctx)
{
	(void)num;
	(void)ctx;
	return -38;
}
__attribute__((weak)) void syscall_offload_wait_reply(void *req, void *res,
		int cpu, void *thread)
{
	(void)req;
	(void)res;
	(void)cpu;
	(void)thread;
}
__attribute__((weak)) void schedule(void) {}
unsigned long shmid_index[512];
__attribute__((weak)) unsigned long attr_mask =
	0x01UL | 0x02UL | 0x04UL | 0x40UL | (1UL << 11) |
	0x8000000000000000UL;
__attribute__((weak)) unsigned long x86_attr_mask_bridge(void)
{
	return attr_mask;
}
__attribute__((weak)) int zero_at_free = 1;
__attribute__((weak)) char *syscall_name[2048];
__attribute__((weak)) void xpmem_id_wrapper_bug_on(int condition)
{
	(void)condition;
}
__attribute__((weak)) void xpmem_tg_hashtable_index_log(int tgid, int index)
{
	(void)tgid;
	(void)index;
}
__attribute__((weak)) void xpmem_ap_hashtable_index_log(long apid, int index)
{
	(void)apid;
	(void)index;
}
__attribute__((weak)) void *xpmem_my_part;
struct rust_stub_xpmem_partition_offsets {
	unsigned long part_size;
	unsigned long part_n_opened_offset;
	unsigned long part_tg_hashtable_offset;
	unsigned long hashlist_stride;
	unsigned long hashlist_lock_offset;
	unsigned long hashlist_list_offset;
};
struct rust_stub_xpmem_tg_lookup_offsets {
	unsigned long part_tg_hashtable_offset;
	unsigned long hashlist_stride;
	unsigned long hashlist_list_offset;
	unsigned long tg_tgid_offset;
	unsigned long tg_flags_offset;
	unsigned long tg_hashlist_offset;
};
__attribute__((weak)) struct rust_stub_xpmem_partition_offsets
	xpmem_partition_offsets;
__attribute__((weak)) struct rust_stub_xpmem_tg_lookup_offsets
	xpmem_tg_lookup_offsets;
__attribute__((weak)) unsigned long xpmem_vm_range_private_data_offset;
__attribute__((weak)) void xpmem_tg_ref_lookup_log(int event, int tgid,
		int return_destroying, void *part, void *result)
{
	(void)event;
	(void)tgid;
	(void)return_destroying;
	(void)part;
	(void)result;
}
__attribute__((weak)) void xpmem_rwlock_reader_lock_bridge(void *lock,
		void *node)
{
	(void)lock;
	(void)node;
}
__attribute__((weak)) void xpmem_rwlock_reader_unlock_bridge(void *lock,
		void *node)
{
	(void)lock;
	(void)node;
}
__attribute__((weak)) void xpmem_tg_ref_bridge(void *tg)
{
	(void)tg;
}
__attribute__((weak)) void xpmem_destroyable_log(int event)
{
	(void)event;
}
__attribute__((weak)) void xpmem_tg_deref_bridge(void *tg)
{
	(void)tg;
}
__attribute__((weak)) void xpmem_seg_deref_bridge(void *seg)
{
	(void)seg;
}
__attribute__((weak)) void xpmem_ap_deref_bridge(void *ap)
{
	(void)ap;
}
__attribute__((weak)) void xpmem_att_deref_bridge(void *att)
{
	(void)att;
}
__attribute__((weak)) void *xpmem_refcnt_ptr_bridge(void *object, int kind)
{
	(void)kind;
	return object;
}
__attribute__((weak)) void xpmem_refcnt_log(int kind, int value)
{
	(void)kind;
	(void)value;
}
__attribute__((weak)) void xpmem_atomic_set_bridge(void *counter, int value)
{
	if (counter)
		*(int *)counter = value;
}
__attribute__((weak)) int xpmem_atomic_read_bridge(void *counter)
{
	return counter ? *(int *)counter : 0;
}
__attribute__((weak)) int xpmem_atomic_inc_bridge(void *counter)
{
	if (counter)
		return ++*(int *)counter;
	return 0;
}
__attribute__((weak)) void xpmem_bug_on_bridge(int condition)
{
	(void)condition;
}
