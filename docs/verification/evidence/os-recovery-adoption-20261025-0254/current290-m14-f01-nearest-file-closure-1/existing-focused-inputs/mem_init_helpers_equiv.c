#include <stddef.h>
#include <stdint.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/types.h>
#include <sys/types.h>
#include <unistd.h>
#include <unistd.h>
#include <unistd.h>
#include <stdint.h>

extern int is_mckernel_memory(unsigned long, unsigned long);
extern int phys_to_nid(unsigned long);
extern char *find_command_line(char *);
extern unsigned long round_up(unsigned long, unsigned long);
extern unsigned long round_down(unsigned long, unsigned long);
extern uint64_t hash_64(uint64_t, unsigned int);
extern uint32_t hash_32(uint32_t, unsigned int);
extern unsigned long hash_long(unsigned long, unsigned int);
extern unsigned long hash_ptr(void *, unsigned int);

struct list_head {
	struct list_head *next;
	struct list_head *prev;
};

struct rb_node {
	unsigned long __rb_parent_color;
	struct rb_node *rb_right;
	struct rb_node *rb_left;
} __attribute__((aligned(sizeof(long))));

struct rb_root {
	struct rb_node *rb_node;
};

struct llist_node {
	struct llist_node *next;
};

struct llist_head {
	struct llist_node *first;
};

struct mcs_lock_node {
	unsigned long locked;
	struct mcs_lock_node *next;
	unsigned long irqsave;
} __attribute__((aligned(64)));

struct node_distance {
	int id;
	int distance;
};

struct fake_numa_node {
	int id;
	int linux_numa_id;
	int type;
	int pad0;
	struct list_head allocators;
	struct node_distance *nodes_by_distance;
	int zeroing_workers;
	int nr_to_zero_pages;
	struct llist_head zeroed_list;
	struct llist_head to_zero_list;
	struct rb_root free_chunks;
	struct mcs_lock_node lock;
	unsigned long nr_pages;
	unsigned long nr_free_pages;
	unsigned long min_addr;
	unsigned long max_addr;
} __attribute__((aligned(64)));

struct fake_rb_free_chunk {
	unsigned long addr;
	unsigned long size;
	struct rb_node node;
	struct llist_node list;
};

struct ihk_dump_page {
	unsigned long start;
	unsigned long map_count;
	unsigned long map[0];
};

struct ihk_dump_page_set {
	volatile unsigned int completion_flag;
	unsigned int count;
	unsigned long page_size;
	unsigned long phy_page;
};

struct dump_pase_info {
	struct ihk_dump_page_set *dump_page_set;
	struct ihk_dump_page *dump_pages;
};

struct fake_address_space {
	void *page_table;
};

struct fake_process_vm {
	struct fake_address_space *address_space;
};

struct fake_process {
	struct list_head hash_list;
	struct fake_process_vm *vm;
	int tag;
};

#define IHK_MAX_NUM_PGSIZES 8
#define IHK_MAX_NUM_NUMA_NODES 1024
#define IHK_MAX_NUM_CPUS 1024

struct rusage_percpu {
	unsigned long user_tsc;
	unsigned long system_tsc;
};

struct rusage_global {
	long memory_stat_rss[IHK_MAX_NUM_PGSIZES];
	long memory_stat_mapped_file[IHK_MAX_NUM_PGSIZES];
	long rss_current;
	unsigned long memory_max_usage;
	unsigned long max_num_threads;
	unsigned long num_threads;
	unsigned long memory_kmem_usage;
	unsigned long memory_kmem_max_usage;
	unsigned long memory_numa_stat[IHK_MAX_NUM_NUMA_NODES];
	struct rusage_percpu cpu[IHK_MAX_NUM_CPUS];
	unsigned long total_memory;
	unsigned long total_memory_usage;
	unsigned long total_memory_max_usage;
	unsigned long num_numa_nodes;
	unsigned long num_processors;
	unsigned long ns_per_tsc;
};

struct ihk_mc_cpu_info {
	int ncpus;
	int *hw_ids;
	int *nodes;
	int *linux_cpu_ids;
	int *ikc_cpus;
};

	typedef struct {
		int counter;
	} ihk_atomic_t;

	struct fake_spinlock {
		unsigned int head_tail;
	};

	struct fake_cpu_set {
		unsigned long bits[16];
	};

	struct fake_tlb_address_space {
		void *page_table;
		void *opt;
		void *free_cb;
		ihk_atomic_t refcount;
		struct fake_cpu_set cpu_set;
		struct fake_spinlock cpu_set_lock;
		int nslots;
	};

	struct fake_tlb_process_vm {
		struct fake_tlb_address_space *address_space;
	};

	struct fake_tlb_flush_entry {
		struct fake_tlb_process_vm *vm;
		unsigned long *addr;
		int nr_addr;
		ihk_atomic_t pending;
		struct fake_spinlock lock;
	} __attribute__((aligned(64)));

	typedef struct {
		long counter64;
	} ihk_atomic64_t;

struct page {
	struct list_head list;
	struct list_head hash;
	uint8_t mode;
	uint64_t phys;
	ihk_atomic_t count;
	ihk_atomic64_t mapped;
	int64_t offset;
	int pgshift;
};

struct ihk_mc_pa_ops {
	void *(*alloc_page)(int, int, unsigned long, int, int, uintptr_t);
	void (*free_page)(void *, int, int);
	void *(*alloc)(int, unsigned long);
	void (*free)(void *);
};

extern void *mem_pa_alloc_aligned_pages_node_result(
	struct ihk_mc_pa_ops *, int, int, unsigned long, int, int,
	uintptr_t, void *(*)(int));
extern void *mem_pa_alloc_pages_result(struct ihk_mc_pa_ops *, int,
	unsigned long, int, void *(*)(int));
extern void mem_pa_free_pages_result(struct ihk_mc_pa_ops *, void *, int, int);
extern int mem_reserve_pages_body_result(void *, unsigned long, unsigned long,
	unsigned long, unsigned long,
	void (*)(unsigned long, unsigned long, unsigned long),
	void (*)(void *, unsigned long, unsigned long));
extern int mem_reserve_pages_public_body_result(void *, unsigned long,
	unsigned long, unsigned long, unsigned long,
	void (*)(unsigned long, unsigned long, unsigned long),
	void (*)(void *, unsigned long, unsigned long),
	int (*)(void *, unsigned long, unsigned long, unsigned long,
		unsigned long, void (*)(unsigned long, unsigned long,
			unsigned long),
		void (*)(void *, unsigned long, unsigned long)),
	void (*)(void));
extern void *___ihk_mc_alloc_aligned_pages_node(int, int, unsigned long,
	int, int, uintptr_t);
extern void *___ihk_mc_alloc_pages(int, unsigned long, int);
extern void ___ihk_mc_free_pages(void *, int, int);
extern void ihk_mc_set_page_allocator(struct ihk_mc_pa_ops *);
extern int mem_begin_free_pages_pending_result(struct list_head *);
extern int mem_begin_free_pages_pending_body_result(struct list_head *,
	int (*)(struct list_head *), void (*)(void));
extern int mem_begin_free_pages_pending_public_body_result(
	struct list_head *(*)(void), int (*)(struct list_head *),
	void (*)(void));
extern int mem_free_pages_pending_enqueue_result(struct page *,
	struct list_head *, int, void (*)(unsigned long));
extern int mem_finish_free_pages_pending_result(struct list_head *,
	void (*)(unsigned long, int, int));
extern int mem_finish_free_pages_pending_body_result(struct list_head *,
	int (*)(struct list_head *, void (*)(unsigned long, int, int)),
	void (*)(unsigned long, int, int), void (*)(void));
extern int mem_finish_free_pages_pending_public_body_result(
	struct list_head *(*)(void),
	int (*)(struct list_head *, void (*)(unsigned long, int, int)),
	void (*)(unsigned long, int, int),
	void (*)(void));
extern int mem_free_pages_in_allocator_rbtree_result(void *, int, int,
	int (*)(void), int (*)(int, unsigned long *, unsigned long *, int *),
	unsigned long (*)(void *), void *(*)(int),
	void (*)(void *, unsigned long, int), void (*)(int, int, int));
extern int mem_mask_test_result(int, unsigned long *, int);
extern int mem_interleave_nodes_result(int, unsigned long *, int);
extern int mem_range_is_shm_result(int, int, unsigned long);
extern int mem_policy_fields_result(int, int, unsigned long *, int *,
	int *, unsigned long **, int **);
extern void *mem_current_vm_result(int, void *, void *);
extern int mem_default_alloc_policy_result(unsigned long, unsigned long *,
	int *, int *);
extern int mem_alloc_policy_should_try_policy_result(int, unsigned long, int,
	int);
extern int mem_alloc_node_id_valid_result(int, int);
extern int mem_alloc_policy_inputs_valid_result(int, int, int, int, int);
extern int mem_alloc_order_node_result(int, int, int);
extern void *mem_mckernel_alloc_policy_result(int, int, unsigned long, int,
	int, int, int, int, int, unsigned long *, int *,
	unsigned long (*)(int, int, int, int, int *),
	int (*)(int, int), int (*)(int, unsigned long *),
	int (*)(int, unsigned long *), void (*)(int, int, int),
	void *(*)(unsigned long), void (*)(int, int, int, int));
extern void *mem_mckernel_allocate_aligned_pages_node_body_result(int, int,
	unsigned long, int, int, uintptr_t, int, int, void *(*)(void),
	void *(*)(void *, unsigned long),
	void *(*)(void *, unsigned long, unsigned long), int (*)(void *),
	void (*)(void *, int *, unsigned long **, int **),
	void (*)(void *, int *, unsigned long **, int **), int (*)(void),
	void *(*)(int, int, unsigned long, int, int, int, int, int, int,
		  unsigned long *, int *));
extern void *mem_mckernel_allocate_aligned_pages_node_public_body_result(
	int, int, unsigned long, int, int, uintptr_t, int, int (*)(void),
	void *(*)(void), void *(*)(void *, unsigned long),
	void *(*)(void *, unsigned long, unsigned long), int (*)(void *),
	void (*)(void *, int *, unsigned long **, int **),
	void (*)(void *, int *, unsigned long **, int **), int (*)(void),
	void *(*)(int, int, unsigned long, int, int, int, int, int, int,
		  unsigned long *, int *));
extern int mem_mckernel_free_pages_body_result(void *, int, int,
	struct list_head *, unsigned long (*)(void *),
	struct page *(*)(unsigned long), void (*)(void *, int, int),
	void (*)(unsigned long));
extern int mem_mckernel_free_pages_public_body_result(void *, int, int,
	struct list_head *(*)(void), unsigned long (*)(void *),
	struct page *(*)(unsigned long), void (*)(void *, int, int),
	void (*)(unsigned long),
	int (*)(void *, int, int, struct list_head *,
		unsigned long (*)(void *), struct page *(*)(unsigned long),
		void (*)(void *, int, int), void (*)(unsigned long)));
extern int mem_query_free_mem_interrupt_body_result(int, char *, int, int,
	int, int, int (*)(int), void (*)(int), void (*)(void),
	char *(*)(char *), void (*)(void), void (*)(void), int (*)(void),
	void (*)(int), void (*)(int, unsigned int));
extern int mem_query_free_mem_interrupt_public_body_result(void *,
	int (*)(void), char *, int, int, int, int, int (*)(int),
	void (*)(int), void (*)(void), char *(*)(char *), void (*)(void),
	void (*)(void), int (*)(void), void (*)(int),
	void (*)(int, unsigned int));
extern int mem_set_page_allocator_result(struct ihk_mc_pa_ops **,
	struct ihk_mc_pa_ops *, void (*)(void), void (*)(void));
extern int mem_rusage_init_body_result(struct rusage_global *, unsigned long,
	struct ihk_mc_cpu_info *(*)(void), int (*)(void),
	unsigned long (*)(void), unsigned long (*)(void *),
	int (*)(unsigned long, unsigned long), void (*)(void),
	void (*)(unsigned long));
extern int mem_register_kmalloc_result(struct ihk_mc_pa_ops *, int,
	void *(*)(int, unsigned long), void (*)(void *),
	void *(*)(int, unsigned long), void (*)(void *));
extern int mem_virtual_allocator_init_body_result(void **, unsigned long,
	unsigned long, unsigned long, int,
	void *(*)(unsigned long, unsigned long, unsigned long),
	int (*)(void *, void *, unsigned long, int));
extern void *mem_map_virtual_body_result(void *, unsigned long, int, unsigned long,
	unsigned long (*)(void *, int, int),
	int (*)(void *, void *, unsigned long, unsigned long),
	int (*)(void *, void *), void (*)(void *, unsigned long, int),
	void (*)(unsigned long), void (*)(void));
extern int mem_unmap_virtual_body_result(void *, void *, int,
	int (*)(void *, void *), void (*)(unsigned long),
	void (*)(void *, unsigned long, int));
extern int mem_init_sequence_result(struct ihk_mc_pa_ops *, unsigned long,
	unsigned long, int *, int *, int *, void (*)(void), void (*)(void),
	void (*)(void), void (*)(struct ihk_mc_pa_ops *),
	void (*)(unsigned long), int (*)(int), int (*)(int, unsigned long),
	void (*)(void), void (*)(void), char *(*)(char *), void (*)(void),
	void (*)(int));
extern int mem_numa_distances_init_result(struct fake_numa_node *, int,
	struct node_distance *(*)(int, unsigned long), int (*)(int, int),
	void (*)(int), void (*)(int, struct node_distance *, int));
extern int mem_numa_distances_init_public_result(struct fake_numa_node *,
	int (*)(void), struct node_distance *(*)(int, unsigned long),
	int (*)(int, int), void (*)(int),
	void (*)(int, struct node_distance *, int));
extern int mem_numa_init_body_result(struct fake_numa_node *, int, int, int,
	unsigned long, int (*)(int, int *, int *),
	int (*)(int, unsigned long *, unsigned long *, int *),
	void (*)(struct fake_numa_node *, int),
	void (*)(struct fake_numa_node *, unsigned long, unsigned long),
	void *(*)(unsigned long, unsigned long),
	void (*)(void *, struct fake_numa_node *),
	unsigned long (*)(void *), void (*)(unsigned long),
	void (*)(int, int, int, int, unsigned long, unsigned long,
		 unsigned long, int, int),
	void (*)(int));
extern unsigned long mem_try_alloc_node_result(struct fake_numa_node *, int,
	int, int, int, int, int *, int (*)(int, int, int),
	unsigned long (*)(struct fake_numa_node *, int, int));
extern unsigned long mem_try_alloc_node_public_result(struct fake_numa_node *,
	int, int, int, int, int *, int (*)(void), int (*)(int, int, int),
	unsigned long (*)(struct fake_numa_node *, int, int));
extern int mem_distance_id_result(struct fake_numa_node *, int, int, int);
extern int mem_distance_id_public_result(struct fake_numa_node *, int, int,
	int (*)(void));
extern struct fake_numa_node *mem_get_numa_node_by_distance_result(
	struct fake_numa_node *, int, int, int, int (*)(void));
extern struct fake_numa_node *mem_get_numa_node_by_distance_public_result(
	struct fake_numa_node *, int, int, int (*)(void), int (*)(void));
extern struct fake_numa_node *mem_get_numa_node_public_result(
	struct fake_numa_node *, int, int);
extern int mem_chk_page_address_result(unsigned long, int (*)(void),
	int (*)(int, unsigned long *, unsigned long *, int *));
extern int mem_clear_dump_page_completion_result(
	struct ihk_dump_page_set *(*)(void));
extern int mem_dump_mark_range_result(struct dump_pase_info *, unsigned long,
	unsigned long, int, void (*)(int, unsigned long, unsigned long,
	unsigned long, unsigned long, unsigned long));
extern int mem_get_mem_user_page_result(struct dump_pase_info *,
	unsigned long *, int, int (*)(unsigned long),
	void (*)(int, unsigned long, unsigned long, unsigned long,
	unsigned long, unsigned long));
extern unsigned long mem_dump_free_pages_public_result(struct fake_numa_node *,
	int, int (*)(void));
extern void *mem_dump_first_free_chunk_public_result(struct fake_numa_node *,
	int, int (*)(void));
extern void *mem_dump_next_free_chunk_result(void *);
extern unsigned long mem_dump_chunk_addr_result(void *);
extern unsigned long mem_dump_chunk_size_result(void *);
extern int mem_query_mem_free_page_result(struct dump_pase_info *, int,
	unsigned long (*)(int), void *(*)(int), void *(*)(void *),
	unsigned long (*)(void *), unsigned long (*)(void *),
	void (*)(int, unsigned long, unsigned long, unsigned long,
	unsigned long, unsigned long));
extern int mem_query_mem_free_page_public_result(struct dump_pase_info *,
	int (*)(void), unsigned long (*)(int), void *(*)(int),
	void *(*)(void *), unsigned long (*)(void *),
	unsigned long (*)(void *),
	void (*)(int, unsigned long, unsigned long, unsigned long,
	unsigned long, unsigned long));
extern int mem_query_mem_user_page_result(struct list_head *, int,
	unsigned long, unsigned long, unsigned long, unsigned long,
	unsigned long,
	int (*)(void *, void *, void *, int, int,
		int (*)(void *, void *, unsigned long *, void *, int), void *),
	int (*)(void *, void *, unsigned long *, void *, int), void *);
extern int mem_query_mem_areas_result(int, int, int,
	struct ihk_dump_page_set *(*)(void), struct ihk_dump_page *(*)(void),
	void (*)(void *), void (*)(void *), void (*)(void));
extern unsigned long *mem_pt_lookup_fault_pte_body_result(void *, void *,
	int, void **, size_t *, int *, unsigned long, unsigned long,
	unsigned long *(*)(void *, void *, int, void **, size_t *, int *),
	int (*)(void *, void *, unsigned long), void (*)(void *));
	extern int mem_lookup_node_body_result(void *, void *, unsigned long,
		unsigned long,
		unsigned long *(*)(void *, void *, int, void **, size_t *, int *),
		int (*)(void *, void *, unsigned long), int (*)(unsigned long));
	extern int mem_remote_flush_tlb_array_body_result(
		struct fake_tlb_process_vm *, unsigned long *, int, int,
		struct fake_tlb_flush_entry *, int, int, int, unsigned long (*)(void),
		int (*)(void), int (*)(int), void (*)(int, int),
		void (*)(unsigned long), void (*)(unsigned long),
		void (*)(unsigned long, int), void (*)(unsigned long),
		int (*)(unsigned long), void (*)(unsigned long), void (*)(void),
		void (*)(void));
	extern int mem_tlb_flush_handler_body_result(int,
		struct fake_tlb_flush_entry *, int, int, unsigned long (*)(void),
		void (*)(unsigned long), void (*)(unsigned long), void (*)(void),
		void (*)(unsigned long));

	#define IHK_MC_AP_USER 0x001000UL
	#define IHK_MC_AP_NOWAIT 0x000002UL
#define IHK_DUMP_PAGE_SET_INCOMPLETE 0
#define IHK_DUMP_PAGE_SET_COMPLETED 1
#define DUMP_LEVEL_USER_UNUSED_EXCLUDE 24
#define USER_END 0x0000800000000000UL
#define PTATTR_ACTIVE 0x01UL
#define PTATTR_USER 0x04UL
#define PT_PHYSMASK ((((1UL << 52) - 1)) & ~(4096UL - 1))
#define PF_USER (1UL << 2)
#define PF_POPULATE (1UL << 30)
#define PAGE_SHIFT 12
#define PAGE_SIZE (1UL << PAGE_SHIFT)
#define PAGE_MASK (~(PAGE_SIZE - 1))
#define MPOL_DEFAULT 0
#define MPOL_PREFERRED 1
#define MPOL_BIND 2
#define MPOL_INTERLEAVE 3
#define MEM_INIT_MF_SHM 0x40000UL
#define MEM_ALLOC_LOG_EXPLICIT_OK 1
#define MEM_ALLOC_LOG_EXPLICIT_MISS 2
#define MEM_ALLOC_LOG_POLICY_OK 3
#define MEM_ALLOC_LOG_POLICY_MISS 4
#define MEM_ALLOC_LOG_DISTANCE_OK 5
#define MEM_ALLOC_LOG_DISTANCE_FIRST_MISS 6
#define MEM_ALLOC_LOG_OOM 7
#define MEM_INIT_LOG_ANON_ON_DEMAND 1
#define MEM_INIT_LOG_XPMEM_PAGE_IN_REMOTE 2
#define MEM_INIT_LOG_HUGETLBFS_ON_DEMAND 3
#define MEM_NUMA_INIT_LOG_CHUNK 1
#define MEM_NUMA_INIT_LOG_NODE 2

struct mem_chunk {
	unsigned long start;
	unsigned long end;
	int nid;
};

static struct mem_chunk chunks[8];
static int nr_chunks;
static char *current_kargs;

int ihk_mc_get_nr_memory_chunks(void)
{
	return nr_chunks;
}

int ihk_mc_get_memory_chunk(int id, unsigned long *start,
			    unsigned long *end, int *numa_id)
{
	if (id < 0 || id >= nr_chunks)
		return -1;
	if (start)
		*start = chunks[id].start;
	if (end)
		*end = chunks[id].end;
	if (numa_id)
		*numa_id = chunks[id].nid;
	return 0;
}

char *ihk_get_kargs(void)
{
	return current_kargs;
}

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

static void mix_signed(unsigned long *digest, long value)
{
	mix(digest, (unsigned long)value);
}

static void require_line(int cond, int line)
{
	if (!cond) {
		printf("mem init require failed line=%d\n", line);
		exit(1);
	}
}

#define require(cond) require_line((cond), __LINE__)

static long ptr_offset(const char *base, const char *ptr)
{
	if (!base || !ptr)
		return -1;
	return ptr - base;
}

static unsigned long round_helpers_digest(void)
{
	static const unsigned long values[] = {
		0, 1, 2, 3, 7, 8, 9, 15, 16, 17, 4095, 4096, 4097,
		0xfffffffffffffff0UL,
	};
	static const unsigned long aligns[] = {
		1, 2, 4, 8, 16, 4096,
	};
	unsigned long digest = 0x726f756e646d6d61UL;

	for (unsigned int i = 0; i < sizeof(values) / sizeof(values[0]); i++) {
		for (unsigned int j = 0; j < sizeof(aligns) / sizeof(aligns[0]); j++) {
			unsigned long value = values[i];
			unsigned long align = aligns[j];
			unsigned long expected_up = ((value - 1) | (align - 1)) + 1;
			unsigned long expected_down = value & ~(align - 1);
			unsigned long actual_up = round_up(value, align);
			unsigned long actual_down = round_down(value, align);

			require(actual_up == expected_up);
			require(actual_down == expected_down);
			mix(&digest, actual_up);
			mix(&digest, actual_down);
		}
	}

	return digest;
}

static uint64_t expected_hash_64(uint64_t val, unsigned int bits)
{
	uint64_t hash = val;
	uint64_t n = hash;

	n <<= 18;
	hash -= n;
	n <<= 33;
	hash -= n;
	n <<= 3;
	hash += n;
	n <<= 3;
	hash -= n;
	n <<= 4;
	hash += n;
	n <<= 2;
	hash += n;

	return hash >> (64 - bits);
}

static uint32_t expected_hash_32(uint32_t val, unsigned int bits)
{
	uint32_t hash = val * 0x9e370001UL;

	return hash >> (32 - bits);
}

