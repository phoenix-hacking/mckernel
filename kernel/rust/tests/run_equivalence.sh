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

cat > "${tmpdir}/waitq_equiv.c" <<'EOF_WAITQ'
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

struct thread;
struct waitq_entry;

typedef int (*waitq_func_t)(struct waitq_entry *, unsigned, int, void *);

typedef struct ihk_spinlock {
	union {
		unsigned int head_tail;
		struct {
			unsigned short head;
			unsigned short tail;
		} tickets;
	};
} ihk_spinlock_t;

struct list_head {
	struct list_head *next;
	struct list_head *prev;
};

typedef struct waitq {
	ihk_spinlock_t lock;
	struct list_head waitq;
} waitq_t;

typedef struct waitq_entry {
	struct list_head link;
	void *private;
	unsigned int flags;
	waitq_func_t func;
} waitq_entry_t;

struct item {
	int id;
	int wakes;
	waitq_entry_t entry;
};

extern void waitq_init(waitq_t *);
extern void waitq_init_entry(waitq_entry_t *, struct thread *);
extern void waitq_add_entry_locked(waitq_t *, waitq_entry_t *);
extern void waitq_remove_entry_locked(waitq_t *, waitq_entry_t *);
extern int waitq_wake_nr_locked(waitq_t *, int);
extern int waitq_wake_schedule_needed_result(int);

int sched_wakeup_thread(struct thread *thread, int state)
{
	return ((uintptr_t)thread ^ (unsigned int)state) & 0x7fffffff;
}

int sched_wakeup_thread_locked(struct thread *thread, int state)
{
	return (((uintptr_t)thread << 1) ^ (unsigned int)state) & 0x7fffffff;
}

void schedule(void) {}
void preempt_disable(void) {}
void preempt_enable(void) {}

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

static void require(int condition)
{
	if (!condition)
		exit(21);
}

static struct item *item_from_entry(waitq_entry_t *entry)
{
	return (struct item *)((char *)entry - offsetof(struct item, entry));
}

static struct item *item_from_link(struct list_head *link)
{
	return item_from_entry((waitq_entry_t *)((char *)link -
		offsetof(waitq_entry_t, link)));
}

static int record_wake(waitq_entry_t *entry, unsigned mode, int flags, void *key)
{
	struct item *item = item_from_entry(entry);

	item->wakes += 1 + (int)mode + flags + (key != NULL);
	return item->id;
}

static void digest_waitq(unsigned long *digest, waitq_t *waitq)
{
	struct list_head *head = &waitq->waitq;
	struct list_head *pos = head->next;
	int count = 0;

	require(head->prev->next == head);
	require(head->next->prev == head);
	mix(digest, waitq->lock.head_tail);
	while (pos != head) {
		struct item *item = item_from_link(pos);

		require(pos->next->prev == pos);
		require(pos->prev->next == pos);
		mix(digest, ((unsigned long)(unsigned int)item->id << 32) |
			    (unsigned int)item->wakes);
		pos = pos->next;
		require(++count < 32);
	}
	mix(digest, (unsigned long)count);
}

int main(void)
{
	waitq_t waitq;
	struct item items[5];
	unsigned long digest = 0x0bad5eed7157cafeUL;
	int ret;

	for (int i = 0; i < 5; i++) {
		items[i].id = i + 10;
		items[i].wakes = 0;
		items[i].entry.flags = 0xf00d0000U + i;
		waitq_init_entry(&items[i].entry,
				 (struct thread *)(uintptr_t)(0x1000 + i * 0x40));
		require(items[i].entry.func != NULL);
		mix(&digest, (unsigned long)items[i].entry.func(
			&items[i].entry, 0, 0, NULL));
		items[i].entry.func = record_wake;
		require(items[i].entry.private ==
			(void *)(uintptr_t)(0x1000 + i * 0x40));
		require(items[i].entry.flags == 0xf00d0000U + i);
	}

	waitq.lock.head_tail = 0xffffffffU;
	waitq_init(&waitq);
	require(waitq.lock.head_tail == 0);
	digest_waitq(&digest, &waitq);

	waitq_add_entry_locked(&waitq, &items[0].entry);
	waitq_add_entry_locked(&waitq, &items[1].entry);
	waitq_add_entry_locked(&waitq, &items[2].entry);
	digest_waitq(&digest, &waitq);

	ret = waitq_wake_nr_locked(&waitq, 0);
	require(ret == 0);
	require(waitq_wake_schedule_needed_result(ret) == 0);
	require(items[0].wakes == 0 && items[1].wakes == 0 && items[2].wakes == 0);
	mix(&digest, (unsigned long)(int)ret);

	ret = waitq_wake_nr_locked(&waitq, 2);
	require(ret == 2);
	require(waitq_wake_schedule_needed_result(ret) == 1);
	require(items[0].wakes == 1 && items[1].wakes == 1 && items[2].wakes == 0);
	mix(&digest, (unsigned long)(int)ret);
	digest_waitq(&digest, &waitq);

	waitq_remove_entry_locked(&waitq, &items[1].entry);
	require(items[1].entry.link.next == &items[1].entry.link);
	require(items[1].entry.link.prev == &items[1].entry.link);
	digest_waitq(&digest, &waitq);

	waitq_add_entry_locked(&waitq, &items[3].entry);
	waitq_add_entry_locked(&waitq, &items[1].entry);
	digest_waitq(&digest, &waitq);

	ret = waitq_wake_nr_locked(&waitq, 10);
	require(ret == 3);
	require(items[0].wakes == 2 && items[2].wakes == 1 &&
		items[3].wakes == 1 && items[1].wakes == 2);
	mix(&digest, (unsigned long)(int)ret);
	digest_waitq(&digest, &waitq);

	waitq_remove_entry_locked(&waitq, &items[0].entry);
	waitq_remove_entry_locked(&waitq, &items[2].entry);
	waitq_remove_entry_locked(&waitq, &items[3].entry);
	waitq_remove_entry_locked(&waitq, &items[1].entry);
	digest_waitq(&digest, &waitq);

	ret = waitq_wake_nr_locked(&waitq, 1);
	require(ret == -1);
	require(waitq_wake_schedule_needed_result(ret) == 0);
	mix(&digest, (unsigned long)(int)ret);

	printf("waitq ok digest=%016lx\n", digest);
	return 0;
}
EOF_WAITQ

cat > "${tmpdir}/mem_init_helpers_equiv.c" <<'EOF_MEM_INIT'
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

extern int is_mckernel_memory(unsigned long, unsigned long);
extern int phys_to_nid(unsigned long);
extern char *find_command_line(char *);

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

static long ptr_offset(const char *base, const char *ptr)
{
	if (!base || !ptr)
		return -1;
	return ptr - base;
}

static void set_chunks(const struct mem_chunk *src, int count)
{
	nr_chunks = count;
	for (int i = 0; i < count; i++)
		chunks[i] = src[i];
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

	printf("mem_init_helpers ok digest=%016lx\n", digest);
	return 0;
}
EOF_MEM_INIT

cat > "${tmpdir}/page_helpers_equiv.c" <<'EOF_PAGE_HELPERS'
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

struct list_head {
	struct list_head *next;
	struct list_head *prev;
};

typedef struct {
	int counter;
} ihk_atomic_t;

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

enum {
	PM_NONE = 0x00,
	PM_PENDING_FREE = 0x01,
	PM_WILL_PAGEIO = 0x02,
	PM_PAGEIO = 0x03,
	PM_DONE_PAGEIO = 0x04,
	PM_PAGEIO_EOF = 0x05,
	PM_PAGEIO_ERROR = 0x06,
	PM_MAPPED = 0x07,
	MF_REG_FILE = 0x1000,
	MF_SHM = 0x40000,
};

extern uintptr_t page_to_phys(struct page *);
extern int is_splitable(struct page *, uint32_t);
extern int page_mode_in_memobj_result(int);
extern int page_multi_mapped_result(int);

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

static void mix_signed(unsigned long *digest, long value)
{
	mix(digest, (unsigned long)value);
}

static struct page make_page(uint8_t mode, int count, uint64_t phys)
{
	struct page page = {
		.mode = mode,
		.phys = phys,
		.count = { .counter = count },
		.mapped = { .counter64 = 0x1234 },
		.offset = 0x5678,
		.pgshift = 12,
	};

	page.list.next = &page.list;
	page.list.prev = &page.list;
	page.hash.next = &page.hash;
	page.hash.prev = &page.hash;
	return page;
}

int main(void)
{
	static const uint8_t modes[] = {
		PM_NONE, PM_PENDING_FREE, PM_WILL_PAGEIO, PM_PAGEIO,
		PM_DONE_PAGEIO, PM_PAGEIO_EOF, PM_PAGEIO_ERROR, PM_MAPPED,
		0xff,
	};
	static const int counts[] = { 0, 1, 2, 7 };
	static const uint32_t flags[] = { 0, MF_REG_FILE, MF_SHM,
					  MF_REG_FILE | MF_SHM };
	unsigned long digest = 0x9a17c0de51ab1e5UL;

	if (sizeof(struct page) != 80 ||
	    offsetof(struct page, mode) != 32 ||
	    offsetof(struct page, phys) != 40 ||
	    offsetof(struct page, count) != 48 ||
	    offsetof(struct page, mapped) != 56 ||
	    offsetof(struct page, pgshift) != 72)
		exit(2);

	mix(&digest, page_to_phys(NULL));
	mix_signed(&digest, is_splitable(NULL, 0));
	mix_signed(&digest, is_splitable(NULL, MF_SHM));

	for (unsigned int i = 0; i < sizeof(modes) / sizeof(modes[0]); i++)
		mix_signed(&digest, page_mode_in_memobj_result(modes[i]));
	for (unsigned int i = 0; i < sizeof(counts) / sizeof(counts[0]); i++)
		mix_signed(&digest, page_multi_mapped_result(counts[i]));

	for (unsigned int i = 0; i < sizeof(modes) / sizeof(modes[0]); i++) {
		for (unsigned int j = 0; j < sizeof(counts) / sizeof(counts[0]); j++) {
			struct page page = make_page(modes[i], counts[j],
				0xabc000UL + (i << 12) + (j << 5));

			mix(&digest, page_to_phys(&page));
			for (unsigned int k = 0; k < sizeof(flags) / sizeof(flags[0]); k++) {
				mix_signed(&digest, is_splitable(&page, flags[k]));
			}
		}
	}

	printf("page_helpers ok digest=%016lx\n", digest);
	return 0;
}
EOF_PAGE_HELPERS

cat > "${tmpdir}/shmid_helpers_equiv.c" <<'EOF_SHMID_HELPERS'
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

extern unsigned long shmid_index[512];
extern int get_shmid_max_index(void);
extern int get_shmid_index(void);
extern int shmid_to_index(int);
extern int shmid_to_seq(int);
extern int make_shmid(void *);
extern int shmget_existing_access_result(unsigned int, unsigned int, int,
					 unsigned int, unsigned int,
					 unsigned int, unsigned int,
					 uint16_t);
extern int shmat_access_result(unsigned int, unsigned int, int,
			       unsigned int, unsigned int,
			       unsigned int, unsigned int, uint16_t);
extern int shmctl_ipc_stat_access_result(unsigned int, unsigned int,
					 unsigned int, unsigned int,
					 unsigned int, unsigned int,
					 uint16_t);
extern int shm_owner_result(unsigned int, unsigned int, unsigned int);
extern int shm_owner_or_cap_result(int, unsigned int, unsigned int,
				   unsigned int);
extern int shmlock_rlimit_result(int, unsigned long, unsigned long,
				 unsigned long);

struct shmobj_fixture {
	uint8_t pad_to_index[56];
	int index;
	uint8_t pad_to_seq[44];
	uint16_t seq;
	uint8_t rest[126];
} __attribute__((aligned(8)));

struct perm_case {
	unsigned int euid;
	unsigned int egid;
	unsigned int uid;
	unsigned int cuid;
	unsigned int gid;
	unsigned int cgid;
	uint16_t mode;
	int shmflg;
};

struct rlimit_case {
	int has_cap;
	unsigned long rlim_cur;
	unsigned long user_locked;
	unsigned long size;
};

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

static void mix_signed(unsigned long *digest, long value)
{
	mix(digest, (unsigned long)value);
}

static void require(int condition)
{
	if (!condition)
		exit(23);
}

static void clear_index(void)
{
	for (int i = 0; i < 512; i++)
		shmid_index[i] = 0;
}

static void set_index_bit(int index)
{
	shmid_index[index / 64] |= 1UL << (index % 64);
}

static int test_index_bit(int index)
{
	return (shmid_index[index / 64] & (1UL << (index % 64))) != 0;
}

static void digest_words(unsigned long *digest, int first, int last)
{
	for (int i = first; i <= last; i++)
		mix(digest, shmid_index[i]);
}

int main(void)
{
	static const int preset_bits[] = {
		0, 1, 7, 63, 64, 65, 127, 128, 255, 4095,
		4096, 8191, 12345, 32766, 32767,
	};
	static const int holes[] = {
		0, 1, 2, 63, 64, 65, 130, 4096, 12000,
	};
	static const int shmids[] = {
		0, 1, 0xffff, 0x10000, 0x12345678, 0x7fffffff,
		-1, -2, -65536, -65535,
	};
	static const struct perm_case perms[] = {
		{ 0, 0, 10, 20, 30, 40, 0000, 0 },
		{ 10, 30, 10, 20, 30, 40, 0600, 0 },
		{ 20, 99, 10, 20, 30, 40, 0400, 010000 },
		{ 90, 30, 10, 20, 30, 40, 0060, 0 },
		{ 90, 40, 10, 20, 30, 40, 0040, 010000 },
		{ 90, 99, 10, 20, 30, 40, 0006, 0 },
		{ 90, 99, 10, 20, 30, 40, 0004, 010000 },
		{ 90, 99, 10, 20, 30, 40, 0000, 0 },
		{ 10, 99, 10, 20, 30, 40, 0777, 02000 },
		{ 11, 31, 10, 20, 30, 40, 0644, 01000 | 02000 },
	};
	static const struct rlimit_case rlimits[] = {
		{ 0, 0, 0, 0 },
		{ 1, 0, 0, 4096 },
		{ 0, 4096, 0, 4096 },
		{ 0, 4096, 4096, 1 },
		{ 0, 8192, 2048, 4096 },
		{ 0, 8192, 4096, 4097 },
		{ 0, ~0UL, ~0UL - 10, 4096 },
	};
	unsigned long digest = 0x514d4944c0ffeeUL;
	struct shmobj_fixture obj;

	clear_index();
	mix_signed(&digest, get_shmid_max_index());

	for (unsigned int i = 0; i < sizeof(preset_bits) / sizeof(preset_bits[0]); i++) {
		clear_index();
		for (unsigned int j = 0; j <= i; j++)
			set_index_bit(preset_bits[j]);
		mix_signed(&digest, get_shmid_max_index());
		digest_words(&digest, 0, 4);
		digest_words(&digest, 508, 511);
	}

	for (unsigned int h = 0; h < sizeof(holes) / sizeof(holes[0]); h++) {
		int hole = holes[h];

		clear_index();
		for (int bit = 0; bit < hole; bit++)
			set_index_bit(bit);
		for (int extra = hole + 1; extra < hole + 7 && extra < 32768; extra += 2)
			set_index_bit(extra);

		mix_signed(&digest, get_shmid_max_index());
		int allocated = get_shmid_index();
		require(allocated == hole);
		require(test_index_bit(hole));
		mix_signed(&digest, allocated);
		mix_signed(&digest, get_shmid_max_index());
		digest_words(&digest, hole / 64, hole / 64);
	}

	clear_index();
	for (int i = 0; i < 130; i++) {
		int allocated = get_shmid_index();
		require(allocated == i);
		mix_signed(&digest, allocated);
	}
	require(get_shmid_max_index() == 129);
	digest_words(&digest, 0, 3);

	for (unsigned int i = 0; i < sizeof(shmids) / sizeof(shmids[0]); i++) {
		mix_signed(&digest, shmid_to_index(shmids[i]));
		mix_signed(&digest, shmid_to_seq(shmids[i]));
	}

	for (int i = 0; i < 10; i++) {
		obj.index = i * 17;
		obj.seq = (uint16_t)(0x1234 + i * 31);
		mix_signed(&digest, make_shmid(&obj));
	}

	for (unsigned int i = 0; i < sizeof(perms) / sizeof(perms[0]); i++) {
		const struct perm_case *p = &perms[i];

		mix_signed(&digest, shmget_existing_access_result(p->euid,
			p->egid, p->shmflg, p->uid, p->cuid, p->gid,
			p->cgid, p->mode));
		mix_signed(&digest, shmat_access_result(p->euid, p->egid,
			p->shmflg, p->uid, p->cuid, p->gid, p->cgid,
			p->mode));
		mix_signed(&digest, shmctl_ipc_stat_access_result(p->euid,
			p->egid, p->uid, p->cuid, p->gid, p->cgid,
			p->mode));
		mix_signed(&digest, shm_owner_result(p->euid, p->uid,
			p->cuid));
		mix_signed(&digest, shm_owner_or_cap_result(i & 1, p->euid,
			p->uid, p->cuid));
	}

	for (unsigned int i = 0; i < sizeof(rlimits) / sizeof(rlimits[0]); i++) {
		const struct rlimit_case *r = &rlimits[i];

		mix_signed(&digest, shmlock_rlimit_result(r->has_cap,
			r->rlim_cur, r->user_locked, r->size));
	}

	printf("shmid_helpers ok digest=%016lx\n", digest);
	return 0;
}
EOF_SHMID_HELPERS

cat > "${tmpdir}/sched_helpers_equiv.c" <<'EOF_SCHED_HELPERS'
#include <stdio.h>
#include <stdlib.h>

extern int sched_get_priority_max_value(int);
extern int sched_get_priority_min_value(int);
extern int sched_policy_is_valid(int);
extern int sched_policy_needs_root(int);
extern int setscheduler_validate(int, int);
extern long sched_rr_interval_nsec(int);
extern int sched_affinity_permission_result(unsigned int, unsigned int,
					    unsigned int);
extern int sched_getaffinity_len_result(unsigned long, int);
extern unsigned long sched_affinity_copy_len(unsigned long, unsigned long);
extern unsigned long timer_spin_sleep_remaining_result(unsigned long,
						       unsigned long);
extern int timer_runq_should_schedule_result(int);
extern unsigned long timer_after_spin_remaining_result(unsigned long,
						       unsigned long);
extern unsigned long timer_after_tick_remaining_result(unsigned long,
						       unsigned long);
extern int futex_key_match_result(int, int, unsigned long, unsigned long,
				  unsigned long, unsigned long, unsigned long,
				  unsigned long);

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

static void mix_signed(unsigned long *digest, long value)
{
	mix(digest, (unsigned long)value);
}

int main(void)
{
	static const int policies[] = {
		-100, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 99,
	};
	static const int priorities[] = {
		-1, 0, 1, 2, 50, 99, 100,
	};
	static const unsigned int ids[][3] = {
		{ 0, 10, 20 },
		{ 10, 10, 20 },
		{ 20, 10, 20 },
		{ 30, 10, 20 },
		{ 99, 99, 99 },
	};
	static const unsigned long lens[] = {
		0, 1, 4, 7, 8, 16, 128, 129,
	};
	static const int cpu_counts[] = {
		1, 2, 8, 63, 64, 65, 1024,
	};
	static const unsigned long timeouts[] = {
		0, 1, 499, 500, 501, 999, 1000, ~0UL,
	};
	static const int runq_lens[] = {
		-1, 0, 1, 2, 8,
	};
	static const unsigned long futex_keys[][6] = {
		{ 0x1000, 0x2000, 0, 0x1000, 0x2000, 0 },
		{ 0x1000, 0x2000, 4, 0x1000, 0x2000, 8 },
		{ 0x1000, 0x2000, 4, 0x1001, 0x2000, 4 },
		{ 0x1000, 0x2000, 4, 0x1000, 0x3000, 4 },
	};
	unsigned long digest = 0x5c7ed123456789abUL;

	for (unsigned int i = 0; i < sizeof(policies) / sizeof(policies[0]); i++) {
		mix_signed(&digest, sched_get_priority_max_value(policies[i]));
		mix_signed(&digest, sched_get_priority_min_value(policies[i]));
		mix_signed(&digest, sched_policy_is_valid(policies[i]));
		mix_signed(&digest, sched_policy_needs_root(policies[i]));
		mix_signed(&digest, sched_rr_interval_nsec(policies[i]));
		for (unsigned int p = 0; p < sizeof(priorities) / sizeof(priorities[0]); p++)
			mix_signed(&digest, setscheduler_validate(policies[i], priorities[p]));
	}

	for (unsigned int i = 0; i < sizeof(ids) / sizeof(ids[0]); i++) {
		mix_signed(&digest, sched_affinity_permission_result(ids[i][0],
			ids[i][1], ids[i][2]));
	}

	for (unsigned int i = 0; i < sizeof(lens) / sizeof(lens[0]); i++) {
		for (unsigned int j = 0; j < sizeof(cpu_counts) / sizeof(cpu_counts[0]); j++)
			mix_signed(&digest, sched_getaffinity_len_result(lens[i], cpu_counts[j]));
		mix(&digest, sched_affinity_copy_len(lens[i], 128));
		mix(&digest, sched_affinity_copy_len(lens[i], 1024));
	}

	for (unsigned int i = 0; i < sizeof(timeouts) / sizeof(timeouts[0]); i++) {
		for (unsigned int j = 0; j < sizeof(timeouts) / sizeof(timeouts[0]); j++) {
			mix(&digest, timer_spin_sleep_remaining_result(timeouts[i], timeouts[j]));
			mix(&digest, timer_after_spin_remaining_result(timeouts[i], timeouts[j]));
			mix(&digest, timer_after_tick_remaining_result(timeouts[i], timeouts[j]));
		}
	}

	for (unsigned int i = 0; i < sizeof(runq_lens) / sizeof(runq_lens[0]); i++)
		mix_signed(&digest, timer_runq_should_schedule_result(runq_lens[i]));

	for (unsigned int i = 0; i < sizeof(futex_keys) / sizeof(futex_keys[0]); i++) {
		mix_signed(&digest, futex_key_match_result(1, 1,
			futex_keys[i][0], futex_keys[i][1], futex_keys[i][2],
			futex_keys[i][3], futex_keys[i][4], futex_keys[i][5]));
		mix_signed(&digest, futex_key_match_result(0, 1,
			futex_keys[i][0], futex_keys[i][1], futex_keys[i][2],
			futex_keys[i][3], futex_keys[i][4], futex_keys[i][5]));
		mix_signed(&digest, futex_key_match_result(1, 0,
			futex_keys[i][0], futex_keys[i][1], futex_keys[i][2],
			futex_keys[i][3], futex_keys[i][4], futex_keys[i][5]));
	}

	printf("sched_helpers ok digest=%016lx\n", digest);
	return 0;
}
EOF_SCHED_HELPERS

cat > "${tmpdir}/rlimit_helpers_equiv.c" <<'EOF_RLIMIT_HELPERS'
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

extern int prlimit_validate_resource(int);
extern int prlimit_validate_new_limit(uint64_t, uint64_t);
extern int prlimit_linux_update_needed(int);
extern int prlimit_to_mckernel_resource(int);

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

static void mix_signed(unsigned long *digest, long value)
{
	mix(digest, (unsigned long)value);
}

int main(void)
{
	static const int resources[] = {
		-100, -2, -1, 0, 1, 2, 3, 4, 5, 6, 7, 8,
		9, 10, 11, 12, 13, 14, 15, 16, 17, 99,
	};
	static const uint64_t limits[][2] = {
		{ 0, 0 },
		{ 0, 1 },
		{ 1, 0 },
		{ 4096, 4096 },
		{ 4097, 4096 },
		{ UINT64_MAX, UINT64_MAX },
		{ UINT64_MAX, UINT64_MAX - 1 },
	};
	unsigned long digest = 0x714d175123456789UL;

	for (unsigned int i = 0; i < sizeof(resources) / sizeof(resources[0]); i++) {
		mix_signed(&digest, prlimit_validate_resource(resources[i]));
		mix_signed(&digest, prlimit_linux_update_needed(resources[i]));
		mix_signed(&digest, prlimit_to_mckernel_resource(resources[i]));
	}

	for (unsigned int i = 0; i < sizeof(limits) / sizeof(limits[0]); i++) {
		mix_signed(&digest, prlimit_validate_new_limit(limits[i][0],
			limits[i][1]));
	}

	printf("rlimit_helpers ok digest=%016lx\n", digest);
	return 0;
}
EOF_RLIMIT_HELPERS

cat > "${tmpdir}/syscall_policy_helpers_equiv.c" <<'EOF_SYSCALL_POLICY_HELPERS'
#include <limits.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

#define VR_RESERVED 0x2UL
#define VR_IO_NOCACHE 0x100UL
#define VR_REMOTE 0x200UL
#define VR_LOCKED 0x4000UL
#define PAGE_SIZE 4096UL
#define PAGE_MASK (~(PAGE_SIZE - 1))
#define PGOFF_LIMIT (1UL << 51)
#define MCL_CURRENT 0x01
#define MCL_FUTURE 0x02
#define PROT_READ 0x01
#define PROT_WRITE 0x02
#define PROT_EXEC 0x04
#define MAP_SHARED 0x01
#define MAP_PRIVATE 0x02
#define MAP_FIXED 0x10
#define MAP_ANONYMOUS 0x20
#define MAP_LOCKED 0x2000
#define MAP_POPULATE 0x8000
#define VR_DEMAND_PAGING 0x1000UL
#define VR_PRIVATE 0x2000UL
#define VR_PROT_READ 0x00010000UL
#define VR_PROT_WRITE 0x00020000UL
#define VR_PROT_EXEC 0x00040000UL
#define VR_PROT_MASK 0x00070000UL
#define PROT_TO_VR_FLAG(prot) (((unsigned long)(prot) << 16) & VR_PROT_MASK)
#define VRFLAG_PROT_TO_MAXPROT(vrflag) (((vrflag) & VR_PROT_MASK) << 4)
#define MREMAP_MAYMOVE 0x01
#define MREMAP_FIXED 0x02
#define MS_ASYNC 0x01
#define MS_INVALIDATE 0x02
#define MS_SYNC 0x04
#define MPOL_DEFAULT 0
#define MPOL_PREFERRED 1
#define MPOL_BIND 2
#define MPOL_INTERLEAVE 3
#define MPOL_F_STATIC_NODES (1 << 15)
#define MPOL_F_RELATIVE_NODES (1 << 14)
#define MPOL_F_NODE (1 << 0)
#define MPOL_F_ADDR (1 << 1)
#define MPOL_F_MEMS_ALLOWED (1 << 2)
#define MPOL_MF_STRICT (1 << 0)
#define MPOL_MF_MOVE (1 << 1)
#define MPOL_MF_MOVE_ALL (1 << 2)
#define SIG_BLOCK 0
#define SIG_UNBLOCK 1
#define SIG_SETMASK 2
#define SIGKILL_MASK (1UL << 8)
#define SIGSTOP_MASK (1UL << 18)
#define SFD_CLOEXEC 02000000
#define SFD_NONBLOCK 04000
#define RUSAGE_SELF 0
#define RUSAGE_CHILDREN -1
#define RUSAGE_THREAD 1
#define GETRUSAGE_DISPATCH_SELF 1
#define GETRUSAGE_DISPATCH_CHILDREN 2
#define GETRUSAGE_DISPATCH_THREAD 3
#define GETRUSAGE_THREAD_UPDATE_READY 0
#define GETRUSAGE_THREAD_UPDATE_INTERRUPT 1
#define TERMINATE_CHILD_ACTION_NONE 0
#define TERMINATE_CHILD_ACTION_FREE_ZOMBIE 1
#define TERMINATE_CHILD_ACTION_REPARENT_CHILD 2
#define TERMINATE_CHILD_ACTION_REPARENT_PTRACED 3
#define ITIMER_REAL 0
#define ITIMER_VIRTUAL 1
#define ITIMER_PROF 2
#define CLOCK_REALTIME 0
#define CLOCK_MONOTONIC 1
#define CLOCK_PROCESS_CPUTIME_ID 2
#define CLOCK_THREAD_CPUTIME_ID 3
#define NS_PER_SEC 1000000000L
#define TIME_DISPATCH_NOOP 0
#define TIME_DISPATCH_LOCAL_REALTIME 1
#define TIME_DISPATCH_PROCESS_CPUTIME 2
#define TIME_DISPATCH_THREAD_CPUTIME 3
#define TIME_DISPATCH_FORWARD 4
#define MINSIGSTKSZ 2048
#define SS_DISABLE 2
#define IOV_MAX 1024UL
#define PROCESS_VM_READ 0
#define PROCESS_VM_WRITE 1
#define PTRACE_TRACEME 0
#define PTRACE_PEEKTEXT 1
#define PTRACE_PEEKDATA 2
#define PTRACE_PEEKUSER 3
#define PTRACE_POKETEXT 4
#define PTRACE_POKEDATA 5
#define PTRACE_POKEUSER 6
#define PTRACE_CONT 7
#define PTRACE_KILL 8
#define PTRACE_SINGLESTEP 9
#define PTRACE_GETREGS 12
#define PTRACE_SETREGS 13
#define PTRACE_GETFPREGS 14
#define PTRACE_SETFPREGS 15
#define PTRACE_ATTACH 16
#define PTRACE_DETACH 17
#define PTRACE_SYSCALL 24
#define PTRACE_GETFPXREGS 18
#define PTRACE_SETFPXREGS 19
#define PTRACE_SETOPTIONS 0x4200
#define PTRACE_GETEVENTMSG 0x4201
#define PTRACE_GETSIGINFO 0x4202
#define PTRACE_SETSIGINFO 0x4203
#define PTRACE_GETREGSET 0x4204
#define PTRACE_SETREGSET 0x4205
#define PTRACE_WAKEUP_ACTION_NONE 0
#define PTRACE_WAKEUP_ACTION_KILL 1
#define PTRACE_WAKEUP_ACTION_RESUME 2
#define PTRACE_RESUME_SIGNAL_SOURCE_USER 0
#define PTRACE_RESUME_SIGNAL_SOURCE_SENDSIG 1
#define PTRACE_RESUME_SIGNAL_SOURCE_RECVSIG 2
#define PTRACE_SIGINFO_STORE_SENDSIG 0x1
#define PTRACE_SIGINFO_STORE_RECVSIG 0x2
#define PTRACE_SIGINFO_ALLOC_SENDSIG 0x4
#define PTRACE_DISPATCH_ARCH 0
#define PTRACE_DISPATCH_TRACEME 1
#define PTRACE_DISPATCH_WAKEUP 2
#define PTRACE_DISPATCH_GETREGS 3
#define PTRACE_DISPATCH_SETREGS 4
#define PTRACE_DISPATCH_GETFPREGS 5
#define PTRACE_DISPATCH_SETFPREGS 6
#define PTRACE_DISPATCH_PEEKUSER 7
#define PTRACE_DISPATCH_POKEUSER 8
#define PTRACE_DISPATCH_PEEKTEXT 9
#define PTRACE_DISPATCH_POKETEXT 10
#define PTRACE_DISPATCH_SETOPTIONS 11
#define PTRACE_DISPATCH_ATTACH 12
#define PTRACE_DISPATCH_DETACH 13
#define PTRACE_DISPATCH_GETSIGINFO 14
#define PTRACE_DISPATCH_SETSIGINFO 15
#define PTRACE_DISPATCH_GETREGSET 16
#define PTRACE_DISPATCH_SETREGSET 17
#define PTRACE_DISPATCH_GETEVENTMSG 18
#define PTRACE_O_TRACESYSGOOD 1
#define PTRACE_O_TRACEFORK 2
#define PTRACE_O_TRACEVFORK 4
#define PTRACE_O_TRACECLONE 8
#define PTRACE_O_TRACEEXEC 0x10
#define PTRACE_O_TRACEVFORKDONE 0x20
#define PTRACE_O_TRACEEXIT 0x40
#define PTRACE_O_MASK 0x7f
#define PT_TRACED 0x80
#define PT_TRACE_EXEC 0x100
#define PT_TRACE_SYSCALL 0x200
#define PTRACE_EVENT_FORK 1
#define PTRACE_EVENT_VFORK 2
#define PTRACE_EVENT_CLONE 3
#define PTRACE_EVENT_EXEC 4
#define PTRACE_EVENT_VFORK_DONE 5
#define PS_RUNNING 0x1
#define PS_ZOMBIE 0x8
#define PS_EXITED 0x10
#define PS_STOPPED 0x20
#define PS_TRACED 0x40
#define PS_DELAY_STOPPED 0x200
#define PS_DELAY_TRACED 0x400
#define SIGNAL_STOP_STOPPED 0x1
#define SIGNAL_STOP_CONTINUED 0x2
#define WAIT_STOP_SOURCE_NONE 0
#define WAIT_STOP_SOURCE_THREAD 1
#define WAIT_STOP_SOURCE_PROCESS 2
#define WAIT_STOP_SOURCE_MAIN_THREAD 3
#define WAIT_THREAD_REAP_ACTION_NONE 0
#define WAIT_THREAD_REAP_ACTION_RELEASE 1
#define WAIT_THREAD_REAP_ACTION_PTRACE_DETACH 2
#define EXIT_GROUP_STATUS_CONFIRMED 0x0000000100000000UL
#undef WNOHANG
#undef WUNTRACED
#undef WSTOPPED
#undef WEXITED
#undef WCONTINUED
#undef WNOWAIT
#undef __WALL
#undef __WCLONE
#define WNOHANG 0x00000001
#define WUNTRACED 0x00000002
#define WSTOPPED WUNTRACED
#define WEXITED 0x00000004
#define WCONTINUED 0x00000008
#define WNOWAIT 0x01000000
#define __WALL 0x40000000
#define __WCLONE ((int)0x80000000u)
#define P_ALL 0
#define P_PID 1
#define P_PGID 2
#define SIGCHLD 17
#define SIGSTOP 19
#define SIGCONT 18
#define SIGURG 23
#define SIG_IGN_HANDLER 1UL
#define SIGTRAP 5
#define _NSIG 64
#define CSIGNAL 0x000000ff
#define CLONE_VM 0x00000100
#define CLONE_FS 0x00000200
#define CLONE_SIGHAND 0x00000800
#define CLONE_VFORK 0x00004000
#define CLONE_PARENT 0x00008000
#define CLONE_THREAD 0x00010000
#define CLONE_NEWNS 0x00020000
#define CLONE_SYSVSEM 0x00040000
#define CLONE_SETTLS 0x00080000
#define CLONE_PARENT_SETTID 0x00100000
#define CLONE_CHILD_CLEARTID 0x00200000
#define CLONE_CHILD_SETTID 0x01000000
#define CLONE_NEWIPC 0x08000000
#define CLONE_NEWPID 0x20000000
#define SPAWN_TO_LOCAL 0
#define SPAWN_TO_REMOTE 1
#define SPAWNING_TO_REMOTE 1001
#define CLONE_TLS_SOURCE_INHERIT 0
#define CLONE_TLS_SOURCE_ARGUMENT 1
#define AT_FDCWD -100
#define AT_SYMLINK_NOFOLLOW 0x100
#define AT_EMPTY_PATH 0x1000
#define FUTEX_WAIT 0
#define FUTEX_CMP_REQUEUE 4
#define FUTEX_WAKE_OP 5
#define FUTEX_WAIT_BITSET 9
#define FUTEX_PRIVATE_FLAG 128
#define FUTEX_CLOCK_REALTIME 256
#define FUTEX_CMD_MASK (~(FUTEX_PRIVATE_FLAG | FUTEX_CLOCK_REALTIME))

