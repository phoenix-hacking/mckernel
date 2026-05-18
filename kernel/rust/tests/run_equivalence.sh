#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
tmpdir="$(mktemp -d /tmp/mckernel-rust-equiv.XXXXXX)"
trap 'rm -rf "${tmpdir}"' EXIT

cd "${repo_root}"

cat > "${tmpdir}/rbtree_equiv.c" <<'EOF_RBTREE'
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

struct rb_node {
	unsigned long __rb_parent_color;
	struct rb_node *rb_right;
	struct rb_node *rb_left;
} __attribute__((aligned(sizeof(long))));

struct rb_root {
	struct rb_node *rb_node;
};

#define rb_entry(ptr, type, member) ((type *)((char *)(ptr) - offsetof(type, member)))

extern void rb_insert_color(struct rb_node *, struct rb_root *);
extern void rb_erase(struct rb_node *, struct rb_root *);
extern struct rb_node *rb_next(const struct rb_node *);
extern struct rb_node *rb_next_safe(const struct rb_node *);
extern struct rb_node *rb_prev(const struct rb_node *);
extern struct rb_node *rb_first(const struct rb_root *);
extern struct rb_node *rb_first_safe(const struct rb_root *);
extern struct rb_node *rb_last(const struct rb_root *);
extern struct rb_node *rb_first_postorder(const struct rb_root *);
extern struct rb_node *rb_next_postorder(const struct rb_node *);
extern void rb_replace_node(struct rb_node *, struct rb_node *, struct rb_root *);
extern struct rb_node *rb_preorder_dfs_search(const struct rb_root *,
					      _Bool (*)(struct rb_node *, void *),
					      void *);

int ihk_mc_chk_page_address(unsigned long mem_addr) { (void)mem_addr; return 0; }
unsigned long virt_to_phys(void *v) { return (unsigned long)v; }
void *phys_to_virt(unsigned long p) { return (void *)p; }
int zero_at_free = 1;

struct item {
	int key;
	int value;
	struct rb_node rb;
};

static void rb_link_node(struct rb_node *node, struct rb_node *parent,
			 struct rb_node **link)
{
	node->__rb_parent_color = (unsigned long)parent;
	node->rb_left = NULL;
	node->rb_right = NULL;
	*link = node;
}

static void insert_item(struct rb_root *root, struct item *item)
{
	struct rb_node **link = &root->rb_node;
	struct rb_node *parent = NULL;

	while (*link) {
		struct item *entry = rb_entry(*link, struct item, rb);
		parent = *link;
		if (item->key < entry->key)
			link = &(*link)->rb_left;
		else if (item->key > entry->key)
			link = &(*link)->rb_right;
		else
			exit(2);
	}

	rb_link_node(&item->rb, parent, link);
	rb_insert_color(&item->rb, root);
}

static _Bool match_key(struct rb_node *node, void *arg)
{
	return rb_entry(node, struct item, rb)->key == *(int *)arg;
}

static void require_sorted(struct rb_root *root, const int *expected, int count)
{
	struct rb_node *node = rb_first(root);
	int i = 0;

	if (node != rb_first_safe(root))
		exit(3);

	for (; node; node = rb_next(node), i++) {
		if (i >= count || rb_entry(node, struct item, rb)->key != expected[i])
			exit(4);
		if (rb_next_safe(node) != rb_next(node))
			exit(5);
	}
	if (i != count)
		exit(6);

	node = rb_last(root);
	for (i = count - 1; i >= 0; i--, node = rb_prev(node)) {
		if (!node || rb_entry(node, struct item, rb)->key != expected[i])
			exit(7);
	}
	if (node)
		exit(8);
}

int main(void)
{
	struct rb_root root = { NULL };
	int keys[] = { 40, 10, 70, 20, 60, 80, 30, 50, 15, 65, 5, 75 };
	struct item items[sizeof(keys) / sizeof(keys[0])];
	int sorted[] = { 5, 10, 15, 20, 30, 40, 50, 60, 65, 70, 75, 80 };
	int after_erase[] = { 5, 10, 15, 20, 30, 50, 60, 65, 70, 75, 80 };
	int target = 65;
	struct item replacement = { .key = 65, .value = 6500 };
	struct rb_node *found;
	int post_count = 0;

	for (size_t i = 0; i < sizeof(items) / sizeof(items[0]); i++) {
		items[i].key = keys[i];
		items[i].value = keys[i] * 10;
		insert_item(&root, &items[i]);
	}

	require_sorted(&root, sorted, 12);
	found = rb_preorder_dfs_search(&root, match_key, &target);
	if (!found)
		exit(9);
	rb_replace_node(found, &replacement.rb, &root);
	require_sorted(&root, sorted, 12);

	for (found = rb_first_postorder(&root); found; found = rb_next_postorder(found))
		post_count++;
	if (post_count != 12)
		exit(10);

	for (size_t i = 0; i < sizeof(items) / sizeof(items[0]); i++) {
		if (items[i].key == 40) {
			rb_erase(&items[i].rb, &root);
			break;
		}
	}
	require_sorted(&root, after_erase, 11);
	printf("rbtree ok count=11 first=5 last=80 post=%d\n", post_count);
	return 0;
}
EOF_RBTREE

cat > "${tmpdir}/llist_equiv.c" <<'EOF_LLIST'
#include <stdio.h>
#include <stdlib.h>

struct llist_node { struct llist_node *next; };
struct llist_head { struct llist_node *first; };

extern _Bool llist_add_batch(struct llist_node *, struct llist_node *,
			     struct llist_head *);
extern struct llist_node *llist_del_first(struct llist_head *);
extern struct llist_node *llist_reverse_order(struct llist_node *);

struct item {
	int value;
	struct llist_node node;
};

#define entry(ptr) ((struct item *)((char *)(ptr) - __builtin_offsetof(struct item, node)))

static void require(int cond)
{
	if (!cond)
		exit(2);
}