static unsigned long hash_helpers_digest(void)
{
	static const uint64_t values64[] = {
		0, 1, 2, 3, 0x123456789abcdef0ULL,
		0x8000000000000000ULL, 0xffffffffffffffffULL,
	};
	static const uint32_t values32[] = {
		0, 1, 2, 3, 0x12345678U, 0x80000000U, 0xffffffffU,
	};
	static const unsigned int bits64[] = {
		1, 2, 5, 17, 31, 32, 47, 63, 64,
	};
	static const unsigned int bits32[] = {
		1, 2, 5, 16, 31, 32,
	};
	unsigned long digest = 0x686173686d6d2121UL;

	for (unsigned int i = 0; i < sizeof(values64) / sizeof(values64[0]); i++) {
		for (unsigned int j = 0; j < sizeof(bits64) / sizeof(bits64[0]); j++) {
			uint64_t value = values64[i];
			unsigned int bits = bits64[j];
			uint64_t expected = expected_hash_64(value, bits);
			uint64_t actual64 = hash_64(value, bits);
			unsigned long actuall = hash_long((unsigned long)value, bits);
			unsigned long actualp = hash_ptr((void *)(uintptr_t)value, bits);

			require(actual64 == expected);
			require(actuall == (unsigned long)expected);
			require(actualp == (unsigned long)expected);
			mix(&digest, (unsigned long)actual64);
			mix(&digest, actuall);
			mix(&digest, actualp);
		}
	}

	for (unsigned int i = 0; i < sizeof(values32) / sizeof(values32[0]); i++) {
		for (unsigned int j = 0; j < sizeof(bits32) / sizeof(bits32[0]); j++) {
			uint32_t expected = expected_hash_32(values32[i], bits32[j]);
			uint32_t actual = hash_32(values32[i], bits32[j]);

			require(actual == expected);
			mix(&digest, actual);
		}
	}

	return digest;
}

static void set_chunks(const struct mem_chunk *src, int count)
{
	nr_chunks = count;
	for (int i = 0; i < count; i++)
		chunks[i] = src[i];
}

static unsigned char alloc_area[256];
static int alloc_page_calls;
static int alloc_page_npages;
static int alloc_page_p2align;
static unsigned long alloc_page_flag;
static int alloc_page_node;
static int alloc_page_is_user;
static uintptr_t alloc_page_virt_addr;
static int early_alloc_calls;
static int early_alloc_npages;
static int free_page_calls;
static void *free_page_ptr;
static int free_page_npages;
static int free_page_is_user;
static int reserve_log_calls;
static unsigned long reserve_log_start;
static unsigned long reserve_log_end;
static unsigned long reserve_log_pages;
static int reserve_range_calls;
static void *reserve_range_pa;
static unsigned long reserve_range_start;
static unsigned long reserve_range_end;
static int reserve_panic_count;
static int pending_warn_count;
static unsigned long pending_warn_phys;
static int pending_free_count;
static unsigned long pending_free_phys[4];
static int pending_free_npages[4];
static int pending_free_is_user[4];
static int pending_panic_count;
static unsigned long fake_current_phys;
static void *fake_nodes[8];
static int numa_free_count;
static void *numa_free_node;
static unsigned long numa_free_addr;
static int numa_free_npages;
static int rusage_sub_count;
static int rusage_sub_nid;
static int rusage_sub_npages;
static int rusage_sub_is_user;
static unsigned long policy_alloc_pa[8];
static int policy_alloc_oom[8];
static int policy_alloc_count;
static int policy_alloc_nodes[16];
static int policy_alloc_npages;
static int policy_alloc_p2align;
static int policy_alloc_is_user;
static int policy_distance[8];
static int policy_rusage_add_count;
static int policy_rusage_add_nid;
static int policy_rusage_add_npages;
static int policy_rusage_add_is_user;
static int policy_log_count;
static unsigned long policy_log_digest;
static int policy_last_log_event;
static int policy_last_log_numa;
struct fake_alloc_body_policy {
	int numa_mem_policy;
	unsigned long *numa_mask;
	int il_prev;
};
struct fake_alloc_body_range {
	int is_shm;
};
struct fake_alloc_body_vm {
	int numa_mem_policy;
	unsigned long *numa_mask;
	int il_prev;
	struct fake_alloc_body_policy *range_policy;
	struct fake_alloc_body_range *range;
};
static struct fake_alloc_body_vm alloc_body_vm;
static struct fake_alloc_body_policy alloc_body_range_policy;
static struct fake_alloc_body_range alloc_body_range;
static void *alloc_body_current_vm;
static int alloc_body_current_node;
static void *alloc_body_policy_return;
static int alloc_body_current_vm_count;
static int alloc_body_range_policy_count;
static unsigned long alloc_body_range_policy_addr;
static int alloc_body_lookup_count;
static unsigned long alloc_body_lookup_start;
static unsigned long alloc_body_lookup_end;
static int alloc_body_range_is_shm_count;
static int alloc_body_range_fields_count;
static int alloc_body_vm_fields_count;
static int alloc_body_current_node_count;
static int alloc_body_policy_count;
static int alloc_body_policy_npages;
static int alloc_body_policy_p2align;
static unsigned long alloc_body_policy_flag;
static int alloc_body_policy_pref_node;
static int alloc_body_policy_is_user;
static int alloc_body_policy_current_node;
static int alloc_body_policy_nr_nodes;
static int alloc_body_policy_numa_mem_policy;
static int alloc_body_policy_chk_shm;
static unsigned long *alloc_body_policy_mask;
static int *alloc_body_policy_il_prev;
static int free_body_phys_to_page_count;
static struct page *free_body_page_return;
static int free_body_allocator_count;
static void *free_body_allocator_va;
static int free_body_allocator_npages;
static int free_body_allocator_is_user;
static struct list_head *free_body_pending_return;
static int free_body_pending_count;
static int query_free_node_pages[8];
static int query_free_nr_nodes;
static int query_free_nr_nodes_count;
static int query_free_node_calls;
static int query_free_node_trace[16];
static int query_free_total_log_count;
static int query_free_total_pages;
static int query_free_panic_count;
static int query_free_memdebug_present;
static int query_free_find_count;
static char *query_free_find_name;
static int query_free_kmalloc_count;
static int query_free_pagealloc_count;
static int query_free_page_hash_count_calls;
static int query_free_page_hash_pages;
static int query_free_page_hash_log_count;
static int query_free_page_hash_log_pages;
static int query_free_sbox_count;
static int query_free_sbox_offsets[4];
static unsigned int query_free_sbox_values[4];
static int lifecycle_order[32];
static int lifecycle_order_count;
static int lifecycle_track_init_count;
static int lifecycle_early_invalidate_count;
static int lifecycle_set_allocator_count;
static struct ihk_mc_pa_ops *lifecycle_set_allocator_ops;
static int lifecycle_set_pf_count;
static unsigned long lifecycle_pf_handler;
static int lifecycle_get_vector_count;
static int lifecycle_get_vector_type;
static int lifecycle_register_count;
static int lifecycle_register_vector;
static unsigned long lifecycle_register_handler;
static int lifecycle_flags[3];
static int lifecycle_log_events[8];
static int lifecycle_log_count;
static char *lifecycle_cmdline;
static struct ihk_mc_cpu_info rusage_cpu_info;
static int rusage_get_cpu_info_null;
static int rusage_get_cpu_info_count;
static int rusage_nr_nodes_count;
static int rusage_nr_nodes_value;
static int rusage_ns_count;
static unsigned long rusage_ns_value;
static int rusage_virt_to_phys_count;
static void *rusage_virt_to_phys_arg;
static unsigned long rusage_virt_to_phys_value;
static int rusage_set_count;
static unsigned long rusage_set_phys;
static unsigned long rusage_set_size;
static int rusage_set_rc;
static int rusage_panic_count;
static int rusage_log_count;
static unsigned long rusage_log_total;
static int numa_get_fail_node;
static int numa_node_init_count;
static int numa_node_init_ids[8];
static int numa_node_init_rbtree[8];
static int numa_add_free_count;
static int numa_add_free_nodes[8];
static unsigned long numa_add_free_starts[8];
static unsigned long numa_add_free_lens[8];
static int numa_page_allocator_count;
static unsigned long numa_page_allocator_starts[8];
static unsigned long numa_page_allocator_ends[8];
static unsigned long numa_page_allocator_pages[8];
static unsigned long numa_allocator_tokens[8];
static int numa_list_allocator_count;
static int numa_list_allocator_nodes[8];
static unsigned long numa_list_allocator_tokens[8];
static int numa_pagealloc_count_calls;
static int numa_rusage_count;
static unsigned long numa_rusage_bytes;
static int numa_log_count;
static unsigned long numa_log_digest;
static int numa_panic_count;
static int numa_panic_node;
static struct node_distance distance_storage[8][8];
static int distance_matrix[8][8];
static int distance_alloc_count;
static int distance_alloc_fail_index;
static int distance_alloc_npages[8];
static unsigned long distance_alloc_flags[8];
static int distance_alloc_fail_logs[8];
static int distance_alloc_fail_count;
static int distance_log_nodes[8];
static int distance_log_count;
static unsigned long distance_log_digest;
static int topology_oom_nodes[8];
static int topology_oom_count;
static int topology_alloc_count;
static int topology_alloc_node_ids[8];
static int topology_alloc_npages;
static int topology_alloc_p2align;
static unsigned long topology_alloc_returns[8];
static int topology_nr_nodes;
static int topology_nr_nodes_count;
static int topology_current_node;
static int topology_current_count;
static unsigned char dump_storage[512];
static struct ihk_dump_page_set dump_page_set;
static int dump_get_set_count;
static int dump_get_page_count;
static int dump_query_user_count;
static int dump_query_free_count;
static int dump_log_count;
static int dump_warn_count;
static unsigned long dump_warn_digest;
static int dump_free_counts[4];
static int dump_first_count;
static int dump_next_count;
static struct fake_free_chunk {
	unsigned long addr;
	unsigned long size;
	int next;
} dump_chunks[6];
static struct fake_rb_free_chunk dump_rb_chunks[4];
static int dump_first_index[4];
static struct list_head dump_process_hash[4];
static struct fake_process dump_processes[5];
static struct fake_process_vm dump_vms[5];
static struct fake_address_space dump_spaces[5];
static unsigned long dump_page_tables[5];
static unsigned long dump_query_digest;
static int dump_visit_count;
static int dump_pte_visitor_count;
static void *dump_last_arg;
static unsigned long fault_lookup_ptes[4];
static int fault_lookup_count;
static void *fault_lookup_pts[8];
static void *fault_lookup_virts[8];
static int fault_lookup_pgshifts[8];
static void **fault_lookup_baseps[8];
static size_t *fault_lookup_sizeps[8];
static int *fault_lookup_p2alignps[8];
static int fault_page_fault_count;
static void *fault_page_fault_vm;
static void *fault_page_fault_virt;
static unsigned long fault_page_fault_reason;
static int fault_page_fault_rc;
static int fault_log_count;
static void *fault_log_virt;
static int fault_phys_to_nid_count;
static unsigned long fault_phys_to_nid_phys;
static int fault_phys_to_nid_result;
static unsigned long vmap_allocator_token = 0xabcddcbaUL;
static int vmap_init_count;
static unsigned long vmap_init_start;
static unsigned long vmap_init_size;
static unsigned long vmap_init_unit;
static int vmap_prepare_count;
static void *vmap_prepare_pt;
static void *vmap_prepare_virt;
static unsigned long vmap_prepare_size;
static int vmap_prepare_flag;
static int vmap_prepare_rc;
static int vmap_alloc_count;
static void *vmap_alloc_desc;
static int vmap_alloc_npages;
static int vmap_alloc_p2align;
static unsigned long vmap_alloc_return;
static int vmap_free_count;
static void *vmap_free_desc;
static unsigned long vmap_free_addr;
static int vmap_free_npages;
static int vmap_set_count;
static void *vmap_set_pt[8];
static unsigned long vmap_set_virt[8];
static unsigned long vmap_set_phys[8];
static unsigned long vmap_set_attr[8];
static int vmap_set_fail_at;
static int vmap_clear_count;
static void *vmap_clear_pt[8];
static unsigned long vmap_clear_virt[8];
	static int vmap_flush_count;
	static unsigned long vmap_flush_addr[8];
	static int vmap_barrier_count;
	static int tlb_lock_count;
	static int tlb_unlock_count;
	static unsigned long tlb_lock_addr[8];
	static unsigned long tlb_unlock_addr[8];
	static int tlb_atomic_set_count;
	static unsigned long tlb_atomic_set_addr;
	static int tlb_atomic_set_value;
	static int tlb_atomic_inc_count;
	static unsigned long tlb_atomic_inc_addr[8];
	static int tlb_atomic_dec_count;
	static unsigned long tlb_atomic_dec_addr;
	static int tlb_atomic_read_count;
	static int tlb_atomic_read_remaining;
	static int tlb_pause_count;
	static int tlb_current_cpu;
	static int tlb_current_count;
	static int tlb_get_vector_count;
	static int tlb_get_vector_arg[8];
	static int tlb_interrupt_count;
	static int tlb_interrupt_cpu[8];
	static int tlb_interrupt_vector[8];
	static int tlb_flush_single_count;
	static unsigned long tlb_flush_single_addr[8];
	static int tlb_flush_all_count;
	static int tlb_irq_save_count;
	static int tlb_irq_restore_count;
	static unsigned long tlb_irq_restore_flags;
	static unsigned long tlb_rdtsc_value;

	static void reset_tlb_trace(void)
	{
		tlb_lock_count = 0;
		tlb_unlock_count = 0;
		memset(tlb_lock_addr, 0, sizeof(tlb_lock_addr));
		memset(tlb_unlock_addr, 0, sizeof(tlb_unlock_addr));
		tlb_atomic_set_count = 0;
		tlb_atomic_set_addr = 0;
		tlb_atomic_set_value = -1;
		tlb_atomic_inc_count = 0;
		memset(tlb_atomic_inc_addr, 0, sizeof(tlb_atomic_inc_addr));
		tlb_atomic_dec_count = 0;
		tlb_atomic_dec_addr = 0;
		tlb_atomic_read_count = 0;
		tlb_atomic_read_remaining = 0;
		tlb_pause_count = 0;
		tlb_current_cpu = 0;
		tlb_current_count = 0;
		tlb_get_vector_count = 0;
		memset(tlb_get_vector_arg, 0, sizeof(tlb_get_vector_arg));
		tlb_interrupt_count = 0;
		memset(tlb_interrupt_cpu, 0, sizeof(tlb_interrupt_cpu));
		memset(tlb_interrupt_vector, 0, sizeof(tlb_interrupt_vector));
		tlb_flush_single_count = 0;
		memset(tlb_flush_single_addr, 0, sizeof(tlb_flush_single_addr));
		tlb_flush_all_count = 0;
		tlb_irq_save_count = 0;
		tlb_irq_restore_count = 0;
		tlb_irq_restore_flags = 0;
		tlb_rdtsc_value = 0x1234UL;
	}

	static unsigned long fake_tlb_rdtsc(void)
	{
		return tlb_rdtsc_value;
	}

	static int fake_tlb_current_cpu(void)
	{
		tlb_current_count++;
		return tlb_current_cpu;
	}

	static int fake_tlb_get_vector(int type)
	{
		if (tlb_get_vector_count < 8)
			tlb_get_vector_arg[tlb_get_vector_count] = type;
		tlb_get_vector_count++;
		return 0x80 + type;
	}

	static void fake_tlb_interrupt_cpu(int cpu, int vector)
	{
		if (tlb_interrupt_count < 8) {
			tlb_interrupt_cpu[tlb_interrupt_count] = cpu;
			tlb_interrupt_vector[tlb_interrupt_count] = vector;
		}
		tlb_interrupt_count++;
	}

	static void fake_tlb_lock(unsigned long lock_addr)
	{
		if (tlb_lock_count < 8)
			tlb_lock_addr[tlb_lock_count] = lock_addr;
		tlb_lock_count++;
	}

	static void fake_tlb_unlock(unsigned long lock_addr)
	{
		if (tlb_unlock_count < 8)
			tlb_unlock_addr[tlb_unlock_count] = lock_addr;
		tlb_unlock_count++;
	}

	static void fake_tlb_atomic_set(unsigned long atomic_addr, int value)
	{
		tlb_atomic_set_count++;
		tlb_atomic_set_addr = atomic_addr;
		tlb_atomic_set_value = value;
		((ihk_atomic_t *)atomic_addr)->counter = value;
	}

	static void fake_tlb_atomic_inc(unsigned long atomic_addr)
	{
		if (tlb_atomic_inc_count < 8)
			tlb_atomic_inc_addr[tlb_atomic_inc_count] = atomic_addr;
		tlb_atomic_inc_count++;
		((ihk_atomic_t *)atomic_addr)->counter++;
	}

	static void fake_tlb_atomic_dec(unsigned long atomic_addr)
	{
		tlb_atomic_dec_count++;
		tlb_atomic_dec_addr = atomic_addr;
		((ihk_atomic_t *)atomic_addr)->counter--;
	}

	static int fake_tlb_atomic_read(unsigned long atomic_addr)
	{
		int value = tlb_atomic_read_remaining;

		(void)atomic_addr;
		tlb_atomic_read_count++;
		if (tlb_atomic_read_remaining > 0)
			tlb_atomic_read_remaining--;
		return value;
	}

	static void fake_tlb_flush_single(unsigned long addr)
	{
		if (tlb_flush_single_count < 8)
			tlb_flush_single_addr[tlb_flush_single_count] = addr;
		tlb_flush_single_count++;
	}

	static void fake_tlb_flush_all(void)
	{
		tlb_flush_all_count++;
	}

	static void fake_tlb_pause(void)
	{
		tlb_pause_count++;
	}

	static unsigned long fake_tlb_irq_save(void)
	{
		tlb_irq_save_count++;
		return 0xabcUL;
	}

	static void fake_tlb_irq_restore(unsigned long flags)
	{
		tlb_irq_restore_count++;
		tlb_irq_restore_flags = flags;
	}

	static void *fake_alloc_page(int npages, int p2align, unsigned long flag,
			     int node, int is_user, uintptr_t virt_addr)
{
	alloc_page_calls++;
	alloc_page_npages = npages;
	alloc_page_p2align = p2align;
	alloc_page_flag = flag;
	alloc_page_node = node;
	alloc_page_is_user = is_user;
	alloc_page_virt_addr = virt_addr;
	return alloc_area + 64;
}

static void *fake_early_alloc(int npages)
{
	early_alloc_calls++;
	early_alloc_npages = npages;
	return alloc_area + 128;
}

void *early_alloc_pages(int npages)
{
	return fake_early_alloc(npages);
}

static void fake_free_page(void *ptr, int npages, int is_user)
{
	free_page_calls++;
	free_page_ptr = ptr;
	free_page_npages = npages;
	free_page_is_user = is_user;
}

static void reset_reserve_trace(void)
{
	reserve_log_calls = 0;
	reserve_log_start = 0;
	reserve_log_end = 0;
	reserve_log_pages = 0;
	reserve_range_calls = 0;
	reserve_range_pa = NULL;
	reserve_range_start = 0;
	reserve_range_end = 0;
	reserve_panic_count = 0;
}

static void fake_reserve_log(unsigned long start, unsigned long end,
			     unsigned long pages)
{
	reserve_log_calls++;
	reserve_log_start = start;
	reserve_log_end = end;
	reserve_log_pages = pages;
}

static void fake_reserve_range(void *pa, unsigned long start,
			       unsigned long end)
{
	reserve_range_calls++;
	reserve_range_pa = pa;
	reserve_range_start = start;
	reserve_range_end = end;
}

static void fake_reserve_panic(void)
{
	reserve_panic_count++;
}

static void fake_pending_warn(unsigned long phys)
{
	pending_warn_count++;
	pending_warn_phys = phys;
}

static void fake_pending_free(unsigned long phys, int npages, int is_user)
{
	if (pending_free_count < 4) {
		pending_free_phys[pending_free_count] = phys;
		pending_free_npages[pending_free_count] = npages;
		pending_free_is_user[pending_free_count] = is_user;
	}
	pending_free_count++;
}

static void fake_pending_panic(void)
{
	pending_panic_count++;
}

static int fake_get_nr_chunks(void)
{
	return nr_chunks;
}

static unsigned long fake_virt_to_phys(void *va)
{
	(void)va;
	return fake_current_phys;
}

static void *fake_get_numa_node(int numa_id)
{
	if (numa_id < 0 || numa_id >= 8)
		return NULL;
	return fake_nodes[numa_id];
}

static void fake_numa_free(void *node, unsigned long addr, int npages)
{
	numa_free_count++;
	numa_free_node = node;
	numa_free_addr = addr;
	numa_free_npages = npages;
}

static void fake_rusage_sub(int numa_id, int npages, int is_user)
{
	rusage_sub_count++;
	rusage_sub_nid = numa_id;
	rusage_sub_npages = npages;
	rusage_sub_is_user = is_user;
}

static void reset_policy_alloc_trace(void)
{
	for (int i = 0; i < 8; i++) {
		policy_alloc_pa[i] = 0;
		policy_alloc_oom[i] = 0;
		policy_distance[i] = i;
	}
	for (int i = 0; i < 16; i++)
		policy_alloc_nodes[i] = -1;
	policy_alloc_count = 0;
	policy_alloc_npages = 0;
	policy_alloc_p2align = 0;
	policy_alloc_is_user = 0;
	policy_rusage_add_count = 0;
	policy_rusage_add_nid = -1;
	policy_rusage_add_npages = 0;
	policy_rusage_add_is_user = 0;
	policy_log_count = 0;
	policy_log_digest = 0x706f6c616c6c6f63UL;
	policy_last_log_event = 0;
	policy_last_log_numa = -1;
}

static unsigned long fake_policy_try_alloc(int numa_id, int npages,
					   int p2align, int is_user,
					   int *oomp)
{
	if (policy_alloc_count < 16)
		policy_alloc_nodes[policy_alloc_count] = numa_id;
	policy_alloc_count++;
	policy_alloc_npages = npages;
	policy_alloc_p2align = p2align;
	policy_alloc_is_user = is_user;
	if (oomp)
		*oomp = policy_alloc_oom[numa_id];
	return policy_alloc_pa[numa_id];
}

static int fake_policy_distance_id(int base_node, int index)
{
	(void)base_node;
	if (index < 0 || index >= 8)
		return -1;
	return policy_distance[index];
}

static int fake_policy_mask_test(int numa_id, unsigned long *mask)
{
	if (!mask || numa_id < 0)
		return 0;
	return (mask[numa_id / (8 * sizeof(unsigned long))] >>
		(numa_id % (8 * sizeof(unsigned long)))) & 1UL;
}

static int fake_policy_interleave_next(int off, unsigned long *mask)
{
	return mem_interleave_nodes_result(off, mask, 256);
}

static void fake_policy_rusage_add(int numa_id, int npages, int is_user)
{
	policy_rusage_add_count++;
	policy_rusage_add_nid = numa_id;
	policy_rusage_add_npages = npages;
	policy_rusage_add_is_user = is_user;
}

static void *fake_policy_phys_to_virt(unsigned long pa)
{
	return (void *)(pa + 0x100000000UL);
}

static void fake_policy_log(int event, int current_node, int numa_id,
			    int npages)
{
	policy_log_count++;
	policy_last_log_event = event;
	policy_last_log_numa = numa_id;
	mix(&policy_log_digest, (unsigned long)event);
	mix(&policy_log_digest, (unsigned long)current_node);
	mix(&policy_log_digest, (unsigned long)(int)numa_id);
	mix(&policy_log_digest, (unsigned long)npages);
}

