#define IHK_MAX_NUM_NUMA_NODES 1024
#define IHK_MAX_NUM_CPUS 1024

enum ihk_os_pgsize {
	IHK_OS_PGSIZE_4KB,
	IHK_OS_PGSIZE_64KB,
	IHK_OS_PGSIZE_2MB,
	IHK_OS_PGSIZE_32MB,
	IHK_OS_PGSIZE_1GB,
	IHK_OS_PGSIZE_16GB,
	IHK_OS_PGSIZE_512MB,
	IHK_OS_PGSIZE_4TB,
	IHK_MAX_NUM_PGSIZES
};
struct rusage_percpu {
	unsigned long user_tsc;
	unsigned long system_tsc;
};
struct rusage_global {
	/* Memory usage accounting */
	long memory_stat_rss[IHK_MAX_NUM_PGSIZES];
	long memory_stat_mapped_file[IHK_MAX_NUM_PGSIZES];
	long rss_current; /* anon && user, used only for memory_max_usage */
	unsigned long memory_max_usage;
	unsigned long max_num_threads;
	unsigned long num_threads;
	unsigned long memory_kmem_usage;
	unsigned long memory_kmem_max_usage;
	unsigned long memory_numa_stat[IHK_MAX_NUM_NUMA_NODES];

	/* CPU usage accounting */
	struct rusage_percpu cpu[IHK_MAX_NUM_CPUS]; /* clv[i].monitor = &cpu[i] */

	/* OOM monitoring */
	unsigned long total_memory;
	unsigned long total_memory_usage;
	unsigned long total_memory_max_usage;
#ifdef RUSAGE_DEBUG
	unsigned long total_memory_max_usage_old; /* debug */
#endif
	/* Used for translating results into struct ihk_os_rusage */
	unsigned long num_numa_nodes;
	unsigned long num_processors;
	unsigned long ns_per_tsc;
};

struct page;
typedef void *page_table_t;
typedef struct {
	int counter;
} ihk_atomic_t;
struct memobj {
	struct memobj_ops *ops;
	uint32_t flags;
	uint32_t status;
	size_t size;
	ihk_atomic_t refcnt;

	/* For pre-mapped memobjects */
	void **pages;
	int nr_pages;
	char *path;
};

typedef void memobj_free_func_t(struct memobj *obj);
typedef int memobj_get_page_func_t(struct memobj *obj, off_t off, int p2align, uintptr_t *physp, unsigned long *flag, uintptr_t virt_addr);
typedef uintptr_t memobj_copy_page_func_t(struct memobj *obj, uintptr_t orgphys, int p2align);
typedef int memobj_flush_page_func_t(struct memobj *obj, uintptr_t phys, size_t pgsize);
typedef int memobj_invalidate_page_func_t(struct memobj *obj, uintptr_t phys, size_t pgsize);
typedef int memobj_lookup_page_func_t(struct memobj *obj, off_t off, int p2align, uintptr_t *physp, unsigned long *flag);
typedef int memobj_update_page_func_t(struct memobj *obj, page_table_t pt,
		struct page *orig_page, void *vaddr);

struct memobj_ops {
	memobj_free_func_t *free;
	memobj_get_page_func_t *get_page;
	memobj_copy_page_func_t *copy_page;
	memobj_flush_page_func_t *flush_page;
	memobj_invalidate_page_func_t *invalidate_page;
	memobj_lookup_page_func_t *lookup_page;
	memobj_update_page_func_t *update_page;
};