int main(void)
{
	struct llist_head head = { NULL };
	struct item items[6];
	struct llist_node *node;
	struct llist_node *rev;
	int sum = 0;

	for (int i = 0; i < 6; i++) {
		items[i].value = i + 1;
		items[i].node.next = NULL;
	}

	items[0].node.next = &items[1].node;
	items[1].node.next = &items[2].node;
	require(llist_add_batch(&items[0].node, &items[2].node, &head) == 1);
	items[3].node.next = &items[4].node;
	require(llist_add_batch(&items[3].node, &items[4].node, &head) == 0);
	node = llist_del_first(&head);
	require(node == &items[3].node && head.first == &items[4].node);
	node = llist_del_first(&head);
	require(node == &items[4].node);
	require(llist_add_batch(&items[5].node, &items[5].node, &head) == 0);
	rev = llist_reverse_order(head.first);
	for (node = rev; node; node = node->next)
		sum = sum * 10 + entry(node)->value;
	printf("llist ok sum=%d first=%d\n", sum, entry(rev)->value);
	return 0;
}
EOF_LLIST

cat > "${tmpdir}/bitmap_equiv.c" <<'EOF_BITMAP'
#include <stdio.h>
#include <string.h>

extern int hex_to_bin(char);
extern int __bitmap_empty(const unsigned long *, int);
extern int __bitmap_full(const unsigned long *, int);
extern int __bitmap_equal(const unsigned long *, const unsigned long *, int);
extern void __bitmap_complement(unsigned long *, const unsigned long *, int);
extern void __bitmap_shift_right(unsigned long *, const unsigned long *, int, int);
extern void __bitmap_shift_left(unsigned long *, const unsigned long *, int, int);
extern int __bitmap_and(unsigned long *, const unsigned long *, const unsigned long *, int);
extern void __bitmap_or(unsigned long *, const unsigned long *, const unsigned long *, int);
extern void __bitmap_xor(unsigned long *, const unsigned long *, const unsigned long *, int);
extern int __bitmap_andnot(unsigned long *, const unsigned long *, const unsigned long *, int);
extern int __bitmap_intersects(const unsigned long *, const unsigned long *, int);
extern int __bitmap_subset(const unsigned long *, const unsigned long *, int);
extern int __bitmap_weight(const unsigned long *, int);
extern void bitmap_set(unsigned long *, int, int);
extern void bitmap_clear(unsigned long *, int, int);
extern unsigned long bitmap_find_next_zero_area(unsigned long *, unsigned long,
						unsigned long, unsigned int,
						unsigned long);
extern int bitmap_find_free_region(unsigned long *, int, int);
extern void bitmap_release_region(unsigned long *, int, int);
extern int bitmap_allocate_region(unsigned long *, int, int);
extern int bitmap_ord_to_pos(const unsigned long *, int, int);
extern void bitmap_remap(unsigned long *, const unsigned long *,
			 const unsigned long *, const unsigned long *, int);
extern int bitmap_bitremap(int, const unsigned long *,
			   const unsigned long *, int);
extern void bitmap_onto(unsigned long *, const unsigned long *,
			const unsigned long *, int);
extern void bitmap_fold(unsigned long *, const unsigned long *, int, int);

static unsigned long rng_state = 0x123456789abcdef0UL;

static unsigned long rnd(void)
{
	rng_state = rng_state * 6364136223846793005UL + 1442695040888963407UL;
	return rng_state;
}

static void fill(unsigned long *dst, int words)
{
	for (int i = 0; i < words; i++)
		dst[i] = rnd();
}

static unsigned long digest_words(const unsigned long *src, int words)
{
	unsigned long d = 0xcbf29ce484222325UL;
	for (int i = 0; i < words; i++) {
		d ^= src[i];
		d *= 0x100000001b3UL;
	}
	return d;
}