static void reset_alloc_body_trace(void)
{
	memset(&alloc_body_vm, 0, sizeof(alloc_body_vm));
	memset(&alloc_body_range_policy, 0, sizeof(alloc_body_range_policy));
	memset(&alloc_body_range, 0, sizeof(alloc_body_range));
	alloc_body_current_vm = NULL;
	alloc_body_current_node = 0;
	alloc_body_policy_return = alloc_area + 200;
	alloc_body_current_vm_count = 0;
	alloc_body_range_policy_count = 0;
	alloc_body_range_policy_addr = 0;
	alloc_body_lookup_count = 0;
	alloc_body_lookup_start = 0;
	alloc_body_lookup_end = 0;
	alloc_body_range_is_shm_count = 0;
	alloc_body_range_fields_count = 0;
	alloc_body_vm_fields_count = 0;
	alloc_body_current_node_count = 0;
	alloc_body_policy_count = 0;
	alloc_body_policy_npages = 0;
	alloc_body_policy_p2align = 0;
	alloc_body_policy_flag = 0;
	alloc_body_policy_pref_node = 0;
	alloc_body_policy_is_user = 0;
	alloc_body_policy_current_node = 0;
	alloc_body_policy_nr_nodes = 0;
	alloc_body_policy_numa_mem_policy = 0;
	alloc_body_policy_chk_shm = 0;
	alloc_body_policy_mask = NULL;
	alloc_body_policy_il_prev = NULL;
}

static void *fake_alloc_body_current_vm(void)
{
	alloc_body_current_vm_count++;
	return alloc_body_current_vm;
}

static void *fake_alloc_body_range_policy_search(void *vm,
						 unsigned long virt_addr)
{
	struct fake_alloc_body_vm *fake_vm = vm;

	alloc_body_range_policy_count++;
	alloc_body_range_policy_addr = virt_addr;
	return fake_vm ? fake_vm->range_policy : NULL;
}

static void *fake_alloc_body_lookup_range(void *vm, unsigned long start,
					  unsigned long end)
{
	struct fake_alloc_body_vm *fake_vm = vm;

	alloc_body_lookup_count++;
	alloc_body_lookup_start = start;
	alloc_body_lookup_end = end;
	return fake_vm ? fake_vm->range : NULL;
}

static int fake_alloc_body_range_is_shm(void *range)
{
	struct fake_alloc_body_range *fake_range = range;

	alloc_body_range_is_shm_count++;
	return fake_range ? fake_range->is_shm : 0;
}

static void fake_alloc_body_range_fields(void *policy, int *numa_mem_policy,
					 unsigned long **numa_mask,
					 int **il_prev)
{
	struct fake_alloc_body_policy *fake_policy = policy;

	alloc_body_range_fields_count++;
	mem_policy_fields_result(!!fake_policy,
		fake_policy ? fake_policy->numa_mem_policy : -1,
		fake_policy ? fake_policy->numa_mask : NULL,
		fake_policy ? &fake_policy->il_prev : NULL,
		numa_mem_policy, numa_mask, il_prev);
}

static void fake_alloc_body_vm_fields(void *vm, int *numa_mem_policy,
				      unsigned long **numa_mask,
				      int **il_prev)
{
	struct fake_alloc_body_vm *fake_vm = vm;

	alloc_body_vm_fields_count++;
	mem_policy_fields_result(!!fake_vm,
		fake_vm ? fake_vm->numa_mem_policy : -1,
		fake_vm ? fake_vm->numa_mask : NULL,
		fake_vm ? &fake_vm->il_prev : NULL,
		numa_mem_policy, numa_mask, il_prev);
}

static int fake_alloc_body_current_numa_id(void)
{
	alloc_body_current_node_count++;
	return alloc_body_current_node;
}

static void *fake_alloc_body_policy_alloc(int npages, int p2align,
					  unsigned long flag, int pref_node,
					  int is_user, int current_node,
					  int nr_nodes, int numa_mem_policy,
					  int chk_shm, unsigned long *numa_mask,
					  int *il_prev)
{
	alloc_body_policy_count++;
	alloc_body_policy_npages = npages;
	alloc_body_policy_p2align = p2align;
	alloc_body_policy_flag = flag;
	alloc_body_policy_pref_node = pref_node;
	alloc_body_policy_is_user = is_user;
	alloc_body_policy_current_node = current_node;
	alloc_body_policy_nr_nodes = nr_nodes;
	alloc_body_policy_numa_mem_policy = numa_mem_policy;
	alloc_body_policy_chk_shm = chk_shm;
	alloc_body_policy_mask = numa_mask;
	alloc_body_policy_il_prev = il_prev;
	return alloc_body_policy_return;
}

static struct page *fake_free_body_phys_to_page(unsigned long phys)
{
	free_body_phys_to_page_count++;
	pending_warn_phys = phys;
	return free_body_page_return;
}

static void fake_free_body_in_allocator(void *va, int npages, int is_user)
{
	free_body_allocator_count++;
	free_body_allocator_va = va;
	free_body_allocator_npages = npages;
	free_body_allocator_is_user = is_user;
}

static struct list_head *fake_free_body_pending_pages(void)
{
	free_body_pending_count++;
	return free_body_pending_return;
}

static void reset_query_free_trace(void)
{
	for (int i = 0; i < 8; i++)
		query_free_node_pages[i] = 0;
	for (int i = 0; i < 16; i++)
		query_free_node_trace[i] = -1;
	for (int i = 0; i < 4; i++) {
		query_free_sbox_offsets[i] = 0;
		query_free_sbox_values[i] = 0;
	}
	query_free_node_calls = 0;
	query_free_nr_nodes = 0;
	query_free_nr_nodes_count = 0;
	query_free_total_log_count = 0;
	query_free_total_pages = 0;
	query_free_panic_count = 0;
	query_free_memdebug_present = 0;
	query_free_find_count = 0;
	query_free_find_name = NULL;
	query_free_kmalloc_count = 0;
	query_free_pagealloc_count = 0;
	query_free_page_hash_count_calls = 0;
	query_free_page_hash_pages = 0;
	query_free_page_hash_log_count = 0;
	query_free_page_hash_log_pages = 0;
	query_free_sbox_count = 0;
}

static int fake_query_free_node_pages(int node)
{
	if (query_free_node_calls < 16)
		query_free_node_trace[query_free_node_calls] = node;
	query_free_node_calls++;
	if (node < 0 || node >= 8)
		return 0;
	return query_free_node_pages[node];
}

static int fake_query_free_nr_nodes(void)
{
	query_free_nr_nodes_count++;
	return query_free_nr_nodes;
}

static void fake_query_free_total_log(int pages)
{
	query_free_total_log_count++;
	query_free_total_pages = pages;
}

static void fake_query_free_panic(void)
{
	query_free_panic_count++;
}

static char *fake_query_free_find_command_line(char *name)
{
	query_free_find_count++;
	query_free_find_name = name;
	return query_free_memdebug_present ? name : NULL;
}

static void fake_query_free_kmalloc_memcheck(void)
{
	query_free_kmalloc_count++;
}

static void fake_query_free_pagealloc_memcheck(void)
{
	query_free_pagealloc_count++;
}

static int fake_query_free_page_hash_count(void)
{
	query_free_page_hash_count_calls++;
	return query_free_page_hash_pages;
}

static void fake_query_free_page_hash_log(int pages)
{
	query_free_page_hash_log_count++;
	query_free_page_hash_log_pages = pages;
}

static void fake_query_free_sbox_write(int offset, unsigned int value)
{
	if (query_free_sbox_count < 4) {
		query_free_sbox_offsets[query_free_sbox_count] = offset;
		query_free_sbox_values[query_free_sbox_count] = value;
	}
	query_free_sbox_count++;
}

static void lifecycle_note(int event)
{
	if (lifecycle_order_count < 32)
		lifecycle_order[lifecycle_order_count] = event;
	lifecycle_order_count++;
}

static void fake_lifecycle_track_init(void)
{
	lifecycle_track_init_count++;
	lifecycle_note(1);
}

static void fake_lifecycle_early_invalidate(void)
{
	lifecycle_early_invalidate_count++;
	lifecycle_note(2);
}

void early_alloc_invalidate(void)
{
	lifecycle_early_invalidate_count++;
}

void x86_early_alloc_invalidate_bridge(void)
{
	lifecycle_early_invalidate_count++;
}

#ifndef MEM_INIT_C_FALLBACK
extern int pagealloc_track_initialized;

void pagealloc_track_init(void)
{
	lifecycle_track_init_count++;
}
#endif

static void fake_lifecycle_monitor(void)
{
	lifecycle_note(10);
}

static void fake_lifecycle_rusage(void)
{
	lifecycle_note(11);
}

static void fake_lifecycle_numa(void)
{
	lifecycle_note(12);
}

static void fake_lifecycle_set_allocator(struct ihk_mc_pa_ops *ops)
{
	lifecycle_set_allocator_count++;
	lifecycle_set_allocator_ops = ops;
	lifecycle_note(13);
}

static void fake_lifecycle_set_page_fault(unsigned long handler)
{
	lifecycle_set_pf_count++;
	lifecycle_pf_handler = handler;
	lifecycle_note(14);
}

static int fake_lifecycle_get_vector(int type)
{
	lifecycle_get_vector_count++;
	lifecycle_get_vector_type = type;
	lifecycle_note(15);
	return type + 40;
}

static int fake_lifecycle_register_interrupt(int vector, unsigned long handler)
{
	lifecycle_register_count++;
	lifecycle_register_vector = vector;
	lifecycle_register_handler = handler;
	lifecycle_note(16);
	return vector == 42 ? 0 : -22;
}

static void fake_lifecycle_page_init(void)
{
	lifecycle_note(17);
}

static void fake_lifecycle_virtual_allocator(void)
{
	lifecycle_note(18);
}

static char *fake_lifecycle_find_command(char *name)
{
	lifecycle_note(19);
	if (!lifecycle_cmdline || !name)
		return NULL;
	return strstr(lifecycle_cmdline, name);
}

static void fake_lifecycle_numa_distances(void)
{
	lifecycle_note(20);
}

static void fake_lifecycle_log(int event)
{
	if (lifecycle_log_count < 8)
		lifecycle_log_events[lifecycle_log_count] = event;
	lifecycle_log_count++;
	lifecycle_note(21);
}

static void reset_rusage_trace(void)
{
	memset(&rusage_cpu_info, 0, sizeof(rusage_cpu_info));
	rusage_cpu_info.ncpus = 6;
	rusage_get_cpu_info_null = 0;
	rusage_get_cpu_info_count = 0;
	rusage_nr_nodes_count = 0;
	rusage_nr_nodes_value = 5;
	rusage_ns_count = 0;
	rusage_ns_value = 77;
	rusage_virt_to_phys_count = 0;
	rusage_virt_to_phys_arg = NULL;
	rusage_virt_to_phys_value = 0xabc000UL;
	rusage_set_count = 0;
	rusage_set_phys = 0;
	rusage_set_size = 0;
	rusage_set_rc = 0;
	rusage_panic_count = 0;
	rusage_log_count = 0;
	rusage_log_total = 0;
}

static struct ihk_mc_cpu_info *fake_rusage_get_cpu_info(void)
{
	rusage_get_cpu_info_count++;
	return rusage_get_cpu_info_null ? NULL : &rusage_cpu_info;
}

static int fake_rusage_nr_nodes(void)
{
	rusage_nr_nodes_count++;
	return rusage_nr_nodes_value;
}

static unsigned long fake_rusage_ns_per_tsc(void)
{
	rusage_ns_count++;
	return rusage_ns_value;
}

static unsigned long fake_rusage_virt_to_phys(void *ptr)
{
	rusage_virt_to_phys_count++;
	rusage_virt_to_phys_arg = ptr;
	return rusage_virt_to_phys_value;
}

static int fake_rusage_set(unsigned long phys, unsigned long size)
{
	rusage_set_count++;
	rusage_set_phys = phys;
	rusage_set_size = size;
	return rusage_set_rc;
}

static void fake_rusage_panic(void)
{
	rusage_panic_count++;
}

static void fake_rusage_log(unsigned long total_memory)
{
	rusage_log_count++;
	rusage_log_total = total_memory;
}

static void *fake_register_debug_alloc(int size, unsigned long flag)
{
	(void)size;
	(void)flag;
	return (void *)0xd00dUL;
}

static void fake_register_debug_free(void *ptr)
{
	(void)ptr;
}

static void *fake_register_base_alloc(int size, unsigned long flag)
{
	(void)size;
	(void)flag;
	return (void *)0xbabeUL;
}

static void fake_register_base_free(void *ptr)
{
	(void)ptr;
}

static void reset_lifecycle_trace(void)
{
	memset(lifecycle_order, 0, sizeof(lifecycle_order));
	memset(lifecycle_log_events, 0, sizeof(lifecycle_log_events));
	memset(lifecycle_flags, 0, sizeof(lifecycle_flags));
	lifecycle_order_count = 0;
	lifecycle_track_init_count = 0;
	lifecycle_early_invalidate_count = 0;
	lifecycle_set_allocator_count = 0;
	lifecycle_set_allocator_ops = NULL;
	lifecycle_set_pf_count = 0;
	lifecycle_pf_handler = 0;
	lifecycle_get_vector_count = 0;
	lifecycle_get_vector_type = 0;
	lifecycle_register_count = 0;
	lifecycle_register_vector = 0;
	lifecycle_register_handler = 0;
	lifecycle_log_count = 0;
	lifecycle_cmdline = NULL;
}

static void reset_vmap_trace(void)
{
	vmap_init_count = 0;
	vmap_init_start = 0;
	vmap_init_size = 0;
	vmap_init_unit = 0;
	vmap_prepare_count = 0;
	vmap_prepare_pt = NULL;
	vmap_prepare_virt = NULL;
	vmap_prepare_size = 0;
	vmap_prepare_flag = 0;
	vmap_prepare_rc = 0;
	vmap_alloc_count = 0;
	vmap_alloc_desc = NULL;
	vmap_alloc_npages = 0;
	vmap_alloc_p2align = -1;
	vmap_alloc_return = 0x80000000UL;
	vmap_free_count = 0;
	vmap_free_desc = NULL;
	vmap_free_addr = 0;
	vmap_free_npages = 0;
	vmap_set_count = 0;
	memset(vmap_set_pt, 0, sizeof(vmap_set_pt));
	memset(vmap_set_virt, 0, sizeof(vmap_set_virt));
	memset(vmap_set_phys, 0, sizeof(vmap_set_phys));
	memset(vmap_set_attr, 0, sizeof(vmap_set_attr));
	vmap_set_fail_at = -1;
	vmap_clear_count = 0;
	memset(vmap_clear_pt, 0, sizeof(vmap_clear_pt));
	memset(vmap_clear_virt, 0, sizeof(vmap_clear_virt));
	vmap_flush_count = 0;
	memset(vmap_flush_addr, 0, sizeof(vmap_flush_addr));
	vmap_barrier_count = 0;
}

static void *fake_vmap_pagealloc_init(unsigned long start, unsigned long size,
				      unsigned long unit)
{
	vmap_init_count++;
	vmap_init_start = start;
	vmap_init_size = size;
	vmap_init_unit = unit;
	return &vmap_allocator_token;
}

static int fake_vmap_prepare_map(void *pt, void *virt, unsigned long size,
				 int flag)
{
	vmap_prepare_count++;
	vmap_prepare_pt = pt;
	vmap_prepare_virt = virt;
	vmap_prepare_size = size;
	vmap_prepare_flag = flag;
	return vmap_prepare_rc;
}

static unsigned long fake_vmap_alloc(void *desc, int npages, int p2align)
{
	vmap_alloc_count++;
	vmap_alloc_desc = desc;
	vmap_alloc_npages = npages;
	vmap_alloc_p2align = p2align;
	return vmap_alloc_return;
}

static void fake_vmap_free(void *desc, unsigned long addr, int npages)
{
	vmap_free_count++;
	vmap_free_desc = desc;
	vmap_free_addr = addr;
	vmap_free_npages = npages;
}

static int fake_vmap_set_page(void *pt, void *virt, unsigned long phys,
			      unsigned long attr)
{
	int idx = vmap_set_count++;

	if (idx < 8) {
		vmap_set_pt[idx] = pt;
		vmap_set_virt[idx] = (unsigned long)virt;
		vmap_set_phys[idx] = phys;
		vmap_set_attr[idx] = attr;
	}
	return idx == vmap_set_fail_at ? -22 : 0;
}

static int fake_vmap_clear_page(void *pt, void *virt)
{
	int idx = vmap_clear_count++;

	if (idx < 8) {
		vmap_clear_pt[idx] = pt;
		vmap_clear_virt[idx] = (unsigned long)virt;
	}
	return 0;
}

static void fake_vmap_flush(unsigned long addr)
{
	if (vmap_flush_count < 8)
		vmap_flush_addr[vmap_flush_count] = addr;
	vmap_flush_count++;
}

static void fake_vmap_barrier(void)
{
	vmap_barrier_count++;
}

static void reset_numa_init_trace(void)
{
	numa_get_fail_node = -1;
	numa_node_init_count = 0;
	numa_add_free_count = 0;
	numa_page_allocator_count = 0;
	numa_list_allocator_count = 0;
	numa_pagealloc_count_calls = 0;
	numa_rusage_count = 0;
	numa_rusage_bytes = 0;
	numa_log_count = 0;
	numa_log_digest = 0;
	numa_panic_count = 0;
	numa_panic_node = -1;
	for (int i = 0; i < 8; i++) {
		numa_page_allocator_pages[i] = 0;
		numa_allocator_tokens[i] = 0xabc000UL + (unsigned long)i;
	}
}

static int fake_numa_get_node_info(int node, int *linux_numa_id, int *type)
{
	if (node == numa_get_fail_node)
		return -1;
	if (linux_numa_id)
		*linux_numa_id = 100 + node;
	if (type)
		*type = 10 + node;
	return 0;
}

static void fake_numa_node_init(struct fake_numa_node *node,
				int rbtree_allocator)
{
	if (numa_node_init_count < 8) {
		numa_node_init_ids[numa_node_init_count] =
			node ? node->id : -1;
		numa_node_init_rbtree[numa_node_init_count] =
			rbtree_allocator;
	}
	if (node)
		node->min_addr = (unsigned long)rbtree_allocator;
	numa_node_init_count++;
}

static void fake_numa_add_free_pages(struct fake_numa_node *node,
				     unsigned long start, unsigned long len)
{
	if (numa_add_free_count < 8) {
		numa_add_free_nodes[numa_add_free_count] =
			node ? node->id : -1;
		numa_add_free_starts[numa_add_free_count] = start;
		numa_add_free_lens[numa_add_free_count] = len;
	}
	numa_add_free_count++;
}

static void *fake_numa_page_allocator_init(unsigned long start,
					   unsigned long end)
{
	int idx = numa_page_allocator_count;

	if (idx < 8) {
		numa_page_allocator_starts[idx] = start;
		numa_page_allocator_ends[idx] = end;
		numa_page_allocator_pages[idx] = (end - start) >> PAGE_SHIFT;
	}
	numa_page_allocator_count++;
	return idx < 8 ? &numa_allocator_tokens[idx] : NULL;
}

static void fake_numa_list_allocator(void *allocator,
				     struct fake_numa_node *node)
{
	if (numa_list_allocator_count < 8) {
		numa_list_allocator_nodes[numa_list_allocator_count] =
			node ? node->id : -1;
		numa_list_allocator_tokens[numa_list_allocator_count] =
			allocator ? *(unsigned long *)allocator : 0;
	}
	numa_list_allocator_count++;
}

static unsigned long fake_numa_pagealloc_count(void *allocator)
{
	numa_pagealloc_count_calls++;
	for (int i = 0; i < 8; i++) {
		if (allocator == &numa_allocator_tokens[i])
			return numa_page_allocator_pages[i];
	}
	return 0;
}

static void fake_numa_rusage_total_add(unsigned long bytes)
{
	numa_rusage_count++;
	numa_rusage_bytes += bytes;
}

static void fake_numa_log(int event, int node, int linux_numa_id, int type,
			  unsigned long start, unsigned long end,
			  unsigned long bytes, int pages, int rbtree_allocator)
{
	numa_log_count++;
	mix(&numa_log_digest, (unsigned long)event);
	mix_signed(&numa_log_digest, node);
	mix_signed(&numa_log_digest, linux_numa_id);
	mix_signed(&numa_log_digest, type);
	mix(&numa_log_digest, start ^ end ^ bytes);
	mix_signed(&numa_log_digest, pages);
	mix_signed(&numa_log_digest, rbtree_allocator);
}

static void fake_numa_panic(int node)
{
	numa_panic_count++;
	numa_panic_node = node;
}

static void reset_distance_trace(void)
{
	memset(distance_storage, 0, sizeof(distance_storage));
	memset(distance_matrix, 0, sizeof(distance_matrix));
	memset(distance_alloc_npages, 0, sizeof(distance_alloc_npages));
	memset(distance_alloc_flags, 0, sizeof(distance_alloc_flags));
	memset(distance_alloc_fail_logs, 0, sizeof(distance_alloc_fail_logs));
	memset(distance_log_nodes, 0, sizeof(distance_log_nodes));
	distance_alloc_count = 0;
	distance_alloc_fail_index = -1;
	distance_alloc_fail_count = 0;
	distance_log_count = 0;
	distance_log_digest = 0x64697374616e6365UL;
}

static struct node_distance *fake_distance_alloc(int npages,
						 unsigned long flag)
{
	int idx = distance_alloc_count++;

	if (idx < 8) {
		distance_alloc_npages[idx] = npages;
		distance_alloc_flags[idx] = flag;
	}
	if (idx == distance_alloc_fail_index)
		return NULL;
	return idx < 8 ? distance_storage[idx] : NULL;
}

static int fake_distance_get(int from, int to)
{
	if (from < 0 || from >= 8 || to < 0 || to >= 8)
		return -1;
	return distance_matrix[from][to];
}

static void fake_distance_alloc_fail_log(int node)
{
	if (distance_alloc_fail_count < 8)
		distance_alloc_fail_logs[distance_alloc_fail_count] = node;
	distance_alloc_fail_count++;
}

static void fake_distance_log(int node, struct node_distance *distances,
			      int nr_nodes)
{
	if (distance_log_count < 8)
		distance_log_nodes[distance_log_count] = node;
	distance_log_count++;
	mix(&distance_log_digest, (unsigned long)node);
	mix(&distance_log_digest, (unsigned long)nr_nodes);
	for (int i = 0; i < nr_nodes; i++) {
		mix(&distance_log_digest, (unsigned long)distances[i].id);
		mix(&distance_log_digest,
		    (unsigned long)distances[i].distance);
	}
}

static void reset_topology_trace(void)
{
	memset(topology_oom_nodes, 0, sizeof(topology_oom_nodes));
	memset(topology_alloc_node_ids, 0, sizeof(topology_alloc_node_ids));
	memset(topology_alloc_returns, 0, sizeof(topology_alloc_returns));
	topology_oom_count = 0;
	topology_alloc_count = 0;
	topology_alloc_npages = 0;
	topology_alloc_p2align = 0;
	topology_nr_nodes = 0;
	topology_nr_nodes_count = 0;
	topology_current_node = 0;
	topology_current_count = 0;
}

static int fake_topology_check_oom(int numa_id, int npages, int is_user)
{
	if (topology_oom_count < 8)
		topology_oom_nodes[topology_oom_count] =
			numa_id * 10000 + npages * 10 + is_user;
	topology_oom_count++;
	return topology_alloc_returns[numa_id] == 0xdeadUL ? -12 : 0;
}

static unsigned long fake_topology_alloc(struct fake_numa_node *node,
					 int npages, int p2align)
{
	int idx = topology_alloc_count++;

	if (idx < 8)
		topology_alloc_node_ids[idx] = node ? node->id : -1;
	topology_alloc_npages = npages;
	topology_alloc_p2align = p2align;
	if (!node || node->id < 0 || node->id >= 8)
		return 0;
	return topology_alloc_returns[node->id];
}

static int fake_topology_current_node(void)
{
	topology_current_count++;
	return topology_current_node;
}

static int fake_topology_nr_nodes(void)
{
	topology_nr_nodes_count++;
	return topology_nr_nodes;
}

