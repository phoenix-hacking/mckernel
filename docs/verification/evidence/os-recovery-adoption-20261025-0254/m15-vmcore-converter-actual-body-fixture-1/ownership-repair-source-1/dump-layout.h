/* Exact existing C dump layout declarations; test fixture only. */
struct ihk_dump_page {
	unsigned long start;
	unsigned long map_count;
	unsigned long map[0];
};

struct ihk_dump_page_set {
	unsigned int completion_flag;
	unsigned int count;
	unsigned long page_size;
	unsigned long phy_page;
};

struct dump_mem_chunk {
	unsigned long addr;
	unsigned long size;
};

typedef struct dump_mem_chunks_s {
	int nr_chunks;
	unsigned long kernel_base;
	/* memstart_addr in aarch64 */
	unsigned long phys_start;
	struct dump_mem_chunk chunks[];
} dump_mem_chunks_t;

