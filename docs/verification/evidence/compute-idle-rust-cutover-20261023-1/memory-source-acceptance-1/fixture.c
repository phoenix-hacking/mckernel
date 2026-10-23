/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * The oracle includes the unchanged production C bodies. Both variants reuse
 * the real existing Rust PTE/action helpers and Rust page-mode helper.
 */
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef unsigned long pte_t;
struct memobj {
    void *ops;
    uint32_t flags, status;
    size_t size;
    int refcnt, padding;
    void **pages;
    int nr_pages, padding2;
    char *path;
};
struct page {
    void *list[2], *hash[2];
    unsigned char mode;
    unsigned long phys;
    int count;
    long mapped, offset;
    int pgshift;
};
struct clear_range_args {
    int free_physical;
    struct memobj *memobj;
    void *vm;
    unsigned long *addr;
    int nr_addr, max_nr_addr;
};
#define MF_ZEROFILL 0x0010
#define MF_PRIVATE 0x200000
#define MF_XPMEM 0x10000
#define PHYS_MASK 0x000ffffffffff000UL
_Static_assert(sizeof(struct memobj) == 56, "real Rust Memobj ABI");
_Static_assert(offsetof(struct memobj, flags) == 8, "real Rust Memobj flags ABI");
_Static_assert(sizeof(struct page) == 80, "real Rust Page ABI");
_Static_assert(offsetof(struct page, mode) == 32, "real Rust Page mode ABI");
_Static_assert(sizeof(struct clear_range_args) == 40, "clear-range ABI");
_Static_assert(offsetof(struct clear_range_args, memobj) == 8, "clear-range memobj ABI");
extern void x86_clear_range_old_entry_result(unsigned long, unsigned long,
        unsigned long *, int *, int *);
extern int x86_clear_range_old_action_result(int, int, int, int, int, int, int, int);
extern int page_is_in_memobj(struct page *);
extern int x86_clear_old_action_bridge(void *, unsigned long, size_t,
        unsigned long *, void **, int *);

static struct page test_page;
static struct memobj obj, replacement;
static struct {
    struct clear_range_args *args;
    unsigned long *phys;
    void **page;
    int *fileoff;
    unsigned long want_phys;
    int has_page, calls, mutation, order_failure;
} ctx;

struct page *phys_to_page(unsigned long phys)
{
    ++ctx.calls;
    /* These writes must precede lookup; optional page publication must follow it. */
    if (phys != ctx.want_phys || *ctx.phys != ctx.want_phys ||
            (ctx.fileoff && *ctx.fileoff != 0) ||
            (ctx.page && *ctx.page != (void *)(uintptr_t)0x5a5a))
        ctx.order_failure = 1;
    switch (ctx.mutation) {
    case 1: if (ctx.args->memobj) ctx.args->memobj->flags ^= 0xffffffffU; break;
    case 2: ctx.args->free_physical = !ctx.args->free_physical; break;
    case 3: ctx.args->memobj = NULL; break;
    case 4: ctx.args->memobj = &replacement; break;
    case 5:
        if (ctx.args->memobj) ctx.args->memobj->flags ^= 0xffffffffU;
        ctx.args->free_physical = !ctx.args->free_physical;
        ctx.args->memobj = NULL;
        break;
    }
    return ctx.has_page ? &test_page : NULL;
}

#define x86_clear_old_action_bridge original_x86_clear_old_action_bridge
#include "original-clear-range.c.inc"
#undef x86_clear_old_action_bridge