static void mix_value(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

int main(void)
{
	unsigned long a[5], b[5], c[5];
	unsigned long digest = 0;
	int bit_sizes[] = { 1, 2, 7, 31, 32, 63, 64, 65, 95, 127, 128, 129, 191, 255, 256, 257 };
	int shifts[] = { 0, 1, 7, 31, 32, 63, 64, 65, 129, 255, 300 };
	unsigned long aligns[] = { 0, 1, 3, 7, 15, 31, 63 };
	unsigned int zero_area_sizes[] = { 0, 1, 2, 5, 17, 64, 130 };
	int region_orders[] = { 0, 1, 2, 3, 4, 5, 6, 7, 8 };

	for (int h = 0; h < 256; h++)
		digest = digest * 131 + (unsigned long)(hex_to_bin((char)h) + 2);

	for (unsigned int bi = 0; bi < sizeof(bit_sizes) / sizeof(bit_sizes[0]); bi++) {
		int bits = bit_sizes[bi];
		int words = (bits + 63) / 64;
		fill(a, 5);
		fill(b, 5);
		digest ^= (unsigned long)__bitmap_empty(a, bits);
		digest ^= (unsigned long)__bitmap_full(a, bits) << 1;
		digest ^= (unsigned long)__bitmap_equal(a, b, bits) << 2;
		digest ^= (unsigned long)__bitmap_intersects(a, b, bits) << 3;
		digest ^= (unsigned long)__bitmap_subset(a, b, bits) << 4;
		digest ^= (unsigned long)__bitmap_weight(a, bits) << 8;
		memset(c, 0xa5, sizeof(c)); __bitmap_complement(c, a, bits); digest ^= digest_words(c, words);
		memset(c, 0x5a, sizeof(c)); digest ^= (unsigned long)__bitmap_and(c, a, b, bits); digest ^= digest_words(c, words);
		memset(c, 0x5a, sizeof(c)); __bitmap_or(c, a, b, bits); digest ^= digest_words(c, words);
		memset(c, 0x5a, sizeof(c)); __bitmap_xor(c, a, b, bits); digest ^= digest_words(c, words);
		memset(c, 0x5a, sizeof(c)); digest ^= (unsigned long)__bitmap_andnot(c, a, b, bits); digest ^= digest_words(c, words);
		for (unsigned int si = 0; si < sizeof(shifts) / sizeof(shifts[0]); si++) {
			int shift_words = shifts[si] / (int)(sizeof(unsigned long) * 8);
			if (shift_words > words)
				continue;
			memset(c, 0x5a, sizeof(c)); __bitmap_shift_left(c, a, shifts[si], bits); digest ^= digest_words(c, words);
			memset(c, 0x5a, sizeof(c)); __bitmap_shift_right(c, a, shifts[si], bits); digest ^= digest_words(c, words);
		}
		memset(c, 0, sizeof(c));
		for (int start = 0; start < bits; start += 17) {
			int nr = (start * 7 + bits) % 41;
			if (start + nr > bits)
				nr = bits - start;
			bitmap_set(c, start, nr);
			if (nr > 2)
				bitmap_clear(c, start + 1, nr - 2);
		}
		digest ^= digest_words(c, words);
		{
			int ords[] = { -1, 0, 1, 2, 7, bits / 2, bits - 1, bits, bits + 3 };
			int oldbits[] = { -1, 0, 1, bits / 2, bits - 1, bits, bits + 9 };
			int fold_sizes[] = { 1, 2, 3, 7, bits > 1 ? bits / 2 : 1, bits };
			for (unsigned int oi = 0; oi < sizeof(ords) / sizeof(ords[0]); oi++)
				mix_value(&digest, (unsigned long)(long)bitmap_ord_to_pos(a, ords[oi], bits));
			for (unsigned int oi = 0; oi < sizeof(oldbits) / sizeof(oldbits[0]); oi++)
				mix_value(&digest, (unsigned long)(long)bitmap_bitremap(oldbits[oi], a, b, bits));
			memset(c, 0x5a, sizeof(c)); bitmap_remap(c, a, b, a, bits); digest ^= digest_words(c, words);
			memset(c, 0x5a, sizeof(c)); bitmap_remap(c, a, a, b, bits); digest ^= digest_words(c, words);
			memset(c, 0x5a, sizeof(c)); bitmap_onto(c, a, b, bits); digest ^= digest_words(c, words);
			for (unsigned int fi = 0; fi < sizeof(fold_sizes) / sizeof(fold_sizes[0]); fi++) {
				memset(c, 0x5a, sizeof(c)); bitmap_fold(c, a, fold_sizes[fi], bits); digest ^= digest_words(c, words);
			}
		}
		for (unsigned int ai = 0; ai < sizeof(aligns) / sizeof(aligns[0]); ai++) {
			for (unsigned int zi = 0; zi < sizeof(zero_area_sizes) / sizeof(zero_area_sizes[0]); zi++) {
				for (unsigned long start = 0; start <= (unsigned long)bits + 5; start += 13) {
					unsigned long area = bitmap_find_next_zero_area(c, bits, start,
						zero_area_sizes[zi], aligns[ai]);
					mix_value(&digest, area);
				}
			}
		}
		for (unsigned int oi = 0; oi < sizeof(region_orders) / sizeof(region_orders[0]); oi++) {
			int order = region_orders[oi];
			int region_bits = 1 << order;
			memset(c, 0, sizeof(c));
			mix_value(&digest, (unsigned long)bitmap_find_free_region(c, bits, order));
			digest ^= digest_words(c, words);
			for (int pos = 0; pos + region_bits <= bits; pos += region_bits * 3) {
				mix_value(&digest, (unsigned long)bitmap_allocate_region(c, pos, order));
				digest ^= digest_words(c, words);
				mix_value(&digest, (unsigned long)bitmap_allocate_region(c, pos, order));
				bitmap_release_region(c, pos, order);
				digest ^= digest_words(c, words);
				mix_value(&digest, (unsigned long)bitmap_allocate_region(c, pos, order));
			}
			digest ^= digest_words(c, words);
		}
	}
	printf("bitmap ok digest=%016lx\n", digest);
	return 0;
}
EOF_BITMAP

cat > "${tmpdir}/page_alloc_equiv.c" <<'EOF_PAGE_ALLOC'
extern int printf(const char *, ...);
extern void exit(int);
extern void abort(void);

#ifndef PAGE_ALLOC_USE_C
extern void *memset(void *, int, unsigned long);
#endif

#ifndef NULL
#define NULL ((void *)0)
#endif

#define ARENA_BASE 0x1000000UL
#define ARENA_SIZE (128UL * 4096UL)
#define LOCAL_PAGE_SIZE 4096UL

#ifndef PAGE_ALLOC_USE_C
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

struct free_chunk {
	unsigned long addr, size;
	struct rb_node node;
	struct llist_node list;
};

#define rb_entry(ptr, type, member) \
	((type *)((char *)(ptr) - __builtin_offsetof(type, member)))

extern struct rb_node *rb_first(const struct rb_root *);
extern struct rb_node *rb_next(const struct rb_node *);
#endif

static unsigned char arena[ARENA_SIZE];

void *phys_to_virt(unsigned long p)
{
	if (p < ARENA_BASE || p >= ARENA_BASE + ARENA_SIZE)
		exit(80);
	return arena + (p - ARENA_BASE);
}

unsigned long virt_to_phys(void *v)
{
	return ARENA_BASE + (unsigned long)((unsigned char *)v - arena);
}

int ihk_mc_chk_page_address(unsigned long mem_addr)
{
	(void)mem_addr;
	return 0;
}

int kprintf(const char *format, ...)
{
	(void)format;
	return 0;
}

void panic(const char *message)
{
	(void)message;
	abort();
}

#ifdef PAGE_ALLOC_USE_C
#include "lib/page_alloc.c"
#else
int zero_at_free = 1;

extern int __page_alloc_rbtree_free_range(struct rb_root *root,
					  unsigned long addr,
					  unsigned long size);
extern unsigned long __page_alloc_rbtree_alloc_pages(struct rb_root *root,
						     int npages,
						     int p2align);
extern unsigned long __page_alloc_rbtree_reserve_pages(struct rb_root *root,
						       unsigned long aligned_addr,
						       int npages);
extern struct free_chunk *__page_alloc_rbtree_get_root_chunk(struct rb_root *root);
#endif

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

static unsigned long digest_tree(struct rb_root *root)
{
	struct rb_node *node;
	unsigned long digest = 0xcbf29ce484222325UL;
	unsigned long last_end = 0;
	int count = 0;

	for (node = rb_first(root); node; node = rb_next(node)) {
		struct free_chunk *chunk = rb_entry(node, struct free_chunk, node);

		if ((void *)chunk != phys_to_virt(chunk->addr))
			exit(81);
		if (count && chunk->addr <= last_end)
			exit(82);

		mix(&digest, chunk->addr);
		mix(&digest, chunk->size);
		last_end = chunk->addr + chunk->size;
		count++;
	}

	mix(&digest, (unsigned long)count);
	return digest;
}

static void require(int condition)
{
	if (!condition)
		exit(83);
}

int main(void)
{
	struct rb_root root = { NULL };
	unsigned long digest = 0;
	unsigned long a, b, c;

	memset(arena, 0xa5, sizeof(arena));

	require(__page_alloc_rbtree_free_range(&root, ARENA_BASE, 4 * LOCAL_PAGE_SIZE) == 0);
	mix(&digest, digest_tree(&root));
	require(__page_alloc_rbtree_free_range(&root, ARENA_BASE + 8 * LOCAL_PAGE_SIZE,
					       2 * LOCAL_PAGE_SIZE) == 0);
	mix(&digest, digest_tree(&root));
	require(__page_alloc_rbtree_free_range(&root, ARENA_BASE + 4 * LOCAL_PAGE_SIZE,
					       4 * LOCAL_PAGE_SIZE) == 0);
	mix(&digest, digest_tree(&root));

	a = __page_alloc_rbtree_alloc_pages(&root, 1, 0);
	require(a == ARENA_BASE);
	mix(&digest, a);
	mix(&digest, digest_tree(&root));

	b = __page_alloc_rbtree_alloc_pages(&root, 2, 2);
	require(b == ARENA_BASE + 4 * LOCAL_PAGE_SIZE);
	mix(&digest, b);
	mix(&digest, digest_tree(&root));

	require(__page_alloc_rbtree_free_range(&root, a, LOCAL_PAGE_SIZE) == 0);
	mix(&digest, digest_tree(&root));
	require(__page_alloc_rbtree_free_range(&root, b, 2 * LOCAL_PAGE_SIZE) == 0);
	mix(&digest, digest_tree(&root));

	zero_at_free = 0;
	c = __page_alloc_rbtree_alloc_pages(&root, 10, 0);
	require(c == ARENA_BASE);
	mix(&digest, c);
	mix(&digest, digest_tree(&root));
	require(root.rb_node == NULL);

	require(__page_alloc_rbtree_free_range(&root, ARENA_BASE, 10 * LOCAL_PAGE_SIZE) == 0);
	require(__page_alloc_rbtree_free_range(&root, ARENA_BASE + LOCAL_PAGE_SIZE,
					       LOCAL_PAGE_SIZE) == 22);
	mix(&digest, digest_tree(&root));
	require(__page_alloc_rbtree_alloc_pages(&root, 16, 0) == 0);
	mix(&digest, digest_tree(&root));

	require(__page_alloc_rbtree_reserve_pages(&root,
						  ARENA_BASE + 2 * LOCAL_PAGE_SIZE,
						  3) == ARENA_BASE + 2 * LOCAL_PAGE_SIZE);
	mix(&digest, digest_tree(&root));
	require(__page_alloc_rbtree_reserve_pages(&root,
						  ARENA_BASE + 2 * LOCAL_PAGE_SIZE,
						  1) == 0);
	mix(&digest, digest_tree(&root));
	{
		struct free_chunk *chunk;
		int chunks = 0;

		while ((chunk = __page_alloc_rbtree_get_root_chunk(&root))) {
			require((void *)chunk == phys_to_virt(chunk->addr));
			mix(&digest, chunk->addr);
			mix(&digest, chunk->size);
			chunks++;
		}

		require(chunks == 2);
		require(root.rb_node == NULL);
	}
	mix(&digest, digest_tree(&root));

	printf("page_alloc ok digest=%016lx\n", digest);
	return 0;
}
EOF_PAGE_ALLOC

cat > "${tmpdir}/page_alloc_bitmap_equiv.c" <<'EOF_PAGE_ALLOC_BITMAP'
extern int printf(const char *, ...);
extern void exit(int);
extern void abort(void);

#ifndef NULL
#define NULL ((void *)0)
#endif

#define ARENA_BASE 0x4000000UL
#define ARENA_PAGES 256
#define ARENA_SIZE (ARENA_PAGES * LOCAL_PAGE_SIZE)
#define LOCAL_PAGE_SIZE 4096UL

static unsigned char initial_desc[4096] __attribute__((aligned(64)));
static unsigned char page_arena[ARENA_SIZE];

int ihk_mc_chk_page_address(unsigned long mem_addr)
{
	(void)mem_addr;
	return 0;
}

unsigned long virt_to_phys(void *v)
{
	return (unsigned long)v;
}

void *phys_to_virt(unsigned long p)
{
	if (p < ARENA_BASE || p >= ARENA_BASE + ARENA_SIZE)
		exit(92);
	return page_arena + (p - ARENA_BASE);
}

int kprintf(const char *format, ...)
{
	(void)format;
	return 0;
}

void panic(const char *message)
{
	(void)message;
	abort();
}

void preempt_disable(void) {}
void preempt_enable(void) {}
void cpu_pause(void) {}
unsigned long cpu_disable_interrupt_save(void) { return 0; }
void cpu_restore_interrupt(unsigned long irqstate) { (void)irqstate; }

#include "lib/page_alloc.c"

int cpu_local_var_initialized;

int ihk_mc_get_processor_id(void)
{
	return 0;
}

struct cpu_local_var *get_cpu_local_var(int id)
{
	(void)id;
	return NULL;
}

int ihk_ikc_send(struct ihk_ikc_channel_desc *channel, void *p, int opt)
{
	(void)channel;
	(void)p;
	(void)opt;
	return 0;
}

int ihk_mc_get_nr_numa_nodes(void)
{
	exit(95);
}

struct ihk_mc_numa_node *ihk_mc_get_numa_node_by_distance(int i)
{
	(void)i;
	exit(96);
	return NULL;
}

void *_ihk_mc_alloc_aligned_pages_node(int npages, int p2align,
	ihk_mc_ap_flag flag, int node, int is_user, uintptr_t virt_addr,
	char *file, int line)
{
	(void)npages;
	(void)p2align;
	(void)flag;
	(void)node;
	(void)is_user;
	(void)virt_addr;
	(void)file;
	(void)line;
	return NULL;
}

void _ihk_mc_free_pages(void *ptr, int npages, int is_user, char *file, int line)
{
	(void)ptr;
	(void)npages;
	(void)is_user;
	(void)file;
	(void)line;
}

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

static void require_at(int condition, int line)
{
	if (!condition) {
		printf("require failed line=%d\n", line);
		exit(91);
	}
}

#define require(condition) require_at((condition), __LINE__)

static void sample_state(unsigned long *digest, void *desc)
{
	mix(digest, ihk_pagealloc_count(desc));
	mix(digest, (unsigned long)ihk_pagealloc_query_free(desc));
}

static void fill_page_arena(unsigned char value)
{
	for (unsigned long i = 0; i < sizeof(page_arena); i++)
		page_arena[i] = value;
}

static int page_is_free(void *desc, int page)
{
	struct ihk_page_allocator_desc *d = desc;
	return !(d->map[page >> 6] & (1UL << (page & 63)));
}

static void verify_zeroed_free_pages(unsigned long *digest, void *desc)
{
	for (int page = 0; page < ARENA_PAGES; page++) {
		int expected = page_is_free(desc, page) ? 0 : 0x5a;
		unsigned char *base = page_arena + page * LOCAL_PAGE_SIZE;

		for (int offset = 0; offset < LOCAL_PAGE_SIZE; offset++) {
			if (base[offset] != (unsigned char)expected) {
				printf("zero mismatch page=%d offset=%d got=%u expected=%d\n",
				       page, offset, (unsigned int)base[offset], expected);
				exit(93);
			}
		}

		mix(digest, ((unsigned long)page << 8) | (unsigned long)expected);
	}
}

static unsigned long digest_free_tree(struct rb_root *root)
{
	unsigned long digest = 0;
	struct rb_node *node;

	for (node = rb_first(root); node; node = rb_next(node)) {
		struct free_chunk *chunk = container_of(node, struct free_chunk, node);

		mix(&digest, chunk->addr);
		mix(&digest, chunk->size);
	}

	return digest;
}

static void require_page_bytes(int page, int start, unsigned char expected)
{
	unsigned char *base = page_arena + page * LOCAL_PAGE_SIZE;

	for (int offset = start; offset < LOCAL_PAGE_SIZE; offset++) {
		if (base[offset] != expected) {
			printf("page byte mismatch page=%d offset=%d got=%u expected=%u\n",
			       page, offset, (unsigned int)base[offset],
			       (unsigned int)expected);
			exit(94);
		}
	}
}

int main(void)
{
	unsigned long desc_pages = 0;
	unsigned long digest = 0;
	void *desc;
	unsigned long a, b, c, d;

	memset(initial_desc, 0xcc, sizeof(initial_desc));
	desc = __ihk_pagealloc_init(ARENA_BASE, 256 * LOCAL_PAGE_SIZE,
				    LOCAL_PAGE_SIZE, initial_desc, &desc_pages);
	require(desc == initial_desc);
	require(desc_pages == 1);
	sample_state(&digest, desc);
	require(ihk_pagealloc_count(desc) == 256);
	require(ihk_pagealloc_query_free(desc) == 256);

	ihk_pagealloc_reserve(desc, ARENA_BASE + 8 * LOCAL_PAGE_SIZE,
			      ARENA_BASE + 12 * LOCAL_PAGE_SIZE);
	sample_state(&digest, desc);
	require(ihk_pagealloc_count(desc) == 252);

	a = ihk_pagealloc_alloc(desc, 1, 0);
	require(a == ARENA_BASE);
	mix(&digest, a);
	sample_state(&digest, desc);

	b = ihk_pagealloc_alloc(desc, 3, 2);
	require(b == ARENA_BASE + 4 * LOCAL_PAGE_SIZE);
	mix(&digest, b);
	sample_state(&digest, desc);

	c = ihk_pagealloc_alloc(desc, 32, 5);
	require(c == ARENA_BASE + 64 * LOCAL_PAGE_SIZE);
	mix(&digest, c);
	sample_state(&digest, desc);

	ihk_pagealloc_free(desc, a, 1);
	sample_state(&digest, desc);
	d = ihk_pagealloc_alloc(desc, 2, 0);
	require(d == ARENA_BASE);
	mix(&digest, d);
	sample_state(&digest, desc);

	ihk_pagealloc_free(desc, d, 2);
	ihk_pagealloc_free(desc, b, 3);
	ihk_pagealloc_free(desc, c, 32);
	sample_state(&digest, desc);
	require(ihk_pagealloc_count(desc) == 252);

	ihk_pagealloc_reserve(desc, ARENA_BASE + 128 * LOCAL_PAGE_SIZE,
			      ARENA_BASE + 192 * LOCAL_PAGE_SIZE);
	sample_state(&digest, desc);
	require(ihk_pagealloc_count(desc) == 188);

	c = ihk_pagealloc_alloc(desc, 64, 6);
	require(c == ARENA_BASE + 64 * LOCAL_PAGE_SIZE);
	mix(&digest, c);
	sample_state(&digest, desc);
	require(ihk_pagealloc_count(desc) == 124);

	fill_page_arena(0x5a);
	__ihk_pagealloc_zero_free_pages(desc);
	verify_zeroed_free_pages(&digest, desc);

	{
		struct ihk_mc_numa_node numa;
		unsigned long base = ARENA_BASE + 200 * LOCAL_PAGE_SIZE;

		memset(&numa, 0, sizeof(numa));
		numa.min_addr = ~0UL;
		fill_page_arena(0x7b);
		zero_at_free = 1;

		require(ihk_numa_add_free_pages(&numa, base,
						4 * LOCAL_PAGE_SIZE) == 0);
		require(numa.nr_pages == 4);
		require(numa.nr_free_pages == 4);
		require(numa.min_addr == base);
		require(numa.max_addr == base + 4 * LOCAL_PAGE_SIZE);
		require_page_bytes(199, 0, 0x7b);
		require_page_bytes(200, sizeof(struct free_chunk), 0);
		require_page_bytes(201, 0, 0);
		require_page_bytes(202, 0, 0);
		require_page_bytes(203, 0, 0);
		require_page_bytes(204, 0, 0x7b);
		mix(&digest, digest_free_tree(&numa.free_chunks));

		require(ihk_numa_add_free_pages(&numa,
						base + 4 * LOCAL_PAGE_SIZE,
						2 * LOCAL_PAGE_SIZE) == 0);
		require(numa.nr_pages == 6);
		require(numa.nr_free_pages == 6);
		require(numa.min_addr == base);
		require(numa.max_addr == base + 6 * LOCAL_PAGE_SIZE);
		require_page_bytes(204, 0, 0);
		require_page_bytes(205, 0, 0);
		mix(&digest, digest_free_tree(&numa.free_chunks));

		require(ihk_numa_add_free_pages(&numa,
						base + 2 * LOCAL_PAGE_SIZE,
						LOCAL_PAGE_SIZE) == 22);
		require(numa.nr_pages == 6);
		require(numa.nr_free_pages == 6);
		mix(&digest, digest_free_tree(&numa.free_chunks));

		zero_at_free = 0;
		require(ihk_numa_add_free_pages(&numa,
						base - 2 * LOCAL_PAGE_SIZE,
						2 * LOCAL_PAGE_SIZE) == 0);
		require(numa.nr_pages == 8);
		require(numa.nr_free_pages == 8);
		require(numa.min_addr == base - 2 * LOCAL_PAGE_SIZE);
		require(numa.max_addr == base + 6 * LOCAL_PAGE_SIZE);
		mix(&digest, digest_free_tree(&numa.free_chunks));

		require(__page_alloc_rbtree_alloc_pages(&numa.free_chunks, 8, 0) ==
			base - 2 * LOCAL_PAGE_SIZE);
		require(numa.free_chunks.rb_node == NULL);

		{
			struct free_chunk *small =
				(struct free_chunk *)phys_to_virt(ARENA_BASE +
						220 * LOCAL_PAGE_SIZE);
			struct free_chunk *big =
				(struct free_chunk *)phys_to_virt(ARENA_BASE +
						224 * LOCAL_PAGE_SIZE);
			unsigned long small_addr;
			unsigned long big_addr;
			int zeroed;

			fill_page_arena(0x33);
			memset(small, 0, sizeof(*small));
			memset(big, 0, sizeof(*big));
			small->addr = ARENA_BASE + 220 * LOCAL_PAGE_SIZE;
			small->size = LOCAL_PAGE_SIZE;
			big->addr = ARENA_BASE + 224 * LOCAL_PAGE_SIZE;
			big->size = 3 * LOCAL_PAGE_SIZE;
			small_addr = small->addr;
			big_addr = big->addr;
			numa.to_zero_list.first = NULL;
			numa.zeroed_list.first = NULL;
			numa.nr_pages = 4;
			numa.nr_free_pages = 0;
			numa.nr_to_zero_pages.counter = 4;
			zero_at_free = 1;

			llist_add(&big->list, &numa.to_zero_list);
			llist_add(&small->list, &numa.to_zero_list);

			zeroed = __ihk_numa_zero_free_pages(&numa, 2);
			require(zeroed == 3);
			require(numa.nr_to_zero_pages.counter == 1);
			require(numa.zeroed_list.first == &big->list);
			require(numa.to_zero_list.first == &small->list);
			require_page_bytes(220, sizeof(struct free_chunk), 0x33);
			require_page_bytes(224, sizeof(struct free_chunk), 0);
			require_page_bytes(225, 0, 0);
			require_page_bytes(226, 0, 0);
			mix(&digest, (unsigned long)zeroed);
			mix(&digest, (unsigned long)numa.nr_to_zero_pages.counter);

			zeroed = __ihk_numa_zero_free_pages(&numa, 0);
			require(zeroed == 1);
			require(numa.nr_to_zero_pages.counter == 0);
			require(numa.zeroed_list.first == &small->list);
			require(numa.to_zero_list.first == NULL);
			require_page_bytes(220, sizeof(struct free_chunk), 0);
			mix(&digest, (unsigned long)zeroed);
			mix(&digest, (unsigned long)numa.nr_to_zero_pages.counter);

			c = ihk_numa_alloc_pages(&numa, 3, 0);
			require(c == big_addr);
			require(numa.nr_free_pages == 1);
			require(numa.zeroed_list.first == NULL);
			require(numa.to_zero_list.first == NULL);
			mix(&digest, c);
			mix(&digest, numa.nr_free_pages);

			c = ihk_numa_alloc_pages(&numa, 1, 0);
			require(c == small_addr);
			require(numa.nr_free_pages == 0);
			require(numa.free_chunks.rb_node == NULL);
			mix(&digest, c);
			mix(&digest, numa.nr_free_pages);

			numa.min_addr = small_addr;
			numa.max_addr = big_addr + 3 * LOCAL_PAGE_SIZE;
			zero_at_free = 0;
			deferred_zero_at_free = 1;
			ihk_numa_free_pages(&numa, small_addr, 1);
			require(numa.nr_free_pages == 1);
			require(numa.to_zero_list.first == NULL);
			mix(&digest, digest_free_tree(&numa.free_chunks));
			c = ihk_numa_alloc_pages(&numa, 1, 0);
			require(c == small_addr);
			require(numa.nr_free_pages == 0);
			require(numa.free_chunks.rb_node == NULL);
			mix(&digest, c);
			mix(&digest, numa.nr_free_pages);

			fill_page_arena(0x44);
			zero_at_free = 1;
			deferred_zero_at_free = 0;
			ihk_numa_free_pages(&numa, small_addr, 1);
			require(numa.nr_free_pages == 1);
			require_page_bytes(220, sizeof(struct free_chunk), 0);
			mix(&digest, digest_free_tree(&numa.free_chunks));
			c = ihk_numa_alloc_pages(&numa, 1, 0);
			require(c == small_addr);
			require(numa.nr_free_pages == 0);
			require(numa.free_chunks.rb_node == NULL);
			mix(&digest, c);
			mix(&digest, numa.nr_free_pages);

			fill_page_arena(0x55);
			zero_at_free = 1;
			deferred_zero_at_free = 1;
			numa.nr_to_zero_pages.counter = 0;
			numa.to_zero_list.first = NULL;
			numa.zeroed_list.first = NULL;
			ihk_numa_free_pages(&numa, big_addr, 3);
			require(numa.nr_free_pages == 0);
			require(numa.nr_to_zero_pages.counter == 3);
			require(numa.to_zero_list.first == &big->list);
			require(numa.zeroed_list.first == NULL);
			require(big->addr == big_addr);
			require(big->size == 3 * LOCAL_PAGE_SIZE);
			require_page_bytes(224, sizeof(struct free_chunk), 0x55);
			require_page_bytes(225, 0, 0x55);
			mix(&digest, (unsigned long)numa.nr_to_zero_pages.counter);

			zeroed = __ihk_numa_zero_free_pages(&numa, 0);
			require(zeroed == 3);
			require(numa.nr_to_zero_pages.counter == 0);
			require(numa.to_zero_list.first == NULL);
			require(numa.zeroed_list.first == &big->list);
			require_page_bytes(224, sizeof(struct free_chunk), 0);
			require_page_bytes(225, 0, 0);
			require_page_bytes(226, 0, 0);
			mix(&digest, (unsigned long)zeroed);

			c = ihk_numa_alloc_pages(&numa, 3, 0);
			require(c == big_addr);
			require(numa.nr_free_pages == 0);
			require(numa.free_chunks.rb_node == NULL);
			require(numa.zeroed_list.first == NULL);
			mix(&digest, c);
			mix(&digest, numa.nr_free_pages);
		}
	}

	printf("page_alloc_bitmap ok digest=%016lx\n", digest);
	return 0;
}
EOF_PAGE_ALLOC_BITMAP

cat > "${tmpdir}/rust_stubs.c" <<'EOF_STUBS'
int ihk_mc_chk_page_address(unsigned long mem_addr) { (void)mem_addr; return 0; }
unsigned long virt_to_phys(void *v) { return (unsigned long)v; }
void *phys_to_virt(unsigned long p) { return (void *)p; }
int zero_at_free = 1;
EOF_STUBS

cat > "${tmpdir}/ctype_stub.c" <<'EOF_CTYPE'
int kprintf(const char *format, ...)
{
	(void)format;
	return 0;
}

void panic(const char *message)
{
	(void)message;
	__builtin_abort();
}

unsigned char _ctype[256] = {
	['A' ... 'F'] = 0x01 | 0x40,
	['G' ... 'Z'] = 0x01,
	['a' ... 'f'] = 0x02 | 0x40,
	['g' ... 'z'] = 0x02,
	['0' ... '9'] = 0x04 | 0x40,
	[' '] = 0x20 | 0x80,
	['\f'] = 0x20,
	['\n'] = 0x20,
	['\r'] = 0x20,
	['\t'] = 0x20,
	['\v'] = 0x20,
};
EOF_CTYPE

cat > "${tmpdir}/config.h" <<'EOF_CONFIG'
/* Minimal generated-config placeholder for page_alloc equivalence. */
EOF_CONFIG

mkdir -p "${tmpdir}/out"

inc=(
	-Ilib/include
	-Ikernel/include
	-Iarch/x86_64/kernel/include
	-Iarch/x86_64/kernel/include/ihk
	-Iihk/cokernel/smp/x86_64/include
	-Iihk/ikc/include
	-Iihk/linux/include
)
sys=(-isystem "$(cc -print-file-name=include)")
kflags=(-ffreestanding -nostdinc "${sys[@]}" -D__KERNEL__ -DIHK_OS_MANYCORE "${inc[@]}")

cc "${kflags[@]}" -c kernel/rbtree.c -o "${tmpdir}/out/rbtree_c.o"
cc "${kflags[@]}" -c kernel/llist.c -o "${tmpdir}/out/llist_c.o"
cc "${kflags[@]}" -ffunction-sections -fdata-sections -c lib/bitmap.c -o "${tmpdir}/out/bitmap_c.o"
cc "${kflags[@]}" -ffunction-sections -fdata-sections -c lib/bitops.c -o "${tmpdir}/out/bitops_c.o"

rustc --crate-name mckernel_rust \
	--crate-type lib \
	--edition=2021 \
	-C panic=abort \
	-C opt-level=2 \
	-C debuginfo=2 \
	-C code-model=large \
	-C relocation-model=static \
	-C no-redzone=yes \
	-C force-frame-pointers=yes \
	-C overflow-checks=off \
	-C force-unwind-tables=no \
	-C no-vectorize-loops \
	-C no-vectorize-slp \
	--emit=obj="${tmpdir}/out/mckernel_rust.o" \
	kernel/rust/lib.rs

cc "${tmpdir}/rbtree_equiv.c" "${tmpdir}/out/rbtree_c.o" -o "${tmpdir}/out/rbtree_c"
cc "${tmpdir}/rbtree_equiv.c" "${tmpdir}/out/mckernel_rust.o" -o "${tmpdir}/out/rbtree_rust"
cc "${tmpdir}/llist_equiv.c" "${tmpdir}/out/llist_c.o" -o "${tmpdir}/out/llist_c"
cc "${tmpdir}/llist_equiv.c" "${tmpdir}/rust_stubs.c" "${tmpdir}/out/mckernel_rust.o" -o "${tmpdir}/out/llist_rust"
cc -Wl,--gc-sections "${tmpdir}/bitmap_equiv.c" "${tmpdir}/ctype_stub.c" \
	"${tmpdir}/out/bitmap_c.o" "${tmpdir}/out/bitops_c.o" -o "${tmpdir}/out/bitmap_c"
cc "${tmpdir}/bitmap_equiv.c" "${tmpdir}/rust_stubs.c" \
	"${tmpdir}/out/mckernel_rust.o" -o "${tmpdir}/out/bitmap_rust"
cc "${kflags[@]}" -I"${tmpdir}" -I. -ffunction-sections -fdata-sections -DPAGE_ALLOC_USE_C \
	"${tmpdir}/page_alloc_equiv.c" "${tmpdir}/out/rbtree_c.o" \
	-Wl,--gc-sections -o "${tmpdir}/out/page_alloc_c"
cc "${tmpdir}/page_alloc_equiv.c" "${tmpdir}/out/mckernel_rust.o" \
	-o "${tmpdir}/out/page_alloc_rust"
cc "${kflags[@]}" -I"${tmpdir}" -I. -ffunction-sections -fdata-sections \
	"${tmpdir}/page_alloc_bitmap_equiv.c" "${tmpdir}/out/rbtree_c.o" \
	"${tmpdir}/out/llist_c.o" \
	-Wl,--gc-sections -o "${tmpdir}/out/page_alloc_bitmap_c"
cc "${kflags[@]}" -I"${tmpdir}" -I. -ffunction-sections -fdata-sections \
	-DMCKERNEL_RUST_PAGEALLOC_BITMAP -DMCKERNEL_RUST_PAGE_ALLOC_RBTREE \
	"${tmpdir}/page_alloc_bitmap_equiv.c" "${tmpdir}/out/mckernel_rust.o" \
	-Wl,--gc-sections -o "${tmpdir}/out/page_alloc_bitmap_rust"

"${tmpdir}/out/rbtree_c" > "${tmpdir}/out/rbtree_c.out"
"${tmpdir}/out/rbtree_rust" > "${tmpdir}/out/rbtree_rust.out"
"${tmpdir}/out/llist_c" > "${tmpdir}/out/llist_c.out"
"${tmpdir}/out/llist_rust" > "${tmpdir}/out/llist_rust.out"
"${tmpdir}/out/bitmap_c" > "${tmpdir}/out/bitmap_c.out"
"${tmpdir}/out/bitmap_rust" > "${tmpdir}/out/bitmap_rust.out"
"${tmpdir}/out/page_alloc_c" > "${tmpdir}/out/page_alloc_c.out"
"${tmpdir}/out/page_alloc_rust" > "${tmpdir}/out/page_alloc_rust.out"
"${tmpdir}/out/page_alloc_bitmap_c" > "${tmpdir}/out/page_alloc_bitmap_c.out" || {
	cat "${tmpdir}/out/page_alloc_bitmap_c.out"
	exit 1
}
"${tmpdir}/out/page_alloc_bitmap_rust" > "${tmpdir}/out/page_alloc_bitmap_rust.out" || {
	cat "${tmpdir}/out/page_alloc_bitmap_rust.out"
	exit 1
}

diff -u "${tmpdir}/out/rbtree_c.out" "${tmpdir}/out/rbtree_rust.out"
diff -u "${tmpdir}/out/llist_c.out" "${tmpdir}/out/llist_rust.out"
diff -u "${tmpdir}/out/bitmap_c.out" "${tmpdir}/out/bitmap_rust.out"
diff -u "${tmpdir}/out/page_alloc_c.out" "${tmpdir}/out/page_alloc_rust.out"
diff -u "${tmpdir}/out/page_alloc_bitmap_c.out" "${tmpdir}/out/page_alloc_bitmap_rust.out"

nm -u "${tmpdir}/out/mckernel_rust.o" | tee "${tmpdir}/out/rust.undefined"
grep -Eq 'U ihk_mc_chk_page_address' "${tmpdir}/out/rust.undefined"
grep -Eq 'U phys_to_virt' "${tmpdir}/out/rust.undefined"
grep -Eq 'U virt_to_phys' "${tmpdir}/out/rust.undefined"
grep -Eq 'U zero_at_free' "${tmpdir}/out/rust.undefined"
test "$(grep -c ' U ' "${tmpdir}/out/rust.undefined")" -eq 4

simd_count="$(objdump -d "${tmpdir}/out/mckernel_rust.o" |
	grep -Eic 'xmm|ymm|mmx|movdqa|movdqu|movups|pshuf|padd|pand|pxor|popcnt' || true)"
test "${simd_count}" -eq 0

cat "${tmpdir}/out/rbtree_c.out"
cat "${tmpdir}/out/llist_c.out"
cat "${tmpdir}/out/bitmap_c.out"
cat "${tmpdir}/out/page_alloc_c.out"
cat "${tmpdir}/out/page_alloc_bitmap_c.out"
echo "rust object unresolved symbols and SIMD checks ok"