static struct ihk_dump_page *dump_page_at(struct ihk_dump_page *page, int idx)
{
	for (int i = 0; i < idx; i++) {
		page = (struct ihk_dump_page *)((char *)page +
			sizeof(struct ihk_dump_page) +
			page->map_count * sizeof(unsigned long));
	}
	return page;
}

static void reset_dump_trace(void)
{
	memset(dump_storage, 0, sizeof(dump_storage));
	memset(&dump_page_set, 0, sizeof(dump_page_set));
	memset(dump_free_counts, 0, sizeof(dump_free_counts));
	memset(dump_chunks, 0, sizeof(dump_chunks));
	memset(dump_rb_chunks, 0, sizeof(dump_rb_chunks));
	for (int i = 0; i < 4; i++)
		dump_first_index[i] = -1;
	dump_get_set_count = 0;
	dump_get_page_count = 0;
	dump_query_user_count = 0;
	dump_query_free_count = 0;
	dump_log_count = 0;
	dump_warn_count = 0;
	dump_first_count = 0;
	dump_next_count = 0;
	dump_warn_digest = 0x64756d7070616765UL;

	struct ihk_dump_page *page0 = (struct ihk_dump_page *)dump_storage;
	page0->start = 0x100000;
	page0->map_count = 2;
	page0->map[0] = ~0UL;
	page0->map[1] = ~0UL;

	struct ihk_dump_page *page1 = dump_page_at(page0, 1);
	page1->start = 0x200000;
	page1->map_count = 1;
	page1->map[0] = ~0UL;

	dump_page_set.count = 2;
	dump_page_set.page_size = sizeof(dump_storage);
}

static struct ihk_dump_page_set *fake_dump_get_page_set(void)
{
	dump_get_set_count++;
	return &dump_page_set;
}

static struct ihk_dump_page *fake_dump_get_page(void)
{
	dump_get_page_count++;
	return (struct ihk_dump_page *)dump_storage;
}

static void fake_dump_query_user(void *arg)
{
	struct dump_pase_info *info = arg;
	dump_query_user_count++;
	require(info->dump_page_set == &dump_page_set);
	require(info->dump_pages == (struct ihk_dump_page *)dump_storage);
}

static void fake_dump_query_free(void *arg)
{
	struct dump_pase_info *info = arg;
	dump_query_free_count++;
	require(info->dump_page_set == &dump_page_set);
	require(info->dump_pages == (struct ihk_dump_page *)dump_storage);
}

static void fake_dump_log(void)
{
	dump_log_count++;
}

static void fake_dump_warn(int kind, unsigned long map_count,
			   unsigned long map_index, unsigned long map_start,
			   unsigned long map_end, unsigned long page_index)
{
	dump_warn_count++;
	mix(&dump_warn_digest, (unsigned long)kind);
	mix(&dump_warn_digest, map_count);
	mix(&dump_warn_digest, map_index);
	mix(&dump_warn_digest, map_start);
	mix(&dump_warn_digest, map_end);
	mix(&dump_warn_digest, page_index);
}

static void dump_init_list_head(struct list_head *head)
{
	head->next = head;
	head->prev = head;
}

static void dump_list_add_tail(struct list_head *node, struct list_head *head)
{
	struct list_head *prev = head->prev;
	node->next = head;
	node->prev = prev;
	prev->next = node;
	head->prev = node;
}

static void reset_dump_user_trace(void)
{
	for (int i = 0; i < 4; i++)
		dump_init_list_head(&dump_process_hash[i]);
	memset(dump_processes, 0, sizeof(dump_processes));
	memset(dump_vms, 0, sizeof(dump_vms));
	memset(dump_spaces, 0, sizeof(dump_spaces));
	memset(dump_page_tables, 0, sizeof(dump_page_tables));
	dump_query_digest = 0x7175657279757365UL;
	dump_visit_count = 0;
	dump_pte_visitor_count = 0;
	dump_last_arg = NULL;

	for (int i = 0; i < 5; i++) {
		dump_page_tables[i] = 0x5000UL + (unsigned long)i * 0x1000UL;
		dump_spaces[i].page_table = &dump_page_tables[i];
		dump_vms[i].address_space = &dump_spaces[i];
		dump_processes[i].tag = i;
	}

	dump_processes[0].vm = &dump_vms[0];
	dump_processes[1].vm = NULL;
	dump_processes[2].vm = &dump_vms[2];
	dump_spaces[2].page_table = NULL;
	dump_processes[3].vm = &dump_vms[3];
	dump_processes[4].vm = &dump_vms[4];
	dump_vms[4].address_space = NULL;

	dump_list_add_tail(&dump_processes[0].hash_list, &dump_process_hash[0]);
	dump_list_add_tail(&dump_processes[1].hash_list, &dump_process_hash[0]);
	dump_list_add_tail(&dump_processes[2].hash_list, &dump_process_hash[1]);
	dump_list_add_tail(&dump_processes[3].hash_list, &dump_process_hash[2]);
	dump_list_add_tail(&dump_processes[4].hash_list, &dump_process_hash[3]);
}

static int fake_dump_pte_visitor(void *arg, void *pt, unsigned long *ptep,
				 void *pgaddr, int pgshift)
{
	unsigned long pt_index = 999;

	dump_pte_visitor_count++;
	dump_last_arg = arg;
	for (unsigned long i = 0; i < 5; i++) {
		if (pt == &dump_page_tables[i]) {
			pt_index = i;
			break;
		}
	}
	mix(&dump_query_digest, pt_index);
	mix(&dump_query_digest, ptep ? *ptep : 0);
	mix(&dump_query_digest, pgaddr ? 1 : 0);
	mix(&dump_query_digest, (unsigned long)pgshift);
	return 0;
}

static int fake_dump_visit_pte_range(void *pt, void *start, void *end,
				     int pgshift, int flags,
				     int (*funcp)(void *, void *,
					     unsigned long *, void *, int),
				     void *arg)
{
	unsigned long pte = 0xabcd0000UL + (unsigned long)dump_visit_count;

	dump_visit_count++;
	require(start == NULL);
	require(end == (void *)USER_END);
	require(pgshift == 0);
	require(flags == 0);
	require(funcp == fake_dump_pte_visitor);
	return funcp(arg, pt, &pte, start, 12 + dump_visit_count);
}

static unsigned long fake_dump_free_pages(int node)
{
	return (node >= 0 && node < 4) ? (unsigned long)dump_free_counts[node] : 0;
}

static void *fake_dump_first_chunk(int node)
{
	dump_first_count++;
	if (node < 0 || node >= 4 || dump_first_index[node] < 0)
		return NULL;
	return &dump_chunks[dump_first_index[node]];
}

static void *fake_dump_next_chunk(void *chunk)
{
	struct fake_free_chunk *c = chunk;
	dump_next_count++;
	if (!c || c->next < 0)
		return NULL;
	return &dump_chunks[c->next];
}

static unsigned long fake_dump_chunk_addr(void *chunk)
{
	return ((struct fake_free_chunk *)chunk)->addr;
}

static unsigned long fake_dump_chunk_size(void *chunk)
{
	return ((struct fake_free_chunk *)chunk)->size;
}

static int fake_dump_chk_page_address(unsigned long phys)
{
	return mem_chk_page_address_result(phys, fake_get_nr_chunks,
					   ihk_mc_get_memory_chunk);
}

static void reset_fault_lookup_trace(void)
{
	memset(fault_lookup_ptes, 0, sizeof(fault_lookup_ptes));
	memset(fault_lookup_pts, 0, sizeof(fault_lookup_pts));
	memset(fault_lookup_virts, 0, sizeof(fault_lookup_virts));
	memset(fault_lookup_pgshifts, 0, sizeof(fault_lookup_pgshifts));
	memset(fault_lookup_baseps, 0, sizeof(fault_lookup_baseps));
	memset(fault_lookup_sizeps, 0, sizeof(fault_lookup_sizeps));
	memset(fault_lookup_p2alignps, 0, sizeof(fault_lookup_p2alignps));
	fault_lookup_count = 0;
	fault_page_fault_count = 0;
	fault_page_fault_vm = NULL;
	fault_page_fault_virt = NULL;
	fault_page_fault_reason = 0;
	fault_page_fault_rc = 0;
	fault_log_count = 0;
	fault_log_virt = NULL;
	fault_phys_to_nid_count = 0;
	fault_phys_to_nid_phys = 0;
	fault_phys_to_nid_result = 4;
}

static unsigned long *fake_lookup_fault_pte(void *pt, void *virt, int pgshift,
					    void **basep, size_t *sizep,
					    int *p2alignp)
{
	int index = fault_lookup_count++;

	fault_lookup_pts[index] = pt;
	fault_lookup_virts[index] = virt;
	fault_lookup_pgshifts[index] = pgshift;
	fault_lookup_baseps[index] = basep;
	fault_lookup_sizeps[index] = sizep;
	fault_lookup_p2alignps[index] = p2alignp;
	if (index >= 4)
		return NULL;
	return &fault_lookup_ptes[index];
}

static int fake_fault_process_vm(void *vm, void *virt, unsigned long reason)
{
	fault_page_fault_count++;
	fault_page_fault_vm = vm;
	fault_page_fault_virt = virt;
	fault_page_fault_reason = reason;
	return fault_page_fault_rc;
}

static void fake_fault_log(void *virt)
{
	fault_log_count++;
	fault_log_virt = virt;
}

static int fake_fault_phys_to_nid(unsigned long phys)
{
	fault_phys_to_nid_count++;
	fault_phys_to_nid_phys = phys;
	return fault_phys_to_nid_result;
}

#ifdef MEM_INIT_C_FALLBACK
int mem_set_page_allocator_result(struct ihk_mc_pa_ops **pa_ops_slot,
				  struct ihk_mc_pa_ops *ops,
				  void (*pagealloc_track_init_fn)(void),
				  void (*early_alloc_invalidate_fn)(void))
{
	if (!pa_ops_slot || !pagealloc_track_init_fn ||
	    !early_alloc_invalidate_fn)
		return -22;
	pagealloc_track_init_fn();
	early_alloc_invalidate_fn();
	*pa_ops_slot = ops;
	return 0;
}

int mem_rusage_init_body_result(struct rusage_global *rusage,
				unsigned long rusage_size,
				struct ihk_mc_cpu_info *(*get_cpu_info_fn)(void),
				int (*nr_numa_nodes_fn)(void),
				unsigned long (*ns_per_tsc_fn)(void),
				unsigned long (*virt_to_phys_fn)(void *),
				int (*set_rusage_fn)(unsigned long,
						      unsigned long),
				void (*panic_fn)(void),
				void (*log_fn)(unsigned long))
{
	struct ihk_mc_cpu_info *cpu_info;
	int rc;

	if (!rusage || !get_cpu_info_fn || !nr_numa_nodes_fn ||
	    !ns_per_tsc_fn || !virt_to_phys_fn || !set_rusage_fn)
		return -22;

	cpu_info = get_cpu_info_fn();
	if (!cpu_info) {
		if (panic_fn)
			panic_fn();
		return -22;
	}

	memset(rusage, 0, sizeof(*rusage));
	rusage->num_processors = cpu_info->ncpus;
	rusage->num_numa_nodes = nr_numa_nodes_fn();
	rusage->ns_per_tsc = ns_per_tsc_fn();
	rc = set_rusage_fn(virt_to_phys_fn(rusage), rusage_size);
	if (log_fn)
		log_fn(rusage->total_memory);
	return rc;
}

int mem_register_kmalloc_result(struct ihk_mc_pa_ops *allocator,
				int memdebug_present,
				void *(*debug_alloc_fn)(int, unsigned long),
				void (*debug_free_fn)(void *),
				void *(*base_alloc_fn)(int, unsigned long),
				void (*base_free_fn)(void *))
{
	if (!allocator)
		return -22;
	if (memdebug_present) {
		if (!debug_alloc_fn || !debug_free_fn)
			return -22;
		allocator->alloc = debug_alloc_fn;
		allocator->free = debug_free_fn;
	} else {
		if (!base_alloc_fn || !base_free_fn)
			return -22;
		allocator->alloc = base_alloc_fn;
		allocator->free = base_free_fn;
	}
	return 0;
}

int mem_virtual_allocator_init_body_result(void **vmap_allocator_slot,
		unsigned long start, unsigned long size, unsigned long unit,
		int first_level,
		void *(*pagealloc_init_fn)(unsigned long, unsigned long,
					   unsigned long),
		int (*pt_prepare_map_fn)(void *, void *, unsigned long, int))
{
	if (!vmap_allocator_slot || !pagealloc_init_fn || !pt_prepare_map_fn)
		return -22;
	*vmap_allocator_slot = pagealloc_init_fn(start, size, unit);
	return pt_prepare_map_fn(NULL, (void *)start, size, first_level);
}

void *mem_map_virtual_body_result(void *vmap_allocator, unsigned long phys,
				  int npages, unsigned long attr,
				  unsigned long (*pagealloc_alloc_fn)(void *,
					int, int),
				  int (*pt_set_page_fn)(void *, void *,
					unsigned long, unsigned long),
				  int (*pt_clear_page_fn)(void *, void *),
				  void (*pagealloc_free_fn)(void *,
					unsigned long, int),
				  void (*flush_tlb_single_fn)(unsigned long),
				  void (*barrier_fn)(void))
{
	unsigned long offset;
	unsigned long aligned_phys;
	unsigned long va;

	if (!vmap_allocator || npages < 0 || !pagealloc_alloc_fn ||
	    !pt_set_page_fn || !pt_clear_page_fn || !pagealloc_free_fn ||
	    !flush_tlb_single_fn || !barrier_fn)
		return NULL;

	offset = phys & (PAGE_SIZE - 1);
	aligned_phys = phys & PAGE_MASK;
	va = pagealloc_alloc_fn(vmap_allocator, npages, 0);
	if (!va)
		return NULL;

	for (int i = 0; i < npages; i++) {
		unsigned long page_va = va + ((unsigned long)i << PAGE_SHIFT);
		unsigned long page_phys =
			aligned_phys + ((unsigned long)i << PAGE_SHIFT);
		if (pt_set_page_fn(NULL, (void *)page_va, page_phys, attr)) {
			for (int j = 0; j < i; j++) {
				unsigned long clear_va =
					va + ((unsigned long)j << PAGE_SHIFT);
				pt_clear_page_fn(NULL, (void *)clear_va);
			}
			pagealloc_free_fn(vmap_allocator, va, npages);
			return NULL;
		}
		flush_tlb_single_fn(page_va);
	}
	barrier_fn();
	return (void *)(va + offset);
}

int mem_unmap_virtual_body_result(void *vmap_allocator, void *va, int npages,
				  int (*pt_clear_page_fn)(void *, void *),
				  void (*flush_tlb_single_fn)(unsigned long),
				  void (*pagealloc_free_fn)(void *,
					unsigned long, int))
{
	unsigned long base;

	if (!vmap_allocator || !va || npages < 0 || !pt_clear_page_fn ||
	    !flush_tlb_single_fn || !pagealloc_free_fn)
		return -22;

	base = (unsigned long)va & PAGE_MASK;
	for (int i = 0; i < npages; i++) {
		unsigned long page_va = base + ((unsigned long)i << PAGE_SHIFT);
		pt_clear_page_fn(NULL, (void *)page_va);
		flush_tlb_single_fn(page_va);
	}
	pagealloc_free_fn(vmap_allocator, base, npages);
	return 0;
}

static void mem_init_check_command_c(int *flag, char *name,
				     char *(*find_command_line_fn)(char *),
				     void (*log_fn)(int), int event)
{
	if (!flag)
		return;
	if (find_command_line_fn(name)) {
		*flag = 1;
		if (log_fn)
			log_fn(event);
	}
}

int mem_init_sequence_result(struct ihk_mc_pa_ops *allocator_ops,
			     unsigned long page_fault_handler_addr,
			     unsigned long query_free_mem_handler_addr,
			     int *anon_on_demand_flag, int *xpmem_remote_flag,
			     int *hugetlbfs_on_demand_flag,
			     void (*monitor_init_fn)(void),
			     void (*rusage_init_fn)(void),
			     void (*numa_init_fn)(void),
			     void (*set_page_allocator_fn)(struct ihk_mc_pa_ops *),
			     void (*set_page_fault_handler_fn)(unsigned long),
			     int (*get_vector_fn)(int),
			     int (*register_interrupt_handler_fn)(int,
								  unsigned long),
			     void (*page_init_fn)(void),
			     void (*virtual_allocator_init_fn)(void),
			     char *(*find_command_line_fn)(char *),
			     void (*numa_distances_init_fn)(void),
			     void (*log_fn)(int))
{
	int vector;
	int register_rc;

	if (!monitor_init_fn || !rusage_init_fn || !numa_init_fn ||
	    !set_page_allocator_fn || !set_page_fault_handler_fn ||
	    !get_vector_fn || !register_interrupt_handler_fn ||
	    !page_init_fn || !virtual_allocator_init_fn ||
	    !find_command_line_fn || !numa_distances_init_fn)
		return -22;

	monitor_init_fn();
	rusage_init_fn();
	numa_init_fn();
	set_page_allocator_fn(allocator_ops);
	set_page_fault_handler_fn(page_fault_handler_addr);
	vector = get_vector_fn(2);
	register_rc = register_interrupt_handler_fn(vector,
						   query_free_mem_handler_addr);
	page_init_fn();
	virtual_allocator_init_fn();
	mem_init_check_command_c(anon_on_demand_flag, "anon_on_demand",
				 find_command_line_fn, log_fn,
				 MEM_INIT_LOG_ANON_ON_DEMAND);
	mem_init_check_command_c(xpmem_remote_flag,
				 "xpmem_page_in_remote_on_attach",
				 find_command_line_fn, log_fn,
				 MEM_INIT_LOG_XPMEM_PAGE_IN_REMOTE);
	mem_init_check_command_c(hugetlbfs_on_demand_flag,
				 "hugetlbfs_on_demand",
				 find_command_line_fn, log_fn,
				 MEM_INIT_LOG_HUGETLBFS_ON_DEMAND);
	numa_distances_init_fn();
	return register_rc;
	}

	int mem_numa_distances_init_result(struct fake_numa_node *memory_nodes,
			int nr_nodes,
			struct node_distance *(*alloc_pages_fn)(int,
								unsigned long),
			int (*get_distance_fn)(int, int),
			void (*alloc_fail_log_fn)(int),
			void (*distances_log_fn)(int, struct node_distance *, int))
	{
		int npages;

		if (!memory_nodes || nr_nodes < 0 || !alloc_pages_fn ||
		    !get_distance_fn || !alloc_fail_log_fn || !distances_log_fn)
			return -22;
		if (nr_nodes == 0)
			return 0;

		npages = (sizeof(struct node_distance) * nr_nodes + 4095) >> 12;
		for (int i = 0; i < nr_nodes; i++) {
			struct node_distance *distances =
				alloc_pages_fn(npages, IHK_MC_AP_NOWAIT);
			int swapped = 1;

			memory_nodes[i].nodes_by_distance = distances;
			if (!distances) {
				alloc_fail_log_fn(i);
				continue;
			}

			for (int j = 0; j < nr_nodes; j++) {
				distances[j].id = j;
				distances[j].distance = get_distance_fn(i, j);
			}

			while (swapped) {
				swapped = 0;
				for (int j = 1; j < nr_nodes; j++) {
					if ((distances[j - 1].distance >
							distances[j].distance) ||
					    ((distances[j - 1].distance ==
							distances[j].distance) &&
					     (distances[j - 1].id > distances[j].id))) {
						struct node_distance tmp =
							distances[j - 1];
						distances[j - 1] = distances[j];
						distances[j] = tmp;
						swapped = 1;
					}
				}
			}
			distances_log_fn(i, distances, nr_nodes);
		}
		return 0;
	}

	int mem_numa_distances_init_public_result(
			struct fake_numa_node *memory_nodes,
			int (*nr_nodes_fn)(void),
			struct node_distance *(*alloc_pages_fn)(int,
								unsigned long),
			int (*get_distance_fn)(int, int),
			void (*alloc_fail_log_fn)(int),
			void (*distances_log_fn)(int, struct node_distance *, int))
	{
		if (!nr_nodes_fn)
			return -22;

		return mem_numa_distances_init_result(memory_nodes, nr_nodes_fn(),
				alloc_pages_fn, get_distance_fn, alloc_fail_log_fn,
				distances_log_fn);
	}

	#endif