extern int robust_list_len_result(size_t);
extern int tkill_tid_result(int);
extern int tgkill_target_result(int, int);
extern int sigaction_validate(int, int);
extern int rt_sigprocmask_validate(size_t, size_t, int, int);
extern unsigned long rt_sigprocmask_apply(unsigned long, unsigned long, int,
					  int);
extern int rt_sigpending_size_result(size_t, size_t);
extern int signalfd4_sigsetsize_result(size_t, size_t);
extern int signalfd4_flags_result(int);
extern int syscall_refresh_cred_needed_result(long);
extern int syscall_getpid_result(int);
extern int syscall_getppid_result(int);
extern int syscall_gettid_result(int);
extern int syscall_set_tid_address_return_result(int);
extern int setpgid_normalize_pid(int, int);
extern int setpgid_normalize_pgid(int, int);
extern int setpgid_execed_result(int);
extern int memlock_prepare_range(uintptr_t, size_t, uintptr_t, uintptr_t,
				 uintptr_t *, size_t *, uintptr_t *);
extern int memlock_range_flag_result(unsigned long);
extern int range_has_disallowed_change_flags(unsigned long);
extern int munmap_prepare_range(uintptr_t, size_t, uintptr_t, uintptr_t,
				size_t *);
extern int mprotect_prepare_range(uintptr_t, size_t, uintptr_t, uintptr_t,
				  size_t *, uintptr_t *);
extern int mlockall_policy_result(int, int, uint64_t);
extern int remap_file_pages_prepare(uintptr_t, size_t, int, size_t,
				    uintptr_t *, uintptr_t *, long *);
extern int mremap_prepare_args(uintptr_t, size_t, size_t, int, uintptr_t,
			       uintptr_t, uintptr_t, size_t *, size_t *,
			       uintptr_t *, int *);
extern int mremap_fixed_range_result(uintptr_t, uintptr_t, uintptr_t,
				     uintptr_t, uintptr_t);
extern int mremap_maymove_result(int);
extern int msync_prepare_range(uintptr_t, size_t, int, size_t *, uintptr_t *);
extern int msync_locked_range_result(int, unsigned long);
extern int mbind_prepare_range(uintptr_t, unsigned long, unsigned long *);
extern int mempolicy_nodemask_bits_result(unsigned long, unsigned long *);
extern int mempolicy_nodemask_bits_is_clamped(unsigned long);
extern int mbind_mode_flags_result(int, unsigned int, int *, int *);
extern int mempolicy_mode_is_supported(int);
extern int set_mempolicy_normalize_mode(int, int *);
extern int get_mempolicy_validate(unsigned long, int, int, unsigned long, int,
				  unsigned long *);
extern int move_pages_policy_result(int, int);
extern int brk_prepare_result(unsigned long, unsigned long, unsigned long,
			      unsigned long, unsigned long *, int *);
extern unsigned long brk_default_vrflags(void);
extern int mincore_prepare_range(uintptr_t, size_t, uintptr_t, uintptr_t,
				 uintptr_t *);
extern unsigned long mmap_base_vrflags(int, int, unsigned long, int);
extern int mmap_populated_mapping_result(int);
extern int mmap_should_set_host_ro(int, int, int);
extern int mmap_update_private_maxprot(int, int);
extern int mmap_prot_denied_result(int, int, int *);
extern unsigned long mmap_maxprot_to_vrflags(int);
extern int mmap_should_force_straight(int, int, unsigned long, size_t, size_t);
extern int mmap_is_shared(int);
extern int getrusage_who_result(int);
extern int getrusage_dispatch_result(int);
extern int getrusage_thread_update_action_result(int, int, int);
extern long getrusage_maxrss_kb_result(long);
extern int itimer_which_result(int);
extern int itimer_is_real(int);
extern int itimer_should_start(long, long);
extern int clock_gettime_dispatch(int, int, int);
extern int gettimeofday_dispatch(int, int, int);
extern int nanosleep_validate_timespec(long, long);
extern int rt_sigtimedwait_prepare(size_t, size_t, int);
extern int rt_sigtimedwait_timeout_result(long, long, int);
extern void rt_sigtimedwait_prepare_masks(unsigned long, unsigned long,
					  unsigned long *, unsigned long *,
					  unsigned long *);
extern void rt_sigtimedwait_deadline(long, long, long, long, long *, long *);
extern int rt_sigtimedwait_timeout_expired(long, long, long, long);
extern int sigmask_to_signal_number(unsigned long);
extern int signal_pending_deliverable_result(int, int, unsigned long,
					     unsigned long, unsigned long);
extern int signal_pending_interrupt_action_result(int, unsigned long,
						  unsigned long, unsigned long,
						  int);
extern int rt_sigqueueinfo_pid_result(int);
extern int sigsuspend_sigsetsize_result(size_t, size_t);
extern unsigned long sigsuspend_prepare_mask(unsigned long);
extern int sigsuspend_pending_matches(unsigned long, unsigned long);
extern int sigaction_sigsetsize_result(size_t, size_t);
extern int sigaltstack_validate(int, size_t);
extern int sigaltstack_is_disable(int);
extern int process_vm_validate_args(unsigned long, unsigned long, unsigned long);
extern int process_vm_op_is_write(int);
extern int process_vm_op_is_valid(int);
extern int ptrace_signal_data_result(long);
extern int ptrace_detach_signal_result(long);
extern int ptrace_user_area_result(long, unsigned long);
extern int ptrace_status_allows_io(int);
extern int ptrace_setoptions_flags_result(int);
extern int ptrace_apply_options(int, int);
extern int ptrace_child_traced_result(int, int, int);
extern int ptrace_attach_policy_result(int, int, int, int);
extern int ptrace_detach_state_result(int, int);
extern int ptrace_siginfo_state_result(int, int);
extern int ptrace_eventmsg_state_result(int);
extern int ptrace_wakeup_request_action_result(long);
extern int ptrace_resume_single_step_result(long);
extern int ptrace_resume_trace_syscall_result(long);
extern int ptrace_resume_signal_needed_result(long, long);
extern int ptrace_resume_signal_source_result(long, int, int);
extern int ptrace_detach_forward_signal_needed_result(int);
extern int ptrace_detach_exit_signal_needed_result(int);
extern int ptrace_setsiginfo_target_result(int, int, int);
extern int ptrace_request_dispatch_result(long);
extern int wait4_options_result(int);
extern int waitid_to_wait_pid_result(int, int, int *);
extern int waitid_options_result(int);
extern int wait_should_scan_process_result(int);
extern int wait_should_scan_thread_result(int, int);
extern int wait_process_pid_matches_result(int, int, int, int);
extern int wait_thread_tid_matches_result(int, int, int);
extern int wait_process_exited_candidate_result(int, int);
extern int wait_thread_exited_candidate_result(int, int);
extern int wait_nonptraced_stop_candidate_result(int, int, int);
extern int wait_ptraced_stop_candidate_result(int, int);
extern int wait_continued_candidate_result(int, int);
extern int wait_reap_needed_result(int);
extern int wait_nohang_result(int);
extern int wait_empty_result(int);
extern int wait_stopped_status_result(int);
extern int wait_continued_status_result(void);
extern int wait_zombie_skip_host_result(int, int, int);
extern int wait_thread_empty_candidate_result(int, int);
extern int waitid_status_code_result(int);
extern int wait_stopped_source_result(int, int, int, int, int);
extern int wait_stopped_exit_status_result(int, int, int, int);
extern int wait_report_id_result(int, int, int);
extern int wait_reaped_exit_status_result(int, int);
extern int wait_reaped_signal_flags_result(int, int, int);
extern int wait_process_reparent_needed_result(int, int);
extern int wait_main_thread_ptrace_detach_needed_result(int, int);
extern int wait_thread_reap_action_result(int, int);
extern int wait_status_copy_needed_result(int, int);
extern int wait_rusage_copy_needed_result(int);
extern int waitid_siginfo_needed_result(int, int);
extern int exit_code_status_result(int);
extern int exit_code_signal_result(int);
extern int exit_syscall_code_result(int);
extern int thread_exit_signal_result(int, int);
extern int sigchld_code_result(int);
extern int exit_group_status_claimed_result(unsigned long);
extern unsigned long exit_group_status_result(int, int);
extern int terminate_thread_active_result(int);
extern int terminate_status_result(int, int);
extern int terminate_report_thread_release_needed_result(int, int);
extern int terminate_child_action_result(int, int, int);
extern int clone_pthread_marker_result(int, unsigned long, unsigned long);
extern int clone_flags_result(int, int);
extern int clone_host_parent_flags_result(int, int);
extern int clone_report_thread_result(int, int);
extern int clone_parent_tid_store_needed_result(int);
extern int clone_child_cleartid_needed_result(int);
extern int clone_child_tid_store_needed_result(int);
extern int clone_tls_source_result(int);
extern int clone_use_last_cpu_result(int, int);
extern int clone_remote_spawn_result(int);
extern int clone_parent_use_pid1_result(int);
extern int ptrace_exec_event_signal_result(int);
extern int ptrace_syscall_event_signal_result(int);
extern int ptrace_clone_event_result(int, int);
extern int ptrace_clone_reparent_result(int);
extern int execveat_policy_result(int, int, int);
extern int futex_decode_flags_result(int, int *, int *);
extern int futex_wait_timeout_needed_result(int, int);
extern int futex_timeout_is_absolute_result(int);
extern int futex_clock_id_result(int);
extern unsigned int futex_requeue_val2_result(int, unsigned long);
extern unsigned long futex_timeout_ns_result(int, long, long, long, long);

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

static void mix_signed(unsigned long *digest, long value)
{
	mix(digest, (unsigned long)value);
}

struct range_case {
	uintptr_t start;
	size_t len;
	uintptr_t user_start;
	uintptr_t user_end;
};

static void exercise_memlock(unsigned long *digest)
{
	static const struct range_case cases[] = {
		{ 0x10000UL, 0, 0x10000UL, 0x20000UL },
		{ 0x10001UL, 1, 0x10000UL, 0x20000UL },
		{ 0x0UL, 4096, 0x10000UL, 0x20000UL },
		{ 0x1f000UL, 0x2000, 0x10000UL, 0x20000UL },
		{ ULONG_MAX - 0xfffUL, 0x3000, 0x10000UL, 0x20000UL },
	};

	for (unsigned int i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
		uintptr_t start = 0xa5a5;
		uintptr_t end = 0x5a5a;
		size_t len = 0xcccc;
		int rc = memlock_prepare_range(cases[i].start, cases[i].len,
			cases[i].user_start, cases[i].user_end,
			&start, &len, &end);

		mix_signed(digest, rc);
		mix(digest, start);
		mix(digest, len);
		mix(digest, end);
	}
}

static void exercise_unmap_protect(unsigned long *digest)
{
	static const struct range_case cases[] = {
		{ 0x10000UL, 0, 0x10000UL, 0x20000UL },
		{ 0x10000UL, 4096, 0x10000UL, 0x20000UL },
		{ 0x10001UL, 4096, 0x10000UL, 0x20000UL },
		{ 0x1f000UL, 4096, 0x10000UL, 0x20000UL },
		{ 0x20000UL, 4096, 0x10000UL, 0x20000UL },
		{ 0x10000UL, 0x10001, 0x10000UL, 0x20000UL },
		{ ULONG_MAX - 0xfffUL, 0x3000, 0x10000UL, 0x20000UL },
	};

	for (unsigned int i = 0; i < sizeof(cases) / sizeof(cases[0]); i++) {
		size_t len = 0xdddd;
		uintptr_t end = 0xbeef;

		mix_signed(digest, munmap_prepare_range(cases[i].start,
			cases[i].len, cases[i].user_start, cases[i].user_end,
			&len));
		mix(digest, len);

		len = 0xeeee;
		mix_signed(digest, mprotect_prepare_range(cases[i].start,
			cases[i].len, cases[i].user_start, cases[i].user_end,
			&len, &end));
		mix(digest, len);
		mix(digest, end);
	}
}

static void exercise_memory_syscall_policy(unsigned long *digest)
{
	static const int mlock_flags[] = { 0, MCL_CURRENT, MCL_FUTURE,
		MCL_CURRENT | MCL_FUTURE, 4 };
	static const struct range_case remap_cases[] = {
		{ 0x10000UL, 0, 0, 0 },
		{ 0x10001UL, PAGE_SIZE, 0, 0 },
		{ 0x10000UL, PAGE_SIZE, 0, 0 },
		{ 0xfffffffffffff000UL, PAGE_SIZE * 2, 0, 0 },
	};
	static const size_t pgoffs[] = { 0, 1, PGOFF_LIMIT - 1, PGOFF_LIMIT };
	static const int prot_values[] = { 0, 1 };
	static const int mremap_flags[] = {
		0, MREMAP_MAYMOVE, MREMAP_FIXED,
		MREMAP_FIXED | MREMAP_MAYMOVE, 4,
	};
	static const int msync_flags[] = {
		0, MS_ASYNC, MS_INVALIDATE, MS_SYNC,
		MS_ASYNC | MS_SYNC, 8,
	};
	static const unsigned long maxnodes[] = {
		0, 1, 255, 256, 257, PAGE_SIZE << 3, (PAGE_SIZE << 3) + 1,
	};
	static const int modes[] = {
		-1, MPOL_DEFAULT, MPOL_PREFERRED, MPOL_BIND, MPOL_INTERLEAVE,
		4, MPOL_BIND | MPOL_F_STATIC_NODES,
		MPOL_BIND | MPOL_F_RELATIVE_NODES,
		MPOL_BIND | MPOL_F_STATIC_NODES | MPOL_F_RELATIVE_NODES,
	};
	static const int mempolicy_flags[] = {
		0, MPOL_MF_STRICT, MPOL_MF_MOVE,
		MPOL_MF_STRICT | MPOL_MF_MOVE,
	};

	for (unsigned int i = 0; i < sizeof(mlock_flags) / sizeof(mlock_flags[0]); i++) {
		mix_signed(digest, mlockall_policy_result(mlock_flags[i], 0, 0));
		mix_signed(digest, mlockall_policy_result(mlock_flags[i], 0, 4096));
		mix_signed(digest, mlockall_policy_result(mlock_flags[i], 1, 0));
	}

	for (unsigned int i = 0; i < sizeof(remap_cases) / sizeof(remap_cases[0]); i++) {
		for (unsigned int p = 0; p < sizeof(prot_values) / sizeof(prot_values[0]); p++) {
			for (unsigned int o = 0; o < sizeof(pgoffs) / sizeof(pgoffs[0]); o++) {
				uintptr_t start = 0xa5a5;
				uintptr_t end = 0x5a5a;
				long off = -1;

				mix_signed(digest, remap_file_pages_prepare(remap_cases[i].start,
					remap_cases[i].len, prot_values[p], pgoffs[o],
					&start, &end, &off));
				mix(digest, start);
				mix(digest, end);
				mix(digest, (unsigned long)off);
			}
		}
	}

	for (unsigned int f = 0; f < sizeof(mremap_flags) / sizeof(mremap_flags[0]); f++) {
		size_t oldsize = 0;
		size_t newsize = 0;
		uintptr_t oldend = 0;
		int no_op = 0;

		mix_signed(digest, mremap_prepare_args(0x10000, PAGE_SIZE,
			PAGE_SIZE, mremap_flags[f], 0x30000, 0x10000, 0x80000,
			&oldsize, &newsize, &oldend, &no_op));
		mix(digest, oldsize);
		mix(digest, newsize);
		mix(digest, oldend);
		mix_signed(digest, no_op);

		mix_signed(digest, mremap_prepare_args(0x10001, PAGE_SIZE,
			PAGE_SIZE * 2, mremap_flags[f], 0x30001, 0x10000, 0x80000,
			&oldsize, &newsize, &oldend, &no_op));
		mix(digest, oldsize);
		mix(digest, newsize);
		mix(digest, oldend);
		mix_signed(digest, no_op);
		mix_signed(digest, mremap_maymove_result(mremap_flags[f]));
	}

	mix_signed(digest, mremap_prepare_args(0xfffffffffffff000UL, 0x3000,
		0x4000, MREMAP_MAYMOVE, 0, 0x10000, 0x80000,
		&(size_t){0}, &(size_t){0}, &(uintptr_t){0}, &(int){0}));
	mix_signed(digest, mremap_prepare_args(0x10000, PAGE_SIZE,
		0x800000, MREMAP_MAYMOVE, 0, 0x10000, 0x80000,
		&(size_t){0}, &(size_t){0}, &(uintptr_t){0}, &(int){0}));

	mix_signed(digest, mremap_fixed_range_result(0x08000, 0x10000,
		0x20000, 0x24000, 0x30000));
	mix_signed(digest, mremap_fixed_range_result(0x22000, 0x10000,
		0x20000, 0x24000, 0x26000));
	mix_signed(digest, mremap_fixed_range_result(0x30000, 0x10000,
		0x20000, 0x24000, 0x34000));

	for (unsigned int f = 0; f < sizeof(msync_flags) / sizeof(msync_flags[0]); f++) {
		size_t len = 0;
		uintptr_t end = 0;

		mix_signed(digest, msync_prepare_range(0x10000, PAGE_SIZE,
			msync_flags[f], &len, &end));
		mix(digest, len);
		mix(digest, end);
		mix_signed(digest, msync_prepare_range(0x10001, PAGE_SIZE,
			msync_flags[f], &len, &end));
		mix_signed(digest, msync_locked_range_result(msync_flags[f], 0));
		mix_signed(digest, msync_locked_range_result(msync_flags[f], VR_LOCKED));
	}
	mix_signed(digest, msync_prepare_range(0xfffffffffffff000UL, 0x3000,
		MS_SYNC, &(size_t){0}, &(uintptr_t){0}));

	mix_signed(digest, mbind_prepare_range(0x10000, PAGE_SIZE,
		&(unsigned long){0}));
	mix_signed(digest, mbind_prepare_range(0x10001, PAGE_SIZE,
		&(unsigned long){0}));
	mix_signed(digest, mbind_prepare_range(0x10000, 0,
		&(unsigned long){0}));
	mix_signed(digest, mbind_prepare_range(0xfffffffffffff000UL, 0x3000,
		&(unsigned long){0}));

	for (unsigned int i = 0; i < sizeof(maxnodes) / sizeof(maxnodes[0]); i++) {
		unsigned long bits = 0xdead;

		mix_signed(digest, mempolicy_nodemask_bits_result(maxnodes[i], &bits));
		mix(digest, bits);
		mix_signed(digest, mempolicy_nodemask_bits_is_clamped(maxnodes[i]));
	}

	for (unsigned int m = 0; m < sizeof(modes) / sizeof(modes[0]); m++) {
		for (unsigned int f = 0; f < sizeof(mempolicy_flags) / sizeof(mempolicy_flags[0]); f++) {
			int mode_flags = 0;
			int normalized = 0;

			mix_signed(digest, mbind_mode_flags_result(modes[m],
				mempolicy_flags[f], &mode_flags, &normalized));
			mix_signed(digest, mode_flags);
			mix_signed(digest, normalized);
		}
		mix_signed(digest, mempolicy_mode_is_supported(modes[m]));
		mix_signed(digest, set_mempolicy_normalize_mode(modes[m], &(int){0}));
	}

	mix_signed(digest, get_mempolicy_validate(0, 0, MPOL_DEFAULT, 0, 2,
		&(unsigned long){0}));
	mix_signed(digest, get_mempolicy_validate(0x10000, 0, MPOL_DEFAULT, 0, 2,
		&(unsigned long){0}));
	mix_signed(digest, get_mempolicy_validate(0, MPOL_F_ADDR, MPOL_DEFAULT, 0, 2,
		&(unsigned long){0}));
	mix_signed(digest, get_mempolicy_validate(0, MPOL_F_NODE, MPOL_INTERLEAVE, 0, 2,
		&(unsigned long){0}));
	mix_signed(digest, get_mempolicy_validate(0x10000, MPOL_F_ADDR | MPOL_F_NODE,
		MPOL_INTERLEAVE, 8, 2, &(unsigned long){0}));
	mix_signed(digest, get_mempolicy_validate(0, MPOL_F_MEMS_ALLOWED,
		MPOL_DEFAULT, 1, 2, &(unsigned long){0}));

	mix_signed(digest, move_pages_policy_result(0, 0));
	mix_signed(digest, move_pages_policy_result(1, 0));
	mix_signed(digest, move_pages_policy_result(0, MPOL_MF_MOVE));
	mix_signed(digest, move_pages_policy_result(0, MPOL_MF_MOVE_ALL));
	mix_signed(digest, move_pages_policy_result(0, 8));
}

static void exercise_brk_mincore_mmap_policy(unsigned long *digest)
{
	static const unsigned long brk_addrs[] = {
		0, 0x1000, 0x1fff, 0x2000, 0x3000, 0x4000, 0x4001,
	};
	static const struct range_case mincore_cases[] = {
		{ 0x10000UL, 0, 0x10000UL, 0x20000UL },
		{ 0x10000UL, PAGE_SIZE, 0x10000UL, 0x20000UL },
		{ 0x10001UL, PAGE_SIZE, 0x10000UL, 0x20000UL },
		{ 0x0UL, PAGE_SIZE, 0x10000UL, 0x20000UL },
		{ 0x1f000UL, PAGE_SIZE * 2, 0x10000UL, 0x20000UL },
		{ 0x10000UL, ULONG_MAX, 0x10000UL, 0x20000UL },
	};
	static const int prot_values[] = {
		0, PROT_READ, PROT_WRITE, PROT_EXEC,
		PROT_READ | PROT_WRITE,
		PROT_READ | PROT_EXEC,
		PROT_READ | PROT_WRITE | PROT_EXEC,
	};
	static const int mmap_flags[] = {
		0, MAP_SHARED, MAP_PRIVATE, MAP_PRIVATE | MAP_ANONYMOUS,
		MAP_PRIVATE | MAP_ANONYMOUS | MAP_LOCKED,
		MAP_PRIVATE | MAP_ANONYMOUS | MAP_POPULATE,
		MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED,
	};
	static const int maxprots[] = {
		0, PROT_READ, PROT_WRITE, PROT_EXEC,
		PROT_READ | PROT_WRITE,
		PROT_READ | PROT_EXEC,
		PROT_READ | PROT_WRITE | PROT_EXEC,
	};

	for (unsigned int i = 0; i < sizeof(brk_addrs) / sizeof(brk_addrs[0]); i++) {
		unsigned long result = 0xaaaa;
		int extend = -1;

		mix_signed(digest, brk_prepare_result(brk_addrs[i],
			0x1000, 0x2000, 0x4000, &result, &extend));
		mix(digest, result);
		mix_signed(digest, extend);
	}
	mix(digest, brk_default_vrflags());

	for (unsigned int i = 0; i < sizeof(mincore_cases) / sizeof(mincore_cases[0]); i++) {
		uintptr_t end = 0xbeef;

		mix_signed(digest, mincore_prepare_range(mincore_cases[i].start,
			mincore_cases[i].len, mincore_cases[i].user_start,
			mincore_cases[i].user_end, &end));
		mix(digest, end);
	}

	for (unsigned int p = 0; p < sizeof(prot_values) / sizeof(prot_values[0]); p++) {
		for (unsigned int f = 0; f < sizeof(mmap_flags) / sizeof(mmap_flags[0]); f++) {
			mix(digest, mmap_base_vrflags(prot_values[p], mmap_flags[f],
				VR_REMOTE, 0));
			mix(digest, mmap_base_vrflags(prot_values[p], mmap_flags[f],
				VR_REMOTE, 1));
			mix_signed(digest, mmap_populated_mapping_result(mmap_flags[f]));
			mix_signed(digest, mmap_should_set_host_ro(mmap_flags[f],
				prot_values[p], 0));
			mix_signed(digest, mmap_should_set_host_ro(mmap_flags[f],
				prot_values[p], 1));
			mix_signed(digest, mmap_is_shared(mmap_flags[f]));
		}
	}

	for (unsigned int f = 0; f < sizeof(mmap_flags) / sizeof(mmap_flags[0]); f++) {
		for (unsigned int m = 0; m < sizeof(maxprots) / sizeof(maxprots[0]); m++) {
			mix_signed(digest, mmap_update_private_maxprot(mmap_flags[f],
				maxprots[m]));
			mix(digest, mmap_maxprot_to_vrflags(maxprots[m]));
			for (unsigned int p = 0; p < sizeof(prot_values) / sizeof(prot_values[0]); p++) {
				int denied = 0x55;

				mix_signed(digest, mmap_prot_denied_result(prot_values[p],
					maxprots[m], &denied));
				mix_signed(digest, denied);
			}
		}
	}

	mix_signed(digest, mmap_should_force_straight(MAP_PRIVATE | MAP_ANONYMOUS,
		1, 0x10000, 0x4000, 0x2000));
	mix_signed(digest, mmap_should_force_straight(MAP_PRIVATE | MAP_ANONYMOUS,
		1, 0, 0x4000, 0x2000));
	mix_signed(digest, mmap_should_force_straight(MAP_PRIVATE | MAP_ANONYMOUS | MAP_FIXED,
		1, 0x10000, 0x4000, 0x2000));
	mix_signed(digest, mmap_should_force_straight(MAP_PRIVATE | MAP_ANONYMOUS,
		1, 0x10000, 0x1000, 0x2000));
	mix_signed(digest, mmap_should_force_straight(MAP_PRIVATE | MAP_ANONYMOUS,
		0, 0x10000, 0x4000, 0x2000));
}

static void exercise_signal_time_policy(unsigned long *digest)
{
	static const int tids[] = { INT_MIN, -1, 0, 1, 99 };
	static const size_t sigset_sizes[] = { 0, sizeof(unsigned long),
		sizeof(unsigned long) + 1 };
	static const int hows[] = { -1, SIG_BLOCK, SIG_UNBLOCK, SIG_SETMASK, 3 };
	static const unsigned long masks[] = {
		0, 1, SIGKILL_MASK, SIGSTOP_MASK,
		SIGKILL_MASK | SIGSTOP_MASK | 0x55UL,
	};
	static const int signalfd_flags[] = {
		0, SFD_NONBLOCK, SFD_CLOEXEC, SFD_NONBLOCK | SFD_CLOEXEC,
		0x10, SFD_NONBLOCK | 0x10,
	};
	static const int who_values[] = {
		RUSAGE_CHILDREN, RUSAGE_SELF, RUSAGE_THREAD, -2, 2,
	};
	static const int statuses[] = {
		0, PS_RUNNING, PS_ZOMBIE, PS_EXITED, PS_STOPPED,
	};
	static const long rss_values[] = {
		-2048, -1, 0, 1, 1023, 1024, 4096, 123456789,
	};
	static const int exit_codes[] = {
		-1, 0, 1, 9, 0x7f, 0x80, 0x8b, 0x0100, 0xff00,
	};
	static const unsigned long group_statuses[] = {
		0, 1, 0xff00, EXIT_GROUP_STATUS_CONFIRMED,
		EXIT_GROUP_STATUS_CONFIRMED | 0x8b,
	};
	static const int itimers[] = {
		-1, ITIMER_REAL, ITIMER_VIRTUAL, ITIMER_PROF, 3,
	};
	static const long timeval_pairs[][2] = {
		{ 0, 0 }, { 1, 0 }, { 0, 1 }, { -1, 0 },
	};
	static const int clock_ids[] = {
		-1, CLOCK_REALTIME, CLOCK_PROCESS_CPUTIME_ID,
		CLOCK_THREAD_CPUTIME_ID, 11,
	};
	static const int bools[] = { 0, 1 };
	static const long timespecs[][2] = {
		{ 0, 0 },
		{ 1, 999999999L },
		{ 1, NS_PER_SEC },
		{ -1, 0 },
		{ 0, -1 },
	};

	for (unsigned int g = 0; g < sizeof(tids) / sizeof(tids[0]); g++) {
		for (unsigned int t = 0; t < sizeof(tids) / sizeof(tids[0]); t++)
			mix_signed(digest, tgkill_target_result(tids[g], tids[t]));
	}

	for (unsigned int s = 0; s < sizeof(sigset_sizes) / sizeof(sigset_sizes[0]); s++) {
		for (unsigned int h = 0; h < sizeof(hows) / sizeof(hows[0]); h++) {
			mix_signed(digest, rt_sigprocmask_validate(sigset_sizes[s],
				sizeof(unsigned long), 0, hows[h]));
			mix_signed(digest, rt_sigprocmask_validate(sigset_sizes[s],
				sizeof(unsigned long), 1, hows[h]));
		}
		mix_signed(digest, rt_sigpending_size_result(sigset_sizes[s],
			sizeof(unsigned long)));
		mix_signed(digest, signalfd4_sigsetsize_result(sigset_sizes[s],
			sizeof(unsigned long)));
	}

	for (unsigned int m = 0; m < sizeof(masks) / sizeof(masks[0]); m++) {
		for (unsigned int s = 0; s < sizeof(masks) / sizeof(masks[0]); s++) {
			for (unsigned int h = 0; h < sizeof(hows) / sizeof(hows[0]); h++) {
				mix(digest, rt_sigprocmask_apply(masks[m], masks[s],
					0, hows[h]));
				mix(digest, rt_sigprocmask_apply(masks[m], masks[s],
					1, hows[h]));
			}
		}
	}

	for (unsigned int f = 0; f < sizeof(signalfd_flags) / sizeof(signalfd_flags[0]); f++)
		mix_signed(digest, signalfd4_flags_result(signalfd_flags[f]));

	for (unsigned int w = 0; w < sizeof(who_values) / sizeof(who_values[0]); w++) {
		mix_signed(digest, getrusage_who_result(who_values[w]));
		mix_signed(digest, getrusage_dispatch_result(who_values[w]));
	}
	for (unsigned int c = 0; c < sizeof(bools) / sizeof(bools[0]); c++) {
		for (unsigned int s = 0; s < sizeof(statuses) / sizeof(statuses[0]); s++) {
			for (unsigned int k = 0; k < sizeof(bools) / sizeof(bools[0]); k++)
				mix_signed(digest, getrusage_thread_update_action_result(
					bools[c], statuses[s], bools[k]));
		}
	}
	for (unsigned int r = 0; r < sizeof(rss_values) / sizeof(rss_values[0]); r++)
		mix_signed(digest, getrusage_maxrss_kb_result(rss_values[r]));
	for (unsigned int e = 0; e < sizeof(exit_codes) / sizeof(exit_codes[0]); e++) {
		mix_signed(digest, exit_code_status_result(exit_codes[e]));
		mix_signed(digest, exit_code_signal_result(exit_codes[e]));
		mix_signed(digest, exit_syscall_code_result(exit_codes[e]));
		mix_signed(digest, sigchld_code_result(exit_codes[e]));
		for (unsigned int p = 0; p < sizeof(bools) / sizeof(bools[0]); p++)
			mix_signed(digest, thread_exit_signal_result(
				bools[p], exit_codes[e]));
	}
	for (unsigned int g = 0; g < sizeof(group_statuses) / sizeof(group_statuses[0]); g++)
		mix_signed(digest, exit_group_status_claimed_result(
			group_statuses[g]));
	for (unsigned int rc = 0; rc < sizeof(exit_codes) / sizeof(exit_codes[0]); rc++) {
		for (unsigned int sig = 0; sig < sizeof(exit_codes) / sizeof(exit_codes[0]); sig++)
			mix(digest, exit_group_status_result(exit_codes[rc],
				exit_codes[sig]));
	}
	for (unsigned int s = 0; s < sizeof(statuses) / sizeof(statuses[0]); s++)
		mix_signed(digest, terminate_thread_active_result(statuses[s]));
	for (unsigned int rc = 0; rc < sizeof(exit_codes) / sizeof(exit_codes[0]); rc++) {
		for (unsigned int sig = 0; sig < sizeof(exit_codes) / sizeof(exit_codes[0]); sig++)
			mix_signed(digest, terminate_status_result(
				exit_codes[rc], exit_codes[sig]));
	}
	for (unsigned int same = 0; same < sizeof(bools) / sizeof(bools[0]); same++) {
		for (unsigned int sig = 0; sig < sizeof(exit_codes) / sizeof(exit_codes[0]); sig++)
			mix_signed(digest, terminate_report_thread_release_needed_result(
				bools[same], exit_codes[sig]));
	}
	for (unsigned int ppid = 0; ppid < sizeof(bools) / sizeof(bools[0]); ppid++) {
		for (unsigned int parent = 0; parent < sizeof(bools) / sizeof(bools[0]); parent++) {
			for (unsigned int s = 0; s < sizeof(statuses) / sizeof(statuses[0]); s++)
				mix_signed(digest, terminate_child_action_result(
					bools[ppid], bools[parent],
					statuses[s]));
		}
	}

	for (unsigned int i = 0; i < sizeof(itimers) / sizeof(itimers[0]); i++) {
		mix_signed(digest, itimer_which_result(itimers[i]));
		mix_signed(digest, itimer_is_real(itimers[i]));
	}

	for (unsigned int i = 0; i < sizeof(timeval_pairs) / sizeof(timeval_pairs[0]); i++)
		mix_signed(digest, itimer_should_start(timeval_pairs[i][0],
			timeval_pairs[i][1]));

	for (unsigned int c = 0; c < sizeof(clock_ids) / sizeof(clock_ids[0]); c++) {
		for (unsigned int l = 0; l < sizeof(bools) / sizeof(bools[0]); l++) {
			for (unsigned int t = 0; t < sizeof(bools) / sizeof(bools[0]); t++)
				mix_signed(digest, clock_gettime_dispatch(clock_ids[c],
					bools[l], bools[t]));
		}
	}

	for (unsigned int tv = 0; tv < sizeof(bools) / sizeof(bools[0]); tv++) {
		for (unsigned int tz = 0; tz < sizeof(bools) / sizeof(bools[0]); tz++) {
			for (unsigned int l = 0; l < sizeof(bools) / sizeof(bools[0]); l++)
				mix_signed(digest, gettimeofday_dispatch(bools[tv],
					bools[tz], bools[l]));
		}
	}

	for (unsigned int i = 0; i < sizeof(timespecs) / sizeof(timespecs[0]); i++)
		mix_signed(digest, nanosleep_validate_timespec(timespecs[i][0],
			timespecs[i][1]));
}

