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

cat > "${tmpdir}/rust_stubs.c" <<'EOF_STUBS'
int ihk_mc_chk_page_address(unsigned long mem_addr) { (void)mem_addr; return 0; }
unsigned long virt_to_phys(void *v) { return (unsigned long)v; }
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

"${tmpdir}/out/rbtree_c" > "${tmpdir}/out/rbtree_c.out"
"${tmpdir}/out/rbtree_rust" > "${tmpdir}/out/rbtree_rust.out"
"${tmpdir}/out/llist_c" > "${tmpdir}/out/llist_c.out"
"${tmpdir}/out/llist_rust" > "${tmpdir}/out/llist_rust.out"
"${tmpdir}/out/bitmap_c" > "${tmpdir}/out/bitmap_c.out"
"${tmpdir}/out/bitmap_rust" > "${tmpdir}/out/bitmap_rust.out"

diff -u "${tmpdir}/out/rbtree_c.out" "${tmpdir}/out/rbtree_rust.out"
diff -u "${tmpdir}/out/llist_c.out" "${tmpdir}/out/llist_rust.out"
diff -u "${tmpdir}/out/bitmap_c.out" "${tmpdir}/out/bitmap_rust.out"

nm -u "${tmpdir}/out/mckernel_rust.o" | tee "${tmpdir}/out/rust.undefined"
grep -Eq 'U ihk_mc_chk_page_address' "${tmpdir}/out/rust.undefined"
grep -Eq 'U virt_to_phys' "${tmpdir}/out/rust.undefined"
test "$(grep -c ' U ' "${tmpdir}/out/rust.undefined")" -eq 2

simd_count="$(objdump -d "${tmpdir}/out/mckernel_rust.o" |
	grep -Eic 'xmm|ymm|mmx|movdqa|movdqu|movups|pshuf|padd|pand|pxor|popcnt' || true)"
test "${simd_count}" -eq 0

cat "${tmpdir}/out/rbtree_c.out"
cat "${tmpdir}/out/llist_c.out"
cat "${tmpdir}/out/bitmap_c.out"
echo "rust object unresolved symbols and SIMD checks ok"
