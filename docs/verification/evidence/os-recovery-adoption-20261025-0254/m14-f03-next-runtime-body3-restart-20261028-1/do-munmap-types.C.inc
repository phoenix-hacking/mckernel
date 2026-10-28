typedef void (*do_munmap_void_fn_t)(void);
typedef int (*do_munmap_remove_range_fn_t)(void *vm, unsigned long start,
		unsigned long end, int *ro_freedp);
typedef long (*do_munmap_clear_host_fn_t)(unsigned long addr, size_t len,
		int holding_lock);
typedef void (*do_munmap_log_fn_t)(unsigned long addr, size_t len,
		int error);
typedef int (*mprotect_set_host_vma_fn_t)(unsigned long start,
		size_t len, int prot, int holding_lock);