static void exercise_signal_wait_policy(unsigned long *digest)
{
	static const size_t sigset_sizes[] = {
		0, sizeof(unsigned long), sizeof(unsigned long) + 1,
	};
	static const unsigned long masks[] = {
		0, 1, 2, SIGKILL_MASK, SIGSTOP_MASK,
		SIGKILL_MASK | SIGSTOP_MASK | 0x55UL, 0x8000000000000000UL,
	};
	static const long timeouts[][2] = {
		{ 0, 0 },
		{ 0, 1 },
		{ 1, 999999999L },
		{ 1, NS_PER_SEC },
		{ -1, 0 },
		{ 0, -1 },
	};
	static const long deadlines[][4] = {
		{ 10, 20, 0, 0 },
		{ 10, 999999999L, 0, 1 },
		{ 10, 900000000L, 1, 200000000L },
	};
	static const long expiry[][4] = {
		{ 9, 999999999L, 10, 0 },
		{ 10, 0, 10, 0 },
		{ 10, 1, 10, 0 },
		{ 11, 0, 10, 999999999L },
	};
	static const int flags[] = { 0, SS_DISABLE, 1, 3 };
	static const size_t stack_sizes[] = { 0, MINSIGSTKSZ - 1, MINSIGSTKSZ,
		MINSIGSTKSZ + 1 };
	static const int pids[] = { -1, 0, 1, 99 };
	static const int sigs[] = { 1, SIGCHLD, SIGCONT, SIGURG, 9, 64 };
	static const unsigned long handlers[] = { 0, SIG_IGN_HANDLER, 0x1000 };
	static const int bools[] = { 0, 1 };

	for (unsigned int s = 0; s < sizeof(sigset_sizes) / sizeof(sigset_sizes[0]); s++) {
		mix_signed(digest, rt_sigtimedwait_prepare(sigset_sizes[s],
			sizeof(unsigned long), 0));
		mix_signed(digest, rt_sigtimedwait_prepare(sigset_sizes[s],
			sizeof(unsigned long), 1));
		mix_signed(digest, sigsuspend_sigsetsize_result(sigset_sizes[s],
			sizeof(unsigned long)));
		mix_signed(digest, sigaction_sigsetsize_result(sigset_sizes[s],
			sizeof(unsigned long)));
	}

	for (unsigned int i = 0; i < sizeof(timeouts) / sizeof(timeouts[0]); i++) {
		mix_signed(digest, rt_sigtimedwait_timeout_result(timeouts[i][0],
			timeouts[i][1], 0));
		mix_signed(digest, rt_sigtimedwait_timeout_result(timeouts[i][0],
			timeouts[i][1], 1));
	}

	for (unsigned int raw = 0; raw < sizeof(masks) / sizeof(masks[0]); raw++) {
		for (unsigned int cur = 0; cur < sizeof(masks) / sizeof(masks[0]); cur++) {
			unsigned long wait_mask = 0;
			unsigned long blocked_mask = 0;
			unsigned long interrupt_mask = 0;

			rt_sigtimedwait_prepare_masks(masks[raw], masks[cur],
				&wait_mask, &blocked_mask, &interrupt_mask);
			mix(digest, wait_mask);
			mix(digest, blocked_mask);
			mix(digest, interrupt_mask);
			mix(digest, sigsuspend_prepare_mask(masks[raw]));
			mix_signed(digest, sigsuspend_pending_matches(masks[cur],
				wait_mask));
		}
		mix_signed(digest, sigmask_to_signal_number(masks[raw]));
	}

	for (unsigned int i = 0; i < sizeof(deadlines) / sizeof(deadlines[0]); i++) {
		long sec = 0;
		long nsec = 0;

		rt_sigtimedwait_deadline(deadlines[i][0], deadlines[i][1],
			deadlines[i][2], deadlines[i][3], &sec, &nsec);
		mix_signed(digest, sec);
		mix_signed(digest, nsec);
	}

	for (unsigned int i = 0; i < sizeof(expiry) / sizeof(expiry[0]); i++)
		mix_signed(digest, rt_sigtimedwait_timeout_expired(expiry[i][0],
			expiry[i][1], expiry[i][2], expiry[i][3]));

	for (unsigned int i = 0; i < sizeof(pids) / sizeof(pids[0]); i++)
		mix_signed(digest, rt_sigqueueinfo_pid_result(pids[i]));

	for (unsigned int s = 0; s < sizeof(sigs) / sizeof(sigs[0]); s++) {
		for (unsigned int h = 0; h < sizeof(handlers) / sizeof(handlers[0]); h++) {
			for (unsigned int p = 0; p < sizeof(masks) / sizeof(masks[0]); p++) {
				for (unsigned int b = 0; b < sizeof(masks) / sizeof(masks[0]); b++) {
					for (unsigned int d = 0; d < sizeof(bools) / sizeof(bools[0]); d++) {
						mix_signed(digest,
							signal_pending_deliverable_result(
								bools[d], sigs[s],
								handlers[h],
								masks[p], masks[b]));
						mix_signed(digest,
							signal_pending_interrupt_action_result(
								sigs[s], handlers[h],
								masks[p], masks[b],
								bools[d]));
					}
				}
			}
		}
	}

	for (unsigned int f = 0; f < sizeof(flags) / sizeof(flags[0]); f++) {
		for (unsigned int s = 0; s < sizeof(stack_sizes) / sizeof(stack_sizes[0]); s++)
			mix_signed(digest, sigaltstack_validate(flags[f],
				stack_sizes[s]));
		mix_signed(digest, sigaltstack_is_disable(flags[f]));
	}
}

static void exercise_ptrace_process_vm_policy(unsigned long *digest)
{
	static const unsigned long flags[] = { 0, 1, ULONG_MAX };
	static const unsigned long iovcnts[] = { 0, 1, IOV_MAX, IOV_MAX + 1 };
	static const int ops[] = { -1, PROCESS_VM_READ, PROCESS_VM_WRITE, 2 };
	static const long signal_data[] = { -1, 0, 1, 19, 64, 65, LONG_MAX };
	static const long addrs[] = { LONG_MIN, -1, 0, 7, 8, 120, 121, LONG_MAX };
	static const int statuses[] = {
		0, PS_RUNNING, PS_STOPPED, PS_TRACED, PS_STOPPED | PS_TRACED,
	};
	static const int option_flags[] = {
		0, PTRACE_O_TRACESYSGOOD, PTRACE_O_TRACEFORK,
		PTRACE_O_TRACEVFORK, PTRACE_O_TRACECLONE, PTRACE_O_TRACEEXEC,
		PTRACE_O_TRACEVFORKDONE, PTRACE_O_TRACEEXIT, PTRACE_O_MASK,
		PTRACE_O_MASK | 0x80, -1,
	};
	static const int ptrace_values[] = {
		0, PT_TRACED, PT_TRACE_EXEC, PT_TRACED | PT_TRACE_EXEC,
	};
	static const int bools[] = { 0, 1 };
	static const int pids[] = { 1, 2 };
	static const long ptrace_requests[] = {
		PTRACE_TRACEME, PTRACE_PEEKTEXT, PTRACE_PEEKDATA,
		PTRACE_PEEKUSER, PTRACE_POKETEXT, PTRACE_POKEDATA,
		PTRACE_POKEUSER, PTRACE_CONT, PTRACE_KILL,
		PTRACE_SINGLESTEP, PTRACE_GETREGS, PTRACE_SETREGS,
		PTRACE_GETFPREGS, PTRACE_SETFPREGS, PTRACE_ATTACH,
		PTRACE_DETACH, PTRACE_SYSCALL, PTRACE_SETOPTIONS,
		PTRACE_GETEVENTMSG, PTRACE_GETSIGINFO, PTRACE_SETSIGINFO,
		PTRACE_GETREGSET, PTRACE_SETREGSET, PTRACE_GETFPXREGS,
		PTRACE_SETFPXREGS, 999,
	};
	static const long ptrace_data[] = { 0, 1, SIGSTOP, 64, 65 };

	for (unsigned int f = 0; f < sizeof(flags) / sizeof(flags[0]); f++) {
		for (unsigned int l = 0; l < sizeof(iovcnts) / sizeof(iovcnts[0]); l++) {
			for (unsigned int r = 0; r < sizeof(iovcnts) / sizeof(iovcnts[0]); r++)
				mix_signed(digest, process_vm_validate_args(flags[f],
					iovcnts[l], iovcnts[r]));
		}
	}

	for (unsigned int i = 0; i < sizeof(ops) / sizeof(ops[0]); i++) {
		mix_signed(digest, process_vm_op_is_write(ops[i]));
		mix_signed(digest, process_vm_op_is_valid(ops[i]));
	}

	for (unsigned int i = 0; i < sizeof(signal_data) / sizeof(signal_data[0]); i++) {
		mix_signed(digest, ptrace_signal_data_result(signal_data[i]));
		mix_signed(digest, ptrace_detach_signal_result(signal_data[i]));
	}

	for (unsigned int i = 0; i < sizeof(addrs) / sizeof(addrs[0]); i++) {
		mix_signed(digest, ptrace_user_area_result(addrs[i], 128));
		mix_signed(digest, ptrace_user_area_result(addrs[i], 8));
	}

	for (unsigned int i = 0; i < sizeof(statuses) / sizeof(statuses[0]); i++)
		mix_signed(digest, ptrace_status_allows_io(statuses[i]));

	for (unsigned int f = 0; f < sizeof(option_flags) / sizeof(option_flags[0]); f++) {
		mix_signed(digest, ptrace_setoptions_flags_result(option_flags[f]));
		for (unsigned int p = 0; p < sizeof(ptrace_values) / sizeof(ptrace_values[0]); p++)
			mix_signed(digest, ptrace_apply_options(ptrace_values[p],
				option_flags[f]));
	}

	for (unsigned int c = 0; c < sizeof(bools) / sizeof(bools[0]); c++) {
		for (unsigned int p = 0; p < sizeof(bools) / sizeof(bools[0]); p++) {
			for (unsigned int t = 0; t < sizeof(ptrace_values) / sizeof(ptrace_values[0]); t++)
				mix_signed(digest, ptrace_child_traced_result(bools[c],
					bools[p], ptrace_values[t]));
		}
	}

	for (unsigned int tr = 0; tr < sizeof(pids) / sizeof(pids[0]); tr++) {
		for (unsigned int ta = 0; ta < sizeof(pids) / sizeof(pids[0]); ta++) {
			for (unsigned int pt = 0; pt < sizeof(ptrace_values) / sizeof(ptrace_values[0]); pt++) {
				for (unsigned int same = 0; same < sizeof(bools) / sizeof(bools[0]); same++)
					mix_signed(digest, ptrace_attach_policy_result(
						pids[tr], pids[ta], ptrace_values[pt],
						bools[same]));
			}
		}
	}

	for (unsigned int traced = 0; traced < sizeof(bools) / sizeof(bools[0]); traced++) {
		for (unsigned int same = 0; same < sizeof(bools) / sizeof(bools[0]); same++)
			mix_signed(digest, ptrace_detach_state_result(bools[traced],
				bools[same]));
	}

	for (unsigned int s = 0; s < sizeof(statuses) / sizeof(statuses[0]); s++) {
		for (unsigned int h = 0; h < sizeof(bools) / sizeof(bools[0]); h++)
			mix_signed(digest, ptrace_siginfo_state_result(statuses[s],
				bools[h]));
		mix_signed(digest, ptrace_eventmsg_state_result(statuses[s]));
		for (unsigned int send = 0; send < sizeof(bools) / sizeof(bools[0]); send++) {
			for (unsigned int recv = 0; recv < sizeof(bools) / sizeof(bools[0]); recv++)
				mix_signed(digest, ptrace_setsiginfo_target_result(
					statuses[s], bools[send], bools[recv]));
		}
	}

	for (unsigned int r = 0; r < sizeof(ptrace_requests) / sizeof(ptrace_requests[0]); r++) {
		mix_signed(digest, ptrace_request_dispatch_result(
			ptrace_requests[r]));
		mix_signed(digest, ptrace_wakeup_request_action_result(
			ptrace_requests[r]));
		mix_signed(digest, ptrace_resume_single_step_result(
			ptrace_requests[r]));
		mix_signed(digest, ptrace_resume_trace_syscall_result(
			ptrace_requests[r]));
		for (unsigned int d = 0; d < sizeof(ptrace_data) / sizeof(ptrace_data[0]); d++)
			mix_signed(digest, ptrace_resume_signal_needed_result(
				ptrace_requests[r], ptrace_data[d]));
		for (unsigned int send = 0; send < sizeof(bools) / sizeof(bools[0]); send++) {
			for (unsigned int recv = 0; recv < sizeof(bools) / sizeof(bools[0]); recv++)
				mix_signed(digest, ptrace_resume_signal_source_result(
					ptrace_requests[r], bools[send],
					bools[recv]));
		}
	}
}

static void exercise_wait_policy(unsigned long *digest)
{
	static const int pids[] = { -55, -2, -1, 0, 1, 2, 55 };
	static const int pgids[] = { 1, 2, 55 };
	static const int statuses[] = {
		0, PS_RUNNING, PS_ZOMBIE, PS_EXITED, PS_STOPPED, PS_TRACED,
		PS_DELAY_STOPPED, PS_DELAY_TRACED, PS_STOPPED | PS_TRACED,
		PS_TRACED | PS_DELAY_TRACED,
	};
	static const int signal_flags[] = {
		0, SIGNAL_STOP_STOPPED, SIGNAL_STOP_CONTINUED,
		SIGNAL_STOP_STOPPED | SIGNAL_STOP_CONTINUED,
	};
	static const int ptrace_values[] = { 0, PT_TRACED, PT_TRACE_EXEC,
		PT_TRACED | PT_TRACE_EXEC };
	static const int option_values[] = {
		0, WNOHANG, WUNTRACED, WEXITED, WCONTINUED, WNOWAIT,
		WEXITED | WNOHANG, WEXITED | WNOWAIT,
		WUNTRACED | WCONTINUED, WEXITED | WUNTRACED | WCONTINUED,
		__WCLONE, __WALL, WEXITED | __WCLONE,
		WEXITED | __WALL | WNOWAIT, WEXITED | WUNTRACED |
		WCONTINUED | WNOHANG | WNOWAIT | __WCLONE | __WALL,
		0x10, -1,
	};
	static const int idtypes[] = { P_ALL, P_PID, P_PGID, 3, -1 };
	static const int bools[] = { 0, 1 };
	static const int termsigs[] = { 0, SIGCHLD, 9, 15 };
	static const int wait_statuses[] = {
		0, 1, 9, 0x7f, 0x137f, 0xffff, 0x0100, 0x8b,
	};
	static const int exit_statuses[] = { 0, 1, 9, 0x13, 0xff, 0x137f };
	static const int wait_results[] = { -10, -1, 0, 1, 55 };

	for (unsigned int o = 0; o < sizeof(option_values) / sizeof(option_values[0]); o++) {
		mix_signed(digest, wait4_options_result(option_values[o]));
		mix_signed(digest, waitid_options_result(option_values[o]));
		mix_signed(digest, wait_should_scan_process_result(option_values[o]));
		mix_signed(digest, wait_reap_needed_result(option_values[o]));
		mix_signed(digest, wait_nohang_result(option_values[o]));
		for (unsigned int b = 0; b < sizeof(bools) / sizeof(bools[0]); b++) {
			mix_signed(digest, wait_process_reparent_needed_result(
				option_values[o], bools[b]));
			mix_signed(digest, wait_rusage_copy_needed_result(bools[b]));
			for (unsigned int rc = 0; rc < sizeof(wait_results) / sizeof(wait_results[0]); rc++) {
				mix_signed(digest, wait_status_copy_needed_result(
					wait_results[rc], bools[b]));
				mix_signed(digest, waitid_siginfo_needed_result(
					wait_results[rc], bools[b]));
			}
		}
		for (unsigned int p = 0; p < sizeof(pids) / sizeof(pids[0]); p++)
			mix_signed(digest, wait_should_scan_thread_result(pids[p],
				option_values[o]));
		for (unsigned int s = 0; s < sizeof(statuses) / sizeof(statuses[0]); s++) {
			mix_signed(digest, wait_process_exited_candidate_result(
				option_values[o], statuses[s]));
			mix_signed(digest, wait_thread_exited_candidate_result(
				option_values[o], statuses[s]));
			for (unsigned int pt = 0; pt < sizeof(ptrace_values) / sizeof(ptrace_values[0]); pt++)
				mix_signed(digest, wait_ptraced_stop_candidate_result(
					ptrace_values[pt], statuses[s]));
		}
		for (unsigned int fl = 0; fl < sizeof(signal_flags) / sizeof(signal_flags[0]); fl++) {
			mix_signed(digest, wait_continued_candidate_result(
				signal_flags[fl], option_values[o]));
			mix_signed(digest, wait_reaped_signal_flags_result(
				option_values[o], signal_flags[fl],
				SIGNAL_STOP_STOPPED));
			mix_signed(digest, wait_reaped_signal_flags_result(
				option_values[o], signal_flags[fl],
				SIGNAL_STOP_CONTINUED));
			for (unsigned int pt = 0; pt < sizeof(ptrace_values) / sizeof(ptrace_values[0]); pt++)
				mix_signed(digest, wait_nonptraced_stop_candidate_result(
					ptrace_values[pt], signal_flags[fl],
					option_values[o]));
		}
		for (unsigned int pt = 0; pt < sizeof(ptrace_values) / sizeof(ptrace_values[0]); pt++) {
			mix_signed(digest, wait_main_thread_ptrace_detach_needed_result(
				option_values[o], ptrace_values[pt]));
			mix_signed(digest, wait_thread_reap_action_result(
				option_values[o], ptrace_values[pt]));
		}
		for (unsigned int e = 0; e < sizeof(exit_statuses) / sizeof(exit_statuses[0]); e++)
			mix_signed(digest, wait_reaped_exit_status_result(
				option_values[o], exit_statuses[e]));
	}

	for (unsigned int has = 0; has < sizeof(bools) / sizeof(bools[0]); has++) {
		for (unsigned int s = 0; s < sizeof(statuses) / sizeof(statuses[0]); s++) {
			for (unsigned int ce = 0; ce < sizeof(exit_statuses) / sizeof(exit_statuses[0]); ce++) {
				for (unsigned int ge = 0; ge < sizeof(exit_statuses) / sizeof(exit_statuses[0]); ge++) {
					for (unsigned int me = 0; me < sizeof(exit_statuses) / sizeof(exit_statuses[0]); me++) {
						int source = wait_stopped_source_result(
							bools[has], exit_statuses[ce],
							statuses[s], exit_statuses[ge],
							exit_statuses[me]);

						mix_signed(digest, source);
						mix_signed(digest, wait_stopped_exit_status_result(
							source, exit_statuses[ce],
							exit_statuses[ge],
							exit_statuses[me]));
						mix_signed(digest, wait_report_id_result(
							source, 55, 77));
					}
				}
			}
		}
	}

	for (unsigned int idt = 0; idt < sizeof(idtypes) / sizeof(idtypes[0]); idt++) {
		for (unsigned int id = 0; id < sizeof(pids) / sizeof(pids[0]); id++) {
			int pid = 0x12345678;

			mix_signed(digest, waitid_to_wait_pid_result(idtypes[idt],
				pids[id], &pid));
			mix_signed(digest, pid);
		}
	}

	for (unsigned int p = 0; p < sizeof(pids) / sizeof(pids[0]); p++) {
		for (unsigned int pg = 0; pg < sizeof(pgids) / sizeof(pgids[0]); pg++) {
			for (unsigned int cg = 0; cg < sizeof(pgids) / sizeof(pgids[0]); cg++) {
				for (unsigned int cp = 0; cp < sizeof(pids) / sizeof(pids[0]); cp++)
					mix_signed(digest, wait_process_pid_matches_result(
						pids[p], pgids[pg], pgids[cg],
						pids[cp]));
			}
		}
	}

	for (unsigned int tid = 0; tid < sizeof(pids) / sizeof(pids[0]); tid++) {
		for (unsigned int child = 0; child < sizeof(pids) / sizeof(pids[0]); child++) {
			for (unsigned int main = 0; main < sizeof(bools) / sizeof(bools[0]); main++)
				mix_signed(digest, wait_thread_tid_matches_result(
					pids[tid], pids[child], bools[main]));
		}
	}

	for (unsigned int e = 0; e < sizeof(bools) / sizeof(bools[0]); e++)
		mix_signed(digest, wait_empty_result(bools[e]));

	for (unsigned int s = 0; s < sizeof(wait_statuses) / sizeof(wait_statuses[0]); s++) {
		mix_signed(digest, wait_stopped_status_result(wait_statuses[s]));
		mix_signed(digest, waitid_status_code_result(wait_statuses[s]));
	}
	mix_signed(digest, wait_continued_status_result());

	for (unsigned int ppid = 0; ppid < sizeof(pids) / sizeof(pids[0]); ppid++) {
		for (unsigned int cur = 0; cur < sizeof(pids) / sizeof(pids[0]); cur++) {
			for (unsigned int nw = 0; nw < sizeof(bools) / sizeof(bools[0]); nw++)
				mix_signed(digest, wait_zombie_skip_host_result(
					pids[ppid], pids[cur], bools[nw]));
		}
	}

	for (unsigned int main = 0; main < sizeof(bools) / sizeof(bools[0]); main++) {
		for (unsigned int sig = 0; sig < sizeof(termsigs) / sizeof(termsigs[0]); sig++)
			mix_signed(digest, wait_thread_empty_candidate_result(
				bools[main], termsigs[sig]));
	}
}

static void exercise_clone_exec_futex_policy(unsigned long *digest)
{
	static const int clone_flags[] = {
		0, SIGCHLD, CLONE_VM, CLONE_THREAD,
		CLONE_VM | CLONE_THREAD | CLONE_SIGHAND,
		CLONE_VM | CLONE_THREAD | CLONE_SIGHAND | SIGCHLD,
		CLONE_VM | CLONE_THREAD | CLONE_SIGHAND | 65,
		CLONE_SIGHAND, CLONE_THREAD | CLONE_SIGHAND,
		CLONE_FS | CLONE_NEWNS, CLONE_NEWIPC | CLONE_SYSVSEM,
		CLONE_VM | CLONE_THREAD | CLONE_SIGHAND | CLONE_NEWPID,
		CLONE_PARENT | SIGCHLD, CLONE_VFORK | SIGCHLD,
		CLONE_VFORK | 9, CLONE_SETTLS,
		CLONE_PARENT_SETTID, CLONE_CHILD_CLEARTID,
		CLONE_CHILD_SETTID,
		CLONE_VM | CLONE_THREAD | CLONE_SIGHAND | CLONE_SETTLS |
			CLONE_PARENT_SETTID | CLONE_CHILD_CLEARTID |
			CLONE_CHILD_SETTID | SIGCHLD,
	};
	static const unsigned long stack_values[] = {
		0, 1, 0x10000UL, 0x7fffffffffffUL,
	};
	static const int ptrace_values[] = {
		0, PT_TRACED, PT_TRACE_EXEC, PT_TRACE_SYSCALL,
		PTRACE_O_TRACESYSGOOD, PTRACE_O_TRACEFORK,
		PTRACE_O_TRACEVFORK, PTRACE_O_TRACEVFORKDONE,
		PTRACE_O_TRACECLONE, PTRACE_O_TRACEEXEC,
		PT_TRACE_SYSCALL | PTRACE_O_TRACESYSGOOD,
		PTRACE_O_TRACEVFORK | PTRACE_O_TRACEVFORKDONE,
		PTRACE_O_TRACEFORK | PTRACE_O_TRACECLONE,
	};
	static const int events[] = {
		0, PTRACE_EVENT_FORK, PTRACE_EVENT_VFORK,
		PTRACE_EVENT_CLONE, PTRACE_EVENT_EXEC,
		PTRACE_EVENT_VFORK_DONE,
	};
	static const int exec_flags[] = {
		0, AT_SYMLINK_NOFOLLOW, AT_EMPTY_PATH,
		AT_SYMLINK_NOFOLLOW | AT_EMPTY_PATH, 0x200, -1,
	};
	static const int dirfds[] = {
		AT_FDCWD, -200, -1, 0, 3,
	};
	static const int first_chars[] = {
		0, '/', '.', 'a',
	};
	static const int futex_flags[] = {
		FUTEX_WAIT, FUTEX_WAIT_BITSET, FUTEX_CMP_REQUEUE,
		FUTEX_WAKE_OP, FUTEX_WAIT | FUTEX_PRIVATE_FLAG,
		FUTEX_WAIT_BITSET | FUTEX_CLOCK_REALTIME,
		FUTEX_WAKE_OP | FUTEX_PRIVATE_FLAG | FUTEX_CLOCK_REALTIME,
		-1,
	};
	static const unsigned long arg3_values[] = {
		0, 1, 0xffffffffUL, 0x100000001UL,
	};
	static const long time_values[][4] = {
		{ 0, 0, 0, 0 },
		{ 1, 2, 0, 1 },
		{ 10, 500, 2, 250 },
		{ 2, 0, 10, 0 },
	};
	static const int bools[] = { 0, 1 };
	static const int ptrace_data_values[] = { 0, 1, 9, 64 };
	static const int process_statuses[] = {
		0, PS_RUNNING, PS_EXITED, PS_ZOMBIE, PS_STOPPED,
	};
	static const int mod_clone_values[] = {
		SPAWN_TO_LOCAL, SPAWN_TO_REMOTE, SPAWNING_TO_REMOTE, 7,
	};

	for (unsigned int f = 0; f < sizeof(clone_flags) / sizeof(clone_flags[0]); f++) {
		for (unsigned int c = 0; c < sizeof(bools) / sizeof(bools[0]); c++)
			mix_signed(digest, clone_flags_result(clone_flags[f],
				bools[c]));
		for (unsigned int s = 0; s < sizeof(stack_values) / sizeof(stack_values[0]); s++) {
			for (unsigned int p = 0; p < sizeof(stack_values) / sizeof(stack_values[0]); p++)
				mix_signed(digest, clone_pthread_marker_result(
					clone_flags[f], stack_values[s],
					stack_values[p]));
		}
		for (unsigned int p = 0; p < sizeof(dirfds) / sizeof(dirfds[0]); p++)
			mix_signed(digest, clone_host_parent_flags_result(
				clone_flags[f], dirfds[p]));
		for (unsigned int b = 0; b < sizeof(bools) / sizeof(bools[0]); b++)
			mix_signed(digest, clone_report_thread_result(
				clone_flags[f], bools[b] ? SIGCHLD : 9));
		mix_signed(digest, clone_parent_tid_store_needed_result(
			clone_flags[f]));
		mix_signed(digest, clone_child_cleartid_needed_result(
			clone_flags[f]));
		mix_signed(digest, clone_child_tid_store_needed_result(
			clone_flags[f]));
		mix_signed(digest, clone_tls_source_result(clone_flags[f]));
	}

	for (unsigned int m = 0; m < sizeof(mod_clone_values) / sizeof(mod_clone_values[0]); m++) {
		mix_signed(digest, clone_remote_spawn_result(
			mod_clone_values[m]));
		for (unsigned int b = 0; b < sizeof(bools) / sizeof(bools[0]); b++)
			mix_signed(digest, clone_use_last_cpu_result(
				mod_clone_values[m], bools[b]));
	}

	for (unsigned int s = 0; s < sizeof(process_statuses) / sizeof(process_statuses[0]); s++)
		mix_signed(digest, clone_parent_use_pid1_result(
			process_statuses[s]));
	for (unsigned int s = 0; s < sizeof(process_statuses) / sizeof(process_statuses[0]); s++)
		mix_signed(digest, ptrace_detach_exit_signal_needed_result(
			process_statuses[s]));
	for (unsigned int d = 0; d < sizeof(ptrace_data_values) / sizeof(ptrace_data_values[0]); d++)
		mix_signed(digest, ptrace_detach_forward_signal_needed_result(
			ptrace_data_values[d]));

	for (unsigned int p = 0; p < sizeof(ptrace_values) / sizeof(ptrace_values[0]); p++) {
		mix_signed(digest, ptrace_exec_event_signal_result(
			ptrace_values[p]));
		mix_signed(digest, ptrace_syscall_event_signal_result(
			ptrace_values[p]));
		for (unsigned int f = 0; f < sizeof(clone_flags) / sizeof(clone_flags[0]); f++)
			mix_signed(digest, ptrace_clone_event_result(
				ptrace_values[p], clone_flags[f]));
	}

	for (unsigned int e = 0; e < sizeof(events) / sizeof(events[0]); e++)
		mix_signed(digest, ptrace_clone_reparent_result(events[e]));

	for (unsigned int f = 0; f < sizeof(exec_flags) / sizeof(exec_flags[0]); f++) {
		for (unsigned int d = 0; d < sizeof(dirfds) / sizeof(dirfds[0]); d++) {
			for (unsigned int c = 0; c < sizeof(first_chars) / sizeof(first_chars[0]); c++)
				mix_signed(digest, execveat_policy_result(
					exec_flags[f], dirfds[d], first_chars[c]));
		}
	}

	for (unsigned int f = 0; f < sizeof(futex_flags) / sizeof(futex_flags[0]); f++) {
		int op = 0x12345678;
		int fshared = 0x12345678;

		mix_signed(digest, futex_decode_flags_result(futex_flags[f],
			&op, &fshared));
		mix_signed(digest, op);
		mix_signed(digest, fshared);
		mix_signed(digest, futex_clock_id_result(futex_flags[f]));
		mix_signed(digest, futex_wait_timeout_needed_result(op, 0));
		mix_signed(digest, futex_wait_timeout_needed_result(op, 1));
		mix_signed(digest, futex_timeout_is_absolute_result(op));
		for (unsigned int a = 0; a < sizeof(arg3_values) / sizeof(arg3_values[0]); a++)
			mix(digest, futex_requeue_val2_result(op, arg3_values[a]));
		for (unsigned int t = 0; t < sizeof(time_values) / sizeof(time_values[0]); t++)
			mix(digest, futex_timeout_ns_result(op, time_values[t][0],
				time_values[t][1], time_values[t][2],
				time_values[t][3]));
	}
}