static unsigned long mem_runtime_orchestration_digest(void)
{
	struct ihk_mc_pa_ops ops = { fake_alloc_page, fake_free_page, NULL, NULL };
	struct list_head pending = { NULL, NULL };
	struct page page0 = { 0 };
	struct page page1 = { 0 };
	struct page bad = { 0 };
	struct fake_numa_node numa_nodes[4] = { 0 };
	struct fake_numa_node distance_nodes[4] = { 0 };
	struct mem_chunk free_chunks[] = {
		{ 0x100000, 0x104000, 2 },
		{ 0x200000, 0x208000, 4 },
	};
	struct rusage_global fake_rusage;
	unsigned long digest = 0x6d656d72756e2121UL;
	unsigned long mask;
	unsigned long interleave_mask[4];
	void *ptr;
	int il_prev;
	int rc;
	struct ihk_mc_pa_ops *ops_slot = NULL;

	reset_lifecycle_trace();
	rc = mem_set_page_allocator_result(&ops_slot, &ops,
					   fake_lifecycle_track_init,
					   fake_lifecycle_early_invalidate);
	require(rc == 0);
	require(ops_slot == &ops);
	require(lifecycle_track_init_count == 1);
	require(lifecycle_early_invalidate_count == 1);
	require(lifecycle_order_count == 2);
	require(lifecycle_order[0] == 1);
	require(lifecycle_order[1] == 2);
	mix(&digest, (unsigned long)lifecycle_track_init_count);
	mix(&digest, (unsigned long)lifecycle_early_invalidate_count);
	mix(&digest, (unsigned long)(ops_slot == &ops));

	memset(&fake_rusage, 0xa5, sizeof(fake_rusage));
	reset_rusage_trace();
	rc = mem_rusage_init_body_result(&fake_rusage, sizeof(fake_rusage),
		fake_rusage_get_cpu_info, fake_rusage_nr_nodes,
		fake_rusage_ns_per_tsc, fake_rusage_virt_to_phys,
		fake_rusage_set, fake_rusage_panic, fake_rusage_log);
	require(rc == 0);
	require(fake_rusage.num_processors == 6);
	require(fake_rusage.num_numa_nodes == 5);
	require(fake_rusage.ns_per_tsc == 77);
	require(fake_rusage.memory_stat_rss[0] == 0);
	require(fake_rusage.memory_numa_stat[3] == 0);
	require(fake_rusage.cpu[2].system_tsc == 0);
	require(rusage_get_cpu_info_count == 1);
	require(rusage_nr_nodes_count == 1);
	require(rusage_ns_count == 1);
	require(rusage_virt_to_phys_count == 1);
	require(rusage_virt_to_phys_arg == &fake_rusage);
	require(rusage_set_count == 1);
	require(rusage_set_phys == 0xabc000UL);
	require(rusage_set_size == sizeof(fake_rusage));
	require(rusage_panic_count == 0);
	require(rusage_log_count == 1);
	require(rusage_log_total == 0);
	mix(&digest, fake_rusage.num_processors);
	mix(&digest, fake_rusage.num_numa_nodes);
	mix(&digest, fake_rusage.ns_per_tsc);
	mix(&digest, rusage_set_size);

	reset_rusage_trace();
	rusage_get_cpu_info_null = 1;
	rusage_set_rc = -5;
	rc = mem_rusage_init_body_result(&fake_rusage, sizeof(fake_rusage),
		fake_rusage_get_cpu_info, fake_rusage_nr_nodes,
		fake_rusage_ns_per_tsc, fake_rusage_virt_to_phys,
		fake_rusage_set, fake_rusage_panic, fake_rusage_log);
	require(rc == -22);
	require(rusage_panic_count == 1);
	require(rusage_set_count == 0);
	require(rusage_log_count == 0);
	mix_signed(&digest, rc);
	mix(&digest, (unsigned long)rusage_panic_count);

	ops.alloc = NULL;
	ops.free = NULL;
	rc = mem_register_kmalloc_result(&ops, 0, fake_register_debug_alloc,
					 fake_register_debug_free,
					 fake_register_base_alloc,
					 fake_register_base_free);
	require(rc == 0);
	require(ops.alloc == fake_register_base_alloc);
	require(ops.free == fake_register_base_free);
	mix_signed(&digest, rc);
	mix(&digest, (unsigned long)(ops.alloc == fake_register_base_alloc));
	ops.alloc = NULL;
	ops.free = NULL;
	rc = mem_register_kmalloc_result(&ops, 1, fake_register_debug_alloc,
					 fake_register_debug_free,
					 fake_register_base_alloc,
					 fake_register_base_free);
	require(rc == 0);
	require(ops.alloc == fake_register_debug_alloc);
	require(ops.free == fake_register_debug_free);
	mix(&digest, (unsigned long)(ops.free == fake_register_debug_free));

	{
		void *vmap_slot = NULL;

		reset_vmap_trace();
		rc = mem_virtual_allocator_init_body_result(&vmap_slot,
			0x10000000UL, 0x20000UL, PAGE_SIZE, 7,
			fake_vmap_pagealloc_init, fake_vmap_prepare_map);
		require(rc == 0);
		require(vmap_slot == &vmap_allocator_token);
		require(vmap_init_count == 1);
		require(vmap_init_start == 0x10000000UL);
		require(vmap_init_size == 0x20000UL);
		require(vmap_init_unit == PAGE_SIZE);
		require(vmap_prepare_count == 1);
		require(vmap_prepare_pt == NULL);
		require(vmap_prepare_virt == (void *)0x10000000UL);
		require(vmap_prepare_size == 0x20000UL);
		require(vmap_prepare_flag == 7);
		mix(&digest, (unsigned long)vmap_init_count);
		mix(&digest, vmap_prepare_size);

		reset_vmap_trace();
		vmap_alloc_return = 0x80000000UL;
		ptr = mem_map_virtual_body_result(&vmap_allocator_token,
			0x12345UL, 3, 0x8000000000000055UL, fake_vmap_alloc,
			fake_vmap_set_page, fake_vmap_clear_page,
			fake_vmap_free, fake_vmap_flush, fake_vmap_barrier);
		require(ptr == (void *)0x80000345UL);
		require(vmap_alloc_count == 1);
		require(vmap_alloc_desc == &vmap_allocator_token);
		require(vmap_alloc_npages == 3);
		require(vmap_alloc_p2align == 0);
		require(vmap_set_count == 3);
		require(vmap_set_virt[0] == 0x80000000UL);
		require(vmap_set_virt[2] == 0x80002000UL);
		require(vmap_set_phys[0] == 0x12000UL);
		require(vmap_set_phys[2] == 0x14000UL);
		require(vmap_set_attr[1] == 0x8000000000000055UL);
		require(vmap_clear_count == 0);
		require(vmap_flush_count == 3);
		require(vmap_flush_addr[2] == 0x80002000UL);
		require(vmap_barrier_count == 1);
		require(vmap_free_count == 0);
		mix(&digest, (unsigned long)vmap_set_count);
		mix(&digest, vmap_set_phys[2]);
		mix(&digest, (unsigned long)vmap_barrier_count);

		reset_vmap_trace();
		vmap_alloc_return = 0;
		ptr = mem_map_virtual_body_result(&vmap_allocator_token,
			0x20000UL, 2, 0x33, fake_vmap_alloc,
			fake_vmap_set_page, fake_vmap_clear_page,
			fake_vmap_free, fake_vmap_flush, fake_vmap_barrier);
		require(ptr == NULL);
		require(vmap_alloc_count == 1);
		require(vmap_set_count == 0);
		require(vmap_free_count == 0);
		require(vmap_barrier_count == 0);
		mix(&digest, (unsigned long)vmap_alloc_count);

		reset_vmap_trace();
		vmap_alloc_return = 0x90000000UL;
		vmap_set_fail_at = 1;
		ptr = mem_map_virtual_body_result(&vmap_allocator_token,
			0x45678UL, 3, 0x66, fake_vmap_alloc,
			fake_vmap_set_page, fake_vmap_clear_page,
			fake_vmap_free, fake_vmap_flush, fake_vmap_barrier);
		require(ptr == NULL);
		require(vmap_set_count == 2);
		require(vmap_set_phys[0] == 0x45000UL);
		require(vmap_clear_count == 1);
		require(vmap_clear_virt[0] == 0x90000000UL);
		require(vmap_free_count == 1);
		require(vmap_free_addr == 0x90000000UL);
		require(vmap_free_npages == 3);
		require(vmap_flush_count == 1);
		require(vmap_barrier_count == 0);
		mix(&digest, (unsigned long)vmap_clear_count);
		mix(&digest, vmap_free_addr);

		reset_vmap_trace();
		rc = mem_unmap_virtual_body_result(&vmap_allocator_token,
			(void *)0x80000345UL, 2, fake_vmap_clear_page,
			fake_vmap_flush, fake_vmap_free);
		require(rc == 0);
		require(vmap_clear_count == 2);
		require(vmap_clear_virt[0] == 0x80000000UL);
		require(vmap_clear_virt[1] == 0x80001000UL);
		require(vmap_flush_count == 2);
		require(vmap_flush_addr[1] == 0x80001000UL);
		require(vmap_free_count == 1);
		require(vmap_free_addr == 0x80000000UL);
		require(vmap_free_npages == 2);
		mix_signed(&digest, rc);
		mix(&digest, (unsigned long)vmap_flush_count);
	}

	reset_lifecycle_trace();
	lifecycle_cmdline = "root=/dev/test anon_on_demand "
		"xpmem_page_in_remote_on_attach hugetlbfs_on_demand";
	rc = mem_init_sequence_result(&ops, 0x11110000UL, 0x22220000UL,
		&lifecycle_flags[0], &lifecycle_flags[1], &lifecycle_flags[2],
		fake_lifecycle_monitor, fake_lifecycle_rusage,
		fake_lifecycle_numa, fake_lifecycle_set_allocator,
		fake_lifecycle_set_page_fault, fake_lifecycle_get_vector,
		fake_lifecycle_register_interrupt, fake_lifecycle_page_init,
		fake_lifecycle_virtual_allocator, fake_lifecycle_find_command,
		fake_lifecycle_numa_distances, fake_lifecycle_log);
	require(rc == 0);
	require(lifecycle_order_count == 16);
	require(lifecycle_order[0] == 10);
	require(lifecycle_order[1] == 11);
	require(lifecycle_order[2] == 12);
	require(lifecycle_order[3] == 13);
	require(lifecycle_order[4] == 14);
	require(lifecycle_order[5] == 15);
	require(lifecycle_order[6] == 16);
	require(lifecycle_order[7] == 17);
	require(lifecycle_order[8] == 18);
	require(lifecycle_order[9] == 19);
	require(lifecycle_order[10] == 21);
	require(lifecycle_order[11] == 19);
	require(lifecycle_order[12] == 21);
	require(lifecycle_order[13] == 19);
	require(lifecycle_order[14] == 21);
	require(lifecycle_order[15] == 20);
	require(lifecycle_set_allocator_count == 1);
	require(lifecycle_set_allocator_ops == &ops);
	require(lifecycle_set_pf_count == 1);
	require(lifecycle_pf_handler == 0x11110000UL);
	require(lifecycle_get_vector_count == 1);
	require(lifecycle_get_vector_type == 2);
	require(lifecycle_register_count == 1);
	require(lifecycle_register_vector == 42);
	require(lifecycle_register_handler == 0x22220000UL);
	require(lifecycle_flags[0] == 1);
	require(lifecycle_flags[1] == 1);
	require(lifecycle_flags[2] == 1);
	require(lifecycle_log_count == 3);
	require(lifecycle_log_events[0] == MEM_INIT_LOG_ANON_ON_DEMAND);
	require(lifecycle_log_events[1] == MEM_INIT_LOG_XPMEM_PAGE_IN_REMOTE);
	require(lifecycle_log_events[2] == MEM_INIT_LOG_HUGETLBFS_ON_DEMAND);
	mix(&digest, (unsigned long)lifecycle_order_count);
	mix(&digest, (unsigned long)lifecycle_register_vector);
	mix(&digest, (unsigned long)lifecycle_log_count);

	reset_lifecycle_trace();
	lifecycle_cmdline = "root=/dev/test";
	rc = mem_init_sequence_result(&ops, 0xaaaaUL, 0xbbbbUL,
		&lifecycle_flags[0], &lifecycle_flags[1], NULL,
		fake_lifecycle_monitor, fake_lifecycle_rusage,
		fake_lifecycle_numa, fake_lifecycle_set_allocator,
		fake_lifecycle_set_page_fault, fake_lifecycle_get_vector,
		fake_lifecycle_register_interrupt, fake_lifecycle_page_init,
		fake_lifecycle_virtual_allocator, fake_lifecycle_find_command,
		fake_lifecycle_numa_distances, fake_lifecycle_log);
	require(rc == 0);
	require(lifecycle_flags[0] == 0);
	require(lifecycle_flags[1] == 0);
	require(lifecycle_log_count == 0);
	require(lifecycle_order_count == 12);
	require(lifecycle_order[9] == 19);
	require(lifecycle_order[10] == 19);
	require(lifecycle_order[11] == 20);
	mix(&digest, (unsigned long)lifecycle_order_count);
	mix(&digest, (unsigned long)lifecycle_log_count);

	{
		struct mem_chunk numa_chunks[] = {
			{ 0x1000, 0x5000, 1 },
			{ 0x8000, 0xc000, 2 },
			{ 0xd000, 0xe000, 8 },
		};

		memset(numa_nodes, 0, sizeof(numa_nodes));
		set_chunks(numa_chunks, 3);
		reset_numa_init_trace();
		rc = mem_numa_init_body_result(numa_nodes, 3, 3, 1,
			0x3000, fake_numa_get_node_info,
			ihk_mc_get_memory_chunk, fake_numa_node_init,
			fake_numa_add_free_pages,
			fake_numa_page_allocator_init,
			fake_numa_list_allocator,
			fake_numa_pagealloc_count,
			fake_numa_rusage_total_add, fake_numa_log,
			fake_numa_panic);
		require(rc == 0);
		require(numa_node_init_count == 3);
		require(numa_nodes[0].id == 0);
		require(numa_nodes[1].linux_numa_id == 101);
		require(numa_nodes[2].type == 12);
		require(numa_nodes[0].allocators.next == &numa_nodes[0].allocators);
		require(numa_nodes[2].nodes_by_distance == NULL);
		require(numa_node_init_ids[2] == 2);
		require(numa_node_init_rbtree[0] == 1);
		require(numa_add_free_count == 2);
		require(numa_add_free_nodes[0] == 1);
		require(numa_add_free_starts[0] == 0x3000);
		require(numa_add_free_lens[0] == 0x2000);
		require(numa_add_free_nodes[1] == 2);
		require(numa_page_allocator_count == 0);
		require(numa_rusage_count == 2);
		require(numa_rusage_bytes == 0x6000);
		require(numa_log_count == 5);
		mix_signed(&digest, rc);
		mix(&digest, numa_rusage_bytes);
		mix(&digest, numa_log_digest);
		mix_signed(&digest, numa_add_free_count);

		memset(numa_nodes, 0, sizeof(numa_nodes));
		set_chunks(numa_chunks, 2);
		reset_numa_init_trace();
		rc = mem_numa_init_body_result(numa_nodes, 3, 2, 0,
			0, fake_numa_get_node_info,
			ihk_mc_get_memory_chunk, fake_numa_node_init,
			fake_numa_add_free_pages,
			fake_numa_page_allocator_init,
			fake_numa_list_allocator,
			fake_numa_pagealloc_count,
			fake_numa_rusage_total_add, fake_numa_log,
			fake_numa_panic);
		require(rc == 0);
		require(numa_add_free_count == 0);
		require(numa_page_allocator_count == 2);
		require(numa_page_allocator_starts[0] == 0x1000);
		require(numa_page_allocator_ends[1] == 0xc000);
		require(numa_list_allocator_count == 2);
		require(numa_list_allocator_nodes[0] == 1);
		require(numa_pagealloc_count_calls == 2);
		require(numa_rusage_bytes == 0x8000);
		require(numa_log_count == 5);
		mix(&digest, numa_rusage_bytes);
		mix(&digest, numa_log_digest);
		mix_signed(&digest, numa_page_allocator_count);

		memset(numa_nodes, 0, sizeof(numa_nodes));
		reset_numa_init_trace();
		numa_get_fail_node = 1;
		rc = mem_numa_init_body_result(numa_nodes, 3, 0, 1,
			0, fake_numa_get_node_info,
			ihk_mc_get_memory_chunk, fake_numa_node_init,
			fake_numa_add_free_pages,
			fake_numa_page_allocator_init,
			fake_numa_list_allocator,
			fake_numa_pagealloc_count,
			fake_numa_rusage_total_add, fake_numa_log,
			fake_numa_panic);
		require(rc == -22);
		require(numa_panic_count == 1);
		require(numa_panic_node == 1);
		require(numa_node_init_count == 1);
			mix_signed(&digest, rc);
			mix_signed(&digest, numa_panic_node);
		}

	require(sizeof(struct fake_numa_node) == 256);
	require(offsetof(struct fake_numa_node, nodes_by_distance) == 32);
	require(offsetof(struct fake_numa_node, free_chunks) == 64);
	require(offsetof(struct fake_numa_node, nr_free_pages) == 200);
	reset_distance_trace();
	distance_matrix[0][0] = 30;
	distance_matrix[0][1] = 10;
	distance_matrix[0][2] = 10;
	distance_matrix[1][0] = 40;
	distance_matrix[1][1] = 5;
	distance_matrix[1][2] = 20;
	distance_matrix[2][0] = 7;
	distance_matrix[2][1] = 7;
	distance_matrix[2][2] = 3;
	rc = mem_numa_distances_init_result(distance_nodes, 3,
		fake_distance_alloc, fake_distance_get,
		fake_distance_alloc_fail_log, fake_distance_log);
	require(rc == 0);
	require(distance_alloc_count == 3);
	require(distance_alloc_npages[0] == 1);
	require(distance_alloc_flags[0] == IHK_MC_AP_NOWAIT);
	require(distance_nodes[0].nodes_by_distance == distance_storage[0]);
	require(distance_nodes[1].nodes_by_distance == distance_storage[1]);
	require(distance_nodes[2].nodes_by_distance == distance_storage[2]);
	require(distance_storage[0][0].id == 1);
	require(distance_storage[0][1].id == 2);
	require(distance_storage[0][2].id == 0);
	require(distance_storage[1][0].id == 1);
	require(distance_storage[1][1].id == 2);
	require(distance_storage[1][2].id == 0);
	require(distance_storage[2][0].id == 2);
	require(distance_storage[2][1].id == 0);
	require(distance_storage[2][2].id == 1);
	require(distance_log_count == 3);
	require(distance_alloc_fail_count == 0);
	mix(&digest, (unsigned long)distance_alloc_count);
	mix(&digest, distance_log_digest);

	memset(distance_nodes, 0, sizeof(distance_nodes));
	reset_distance_trace();
	reset_topology_trace();
	topology_nr_nodes = 3;
	distance_matrix[0][0] = 9;
	distance_matrix[0][1] = 4;
	distance_matrix[0][2] = 8;
	distance_matrix[1][0] = 7;
	distance_matrix[1][1] = 6;
	distance_matrix[1][2] = 5;
	distance_matrix[2][0] = 3;
	distance_matrix[2][1] = 2;
	distance_matrix[2][2] = 1;
	rc = mem_numa_distances_init_public_result(distance_nodes,
		fake_topology_nr_nodes, fake_distance_alloc,
		fake_distance_get, fake_distance_alloc_fail_log,
		fake_distance_log);
	require(rc == 0);
	require(topology_nr_nodes_count == 1);
	require(distance_alloc_count == 3);
	require(distance_storage[0][0].id == 1);
	require(distance_storage[2][0].id == 2);
	rc = mem_numa_distances_init_public_result(distance_nodes,
		NULL, fake_distance_alloc, fake_distance_get,
		fake_distance_alloc_fail_log, fake_distance_log);
	require(rc == -22);
	require(topology_nr_nodes_count == 1);
	mix(&digest, (unsigned long)topology_nr_nodes_count);
	mix(&digest, distance_log_digest);

	memset(distance_nodes, 0, sizeof(distance_nodes));
	reset_distance_trace();
	distance_alloc_fail_index = 1;
	distance_matrix[0][0] = 2;
	distance_matrix[0][1] = 1;
	distance_matrix[2][0] = 3;
	distance_matrix[2][1] = 4;
	rc = mem_numa_distances_init_result(distance_nodes, 3,
		fake_distance_alloc, fake_distance_get,
		fake_distance_alloc_fail_log, fake_distance_log);
	require(rc == 0);
	require(distance_alloc_count == 3);
	require(distance_nodes[0].nodes_by_distance == distance_storage[0]);
	require(distance_nodes[1].nodes_by_distance == NULL);
	require(distance_nodes[2].nodes_by_distance == distance_storage[2]);
	require(distance_alloc_fail_count == 1);
	require(distance_alloc_fail_logs[0] == 1);
	require(distance_log_count == 2);
	require(distance_log_nodes[0] == 0);
	require(distance_log_nodes[1] == 2);
	mix(&digest, (unsigned long)distance_alloc_fail_count);
	mix(&digest, distance_log_digest);

	memset(distance_nodes, 0, sizeof(distance_nodes));
	for (int i = 0; i < 4; i++)
		distance_nodes[i].id = i;
	reset_topology_trace();
	topology_alloc_returns[2] = 0x220000;
	{
		int oom = 99;
		unsigned long pa = mem_try_alloc_node_result(distance_nodes, 4,
			2, 6, 3, 1, &oom, fake_topology_check_oom,
			fake_topology_alloc);
		require(pa == 0x220000);
		require(oom == 0);
		require(topology_oom_count == 1);
		require(topology_alloc_count == 1);
		require(topology_alloc_node_ids[0] == 2);
		require(topology_alloc_npages == 6);
		require(topology_alloc_p2align == 3);
		mix(&digest, pa);
		mix(&digest, (unsigned long)topology_alloc_node_ids[0]);
	}

	reset_topology_trace();
	topology_alloc_returns[1] = 0xdeadUL;
	{
		int oom = 0;
		unsigned long pa = mem_try_alloc_node_result(distance_nodes, 4,
			1, 5, 0, 0, &oom, fake_topology_check_oom,
			fake_topology_alloc);
		require(pa == 0);
		require(oom == 1);
		require(topology_oom_count == 1);
		require(topology_alloc_count == 0);
		mix(&digest, (unsigned long)oom);
	}

	{
		int oom = 77;
		unsigned long pa = mem_try_alloc_node_result(distance_nodes, 4,
			7, 5, 0, 0, &oom, fake_topology_check_oom,
			fake_topology_alloc);
		require(pa == 0);
		require(oom == 0);
		require(topology_oom_count == 1);
		require(topology_alloc_count == 0);
		mix(&digest, (unsigned long)oom);
	}

	reset_topology_trace();
	topology_nr_nodes = 4;
	topology_alloc_returns[1] = 0x330000;
	{
		int oom = 55;
		unsigned long pa = mem_try_alloc_node_public_result(distance_nodes,
			1, 4, 2, 1, &oom, fake_topology_nr_nodes,
			fake_topology_check_oom, fake_topology_alloc);
		require(pa == 0x330000);
		require(oom == 0);
		require(topology_nr_nodes_count == 1);
		require(topology_oom_count == 1);
		require(topology_alloc_count == 1);
		require(topology_alloc_node_ids[0] == 1);
		mix(&digest, pa);
		mix(&digest, (unsigned long)topology_nr_nodes_count);

		oom = 66;
		pa = mem_try_alloc_node_public_result(distance_nodes, 1, 4, 2, 1,
			&oom, NULL, fake_topology_check_oom,
			fake_topology_alloc);
		require(pa == 0);
		require(oom == 0);
		require(topology_nr_nodes_count == 1);
		mix(&digest, (unsigned long)oom);
	}

	distance_storage[0][0].id = 3;
	distance_storage[0][1].id = 1;
	distance_nodes[0].nodes_by_distance = distance_storage[0];
	require(mem_distance_id_result(distance_nodes, 4, 0, 0) == 3);
	require(mem_distance_id_result(distance_nodes, 4, 0, 1) == 1);
	require(mem_distance_id_result(distance_nodes, 4, -1, 0) == -1);
	require(mem_distance_id_result(distance_nodes, 4, 2, 0) == -1);
	require(mem_distance_id_result(distance_nodes, 4, 0, 4) == -1);
	mix(&digest, (unsigned long)mem_distance_id_result(distance_nodes, 4,
		0, 1));
	reset_topology_trace();
	topology_nr_nodes = 4;
	require(mem_distance_id_public_result(distance_nodes, 0, 0,
		fake_topology_nr_nodes) == 3);
	require(topology_nr_nodes_count == 1);
	require(mem_distance_id_public_result(distance_nodes, 0, 0, NULL) == -1);
	require(topology_nr_nodes_count == 1);
	mix(&digest, (unsigned long)topology_nr_nodes_count);

	reset_topology_trace();
	topology_current_node = 0;
	ptr = mem_get_numa_node_by_distance_result(distance_nodes, 4, 1, 0,
		fake_topology_current_node);
	require(ptr == &distance_nodes[3]);
	require(topology_current_count == 1);
	ptr = mem_get_numa_node_by_distance_result(distance_nodes, 4, 0, 0,
		fake_topology_current_node);
	require(ptr == NULL);
	ptr = mem_get_numa_node_by_distance_result(distance_nodes, 4, 1, 4,
		fake_topology_current_node);
	require(ptr == NULL);
	distance_storage[0][0].id = 9;
	ptr = mem_get_numa_node_by_distance_result(distance_nodes, 4, 1, 0,
		fake_topology_current_node);
	require(ptr == NULL);
	mix(&digest, (unsigned long)topology_current_count);

	distance_storage[0][0].id = 3;
	reset_topology_trace();
	topology_current_node = 0;
	topology_nr_nodes = 4;
	ptr = mem_get_numa_node_by_distance_public_result(distance_nodes, 1, 0,
		fake_topology_nr_nodes, fake_topology_current_node);
	require(ptr == &distance_nodes[3]);
	require(topology_nr_nodes_count == 1);
	require(topology_current_count == 1);
	ptr = mem_get_numa_node_by_distance_public_result(distance_nodes, 1, 0,
		NULL, fake_topology_current_node);
	require(ptr == NULL);
	require(topology_nr_nodes_count == 1);
	ptr = mem_get_numa_node_public_result(distance_nodes, 4, 2);
	require(ptr == &distance_nodes[2]);
	ptr = mem_get_numa_node_public_result(distance_nodes, 4, 4);
	require(ptr == NULL);
	mix(&digest, (unsigned long)topology_nr_nodes_count);
	mix(&digest, (unsigned long)topology_current_count);

	reset_dump_trace();
	struct dump_pase_info dump_info = {
		.dump_page_set = &dump_page_set,
		.dump_pages = (struct ihk_dump_page *)dump_storage,
	};
	struct ihk_dump_page *dump0 = (struct ihk_dump_page *)dump_storage;
	struct ihk_dump_page *dump1 = dump_page_at(dump0, 1);

	set_chunks(free_chunks, 2);
	require(mem_chk_page_address_result(0x201000, fake_get_nr_chunks,
		ihk_mc_get_memory_chunk) == 0);
	require(mem_chk_page_address_result(0x300000, fake_get_nr_chunks,
		ihk_mc_get_memory_chunk) == -1);
	mix(&digest, (unsigned long)mem_chk_page_address_result(0x201000,
		fake_get_nr_chunks, ihk_mc_get_memory_chunk));

	dump_page_set.completion_flag = IHK_DUMP_PAGE_SET_COMPLETED;
	rc = mem_clear_dump_page_completion_result(fake_dump_get_page_set);
	require(rc == 0);
	require(dump_page_set.completion_flag == IHK_DUMP_PAGE_SET_INCOMPLETE);
	require(dump_get_set_count == 1);
	mix(&digest, (unsigned long)dump_page_set.completion_flag);

	rc = mem_dump_mark_range_result(&dump_info, 0x101000, 0x3000, 0,
		fake_dump_warn);
	require(rc == 3);
	require((dump0->map[0] & (1UL << 1)) == 0);
	require((dump0->map[0] & (1UL << 2)) == 0);
	require((dump0->map[0] & (1UL << 3)) == 0);
	require(dump_warn_count == 0);
	mix(&digest, (unsigned long)rc);
	mix(&digest, dump0->map[0]);

	unsigned long pte = 0x200000 | PTATTR_ACTIVE | PTATTR_USER;
	rc = mem_get_mem_user_page_result(&dump_info, &pte, 13,
		fake_dump_chk_page_address, fake_dump_warn);
	require(rc == 0);
	require((dump1->map[0] & (1UL << 0)) == 0);
	require((dump1->map[0] & (1UL << 1)) == 0);
	mix(&digest, dump1->map[0]);

	pte = 0x204000 | PTATTR_ACTIVE;
	unsigned long before = dump1->map[0];
	mem_get_mem_user_page_result(&dump_info, &pte, 12,
		fake_dump_chk_page_address, fake_dump_warn);
	require(dump1->map[0] == before);
	mix(&digest, before);

	reset_dump_trace();
	dump_info.dump_page_set = &dump_page_set;
	dump_info.dump_pages = (struct ihk_dump_page *)dump_storage;
	dump_free_counts[0] = 2;
	dump_first_index[0] = 0;
	dump_chunks[0].addr = 0x100000;
	dump_chunks[0].size = 0x2000;
	dump_chunks[0].next = 1;
	dump_chunks[1].addr = 0x200000;
	dump_chunks[1].size = 0x1000;
	dump_chunks[1].next = -1;
	rc = mem_query_mem_free_page_result(&dump_info, 2,
		fake_dump_free_pages, fake_dump_first_chunk,
		fake_dump_next_chunk, fake_dump_chunk_addr,
		fake_dump_chunk_size, fake_dump_warn);
	require(rc == 3);
	dump0 = (struct ihk_dump_page *)dump_storage;
	dump1 = dump_page_at(dump0, 1);
	require((dump0->map[0] & (1UL << 0)) == 0);
	require((dump0->map[0] & (1UL << 1)) == 0);
	require((dump1->map[0] & (1UL << 0)) == 0);
	require(dump_first_count == 2);
	require(dump_next_count == 2);
	mix(&digest, (unsigned long)rc);
	mix(&digest, dump0->map[0]);
	mix(&digest, dump1->map[0]);

	reset_dump_trace();
	reset_topology_trace();
	dump_info.dump_page_set = &dump_page_set;
	dump_info.dump_pages = (struct ihk_dump_page *)dump_storage;
	topology_nr_nodes = 2;
	dump_free_counts[0] = 2;
	dump_first_index[0] = 0;
	dump_chunks[0].addr = 0x100000;
	dump_chunks[0].size = 0x1000;
	dump_chunks[0].next = 1;
	dump_chunks[1].addr = 0x200000;
	dump_chunks[1].size = 0x1000;
	dump_chunks[1].next = -1;
	rc = mem_query_mem_free_page_public_result(&dump_info,
		fake_topology_nr_nodes, fake_dump_free_pages,
		fake_dump_first_chunk, fake_dump_next_chunk,
		fake_dump_chunk_addr, fake_dump_chunk_size, fake_dump_warn);
	require(rc == 2);
	require(topology_nr_nodes_count == 1);
	require(dump_first_count == 2);
	rc = mem_query_mem_free_page_public_result(&dump_info, NULL,
		fake_dump_free_pages, fake_dump_first_chunk,
		fake_dump_next_chunk, fake_dump_chunk_addr,
		fake_dump_chunk_size, fake_dump_warn);
	require(rc == -22);
	require(topology_nr_nodes_count == 1);
	mix(&digest, (unsigned long)topology_nr_nodes_count);
	mix(&digest, (unsigned long)dump_first_count);

	reset_dump_trace();
	const struct mem_chunk safe_rb_chunks[] = {
		{ 0, ~0UL, 0 },
	};
	set_chunks(safe_rb_chunks,
		sizeof(safe_rb_chunks) / sizeof(safe_rb_chunks[0]));
	reset_topology_trace();
	struct fake_numa_node dump_nodes[2] = { 0 };
	topology_nr_nodes = 2;
	dump_nodes[1].nr_free_pages = 7;
	dump_nodes[1].free_chunks.rb_node = &dump_rb_chunks[0].node;
	dump_rb_chunks[0].addr = 0x300000;
	dump_rb_chunks[0].size = 0x2000;
	dump_rb_chunks[0].node.__rb_parent_color = 0;
	dump_rb_chunks[0].node.rb_left = NULL;
	dump_rb_chunks[0].node.rb_right = &dump_rb_chunks[1].node;
	dump_rb_chunks[1].addr = 0x400000;
	dump_rb_chunks[1].size = 0x1000;
	dump_rb_chunks[1].node.__rb_parent_color =
		(unsigned long)&dump_rb_chunks[0].node;
	dump_rb_chunks[1].node.rb_left = NULL;
	dump_rb_chunks[1].node.rb_right = NULL;
	require(mem_dump_free_pages_public_result(dump_nodes, 1,
		fake_topology_nr_nodes) == 7);
	void *rb_chunk = mem_dump_first_free_chunk_public_result(dump_nodes, 1,
		fake_topology_nr_nodes);
	require(rb_chunk == &dump_rb_chunks[0]);
	require(mem_dump_chunk_addr_result(rb_chunk) == 0x300000);
	require(mem_dump_chunk_size_result(rb_chunk) == 0x2000);
	rb_chunk = mem_dump_next_free_chunk_result(rb_chunk);
	require(rb_chunk == &dump_rb_chunks[1]);
	require(mem_dump_chunk_addr_result(rb_chunk) == 0x400000);
	require(mem_dump_chunk_size_result(rb_chunk) == 0x1000);
	require(mem_dump_next_free_chunk_result(rb_chunk) == NULL);
	require(mem_dump_first_free_chunk_public_result(dump_nodes, -1,
		fake_topology_nr_nodes) == NULL);
	require(mem_dump_free_pages_public_result(dump_nodes, 2,
		fake_topology_nr_nodes) == 0);
	require(mem_dump_free_pages_public_result(NULL, 1,
		fake_topology_nr_nodes) == 0);
	require(mem_dump_first_free_chunk_public_result(dump_nodes, 1,
		NULL) == NULL);
	require(mem_dump_next_free_chunk_result(NULL) == NULL);
	require(mem_dump_chunk_addr_result(NULL) == 0);
	require(mem_dump_chunk_size_result(NULL) == 0);
	mix(&digest, mem_dump_free_pages_public_result(dump_nodes, 1,
		fake_topology_nr_nodes));
	mix(&digest, mem_dump_chunk_addr_result(&dump_rb_chunks[1]));
	mix(&digest, (unsigned long)topology_nr_nodes_count);

	reset_dump_user_trace();
	rc = mem_query_mem_user_page_result(dump_process_hash, 4,
		offsetof(struct fake_process, hash_list),
		offsetof(struct fake_process, vm),
		offsetof(struct fake_process_vm, address_space),
		offsetof(struct fake_address_space, page_table),
		USER_END, fake_dump_visit_pte_range,
		fake_dump_pte_visitor, &dump_info);
	require(rc == 2);
	require(dump_visit_count == 2);
	require(dump_pte_visitor_count == 2);
	require(dump_last_arg == &dump_info);
	mix(&digest, (unsigned long)rc);
	mix(&digest, dump_query_digest);
	require(mem_query_mem_user_page_result(NULL, 4,
		offsetof(struct fake_process, hash_list),
		offsetof(struct fake_process, vm),
		offsetof(struct fake_process_vm, address_space),
		offsetof(struct fake_address_space, page_table),
		USER_END, fake_dump_visit_pte_range,
		fake_dump_pte_visitor, &dump_info) == 0);
	require(mem_query_mem_user_page_result(dump_process_hash, 4,
		offsetof(struct fake_process, hash_list),
		offsetof(struct fake_process, vm),
		offsetof(struct fake_process_vm, address_space),
		offsetof(struct fake_address_space, page_table),
		USER_END, NULL, fake_dump_pte_visitor, &dump_info) == -22);

	reset_dump_trace();
	dump_page_set.count = 2;
	rc = mem_query_mem_areas_result(0, 2, DUMP_LEVEL_USER_UNUSED_EXCLUDE,
		fake_dump_get_page_set, fake_dump_get_page,
		fake_dump_query_user, fake_dump_query_free, fake_dump_log);
	require(rc == 0);
	require(dump_get_set_count == 0);
	require(dump_page_set.completion_flag == 0);
	rc = mem_query_mem_areas_result(1, 2, DUMP_LEVEL_USER_UNUSED_EXCLUDE,
		fake_dump_get_page_set, fake_dump_get_page,
		fake_dump_query_user, fake_dump_query_free, fake_dump_log);
	require(rc == 1);
	require(dump_get_set_count == 1);
	require(dump_get_page_count == 1);
	require(dump_query_user_count == 1);
	require(dump_query_free_count == 1);
	require(dump_log_count == 1);
	require(dump_page_set.completion_flag == IHK_DUMP_PAGE_SET_COMPLETED);
		mix(&digest, (unsigned long)dump_log_count);
		mix(&digest, (unsigned long)dump_page_set.completion_flag);

		{
			struct fake_tlb_address_space as = { 0 };
			struct fake_tlb_process_vm vm = { .address_space = &as };
			struct fake_tlb_flush_entry entries[4] = { 0 };
			unsigned long addrs[2] = { 0x12345007UL, 0x12346011UL };
			unsigned long full_addr[1] = { 0 };

			require(offsetof(struct fake_tlb_address_space, cpu_set) == 32);
			require(offsetof(struct fake_tlb_address_space, cpu_set_lock) == 160);
			require(offsetof(struct fake_tlb_address_space, nslots) == 164);
			require(sizeof(struct fake_tlb_address_space) == 168);
			require(offsetof(struct fake_tlb_flush_entry, addr) == 8);
			require(offsetof(struct fake_tlb_flush_entry, nr_addr) == 16);
			require(offsetof(struct fake_tlb_flush_entry, pending) == 20);
			require(offsetof(struct fake_tlb_flush_entry, lock) == 24);
			require(sizeof(struct fake_tlb_flush_entry) == 64);

			reset_tlb_trace();
			as.cpu_set.bits[0] = (1UL << 0) | (1UL << 2) | (1UL << 5);
			tlb_current_cpu = 2;
			tlb_atomic_read_remaining = 2;
			rc = mem_remote_flush_tlb_array_body_result(&vm, addrs, 2, 99,
				entries, 4, 32, 64, fake_tlb_rdtsc,
				fake_tlb_current_cpu, fake_tlb_get_vector,
				fake_tlb_interrupt_cpu, fake_tlb_lock,
				fake_tlb_unlock, fake_tlb_atomic_set,
				fake_tlb_atomic_inc, fake_tlb_atomic_read,
				fake_tlb_flush_single, fake_tlb_flush_all,
				fake_tlb_pause);
			require(rc == 1);
			require(entries[1].vm == &vm);
			require(entries[1].addr == addrs);
			require(entries[1].nr_addr == 2);
			require(tlb_lock_count == 2);
			require(tlb_unlock_count == 2);
			require(tlb_lock_addr[0] == (unsigned long)&as.cpu_set_lock);
			require(tlb_lock_addr[1] == (unsigned long)&entries[1].lock);
			require(tlb_atomic_set_addr == (unsigned long)&entries[1].pending);
			require(tlb_atomic_set_value == 0);
			require(tlb_atomic_inc_count == 2);
			require(tlb_interrupt_count == 2);
			require(tlb_interrupt_cpu[0] == 0);
			require(tlb_interrupt_cpu[1] == 5);
			require(tlb_get_vector_arg[0] == 33);
			require(tlb_interrupt_vector[0] == 0x80 + 33);
			require(tlb_flush_single_count == 2);
			require(tlb_flush_single_addr[0] == 0x12345000UL);
			require(tlb_flush_single_addr[1] == 0x12346000UL);
			require(tlb_flush_all_count == 0);
			require(tlb_atomic_read_count == 3);
			require(tlb_pause_count == 2);
			mix(&digest, (unsigned long)tlb_interrupt_count);
			mix(&digest, tlb_flush_single_addr[1]);

			reset_tlb_trace();
			memset(entries, 0, sizeof(entries));
			as.cpu_set.bits[0] = (1UL << 1);
			tlb_current_cpu = 1;
			tlb_rdtsc_value = 7;
			rc = mem_remote_flush_tlb_array_body_result(&vm, full_addr, 1, 0,
				entries, 4, 32, 64, fake_tlb_rdtsc,
				fake_tlb_current_cpu, fake_tlb_get_vector,
				fake_tlb_interrupt_cpu, fake_tlb_lock,
				fake_tlb_unlock, fake_tlb_atomic_set,
				fake_tlb_atomic_inc, fake_tlb_atomic_read,
				fake_tlb_flush_single, fake_tlb_flush_all,
				fake_tlb_pause);
			require(rc == 3);
			require(entries[3].addr == full_addr);
			require(tlb_interrupt_count == 0);
			require(tlb_flush_single_count == 0);
			require(tlb_flush_all_count == 1);
			require(tlb_atomic_read_count == 1);
			require(mem_remote_flush_tlb_array_body_result(NULL, full_addr, 1,
				0, entries, 4, 32, 64, fake_tlb_rdtsc,
				fake_tlb_current_cpu, fake_tlb_get_vector,
				fake_tlb_interrupt_cpu, fake_tlb_lock,
				fake_tlb_unlock, fake_tlb_atomic_set,
				fake_tlb_atomic_inc, fake_tlb_atomic_read,
				fake_tlb_flush_single, fake_tlb_flush_all,
				fake_tlb_pause) == -22);

			reset_tlb_trace();
			entries[2].addr = addrs;
			entries[2].nr_addr = 2;
			entries[2].pending.counter = 3;
			rc = mem_tlb_flush_handler_body_result(34, entries, 4, 32,
				fake_tlb_irq_save, fake_tlb_irq_restore,
				fake_tlb_flush_single, fake_tlb_flush_all,
				fake_tlb_atomic_dec);
			require(rc == 0);
			require(tlb_irq_save_count == 1);
			require(tlb_irq_restore_count == 1);
			require(tlb_irq_restore_flags == 0xabcUL);
			require(tlb_flush_single_count == 2);
			require(tlb_flush_single_addr[0] == 0x12345000UL);
			require(tlb_atomic_dec_addr == (unsigned long)&entries[2].pending);
			require(entries[2].pending.counter == 2);
			mix(&digest, (unsigned long)tlb_irq_restore_flags);

			reset_tlb_trace();
			entries[0].addr = full_addr;
			entries[0].nr_addr = 1;
			entries[0].pending.counter = 1;
			rc = mem_tlb_flush_handler_body_result(32, entries, 4, 32,
				fake_tlb_irq_save, fake_tlb_irq_restore,
				fake_tlb_flush_single, fake_tlb_flush_all,
				fake_tlb_atomic_dec);
			require(rc == 0);
			require(tlb_flush_all_count == 1);
			require(tlb_flush_single_count == 0);
			require(entries[0].pending.counter == 0);
			require(mem_tlb_flush_handler_body_result(31, entries, 4, 32,
				fake_tlb_irq_save, fake_tlb_irq_restore,
				fake_tlb_flush_single, fake_tlb_flush_all,
				fake_tlb_atomic_dec) == -22);
		}

		{
			struct fake_address_space as = { .page_table = (void *)0xabc000UL };
			struct fake_process_vm vm = { .address_space = &as };
		void *base = NULL;
		size_t size = 0;
		int p2align = 0;
		unsigned long *ptep;

		reset_fault_lookup_trace();
		fault_lookup_ptes[0] = 0x222000UL | PTATTR_ACTIVE;
		ptep = mem_pt_lookup_fault_pte_body_result(&vm, (void *)0x4444UL,
			21, &base, &size, &p2align,
			offsetof(struct fake_process_vm, address_space),
			offsetof(struct fake_address_space, page_table),
			fake_lookup_fault_pte, fake_fault_process_vm,
			fake_fault_log);
		require(ptep == &fault_lookup_ptes[0]);
		require(fault_lookup_count == 1);
		require(fault_page_fault_count == 0);
		require(fault_log_count == 0);
		require(fault_lookup_pts[0] == as.page_table);
		require(fault_lookup_virts[0] == (void *)0x4444UL);
		require(fault_lookup_pgshifts[0] == 21);
		require(fault_lookup_baseps[0] == &base);
		require(fault_lookup_sizeps[0] == &size);
		require(fault_lookup_p2alignps[0] == &p2align);
		mix(&digest, fault_lookup_ptes[0]);
		mix(&digest, (unsigned long)fault_lookup_count);

		reset_fault_lookup_trace();
		fault_lookup_ptes[0] = 0;
		fault_lookup_ptes[1] = 0x333000UL | PTATTR_ACTIVE;
		ptep = mem_pt_lookup_fault_pte_body_result(&vm, (void *)0x5555UL,
			13, NULL, NULL, NULL,
			offsetof(struct fake_process_vm, address_space),
			offsetof(struct fake_address_space, page_table),
			fake_lookup_fault_pte, fake_fault_process_vm,
			fake_fault_log);
		require(ptep == &fault_lookup_ptes[1]);
		require(fault_lookup_count == 2);
		require(fault_page_fault_count == 1);
		require(fault_page_fault_vm == &vm);
		require(fault_page_fault_virt == (void *)0x5555UL);
		require(fault_page_fault_reason == (PF_POPULATE | PF_USER));
		require(fault_log_count == 1);
		require(fault_log_virt == (void *)0x5555UL);
		mix(&digest, fault_lookup_ptes[1]);
		mix(&digest, (unsigned long)fault_page_fault_reason);

		reset_fault_lookup_trace();
		fault_lookup_ptes[0] = 0;
		fault_lookup_ptes[1] = 0;
		ptep = mem_pt_lookup_fault_pte_body_result(&vm, (void *)0x6666UL,
			0, NULL, NULL, NULL,
			offsetof(struct fake_process_vm, address_space),
			offsetof(struct fake_address_space, page_table),
			fake_lookup_fault_pte, fake_fault_process_vm,
			fake_fault_log);
		require(ptep == &fault_lookup_ptes[1]);
		require(fault_lookup_count == 2);
		require(fault_page_fault_count == 1);
		require(fault_log_count == 0);
		mix(&digest, (unsigned long)fault_lookup_count);

		reset_fault_lookup_trace();
		fault_page_fault_rc = -14;
		rc = mem_lookup_node_body_result(&vm, (void *)0x7777UL,
			offsetof(struct fake_process_vm, address_space),
			offsetof(struct fake_address_space, page_table),
			fake_lookup_fault_pte, fake_fault_process_vm,
			fake_fault_phys_to_nid);
		require(rc == -14);
		require(fault_page_fault_count == 1);
		require(fault_lookup_count == 0);
		require(fault_phys_to_nid_count == 0);
		mix_signed(&digest, rc);

		reset_fault_lookup_trace();
		fault_lookup_ptes[0] = 0xabcdef000UL | PTATTR_ACTIVE;
		fault_phys_to_nid_result = 6;
		rc = mem_lookup_node_body_result(&vm, (void *)0x8888UL,
			offsetof(struct fake_process_vm, address_space),
			offsetof(struct fake_address_space, page_table),
			fake_lookup_fault_pte, fake_fault_process_vm,
			fake_fault_phys_to_nid);
		require(rc == 6);
		require(fault_page_fault_count == 1);
		require(fault_lookup_count == 1);
		require(fault_lookup_pts[0] == as.page_table);
		require(fault_lookup_virts[0] == (void *)0x8888UL);
		require(fault_lookup_pgshifts[0] == 0);
		require(fault_lookup_baseps[0] == NULL);
		require(fault_lookup_sizeps[0] == NULL);
		require(fault_lookup_p2alignps[0] == NULL);
		require(fault_phys_to_nid_count == 1);
		require(fault_phys_to_nid_phys == (0xabcdef000UL & PT_PHYSMASK));
		mix_signed(&digest, rc);
		mix(&digest, fault_phys_to_nid_phys);

		reset_fault_lookup_trace();
		fault_lookup_ptes[0] = 0;
		rc = mem_lookup_node_body_result(&vm, (void *)0x9999UL,
			offsetof(struct fake_process_vm, address_space),
			offsetof(struct fake_address_space, page_table),
			fake_lookup_fault_pte, fake_fault_process_vm,
			fake_fault_phys_to_nid);
			require(rc == -2);
			require(fault_phys_to_nid_count == 0);
			mix_signed(&digest, rc);
		}

		alloc_page_calls = early_alloc_calls = free_page_calls = 0;
	ptr = mem_pa_alloc_aligned_pages_node_result(&ops, 3, 2, 0x55, 7,
						     1, 0xfeedUL,
						     fake_early_alloc);
	require(ptr == alloc_area + 64);
	require(alloc_page_calls == 1);
	require(alloc_page_npages == 3);
	require(alloc_page_p2align == 2);
	require(alloc_page_flag == 0x55);
	require(alloc_page_node == 7);
	require(alloc_page_is_user == 1);
	require(alloc_page_virt_addr == 0xfeedUL);
	mix(&digest, (unsigned long)alloc_page_calls);
	mix(&digest, (unsigned long)alloc_page_virt_addr);

	ptr = mem_pa_alloc_pages_result(NULL, 5, 0x77, 0, fake_early_alloc);
	require(ptr == alloc_area + 128);
	require(early_alloc_calls == 1);
	require(early_alloc_npages == 5);
	mix(&digest, (unsigned long)early_alloc_calls);
	mix(&digest, (unsigned long)early_alloc_npages);

	mem_pa_free_pages_result(&ops, alloc_area + 16, 4, 1);
	require(free_page_calls == 1);
	require(free_page_ptr == alloc_area + 16);
	require(free_page_npages == 4);
	require(free_page_is_user == 1);
	mem_pa_free_pages_result(NULL, alloc_area + 24, 9, 0);
	require(free_page_calls == 1);
	mix(&digest, (unsigned long)free_page_calls);
	mix(&digest, (unsigned long)free_page_npages);

	reset_reserve_trace();
	rc = mem_reserve_pages_body_result((void *)0x1234UL, 0x1000UL,
		0x9000UL, 0, 0xa000UL, fake_reserve_log,
		fake_reserve_range);
	require(rc == 1);
	require(reserve_log_calls == 1);
	require(reserve_log_start == 0x1000UL);
	require(reserve_log_end == 0x9000UL);
	require(reserve_log_pages == 8);
	require(reserve_range_calls == 1);
	require(reserve_range_pa == (void *)0x1234UL);
	require(reserve_range_start == 0x1000UL);
	require(reserve_range_end == 0x9000UL);
	mix(&digest, (unsigned long)reserve_log_calls);
	mix(&digest, reserve_log_start);
	mix(&digest, reserve_log_end);
	mix(&digest, reserve_log_pages);
	mix(&digest, (unsigned long)reserve_range_calls);

	reset_reserve_trace();
	rc = mem_reserve_pages_body_result((void *)0x1234UL, 0x1000UL,
		0x9000UL, 0x3000UL, 0x5000UL, fake_reserve_log,
		fake_reserve_range);
	require(rc == 1);
	require(reserve_log_start == 0x3000UL);
	require(reserve_log_end == 0x5000UL);
	require(reserve_log_pages == 2);
	require(reserve_range_start == 0x3000UL);
	require(reserve_range_end == 0x5000UL);
	mix(&digest, reserve_log_pages);
	mix(&digest, reserve_range_end);

	reset_reserve_trace();
	rc = mem_reserve_pages_body_result((void *)0x1234UL, 0x1000UL,
		0x9000UL, 0x9000UL, 0xa000UL, fake_reserve_log,
		fake_reserve_range);
	require(rc == 0);
	require(reserve_log_calls == 0);
	require(reserve_range_calls == 0);
	require(mem_reserve_pages_body_result(NULL, 0x1000UL, 0x9000UL,
		0x2000UL, 0x3000UL, fake_reserve_log,
		fake_reserve_range) == -22);
	require(mem_reserve_pages_body_result((void *)0x1234UL,
		0x1000UL, 0x9000UL, 0x2000UL, 0x3000UL, NULL,
		fake_reserve_range) == -22);
	require(mem_reserve_pages_body_result((void *)0x1234UL,
		0x1000UL, 0x9000UL, 0x2000UL, 0x3000UL,
		fake_reserve_log, NULL) == -22);
	mix(&digest, 0x72657370616765UL);

	reset_reserve_trace();
	rc = mem_reserve_pages_public_body_result((void *)0x1234UL,
		0x1000UL, 0x9000UL, 0x2000UL, 0x4000UL,
		fake_reserve_log, fake_reserve_range,
		mem_reserve_pages_body_result, fake_reserve_panic);
	require(rc == 1);
	require(reserve_panic_count == 0);
	require(reserve_log_start == 0x2000UL);
	require(reserve_log_end == 0x4000UL);
	require(reserve_range_start == 0x2000UL);
	require(reserve_range_end == 0x4000UL);

	reset_reserve_trace();
	rc = mem_reserve_pages_public_body_result((void *)0x1234UL,
		0x1000UL, 0x9000UL, 0x9000UL, 0xa000UL,
		fake_reserve_log, fake_reserve_range,
		mem_reserve_pages_body_result, fake_reserve_panic);
	require(rc == 0);
	require(reserve_panic_count == 0);
	require(reserve_log_calls == 0);
	require(reserve_range_calls == 0);

	reset_reserve_trace();
	rc = mem_reserve_pages_public_body_result((void *)0x1234UL,
		0x1000UL, 0x9000UL, 0x2000UL, 0x3000UL,
		fake_reserve_log, fake_reserve_range, NULL,
		fake_reserve_panic);
	require(rc == -22);
	require(reserve_panic_count == 1);
	require(reserve_log_calls == 0);
	require(reserve_range_calls == 0);

	reset_reserve_trace();
	rc = mem_reserve_pages_public_body_result((void *)0x1234UL,
		0x1000UL, 0x9000UL, 0x2000UL, 0x3000UL,
		NULL, fake_reserve_range, mem_reserve_pages_body_result,
		fake_reserve_panic);
	require(rc == -22);
	require(reserve_panic_count == 1);
	require(reserve_log_calls == 0);
	require(reserve_range_calls == 0);
	mix(&digest, 0x72737677726170UL);

#ifndef MEM_INIT_C_FALLBACK
	alloc_page_calls = early_alloc_calls = free_page_calls = 0;
	lifecycle_track_init_count = 0;
	lifecycle_early_invalidate_count = 0;
	pagealloc_track_initialized = 0;
	ihk_mc_set_page_allocator(&ops);
	require(pagealloc_track_initialized == 1);
	require(lifecycle_early_invalidate_count == 1);
	ptr = ___ihk_mc_alloc_aligned_pages_node(6, 3, 0x88, 4, 1,
						 0xbeefUL);
	require(ptr == alloc_area + 64);
	require(alloc_page_calls == 1);
	require(alloc_page_npages == 6);
	require(alloc_page_p2align == 3);
	require(alloc_page_flag == 0x88);
	require(alloc_page_node == 4);
	require(alloc_page_is_user == 1);
	require(alloc_page_virt_addr == 0xbeefUL);
	___ihk_mc_free_pages(ptr, 6, 1);
	require(free_page_calls == 1);
	require(free_page_ptr == ptr);
	require(free_page_npages == 6);
	require(free_page_is_user == 1);
	alloc_page_calls = early_alloc_calls = free_page_calls = 0;
	ihk_mc_set_page_allocator(NULL);
	require(pagealloc_track_initialized == 1);
	require(lifecycle_early_invalidate_count == 2);
	ptr = ___ihk_mc_alloc_pages(2, 0x99, 0);
	require(ptr == alloc_area + 128);
	require(early_alloc_calls == 1);
	require(early_alloc_npages == 2);
#endif

	rc = mem_begin_free_pages_pending_result(&pending);
	require(rc == 0);
	require(pending.next == &pending);
	require(pending.prev == &pending);
	require(mem_begin_free_pages_pending_result(&pending) == -22);
	{
		struct list_head body_pending = { 0 };
		struct list_head public_begin_pending = { 0 };

		pending_panic_count = 0;
		rc = mem_begin_free_pages_pending_body_result(&body_pending,
			mem_begin_free_pages_pending_result, fake_pending_panic);
		require(rc == 0);
		require(pending_panic_count == 0);
		require(body_pending.next == &body_pending);
		require(body_pending.prev == &body_pending);
		rc = mem_begin_free_pages_pending_body_result(&body_pending,
			mem_begin_free_pages_pending_result, fake_pending_panic);
		require(rc == -22);
		require(pending_panic_count == 1);

		free_body_pending_return = &public_begin_pending;
		free_body_pending_count = 0;
		pending_panic_count = 0;
		rc = mem_begin_free_pages_pending_public_body_result(
			fake_free_body_pending_pages,
			mem_begin_free_pages_pending_result,
			fake_pending_panic);
		require(rc == 0);
		require(free_body_pending_count == 1);
		require(pending_panic_count == 0);
		require(public_begin_pending.next == &public_begin_pending);
		require(public_begin_pending.prev == &public_begin_pending);
		rc = mem_begin_free_pages_pending_public_body_result(
			fake_free_body_pending_pages,
			mem_begin_free_pages_pending_result,
			fake_pending_panic);
		require(rc == -22);
		require(free_body_pending_count == 2);
		require(pending_panic_count == 1);
		free_body_pending_return = NULL;
		pending_panic_count = 0;
		rc = mem_begin_free_pages_pending_public_body_result(
			fake_free_body_pending_pages,
			mem_begin_free_pages_pending_result,
			fake_pending_panic);
		require(rc == -22);
		require(pending_panic_count == 1);
		require(free_body_pending_count == 3);
		mix(&digest, (unsigned long)free_body_pending_count);
		mix(&digest, (unsigned long)pending_panic_count);
	}

	page0.mode = 0;
	page0.phys = 0xabc000;
	page1.mode = 7;
	page1.phys = 0xdef000;
	pending_warn_count = 0;
	require(mem_free_pages_pending_enqueue_result(&page0, &pending, 2,
						      fake_pending_warn) == 1);
	require(mem_free_pages_pending_enqueue_result(&page1, &pending, 3,
						      fake_pending_warn) == 1);
	require(pending_warn_count == 1);
	require(pending_warn_phys == page1.phys);
	require(page0.mode == 1);
	require(page0.offset == 2);
	require(page1.mode == 1);
	require(page1.offset == 3);
	mix(&digest, (unsigned long)pending_warn_count);
	mix(&digest, page0.phys);
	mix(&digest, page1.phys);

	pending_free_count = 0;
	rc = mem_finish_free_pages_pending_result(&pending, fake_pending_free);
	require(rc == 2);
	require(pending.next == NULL);
	require(pending.prev == NULL);
	require(page0.mode == 0);
	require(page1.mode == 0);
	require(pending_free_count == 2);
	require(pending_free_phys[0] == page0.phys);
	require(pending_free_npages[0] == 2);
	require(pending_free_is_user[0] == 1);
	require(pending_free_phys[1] == page1.phys);
	require(pending_free_npages[1] == 3);
	require(pending_free_is_user[1] == 1);
	mix(&digest, (unsigned long)pending_free_count);
	mix(&digest, pending_free_phys[0]);
	mix(&digest, (unsigned long)pending_free_npages[1]);

	require(mem_free_pages_pending_enqueue_result(&page0, &pending, 1,
						      fake_pending_warn) == 0);
	{
		struct list_head body_pending = { 0 };
		struct list_head public_finish_pending = { 0 };
		struct page body_page = { 0 };
		struct page body_bad = { 0 };
		struct page public_finish_page = { 0 };
		struct page public_finish_bad = { 0 };

		body_page.mode = 0;
		body_page.phys = 0x111000;
		pending_panic_count = 0;
		require(mem_begin_free_pages_pending_body_result(&body_pending,
			mem_begin_free_pages_pending_result,
			fake_pending_panic) == 0);
		require(mem_free_pages_pending_enqueue_result(&body_page,
			&body_pending, 4, fake_pending_warn) == 1);
		pending_free_count = 0;
		rc = mem_finish_free_pages_pending_body_result(&body_pending,
			mem_finish_free_pages_pending_result, fake_pending_free,
			fake_pending_panic);
		require(rc == 1);
		require(pending_panic_count == 0);
		require(pending_free_count == 1);
		require(pending_free_phys[0] == body_page.phys);
		require(pending_free_npages[0] == 4);
		require(pending_free_is_user[0] == 1);

		body_pending.next = &body_bad.list;
		body_pending.prev = &body_bad.list;
		body_bad.list.next = &body_pending;
		body_bad.list.prev = &body_pending;
		body_bad.mode = 0;
		pending_panic_count = 0;
		require(mem_finish_free_pages_pending_body_result(&body_pending,
			mem_finish_free_pages_pending_result, fake_pending_free,
			fake_pending_panic) == -22);
		require(pending_panic_count == 1);

		public_finish_pending.next = &public_finish_pending;
		public_finish_pending.prev = &public_finish_pending;
		public_finish_page.mode = 0;
		public_finish_page.phys = 0x222000;
		require(mem_free_pages_pending_enqueue_result(&public_finish_page,
			&public_finish_pending, 5, fake_pending_warn) == 1);
		free_body_pending_return = &public_finish_pending;
		free_body_pending_count = 0;
		pending_panic_count = 0;
		pending_free_count = 0;
		rc = mem_finish_free_pages_pending_public_body_result(
			fake_free_body_pending_pages,
			mem_finish_free_pages_pending_result, fake_pending_free,
			fake_pending_panic);
		require(rc == 1);
		require(free_body_pending_count == 1);
		require(pending_panic_count == 0);
		require(pending_free_count == 1);
		require(pending_free_phys[0] == public_finish_page.phys);
		require(pending_free_npages[0] == 5);

		public_finish_pending.next = &public_finish_bad.list;
		public_finish_pending.prev = &public_finish_bad.list;
		public_finish_bad.list.next = &public_finish_pending;
		public_finish_bad.list.prev = &public_finish_pending;
		public_finish_bad.mode = 0;
		free_body_pending_return = &public_finish_pending;
		pending_panic_count = 0;
		rc = mem_finish_free_pages_pending_public_body_result(
			fake_free_body_pending_pages,
			mem_finish_free_pages_pending_result, fake_pending_free,
			fake_pending_panic);
		require(rc == -22);
		require(pending_panic_count == 1);

		free_body_pending_return = NULL;
		pending_panic_count = 0;
		rc = mem_finish_free_pages_pending_public_body_result(
			fake_free_body_pending_pages,
			mem_finish_free_pages_pending_result, fake_pending_free,
			fake_pending_panic);
		require(rc == -22);
		require(pending_panic_count == 1);
		require(free_body_pending_count == 3);
		mix(&digest, (unsigned long)free_body_pending_count);
		mix(&digest, (unsigned long)pending_panic_count);
	}
	pending.next = &bad.list;
	pending.prev = &bad.list;
	bad.list.next = &pending;
	bad.list.prev = &pending;
	bad.mode = 0;
	require(mem_finish_free_pages_pending_result(&pending,
						     fake_pending_free) == -22);
	mix(&digest, (unsigned long)bad.mode);

	set_chunks(free_chunks, 2);
	for (int i = 0; i < 8; i++)
		fake_nodes[i] = NULL;
	fake_nodes[2] = alloc_area + 8;
	fake_nodes[4] = alloc_area + 32;
	fake_current_phys = 0x201000;
	numa_free_count = rusage_sub_count = 0;
	rc = mem_free_pages_in_allocator_rbtree_result((void *)0xfeed0000, 3,
		1, fake_get_nr_chunks, ihk_mc_get_memory_chunk,
		fake_virt_to_phys, fake_get_numa_node, fake_numa_free,
		fake_rusage_sub);
	require(rc == 1);
	require(numa_free_count == 1);
	require(numa_free_node == fake_nodes[4]);
	require(numa_free_addr == fake_current_phys);
	require(numa_free_npages == 3);
	require(rusage_sub_count == 1);
	require(rusage_sub_nid == 4);
	require(rusage_sub_npages == 3);
	require(rusage_sub_is_user == 1);
	mix(&digest, (unsigned long)numa_free_count);
	mix(&digest, (unsigned long)rusage_sub_nid);
	mix(&digest, numa_free_addr);

	fake_current_phys = 0x300000;
	numa_free_count = rusage_sub_count = 0;
	rc = mem_free_pages_in_allocator_rbtree_result((void *)0xbeef0000, 1,
		0, fake_get_nr_chunks, ihk_mc_get_memory_chunk,
		fake_virt_to_phys, fake_get_numa_node, fake_numa_free,
		fake_rusage_sub);
	require(rc == 0);
	require(numa_free_count == 0);
	require(rusage_sub_count == 0);
	mix(&digest, (unsigned long)rc);

	memset(interleave_mask, 0, sizeof(interleave_mask));
	interleave_mask[0] = (1UL << 1) | (1UL << 3);
	interleave_mask[1] = 1UL << 6;
	require(mem_mask_test_result(1, interleave_mask, 128) == 1);
	require(mem_mask_test_result(2, interleave_mask, 128) == 0);
	require(mem_mask_test_result(70, interleave_mask, 128) == 1);
	require(mem_mask_test_result(128, interleave_mask, 128) == 0);
	require(mem_mask_test_result(-1, interleave_mask, 128) == 0);
	require(mem_mask_test_result(1, NULL, 128) == 0);
	require(mem_mask_test_result(1, interleave_mask, 0) == 0);
	require(mem_interleave_nodes_result(-1, interleave_mask, 128) == 1);
	require(mem_interleave_nodes_result(1, interleave_mask, 128) == 3);
	require(mem_interleave_nodes_result(3, interleave_mask, 128) == 70);
	require(mem_interleave_nodes_result(70, interleave_mask, 128) == 1);
	memset(interleave_mask, 0, sizeof(interleave_mask));
	require(mem_interleave_nodes_result(7, interleave_mask, 128) == 128);
	require(mem_interleave_nodes_result(7, NULL, 128) == 128);
	require(mem_interleave_nodes_result(7, interleave_mask, 0) == 0);
	mix(&digest, 0x696c6e6f646573UL);
	mix(&digest, (unsigned long)mem_interleave_nodes_result(3, interleave_mask,
		128));

	require(mem_range_is_shm_result(0, 0, MEM_INIT_MF_SHM) == 0);
	require(mem_range_is_shm_result(1, 0, MEM_INIT_MF_SHM) == 0);
	require(mem_range_is_shm_result(1, 1, 0) == 0);
	require(mem_range_is_shm_result(1, 1, MEM_INIT_MF_SHM) == 1);
	require(mem_range_is_shm_result(1, 1, MEM_INIT_MF_SHM | 1UL) == 0);
	mix_signed(&digest, mem_range_is_shm_result(1, 1, MEM_INIT_MF_SHM));
	mix_signed(&digest, mem_range_is_shm_result(1, 1,
		MEM_INIT_MF_SHM | 1UL));

	{
		int out_policy = -9;
		int il_prev_value = 33;
		int *out_il_prev = NULL;
		unsigned long policy_mask = 0x55UL;
		unsigned long *out_mask = NULL;

		require(mem_policy_fields_result(0, MPOL_BIND, &policy_mask,
			&il_prev_value, &out_policy, &out_mask,
			&out_il_prev) == 0);
		require(out_policy == -9);
		require(out_mask == NULL);
		require(out_il_prev == NULL);
		require(mem_policy_fields_result(1, MPOL_INTERLEAVE,
			&policy_mask, &il_prev_value, &out_policy,
			&out_mask, &out_il_prev) == 1);
		require(out_policy == MPOL_INTERLEAVE);
		require(out_mask == &policy_mask);
		require(out_il_prev == &il_prev_value);
		require(mem_policy_fields_result(1, MPOL_DEFAULT, NULL, NULL,
			NULL, NULL, NULL) == 1);
		mix_signed(&digest, out_policy);
		mix(&digest, *out_mask);
		mix_signed(&digest, *out_il_prev);
	}

	require(mem_current_vm_result(0, alloc_area + 1, alloc_area + 2) == NULL);
	require(mem_current_vm_result(1, NULL, alloc_area + 2) == NULL);
	require(mem_current_vm_result(1, alloc_area + 1, NULL) == NULL);
	require(mem_current_vm_result(1, alloc_area + 1, alloc_area + 2) ==
		alloc_area + 2);
	mix(&digest, (unsigned long)((char *)mem_current_vm_result(1,
		alloc_area + 1, alloc_area + 2) - (char *)alloc_area));

	{
		unsigned long out_flag = 0xffffUL;
		int out_pref = 77;
		int out_policy = 88;

		require(mem_default_alloc_policy_result(IHK_MC_AP_USER | 0x40UL,
			&out_flag, &out_pref, &out_policy) == 1);
		require(out_flag == 0x40UL);
		require(out_pref == -1);
		require(out_policy == MPOL_DEFAULT);
		require(mem_default_alloc_policy_result(IHK_MC_AP_USER,
			NULL, NULL, NULL) == 1);
		mix(&digest, out_flag);
		mix_signed(&digest, out_pref);
		mix_signed(&digest, out_policy);
	}

	require(mem_alloc_policy_should_try_policy_result(-1, 0,
		MPOL_DEFAULT, 0) == 0);
	require(mem_alloc_policy_should_try_policy_result(0, 0,
		MPOL_DEFAULT, 0) == 1);
	require(mem_alloc_policy_should_try_policy_result(-2, 0,
		MPOL_DEFAULT, 0) == 1);
	require(mem_alloc_policy_should_try_policy_result(-1, IHK_MC_AP_USER,
		MPOL_DEFAULT, 0) == 1);
	require(mem_alloc_policy_should_try_policy_result(-1, 0,
		MPOL_BIND, 0) == 1);
	require(mem_alloc_policy_should_try_policy_result(-1, 0,
		MPOL_DEFAULT, 1) == 1);
	mix_signed(&digest, mem_alloc_policy_should_try_policy_result(-1, 0,
		MPOL_DEFAULT, 0));
	mix_signed(&digest, mem_alloc_policy_should_try_policy_result(-1,
		IHK_MC_AP_USER, MPOL_DEFAULT, 0));

	require(mem_alloc_node_id_valid_result(-1, 4) == 0);
	require(mem_alloc_node_id_valid_result(0, 4) == 1);
	require(mem_alloc_node_id_valid_result(3, 4) == 1);
	require(mem_alloc_node_id_valid_result(4, 4) == 0);
	require(mem_alloc_node_id_valid_result(0, 0) == 0);
	require(mem_alloc_node_id_valid_result(0, -1) == 0);
	mix_signed(&digest, mem_alloc_node_id_valid_result(3, 4));
	mix_signed(&digest, mem_alloc_node_id_valid_result(4, 4));

	require(mem_alloc_policy_inputs_valid_result(1, 1, 1, 1, 1) == 1);
	require(mem_alloc_policy_inputs_valid_result(0, 1, 1, 1, 1) == 0);
	require(mem_alloc_policy_inputs_valid_result(1, 0, 1, 1, 1) == 0);
	require(mem_alloc_policy_inputs_valid_result(1, 1, 0, 1, 1) == 0);
	require(mem_alloc_policy_inputs_valid_result(1, 1, 1, 0, 1) == 0);
	require(mem_alloc_policy_inputs_valid_result(1, 1, 1, 1, 0) == 0);
	mix_signed(&digest, mem_alloc_policy_inputs_valid_result(1, 1, 1, 1,
		1));
	mix_signed(&digest, mem_alloc_policy_inputs_valid_result(1, 0, 1, 1,
		1));

	require(mem_alloc_order_node_result(2, 0, 4) == 2);
	require(mem_alloc_order_node_result(2, 1, 4) == 3);
	require(mem_alloc_order_node_result(2, 2, 4) == 0);
	require(mem_alloc_order_node_result(2, 5, 4) == 3);
	require(mem_alloc_order_node_result(-1, 0, 4) == -1);
	require(mem_alloc_order_node_result(1, 0, 0) == -1);
	mix_signed(&digest, mem_alloc_order_node_result(2, 2, 4));
	mix_signed(&digest, mem_alloc_order_node_result(2, 5, 4));

	reset_policy_alloc_trace();
	policy_alloc_pa[3] = 0x300000;
	ptr = mem_mckernel_alloc_policy_result(2, 1, IHK_MC_AP_USER, 3,
		1, 0, 4, MPOL_DEFAULT, 0, NULL, NULL,
		fake_policy_try_alloc, fake_policy_distance_id,
		fake_policy_mask_test, fake_policy_interleave_next,
		fake_policy_rusage_add, fake_policy_phys_to_virt,
		fake_policy_log);
	require(ptr == (void *)(0x300000 + 0x100000000UL));
	require(policy_alloc_count == 1);
	require(policy_alloc_nodes[0] == 3);
	require(policy_alloc_npages == 2);
	require(policy_alloc_p2align == 1);
	require(policy_alloc_is_user == 1);
	require(policy_rusage_add_count == 1);
	require(policy_rusage_add_nid == 3);
	require(policy_last_log_event == MEM_ALLOC_LOG_EXPLICIT_OK);
	mix(&digest, (unsigned long)policy_alloc_count);
	mix(&digest, (unsigned long)policy_last_log_event);
	mix(&digest, policy_log_digest);

	reset_policy_alloc_trace();
	mask = 1UL << 2;
	policy_distance[0] = 0;
	policy_distance[1] = 2;
	policy_distance[2] = 1;
	policy_alloc_pa[2] = 0x220000;
	ptr = mem_mckernel_alloc_policy_result(4, 0, IHK_MC_AP_USER, -1,
		1, 0, 4, MPOL_BIND, 0, &mask, NULL,
		fake_policy_try_alloc, fake_policy_distance_id,
		fake_policy_mask_test, fake_policy_interleave_next,
		fake_policy_rusage_add, fake_policy_phys_to_virt,
		fake_policy_log);
	require(ptr == (void *)(0x220000 + 0x100000000UL));
	require(policy_alloc_count == 1);
	require(policy_alloc_nodes[0] == 2);
	require(policy_rusage_add_nid == 2);
	require(policy_last_log_event == MEM_ALLOC_LOG_POLICY_OK);
	mix(&digest, (unsigned long)policy_alloc_nodes[0]);
	mix(&digest, (unsigned long)policy_rusage_add_nid);
	mix(&digest, policy_log_digest);

	reset_policy_alloc_trace();
	mask = (1UL << 1) | (1UL << 3);
	il_prev = 0;
	policy_alloc_oom[1] = 1;
	policy_alloc_pa[3] = 0x330000;
	ptr = mem_mckernel_alloc_policy_result(1, 0, IHK_MC_AP_USER, -1,
		1, 0, 4, MPOL_INTERLEAVE, 0, &mask, &il_prev,
		fake_policy_try_alloc, fake_policy_distance_id,
		fake_policy_mask_test, fake_policy_interleave_next,
		fake_policy_rusage_add, fake_policy_phys_to_virt,
		fake_policy_log);
	require(ptr == (void *)(0x330000 + 0x100000000UL));
	require(policy_alloc_count == 2);
	require(policy_alloc_nodes[0] == 1);
	require(policy_alloc_nodes[1] == 3);
	require(il_prev == 3);
	require(policy_rusage_add_nid == 3);
	require(policy_last_log_event == MEM_ALLOC_LOG_POLICY_OK);
	mix(&digest, (unsigned long)policy_alloc_count);
	mix(&digest, (unsigned long)il_prev);
	mix(&digest, policy_log_digest);

	reset_policy_alloc_trace();
	policy_distance[0] = 1;
	policy_distance[1] = 2;
	policy_alloc_pa[2] = 0x420000;
	ptr = mem_mckernel_alloc_policy_result(3, 0, 0, -1, 0, 0, 4,
		MPOL_DEFAULT, 0, NULL, NULL, fake_policy_try_alloc,
		fake_policy_distance_id, fake_policy_mask_test,
		fake_policy_interleave_next, fake_policy_rusage_add,
		fake_policy_phys_to_virt, fake_policy_log);
	require(ptr == (void *)(0x420000 + 0x100000000UL));
	require(policy_alloc_count == 2);
	require(policy_alloc_nodes[0] == 1);
	require(policy_alloc_nodes[1] == 2);
	require(policy_rusage_add_nid == 2);
	require(policy_last_log_event == MEM_ALLOC_LOG_DISTANCE_OK);
	mix(&digest, (unsigned long)policy_alloc_nodes[0]);
	mix(&digest, (unsigned long)policy_alloc_nodes[1]);
	mix(&digest, policy_log_digest);

	reset_policy_alloc_trace();
	policy_alloc_pa[0] = 0x500000;
	ptr = mem_mckernel_alloc_policy_result(5, 2, 0, -1, 0, 2, 4,
		MPOL_DEFAULT, 0, NULL, NULL, fake_policy_try_alloc, NULL,
		fake_policy_mask_test, fake_policy_interleave_next,
		fake_policy_rusage_add, fake_policy_phys_to_virt,
		fake_policy_log);
	require(ptr == (void *)(0x500000 + 0x100000000UL));
	require(policy_alloc_count == 3);
	require(policy_alloc_nodes[0] == 2);
	require(policy_alloc_nodes[1] == 3);
	require(policy_alloc_nodes[2] == 0);
	require(policy_rusage_add_nid == 0);
	require(policy_last_log_event == 0);
	mix(&digest, (unsigned long)policy_alloc_count);
	mix(&digest, (unsigned long)policy_alloc_nodes[2]);
	mix(&digest, (unsigned long)policy_rusage_add_nid);

	reset_alloc_body_trace();
	alloc_body_current_node = 6;
	ptr = mem_mckernel_allocate_aligned_pages_node_body_result(0, 1,
		IHK_MC_AP_USER, 3, 1, 0x1000, 0, 8,
		fake_alloc_body_current_vm,
		fake_alloc_body_range_policy_search,
		fake_alloc_body_lookup_range, fake_alloc_body_range_is_shm,
		fake_alloc_body_range_fields, fake_alloc_body_vm_fields,
		fake_alloc_body_current_numa_id,
		fake_alloc_body_policy_alloc);
	require(ptr == NULL);
	require(alloc_body_current_vm_count == 0);
	require(alloc_body_policy_count == 0);
	mix(&digest, (unsigned long)alloc_body_policy_count);

	reset_alloc_body_trace();
	alloc_body_current_node = 6;
	ptr = mem_mckernel_allocate_aligned_pages_node_body_result(4, 2,
		IHK_MC_AP_USER | 0x40UL, 9, 1, 0x1000, 0, 8,
		fake_alloc_body_current_vm,
		fake_alloc_body_range_policy_search,
		fake_alloc_body_lookup_range, fake_alloc_body_range_is_shm,
		fake_alloc_body_range_fields, fake_alloc_body_vm_fields,
		fake_alloc_body_current_numa_id,
		fake_alloc_body_policy_alloc);
	require(ptr == alloc_body_policy_return);
	require(alloc_body_current_vm_count == 0);
	require(alloc_body_current_node_count == 1);
	require(alloc_body_policy_count == 1);
	require(alloc_body_policy_flag == 0x40UL);
	require(alloc_body_policy_pref_node == -1);
	require(alloc_body_policy_numa_mem_policy == MPOL_DEFAULT);
	require(alloc_body_policy_current_node == 6);
	require(alloc_body_policy_nr_nodes == 8);
	mix(&digest, alloc_body_policy_flag);
	mix_signed(&digest, alloc_body_policy_pref_node);
	mix_signed(&digest, alloc_body_policy_numa_mem_policy);

	reset_alloc_body_trace();
	reset_topology_trace();
	topology_nr_nodes = 8;
	alloc_body_current_node = 6;
	ptr = mem_mckernel_allocate_aligned_pages_node_public_body_result(4, 2,
		IHK_MC_AP_USER | 0x40UL, 9, 1, 0x1000, 0,
		fake_topology_nr_nodes, fake_alloc_body_current_vm,
		fake_alloc_body_range_policy_search,
		fake_alloc_body_lookup_range, fake_alloc_body_range_is_shm,
		fake_alloc_body_range_fields, fake_alloc_body_vm_fields,
		fake_alloc_body_current_numa_id,
		fake_alloc_body_policy_alloc);
	require(ptr == alloc_body_policy_return);
	require(topology_nr_nodes_count == 1);
	require(alloc_body_current_vm_count == 0);
	require(alloc_body_current_node_count == 1);
	require(alloc_body_policy_count == 1);
	require(alloc_body_policy_nr_nodes == 8);
	ptr = mem_mckernel_allocate_aligned_pages_node_public_body_result(4, 2,
		IHK_MC_AP_USER, 9, 1, 0x1000, 0, NULL,
		fake_alloc_body_current_vm,
		fake_alloc_body_range_policy_search,
		fake_alloc_body_lookup_range, fake_alloc_body_range_is_shm,
		fake_alloc_body_range_fields, fake_alloc_body_vm_fields,
		fake_alloc_body_current_numa_id,
		fake_alloc_body_policy_alloc);
	require(ptr == NULL);
	require(topology_nr_nodes_count == 1);
	mix(&digest, (unsigned long)topology_nr_nodes_count);
	mix_signed(&digest, alloc_body_policy_nr_nodes);

	reset_alloc_body_trace();
	alloc_body_current_vm = &alloc_body_vm;
	alloc_body_current_node = 4;
	ptr = mem_mckernel_allocate_aligned_pages_node_body_result(2, 0,
		IHK_MC_AP_USER | 0x20UL, 3, 1, (uintptr_t)-1, 1, 6,
		fake_alloc_body_current_vm,
		fake_alloc_body_range_policy_search,
		fake_alloc_body_lookup_range, fake_alloc_body_range_is_shm,
		fake_alloc_body_range_fields, fake_alloc_body_vm_fields,
		fake_alloc_body_current_numa_id,
		fake_alloc_body_policy_alloc);
	require(ptr == alloc_body_policy_return);
	require(alloc_body_current_vm_count == 1);
	require(alloc_body_range_policy_count == 0);
	require(alloc_body_policy_flag == (IHK_MC_AP_USER | 0x20UL));
	require(alloc_body_policy_pref_node == 3);
	require(alloc_body_policy_numa_mem_policy == -1);
	mix(&digest, (unsigned long)alloc_body_current_vm_count);
	mix_signed(&digest, alloc_body_policy_numa_mem_policy);

	reset_alloc_body_trace();
	mask = 1UL << 5;
	alloc_body_current_vm = &alloc_body_vm;
	alloc_body_current_node = 2;
	alloc_body_vm.range_policy = &alloc_body_range_policy;
	alloc_body_vm.range = &alloc_body_range;
	alloc_body_range.is_shm = 1;
	alloc_body_range_policy.numa_mem_policy = MPOL_BIND;
	alloc_body_range_policy.numa_mask = &mask;
	alloc_body_range_policy.il_prev = 7;
	ptr = mem_mckernel_allocate_aligned_pages_node_body_result(8, 1,
		IHK_MC_AP_USER, -1, 1, 0x7000, 1, 9,
		fake_alloc_body_current_vm,
		fake_alloc_body_range_policy_search,
		fake_alloc_body_lookup_range, fake_alloc_body_range_is_shm,
		fake_alloc_body_range_fields, fake_alloc_body_vm_fields,
		fake_alloc_body_current_numa_id,
		fake_alloc_body_policy_alloc);
	require(ptr == alloc_body_policy_return);
	require(alloc_body_range_policy_count == 1);
	require(alloc_body_range_policy_addr == 0x7000);
	require(alloc_body_lookup_count == 1);
	require(alloc_body_lookup_start == 0x7000);
	require(alloc_body_lookup_end == 0x7001);
	require(alloc_body_range_is_shm_count == 1);
	require(alloc_body_range_fields_count == 1);
	require(alloc_body_vm_fields_count == 0);
	require(alloc_body_policy_numa_mem_policy == MPOL_BIND);
	require(alloc_body_policy_chk_shm == 1);
	require(alloc_body_policy_mask == &mask);
	require(alloc_body_policy_il_prev ==
		&alloc_body_range_policy.il_prev);
	mix(&digest, (unsigned long)alloc_body_lookup_count);
	mix_signed(&digest, alloc_body_policy_numa_mem_policy);
	mix_signed(&digest, alloc_body_policy_chk_shm);

	reset_alloc_body_trace();
	mask = (1UL << 1) | (1UL << 3);
	alloc_body_current_vm = &alloc_body_vm;
	alloc_body_current_node = 1;
	alloc_body_vm.numa_mem_policy = MPOL_INTERLEAVE;
	alloc_body_vm.numa_mask = &mask;
	alloc_body_vm.il_prev = 3;
	ptr = mem_mckernel_allocate_aligned_pages_node_body_result(3, 0,
		IHK_MC_AP_USER, -1, 1, 0x8000, 1, 4,
		fake_alloc_body_current_vm,
		fake_alloc_body_range_policy_search,
		fake_alloc_body_lookup_range, fake_alloc_body_range_is_shm,
		fake_alloc_body_range_fields, fake_alloc_body_vm_fields,
		fake_alloc_body_current_numa_id,
		fake_alloc_body_policy_alloc);
	require(ptr == alloc_body_policy_return);
	require(alloc_body_range_policy_count == 1);
	require(alloc_body_lookup_count == 0);
	require(alloc_body_vm_fields_count == 1);
	require(alloc_body_policy_numa_mem_policy == MPOL_INTERLEAVE);
	require(alloc_body_policy_mask == &mask);
	require(alloc_body_policy_il_prev == &alloc_body_vm.il_prev);
	mix(&digest, (unsigned long)alloc_body_vm_fields_count);
	mix_signed(&digest, alloc_body_policy_numa_mem_policy);

	pending.next = &pending;
	pending.prev = &pending;
	page0.mode = 0;
	page0.phys = 0x555000;
	free_body_page_return = &page0;
	free_body_phys_to_page_count = 0;
	free_body_allocator_count = 0;
	fake_current_phys = page0.phys;
	rc = mem_mckernel_free_pages_body_result((void *)0xa000, 7, 1,
		&pending, fake_virt_to_phys, fake_free_body_phys_to_page,
		fake_free_body_in_allocator, fake_pending_warn);
	require(rc == 1);
	require(free_body_phys_to_page_count == 1);
	require(free_body_allocator_count == 0);
	require(page0.mode == 1);
	require(page0.offset == 7);
	mix_signed(&digest, rc);
	mix(&digest, (unsigned long)page0.offset);

	pending.next = NULL;
	pending.prev = NULL;
	page0.mode = 0;
	free_body_page_return = &page0;
	free_body_phys_to_page_count = 0;
	free_body_allocator_count = 0;
	free_body_allocator_va = NULL;
	free_body_allocator_npages = 0;
	free_body_allocator_is_user = 0;
	fake_current_phys = 0x777000;
	rc = mem_mckernel_free_pages_body_result((void *)0xb000, 5, 0,
		&pending, fake_virt_to_phys, fake_free_body_phys_to_page,
		fake_free_body_in_allocator, fake_pending_warn);
	require(rc == 0);
	require(free_body_phys_to_page_count == 1);
	require(free_body_allocator_count == 1);
	require(free_body_allocator_va == (void *)0xb000);
	require(free_body_allocator_npages == 5);
	require(free_body_allocator_is_user == 0);
	mix_signed(&digest, rc);
	mix(&digest, (unsigned long)free_body_allocator_npages);

	{
		struct list_head public_pending;

		public_pending.next = &public_pending;
		public_pending.prev = &public_pending;
		page0.mode = 0;
		page0.phys = 0x888000;
		free_body_pending_return = &public_pending;
		free_body_pending_count = 0;
		free_body_page_return = &page0;
		free_body_phys_to_page_count = 0;
		free_body_allocator_count = 0;
		fake_current_phys = page0.phys;
		rc = mem_mckernel_free_pages_public_body_result((void *)0xc000,
			4, 1, fake_free_body_pending_pages, fake_virt_to_phys,
			fake_free_body_phys_to_page, fake_free_body_in_allocator,
			fake_pending_warn, mem_mckernel_free_pages_body_result);
		require(rc == 1);
		require(free_body_pending_count == 1);
		require(free_body_phys_to_page_count == 1);
		require(free_body_allocator_count == 0);
		require(page0.mode == 1);
		require(page0.offset == 4);

		free_body_pending_return = NULL;
		free_body_pending_count = 0;
		rc = mem_mckernel_free_pages_public_body_result((void *)0xc000,
			4, 1, fake_free_body_pending_pages, fake_virt_to_phys,
			fake_free_body_phys_to_page, fake_free_body_in_allocator,
			fake_pending_warn, mem_mckernel_free_pages_body_result);
		require(rc == -22);
		require(free_body_pending_count == 1);

		free_body_pending_count = 0;
		rc = mem_mckernel_free_pages_public_body_result((void *)0xc000,
			4, 1, fake_free_body_pending_pages, fake_virt_to_phys,
			fake_free_body_phys_to_page, fake_free_body_in_allocator,
			fake_pending_warn, NULL);
		require(rc == -22);
		require(free_body_pending_count == 0);
		mix(&digest, 0x66726565707562UL);
	}

	{
		char memdebug_name[] = "memdebug";

		reset_query_free_trace();
		query_free_node_pages[0] = 4;
		query_free_node_pages[1] = 7;
		query_free_node_pages[2] = 9;
		query_free_page_hash_pages = 13;
		rc = mem_query_free_mem_interrupt_body_result(3,
			memdebug_name, 0, 0, 44, 45,
			fake_query_free_node_pages,
			fake_query_free_total_log, fake_query_free_panic,
			fake_query_free_find_command_line,
			fake_query_free_kmalloc_memcheck,
			fake_query_free_pagealloc_memcheck,
			fake_query_free_page_hash_count,
			fake_query_free_page_hash_log,
			fake_query_free_sbox_write);
		require(rc == 20);
		require(query_free_node_calls == 3);
		require(query_free_node_trace[0] == 0);
		require(query_free_node_trace[2] == 2);
		require(query_free_total_log_count == 1);
		require(query_free_total_pages == 20);
		require(query_free_panic_count == 0);
		require(query_free_find_count == 1);
		require(query_free_kmalloc_count == 0);
		require(query_free_pagealloc_count == 0);
		require(query_free_page_hash_count_calls == 1);
		require(query_free_page_hash_log_pages == 13);
		require(query_free_sbox_count == 0);
		mix_signed(&digest, rc);
		mix_signed(&digest, query_free_total_pages);
		mix_signed(&digest, query_free_page_hash_log_pages);

		reset_query_free_trace();
		query_free_node_pages[0] = 1;
		query_free_node_pages[1] = 2;
		query_free_node_pages[2] = 3;
		query_free_memdebug_present = 1;
		query_free_page_hash_pages = 21;
		rc = mem_query_free_mem_interrupt_body_result(3,
			memdebug_name, 1, 1, 44, 45,
			fake_query_free_node_pages,
			fake_query_free_total_log, fake_query_free_panic,
			fake_query_free_find_command_line,
			fake_query_free_kmalloc_memcheck,
			fake_query_free_pagealloc_memcheck,
			fake_query_free_page_hash_count,
			fake_query_free_page_hash_log,
			fake_query_free_sbox_write);
		require(rc == 6);
		require(query_free_panic_count == 1);
		require(query_free_find_count == 1);
		require(query_free_find_name == memdebug_name);
		require(query_free_kmalloc_count == 1);
		require(query_free_pagealloc_count == 1);
		require(query_free_page_hash_log_pages == 21);
		require(query_free_sbox_count == 2);
		require(query_free_sbox_offsets[0] == 44);
		require(query_free_sbox_values[0] == 6);
		require(query_free_sbox_offsets[1] == 45);
		require(query_free_sbox_values[1] == 1);
		mix_signed(&digest, query_free_panic_count);
		mix_signed(&digest, query_free_kmalloc_count);
		mix(&digest, (unsigned long)query_free_sbox_values[0]);

		reset_query_free_trace();
		rc = mem_query_free_mem_interrupt_body_result(1,
			memdebug_name, 0, 0, 0, 0, NULL,
			fake_query_free_total_log, fake_query_free_panic,
			fake_query_free_find_command_line,
			fake_query_free_kmalloc_memcheck,
			fake_query_free_pagealloc_memcheck,
			fake_query_free_page_hash_count,
			fake_query_free_page_hash_log,
			fake_query_free_sbox_write);
		require(rc == -22);
		require(query_free_total_log_count == 0);
		require(query_free_find_count == 0);
		mix_signed(&digest, rc);

		reset_query_free_trace();
		query_free_nr_nodes = 2;
		query_free_node_pages[0] = 5;
		query_free_node_pages[1] = 6;
		query_free_page_hash_pages = 17;
		rc = mem_query_free_mem_interrupt_public_body_result(
			(void *)0xabcUL, fake_query_free_nr_nodes,
			memdebug_name, 0, 1, 77, 78,
			fake_query_free_node_pages,
			fake_query_free_total_log, fake_query_free_panic,
			fake_query_free_find_command_line,
			fake_query_free_kmalloc_memcheck,
			fake_query_free_pagealloc_memcheck,
			fake_query_free_page_hash_count,
			fake_query_free_page_hash_log,
			fake_query_free_sbox_write);
		require(rc == 11);
		require(query_free_nr_nodes_count == 1);
		require(query_free_node_calls == 2);
		require(query_free_total_pages == 11);
		require(query_free_sbox_count == 2);
		require(query_free_sbox_offsets[0] == 77);
		require(query_free_sbox_values[0] == 11);
		require(query_free_page_hash_log_pages == 17);
		mix_signed(&digest, rc);
		mix_signed(&digest, query_free_nr_nodes_count);
		mix(&digest, (unsigned long)query_free_sbox_values[0]);

		reset_query_free_trace();
		rc = mem_query_free_mem_interrupt_public_body_result(
			NULL, NULL, memdebug_name, 0, 0, 0, 0,
			fake_query_free_node_pages,
			fake_query_free_total_log, fake_query_free_panic,
			fake_query_free_find_command_line,
			fake_query_free_kmalloc_memcheck,
			fake_query_free_pagealloc_memcheck,
			fake_query_free_page_hash_count,
			fake_query_free_page_hash_log,
			fake_query_free_sbox_write);
		require(rc == -22);
		require(query_free_node_calls == 0);
		mix_signed(&digest, rc);
	}

	return digest;
}

