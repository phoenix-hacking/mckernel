typedef void (*x86_pt_free_pages_fn_t)(void *addr, int nr_pages);
/* Exact selected production header typedefs and full level signature. */
typedef void (*x86_clear_remote_flush_fn_t)(void *vm,
					   unsigned long *addrs,
					   int nr_addr, int cpu_id);
typedef void (*x86_clear_flush_memobj_fn_t)(void *memobj,
					    unsigned long phys,
					    size_t pgsize);
typedef void *(*x86_clear_phys_to_virt_fn_t)(unsigned long phys);
typedef void (*x86_clear_free_pages_fn_t)(void *addr, int nr_pages);
typedef int (*x86_clear_page_unmap_fn_t)(void *page);
typedef void (*x86_clear_rss_sub_fn_t)(size_t size, size_t pgsize);
typedef void (*x86_clear_memobj_rss_sub_fn_t)(void *memobj, size_t size,
					      size_t pgsize);
typedef void (*x86_clear_effect_log_fn_t)(int event, unsigned long base,
					  unsigned long phys, size_t pgsize);
typedef void (*x86_clear_range_top_log_fn_t)(int event, void *pt,
					     unsigned long start,
					     unsigned long end,
					     int free_physical);
typedef int (*x86_clear_old_action_fn_t)(void *args, unsigned long old,
					 size_t pgsize,
					 unsigned long *physp,
					 void **pagep,
					 int *fileoffp);
typedef int (*x86_clear_child_walk_fn_t)(void *pt, unsigned long base,
					 unsigned long start,
					 unsigned long end, void *args);
typedef void (*x86_clear_range_log_fn_t)(int event, void *args,
					 unsigned long *ptep,
					 unsigned long base,
					 unsigned long start,
					 unsigned long end, int error,
					 int level_shift,
					 unsigned long phys);
int x86_clear_range_level_body_result(void *args, unsigned long *ptep,
				      unsigned long base,
				      unsigned long start,
				      unsigned long end,
				      int level_shift,
				      unsigned long level_size,
				      unsigned long size_flag,
				      int child_teardown_enabled,
				      void *vm,
				      unsigned long *addr_array,
				      int *nr_addrp, int max_nr_addr,
				      int cpu_id, int free_physical,
				      void *memobj,
				      x86_clear_old_action_fn_t old_action_fn,
				      x86_clear_phys_to_virt_fn_t phys_to_virt_fn,
				      x86_clear_child_walk_fn_t child_walk_fn,
				      x86_clear_remote_flush_fn_t flush_fn,
				      x86_pt_free_pages_fn_t pt_free_pages_fn,
				      x86_clear_flush_memobj_fn_t flush_memobj_fn,
				      x86_clear_free_pages_fn_t free_pages_fn,
				      x86_clear_page_unmap_fn_t page_unmap_fn,
				      x86_clear_rss_sub_fn_t rss_sub_fn,
				      x86_clear_memobj_rss_sub_fn_t memobj_rss_sub_fn,
				      x86_clear_range_log_fn_t range_log_fn,
				      x86_clear_effect_log_fn_t effect_log_fn);