int main(void)
{
	static const size_t robust_lens[] = { 0, 1, 23, 24, 25, 64 };
	static const int tids[] = { INT_MIN, -2, -1, 0, 1, 12345 };
	static const int sigs[] = { -1, 0, 1, 9, 19, 64, 65 };
	static const int pids[] = { -1, 0, 1, 55 };
	static const int currents[] = { 1, 100 };
	static const int execed[] = { -1, 0, 1, 2 };
	static const long syscall_rcs[] = { -4095, -1, 0, 1, 255 };
	static const unsigned long flags[] = {
		0, VR_RESERVED, VR_IO_NOCACHE, VR_REMOTE,
		VR_RESERVED | VR_REMOTE, 0x4000,
	};
	unsigned long digest = 0x6d63537973506f6cUL;

	for (unsigned int i = 0; i < sizeof(robust_lens) / sizeof(robust_lens[0]); i++)
		mix_signed(&digest, robust_list_len_result(robust_lens[i]));

	for (unsigned int i = 0; i < sizeof(tids) / sizeof(tids[0]); i++)
		mix_signed(&digest, tkill_tid_result(tids[i]));

	for (unsigned int i = 0; i < sizeof(sigs) / sizeof(sigs[0]); i++) {
		mix_signed(&digest, sigaction_validate(sigs[i], 0));
		mix_signed(&digest, sigaction_validate(sigs[i], 1));
	}

	for (unsigned int c = 0; c < sizeof(currents) / sizeof(currents[0]); c++) {
		for (unsigned int p = 0; p < sizeof(pids) / sizeof(pids[0]); p++) {
			int pid = setpgid_normalize_pid(currents[c], pids[p]);

			mix_signed(&digest, pid);
			for (unsigned int g = 0; g < sizeof(pids) / sizeof(pids[0]); g++)
				mix_signed(&digest, setpgid_normalize_pgid(pid, pids[g]));
		}
	}

	for (unsigned int i = 0; i < sizeof(execed) / sizeof(execed[0]); i++)
		mix_signed(&digest, setpgid_execed_result(execed[i]));

	for (unsigned int i = 0; i < sizeof(syscall_rcs) / sizeof(syscall_rcs[0]); i++)
		mix_signed(&digest, syscall_refresh_cred_needed_result(syscall_rcs[i]));
	for (unsigned int i = 0; i < sizeof(pids) / sizeof(pids[0]); i++) {
		mix_signed(&digest, syscall_getpid_result(pids[i]));
		mix_signed(&digest, syscall_getppid_result(pids[i]));
		mix_signed(&digest, syscall_gettid_result(pids[i]));
		mix_signed(&digest, syscall_set_tid_address_return_result(pids[i]));
	}

	for (unsigned int i = 0; i < sizeof(flags) / sizeof(flags[0]); i++) {
		mix_signed(&digest, memlock_range_flag_result(flags[i]));
		mix_signed(&digest, range_has_disallowed_change_flags(flags[i]));
	}

	exercise_memlock(&digest);
	exercise_unmap_protect(&digest);
	exercise_memory_syscall_policy(&digest);
	exercise_brk_mincore_mmap_policy(&digest);
	exercise_signal_time_policy(&digest);
	exercise_signal_wait_policy(&digest);
	exercise_ptrace_process_vm_policy(&digest);
	exercise_wait_policy(&digest);
	exercise_clone_exec_futex_policy(&digest);

	printf("syscall_policy_helpers ok digest=%016lx\n", digest);
	return 0;
}
EOF_SYSCALL_POLICY_HELPERS

cat > "${tmpdir}/xpmem_helpers_equiv.c" <<'EOF_XPMEM_HELPERS'
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

#define XPMEM_RDONLY 0x1
#define XPMEM_RDWR 0x2
#define XPMEM_PERMIT_MODE 0x1
#define XPMEM_PERM_IRUSR 00400
#define XPMEM_PERM_IWUSR 00200
#define XPMEM_FLAG_DESTROYING 0x00040
#define XPMEM_FLAG_VALIDPTEs 0x00200
#define VR_PROT_WRITE 0x00020000UL
#define PAGE_SIZE 4096UL
#define PAGE_MASK (~(PAGE_SIZE - 1))

extern int xpmem_id_to_tgid_result(long);
extern int xpmem_tg_hashtable_index_result(int);
extern int xpmem_ap_hashtable_index_result(long);
extern int xpmem_make_id_result(int, int, long *);
extern int xpmem_positive_id_result(long);
extern int xpmem_owner_policy_result(int, int);
extern int xpmem_make_initial_policy_result(int, unsigned long, size_t);
extern int xpmem_make_alignment_result(unsigned long, size_t);
extern int xpmem_get_policy_result(long, int, int, int);
extern int xpmem_perms_result(int, int, unsigned long, short, int, int);
extern int xpmem_check_permit_mode_result(int, int, int, unsigned long, int,
					  int);
extern int xpmem_validate_access_result(int, int, int, unsigned long, size_t,
					long, size_t, int, unsigned long *);
extern int xpmem_attach_initial_policy_result(long, long, unsigned long,
					      size_t, int, size_t *);
extern int xpmem_destroying_state_result(int, int);
extern int xpmem_is_destroying_result(int);
extern int xpmem_destroying_error_result(int, int);
extern int xpmem_two_destroying_error_result(int, int, int);
extern int xpmem_three_destroying_error_result(int, int, int, int);
extern int xpmem_attach_destroying_result(int, int);
extern int xpmem_close_decision_result(int, int, int *, int *);
extern int xpmem_ref_drop_should_free_result(int);
extern int xpmem_begin_destroy_result(int, int *);
extern int xpmem_finish_destroy_result(int);
extern int xpmem_object_lookup_decision_result(long, long, int, int, int);
extern int xpmem_detach_lookup_result(int, unsigned long, unsigned long, int);
extern int xpmem_attach_overlap_result(int, int, unsigned long, size_t,
				       unsigned long);
extern int xpmem_remove_range_step_result(unsigned long, unsigned long,
					  unsigned long, unsigned long,
					  unsigned long, int, int *, int *,
					  int *, int *);
extern int xpmem_remove_memory_range_action_result(unsigned long,
						   unsigned long,
						   unsigned long, size_t,
						   unsigned long *,
						   unsigned long *, int *,
						   int *);
extern int xpmem_range_private_invalid_result(int, unsigned long,
					      unsigned long, int);
extern int xpmem_clear_pte_range_result(int, unsigned long, unsigned long,
					size_t, unsigned long, unsigned long,
					unsigned long *, unsigned long *,
					int *);
extern int xpmem_fault_vaddr_result(unsigned long, unsigned long, size_t,
				    unsigned long, unsigned long *);
extern int xpmem_straight_phys_result(unsigned long, unsigned long, size_t,
				      unsigned long, unsigned long *, size_t *);
extern int xpmem_remote_pte_missing_result(int, int, int);
extern unsigned long xpmem_seg_phys_plus_off_result(unsigned long, size_t,
						    unsigned long);
extern int xpmem_att_page_fits_result(unsigned long, size_t, unsigned long,
				      unsigned long, size_t);
extern int xpmem_pte_mismatch_result(unsigned long, unsigned long);
extern int xpmem_unpin_step_result(unsigned long, size_t, int,
				   unsigned long *, int *);

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

static void mix_signed(unsigned long *digest, long value)
{
	mix(digest, (unsigned long)value);
}

int main(void)
{
	static const int permit_types[] = { 0, XPMEM_PERMIT_MODE, 2 };
	static const unsigned long permit_values[] = { 0, 0600, 0666, 0777, 01000 };
	static const size_t sizes[] = { 0, 1, 4095, 4096, 8192, ULONG_MAX };
	static const unsigned long addrs[] = {
		0, 1, 4095, 4096, 0x10000UL, ULONG_MAX - 1,
	};
	static const long segids[] = { LONG_MIN, -1, 0, 1, LONG_MAX };
	static const int flags[] = {
		0, XPMEM_RDONLY, XPMEM_RDWR,
		XPMEM_RDONLY | XPMEM_RDWR, 4,
	};
	static const int bools[] = { 0, 1 };
	static const int ids[] = { 0, 1, 1000, 1001 };
	static const int uniqs[] = {
		-1, 0, 1, 7, 8, INT_MAX >> 1, (INT_MAX >> 1) + 1, INT_MAX,
	};
	static const unsigned long modes[] = {
		0, 0001, 0002, 0004, 0020, 0040, 0200, 0400, 0600, 0640, 0666,
	};
	static const short perm_flags[] = { XPMEM_PERM_IRUSR, XPMEM_PERM_IWUSR };
	static const long offsets[] = { LONG_MIN, -1, 0, 1, 4095, 4096, LONG_MAX };
	static const unsigned long seg_vaddrs[] = {
		0, 0x10000UL, 0x18000UL, ULONG_MAX - 0xfffUL,
	};
	static const int destroy_flags[] = {
		0, XPMEM_FLAG_DESTROYING, 0x00080,
		XPMEM_FLAG_DESTROYING | 0x00080, 0x00200,
	};
	static const int error_values[] = { -22, -14, -2, -1, 0, 1 };
	static const int ref_counts[] = { -2, -1, 0, 1, 2, 3 };
	static const unsigned long range_starts[] = {
		0, 1, 4096, 8192, ULONG_MAX,
	};
	unsigned long digest = 0x78706d656d527573UL;

	for (unsigned int id = 0; id < sizeof(segids) / sizeof(segids[0]); id++) {
		mix_signed(&digest, xpmem_id_to_tgid_result(segids[id]));
		mix_signed(&digest, xpmem_ap_hashtable_index_result(segids[id]));
		mix_signed(&digest, xpmem_positive_id_result(segids[id]));
	}

	for (unsigned int t = 0; t < sizeof(ids) / sizeof(ids[0]); t++) {
		mix_signed(&digest, xpmem_tg_hashtable_index_result(ids[t]));
		for (unsigned int u = 0; u < sizeof(uniqs) / sizeof(uniqs[0]); u++) {
			long id = 0x13579bdf2468ace0L;
			int ret = xpmem_make_id_result(ids[t], uniqs[u], &id);

			mix_signed(&digest, ret);
			mix_signed(&digest, id);
			if (!ret) {
				mix_signed(&digest, xpmem_id_to_tgid_result(id));
				mix_signed(&digest, xpmem_ap_hashtable_index_result(id));
			}
		}
	}

	for (unsigned int cp = 0; cp < sizeof(ids) / sizeof(ids[0]); cp++) {
		for (unsigned int tg = 0; tg < sizeof(ids) / sizeof(ids[0]); tg++)
			mix_signed(&digest, xpmem_owner_policy_result(ids[cp],
				ids[tg]));
	}

	for (unsigned int t = 0; t < sizeof(permit_types) / sizeof(permit_types[0]); t++) {
		for (unsigned int v = 0; v < sizeof(permit_values) / sizeof(permit_values[0]); v++) {
			for (unsigned int s = 0; s < sizeof(sizes) / sizeof(sizes[0]); s++)
				mix_signed(&digest, xpmem_make_initial_policy_result(
					permit_types[t], permit_values[v], sizes[s]));
		}
	}

	for (unsigned int a = 0; a < sizeof(addrs) / sizeof(addrs[0]); a++) {
		for (unsigned int s = 0; s < sizeof(sizes) / sizeof(sizes[0]); s++)
			mix_signed(&digest, xpmem_make_alignment_result(addrs[a],
				sizes[s]));
	}

	for (unsigned int id = 0; id < sizeof(segids) / sizeof(segids[0]); id++) {
		for (unsigned int f = 0; f < sizeof(flags) / sizeof(flags[0]); f++) {
			for (unsigned int t = 0; t < sizeof(permit_types) / sizeof(permit_types[0]); t++) {
				for (unsigned int h = 0; h < sizeof(bools) / sizeof(bools[0]); h++)
					mix_signed(&digest, xpmem_get_policy_result(
						segids[id], flags[f], permit_types[t],
						bools[h]));
			}
		}
	}

	for (unsigned int u = 0; u < sizeof(ids) / sizeof(ids[0]); u++) {
		for (unsigned int g = 0; g < sizeof(ids) / sizeof(ids[0]); g++) {
			for (unsigned int m = 0; m < sizeof(modes) / sizeof(modes[0]); m++) {
				for (unsigned int p = 0; p < sizeof(perm_flags) / sizeof(perm_flags[0]); p++) {
					for (unsigned int cu = 0; cu < sizeof(ids) / sizeof(ids[0]); cu++) {
						for (unsigned int cg = 0; cg < sizeof(ids) / sizeof(ids[0]); cg++)
							mix_signed(&digest, xpmem_perms_result(
								ids[u], ids[g], modes[m],
								perm_flags[p], ids[cu], ids[cg]));
					}
				}
			}
		}
	}

	for (unsigned int f = 0; f < sizeof(flags) / sizeof(flags[0]); f++) {
		for (unsigned int m = 0; m < sizeof(modes) / sizeof(modes[0]); m++) {
			for (unsigned int cu = 0; cu < sizeof(ids) / sizeof(ids[0]); cu++) {
				for (unsigned int cg = 0; cg < sizeof(ids) / sizeof(ids[0]); cg++)
					mix_signed(&digest, xpmem_check_permit_mode_result(
						flags[f], ids[1], ids[2], modes[m],
						ids[cu], ids[cg]));
			}
		}
	}

	for (unsigned int id = 0; id < sizeof(segids) / sizeof(segids[0]); id++) {
		for (unsigned int o = 0; o < sizeof(offsets) / sizeof(offsets[0]); o++) {
			for (unsigned int a = 0; a < sizeof(addrs) / sizeof(addrs[0]); a++) {
				for (unsigned int s = 0; s < sizeof(sizes) / sizeof(sizes[0]); s++) {
					for (unsigned int f = 0; f < sizeof(bools) / sizeof(bools[0]); f++) {
						size_t adjusted = 0x12345678abcdef00UL;
						mix_signed(&digest, xpmem_attach_initial_policy_result(
							segids[id], offsets[o], addrs[a],
							sizes[s], bools[f], &adjusted));
						mix(&digest, adjusted);
					}
				}
			}
		}
	}

	for (unsigned int cp = 0; cp < sizeof(ids) / sizeof(ids[0]); cp++) {
		for (unsigned int tg = 0; tg < sizeof(ids) / sizeof(ids[0]); tg++) {
			for (unsigned int apm = 0; apm < sizeof(flags) / sizeof(flags[0]); apm++) {
				for (unsigned int sv = 0; sv < sizeof(seg_vaddrs) / sizeof(seg_vaddrs[0]); sv++) {
					for (unsigned int ss = 0; ss < sizeof(sizes) / sizeof(sizes[0]); ss++) {
						for (unsigned int o = 0; o < sizeof(offsets) / sizeof(offsets[0]); o++) {
							for (unsigned int sz = 0; sz < sizeof(sizes) / sizeof(sizes[0]); sz++) {
								unsigned long vaddr = 0xdeadbeefUL;
								mix_signed(&digest, xpmem_validate_access_result(
									ids[cp], ids[tg], flags[apm],
									seg_vaddrs[sv], sizes[ss],
									offsets[o], sizes[sz], XPMEM_RDWR,
									&vaddr));
								mix(&digest, vaddr);
							}
						}
					}
				}
			}
		}
	}

	for (unsigned int n = 0; n < sizeof(ref_counts) / sizeof(ref_counts[0]); n++) {
		for (unsigned int h = 0; h < sizeof(bools) / sizeof(bools[0]); h++) {
			int flush_objects = 0x1234;
			int exit_partition = 0x5678;

			mix_signed(&digest, xpmem_close_decision_result(
				ref_counts[n], bools[h], &flush_objects,
				&exit_partition));
			mix_signed(&digest, flush_objects);
			mix_signed(&digest, exit_partition);
			mix_signed(&digest, xpmem_ref_drop_should_free_result(
				ref_counts[n]));
		}
	}

	for (unsigned int fl = 0; fl < sizeof(destroy_flags) / sizeof(destroy_flags[0]); fl++) {
		mix_signed(&digest, xpmem_is_destroying_result(destroy_flags[fl]));
		for (unsigned int rd = 0; rd < sizeof(bools) / sizeof(bools[0]); rd++)
			mix_signed(&digest, xpmem_destroying_state_result(
				destroy_flags[fl], bools[rd]));
		{
			int new_flags = 0x2468;

			mix_signed(&digest, xpmem_begin_destroy_result(
				destroy_flags[fl], &new_flags));
			mix_signed(&digest, new_flags);
			mix_signed(&digest, xpmem_finish_destroy_result(
				destroy_flags[fl]));
		}
		for (unsigned int e = 0; e < sizeof(error_values) / sizeof(error_values[0]); e++)
			mix_signed(&digest, xpmem_destroying_error_result(
				destroy_flags[fl], error_values[e]));
		for (unsigned int tg = 0; tg < sizeof(destroy_flags) / sizeof(destroy_flags[0]); tg++)
			mix_signed(&digest, xpmem_attach_destroying_result(
				destroy_flags[fl], destroy_flags[tg]));
		for (unsigned int tg = 0; tg < sizeof(destroy_flags) / sizeof(destroy_flags[0]); tg++) {
			for (unsigned int e = 0; e < sizeof(error_values) / sizeof(error_values[0]); e++)
				mix_signed(&digest, xpmem_two_destroying_error_result(
					destroy_flags[fl], destroy_flags[tg],
					error_values[e]));
			for (unsigned int att = 0; att < sizeof(destroy_flags) / sizeof(destroy_flags[0]); att++) {
				for (unsigned int e = 0; e < sizeof(error_values) / sizeof(error_values[0]); e++)
					mix_signed(&digest, xpmem_three_destroying_error_result(
						destroy_flags[fl], destroy_flags[tg],
						destroy_flags[att], error_values[e]));
			}
		}
	}

	for (unsigned int c = 0; c < sizeof(segids) / sizeof(segids[0]); c++) {
		for (unsigned int r = 0; r < sizeof(segids) / sizeof(segids[0]); r++) {
			for (unsigned int fl = 0; fl < sizeof(destroy_flags) / sizeof(destroy_flags[0]); fl++) {
				for (unsigned int rd = 0; rd < sizeof(bools) / sizeof(bools[0]); rd++) {
					for (unsigned int stop = 0; stop < sizeof(bools) / sizeof(bools[0]); stop++)
						mix_signed(&digest,
							xpmem_object_lookup_decision_result(
								segids[c], segids[r],
								destroy_flags[fl],
								bools[rd], bools[stop]));
				}
			}
		}
	}

	for (unsigned int hr = 0; hr < sizeof(bools) / sizeof(bools[0]); hr++) {
		for (unsigned int rs = 0; rs < sizeof(range_starts) / sizeof(range_starts[0]); rs++) {
			for (unsigned int a = 0; a < sizeof(addrs) / sizeof(addrs[0]); a++) {
				for (unsigned int hp = 0; hp < sizeof(bools) / sizeof(bools[0]); hp++)
					mix_signed(&digest, xpmem_detach_lookup_result(
						bools[hr], range_starts[rs],
						addrs[a], bools[hp]));
			}
		}
	}

	for (unsigned int cp = 0; cp < sizeof(ids) / sizeof(ids[0]); cp++) {
		for (unsigned int tg = 0; tg < sizeof(ids) / sizeof(ids[0]); tg++) {
			for (unsigned int rv = 0; rv < sizeof(addrs) / sizeof(addrs[0]); rv++) {
				for (unsigned int sz = 0; sz < sizeof(sizes) / sizeof(sizes[0]); sz++) {
					for (unsigned int sv = 0; sv < sizeof(seg_vaddrs) / sizeof(seg_vaddrs[0]); sv++)
						mix_signed(&digest, xpmem_attach_overlap_result(
							ids[cp], ids[tg], addrs[rv],
							sizes[sz], seg_vaddrs[sv]));
				}
			}
		}
	}

	for (unsigned int rs = 0; rs < sizeof(range_starts) / sizeof(range_starts[0]); rs++) {
		for (unsigned int re = 0; re < sizeof(range_starts) / sizeof(range_starts[0]); re++) {
			for (unsigned int st = 0; st < sizeof(range_starts) / sizeof(range_starts[0]); st++) {
				for (unsigned int en = 0; en < sizeof(range_starts) / sizeof(range_starts[0]); en++) {
					int split_start = 0x1234;
					int split_end = 0x1234;
					int ro_freed = 0x1234;
					int remove_private = 0x1234;

					mix_signed(&digest, xpmem_remove_range_step_result(
						range_starts[rs], range_starts[re],
						range_starts[st], range_starts[en],
						(en & 1) ? VR_PROT_WRITE : 0,
						en & 1, &split_start, &split_end,
						&ro_freed, &remove_private));
					mix_signed(&digest, split_start);
					mix_signed(&digest, split_end);
					mix_signed(&digest, ro_freed);
					mix_signed(&digest, remove_private);
				}
			}
		}
	}

	for (unsigned int vs = 0; vs < sizeof(range_starts) / sizeof(range_starts[0]); vs++) {
		for (unsigned int ve = 0; ve < sizeof(range_starts) / sizeof(range_starts[0]); ve++) {
			for (unsigned int av = 0; av < sizeof(seg_vaddrs) / sizeof(seg_vaddrs[0]); av++) {
				for (unsigned int sz = 0; sz < sizeof(sizes) / sizeof(sizes[0]); sz++) {
					unsigned long remaining = 0x1111;
					unsigned long middle = 0x2222;
					int full = 0x3333;
					int needs_middle = 0x4444;

					mix_signed(&digest,
						xpmem_remove_memory_range_action_result(
							range_starts[vs], range_starts[ve],
							seg_vaddrs[av], sizes[sz],
							&remaining, &middle, &full,
							&needs_middle));
					mix(&digest, remaining);
					mix(&digest, middle);
					mix_signed(&digest, full);
					mix_signed(&digest, needs_middle);
				}
			}
		}
	}

	for (unsigned int h = 0; h < sizeof(bools) / sizeof(bools[0]); h++) {
		for (unsigned int rs = 0; rs < sizeof(range_starts) / sizeof(range_starts[0]); rs++) {
			for (unsigned int v = 0; v < sizeof(addrs) / sizeof(addrs[0]); v++) {
				for (unsigned int m = 0; m < sizeof(bools) / sizeof(bools[0]); m++)
					mix_signed(&digest, xpmem_range_private_invalid_result(
						bools[h], range_starts[rs], addrs[v],
						bools[m]));
			}
		}
	}

	for (unsigned int fl = 0; fl < sizeof(destroy_flags) / sizeof(destroy_flags[0]); fl++) {
		for (unsigned int av = 0; av < sizeof(seg_vaddrs) / sizeof(seg_vaddrs[0]); av++) {
			for (unsigned int at = 0; at < sizeof(addrs) / sizeof(addrs[0]); at++) {
				for (unsigned int sz = 0; sz < sizeof(sizes) / sizeof(sizes[0]); sz++) {
					for (unsigned int st = 0; st < sizeof(addrs) / sizeof(addrs[0]); st++) {
						unsigned long unpin_at = 0xaaaa;
						unsigned long invalidate_len = 0xbbbb;
						int clear_valid = 0xcccc;

						mix_signed(&digest, xpmem_clear_pte_range_result(
							destroy_flags[fl], seg_vaddrs[av],
							addrs[at], sizes[sz], addrs[st],
							addrs[(st + 1) % (sizeof(addrs) / sizeof(addrs[0]))],
							&unpin_at, &invalidate_len,
							&clear_valid));
						mix(&digest, unpin_at);
						mix(&digest, invalidate_len);
						mix_signed(&digest, clear_valid);

						unpin_at = 0xaaaa;
						invalidate_len = 0xbbbb;
						clear_valid = 0xcccc;
						mix_signed(&digest, xpmem_clear_pte_range_result(
							destroy_flags[fl] | XPMEM_FLAG_VALIDPTEs,
							seg_vaddrs[av], addrs[at], sizes[sz],
							addrs[st],
							addrs[(st + 1) % (sizeof(addrs) / sizeof(addrs[0]))],
							&unpin_at, &invalidate_len,
							&clear_valid));
						mix(&digest, unpin_at);
						mix(&digest, invalidate_len);
						mix_signed(&digest, clear_valid);
					}
				}
			}
		}
	}

	for (unsigned int v = 0; v < sizeof(addrs) / sizeof(addrs[0]); v++) {
		for (unsigned int at = 0; at < sizeof(addrs) / sizeof(addrs[0]); at++) {
			for (unsigned int sz = 0; sz < sizeof(sizes) / sizeof(sizes[0]); sz++) {
				for (unsigned int av = 0; av < sizeof(seg_vaddrs) / sizeof(seg_vaddrs[0]); av++) {
					unsigned long seg_vaddr = 0xfeedfaceUL;

					mix_signed(&digest, xpmem_fault_vaddr_result(
						addrs[v], addrs[at], sizes[sz],
						seg_vaddrs[av], &seg_vaddr));
					mix(&digest, seg_vaddr);
				}
			}
		}
	}

	for (unsigned int sv = 0; sv < sizeof(seg_vaddrs) / sizeof(seg_vaddrs[0]); sv++) {
		for (unsigned int base = 0; base < sizeof(seg_vaddrs) / sizeof(seg_vaddrs[0]); base++) {
			for (unsigned int sz = 0; sz < sizeof(sizes) / sizeof(sizes[0]); sz++) {
				unsigned long seg_phys = 0x12345678UL;
				size_t seg_pgsize = 0x1234;

				mix_signed(&digest, xpmem_straight_phys_result(
					seg_vaddrs[sv], seg_vaddrs[base],
					sizes[sz], 0x40000000UL, &seg_phys,
					&seg_pgsize));
				mix(&digest, seg_phys);
				mix(&digest, seg_pgsize);
			}
		}
	}

	for (unsigned int h = 0; h < sizeof(bools) / sizeof(bools[0]); h++) {
		for (unsigned int empty = 0; empty < sizeof(bools) / sizeof(bools[0]); empty++) {
			for (unsigned int page_in = 0; page_in < sizeof(bools) / sizeof(bools[0]); page_in++)
				mix_signed(&digest, xpmem_remote_pte_missing_result(
					bools[h], bools[empty], bools[page_in]));
		}
	}

	for (unsigned int phys = 0; phys < sizeof(seg_vaddrs) / sizeof(seg_vaddrs[0]); phys++) {
		for (unsigned int sz = 1; sz < sizeof(sizes) / sizeof(sizes[0]); sz++) {
			for (unsigned int sv = 0; sv < sizeof(seg_vaddrs) / sizeof(seg_vaddrs[0]); sv++)
				mix(&digest, xpmem_seg_phys_plus_off_result(
					seg_vaddrs[phys], sizes[sz], seg_vaddrs[sv]));
		}
	}

	for (unsigned int pg = 0; pg < sizeof(addrs) / sizeof(addrs[0]); pg++) {
		for (unsigned int sz = 1; sz < sizeof(sizes) / sizeof(sizes[0]); sz++) {
			for (unsigned int st = 0; st < sizeof(range_starts) / sizeof(range_starts[0]); st++) {
				for (unsigned int en = 0; en < sizeof(range_starts) / sizeof(range_starts[0]); en++)
					mix_signed(&digest, xpmem_att_page_fits_result(
						addrs[pg], sizes[sz], range_starts[st],
						range_starts[en], sizes[sz]));
			}
		}
	}

	for (unsigned int a = 0; a < sizeof(addrs) / sizeof(addrs[0]); a++) {
		for (unsigned int b = 0; b < sizeof(seg_vaddrs) / sizeof(seg_vaddrs[0]); b++)
			mix_signed(&digest, xpmem_pte_mismatch_result(
				addrs[a], seg_vaddrs[b]));
	}

	for (unsigned int v = 0; v < sizeof(addrs) / sizeof(addrs[0]); v++) {
		for (unsigned int sz = 1; sz < sizeof(sizes) / sizeof(sizes[0]); sz++) {
			for (unsigned int h = 0; h < sizeof(bools) / sizeof(bools[0]); h++) {
				unsigned long next_vaddr = 0x1234;
				int unpinned = 0x5678;

				mix_signed(&digest, xpmem_unpin_step_result(
					addrs[v], sizes[sz], bools[h],
					&next_vaddr, &unpinned));
				mix(&digest, next_vaddr);
				mix_signed(&digest, unpinned);
			}
		}
	}

	printf("xpmem_helpers ok digest=%016lx\n", digest);
	return 0;
}
EOF_XPMEM_HELPERS

cat > "${tmpdir}/object_helpers_equiv.c" <<'EOF_OBJECT_HELPERS'
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>

extern int memobj_unref_should_free_result(int);
extern int memobj_op_present_result(uintptr_t);
extern int memobj_missing_page_op_result(void);
extern uintptr_t memobj_missing_copy_page_result(void);
extern int memobj_default_page_op_result(void);
extern int memobj_has_pager_flags_result(unsigned int);
extern int memobj_is_removable_flags_result(unsigned int);
extern int memobj_flushable_page_result(int, int);
extern int memobj_flushable_obj_result(int, unsigned int);
extern int memobj_is_freeable_result(int, unsigned int);
extern int memobj_callable_remap_file_pages_result(int, unsigned int);
extern int fileobj_page_hash_result(long);
extern int fileobj_page_mode_valid_result(int);
extern int fileobj_lookup_ref_keep_result(int);
extern int fileobj_create_base_flags_result(int);
extern int fileobj_apply_result_flags_result(int, int);
extern int fileobj_status_from_flags_result(int);
extern int fileobj_hugetlbfs_result(int);
extern int fileobj_premap_zerofill_result(int);
extern int fileobj_premap_npages_result(size_t);
extern int fileobj_validate_p2align_result(int);
extern int fileobj_get_page_action_result(int, int, int *);
extern int fileobj_pageio_zero_result(int);
extern int fileobj_pageio_mode_after_read_result(ssize_t, size_t);
extern int fileobj_flush_skip_result(int, int);
extern int fileobj_initial_refcnt_result(void);
extern unsigned long fileobj_initial_sref_result(void);
extern int fileobj_premap_start_node_result(int);
extern int fileobj_premap_next_node_result(int, int);
extern size_t fileobj_pages_bytes_result(int);
extern int fileobj_premap_page_index_result(long);
extern int fileobj_alloc_npages_result(int);
extern unsigned long fileobj_alloc_flags_result(int);
extern size_t fileobj_alloc_size_result(int);
extern size_t fileobj_pageio_pgsize_result(int);
extern int fileobj_pageio_should_schedule_result(int);
extern int fileobj_new_page_mode_result(void);
extern int fileobj_mapped_mode_result(void);
extern int fileobj_path_present_result(unsigned long);
extern int fileobj_invalid_page_count_result(int);
extern int fileobj_should_free_hashed_page_result(int, int);
extern int fileobj_premap_page_present_result(uintptr_t);
extern int fileobj_lookup_page_error_result(int);
extern unsigned long fileobj_next_sref_result(unsigned long);
extern int fileobj_premap_interleave_result(unsigned long);
extern size_t devobj_npages_result(size_t);
extern size_t devobj_pfn_table_npages_result(size_t);
extern size_t devobj_pfn_table_bytes_result(size_t);
extern long devobj_pgoff_result(long);
extern int devobj_get_page_index_result(long, long, size_t, int *);
extern int devobj_cached_pfn_needs_fetch_result(uintptr_t);
extern int devobj_pfn_present_result(uintptr_t);
extern uintptr_t devobj_pfn_attr_result(uintptr_t);
extern uintptr_t devobj_pfn_phys_result(uintptr_t);
extern int devobj_pfn_absent_error_result(uintptr_t);
extern int devobj_base_flags_result(void);
extern int devobj_initial_refcnt_result(void);
extern long devobj_pfn_request_offset_result(long);
extern int devobj_should_store_pfn_result(uintptr_t);
extern size_t devobj_map_size_result(void);
extern int devobj_path_present_result(unsigned long);
extern int devobj_pfn_table_present_result(uintptr_t);
extern uintptr_t devobj_mapped_pfn_result(uintptr_t, uintptr_t);
extern int sysfs_path_error_result(ssize_t, int, size_t);
extern int sysfs_special_kind_result(long);
extern int sysfs_string_nbits_result(size_t);
extern int sysfs_response_error_result(ssize_t);
extern int sysfs_param_sizes_valid_result(size_t, size_t, size_t, size_t,
					  size_t, size_t);
extern size_t sysfs_data_bufsize_result(void);
extern int sysfs_packet_error_result(int, int);
extern int sysfs_request_busy_result(int);
extern int sysfs_handle_pointer_valid_result(uintptr_t);
extern ssize_t sysfs_default_response_ssize_result(void);
extern int sysfs_release_response_error_result(void);
extern int sysfs_request_handler_kind_result(int);
extern int sysfs_pointer_missing_result(uintptr_t);
extern int sysfs_should_call_show_result(uintptr_t);
extern int sysfs_should_call_store_result(uintptr_t);
extern int sysfs_should_call_release_result(uintptr_t);
extern unsigned long procfs_mem_reason_result(int);
extern int procfs_mem_chunk_size_result(unsigned long, unsigned long);
extern int procfs_pagemap_range_result(unsigned long, int,
				       unsigned long *, unsigned long *);