typedef int (*action_fn)(void *, unsigned long, size_t, unsigned long *, void **, int *);
struct result {
    int action, fileoff, calls, order_failure, free_after, has_memobj_after;
    int page_is_expected;
    unsigned long phys;
    unsigned int flags_after;
};
static struct result run(action_fn fn, unsigned long old, size_t size,
        int free_physical, unsigned int flags, int has_obj, int page_mode,
        int options, int mutation)
{
    struct clear_range_args args = {free_physical, has_obj ? &obj : NULL,
            (void *)0x1230, NULL, 17, 29};
    unsigned long phys = ~0UL;
    int fileoff = -1234;
    void *page = (void *)(uintptr_t)0x5a5a;
    memset(&test_page, 0, sizeof(test_page));
    test_page.mode = page_mode < 0 ? 0 : page_mode;
    memset(&obj, 0, sizeof(obj));
    obj.flags = flags;
    memset(&replacement, 0, sizeof(replacement));
    replacement.flags = ~flags;
    memset(&ctx, 0, sizeof(ctx));
    ctx.args = &args;
    ctx.phys = &phys;
    ctx.page = (options & 1) ? &page : NULL;
    ctx.fileoff = (options & 2) ? &fileoff : NULL;
    ctx.want_phys = old & PHYS_MASK;
    ctx.has_page = page_mode >= 0;
    ctx.mutation = mutation;
    int action = fn(&args, old, size, &phys, ctx.page, ctx.fileoff);
    struct result r = {0};
    r.action = action;
    r.fileoff = fileoff;
    r.calls = ctx.calls;
    r.order_failure = ctx.order_failure;
    r.free_after = args.free_physical;
    r.has_memobj_after = args.memobj != NULL;
    r.page_is_expected = (options & 1)
            ? page == ((!(old & 0x800) && page_mode >= 0) ? (void *)&test_page : NULL)
            : page == (void *)(uintptr_t)0x5a5a;
    r.phys = phys;
    r.flags_after = obj.flags;
    /* Unrelated caller-owned fields must not change. */
    assert(args.vm == (void *)0x1230 && args.addr == NULL &&
            args.nr_addr == 17 && args.max_nr_addr == 29);
    return r;
}
static unsigned long cases, digest = 0xcbf29ce484222325UL;
static void check(unsigned long old, size_t size, int free_physical,
        unsigned flags, int has_obj, int page_mode, int options, int mutation)
{
    struct result c = run(original_x86_clear_old_action_bridge, old, size,
            free_physical, flags, has_obj, page_mode, options, mutation);
    struct result r = run(x86_clear_old_action_bridge, old, size,
            free_physical, flags, has_obj, page_mode, options, mutation);
    if (c.action != r.action || c.fileoff != r.fileoff || c.calls != r.calls ||
            c.order_failure != r.order_failure || c.free_after != r.free_after ||
            c.has_memobj_after != r.has_memobj_after ||
            c.page_is_expected != r.page_is_expected || c.phys != r.phys ||
            c.flags_after != r.flags_after) {
        fprintf(stderr, "differential mismatch case=%lu old=%lx size=%lx free=%d flags=%x obj=%d mode=%d options=%d mutation=%d\n",
                cases, old, size, free_physical, flags, has_obj, page_mode, options, mutation);
        assert(0);
    }
    int fileoff = !!(old & 0x800), want = 0;
    unsigned snap_flags = has_obj ? flags : 0;
    int final_obj = fileoff ? has_obj :
            ((mutation == 3 || mutation == 5) ? 0 : mutation == 4 ? 1 : has_obj);
    int final_free = !fileoff && (mutation == 2 || mutation == 5)
            ? !free_physical : free_physical;
    if (!fileoff) {
        if (page_mode >= 2 && page_mode <= 7 && (old & 0x40) && final_obj &&
                !(snap_flags & (MF_ZEROFILL | MF_PRIVATE))) want |= 1;
        if (final_free) {
            if (page_mode >= 0) want |= 8;
            else if (final_obj && (snap_flags & MF_XPMEM)) want |= 4;
            else want |= 2;
        }
    }
    if (r.action != want || r.phys != (old & PHYS_MASK) || r.calls != !fileoff ||
            r.order_failure || !r.page_is_expected || r.free_after != final_free ||
            r.has_memobj_after != final_obj ||
            r.fileoff != ((options & 2) ? fileoff : -1234)) {
        fprintf(stderr, "semantic mismatch case=%lu action=%d expected=%d mode=%d\n",
                cases, r.action, want, page_mode);
        assert(0);
    }
    digest = (digest ^ (unsigned long)(r.action + 17 * r.calls + 31 * (options + 1))) * 0x100000001b3UL;
    digest = (digest ^ r.phys) * 0x100000001b3UL;
    ++cases;
}
int main(void)
{
    const size_t sizes[] = {4096, 2097152, 1073741824, 8192};
    const unsigned long physical[] = {0, 0x12345000, 0xfffffffffffff000UL};
    const int free_values[] = {0, 1, -7};
    const unsigned flags[] = {0, MF_ZEROFILL, MF_PRIVATE, MF_XPMEM,
        MF_ZEROFILL | MF_PRIVATE, MF_ZEROFILL | MF_XPMEM,
        MF_PRIVATE | MF_XPMEM, MF_ZEROFILL | MF_PRIVATE | MF_XPMEM, 0x80001000U};
    const int modes[] = {-1, 0, 1, 2, 3, 4, 5, 6, 7, 8, 255};
    for (size_t s=0; s<sizeof(sizes)/sizeof(*sizes); ++s)
    for (size_t p=0; p<sizeof(physical)/sizeof(*physical); ++p)
    for (int fileoff=0; fileoff<2; ++fileoff)
    for (int dirty=0; dirty<2; ++dirty)
    for (size_t f=0; f<sizeof(free_values)/sizeof(*free_values); ++f)
    for (size_t b=0; b<sizeof(flags)/sizeof(*flags); ++b)
    for (int has_obj=0; has_obj<2; ++has_obj)
    for (size_t m=0; m<sizeof(modes)/sizeof(*modes); ++m)
    for (int outputs=0; outputs<4; ++outputs)
        check(physical[p] | 1 | ((unsigned long)fileoff << 11) |
                ((unsigned long)dirty << 6), sizes[s], free_values[f],
                flags[b], has_obj, modes[m], outputs, 0);
    /* Callback effects distinguish the original flag snapshot from later args reads. */
    for (int mutation=1; mutation<=5; ++mutation)
    for (int fileoff=0; fileoff<2; ++fileoff)
    for (int f=0; f<2; ++f)
    for (size_t b=0; b<sizeof(flags)/sizeof(*flags); ++b)
    for (int has_obj=0; has_obj<2; ++has_obj)
    for (size_t m=0; m<sizeof(modes)/sizeof(*modes); ++m)
    for (int outputs=0; outputs<4; ++outputs)
        check(0x12345041 | ((unsigned long)fileoff << 11), 4096,
                f, flags[b], has_obj, modes[m], outputs, mutation);
    printf("clear_range_old_action actual-C/Rust ok cases=%lu digest=%016lx\n", cases, digest);
    return 0;
}
