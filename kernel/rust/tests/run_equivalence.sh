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
	require(items[0].wakes == 0 && items[1].wakes == 0 && items[2].wakes == 0);
	mix(&digest, (unsigned long)(int)ret);

	ret = waitq_wake_nr_locked(&waitq, 2);
	require(ret == 2);
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
	-c kernel/mem.c -o "${tmpdir}/out/mem_c.o"
cc "${kflags[@]}" -I"${tmpdir}" -ffunction-sections -fdata-sections \
	-Dmain=mckernel_init_main -c kernel/init.c \
	-o "${tmpdir}/out/init_c.o"
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

diff -u "${tmpdir}/out/rbtree_c.out" "${tmpdir}/out/rbtree_rust.out"
diff -u "${tmpdir}/out/llist_c.out" "${tmpdir}/out/llist_rust.out"
diff -u "${tmpdir}/out/waitq_c.out" "${tmpdir}/out/waitq_rust.out"
diff -u "${tmpdir}/out/mem_init_helpers_c.out" "${tmpdir}/out/mem_init_helpers_rust.out"
diff -u "${tmpdir}/out/page_helpers_c.out" "${tmpdir}/out/page_helpers_rust.out"
diff -u "${tmpdir}/out/plist_c.out" "${tmpdir}/out/plist_rust.out"
diff -u "${tmpdir}/out/bitops_c.out" "${tmpdir}/out/bitops_rust.out"
diff -u "${tmpdir}/out/string_c.out" "${tmpdir}/out/string_rust.out"
diff -u "${tmpdir}/out/numparse_c.out" "${tmpdir}/out/numparse_rust.out"
diff -u "${tmpdir}/out/bitmap_c.out" "${tmpdir}/out/bitmap_rust.out"
diff -u "${tmpdir}/out/bitmap_parse_c.out" "${tmpdir}/out/bitmap_parse_rust.out"
diff -u "${tmpdir}/out/page_alloc_c.out" "${tmpdir}/out/page_alloc_rust.out"
diff -u "${tmpdir}/out/page_alloc_bitmap_c.out" "${tmpdir}/out/page_alloc_bitmap_rust.out"

nm -u "${tmpdir}/out/mckernel_rust.o" | tee "${tmpdir}/out/rust.undefined"
grep -Eq 'U ihk_mc_chk_page_address' "${tmpdir}/out/rust.undefined"
grep -Eq 'U ihk_get_kargs' "${tmpdir}/out/rust.undefined"
grep -Eq 'U ihk_mc_get_memory_chunk' "${tmpdir}/out/rust.undefined"
grep -Eq 'U ihk_mc_get_nr_memory_chunks' "${tmpdir}/out/rust.undefined"
grep -Eq 'U phys_to_virt' "${tmpdir}/out/rust.undefined"
grep -Eq 'U virt_to_phys' "${tmpdir}/out/rust.undefined"
grep -Eq 'U zero_at_free' "${tmpdir}/out/rust.undefined"
test "$(grep -c ' U ' "${tmpdir}/out/rust.undefined")" -eq 7

simd_count="$(objdump -d "${tmpdir}/out/mckernel_rust.o" |
	grep -Eic 'xmm|ymm|mmx|movdqa|movdqu|movups|pshuf|padd|pand|pxor|popcnt' || true)"
test "${simd_count}" -eq 0

cat "${tmpdir}/out/rbtree_c.out"
cat "${tmpdir}/out/llist_c.out"
cat "${tmpdir}/out/waitq_c.out"
cat "${tmpdir}/out/mem_init_helpers_c.out"
cat "${tmpdir}/out/page_helpers_c.out"
cat "${tmpdir}/out/plist_c.out"
cat "${tmpdir}/out/bitops_c.out"
cat "${tmpdir}/out/string_c.out"
cat "${tmpdir}/out/numparse_c.out"
cat "${tmpdir}/out/bitmap_c.out"
cat "${tmpdir}/out/bitmap_parse_c.out"
cat "${tmpdir}/out/page_alloc_c.out"
cat "${tmpdir}/out/page_alloc_bitmap_c.out"
echo "rust object unresolved symbols and SIMD checks ok"