extern int procfs_status_state_result(int);
extern char procfs_thread_stat_state_result(int, int);
extern int procfs_default_count_result(void);
extern int procfs_remote_count_result(unsigned long, int);
extern int procfs_remote_npages_result(int);
extern int procfs_format_error_result(int, int);
extern unsigned long procfs_locked_kb_result(unsigned long);
extern char procfs_maps_read_char_result(unsigned long);
extern char procfs_maps_write_char_result(unsigned long);
extern char procfs_maps_exec_char_result(unsigned long);
extern char procfs_maps_private_char_result(unsigned long);
extern int procfs_maps_path_kind_result(unsigned long, unsigned long,
					unsigned long, unsigned long,
					unsigned long, unsigned long,
					unsigned long);
extern unsigned long procfs_pagemap_next_result(unsigned long);
extern unsigned int procfs_auxv_limit_result(void);
extern unsigned int procfs_cmdline_limit_result(uintptr_t, unsigned int);
extern int procfs_is_release_result(int);
extern int procfs_root_matched_result(int);
extern int procfs_osnum_match_result(int, int);
extern int procfs_zero_length_result(unsigned long);
extern unsigned long procfs_locked_size_add_result(unsigned long,
						   unsigned long,
						   unsigned long,
						   unsigned long);
extern int procfs_bitmask_next_offset_result(int, int);
extern int procfs_pbuf_is_empty_result(unsigned long);
extern int procfs_backlog_needed_result(uintptr_t);
extern int procfs_lock_failed_action_result(uintptr_t);
extern int procfs_lock_retry_result(void);
extern int procfs_thread_tid_result(int, int, int);
extern int procfs_task_missing_terminal_result(int);
extern int procfs_pointer_present_result(uintptr_t);
extern int procfs_buffer_chain_attach_result(unsigned long, uintptr_t);
extern int procfs_entry_kind_result(const char *);
extern uintptr_t procfs_comm_basename_result(uintptr_t);
extern uintptr_t procfs_comm_name_result(uintptr_t, uintptr_t);
extern int pager_linux_io_retry_result(ssize_t);
extern int pager_linux_io_stop_result(ssize_t);
extern int pager_linux_io_first_result(ssize_t);
extern ssize_t pager_linux_io_advance_result(ssize_t, ssize_t);
extern size_t pager_linux_io_remaining_result(size_t, ssize_t);
extern uintptr_t pager_linux_io_next_buf_result(uintptr_t, ssize_t);
extern int pager_linux_io_complete_result(ssize_t, size_t);
extern int pager_copy_fault_retry_result(int);
extern int pager_copy_fault_error_result(int);
extern int pager_myalloc_fits_result(size_t, size_t, size_t);
extern size_t pager_myalloc_next_alloced_result(size_t, size_t);
extern int pager_copy_size_error_result(size_t);
extern unsigned long pager_fault_addr_result(unsigned long);
extern size_t pager_read_chunk_size_result(size_t, size_t);
extern int pager_arealist_tail_room_result(int);
extern int pager_arealist_count_add_result(int, int);
extern ssize_t pager_addrpair_size_result(unsigned long, unsigned long);
extern ssize_t pager_file_pos_result(ssize_t, ssize_t);
extern ssize_t pager_arealist_write_result(ssize_t, int, size_t);
extern int pager_mlock_more_result(unsigned long);
extern unsigned long pager_mlock_next_start_result(unsigned long);
extern int pager_mlock_container_empty_result(uintptr_t, uintptr_t, int, int);
extern int pager_mlock_needs_next_result(int, int);
extern int pager_mlock_reset_count_result(void);
extern int pager_mlock_next_count_result(int);
extern ssize_t pager_pagein_data_pos_result(unsigned int, unsigned int,
					    size_t, size_t);
extern int pager_pageout_args_result(uintptr_t, uintptr_t, size_t,
				     unsigned long, unsigned long);
extern int pager_skip_anon_range_result(int, unsigned long, unsigned long,
					unsigned long, unsigned long,
					unsigned long, unsigned long);
extern int pager_range_locked_result(unsigned long);
extern int pager_skip_physical_removal_result(int);
extern int pager_fd_valid_result(int);
extern int pager_should_unlink_swap_result(long);
extern long pager_io_short_result(long);
extern int zeroobj_initial_flags_result(void);
extern int zeroobj_initial_refcnt_result(void);
extern int zeroobj_initial_page_mode_result(void);
extern long zeroobj_initial_page_offset_result(void);
extern int zeroobj_get_page_validate_result(long, int, int);
extern int shmobj_init_pgshift_result(int);
extern size_t shmobj_pgsize_result(int);
extern int shmobj_initial_flags_result(void);
extern int shmobj_indexed_flags_result(int);
extern size_t shmobj_real_segsz_result(size_t, size_t);
extern int shmobj_page_contains_offset_result(long, int, long);
extern int shmobj_destroy_page_npages_result(int);
extern size_t shmobj_destroy_page_size_result(int);
extern int shmobj_destroy_index_word_result(int);
extern unsigned long shmobj_destroy_index_mask_result(int);
extern int shmlock_user_locked_result(size_t);
extern int shmlock_user_match_result(int, int);
extern int shmlock_user_is_list_head_result(uintptr_t, uintptr_t);
extern size_t shmlock_user_after_unlock_result(size_t, size_t);
extern int shmlock_user_should_free_result(size_t);
extern int shmobj_has_user_result(uintptr_t);
extern int shmobj_destroy_page_count_invalid_result(int);
extern int shmobj_destroy_page_should_free_result(int, int);
extern int shmobj_should_free_direct_result(int);
extern int shmobj_destroy_missing_flag_result(int);
extern int shmobj_initial_refcnt_result(void);
extern int shmobj_initial_index_result(void);
extern int shmobj_initial_ds_pgshift_result(void);
extern int shmobj_get_page_validate_result(size_t, long, int);
extern int shmobj_lookup_page_validate_result(size_t, long);
extern int shmobj_page_npages_result(int);
extern int shmobj_page_pgshift_result(int);
extern int shmobj_need_alloc_page_result(uintptr_t);
extern int shmobj_new_page_mode_result(void);
extern int shmobj_new_page_count_result(void);
extern long shmobj_new_page_mapped_result(void);
extern int shmobj_page_mode_valid_for_new_result(int);
extern int shmobj_lookup_page_missing_error_result(uintptr_t);
extern int shmobj_lookup_should_store_phys_result(uintptr_t);
extern int shmobj_update_args_result(int, int, int);
extern size_t shmobj_update_orig_pgsize_result(int);
extern uintptr_t shmobj_update_page_phys_result(uintptr_t, size_t);
extern long shmobj_update_page_offset_result(long, size_t);
extern int shmobj_pte_missing_result(uintptr_t);
extern int shmobj_update_has_more_pages_result(size_t, size_t);
extern size_t shmobj_update_next_page_off_result(size_t, size_t);
extern int hugefileobj_expected_p2align_result(int);
extern int hugefileobj_validate_p2align_result(int, int);
extern long hugefileobj_page_index_result(long, int);
extern int hugefileobj_npages_per_page_result(size_t);
extern size_t hugefileobj_pgsize_result(int);
extern int hugefileobj_initial_status_result(void);
extern int hugefileobj_initial_refcnt_result(void);
extern int hugefileobj_pointer_present_result(uintptr_t);
extern int hugefileobj_pointer_missing_result(uintptr_t);
extern int hugefileobj_page_present_result(uintptr_t);
extern size_t hugefileobj_page_array_bytes_result(size_t);
extern int hugefileobj_create_nr_pages_result(long, size_t, int);
extern int hugefileobj_needs_grow_result(size_t, int);
extern size_t hugefileobj_copy_bytes_result(size_t);
extern size_t hugefileobj_zero_bytes_result(size_t, size_t);
extern size_t hugefileobj_zero_start_index_result(size_t);

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

static void mix_signed(unsigned long *digest, long value)
{
	mix(digest, (unsigned long)value);
}

static long ptr_offset(const char *base, uintptr_t ptr)
{
	if (!ptr)
		return -1;
	return (const char *)ptr - base;
}

int main(void)
{
	const long offsets[] = { -8192, -1, 0, 1, 4095, 4096, 1048576 };
	const int modes[] = { 0, 1, 2, 3, 4, 5, 6, 7, 8, -1 };
	const int flags[] = { 0, 2, 0x8, 0x10, 0x8000, 0x8010,
			      0x100000, 0x200000, 0x400000, 0x401010 };
	const unsigned int memobj_flags[] = {
		0, 0x1, 0x4, 0x10, 0x10000, 0x200000, 0x400000,
		0x11, 0x10001, 0x210010, 0x600000, 0xffffffffU,
	};
	const unsigned long mpol_flags[] = { 0, 1, 2, 4, 8, 9, 0xffffffffUL };
	const size_t sizes[] = { 0, 1, 4095, 4096, 4097, 8191,
				 8192, ~0UL - 2048 };
	const uintptr_t pfns[] = { 0, 1, 0x1001, 0x8000000000000000UL,
				   0x8000000000001001UL,
				   0x0100000000003001UL };
	const long ops[] = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 999, -1 };
	const int statuses[] = { 1, 2, 4, 8, 0x10, 0x20, 0x40, 0x60, 0 };
	const ssize_t io_rets[] = { -4, -1, 0, 1, 4096 };
	const unsigned long addrs[] = { 0, 1, 4095, 4096, 0x12345 };
	const int pgshifts[] = { 0, 12, 21, 30 };
	const long page_offsets[] = { 0, 1, 4096, 8192 };
	const size_t seg_sizes[] = { 0, 1, 4095, 4096, 4097, 8192 };
	const int p2aligns[] = { 0, 1, 2 };
	const int counts[] = { 0, 1, 8, 1024, 4095, 4096, 4097 };
	const int messages[] = { 0x14, 0x15, 0x3a, 0x3b, 0x3c, 0x3e, 0x40 };
	const char *procfs_names[] = {
		"", "mckernel", "stat", "cpuinfo", "mem", "maps",
		"pagemap", "status", "auxv", "cmdline", "comm",
		"unknown", "maps/", "command",
	};
	const char *cmdlines[] = {
		"", "exe", "/bin/sh", "/usr/bin/python3", "relative/path",
		"/trailing/",
	};
	const unsigned long map_flags[] = {
		0, 0x1, 0x2000, 0x10000, 0x20000, 0x40000,
		0x70000, 0x12001, 0x4000, 0x54000,
	};
	unsigned long digest = 0x0b1ec75eed5eedUL;
	unsigned long start = 0;
	unsigned long end = 0;
	int err = 0;
	int ix = 0;

	for (int ref = -2; ref <= 2; ref++)
		mix_signed(&digest, memobj_unref_should_free_result(ref));
	for (unsigned long ptr = 0; ptr <= 2; ptr++)
		mix_signed(&digest, memobj_op_present_result(ptr));
	mix_signed(&digest, memobj_missing_page_op_result());
	mix(&digest, memobj_missing_copy_page_result());
	mix_signed(&digest, memobj_default_page_op_result());
	for (int has_page = 0; has_page <= 1; has_page++) {
		for (int in_memobj = 0; in_memobj <= 1; in_memobj++)
			mix_signed(&digest,
				memobj_flushable_page_result(has_page, in_memobj));
	}
	for (unsigned int i = 0; i < sizeof(memobj_flags) / sizeof(memobj_flags[0]); i++) {
		for (int has_memobj = 0; has_memobj <= 1; has_memobj++) {
			mix_signed(&digest,
				memobj_flushable_obj_result(has_memobj,
					memobj_flags[i]));
			mix_signed(&digest,
				memobj_is_freeable_result(has_memobj,
					memobj_flags[i]));
			mix_signed(&digest,
				memobj_callable_remap_file_pages_result(
					has_memobj, memobj_flags[i]));
		}
		mix_signed(&digest,
			memobj_has_pager_flags_result(memobj_flags[i]));
		mix_signed(&digest,
			memobj_is_removable_flags_result(memobj_flags[i]));
	}

	for (unsigned int i = 0; i < sizeof(offsets) / sizeof(offsets[0]); i++) {
		mix_signed(&digest, fileobj_page_hash_result(offsets[i]));
		mix_signed(&digest, devobj_pgoff_result(offsets[i]));
	}
	for (unsigned long sref = 0; sref <= 4; sref++)
		mix(&digest, fileobj_next_sref_result(sref));
	for (unsigned int i = 0; i < sizeof(mpol_flags) / sizeof(mpol_flags[0]); i++)
		mix_signed(&digest, fileobj_premap_interleave_result(mpol_flags[i]));

	for (unsigned int i = 0; i < sizeof(modes) / sizeof(modes[0]); i++) {
		mix_signed(&digest, fileobj_page_mode_valid_result(modes[i]));
		mix_signed(&digest, fileobj_get_page_action_result(0, modes[i], &err));
		mix_signed(&digest, err);
		mix_signed(&digest, fileobj_get_page_action_result(1, modes[i], &err));
		mix_signed(&digest, err);
	}

	for (int ref = -1; ref <= 4; ref++)
		mix_signed(&digest, fileobj_lookup_ref_keep_result(ref));

	for (unsigned int i = 0; i < sizeof(flags) / sizeof(flags[0]); i++) {
		int base = fileobj_create_base_flags_result(flags[i]);
		int applied = fileobj_apply_result_flags_result(base, flags[i]);

		mix_signed(&digest, base);
		mix_signed(&digest, applied);
		mix_signed(&digest, fileobj_status_from_flags_result(applied));
		mix_signed(&digest, fileobj_hugetlbfs_result(flags[i]));
		mix_signed(&digest, fileobj_premap_zerofill_result(flags[i]));
		mix_signed(&digest, fileobj_pageio_zero_result(flags[i]));
		mix_signed(&digest, fileobj_flush_skip_result(flags[i], 0));
		mix_signed(&digest, fileobj_flush_skip_result(flags[i], 1));
		mix(&digest, fileobj_alloc_flags_result(flags[i]));
	}

	mix_signed(&digest, fileobj_initial_refcnt_result());
	mix(&digest, fileobj_initial_sref_result());
	mix_signed(&digest, fileobj_new_page_mode_result());
	mix_signed(&digest, fileobj_mapped_mode_result());
	for (unsigned long value = 0; value <= 2; value++) {
		mix_signed(&digest, fileobj_path_present_result(value));
		mix_signed(&digest, devobj_path_present_result(value));
		mix_signed(&digest, devobj_pfn_table_present_result(value));
		mix_signed(&digest, fileobj_premap_page_present_result(value));
	}
	for (int count = -1; count <= 3; count++) {
		mix_signed(&digest, fileobj_invalid_page_count_result(count));
		mix_signed(&digest, fileobj_should_free_hashed_page_result(count, 0));
		mix_signed(&digest, fileobj_should_free_hashed_page_result(count, 1));
	}
	mix_signed(&digest, fileobj_lookup_page_error_result(0));
	mix_signed(&digest, fileobj_lookup_page_error_result(1));
	for (int nodes = 1; nodes <= 8; nodes++) {
		int node = fileobj_premap_start_node_result(nodes);

		mix_signed(&digest, node);
		for (int step = 0; step < 10; step++) {
			node = fileobj_premap_next_node_result(node, nodes);
			mix_signed(&digest, node);
		}
	}
	for (int pages = 0; pages <= 7; pages++)
		mix(&digest, fileobj_pages_bytes_result(pages));
	for (unsigned int i = 0; i < sizeof(offsets) / sizeof(offsets[0]); i++)
		mix_signed(&digest, fileobj_premap_page_index_result(offsets[i]));
	for (unsigned int i = 0; i < sizeof(p2aligns) / sizeof(p2aligns[0]); i++) {
		int npages = fileobj_alloc_npages_result(p2aligns[i]);

		mix_signed(&digest, npages);
		mix(&digest, fileobj_alloc_size_result(npages));
		mix(&digest, fileobj_pageio_pgsize_result(p2aligns[i]));
	}
	for (int attempts = 0; attempts <= 100; attempts += 25)
		mix_signed(&digest, fileobj_pageio_should_schedule_result(attempts));

	for (unsigned int i = 0; i < sizeof(sizes) / sizeof(sizes[0]); i++) {
		mix_signed(&digest, fileobj_premap_npages_result(sizes[i]));
		mix(&digest, devobj_npages_result(sizes[i]));
		mix(&digest, devobj_pfn_table_npages_result(sizes[i]));
		mix(&digest, devobj_pfn_table_bytes_result(sizes[i]));
		mix_signed(&digest, sysfs_string_nbits_result(sizes[i]));
	}

	for (int align = -1; align <= 2; align++)
		mix_signed(&digest, fileobj_validate_p2align_result(align));

	for (long ssize = -5; ssize <= 8192; ssize += 4096)
		mix_signed(&digest, fileobj_pageio_mode_after_read_result(ssize, 4096));

	for (long base = -1; base <= 2; base++) {
		for (long pgoff = -1; pgoff <= 5; pgoff++) {
			ix = 0x76543210;
			mix_signed(&digest, devobj_get_page_index_result(pgoff, base, 3, &ix));
			mix_signed(&digest, ix);
		}
	}

	for (unsigned int i = 0; i < sizeof(pfns) / sizeof(pfns[0]); i++) {
		mix_signed(&digest, devobj_cached_pfn_needs_fetch_result(pfns[i]));
		mix_signed(&digest, devobj_pfn_present_result(pfns[i]));
		mix(&digest, devobj_pfn_attr_result(pfns[i]));
		mix(&digest, devobj_pfn_phys_result(pfns[i]));
		mix_signed(&digest, devobj_pfn_absent_error_result(pfns[i]));
		mix_signed(&digest, devobj_should_store_pfn_result(pfns[i]));
	}
	mix_signed(&digest, devobj_base_flags_result());
	mix_signed(&digest, devobj_initial_refcnt_result());
	mix(&digest, devobj_map_size_result());
	for (unsigned int i = 0; i < sizeof(offsets) / sizeof(offsets[0]); i++)
		mix_signed(&digest, devobj_pfn_request_offset_result(offsets[i]));
	for (unsigned int i = 0; i < sizeof(pfns) / sizeof(pfns[0]); i++) {
		for (unsigned int j = 0; j < sizeof(pfns) / sizeof(pfns[0]); j++)
			mix(&digest, devobj_mapped_pfn_result(pfns[i], pfns[j]));
	}

	for (ssize_t n = -1; n <= 1025; n += 513) {
		mix_signed(&digest, sysfs_path_error_result(n, 0, 1024));
		mix_signed(&digest, sysfs_path_error_result(n, 1, 1024));
	}

	for (unsigned int i = 0; i < sizeof(ops) / sizeof(ops[0]); i++)
		mix_signed(&digest, sysfs_special_kind_result(ops[i]));

	for (ssize_t ssize = -5; ssize <= 5; ssize += 5)
		mix_signed(&digest, sysfs_response_error_result(ssize));
	mix_signed(&digest, sysfs_param_sizes_valid_result(1024, 1024,
		1024, 1024, 1024, 1024));
	mix_signed(&digest, sysfs_param_sizes_valid_result(4097, 1024,
		1024, 1024, 1024, 1024));
	mix(&digest, sysfs_data_bufsize_result());
	for (int send_error = -1; send_error <= 1; send_error++) {
		for (int packet_error = -1; packet_error <= 1; packet_error++)
			mix_signed(&digest, sysfs_packet_error_result(send_error,
				packet_error));
	}
	for (int busy = -1; busy <= 1; busy++)
		mix_signed(&digest, sysfs_request_busy_result(busy));
	for (unsigned long handlep = 0; handlep <= 2; handlep++)
		mix_signed(&digest, sysfs_handle_pointer_valid_result(handlep));
	mix_signed(&digest, sysfs_default_response_ssize_result());
	mix_signed(&digest, sysfs_release_response_error_result());
	for (unsigned int i = 0; i < sizeof(messages) / sizeof(messages[0]); i++)
		mix_signed(&digest, sysfs_request_handler_kind_result(messages[i]));
	for (unsigned long ptr = 0; ptr <= 2; ptr++) {
		mix_signed(&digest, sysfs_pointer_missing_result(ptr));
		mix_signed(&digest, sysfs_should_call_show_result(ptr));
		mix_signed(&digest, sysfs_should_call_store_result(ptr));
		mix_signed(&digest, sysfs_should_call_release_result(ptr));
	}

	mix(&digest, procfs_mem_reason_result(0));
	mix(&digest, procfs_mem_reason_result(1));
	for (unsigned long left = 0; left <= 8192; left += 2048)
		mix_signed(&digest, procfs_mem_chunk_size_result(4095, left));
	mix_signed(&digest, procfs_default_count_result());
	for (unsigned int i = 0; i < sizeof(addrs) / sizeof(addrs[0]); i++) {
		for (unsigned int j = 0; j < sizeof(counts) / sizeof(counts[0]); j++) {
			mix_signed(&digest, procfs_remote_count_result(addrs[i],
				counts[j]));
			mix_signed(&digest, procfs_remote_npages_result(counts[j]));
			mix_signed(&digest, procfs_format_error_result(addrs[i] &
				0xffff, counts[j]));
		}
	}
	for (unsigned int i = 0; i < sizeof(sizes) / sizeof(sizes[0]); i++)
		mix(&digest, procfs_locked_kb_result(sizes[i]));

	for (int count = -8; count <= 24; count += 8) {
		mix_signed(&digest, procfs_pagemap_range_result(16, count, &start, &end));
		mix(&digest, start);
		mix(&digest, end);
	}
	mix_signed(&digest, procfs_pagemap_range_result(3, 8, &start, &end));

	for (unsigned int i = 0; i < sizeof(statuses) / sizeof(statuses[0]); i++) {
		mix_signed(&digest, procfs_status_state_result(statuses[i]));
		mix_signed(&digest, procfs_thread_stat_state_result(statuses[i], 0));
		mix_signed(&digest, procfs_thread_stat_state_result(statuses[i], 1));
	}
	for (unsigned int i = 0; i < sizeof(map_flags) / sizeof(map_flags[0]); i++) {
		mix_signed(&digest, procfs_maps_read_char_result(map_flags[i]));
		mix_signed(&digest, procfs_maps_write_char_result(map_flags[i]));
		mix_signed(&digest, procfs_maps_exec_char_result(map_flags[i]));
		mix_signed(&digest, procfs_maps_private_char_result(map_flags[i]));
		mix_signed(&digest, procfs_maps_path_kind_result(0x1000,
			0x2000, map_flags[i], 0x1000, 0x3000, 0x4000, 0x8000));
		mix_signed(&digest, procfs_maps_path_kind_result(0x3000,
			0x4000, map_flags[i], 0x1000, 0x3000, 0x4000, 0x8000));
		mix_signed(&digest, procfs_maps_path_kind_result(0x5000,
			0x6000, map_flags[i], 0x1000, 0x3000, 0x4000, 0x8000));
	}
	for (unsigned long pos = 0; pos <= 8192; pos += 4096)
		mix(&digest, procfs_pagemap_next_result(pos));
	mix(&digest, procfs_auxv_limit_result());
	for (unsigned long ptr = 0; ptr <= 1; ptr++)
		mix(&digest, procfs_cmdline_limit_result(ptr, 1234));
	for (unsigned int i = 0; i < sizeof(messages) / sizeof(messages[0]); i++)
		mix_signed(&digest, procfs_is_release_result(messages[i]));
	for (int ret = -1; ret <= 2; ret++)
		mix_signed(&digest, procfs_root_matched_result(ret));
	for (int osnum = 0; osnum <= 2; osnum++) {
		for (int req = 0; req <= 2; req++)
			mix_signed(&digest, procfs_osnum_match_result(osnum, req));
	}
	for (unsigned int i = 0; i < sizeof(sizes) / sizeof(sizes[0]); i++)
		mix_signed(&digest, procfs_zero_length_result(sizes[i]));
	for (unsigned int i = 0; i < sizeof(map_flags) / sizeof(map_flags[0]); i++)
		mix(&digest, procfs_locked_size_add_result(1024, 4096,
			8192, map_flags[i]));
	for (int offset = -2; offset <= 8; offset += 5) {
		for (int written = -1; written <= 4; written += 5)
			mix_signed(&digest,
				procfs_bitmask_next_offset_result(offset, written));
	}
	mix_signed(&digest, procfs_pbuf_is_empty_result(~0UL));
	mix_signed(&digest, procfs_pbuf_is_empty_result(0));
	for (unsigned long ptr = 0; ptr <= 2; ptr++) {
		mix_signed(&digest, procfs_backlog_needed_result(ptr));
		mix_signed(&digest, procfs_lock_failed_action_result(ptr));
		mix_signed(&digest, procfs_pointer_present_result(ptr));
	}
	mix_signed(&digest, procfs_lock_retry_result());
	mix_signed(&digest, procfs_entry_kind_result(NULL));
	for (unsigned int i = 0; i < sizeof(procfs_names) / sizeof(procfs_names[0]); i++)
		mix_signed(&digest, procfs_entry_kind_result(procfs_names[i]));
	mix_signed(&digest, ptr_offset(NULL, procfs_comm_basename_result(0)));
	for (unsigned int i = 0; i < sizeof(cmdlines) / sizeof(cmdlines[0]); i++)
		mix_signed(&digest, ptr_offset(cmdlines[i],
			procfs_comm_basename_result((uintptr_t)cmdlines[i])));
	mix(&digest, procfs_comm_name_result((uintptr_t)"exe", 0) ==
		(uintptr_t)"exe");
	mix(&digest, procfs_comm_name_result((uintptr_t)"exe",
		(uintptr_t)"bash") == (uintptr_t)"bash");
	for (int task = 0; task <= 1; task++) {
		mix_signed(&digest, procfs_thread_tid_result(task, 77, 42));
		mix_signed(&digest, procfs_task_missing_terminal_result(task));
	}
	{
		const unsigned long pbufs[] = { 0, ~0UL - 1, ~0UL };

		for (unsigned int p = 0; p < sizeof(pbufs) / sizeof(pbufs[0]); p++) {
		for (unsigned long top = 0; top <= 1; top++)
			mix_signed(&digest,
				procfs_buffer_chain_attach_result(pbufs[p], top));
		}
	}

	for (unsigned int i = 0; i < sizeof(io_rets) / sizeof(io_rets[0]); i++)
		mix_signed(&digest, pager_linux_io_retry_result(io_rets[i]));
	for (long done = -1; done <= 3; done++) {
		mix_signed(&digest, pager_linux_io_first_result(done));
		for (unsigned int i = 0; i < sizeof(io_rets) / sizeof(io_rets[0]); i++) {
			mix_signed(&digest, pager_linux_io_stop_result(io_rets[i]));
			mix_signed(&digest,
				pager_linux_io_advance_result(done, io_rets[i]));
			mix(&digest, pager_linux_io_remaining_result(8192,
				io_rets[i]));
			mix(&digest, pager_linux_io_next_buf_result(0x10000,
				io_rets[i]));
			mix_signed(&digest,
				pager_linux_io_complete_result(done, 4096));
		}
	}
	for (int faulted = 0; faulted <= 2; faulted++)
		mix_signed(&digest, pager_copy_fault_retry_result(faulted));
	for (int ret = -1; ret <= 1; ret++)
		mix_signed(&digest, pager_copy_fault_error_result(ret));

	for (unsigned int i = 0; i < sizeof(sizes) / sizeof(sizes[0]); i++) {
		mix_signed(&digest, pager_copy_size_error_result(sizes[i]));
		mix(&digest, pager_myalloc_next_alloced_result(0, sizes[i]));
		mix_signed(&digest, pager_myalloc_fits_result(0, sizes[i], 8192));
		mix_signed(&digest, pager_myalloc_fits_result(sizes[i], 1, 8192));
	}
	mix_signed(&digest, pager_myalloc_fits_result(~0UL, 1, 4));
	for (unsigned int i = 0; i < sizeof(addrs) / sizeof(addrs[0]); i++)
		mix(&digest, pager_fault_addr_result(addrs[i]));
	for (size_t off = 0; off <= 8192; off += 4096) {
		mix(&digest, pager_read_chunk_size_result(off, off));
		mix(&digest, pager_read_chunk_size_result(off, off + 1));
		mix(&digest, pager_read_chunk_size_result(off, off + 4097));
	}
	for (int tail = -1; tail <= 130; tail += 17)
		mix_signed(&digest, pager_arealist_tail_room_result(tail));
	for (int base = -2; base <= 4; base += 3) {
		for (int add = -1; add <= 3; add += 2)
			mix_signed(&digest,
				pager_arealist_count_add_result(base, add));
	}
	for (unsigned int i = 0; i < sizeof(addrs) / sizeof(addrs[0]); i++) {
		for (unsigned int j = 0; j < sizeof(addrs) / sizeof(addrs[0]); j++) {
			mix_signed(&digest,
				pager_addrpair_size_result(addrs[i], addrs[j]));
			mix_signed(&digest,
				pager_file_pos_result(addrs[i], addrs[j]));
		}
	}
	for (long written = -1; written <= 8192; written += 2049) {
		for (int count = 0; count <= 4; count++)
			mix_signed(&digest,
				pager_arealist_write_result(written, count, 32));
	}
	for (unsigned int i = 0; i < sizeof(addrs) / sizeof(addrs[0]); i++) {
		mix_signed(&digest, pager_mlock_more_result(addrs[i]));
		mix(&digest, pager_mlock_next_start_result(addrs[i]));
	}
	mix_signed(&digest, pager_mlock_more_result(~0UL));
	for (unsigned long from = 0; from <= 1; from++) {
		for (unsigned long tail = 0; tail <= 1; tail++)
			mix_signed(&digest,
				pager_mlock_container_empty_result(from, tail,
					from, tail));
	}
	for (int ccount = 0; ccount <= 3; ccount++) {
		for (int cur_count = 0; cur_count <= 3; cur_count++)
			mix_signed(&digest,
				pager_mlock_needs_next_result(ccount, cur_count));
		mix_signed(&digest, pager_mlock_next_count_result(ccount));
	}
	mix_signed(&digest, pager_mlock_reset_count_result());
	for (unsigned int swap_count = 0; swap_count <= 3; swap_count++) {
		for (unsigned int mlock_count = 0; mlock_count <= 3; mlock_count++)
			mix_signed(&digest,
				pager_pagein_data_pos_result(swap_count,
					mlock_count, 64, 32));
	}
	for (unsigned int i = 0; i < sizeof(addrs) / sizeof(addrs[0]); i++) {
		mix_signed(&digest, pager_pageout_args_result(addrs[i],
			0x2000, 4096, 0x1000, 0x9000));
		mix_signed(&digest, pager_pageout_args_result(0x2000,
			addrs[i], 4096, 0x1000, 0x9000));
	}
	mix_signed(&digest, pager_pageout_args_result(0x2000, 0x3000,
		0x9000, 0x1000, 0x9000));
	for (unsigned int i = 0; i < sizeof(map_flags) / sizeof(map_flags[0]); i++) {
		mix_signed(&digest, pager_skip_anon_range_result(0, 0x5000,
			0x2000, 0x8000, 0x1000, 0x9000, map_flags[i]));
		mix_signed(&digest, pager_skip_anon_range_result(1, 0x5000,
			0x2000, 0x8000, 0x1000, 0x9000, map_flags[i]));
		mix_signed(&digest, pager_range_locked_result(map_flags[i]));
	}
	for (int flag = 0; flag <= 8; flag++)
		mix_signed(&digest, pager_skip_physical_removal_result(flag));
	for (int fd = -2; fd <= 2; fd++)
		mix_signed(&digest, pager_fd_valid_result(fd));
	for (long result = -2; result <= 2; result++) {
		mix_signed(&digest, pager_should_unlink_swap_result(result));
		mix_signed(&digest, pager_io_short_result(result));
	}

	mix_signed(&digest, zeroobj_initial_flags_result());
	mix_signed(&digest, zeroobj_initial_refcnt_result());
	mix_signed(&digest, zeroobj_initial_page_mode_result());
	mix_signed(&digest, zeroobj_initial_page_offset_result());
	for (unsigned int i = 0; i < sizeof(page_offsets) / sizeof(page_offsets[0]); i++) {
		for (int p2 = 0; p2 <= 1; p2++) {
			mix_signed(&digest, zeroobj_get_page_validate_result(
				page_offsets[i], p2, 0));
			mix_signed(&digest, zeroobj_get_page_validate_result(
				page_offsets[i], p2, 1));
		}
	}

	mix_signed(&digest, shmobj_initial_flags_result());
	mix_signed(&digest, shmobj_initial_refcnt_result());
	mix_signed(&digest, shmobj_initial_index_result());
	mix_signed(&digest, shmobj_initial_ds_pgshift_result());
	for (unsigned int i = 0; i < sizeof(flags) / sizeof(flags[0]); i++)
		mix_signed(&digest, shmobj_indexed_flags_result(flags[i]));
	for (unsigned int i = 0; i < sizeof(pgshifts) / sizeof(pgshifts[0]); i++) {
		int pgshift = shmobj_init_pgshift_result(pgshifts[i]);
		size_t pgsize = shmobj_pgsize_result(pgshift);

		mix_signed(&digest, pgshift);
		mix(&digest, pgsize);
		for (unsigned int j = 0; j < sizeof(seg_sizes) / sizeof(seg_sizes[0]); j++)
			mix(&digest, shmobj_real_segsz_result(seg_sizes[j], pgsize));
		for (unsigned int j = 0; j < sizeof(page_offsets) / sizeof(page_offsets[0]); j++)
			mix_signed(&digest, shmobj_page_contains_offset_result(
				page_offsets[j], pgshift, page_offsets[(j + 1) %
				(sizeof(page_offsets) / sizeof(page_offsets[0]))]));
	}
	for (unsigned int i = 1; i < sizeof(pgshifts) / sizeof(pgshifts[0]); i++) {
		mix_signed(&digest, shmobj_destroy_page_npages_result(pgshifts[i]));
		mix(&digest, shmobj_destroy_page_size_result(pgshifts[i]));
	}
	for (int index = 0; index <= 129; index += 31) {
		mix_signed(&digest, shmobj_destroy_index_word_result(index));
		mix(&digest, shmobj_destroy_index_mask_result(index));
	}
	for (size_t locked = 0; locked <= 8192; locked += 4096) {
		mix_signed(&digest, shmlock_user_locked_result(locked));
		mix(&digest, shmlock_user_after_unlock_result(locked, 4096));
		mix_signed(&digest, shmlock_user_should_free_result(locked));
	}
	for (int ruid = -1; ruid <= 2; ruid++) {
		mix_signed(&digest, shmlock_user_match_result(ruid, 1));
		mix_signed(&digest, shmlock_user_match_result(1, ruid));
	}
	for (unsigned long chain = 0; chain <= 1; chain++) {
		for (unsigned long head = 0; head <= 1; head++)
			mix_signed(&digest,
				shmlock_user_is_list_head_result(chain, head));
	}
	for (unsigned long ptr = 0; ptr <= 2; ptr++) {
		mix_signed(&digest, shmobj_has_user_result(ptr));
		mix_signed(&digest, shmobj_need_alloc_page_result(ptr));
		mix_signed(&digest, shmobj_lookup_page_missing_error_result(ptr));
		mix_signed(&digest, shmobj_lookup_should_store_phys_result(ptr));
		mix_signed(&digest, shmobj_pte_missing_result(ptr));
	}
	for (int count = -1; count <= 3; count++) {
		mix_signed(&digest, shmobj_destroy_page_count_invalid_result(count));
		mix_signed(&digest, shmobj_destroy_page_should_free_result(count, 0));
		mix_signed(&digest, shmobj_destroy_page_should_free_result(count, 1));
	}
	for (int index = -2; index <= 2; index++)
		mix_signed(&digest, shmobj_should_free_direct_result(index));
	for (unsigned int i = 0; i < sizeof(flags) / sizeof(flags[0]); i++)
		mix_signed(&digest, shmobj_destroy_missing_flag_result(flags[i]));
	for (unsigned int i = 0; i < sizeof(seg_sizes) / sizeof(seg_sizes[0]); i++) {
		for (unsigned int j = 0; j < sizeof(page_offsets) / sizeof(page_offsets[0]); j++) {
			for (unsigned int k = 0; k < sizeof(p2aligns) / sizeof(p2aligns[0]); k++) {
				mix_signed(&digest, shmobj_get_page_validate_result(
					seg_sizes[i], page_offsets[j], p2aligns[k]));
			}
			mix_signed(&digest, shmobj_lookup_page_validate_result(
				seg_sizes[i], page_offsets[j]));
		}
	}
	for (unsigned int i = 0; i < sizeof(p2aligns) / sizeof(p2aligns[0]); i++) {
		mix_signed(&digest, shmobj_page_npages_result(p2aligns[i]));
		mix_signed(&digest, shmobj_page_pgshift_result(p2aligns[i]));
	}
	mix_signed(&digest, shmobj_new_page_mode_result());
	mix_signed(&digest, shmobj_new_page_count_result());
	mix_signed(&digest, shmobj_new_page_mapped_result());
	for (unsigned int i = 0; i < sizeof(modes) / sizeof(modes[0]); i++)
		mix_signed(&digest,
			shmobj_page_mode_valid_for_new_result(modes[i]));
	for (int has_pt = 0; has_pt <= 1; has_pt++) {
		for (int has_page = 0; has_page <= 1; has_page++) {
			for (int has_vaddr = 0; has_vaddr <= 1; has_vaddr++) {
				mix_signed(&digest, shmobj_update_args_result(
					has_pt, has_page, has_vaddr));
			}
		}
	}
	for (unsigned int i = 1; i < sizeof(pgshifts) / sizeof(pgshifts[0]); i++)
		mix(&digest, shmobj_update_orig_pgsize_result(pgshifts[i]));
	for (unsigned long off = 0; off <= 8192; off += 4096) {
		mix(&digest, shmobj_update_page_phys_result(0x100000, off));
		mix_signed(&digest, shmobj_update_page_offset_result(0x200000, off));
		mix_signed(&digest,
			shmobj_update_has_more_pages_result(off, 8192));
		mix(&digest, shmobj_update_next_page_off_result(off, 4096));
	}

	mix_signed(&digest, hugefileobj_initial_status_result());
	mix_signed(&digest, hugefileobj_initial_refcnt_result());
	for (unsigned long ptr = 0; ptr <= 2; ptr++) {
		mix_signed(&digest, hugefileobj_pointer_present_result(ptr));
		mix_signed(&digest, hugefileobj_pointer_missing_result(ptr));
		mix_signed(&digest, hugefileobj_page_present_result(ptr));
	}
	for (unsigned int i = 1; i < sizeof(pgshifts) / sizeof(pgshifts[0]); i++) {
		int pgshift = pgshifts[i];
		int expected = hugefileobj_expected_p2align_result(pgshift);
		size_t pgsize = hugefileobj_pgsize_result(pgshift);

		mix_signed(&digest, expected);
		mix_signed(&digest, hugefileobj_validate_p2align_result(
			expected, pgshift));
		mix_signed(&digest, hugefileobj_validate_p2align_result(
			expected + 1, pgshift));
		mix(&digest, pgsize);
		mix_signed(&digest, hugefileobj_npages_per_page_result(pgsize));
		for (unsigned int j = 0; j < sizeof(page_offsets) / sizeof(page_offsets[0]); j++)
			mix_signed(&digest, hugefileobj_page_index_result(
				page_offsets[j], pgshift));
		mix_signed(&digest, hugefileobj_create_nr_pages_result(0,
			pgsize, pgshift));
		mix_signed(&digest, hugefileobj_create_nr_pages_result(pgsize,
			pgsize * 3, pgshift));
	}
	for (size_t old = 0; old <= 4; old += 2) {
		for (int needed = 0; needed <= 6; needed += 3) {
			mix_signed(&digest, hugefileobj_needs_grow_result(old,
				needed));
			mix(&digest, hugefileobj_page_array_bytes_result(old));
			mix(&digest, hugefileobj_copy_bytes_result(old));
			mix(&digest, hugefileobj_zero_bytes_result(old,
				old + (size_t)needed));
			mix(&digest, hugefileobj_zero_start_index_result(old));
		}
	}

	printf("object_helpers ok digest=%016lx\n", digest);
	return 0;
}
EOF_OBJECT_HELPERS