int main(void)
{
	static struct mem_chunk layout1[] = {
		{ 0x1000, 0x9000, 0 },
		{ 0x10000, 0x18000, 2 },
		{ 0x40000, 0x48000, 7 },
	};
	static struct mem_chunk layout2[] = {
		{ 0x0, 0x1000, 3 },
		{ 0x1000, 0x2000, 4 },
	};
	static const unsigned long ranges[][2] = {
		{ 0x1000, 0x1000 },
		{ 0x1000, 0x8fff },
		{ 0x1000, 0x9000 },
		{ 0x0fff, 0x1000 },
		{ 0x8800, 0x9800 },
		{ 0x10000, 0x17fff },
		{ 0x10000, 0x18000 },
		{ 0x18000, 0x18000 },
		{ 0x40000, 0x47fff },
		{ 0x44000, 0x48000 },
	};
	static const unsigned long addrs[] = {
		0, 0xfff, 0x1000, 0x8fff, 0x9000, 0x10000, 0x17fff,
		0x18000, 0x40000, 0x47fff, 0x48000,
	};
	char cmdline1[] = "root=/dev/test dump_level=24 idle_halt time_sharing";
	char cmdline2[] = "allow_oversubscribe foo=bar dump_level=7";
	char needle_missing[] = "not_present";
	unsigned long digest = 0xadd45fed31415926UL;

	set_chunks(layout1, sizeof(layout1) / sizeof(layout1[0]));
	for (unsigned int i = 0; i < sizeof(ranges) / sizeof(ranges[0]); i++) {
		mix_signed(&digest, is_mckernel_memory(ranges[i][0], ranges[i][1]));
	}
	for (unsigned int i = 0; i < sizeof(addrs) / sizeof(addrs[0]); i++) {
		mix_signed(&digest, phys_to_nid(addrs[i]));
	}

	set_chunks(layout2, sizeof(layout2) / sizeof(layout2[0]));
	for (unsigned int i = 0; i < sizeof(ranges) / sizeof(ranges[0]); i++) {
		mix_signed(&digest, is_mckernel_memory(ranges[i][0], ranges[i][1]));
	}
	for (unsigned int i = 0; i < sizeof(addrs) / sizeof(addrs[0]); i++) {
		mix_signed(&digest, phys_to_nid(addrs[i]));
	}

	set_chunks(NULL, 0);
	mix_signed(&digest, is_mckernel_memory(0x1000, 0x1000));
	mix_signed(&digest, phys_to_nid(0x1000));

	current_kargs = NULL;
	mix_signed(&digest, ptr_offset(NULL, find_command_line("dump_level=")));
	current_kargs = cmdline1;
	mix_signed(&digest, ptr_offset(cmdline1, find_command_line("dump_level=")));
	mix_signed(&digest, ptr_offset(cmdline1, find_command_line("idle_halt")));
	mix_signed(&digest, ptr_offset(cmdline1, find_command_line("time_sharing")));
	mix_signed(&digest, ptr_offset(cmdline1, find_command_line(needle_missing)));
	current_kargs = cmdline2;
	mix_signed(&digest, ptr_offset(cmdline2, find_command_line("allow_oversubscribe")));
	mix_signed(&digest, ptr_offset(cmdline2, find_command_line("dump_level=")));
	mix_signed(&digest, ptr_offset(cmdline2, find_command_line("bar")));
	mix_signed(&digest, ptr_offset(cmdline2, find_command_line(needle_missing)));
	mix(&digest, round_helpers_digest());
	mix(&digest, hash_helpers_digest());
	mix(&digest, mem_runtime_orchestration_digest());

	printf("mem_init_helpers ok digest=%016lx\n", digest);
	return 0;
}
