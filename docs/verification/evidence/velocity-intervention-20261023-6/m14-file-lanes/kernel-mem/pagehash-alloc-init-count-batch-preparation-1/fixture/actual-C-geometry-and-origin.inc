#define PHYS_PAGE_HASH_SHIFT (10)
#define PHYS_PAGE_HASH_SIZE (1 << PHYS_PAGE_HASH_SHIFT)
#define PHYS_PAGE_HASH_MASK (PHYS_PAGE_HASH_SIZE - 1)
struct list_head page_hash[PHYS_PAGE_HASH_SIZE];
ihk_spinlock_t page_hash_locks[PHYS_PAGE_HASH_SIZE];
const int page_init_hash_bucket_count = PHYS_PAGE_HASH_SIZE;
const unsigned long page_init_hash_head_stride = sizeof(page_hash[0]);
const unsigned long page_unmap_lock_stride = sizeof(page_hash_locks[0]);
const char page_hash_alloc_file[] = __FILE__; const int page_hash_alloc_line = __LINE__;