cat > "${tmpdir}/plist_equiv.c" <<'EOF_PLIST'
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>

struct list_head {
	struct list_head *next;
	struct list_head *prev;
};

struct plist_head {
	struct list_head prio_list;
	struct list_head node_list;
};

struct plist_node {
	int prio;
	struct plist_head plist;
};

struct item {
	int id;
	struct plist_node node;
};

extern void plist_add(struct plist_node *, struct plist_head *);
extern void plist_del(struct plist_node *, struct plist_head *);

#define container_of(ptr, type, member) \
	((type *)((char *)(ptr) - offsetof(type, member)))
#define item_from_node(ptr) container_of(ptr, struct item, node)
#define plist_from_node(ptr) container_of(ptr, struct plist_node, plist.node_list)
#define plist_from_prio(ptr) container_of(ptr, struct plist_node, plist.prio_list)

static void init_list_head(struct list_head *list)
{
	list->next = list;
	list->prev = list;
}

static void plist_head_init(struct plist_head *head)
{
	init_list_head(&head->prio_list);
	init_list_head(&head->node_list);
}

static void plist_node_init(struct plist_node *node, int prio)
{
	node->prio = prio;
	plist_head_init(&node->plist);
}

static int plist_node_empty(const struct plist_node *node)
{
	return node->plist.node_list.next == &node->plist.node_list;
}

static void require(int condition)
{
	if (!condition)
		exit(12);
}

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

static void check_links(struct list_head *head)
{
	struct list_head *pos = head;
	int count = 0;

	do {
		require(pos->next->prev == pos);
		require(pos->prev->next == pos);
		pos = pos->next;
		require(++count < 64);
	} while (pos != head);
}

static unsigned long digest_state(struct plist_head *head)
{
	unsigned long digest = 0x706c697374UL;
	struct list_head *pos;
	int last_prio = -2147483647 - 1;
	int count = 0;

	check_links(&head->node_list);
	check_links(&head->prio_list);

	for (pos = head->node_list.next; pos != &head->node_list; pos = pos->next) {
		struct plist_node *node = plist_from_node(pos);
		struct item *item = item_from_node(node);

		require(node->prio >= last_prio);
		last_prio = node->prio;
		mix(&digest, ((unsigned long)(unsigned int)node->prio << 32) |
			     (unsigned long)(unsigned int)item->id);
		count++;
	}
	mix(&digest, (unsigned long)count);

	count = 0;
	for (pos = head->prio_list.next; pos != &head->prio_list; pos = pos->next) {
		struct plist_node *node = plist_from_prio(pos);
		struct item *item = item_from_node(node);

		require(!plist_node_empty(node));
		mix(&digest, 0x8000000000000000UL |
			     ((unsigned long)(unsigned int)node->prio << 32) |
			     (unsigned long)(unsigned int)item->id);
		count++;
	}
	mix(&digest, (unsigned long)count << 16);
	return digest;
}

int main(void)
{
	struct plist_head head;
	struct item items[8];
	int prios[] = { 20, 5, 10, 5, 15, 10, 0, 15 };
	unsigned long digest = 0;

	plist_head_init(&head);
	for (int i = 0; i < 8; i++) {
		items[i].id = i;
		plist_node_init(&items[i].node, prios[i]);
	}

	plist_add(&items[0].node, &head);
	plist_add(&items[1].node, &head);
	plist_add(&items[2].node, &head);
	plist_add(&items[3].node, &head);
	plist_add(&items[4].node, &head);
	plist_add(&items[5].node, &head);
	mix(&digest, digest_state(&head));

	plist_del(&items[1].node, &head);
	require(plist_node_empty(&items[1].node));
	mix(&digest, digest_state(&head));

	plist_del(&items[5].node, &head);
	require(plist_node_empty(&items[5].node));
	mix(&digest, digest_state(&head));

	plist_add(&items[6].node, &head);
	mix(&digest, digest_state(&head));

	plist_del(&items[2].node, &head);
	require(plist_node_empty(&items[2].node));
	mix(&digest, digest_state(&head));

	plist_add(&items[7].node, &head);
	mix(&digest, digest_state(&head));

	plist_del(&items[4].node, &head);
	require(plist_node_empty(&items[4].node));
	mix(&digest, digest_state(&head));

	plist_del(&items[6].node, &head);
	plist_del(&items[3].node, &head);
	plist_del(&items[7].node, &head);
	plist_del(&items[0].node, &head);
	require(head.node_list.next == &head.node_list);
	require(head.prio_list.next == &head.prio_list);
	mix(&digest, digest_state(&head));

	printf("plist ok digest=%016lx\n", digest);
	return 0;
}
EOF_PLIST

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

cat > "${tmpdir}/bitmap_parse_equiv.c" <<'EOF_BITMAP_PARSE'
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

extern int __bitmap_parse(const char *, unsigned int, int, unsigned long *, int);
extern int bitmap_parse_user(const char *, unsigned int, unsigned long *, int);
extern int bitmap_parselist(const char *, unsigned long *, int);
extern int bitmap_parselist_user(const char *, unsigned int, unsigned long *, int);

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

static void mix_signed(unsigned long *digest, long value)
{
	mix(digest, (unsigned long)value);
}

static size_t local_len(const char *s)
{
	size_t len = 0;

	while (s[len])
		len++;
	return len;
}

static void reset_words(unsigned long *words, unsigned long seed)
{
	for (unsigned int i = 0; i < 4; i++)
		words[i] = seed ^ (0x0101010101010101UL * i);
}

static void mix_words(unsigned long *digest, const unsigned long *words)
{
	for (unsigned int i = 0; i < 4; i++)
		mix(digest, words[i]);
}

static void run_hex_parse(unsigned long *digest, const char *input,
			  unsigned int len, int nbits, int user)
{
	unsigned long mask[4];
	int ret;

	reset_words(mask, 0xa5a55a5adead0000UL);
	if (user)
		ret = bitmap_parse_user(input, len, mask, nbits);
	else
		ret = __bitmap_parse(input, len, 0, mask, nbits);
	mix_signed(digest, ret);
	mix_signed(digest, nbits);
	mix_signed(digest, user);
	mix_words(digest, mask);
}

static void run_list_parse(unsigned long *digest, const char *input,
			   unsigned int len, int nbits, int user)
{
	unsigned long mask[4];
	int ret;

	reset_words(mask, 0x5a5aa5a512340000UL);
	if (user)
		ret = bitmap_parselist_user(input, len, mask, nbits);
	else
		ret = bitmap_parselist(input, mask, nbits);
	mix_signed(digest, ret);
	mix_signed(digest, nbits);
	mix_signed(digest, user);
	mix_words(digest, mask);
}

int main(void)
{
	const char *hex_inputs[] = {
		"", "0", "00", "1", "f", "deadBEEF", "000000001",
		"00000000,00000001", "1,0", "0,1", "ffffffff,ffffffff",
		"100000000", "1,,5", ",44", ",", " 1", "1 ", "1 2",
		" 0000000f,\n00000001", "0x1", "g", "00000000,00000000,1",
	};
	const char *list_inputs[] = {
		"", "0", "0-3,8,10-12", "1,2\nignored", "1, 2", "1 2",
		"3-1", "999", ",", "5-", "-5", " 4 ", "0,64", "63",
		"31-33", "0-0,2-2,4", "0007", "7,7",
	};
	int nbits[] = { 0, 1, 4, 8, 31, 32, 33, 64, 65, 96, 128 };
	unsigned long digest = 0xb17a95eUL;

	for (unsigned int i = 0; i < sizeof(hex_inputs) / sizeof(hex_inputs[0]); i++) {
		for (unsigned int n = 0; n < sizeof(nbits) / sizeof(nbits[0]); n++) {
			run_hex_parse(&digest, hex_inputs[i],
				      (unsigned int)(local_len(hex_inputs[i]) + 1),
				      nbits[n], 0);
			run_hex_parse(&digest, hex_inputs[i],
				      (unsigned int)local_len(hex_inputs[i]),
				      nbits[n], 0);
			run_hex_parse(&digest, hex_inputs[i],
				      (unsigned int)local_len(hex_inputs[i]),
				      nbits[n], 1);
		}
	}

	for (unsigned int i = 0; i < sizeof(list_inputs) / sizeof(list_inputs[0]); i++) {
		for (unsigned int n = 0; n < sizeof(nbits) / sizeof(nbits[0]); n++) {
			run_list_parse(&digest, list_inputs[i],
				       (unsigned int)(local_len(list_inputs[i]) + 1),
				       nbits[n], 0);
			run_list_parse(&digest, list_inputs[i],
				       (unsigned int)local_len(list_inputs[i]),
				       nbits[n], 1);
		}
	}

	printf("bitmap_parse ok digest=%016lx\n", digest);
	return 0;
}
EOF_BITMAP_PARSE

cat > "${tmpdir}/bitops_equiv.c" <<'EOF_BITOPS'
#include <stdint.h>
#include <stdio.h>

extern unsigned long find_next_bit(const unsigned long *, unsigned long,
				   unsigned long);
extern unsigned long find_next_zero_bit(const unsigned long *, unsigned long,
					unsigned long);
extern unsigned long find_first_bit(const unsigned long *, unsigned long);
extern unsigned long find_first_zero_bit(const unsigned long *, unsigned long);
extern unsigned int __sw_hweight32(unsigned int);
extern unsigned int __sw_hweight16(unsigned int);
extern unsigned int __sw_hweight8(unsigned int);
extern unsigned long __sw_hweight64(uint64_t);

static unsigned long rng_state = 0xfedcba9876543210UL;

static unsigned long rnd(void)
{
	rng_state = rng_state * 2862933555777941757UL + 3037000493UL;
	return rng_state;
}

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

int main(void)
{
	unsigned long words[5];
	unsigned long sizes[] = { 0, 1, 2, 7, 31, 32, 63, 64, 65, 95, 127,
		128, 129, 191, 255, 256, 257, 319 };
	unsigned long offsets[] = { 0, 1, 2, 5, 31, 32, 33, 63, 64, 65, 95,
		127, 128, 129, 191, 255, 256, 300, 320 };
	unsigned long digest = 0x6eed0e9da4d94a4fUL;

	for (unsigned int pattern = 0; pattern < 80; pattern++) {
		for (unsigned int i = 0; i < 5; i++)
			words[i] = rnd();

		if ((pattern & 7) == 0) {
			for (unsigned int i = 0; i < 5; i++)
				words[i] = 0;
		} else if ((pattern & 7) == 1) {
			for (unsigned int i = 0; i < 5; i++)
				words[i] = ~0UL;
		} else if ((pattern & 7) == 2) {
			for (unsigned int i = 0; i < 5; i++)
				words[i] = 1UL << ((pattern + i * 13) & 63);
		}

		for (unsigned int si = 0; si < sizeof(sizes) / sizeof(sizes[0]); si++) {
			unsigned long size = sizes[si];

			mix(&digest, find_first_bit(words, size));
			mix(&digest, find_first_zero_bit(words, size));

			for (unsigned int oi = 0; oi < sizeof(offsets) / sizeof(offsets[0]); oi++) {
				mix(&digest, find_next_bit(words, size, offsets[oi]));
				mix(&digest, find_next_zero_bit(words, size, offsets[oi]));
			}
		}

		for (unsigned int i = 0; i < 5; i++) {
			mix(&digest, __sw_hweight8((unsigned int)words[i]));
			mix(&digest, __sw_hweight16((unsigned int)words[i]));
			mix(&digest, __sw_hweight32((unsigned int)words[i]));
			mix(&digest, __sw_hweight64((uint64_t)words[i]));
		}
	}

	printf("bitops ok digest=%016lx\n", digest);
	return 0;
}
EOF_BITOPS

cat > "${tmpdir}/string_equiv.c" <<'EOF_STRING'
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

extern size_t strlen(const char *);
extern size_t strnlen(const char *, size_t);
extern char *strcpy(char *, const char *);
extern char *strncpy(char *, const char *, size_t);
extern int strcmp(const char *, const char *);
extern int strncmp(const char *, const char *, size_t);
extern char *strchr(const char *, int);
extern char *strrchr(const char *, int);
extern char *strpbrk(const char *, const char *);
extern char *strstr(const char *, const char *);
extern void *memcpy(void *, const void *, size_t);
extern void *memcpy_long(void *, const void *, size_t);
extern int memcmp(const void *, const void *, size_t);

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

static void mix_signed(unsigned long *digest, long value)
{
	mix(digest, (unsigned long)value);
}

static void fill_bytes(unsigned char *dst, size_t len, unsigned char seed)
{
	for (size_t i = 0; i < len; i++)
		dst[i] = (unsigned char)(seed + i * 17);
}

static void mix_bytes(unsigned long *digest, const unsigned char *src, size_t len)
{
	for (size_t i = 0; i < len; i++)
		mix(digest, ((unsigned long)i << 8) | src[i]);
}

static long ptr_offset(const char *base, const char *ptr)
{
	if (!ptr)
		return -1;
	return ptr - base;
}

int main(void)
{
	const char *strings[] = {
		"",
		"a",
		"abcdef",
		"abcabc",
		"prefix-suffix",
	};
	const char high[] = { 'A', (char)0xff, 'B', (char)0x80, '\0' };
	const char embedded[] = { 'a', 'b', 'c', '\0', 't', 'a', 'i', 'l', '\0' };
	unsigned char src[96], dst[96], dst2[96];
	unsigned long lsrc[8], ldst[8];
	unsigned long digest = 0x51f15eada5c0deUL;

	for (size_t i = 0; i < sizeof(strings) / sizeof(strings[0]); i++) {
		mix(&digest, strlen(strings[i]));
		for (size_t max = 0; max < 12; max++)
			mix(&digest, strnlen(strings[i], max));
	}
	mix(&digest, strlen(embedded));
	mix(&digest, strnlen(embedded, sizeof(embedded)));
	mix(&digest, strlen(high));

	for (size_t i = 0; i < sizeof(strings) / sizeof(strings[0]); i++) {
		for (size_t j = 0; j < sizeof(strings) / sizeof(strings[0]); j++) {
			mix_signed(&digest, strcmp(strings[i], strings[j]));
			for (size_t n = 0; n < 10; n++)
				mix_signed(&digest, strncmp(strings[i], strings[j], n));
		}
	}
	mix_signed(&digest, strcmp(high, "A"));
	mix_signed(&digest, strncmp(high, "A", 2));
	mix_signed(&digest, memcmp(high, "A", 2));

	fill_bytes(dst, sizeof(dst), 0xa0);
	if (strcpy((char *)dst, "copy-source") != (char *)dst)
		return 2;
	mix_bytes(&digest, dst, 24);

	fill_bytes(dst, sizeof(dst), 0xb0);
	if (strncpy((char *)dst, "xy", 8) != (char *)dst)
		return 3;
	mix_bytes(&digest, dst, 16);

	fill_bytes(dst, sizeof(dst), 0xc0);
	strncpy((char *)dst, "abcdef", 3);
	mix_bytes(&digest, dst, 12);

	fill_bytes(dst, sizeof(dst), 0xd0);
	strncpy((char *)dst, "", 4);
	mix_bytes(&digest, dst, 12);

	fill_bytes(dst, sizeof(dst), 0xe0);
	strncpy((char *)dst, "unchanged", 0);
	mix_bytes(&digest, dst, 12);

	for (int ch = -2; ch <= 260; ch += 17) {
		mix_signed(&digest, ptr_offset(strings[3], strchr(strings[3], ch)));
		mix_signed(&digest, ptr_offset(strings[3], strrchr(strings[3], ch)));
		mix_signed(&digest, ptr_offset(high, strchr(high, ch)));
		mix_signed(&digest, ptr_offset(high, strrchr(high, ch)));
	}
	mix_signed(&digest, ptr_offset(strings[3], strchr(strings[3], '\0')));
	mix_signed(&digest, ptr_offset(strings[3], strrchr(strings[3], '\0')));
	mix_signed(&digest, ptr_offset(strings[4], strpbrk(strings[4], "xyz-f")));
	mix_signed(&digest, ptr_offset(strings[4], strpbrk(strings[4], "")));
	mix_signed(&digest, ptr_offset("", strpbrk("", "abc")));
	mix_signed(&digest, ptr_offset(strings[3], strstr(strings[3], "abc")));
	mix_signed(&digest, ptr_offset(strings[3], strstr(strings[3], "cab")));
	mix_signed(&digest, ptr_offset(strings[3], strstr(strings[3], "")));
	mix_signed(&digest, ptr_offset("", strstr("", "")));

	fill_bytes(src, sizeof(src), 0x11);
	fill_bytes(dst, sizeof(dst), 0x77);
	if (memcpy(dst + 7, src + 3, 41) != dst + 7)
		return 4;
	mix_bytes(&digest, dst, sizeof(dst));

	for (size_t i = 0; i < sizeof(lsrc) / sizeof(lsrc[0]); i++) {
		lsrc[i] = 0x1122334455667788UL ^ (0x0101010101010101UL * i);
		ldst[i] = 0xfeedfacecafebeefUL;
	}
	if (memcpy_long(ldst + 1, lsrc + 2, sizeof(unsigned long) * 3 + 5) != ldst + 1)
		return 5;
	mix_bytes(&digest, (const unsigned char *)ldst, sizeof(ldst));

	fill_bytes(dst, sizeof(dst), 0x21);
	fill_bytes(dst2, sizeof(dst2), 0x21);
	dst2[0] = 0x22;
	dst2[10] = 0x7f;
	dst2[11] = 0x80;
	for (size_t n = 0; n < 24; n++) {
		mix_signed(&digest, memcmp(dst, dst2, n));
		mix_signed(&digest, memcmp(dst2, dst, n));
	}

	printf("string ok digest=%016lx\n", digest);
	return 0;
}
EOF_STRING

cat > "${tmpdir}/numparse_equiv.c" <<'EOF_NUMPARSE'
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>

extern unsigned long simple_strtoul(const char *, char **, unsigned int);
extern long simple_strtol(const char *, char **, unsigned int);
extern unsigned long long simple_strtoull(const char *, char **, unsigned int);
extern long long simple_strtoll(const char *, char **, unsigned int);
extern int strict_strtoul(const char *, unsigned int, unsigned long *);
extern int strict_strtol(const char *, unsigned int, long *);
extern int strict_strtoull(const char *, unsigned int, unsigned long long *);
extern int strict_strtoll(const char *, unsigned int, long long *);
extern unsigned long strtol(const char *, char **, unsigned int);

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

static void mix_signed(unsigned long *digest, long value)
{
	mix(digest, (unsigned long)value);
}

static long ptr_offset(const char *base, const char *ptr)
{
	if (!ptr)
		return -1;
	return ptr - base;
}

int main(void)
{
	const char *inputs[] = {
		"", "0", "00", "01", "077", "0x", "0x0", "0x10",
		"0XfFz", "123abc", "-123abc", "-0x10", "+17",
		"18446744073709551616", "deadBEEF", "101010", "9", "2",
		"12\n", "12x", " 12", "-\n", "-0", "-9223372036854775808",
	};
	unsigned int bases[] = { 0, 1, 2, 8, 10, 16, 17, 36 };
	unsigned long digest = 0x51a1f1ed12345678UL;

	for (unsigned int i = 0; i < sizeof(inputs) / sizeof(inputs[0]); i++) {
		for (unsigned int b = 0; b < sizeof(bases) / sizeof(bases[0]); b++) {
			char *end = (char *)0x1;
			unsigned long ul = simple_strtoul(inputs[i], &end, bases[b]);
			mix(&digest, ul);
			mix_signed(&digest, ptr_offset(inputs[i], end));

			end = (char *)0x1;
			mix_signed(&digest, simple_strtol(inputs[i], &end, bases[b]));
			mix_signed(&digest, ptr_offset(inputs[i], end));

			end = (char *)0x1;
			mix(&digest, (unsigned long)simple_strtoull(inputs[i], &end, bases[b]));
			mix_signed(&digest, ptr_offset(inputs[i], end));

			end = (char *)0x1;
			mix_signed(&digest, (long)simple_strtoll(inputs[i], &end, bases[b]));
			mix_signed(&digest, ptr_offset(inputs[i], end));

			end = (char *)0x1;
			mix(&digest, strtol(inputs[i], &end, bases[b]));
			mix_signed(&digest, ptr_offset(inputs[i], end));
		}
	}

	for (unsigned int i = 0; i < sizeof(inputs) / sizeof(inputs[0]); i++) {
		unsigned long ul = 0xfeedfacecafebeefUL;
		unsigned long long ull = 0x1122334455667788ULL;
		long sl = 0x12345678L;
		long long sll = 0x123456789abcdefLL;
		int ret;

		ret = strict_strtoul(inputs[i], 0, &ul);
		mix_signed(&digest, ret);
		mix(&digest, ul);
		ret = strict_strtol(inputs[i], 0, &sl);
		mix_signed(&digest, ret);
		mix_signed(&digest, sl);
		ret = strict_strtoull(inputs[i], 0, &ull);
		mix_signed(&digest, ret);
		mix(&digest, (unsigned long)ull);
		ret = strict_strtoll(inputs[i], 0, &sll);
		mix_signed(&digest, ret);
		mix_signed(&digest, (long)sll);

		ret = strict_strtoul(inputs[i], 16, &ul);
		mix_signed(&digest, ret);
		mix(&digest, ul);
		ret = strict_strtol(inputs[i], 10, &sl);
		mix_signed(&digest, ret);
		mix_signed(&digest, sl);
	}

	printf("numparse ok digest=%016lx\n", digest);
	return 0;
}
EOF_NUMPARSE

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
	require(((struct ihk_page_allocator_desc *)desc)->end ==
		pagealloc_init_end_result(ARENA_BASE,
			256 * LOCAL_PAGE_SIZE));
	require(((struct ihk_page_allocator_desc *)desc)->count ==
		(unsigned int)pagealloc_init_count_result(32));
	require(pagealloc_destroy_pages_result(
		((struct ihk_page_allocator_desc *)desc)->flag) == 1);
	mix(&digest, ((struct ihk_page_allocator_desc *)desc)->end);
	mix(&digest, ((struct ihk_page_allocator_desc *)desc)->count);
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

			fill_page_arena(0x66);
			zero_at_free = 1;
			deferred_zero_at_free = 0;
			ihk_numa_free_pages(&numa,
					big_addr + 4 * LOCAL_PAGE_SIZE, 1);
			require(numa.nr_free_pages == 0);
			require(numa.free_chunks.rb_node == NULL);
			require_page_bytes(228, 0, 0x66);
			mix(&digest, numa.nr_free_pages);

			ihk_numa_free_pages(&numa, big_addr, 0);
			require(numa.nr_free_pages == 0);
			require(numa.free_chunks.rb_node == NULL);
			require_page_bytes(224, 0, 0x66);
			mix(&digest, numa.nr_free_pages);
		}
	}

	printf("page_alloc_bitmap ok digest=%016lx\n", digest);
	return 0;
}
EOF_PAGE_ALLOC_BITMAP

cat > "${tmpdir}/process_helpers_equiv.c" <<'EOF_PROCESS_HELPERS'
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define VERIFY_READ 0
#define VERIFY_WRITE 1
#define VR_IO_NOCACHE 0x100UL
#define VR_REMOTE 0x200UL
#define VR_WRITE_COMBINED 0x400UL
#define VR_PRIVATE 0x2000UL
#define VR_PROT_READ 0x00010000UL
#define VR_PROT_WRITE 0x00020000UL
#define VR_PROT_EXEC 0x00040000UL
#define MF_HUGETLBFS 0x100000U
#define PTATTR_ACTIVE 0x01UL
#define PTATTR_WRITABLE 0x02UL
#define PTATTR_USER 0x04UL
#define PTATTR_NO_EXECUTE 0x8000000000000000UL
#define PTATTR_UNCACHABLE 0x10000UL
#define PTATTR_FOR_USER 0x20000UL
#define PTATTR_WRITE_COMBINED 0x40000UL
#define PS_EXITED 0x10
#define PT_TRACE_SYSCALL 0x200
#define PTRACE_RESUME_SIGNAL_SOURCE_SENDSIG 1
#define PTRACE_RESUME_SIGNAL_SOURCE_RECVSIG 2
#define UTI_STATE_RUNNING_IN_LINUX 2
#define UTI_STATE_EPILOGUE 3
#define CLONE_VM 0x00000100
#define CLONE_SIGHAND 0x00000800
#define WNOWAIT 0x01000000
#define SIGNAL_STOP_STOPPED 0x1
#define SIGNAL_STOP_CONTINUED 0x2

extern unsigned long common_vrflag_to_ptattr(unsigned long, unsigned long, void *);
extern int process_split_pgshift_result(int, uintptr_t);
extern int process_add_range_bounds_result(unsigned long, unsigned long,
					   unsigned long, unsigned long);
extern int process_extend_up_result(unsigned long, unsigned long, int,
				    unsigned long, unsigned long);
extern unsigned long process_change_prot_newflag_result(unsigned long,
							unsigned long);
extern void process_attr_delta_result(unsigned long, unsigned long,
				      unsigned long *, unsigned long *);
extern unsigned long process_private_file_setattr_result(int, unsigned long,
							 unsigned int,
							 unsigned long);
extern int process_remove_region_alignment_result(unsigned long, unsigned long);
extern int process_access_initial_result(int, unsigned long, unsigned long);
extern int process_access_adjacent_result(unsigned long, int, unsigned long);
extern int process_access_permission_result(int, unsigned long);
extern int process_ref_release_should_destroy_result(int);
extern int process_release_address_space_should_destroy_result(int);
extern int process_release_address_space_should_run_free_cb_result(unsigned long);
extern int process_create_cpu_allowed_result(int, int);
extern int process_create_use_default_cpu_set_result(int);
extern int process_address_space_pid_detach_result(int *, int, int);
extern int process_clone_shares_vm_result(int);
extern int process_clone_shares_sighand_result(int);
extern int process_mckfd_should_dup_result(unsigned long);
extern int process_clone_copy_vm_thread_state_result(void *, const void *,
						     unsigned long,
						     unsigned long, void *,
						     const void *,
						     unsigned long, size_t);
extern int process_tid_index_for_thread_result(const void *, int,
					       unsigned long, unsigned long,
					       unsigned long);
extern int process_tid_index_found_result(int);
extern int process_tid_release_slot_result(void *, int, unsigned long,
					   unsigned long);
extern int process_tid_replace_slot_result(void *, int, unsigned long,
					   unsigned long, unsigned long, int);
extern int process_sigpending_cleanup_needed_result(int);
extern void *process_sigpending_pop_front_result(void *, unsigned long);
extern int process_list_is_linked_result(const void *);
extern void process_list_detach_result(void *);
extern int process_list_detach_counted_result(void *, size_t *);
extern void process_list_add_tail_result(void *, void *);
extern int process_list_add_tail_counted_result(void *, void *,
					       size_t *);
extern int process_list_move_tail_result(void *, void *);
extern int process_list_del_init_result(void *);
extern int process_child_reparent_result(void *, unsigned long, unsigned long,
					 void *, void *, void *, int);
extern int process_thread_report_attach_result(void *, unsigned long, int, int,
					       unsigned long, void *, void *,
					       void *);
extern int process_thread_report_detach_result(void *, unsigned long, void *,
					       void *);
extern int process_ptrace_main_detach_reparent_result(void *, unsigned long,
						      void *, void *, void *,
						      void *);
extern int process_ptrace_main_attach_reparent_result(void *, unsigned long,
						      void *, void *, void *);
extern int process_thread_termsig_clear_result(void *, unsigned long, int);
extern void *process_thread_ptrace_cleanup_result(void *, unsigned long,
						  unsigned long,
						  unsigned long);
extern int process_thread_ptrace_saved_context_clear_result(void *,
							    unsigned long);
extern int process_thread_ptrace_trace_syscall_update_result(void *,
							     unsigned long,
							     int);
extern void *process_thread_ptrace_pending_signal_take_result(void *,
							     unsigned long,
							     unsigned long,
							     int);
extern int process_thread_signal_flags_reap_result(void *, unsigned long, int,
						   int);
extern int process_wait_exit_status_reap_result(void *, unsigned long, int);
extern int process_optional_ptr_should_free_result(unsigned long);
extern int process_hold_thread_warn_exited_result(int);
extern int process_sigcommon_release_should_destroy_result(int);
extern int process_destroy_thread_tid_action_result(int, int, int);
extern int process_thread_should_free_pages_result(int);
extern int process_release_vm_should_run_free_cb_result(unsigned long);
extern int process_release_mckfd_should_close_result(unsigned long);
extern int process_mckfd_push_head_result(void *, void *);
extern void *process_mckfd_pop_head_result(void *);

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

struct fake_tid {
	int tid;
	void *thread;
};

struct fake_vm_state {
	unsigned long pad;
	void *vdso_addr;
	void *vvar_addr;
};

struct fake_sigstack {
	void *ss_sp;
	int ss_flags;
	unsigned long ss_size;
};

struct fake_thread_state {
	int pad;
	struct fake_sigstack sigstack;
};

struct fake_list_head {
	struct fake_list_head *next;
	struct fake_list_head *prev;
};

struct fake_pending {
	struct fake_list_head list;
	unsigned long value;
};

struct fake_process {
	void *ppid_parent;
	void *parent;
	struct fake_list_head siblings;
	struct fake_list_head ptraced_siblings;
	int group_exit_status;
	unsigned long value;
};

struct fake_thread {
	int termsig;
	int exit_status;
	void *report_proc;
	struct fake_list_head report_siblings;
	int ptrace;
	int ptrace_saved_uctx_valid;
	void *ptrace_debugreg;
	void *ptrace_sendsig;
	void *ptrace_recvsig;
	int signal_flags;
	unsigned long value;
};

struct fake_mckfd {
	struct fake_mckfd *next;
	int fd;
};

static void fake_list_init(struct fake_list_head *head)
{
	head->next = head;
	head->prev = head;
}

static void fake_list_add_tail(struct fake_list_head *entry,
			       struct fake_list_head *head)
{
	entry->next = head;
	entry->prev = head->prev;
	head->prev->next = entry;
	head->prev = entry;
}

int main(void)
{
	unsigned long digest = 0x50524f4348454c50UL;
	unsigned long clr = 0, set = 0;
	struct fake_tid tids[3] = {
		{ 10, (void *)0x1000 },
		{ 11, (void *)0x2000 },
		{ 12, (void *)0x3000 },
	};
	struct fake_list_head pending_head;
	struct fake_list_head other_head;
	struct fake_list_head old_children;
	struct fake_list_head new_children;
	struct fake_list_head new_ptraced;
	struct fake_pending pending_a = { { 0 }, 0xa1 };
	struct fake_pending pending_b = { { 0 }, 0xb2 };
	struct fake_pending *pending;
	struct fake_process old_parent = { 0 };
	struct fake_process pid1 = { 0 };
	struct fake_process child_a = { 0 };
	struct fake_process child_b = { 0 };
	struct fake_thread report_thread_a = { 0 };
	struct fake_thread report_thread_b = { 0 };
	struct fake_vm_state src_vm = { 0, (void *)0x700000, (void *)0x710000 };
	struct fake_vm_state dst_vm = { 0 };
	struct fake_thread_state src_thread = {
		0, { (void *)0x720000, 0x33, 0x4400 }
	};
	struct fake_thread_state dst_thread = { 0 };
	size_t runq_len = 0;
	struct fake_mckfd fd_a = { 0, 3 };
	struct fake_mckfd fd_b = { 0, 4 };
	struct fake_mckfd *fd_head = &fd_a;
	struct fake_mckfd *fd;
	int pids[] = { 10, 20, 30, 20 };
	unsigned long flags[] = {
		0,
		VR_PROT_READ,
		VR_PROT_WRITE,
		VR_PROT_READ | VR_PROT_WRITE,
		VR_PROT_READ | VR_PROT_EXEC,
		VR_IO_NOCACHE | VR_PROT_READ,
		VR_REMOTE | VR_PROT_WRITE,
		VR_WRITE_COMBINED | VR_PROT_READ | VR_PROT_EXEC,
	};

	for (unsigned int i = 0; i < sizeof(flags) / sizeof(flags[0]); i++)
		mix(&digest, common_vrflag_to_ptattr(flags[i], 0, 0));

	mix(&digest, process_split_pgshift_result(21, 0x200000));
	mix(&digest, process_split_pgshift_result(21, 0x201000));
	mix(&digest, process_split_pgshift_result(0, 0x1234));
	mix(&digest, process_add_range_bounds_result(0x1000, 0x9000, 0x1000, 0x9000));
	mix(&digest, process_add_range_bounds_result(0x1000, 0x9000, 0, 0x8000));
	mix(&digest, process_add_range_bounds_result(0x1000, 0x9000, 0x2000, 0xa000));
	mix(&digest, process_extend_up_result(0x4000, 0x9000, 0, 0, 0x5000));
	mix(&digest, process_extend_up_result(0x4000, 0x9000, 0, 0, 0x4000));
	mix(&digest, process_extend_up_result(0x4000, 0x9000, 0, 0, 0xa000));
	mix(&digest, process_extend_up_result(0x4000, 0x9000, 1, 0x4800, 0x5000));
	mix(&digest, process_change_prot_newflag_result(0x12340000UL | VR_PRIVATE,
							VR_PROT_READ | VR_PROT_WRITE));
	process_attr_delta_result(PTATTR_USER | PTATTR_ACTIVE,
				  PTATTR_USER | PTATTR_WRITABLE, &clr, &set);
	mix(&digest, clr);
	mix(&digest, set);
	mix(&digest, process_private_file_setattr_result(1, VR_PRIVATE, 0,
							 PTATTR_WRITABLE | PTATTR_ACTIVE));
	mix(&digest, process_private_file_setattr_result(1, VR_PRIVATE,
							 MF_HUGETLBFS,
							 PTATTR_WRITABLE | PTATTR_ACTIVE));
	mix(&digest, process_remove_region_alignment_result(0x1000, 0x2000));
	mix(&digest, process_remove_region_alignment_result(0x1001, 0x2000));
	mix(&digest, process_access_initial_result(1, 0x1000, 0x1000));
	mix(&digest, process_access_initial_result(0, 0, 0x1000));
	mix(&digest, process_access_initial_result(1, 0x2000, 0x1000));
	mix(&digest, process_access_adjacent_result(0x2000, 1, 0x2000));
	mix(&digest, process_access_adjacent_result(0x2000, 0, 0));
	mix(&digest, process_access_adjacent_result(0x2000, 1, 0x3000));
	mix(&digest, process_access_permission_result(VERIFY_READ, VR_PROT_READ));
	mix(&digest, process_access_permission_result(VERIFY_READ, VR_PROT_WRITE));
	mix(&digest, process_access_permission_result(VERIFY_WRITE, VR_PROT_WRITE));
	mix(&digest, process_access_permission_result(VERIFY_WRITE, VR_PROT_READ));
	mix(&digest, process_access_permission_result(99, 0));
	mix(&digest, process_ref_release_should_destroy_result(0));
	mix(&digest, process_ref_release_should_destroy_result(1));
	mix(&digest, process_release_address_space_should_destroy_result(0));
	mix(&digest, process_release_address_space_should_destroy_result(1));
	mix(&digest, process_release_address_space_should_run_free_cb_result(0));
	mix(&digest, process_release_address_space_should_run_free_cb_result(0x4000));
	mix(&digest, process_create_cpu_allowed_result(0, 4));
	mix(&digest, process_create_cpu_allowed_result(4, 4));
	mix(&digest, process_create_cpu_allowed_result(-1, 4));
	mix(&digest, process_create_use_default_cpu_set_result(0));
	mix(&digest, process_create_use_default_cpu_set_result(1));
	mix(&digest, process_address_space_pid_detach_result(pids, 4, 20));
	mix(&digest, pids[1] == 0);
	mix(&digest, pids[3] == 20);
	mix(&digest, process_address_space_pid_detach_result(pids, 4, 99));
	mix(&digest, process_address_space_pid_detach_result(NULL, 4, 20));
	mix(&digest, process_address_space_pid_detach_result(pids, 0, 20));
	mix(&digest, process_clone_shares_vm_result(CLONE_VM));
	mix(&digest, process_clone_shares_vm_result(0));
	mix(&digest, process_clone_shares_sighand_result(CLONE_SIGHAND));
	mix(&digest, process_clone_shares_sighand_result(CLONE_VM));
	mix(&digest, process_mckfd_should_dup_result(0));
	mix(&digest, process_mckfd_should_dup_result(0x5000));
	mix(&digest, process_clone_copy_vm_thread_state_result(&dst_vm,
		&src_vm, offsetof(struct fake_vm_state, vdso_addr),
		offsetof(struct fake_vm_state, vvar_addr), &dst_thread,
		&src_thread, offsetof(struct fake_thread_state, sigstack),
		sizeof(src_thread.sigstack)));
	mix(&digest, dst_vm.vdso_addr == src_vm.vdso_addr);
	mix(&digest, dst_vm.vvar_addr == src_vm.vvar_addr);
	mix(&digest, dst_thread.sigstack.ss_sp == src_thread.sigstack.ss_sp);
	mix(&digest, dst_thread.sigstack.ss_flags ==
		src_thread.sigstack.ss_flags);
	mix(&digest, dst_thread.sigstack.ss_size ==
		src_thread.sigstack.ss_size);
	mix(&digest, process_clone_copy_vm_thread_state_result(NULL,
		&src_vm, offsetof(struct fake_vm_state, vdso_addr),
		offsetof(struct fake_vm_state, vvar_addr), &dst_thread,
		&src_thread, offsetof(struct fake_thread_state, sigstack),
		sizeof(src_thread.sigstack)));
	mix(&digest, process_tid_index_for_thread_result(tids, 3,
							 sizeof(tids[0]),
							 offsetof(struct fake_tid,
								  thread),
							 0x2000));
	mix(&digest, process_tid_index_for_thread_result(tids, 3,
							 sizeof(tids[0]),
							 offsetof(struct fake_tid,
								  thread),
							 0x9000));
	mix(&digest, process_tid_index_for_thread_result(NULL, 3,
							 sizeof(tids[0]),
							 offsetof(struct fake_tid,
								  thread),
							 0x2000));
	mix(&digest, process_tid_index_found_result(1));
	mix(&digest, process_tid_index_found_result(-1));
	mix(&digest, process_tid_release_slot_result(tids, 1,
						     sizeof(tids[0]),
						     offsetof(struct fake_tid,
							      thread)));
	mix(&digest, tids[1].thread == NULL);
	mix(&digest, process_tid_replace_slot_result(tids, 2,
						     sizeof(tids[0]),
						     offsetof(struct fake_tid,
							      tid),
						     offsetof(struct fake_tid,
							      thread),
						     99));
	mix(&digest, tids[2].tid);
	mix(&digest, tids[2].thread == NULL);
	mix(&digest, process_tid_release_slot_result(tids, -1,
						     sizeof(tids[0]),
						     offsetof(struct fake_tid,
							      thread)));
	mix(&digest, process_sigpending_cleanup_needed_result(0));
	mix(&digest, process_sigpending_cleanup_needed_result(1));
	fake_list_init(&pending_head);
	process_list_add_tail_result(&pending_a.list, &pending_head);
	process_list_add_tail_result(&pending_b.list, &pending_head);
	process_list_add_tail_result(NULL, &pending_head);
	process_list_add_tail_result(&pending_b.list, NULL);
	mix(&digest, pending_head.next == &pending_a.list);
	mix(&digest, pending_head.prev == &pending_b.list);
	mix(&digest, pending_a.list.prev == &pending_head);
	mix(&digest, pending_b.list.next == &pending_head);
	pending = process_sigpending_pop_front_result(
		&pending_head, offsetof(struct fake_pending, list));
	mix(&digest, pending == &pending_a);
	mix(&digest, pending_head.next == &pending_b.list);
	mix(&digest, pending_a.list.next == (void *)0x00100129);
	mix(&digest, process_list_is_linked_result(&pending_b.list));
	process_list_detach_result(&pending_b.list);
	mix(&digest, process_list_is_linked_result(&pending_b.list));
	mix(&digest, pending_head.next == &pending_head);
	process_list_add_tail_result(&pending_b.list, &pending_head);
	pending = process_sigpending_pop_front_result(
		&pending_head, offsetof(struct fake_pending, list));
	mix(&digest, pending == &pending_b);
	mix(&digest, pending_head.next == &pending_head);
	mix(&digest, process_sigpending_pop_front_result(
		&pending_head, offsetof(struct fake_pending, list)) == NULL);
	mix(&digest, process_list_is_linked_result(&pending_head));
	process_list_detach_result(NULL);
	process_list_detach_result(&pending_head);
	mix(&digest, pending_head.next == &pending_head);
	fake_list_init(&pending_head);
	mix(&digest, process_list_add_tail_counted_result(&pending_a.list,
							  &pending_head,
							  &runq_len));
	mix(&digest, runq_len);
	mix(&digest, process_list_add_tail_counted_result(&pending_b.list,
							  &pending_head,
							  &runq_len));
	mix(&digest, runq_len);
	mix(&digest, process_list_detach_counted_result(&pending_a.list,
							&runq_len));
	mix(&digest, runq_len);
	mix(&digest, pending_head.next == &pending_b.list);
	mix(&digest, process_list_detach_counted_result(NULL, &runq_len));
	mix(&digest, process_list_add_tail_counted_result(&pending_a.list,
							  NULL, &runq_len));
	mix(&digest, runq_len);
	fake_list_init(&other_head);
	mix(&digest, process_list_move_tail_result(&pending_b.list,
						   &other_head));
	mix(&digest, pending_head.next == &pending_head);
	mix(&digest, other_head.next == &pending_b.list);
	mix(&digest, pending_b.list.prev == &other_head);
	mix(&digest, process_list_move_tail_result(NULL, &pending_head));
	mix(&digest, process_list_move_tail_result(&pending_a.list, NULL));
	mix(&digest, process_list_del_init_result(&pending_b.list));
	mix(&digest, other_head.next == &other_head);
	mix(&digest, pending_b.list.next == &pending_b.list);
	mix(&digest, process_list_del_init_result(NULL));
	fake_list_init(&old_children);
	fake_list_init(&new_children);
	fake_list_init(&new_ptraced);
	fake_list_init(&child_a.siblings);
	fake_list_init(&child_a.ptraced_siblings);
	fake_list_init(&child_b.siblings);
	fake_list_init(&child_b.ptraced_siblings);
	child_a.ppid_parent = &old_parent;
	child_a.parent = &old_parent;
	child_b.ppid_parent = &old_parent;
	child_b.parent = &old_parent;
	fake_list_add_tail(&child_a.siblings, &old_children);
	fake_list_add_tail(&child_b.ptraced_siblings, &old_children);
	mix(&digest, process_child_reparent_result(&child_a,
		offsetof(struct fake_process, ppid_parent),
		offsetof(struct fake_process, parent), &pid1,
		&child_a.siblings, &new_children, 1));
	mix(&digest, child_a.ppid_parent == &pid1);
	mix(&digest, child_a.parent == &pid1);
	mix(&digest, new_children.next == &child_a.siblings);
	mix(&digest, process_child_reparent_result(&child_b,
		offsetof(struct fake_process, ppid_parent),
		offsetof(struct fake_process, parent), &pid1,
		&child_b.ptraced_siblings, &new_ptraced, 0));
	mix(&digest, child_b.ppid_parent == &pid1);
	mix(&digest, child_b.parent == &old_parent);
	mix(&digest, new_ptraced.next == &child_b.ptraced_siblings);
	mix(&digest, process_child_reparent_result(NULL,
		offsetof(struct fake_process, ppid_parent),
		offsetof(struct fake_process, parent), &pid1,
		&child_b.ptraced_siblings, &new_ptraced, 0));
	fake_list_init(&other_head);
	fake_list_init(&report_thread_a.report_siblings);
	fake_list_init(&report_thread_b.report_siblings);
	mix(&digest, process_thread_report_attach_result(&report_thread_a,
		offsetof(struct fake_thread, termsig), 1, 9,
		offsetof(struct fake_thread, report_proc), &pid1,
		&report_thread_a.report_siblings, &other_head));
	mix(&digest, report_thread_a.termsig == 9);
	mix(&digest, report_thread_a.report_proc == &pid1);
	mix(&digest, other_head.next == &report_thread_a.report_siblings);
	mix(&digest, process_thread_report_attach_result(&report_thread_b,
		offsetof(struct fake_thread, termsig), 0, 15,
		offsetof(struct fake_thread, report_proc), &old_parent,
		&report_thread_b.report_siblings, &other_head));
	mix(&digest, report_thread_b.termsig == 0);
	mix(&digest, report_thread_b.report_proc == &old_parent);
	mix(&digest, other_head.prev == &report_thread_b.report_siblings);
	mix(&digest, process_thread_report_detach_result(&report_thread_a,
		offsetof(struct fake_thread, report_proc), NULL,
		&report_thread_a.report_siblings));
	mix(&digest, report_thread_a.report_proc == NULL);
	mix(&digest, other_head.next == &report_thread_b.report_siblings);
	mix(&digest, process_thread_report_detach_result(&report_thread_b,
		offsetof(struct fake_thread, report_proc), &pid1,
		&report_thread_b.report_siblings));
	mix(&digest, report_thread_b.report_proc == &pid1);
	mix(&digest, other_head.next == &other_head);
	fake_list_init(&old_children);
	fake_list_init(&new_children);
	fake_list_init(&child_a.siblings);
	fake_list_init(&child_a.ptraced_siblings);
	child_a.parent = &old_parent;
	fake_list_add_tail(&child_a.ptraced_siblings, &old_children);
	mix(&digest, process_ptrace_main_detach_reparent_result(&child_a,
		offsetof(struct fake_process, parent), &pid1,
		&child_a.ptraced_siblings, &child_a.siblings, &new_children));
	mix(&digest, child_a.parent == &pid1);
	mix(&digest, old_children.next == &old_children);
	mix(&digest, new_children.next == &child_a.siblings);
	mix(&digest, process_ptrace_main_detach_reparent_result(NULL,
		offsetof(struct fake_process, parent), &pid1,
		&child_a.ptraced_siblings, &child_a.siblings, &new_children));
	fake_list_init(&new_children);
	fake_list_init(&child_b.siblings);
	child_b.parent = &old_parent;
	mix(&digest, process_ptrace_main_attach_reparent_result(&child_b,
		offsetof(struct fake_process, parent), &pid1,
		&child_b.siblings, &new_children));
	mix(&digest, child_b.parent == &pid1);
	mix(&digest, new_children.next == &child_b.siblings);
	mix(&digest, process_ptrace_main_attach_reparent_result(NULL,
		offsetof(struct fake_process, parent), &pid1,
		&child_b.siblings, &new_children));
	report_thread_b.termsig = 12;
	mix(&digest, process_thread_termsig_clear_result(&report_thread_b,
		offsetof(struct fake_thread, termsig), 0));
	mix(&digest, report_thread_b.termsig == 12);
	mix(&digest, process_thread_termsig_clear_result(&report_thread_b,
		offsetof(struct fake_thread, termsig), 1));
	mix(&digest, report_thread_b.termsig == 0);
	mix(&digest, process_thread_termsig_clear_result(NULL,
		offsetof(struct fake_thread, termsig), 1));
	report_thread_b.ptrace = 0x123;
	report_thread_b.ptrace_saved_uctx_valid = 1;
	report_thread_b.ptrace_debugreg = (void *)0xabc0;
	mix(&digest, process_thread_ptrace_cleanup_result(&report_thread_b,
		offsetof(struct fake_thread, ptrace),
		offsetof(struct fake_thread, ptrace_saved_uctx_valid),
		offsetof(struct fake_thread, ptrace_debugreg)) ==
		(void *)0xabc0);
	mix(&digest, report_thread_b.ptrace == 0);
	mix(&digest, report_thread_b.ptrace_saved_uctx_valid == 0);
	mix(&digest, report_thread_b.ptrace_debugreg == NULL);
	mix(&digest, process_thread_ptrace_cleanup_result(NULL,
		offsetof(struct fake_thread, ptrace),
		offsetof(struct fake_thread, ptrace_saved_uctx_valid),
		offsetof(struct fake_thread, ptrace_debugreg)) == NULL);
	report_thread_b.ptrace_saved_uctx_valid = 1;
	mix(&digest, process_thread_ptrace_saved_context_clear_result(
		&report_thread_b,
		offsetof(struct fake_thread, ptrace_saved_uctx_valid)));
	mix(&digest, report_thread_b.ptrace_saved_uctx_valid == 0);
	mix(&digest, process_thread_ptrace_saved_context_clear_result(NULL,
		offsetof(struct fake_thread, ptrace_saved_uctx_valid)));
	report_thread_b.ptrace = 0x77 | PT_TRACE_SYSCALL;
	mix(&digest, process_thread_ptrace_trace_syscall_update_result(
		&report_thread_b, offsetof(struct fake_thread, ptrace), 0));
	mix(&digest, (report_thread_b.ptrace & PT_TRACE_SYSCALL) == 0);
	mix(&digest, process_thread_ptrace_trace_syscall_update_result(
		&report_thread_b, offsetof(struct fake_thread, ptrace), 1));
	mix(&digest, (report_thread_b.ptrace & PT_TRACE_SYSCALL) != 0);
	mix(&digest, process_thread_ptrace_trace_syscall_update_result(NULL,
		offsetof(struct fake_thread, ptrace), 1));
	report_thread_b.ptrace_sendsig = (void *)0x5010;
	report_thread_b.ptrace_recvsig = (void *)0x6010;
	mix(&digest, process_thread_ptrace_pending_signal_take_result(
		&report_thread_b, offsetof(struct fake_thread, ptrace_sendsig),
		offsetof(struct fake_thread, ptrace_recvsig),
		PTRACE_RESUME_SIGNAL_SOURCE_SENDSIG) == (void *)0x5010);
	mix(&digest, report_thread_b.ptrace_sendsig == NULL);
	mix(&digest, report_thread_b.ptrace_recvsig == (void *)0x6010);
	mix(&digest, process_thread_ptrace_pending_signal_take_result(
		&report_thread_b, offsetof(struct fake_thread, ptrace_sendsig),
		offsetof(struct fake_thread, ptrace_recvsig),
		PTRACE_RESUME_SIGNAL_SOURCE_RECVSIG) == (void *)0x6010);
	mix(&digest, report_thread_b.ptrace_recvsig == NULL);
	mix(&digest, process_thread_ptrace_pending_signal_take_result(
		&report_thread_b, offsetof(struct fake_thread, ptrace_sendsig),
		offsetof(struct fake_thread, ptrace_recvsig), 0) == NULL);
	mix(&digest, process_thread_ptrace_pending_signal_take_result(NULL,
		offsetof(struct fake_thread, ptrace_sendsig),
		offsetof(struct fake_thread, ptrace_recvsig),
		PTRACE_RESUME_SIGNAL_SOURCE_SENDSIG) == NULL);
	report_thread_b.signal_flags =
		SIGNAL_STOP_STOPPED | SIGNAL_STOP_CONTINUED;
	mix(&digest, process_thread_signal_flags_reap_result(&report_thread_b,
		offsetof(struct fake_thread, signal_flags), 0,
		SIGNAL_STOP_STOPPED));
	mix(&digest, report_thread_b.signal_flags == SIGNAL_STOP_CONTINUED);
	mix(&digest, process_thread_signal_flags_reap_result(&report_thread_b,
		offsetof(struct fake_thread, signal_flags), WNOWAIT,
		SIGNAL_STOP_CONTINUED));
	mix(&digest, report_thread_b.signal_flags == SIGNAL_STOP_CONTINUED);
	mix(&digest, process_thread_signal_flags_reap_result(NULL,
		offsetof(struct fake_thread, signal_flags), 0,
		SIGNAL_STOP_CONTINUED));
	report_thread_b.exit_status = 0x7f;
	mix(&digest, process_wait_exit_status_reap_result(&report_thread_b,
		offsetof(struct fake_thread, exit_status), WNOWAIT));
	mix(&digest, report_thread_b.exit_status == 0x7f);
	mix(&digest, process_wait_exit_status_reap_result(&report_thread_b,
		offsetof(struct fake_thread, exit_status), 0));
	mix(&digest, report_thread_b.exit_status == 0);
	child_a.group_exit_status = 0x55;
	mix(&digest, process_wait_exit_status_reap_result(&child_a,
		offsetof(struct fake_process, group_exit_status), 0));
	mix(&digest, child_a.group_exit_status == 0);
	mix(&digest, process_wait_exit_status_reap_result(NULL,
		offsetof(struct fake_thread, exit_status), 0));
	mix(&digest, process_thread_report_attach_result(NULL,
		offsetof(struct fake_thread, termsig), 1, 9,
		offsetof(struct fake_thread, report_proc), &pid1,
		&report_thread_b.report_siblings, &other_head));
	mix(&digest, process_optional_ptr_should_free_result(0));
	mix(&digest, process_optional_ptr_should_free_result(0x6000));
	mix(&digest, process_hold_thread_warn_exited_result(PS_EXITED));
	mix(&digest, process_hold_thread_warn_exited_result(0));
	mix(&digest, process_sigcommon_release_should_destroy_result(0));
	mix(&digest, process_sigcommon_release_should_destroy_result(1));
	mix(&digest, process_destroy_thread_tid_action_result(0, 0,
							     UTI_STATE_RUNNING_IN_LINUX));
	mix(&digest, process_destroy_thread_tid_action_result(1, 0,
							     UTI_STATE_RUNNING_IN_LINUX));
	mix(&digest, process_destroy_thread_tid_action_result(1, 1,
							     UTI_STATE_RUNNING_IN_LINUX));
	mix(&digest, process_destroy_thread_tid_action_result(1, 0,
							     UTI_STATE_EPILOGUE));
	mix(&digest, process_thread_should_free_pages_result(0));
	mix(&digest, process_thread_should_free_pages_result(1));
	mix(&digest, process_release_vm_should_run_free_cb_result(0));
	mix(&digest, process_release_vm_should_run_free_cb_result(0x1000));
	mix(&digest, process_release_mckfd_should_close_result(0));
	mix(&digest, process_release_mckfd_should_close_result(0x2000));
	fd_head = NULL;
	fd_a.next = NULL;
	fd_b.next = NULL;
	mix(&digest, process_mckfd_push_head_result(&fd_head, &fd_a));
	mix(&digest, fd_head == &fd_a);
	mix(&digest, fd_a.next == NULL);
	mix(&digest, process_mckfd_push_head_result(&fd_head, &fd_b));
	mix(&digest, fd_head == &fd_b);
	mix(&digest, fd_b.next == &fd_a);
	mix(&digest, process_mckfd_push_head_result(NULL, &fd_a));
	mix(&digest, process_mckfd_push_head_result(&fd_head, NULL));
	fd = process_mckfd_pop_head_result(&fd_head);
	mix(&digest, fd == &fd_b);
	mix(&digest, fd_head == &fd_a);
	mix(&digest, fd_b.next == NULL);
	fd = process_mckfd_pop_head_result(&fd_head);
	mix(&digest, fd == &fd_a);
	mix(&digest, fd_head == NULL);
	mix(&digest, process_mckfd_pop_head_result(&fd_head) == NULL);

	printf("process_helpers ok digest=%016lx\n", digest);
	return 0;
}
EOF_PROCESS_HELPERS

cat > "${tmpdir}/x86_memory_helpers_equiv.c" <<'EOF_X86_MEMORY_HELPERS'
#include <stdio.h>
#include <stddef.h>

#define PTATTR_ACTIVE 0x01UL
#define PTATTR_WRITABLE 0x02UL
#define PTATTR_USER 0x04UL
#define PTATTR_LARGEPAGE 0x80UL
#define PTATTR_FILEOFF (1UL << 11)
#define PTATTR_NO_EXECUTE 0x8000000000000000UL
#define PTATTR_UNCACHABLE 0x10000UL
#define PTATTR_FOR_USER 0x20000UL
#define PTATTR_WRITE_COMBINED 0x40000UL

extern unsigned long x86_attr_to_l3attr_result(unsigned long, unsigned long);
extern unsigned long x86_attr_to_l2attr_result(unsigned long, unsigned long);
extern unsigned long x86_attr_to_l1attr_result(unsigned long, unsigned long);
extern unsigned long x86_set_pte_value_result(unsigned long, unsigned long,
					      unsigned long);
extern int x86_pt_set_pte_value_result(size_t, unsigned long, unsigned long,
				       unsigned long, int, unsigned long *);
extern int x86_smaller_page_size_result(size_t, int, size_t *, int *);
extern unsigned long x86_early_alloc_align_end_result(unsigned long);
extern int x86_early_alloc_exhausted_result(unsigned long, unsigned long);
extern unsigned long x86_early_alloc_next_result(unsigned long, int);

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

int main(void)
{
	unsigned long digest = 0x5838364d454d484cUL;
	unsigned long attr_mask = PTATTR_FILEOFF | PTATTR_WRITABLE |
		PTATTR_USER | PTATTR_ACTIVE | PTATTR_NO_EXECUTE;
	unsigned long attrs[] = {
		0,
		PTATTR_ACTIVE | PTATTR_USER,
		PTATTR_ACTIVE | PTATTR_WRITABLE | PTATTR_USER,
		PTATTR_ACTIVE | PTATTR_USER | PTATTR_LARGEPAGE,
		PTATTR_ACTIVE | PTATTR_USER | PTATTR_LARGEPAGE |
			PTATTR_UNCACHABLE,
		PTATTR_ACTIVE | PTATTR_USER | PTATTR_UNCACHABLE,
		PTATTR_ACTIVE | PTATTR_USER | PTATTR_WRITE_COMBINED,
		PTATTR_ACTIVE | PTATTR_USER | PTATTR_WRITE_COMBINED |
			PTATTR_UNCACHABLE,
		PTATTR_ACTIVE | PTATTR_USER | PTATTR_NO_EXECUTE,
		PTATTR_FILEOFF | PTATTR_LARGEPAGE,
	};

	for (unsigned int i = 0; i < sizeof(attrs) / sizeof(attrs[0]); i++) {
		mix(&digest, x86_attr_to_l3attr_result(attrs[i], attr_mask));
		mix(&digest, x86_attr_to_l2attr_result(attrs[i], attr_mask));
		mix(&digest, x86_attr_to_l1attr_result(attrs[i], attr_mask));
		mix(&digest, x86_set_pte_value_result(0x200000 + i * 0x1000,
						      attrs[i], attr_mask));
	}
	size_t sizes[] = {
		0, 1, 4096, 4097, 2UL * 1024 * 1024,
		(2UL * 1024 * 1024) + 1, 1024UL * 1024 * 1024,
		(1024UL * 1024 * 1024) + 1,
	};
	for (unsigned int i = 0; i < sizeof(sizes) / sizeof(sizes[0]); i++) {
		for (int use_1gb = 0; use_1gb <= 1; use_1gb++) {
			size_t newsize = 0xfeedfaceUL;
			int p2align = 12345;
			int error = x86_smaller_page_size_result(sizes[i],
					use_1gb, &newsize, &p2align);
			mix(&digest, sizes[i]);
			mix(&digest, use_1gb);
			mix(&digest, (unsigned long)(unsigned int)-error);
			mix(&digest, newsize);
			mix(&digest, (unsigned long)(unsigned int)p2align);
		}
		mix(&digest, x86_early_alloc_align_end_result(sizes[i]));
		mix(&digest, (unsigned int)x86_early_alloc_exhausted_result(
			sizes[i], 2UL * 1024 * 1024));
		mix(&digest, x86_early_alloc_next_result(sizes[i],
			(int)i - 2));
	}
	{
		size_t pgsizes[] = {
			4096, 2UL * 1024 * 1024, 1024UL * 1024 * 1024,
			12345,
		};
		unsigned long phys[] = {
			0, 4096, 2UL * 1024 * 1024,
			(2UL * 1024 * 1024) + 4096,
			1024UL * 1024 * 1024,
			(1024UL * 1024 * 1024) + 4096,
		};

		for (unsigned int p = 0; p < sizeof(pgsizes) / sizeof(pgsizes[0]); p++) {
			for (unsigned int a = 0; a < sizeof(attrs) / sizeof(attrs[0]); a++) {
				for (unsigned int h = 0; h < sizeof(phys) / sizeof(phys[0]); h++) {
					for (int use_1gb = 0; use_1gb <= 1; use_1gb++) {
						unsigned long entry = 0x12345678UL;
						int error = x86_pt_set_pte_value_result(
							pgsizes[p], phys[h], attrs[a],
							attr_mask, use_1gb, &entry);

						mix(&digest, pgsizes[p]);
						mix(&digest, phys[h]);
						mix(&digest, attrs[a]);
						mix(&digest, use_1gb);
						mix(&digest, (unsigned long)(unsigned int)-error);
						mix(&digest, entry);
					}
				}
			}
		}
	}

printf("x86_memory_helpers ok digest=%016lx\n", digest);
	return 0;
}
EOF_X86_MEMORY_HELPERS

cat > "${tmpdir}/mcexec_helpers_smoke.c" <<'EOF_MCEXEC_HELPERS'
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>

extern int mcexec_path_is_absolute_result(const char *path);
extern int mcexec_path_is_single_component_exec_result(const char *path);
extern int mcexec_path_len_less_than_result(const char *path, size_t limit);
extern int mcexec_copy_path_result(const char *path, char *out, size_t size);
extern int mcexec_join_path_result(const char *prefix, const char *path,
				   char *out, size_t size);
extern int mcexec_objdump_rpath_cmd_result(const char *path, char *out,
					   size_t size);

#define require(expr) do { \
	if (!(expr)) { \
		fprintf(stderr, "require failed at %s:%d: %s\n", \
			__FILE__, __LINE__, #expr); \
		return 1; \
	} \
} while (0)

static void mix(unsigned long *digest, unsigned long value)
{
	*digest ^= value + 0x9e3779b97f4a7c15UL + (*digest << 6) + (*digest >> 2);
}

int main(void)
{
	char out[64];
	char limited[255 + 1];
	unsigned long digest = 0x6d636578656370UL;
	int i;
	int rc;

	require(mcexec_path_is_absolute_result("/bin/hostname") == 1);
	require(mcexec_path_is_absolute_result("bin/hostname") == 0);
	require(mcexec_path_is_absolute_result("") == 0);

	require(mcexec_path_is_single_component_exec_result("hostname") == 1);
	require(mcexec_path_is_single_component_exec_result("") == 1);
	require(mcexec_path_is_single_component_exec_result("./hostname") == 0);
	require(mcexec_path_is_single_component_exec_result(".hidden") == 0);
	require(mcexec_path_is_single_component_exec_result("bin/hostname") == 0);
	require(mcexec_path_is_single_component_exec_result("/bin/hostname") == 0);

	memset(limited, 'a', sizeof(limited));
	limited[254] = '\0';
	require(mcexec_path_len_less_than_result(limited, 255) == 1);
	limited[254] = 'a';
	limited[255] = '\0';
	require(mcexec_path_len_less_than_result(limited, 255) == 0);

	memset(out, 0xa5, sizeof(out));
	rc = mcexec_copy_path_result("abc", out, sizeof(out));
	require(rc == 3);
	require(strcmp(out, "abc") == 0);
	mix(&digest, (unsigned long)rc);
	for (i = 0; out[i]; i++)
		mix(&digest, (unsigned long)(unsigned char)out[i]);

	require(mcexec_copy_path_result("abcd", out, 4) == -ENAMETOOLONG);
	require(mcexec_copy_path_result("abcd", out, 5) == 4);

	memset(out, 0xa5, sizeof(out));
	rc = mcexec_join_path_result("/root", "/bin/hostname", out,
				     sizeof(out));
	require(rc == (int)strlen("/root//bin/hostname"));
	require(strcmp(out, "/root//bin/hostname") == 0);
	mix(&digest, (unsigned long)rc);
	for (i = 0; out[i]; i++)
		mix(&digest, (unsigned long)(unsigned char)out[i]);

	rc = mcexec_join_path_result("", "hostname", out, sizeof(out));
	require(rc == (int)strlen("/hostname"));
	require(strcmp(out, "/hostname") == 0);

	rc = mcexec_join_path_result("/usr/bin", "hostname", out, sizeof(out));
	require(rc == (int)strlen("/usr/bin/hostname"));
	require(strcmp(out, "/usr/bin/hostname") == 0);
	require(mcexec_join_path_result("/usr/bin", "hostname", out,
					strlen("/usr/bin/hostname")) ==
		-ENAMETOOLONG);

	rc = mcexec_objdump_rpath_cmd_result("/proc/self/exe", out,
					     sizeof(out));
	require(rc == (int)strlen("objdump -x /proc/self/exe | awk '/RPATH/ { print $2 }'"));
	require(strcmp(out,
		       "objdump -x /proc/self/exe | awk '/RPATH/ { print $2 }'")
		== 0);
	require(mcexec_objdump_rpath_cmd_result("/proc/self/exe", out,
						strlen(out)) ==
		-ENAMETOOLONG);

	printf("mcexec_helpers ok digest=%016lx\n", digest);
	return 0;
}
EOF_MCEXEC_HELPERS

cat > "${tmpdir}/rust_stubs.c" <<'EOF_STUBS'
int ihk_mc_chk_page_address(unsigned long mem_addr) { (void)mem_addr; return 0; }
unsigned long virt_to_phys(void *v) { return (unsigned long)v; }
void *phys_to_virt(unsigned long p) { return (void *)p; }
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
unsigned long shmid_index[512];
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
	-Iihk/cokernel/smp/x86_64
	-Iihk/cokernel/smp/x86_64/include
	-Iihk/ikc/include
	-Iihk/linux/include
)
sys=(-isystem "$(cc -print-file-name=include)")
kflags=(-ffreestanding -nostdinc "${sys[@]}" -D__KERNEL__ -DIHK_OS_MANYCORE \
	-DMAP_KERNEL_START=0xfffffffffe800000UL \
	-DKERNEL_RAM_VADDR=0xfffffffffe800000UL "${inc[@]}")

cc "${kflags[@]}" -c kernel/rbtree.c -o "${tmpdir}/out/rbtree_c.o"
cc "${kflags[@]}" -c kernel/llist.c -o "${tmpdir}/out/llist_c.o"
cc "${kflags[@]}" -I"${tmpdir}" -ffunction-sections -fdata-sections \
	-c kernel/waitq.c -o "${tmpdir}/out/waitq_c.o"
cc "${kflags[@]}" -I"${tmpdir}" -ffunction-sections -fdata-sections \
	-DMCKERNEL_RUST_WAITQ_CORE -c kernel/waitq.c \
	-o "${tmpdir}/out/waitq_dispatch_c.o"
cc "${kflags[@]}" -I"${tmpdir}" -ffunction-sections -fdata-sections \
	-c kernel/sched_helpers.c -o "${tmpdir}/out/sched_runtime_c.o"
cc "${kflags[@]}" -I"${tmpdir}" -ffunction-sections -fdata-sections \
	-c kernel/mem.c -o "${tmpdir}/out/mem_c.o"
cc "${kflags[@]}" -I"${tmpdir}" -ffunction-sections -fdata-sections \
	-Dmain=mckernel_init_main -c kernel/init.c \
	-o "${tmpdir}/out/init_c.o"
cc "${kflags[@]}" -I"${tmpdir}" -ffunction-sections -fdata-sections \
	-DMCKERNEL_SHMID_HELPERS_TEST_EXPORT \
	-DMCKERNEL_SHM_PERM_HELPERS_TEST_EXPORT \
	-DMCKERNEL_RLIMIT_HELPERS_TEST_EXPORT \
	-DMCKERNEL_SCHED_PRIO_HELPERS_TEST_EXPORT \
	-DMCKERNEL_SCHED_POLICY_HELPERS_TEST_EXPORT \
	-DMCKERNEL_SYSCALL_POLICY_HELPERS_TEST_EXPORT -c kernel/syscall.c \
	-o "${tmpdir}/out/syscall_shmid_c.o"
cc "${kflags[@]}" -I"${tmpdir}" -ffunction-sections -fdata-sections \
	-DMCKERNEL_XPMEM_HELPERS_TEST_EXPORT -c kernel/xpmem.c \
	-o "${tmpdir}/out/xpmem_helpers_c.o"
cc "${kflags[@]}" -I"${tmpdir}" -ffunction-sections -fdata-sections \
	-c kernel/object_helpers.c -o "${tmpdir}/out/object_helpers_c.o"
cc "${kflags[@]}" -I"${tmpdir}" -ffunction-sections -fdata-sections \
	-c kernel/process_helpers.c -o "${tmpdir}/out/process_helpers_c.o"
cc "${kflags[@]}" -I"${tmpdir}" -ffunction-sections -fdata-sections \
	-c arch/x86_64/kernel/memory_helpers.c \
	-o "${tmpdir}/out/x86_memory_helpers_c.o"
cc "${kflags[@]}" -I"${tmpdir}" -ffunction-sections -fdata-sections \
	-c kernel/plist.c -o "${tmpdir}/out/plist_c.o"
cc "${kflags[@]}" -ffunction-sections -fdata-sections -c lib/bitmap.c -o "${tmpdir}/out/bitmap_c.o"
cc "${kflags[@]}" -ffunction-sections -fdata-sections -c lib/bitops.c -o "${tmpdir}/out/bitops_c.o"
cc "${kflags[@]}" -I"${tmpdir}" -ffunction-sections -fdata-sections -fno-builtin \
	-c lib/string.c -o "${tmpdir}/out/string_c.o"
cc "${kflags[@]}" -I"${tmpdir}" -ffunction-sections -fdata-sections -fno-builtin \
	-c lib/vsprintf.c -o "${tmpdir}/out/vsprintf_c.o"

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

rustc --crate-name ihk_core_helpers \
	--crate-type lib \
	--edition=2021 \
	-C panic=abort \
	-C opt-level=2 \
	-C debuginfo=1 \
	-C code-model=kernel \
	-C relocation-model=static \
	-C no-redzone=yes \
	-C force-frame-pointers=yes \
	-C overflow-checks=off \
	-C force-unwind-tables=no \
	-C no-vectorize-loops \
	-C no-vectorize-slp \
	--emit=obj="${tmpdir}/out/ihk_core_helpers.o" \
	ihk/linux/core/rust/core_helpers.rs

rustc --crate-name mcctrl_helpers \
	--crate-type lib \
	--edition=2021 \
	-C panic=abort \
	-C opt-level=2 \
	-C debuginfo=1 \
	-C code-model=kernel \
	-C relocation-model=static \
	-C no-redzone=yes \
	-C force-frame-pointers=yes \
	-C overflow-checks=off \
	-C force-unwind-tables=no \
	-C no-vectorize-loops \
	-C no-vectorize-slp \
	--emit=obj="${tmpdir}/out/mcctrl_helpers.o" \
	executer/kernel/mcctrl/rust/mcctrl_helpers.rs

rustc --crate-name smp_driver_helpers \
	--crate-type lib \
	--edition=2021 \
	-C panic=abort \
	-C opt-level=2 \
	-C debuginfo=1 \
	-C code-model=kernel \
	-C relocation-model=static \
	-C no-redzone=yes \
	-C force-frame-pointers=yes \
	-C overflow-checks=off \
	-C force-unwind-tables=no \
	-C no-vectorize-loops \
	-C no-vectorize-slp \
	--emit=obj="${tmpdir}/out/smp_driver_helpers.o" \
	ihk/linux/driver/smp/rust/smp_driver_helpers.rs

rustc --crate-name mcexec_helpers \
	--crate-type lib \
	--edition=2021 \
	-C panic=abort \
	-C opt-level=2 \
	-C debuginfo=1 \
	-C force-unwind-tables=no \
	--emit=obj="${tmpdir}/out/mcexec_helpers.o" \
	executer/user/rust/mcexec_helpers.rs

check_module_rust_object()
{
	local obj="$1"

	if nm -u "${obj}" | grep -q .; then
		echo "unexpected undefined symbols in ${obj}" >&2
		nm -u "${obj}" >&2
		exit 1
	fi

	if readelf -r "${obj}" | grep -q 'R_X86_64_GOTPCREL'; then
		echo "unsupported x86_64 kernel-module relocation in ${obj}" >&2
		readelf -r "${obj}" | grep 'R_X86_64_GOTPCREL' >&2
		exit 1
	fi
}

check_module_rust_object "${tmpdir}/out/ihk_core_helpers.o"
check_module_rust_object "${tmpdir}/out/mcctrl_helpers.o"
check_module_rust_object "${tmpdir}/out/smp_driver_helpers.o"

cc "${tmpdir}/rbtree_equiv.c" "${tmpdir}/out/rbtree_c.o" -o "${tmpdir}/out/rbtree_c"
cc -Wl,--gc-sections "${tmpdir}/rbtree_equiv.c" \
	"${tmpdir}/out/mckernel_rust.o" -o "${tmpdir}/out/rbtree_rust"
cc "${tmpdir}/llist_equiv.c" "${tmpdir}/out/llist_c.o" -o "${tmpdir}/out/llist_c"
cc "${tmpdir}/llist_equiv.c" "${tmpdir}/rust_stubs.c" "${tmpdir}/out/mckernel_rust.o" -o "${tmpdir}/out/llist_rust"
cc -Wl,--gc-sections "${tmpdir}/waitq_equiv.c" "${tmpdir}/out/waitq_c.o" \
	-o "${tmpdir}/out/waitq_c"
cc -Wl,--gc-sections "${tmpdir}/waitq_equiv.c" "${tmpdir}/rust_stubs.c" \
	"${tmpdir}/out/waitq_dispatch_c.o" "${tmpdir}/out/mckernel_rust.o" \
	-o "${tmpdir}/out/waitq_rust"
cc -fno-builtin -Wl,--gc-sections "${tmpdir}/mem_init_helpers_equiv.c" \
	"${tmpdir}/out/mem_c.o" "${tmpdir}/out/init_c.o" \
	"${tmpdir}/out/string_c.o" -o "${tmpdir}/out/mem_init_helpers_c"
cc -fno-builtin -Wl,--gc-sections "${tmpdir}/mem_init_helpers_equiv.c" \
	"${tmpdir}/rust_stubs.c" "${tmpdir}/out/mckernel_rust.o" \
	-o "${tmpdir}/out/mem_init_helpers_rust"
cc -Wl,--gc-sections "${tmpdir}/page_helpers_equiv.c" \
	"${tmpdir}/out/mem_c.o" -o "${tmpdir}/out/page_helpers_c"
cc -Wl,--gc-sections "${tmpdir}/page_helpers_equiv.c" \
	"${tmpdir}/rust_stubs.c" "${tmpdir}/out/mckernel_rust.o" \
	-o "${tmpdir}/out/page_helpers_rust"
cc -Wl,--gc-sections -Wl,--unresolved-symbols=ignore-all \
	-Wl,--noinhibit-exec "${tmpdir}/shmid_helpers_equiv.c" \
	"${tmpdir}/out/syscall_shmid_c.o" -o "${tmpdir}/out/shmid_helpers_c"
cc -Wl,--gc-sections "${tmpdir}/shmid_helpers_equiv.c" \
	"${tmpdir}/rust_stubs.c" "${tmpdir}/out/mckernel_rust.o" \
	-o "${tmpdir}/out/shmid_helpers_rust"
cc -Wl,--gc-sections -Wl,--unresolved-symbols=ignore-all \
	-Wl,--noinhibit-exec "${tmpdir}/sched_helpers_equiv.c" \
	"${tmpdir}/out/syscall_shmid_c.o" "${tmpdir}/out/sched_runtime_c.o" \
	-o "${tmpdir}/out/sched_helpers_c"
cc -Wl,--gc-sections "${tmpdir}/sched_helpers_equiv.c" \
	"${tmpdir}/rust_stubs.c" "${tmpdir}/out/mckernel_rust.o" \
	-o "${tmpdir}/out/sched_helpers_rust"
cc -Wl,--gc-sections -Wl,--unresolved-symbols=ignore-all \
	-Wl,--noinhibit-exec "${tmpdir}/rlimit_helpers_equiv.c" \
	"${tmpdir}/out/syscall_shmid_c.o" -o "${tmpdir}/out/rlimit_helpers_c"
cc -Wl,--gc-sections "${tmpdir}/rlimit_helpers_equiv.c" \
	"${tmpdir}/rust_stubs.c" "${tmpdir}/out/mckernel_rust.o" \
	-o "${tmpdir}/out/rlimit_helpers_rust"
cc -Wl,--gc-sections -Wl,--unresolved-symbols=ignore-all \
	-Wl,--noinhibit-exec "${tmpdir}/syscall_policy_helpers_equiv.c" \
	"${tmpdir}/out/syscall_shmid_c.o" -o "${tmpdir}/out/syscall_policy_helpers_c"
cc -Wl,--gc-sections "${tmpdir}/syscall_policy_helpers_equiv.c" \
	"${tmpdir}/rust_stubs.c" "${tmpdir}/out/mckernel_rust.o" \
	-o "${tmpdir}/out/syscall_policy_helpers_rust"
cc -Wl,--gc-sections -Wl,--unresolved-symbols=ignore-all \
	-Wl,--noinhibit-exec "${tmpdir}/xpmem_helpers_equiv.c" \
	"${tmpdir}/out/xpmem_helpers_c.o" -o "${tmpdir}/out/xpmem_helpers_c"
cc -Wl,--gc-sections "${tmpdir}/xpmem_helpers_equiv.c" \
	"${tmpdir}/rust_stubs.c" "${tmpdir}/out/mckernel_rust.o" \
	-o "${tmpdir}/out/xpmem_helpers_rust"
cc -Wl,--gc-sections "${tmpdir}/object_helpers_equiv.c" \
	"${tmpdir}/out/object_helpers_c.o" -o "${tmpdir}/out/object_helpers_c"
cc -Wl,--gc-sections "${tmpdir}/object_helpers_equiv.c" \
	"${tmpdir}/rust_stubs.c" "${tmpdir}/out/mckernel_rust.o" \
	-o "${tmpdir}/out/object_helpers_rust"
cc -Wl,--gc-sections -Wl,--unresolved-symbols=ignore-all \
	-Wl,--noinhibit-exec "${tmpdir}/process_helpers_equiv.c" \
	"${tmpdir}/out/process_helpers_c.o" -o "${tmpdir}/out/process_helpers_c"
cc -Wl,--gc-sections "${tmpdir}/process_helpers_equiv.c" \
	"${tmpdir}/rust_stubs.c" "${tmpdir}/out/mckernel_rust.o" \
	-o "${tmpdir}/out/process_helpers_rust"
cc -Wl,--gc-sections "${tmpdir}/x86_memory_helpers_equiv.c" \
	"${tmpdir}/out/x86_memory_helpers_c.o" \
	-o "${tmpdir}/out/x86_memory_helpers_c"
cc -Wl,--gc-sections "${tmpdir}/x86_memory_helpers_equiv.c" \
	"${tmpdir}/rust_stubs.c" "${tmpdir}/out/mckernel_rust.o" \
	-o "${tmpdir}/out/x86_memory_helpers_rust"
cc -Wl,--gc-sections "${tmpdir}/plist_equiv.c" "${tmpdir}/out/plist_c.o" \
	-o "${tmpdir}/out/plist_c"
cc "${tmpdir}/plist_equiv.c" "${tmpdir}/rust_stubs.c" \
	"${tmpdir}/out/mckernel_rust.o" -o "${tmpdir}/out/plist_rust"
cc "${tmpdir}/bitops_equiv.c" "${tmpdir}/out/bitops_c.o" -o "${tmpdir}/out/bitops_c"
cc "${tmpdir}/bitops_equiv.c" "${tmpdir}/rust_stubs.c" \
	"${tmpdir}/out/mckernel_rust.o" -o "${tmpdir}/out/bitops_rust"
cc -fno-builtin -Wl,--gc-sections "${tmpdir}/string_equiv.c" \
	"${tmpdir}/out/string_c.o" -o "${tmpdir}/out/string_c"
cc -fno-builtin "${tmpdir}/string_equiv.c" "${tmpdir}/rust_stubs.c" \
	"${tmpdir}/out/mckernel_rust.o" -o "${tmpdir}/out/string_rust"
cc -fno-builtin -Wl,--gc-sections "${tmpdir}/numparse_equiv.c" \
	"${tmpdir}/out/vsprintf_c.o" "${tmpdir}/out/string_c.o" \
	-o "${tmpdir}/out/numparse_c"
cc -fno-builtin "${tmpdir}/numparse_equiv.c" "${tmpdir}/rust_stubs.c" \
	"${tmpdir}/out/mckernel_rust.o" -o "${tmpdir}/out/numparse_rust"
cc -Wl,--gc-sections "${tmpdir}/bitmap_equiv.c" "${tmpdir}/ctype_stub.c" \
	"${tmpdir}/out/bitmap_c.o" "${tmpdir}/out/bitops_c.o" -o "${tmpdir}/out/bitmap_c"
cc "${tmpdir}/bitmap_equiv.c" "${tmpdir}/rust_stubs.c" \
	"${tmpdir}/out/mckernel_rust.o" -o "${tmpdir}/out/bitmap_rust"
cc -Wl,--gc-sections "${tmpdir}/bitmap_parse_equiv.c" "${tmpdir}/ctype_stub.c" \
	"${tmpdir}/out/bitmap_c.o" "${tmpdir}/out/bitops_c.o" \
	"${tmpdir}/out/string_c.o" -o "${tmpdir}/out/bitmap_parse_c"
cc "${tmpdir}/bitmap_parse_equiv.c" "${tmpdir}/rust_stubs.c" \
	"${tmpdir}/out/mckernel_rust.o" -o "${tmpdir}/out/bitmap_parse_rust"
cc "${kflags[@]}" -I"${tmpdir}" -I. -ffunction-sections -fdata-sections -DPAGE_ALLOC_USE_C \
	"${tmpdir}/page_alloc_equiv.c" "${tmpdir}/out/rbtree_c.o" \
	-Wl,--gc-sections -o "${tmpdir}/out/page_alloc_c"
cc -Wl,--gc-sections "${tmpdir}/page_alloc_equiv.c" "${tmpdir}/out/mckernel_rust.o" \
	-o "${tmpdir}/out/page_alloc_rust"
cc "${kflags[@]}" -I"${tmpdir}" -I. -ffunction-sections -fdata-sections \
	"${tmpdir}/page_alloc_bitmap_equiv.c" "${tmpdir}/out/rbtree_c.o" \
	"${tmpdir}/out/llist_c.o" \
	-Wl,--gc-sections -o "${tmpdir}/out/page_alloc_bitmap_c"
cc "${kflags[@]}" -I"${tmpdir}" -I. -ffunction-sections -fdata-sections \
	-DMCKERNEL_RUST_PAGEALLOC_BITMAP -DMCKERNEL_RUST_PAGE_ALLOC_RBTREE \
	"${tmpdir}/page_alloc_bitmap_equiv.c" "${tmpdir}/out/mckernel_rust.o" \
	-Wl,--gc-sections -o "${tmpdir}/out/page_alloc_bitmap_rust"
cc -Wl,--gc-sections kernel/rust/tests/ihk_module_helpers_smoke.c \
	"${tmpdir}/out/ihk_core_helpers.o" "${tmpdir}/out/mcctrl_helpers.o" \
	"${tmpdir}/out/smp_driver_helpers.o" \
	-o "${tmpdir}/out/ihk_module_helpers_smoke"
cc -Wl,--gc-sections "${tmpdir}/mcexec_helpers_smoke.c" \
	"${tmpdir}/out/mcexec_helpers.o" -o "${tmpdir}/out/mcexec_helpers_smoke"

"${tmpdir}/out/rbtree_c" > "${tmpdir}/out/rbtree_c.out"
"${tmpdir}/out/rbtree_rust" > "${tmpdir}/out/rbtree_rust.out"
"${tmpdir}/out/llist_c" > "${tmpdir}/out/llist_c.out"
"${tmpdir}/out/llist_rust" > "${tmpdir}/out/llist_rust.out"
"${tmpdir}/out/waitq_c" > "${tmpdir}/out/waitq_c.out"
"${tmpdir}/out/waitq_rust" > "${tmpdir}/out/waitq_rust.out"
"${tmpdir}/out/mem_init_helpers_c" > "${tmpdir}/out/mem_init_helpers_c.out"
"${tmpdir}/out/mem_init_helpers_rust" > "${tmpdir}/out/mem_init_helpers_rust.out"
"${tmpdir}/out/page_helpers_c" > "${tmpdir}/out/page_helpers_c.out"
"${tmpdir}/out/page_helpers_rust" > "${tmpdir}/out/page_helpers_rust.out"
"${tmpdir}/out/shmid_helpers_c" > "${tmpdir}/out/shmid_helpers_c.out"
"${tmpdir}/out/shmid_helpers_rust" > "${tmpdir}/out/shmid_helpers_rust.out"
"${tmpdir}/out/sched_helpers_c" > "${tmpdir}/out/sched_helpers_c.out"
"${tmpdir}/out/sched_helpers_rust" > "${tmpdir}/out/sched_helpers_rust.out"
"${tmpdir}/out/rlimit_helpers_c" > "${tmpdir}/out/rlimit_helpers_c.out"
"${tmpdir}/out/rlimit_helpers_rust" > "${tmpdir}/out/rlimit_helpers_rust.out"
"${tmpdir}/out/syscall_policy_helpers_c" > "${tmpdir}/out/syscall_policy_helpers_c.out"
"${tmpdir}/out/syscall_policy_helpers_rust" > "${tmpdir}/out/syscall_policy_helpers_rust.out"
"${tmpdir}/out/xpmem_helpers_c" > "${tmpdir}/out/xpmem_helpers_c.out"
"${tmpdir}/out/xpmem_helpers_rust" > "${tmpdir}/out/xpmem_helpers_rust.out"
"${tmpdir}/out/object_helpers_c" > "${tmpdir}/out/object_helpers_c.out"
"${tmpdir}/out/object_helpers_rust" > "${tmpdir}/out/object_helpers_rust.out"
"${tmpdir}/out/process_helpers_c" > "${tmpdir}/out/process_helpers_c.out"
"${tmpdir}/out/process_helpers_rust" > "${tmpdir}/out/process_helpers_rust.out"
"${tmpdir}/out/x86_memory_helpers_c" > "${tmpdir}/out/x86_memory_helpers_c.out"
"${tmpdir}/out/x86_memory_helpers_rust" > "${tmpdir}/out/x86_memory_helpers_rust.out"
"${tmpdir}/out/plist_c" > "${tmpdir}/out/plist_c.out"
"${tmpdir}/out/plist_rust" > "${tmpdir}/out/plist_rust.out"
"${tmpdir}/out/bitops_c" > "${tmpdir}/out/bitops_c.out"
"${tmpdir}/out/bitops_rust" > "${tmpdir}/out/bitops_rust.out"
"${tmpdir}/out/string_c" > "${tmpdir}/out/string_c.out"
"${tmpdir}/out/string_rust" > "${tmpdir}/out/string_rust.out"
"${tmpdir}/out/numparse_c" > "${tmpdir}/out/numparse_c.out"
"${tmpdir}/out/numparse_rust" > "${tmpdir}/out/numparse_rust.out"
"${tmpdir}/out/bitmap_c" > "${tmpdir}/out/bitmap_c.out"
"${tmpdir}/out/bitmap_rust" > "${tmpdir}/out/bitmap_rust.out"
"${tmpdir}/out/bitmap_parse_c" > "${tmpdir}/out/bitmap_parse_c.out"
"${tmpdir}/out/bitmap_parse_rust" > "${tmpdir}/out/bitmap_parse_rust.out"
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
"${tmpdir}/out/ihk_module_helpers_smoke" > "${tmpdir}/out/ihk_module_helpers_smoke.out"
"${tmpdir}/out/mcexec_helpers_smoke" > "${tmpdir}/out/mcexec_helpers_smoke.out"

diff -u "${tmpdir}/out/rbtree_c.out" "${tmpdir}/out/rbtree_rust.out"
diff -u "${tmpdir}/out/llist_c.out" "${tmpdir}/out/llist_rust.out"
diff -u "${tmpdir}/out/waitq_c.out" "${tmpdir}/out/waitq_rust.out"
diff -u "${tmpdir}/out/mem_init_helpers_c.out" "${tmpdir}/out/mem_init_helpers_rust.out"
diff -u "${tmpdir}/out/page_helpers_c.out" "${tmpdir}/out/page_helpers_rust.out"
diff -u "${tmpdir}/out/shmid_helpers_c.out" "${tmpdir}/out/shmid_helpers_rust.out"
diff -u "${tmpdir}/out/sched_helpers_c.out" "${tmpdir}/out/sched_helpers_rust.out"
diff -u "${tmpdir}/out/rlimit_helpers_c.out" "${tmpdir}/out/rlimit_helpers_rust.out"
diff -u "${tmpdir}/out/syscall_policy_helpers_c.out" "${tmpdir}/out/syscall_policy_helpers_rust.out"
diff -u "${tmpdir}/out/xpmem_helpers_c.out" "${tmpdir}/out/xpmem_helpers_rust.out"
diff -u "${tmpdir}/out/object_helpers_c.out" "${tmpdir}/out/object_helpers_rust.out"
diff -u "${tmpdir}/out/process_helpers_c.out" "${tmpdir}/out/process_helpers_rust.out"
diff -u "${tmpdir}/out/x86_memory_helpers_c.out" "${tmpdir}/out/x86_memory_helpers_rust.out"
diff -u "${tmpdir}/out/plist_c.out" "${tmpdir}/out/plist_rust.out"
diff -u "${tmpdir}/out/bitops_c.out" "${tmpdir}/out/bitops_rust.out"
diff -u "${tmpdir}/out/string_c.out" "${tmpdir}/out/string_rust.out"
diff -u "${tmpdir}/out/numparse_c.out" "${tmpdir}/out/numparse_rust.out"
diff -u "${tmpdir}/out/bitmap_c.out" "${tmpdir}/out/bitmap_rust.out"
diff -u "${tmpdir}/out/bitmap_parse_c.out" "${tmpdir}/out/bitmap_parse_rust.out"
diff -u "${tmpdir}/out/page_alloc_c.out" "${tmpdir}/out/page_alloc_rust.out"
diff -u "${tmpdir}/out/page_alloc_bitmap_c.out" "${tmpdir}/out/page_alloc_bitmap_rust.out"

nm -u "${tmpdir}/out/mckernel_rust.o" | tee "${tmpdir}/out/rust.undefined"
grep -Eq 'U default_wake_function' "${tmpdir}/out/rust.undefined"
grep -Eq 'U ihk_mc_chk_page_address' "${tmpdir}/out/rust.undefined"
grep -Eq 'U ihk_get_kargs' "${tmpdir}/out/rust.undefined"
grep -Eq 'U ihk_mc_get_memory_chunk' "${tmpdir}/out/rust.undefined"
grep -Eq 'U ihk_mc_get_nr_memory_chunks' "${tmpdir}/out/rust.undefined"
grep -Eq 'U phys_to_virt' "${tmpdir}/out/rust.undefined"
grep -Eq 'U shmid_index' "${tmpdir}/out/rust.undefined"
grep -Eq 'U virt_to_phys' "${tmpdir}/out/rust.undefined"
grep -Eq 'U zero_at_free' "${tmpdir}/out/rust.undefined"
test "$(grep -c ' U ' "${tmpdir}/out/rust.undefined")" -eq 9

simd_count="$(objdump -d "${tmpdir}/out/mckernel_rust.o" |
	grep -Eic 'xmm|ymm|mmx|movdqa|movdqu|movups|pshuf|padd|pand|pxor|popcnt' || true)"
test "${simd_count}" -eq 0

cat "${tmpdir}/out/rbtree_c.out"
cat "${tmpdir}/out/llist_c.out"
cat "${tmpdir}/out/waitq_c.out"
cat "${tmpdir}/out/mem_init_helpers_c.out"
cat "${tmpdir}/out/page_helpers_c.out"
cat "${tmpdir}/out/shmid_helpers_c.out"
cat "${tmpdir}/out/sched_helpers_c.out"
cat "${tmpdir}/out/rlimit_helpers_c.out"
cat "${tmpdir}/out/syscall_policy_helpers_c.out"
cat "${tmpdir}/out/xpmem_helpers_c.out"
cat "${tmpdir}/out/object_helpers_c.out"
cat "${tmpdir}/out/process_helpers_c.out"
cat "${tmpdir}/out/x86_memory_helpers_c.out"
cat "${tmpdir}/out/plist_c.out"
cat "${tmpdir}/out/bitops_c.out"
cat "${tmpdir}/out/string_c.out"
cat "${tmpdir}/out/numparse_c.out"
cat "${tmpdir}/out/bitmap_c.out"
cat "${tmpdir}/out/bitmap_parse_c.out"
cat "${tmpdir}/out/page_alloc_c.out"
cat "${tmpdir}/out/page_alloc_bitmap_c.out"
cat "${tmpdir}/out/ihk_module_helpers_smoke.out"
cat "${tmpdir}/out/mcexec_helpers_smoke.out"
echo "rust object unresolved symbols and SIMD checks ok"
