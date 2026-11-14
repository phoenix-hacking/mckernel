/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Exact production C body/entry adapters are included below; the actual existing
 * Rust top helper is shared so the comparison isolates newly moved behavior.
 */
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
struct page_table;
typedef struct page_table *page_table_t;
struct process {
    unsigned char prefix[1624];
    void *straight_va;
    size_t straight_len;
    unsigned char suffix[88];
} __attribute__((aligned(64)));
struct vm_regions { unsigned long unused[13], user_start, user_end; };
struct process_vm {
    void *address_space, *vm_range_tree;
    struct vm_regions region;
    struct process *proc;
    unsigned char suffix[160];
};
struct memobj {
    void *ops;
    uint32_t flags, status;
    size_t size;
    int refcnt, padding;
    void **pages;
    int nr_pages, padding2;
    char *path;
};
struct clear_range_args {
    int free_physical;
    struct memobj *memobj;
    struct process_vm *vm;
    unsigned long *addr;
    int nr_addr, max_nr_addr;
};
#define MF_DEV_FILE 0x2000U
#define MF_PREMAP 0x8000U
#define PAGE_SIZE 4096UL
#define TLB_INVALID_ARRAY_PAGES 4
_Static_assert(sizeof(struct process) == 1728 && _Alignof(struct process) == 64, "Process ABI");
_Static_assert(offsetof(struct process, straight_va) == 1624 && offsetof(struct process, straight_len) == 1632, "straight mapping ABI");
_Static_assert(sizeof(struct process_vm) == 304 && offsetof(struct process_vm, proc) == 136, "ProcessVm ABI");
_Static_assert(offsetof(struct process_vm, region) == 16 && offsetof(struct vm_regions, user_start) == 104, "VM bounds ABI");
_Static_assert(sizeof(struct memobj) == 56 && offsetof(struct memobj, flags) == 8, "Memobj ABI");
_Static_assert(sizeof(struct clear_range_args) == 40, "range args ABI");
typedef void *(*alloc_fn_t)(int, int);
typedef void (*free_fn_t)(void *, int);
typedef int (*walk_fn_t)(void *, unsigned long, unsigned long, unsigned long, void *);
typedef void (*flush_fn_t)(void *, unsigned long *, int, int);
typedef flush_fn_t x86_clear_remote_flush_fn_t;
typedef void (*log_fn_t)(int, void *, unsigned long, unsigned long, int);
extern int x86_clear_range_top_result(void *, void *, unsigned long, unsigned long,
        unsigned long, unsigned long, int, int, int, int, void *, unsigned long **,
        int *, int *, int *, void **, void **, int, unsigned long, void *,
        alloc_fn_t, free_fn_t, walk_fn_t, flush_fn_t, int, log_fn_t);
extern int ihk_mc_pt_clear_range(page_table_t, struct process_vm *, void *, void *);
extern int ihk_mc_pt_free_range(page_table_t, struct process_vm *, void *, void *, struct memobj *);
extern int x86_clear_range_public_body(void *, struct process_vm *, unsigned long,
        unsigned long, int, struct memobj *);
extern void fixture_set_debug(unsigned int);
static struct process proc;
static struct process_vm vm;
static struct memobj obj;
static unsigned long tlb[2048];
static int c_debug;
static struct {
    unsigned long start, end, trace;
    page_table_t pt;
    struct memobj *memobj;
    int mode, valid, alloc_fail, pending, walk_error, mutate, want_free;
    int cpu_calls, alloc_calls, walk_calls, flush_calls, free_calls, debug_calls;
    int allocated, observed_free, log_event;
} ctx;
static void event(unsigned long value) { ctx.trace = ctx.trace * 16 + value; }
int kprintf(const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    assert(strcmp(fmt, "%s: %p,%lx,%lx,%d,%p\n") == 0);
    assert(strcmp(va_arg(ap, const char *), "clear_range") == 0);
    assert(va_arg(ap, void *) == (void *)ctx.pt);
    assert(va_arg(ap, unsigned long) == ctx.start);
    assert(va_arg(ap, unsigned long) == ctx.end);
    assert(va_arg(ap, int) == ctx.mode);
    assert(va_arg(ap, void *) == (void *)ctx.memobj);
    va_end(ap);
    ++ctx.debug_calls; event(1); return 0;
}
#define dkprintf(...) do { if (c_debug) kprintf(__VA_ARGS__); } while (0)
int ihk_mc_get_processor_id(void) { ++ctx.cpu_calls; event(2); return 7; }
void *x86_pt_alloc_pages_bridge(int pages, int flag)
{
    assert(pages == 4 && flag == 1 && !ctx.allocated);
    ++ctx.alloc_calls; event(3);
    if (ctx.mutate) {
        obj.flags ^= 0xffffffffU;
        proc.straight_va = NULL; proc.straight_len = 0;
        vm.region.user_start = vm.region.user_end = 0;
    }
    if (ctx.alloc_fail) return NULL;
    ctx.allocated = 1; return tlb;
}
void x86_pt_free_pages_bridge(void *addr, int pages)
{
    assert(addr == tlb && pages == 4 && ctx.allocated);
    ctx.allocated = 0; ++ctx.free_calls; event(6);
}
int x86_clear_range_walk_l4_bridge(void *pt, unsigned long base,
        unsigned long start, unsigned long end, void *args0)
{
    struct clear_range_args *args = args0;
    assert(pt == ctx.pt && base == 0 && start == ctx.start && end == ctx.end);
    assert(args->vm == &vm && args->memobj == ctx.memobj && args->addr == tlb);
    assert(args->nr_addr == 0 && args->max_nr_addr == 2048);
    assert(args->free_physical == ctx.want_free && ctx.allocated);
    ctx.observed_free = args->free_physical;
    args->nr_addr = ctx.pending;
    for (int i=0; i<ctx.pending; ++i) args->addr[i] = 0x4000UL + (unsigned long)i * 4096;
    ++ctx.walk_calls; event(4); return ctx.walk_error;
}
void remote_flush_tlb_array_cpumask(void *target_vm, unsigned long *addr, int nr, int cpu)
{
    assert(target_vm == &vm && addr == tlb && nr == ctx.pending && cpu == 7);
    assert(ctx.allocated && nr > 0 && ctx.walk_calls == 1);
    for (int i=0; i<nr; ++i) assert(addr[i] == 0x4000UL + (unsigned long)i * 4096);
    ++ctx.flush_calls; event(5);
}
void x86_clear_range_top_log_bridge(int kind, void *pt, unsigned long start,
        unsigned long end, int free_physical)
{
    assert(pt == ctx.pt && start == ctx.start && end == ctx.end && free_physical == ctx.mode);
    ctx.log_event = kind; event(kind == 6 ? 7 : 8);
}
#define ihk_mc_pt_clear_range original_ihk_mc_pt_clear_range
#define ihk_mc_pt_free_range original_ihk_mc_pt_free_range
#include "original-clear-range.c.inc"
#undef ihk_mc_pt_clear_range
#undef ihk_mc_pt_free_range
#define x86_set_range_clear_bridge original_x86_set_range_clear_bridge
#include "original-set-range-clear.c.inc"
#undef x86_set_range_clear_bridge
#define MCKERNEL_RUST_X86_MEMORY_PUBLIC
#define x86_set_range_clear_bridge candidate_x86_set_range_clear_bridge
#include "candidate-set-range-clear.c.inc"
#undef x86_set_range_clear_bridge
#undef MCKERNEL_RUST_X86_MEMORY_PUBLIC
struct result { int error, cpu, alloc, walk, flush, freed, debug, observed_free, log; unsigned long trace; };
static struct result run(int rust, unsigned long start, unsigned long end,
        unsigned flags, int has_obj, int straight, int mode, int alloc_fail,
        int pending, int walk_error, int mutate, int debug)
{
    memset(&proc, 0, sizeof(proc)); memset(&vm, 0, sizeof(vm)); memset(&obj, 0, sizeof(obj));
    memset(&ctx, 0, sizeof(ctx));
    vm.proc = &proc; vm.region.user_start = 0x1000; vm.region.user_end = 0x10000;
    obj.flags = flags;
    switch (straight) {
    case 1: proc.straight_va = (void *)start; proc.straight_len = end-start; break;
    case 2: proc.straight_va = (void *)(start+4096); proc.straight_len = end-start; break;
    case 3: proc.straight_va = (void *)start; proc.straight_len = end-start+4096; break;
    case 4: proc.straight_va = (void *)start; proc.straight_len = 0; break;
    }
    ctx.start=start; ctx.end=end; ctx.pt=(page_table_t)0x1230;
    ctx.memobj = mode && has_obj ? &obj : NULL;
    int requested_free = mode == 0 || mode == 2 ? 0 : mode == 4 ? -7 : mode == 5 ? 2 : 1;
    ctx.mode=requested_free; ctx.valid=start >= 0x1000 && end <= 0x10000 && end > start;
    ctx.alloc_fail=alloc_fail; ctx.pending=pending; ctx.walk_error=walk_error; ctx.mutate=mutate;
    int full_straight = proc.straight_va && start == (unsigned long)proc.straight_va &&
            end == (unsigned long)proc.straight_va + proc.straight_len;
    ctx.want_free = requested_free && !(has_obj && (flags & (MF_DEV_FILE|MF_PREMAP))) && !full_straight;
    c_debug=debug; fixture_set_debug(debug ? 0xff : 0);
    int error;
    if (mode >= 2) error = rust
            ? candidate_x86_set_range_clear_bridge(ctx.pt,&vm,start,end,requested_free,ctx.memobj)
            : original_x86_set_range_clear_bridge(ctx.pt,&vm,start,end,requested_free,ctx.memobj);
    else if (mode) error = rust ? ihk_mc_pt_free_range(ctx.pt,&vm,(void *)start,(void *)end,ctx.memobj)
                          : original_ihk_mc_pt_free_range(ctx.pt,&vm,(void *)start,(void *)end,ctx.memobj);
    else error = rust ? ihk_mc_pt_clear_range(ctx.pt,&vm,(void *)start,(void *)end)
                      : original_ihk_mc_pt_clear_range(ctx.pt,&vm,(void *)start,(void *)end);
    assert(!ctx.allocated);
    assert(error == (!ctx.valid ? -22 : alloc_fail ? -12 : walk_error));
    assert(ctx.cpu_calls == 1 && ctx.debug_calls == !!debug);
    assert(ctx.alloc_calls == ctx.valid);
    assert(ctx.walk_calls == (ctx.valid && !alloc_fail));
    assert(ctx.free_calls == ctx.walk_calls);
    assert(ctx.flush_calls == (ctx.walk_calls && pending > 0));
    assert(ctx.log_event == (!ctx.valid ? 6 : alloc_fail ? 7 : 0));
    struct result r={error,ctx.cpu_calls,ctx.alloc_calls,ctx.walk_calls,ctx.flush_calls,
            ctx.free_calls,ctx.debug_calls,ctx.observed_free,ctx.log_event,ctx.trace};
    return r;
}
int main(void)
{
    const unsigned long ranges[][2]={{0x1000,0x2000},{0x1000,0x10000},{0,0x2000},
        {0x1000,0x11000},{0x2000,0x2000},{0x3000,0x2000},{0x2000,0x4000},{0xfffffffffffff000UL,~0UL}};
    const unsigned flags[]={0,MF_DEV_FILE,MF_PREMAP,MF_DEV_FILE|MF_PREMAP,0x200000,0x40000000U,~0U};
    const int pending[]={0,1,2048}, errors[]={0,-2,7};
    unsigned long cases=0,digest=0xcbf29ce484222325UL;
    for (size_t r=0;r<sizeof(ranges)/sizeof(*ranges);++r)
    for (int straight=0;straight<5;++straight)
    for (size_t f=0;f<sizeof(flags)/sizeof(*flags);++f)
    for (int obj_present=0;obj_present<2;++obj_present)
    for (int mode=0;mode<6;++mode)
    for (int fail=0;fail<2;++fail)
    for (size_t n=0;n<sizeof(pending)/sizeof(*pending);++n)
    for (size_t e=0;e<sizeof(errors)/sizeof(*errors);++e)
    for (int mutate=0;mutate<2;++mutate)
    for (int debug=0;debug<2;++debug) {
        struct result c=run(0,ranges[r][0],ranges[r][1],flags[f],obj_present,straight,mode,fail,pending[n],errors[e],mutate,debug);
        struct result rs=run(1,ranges[r][0],ranges[r][1],flags[f],obj_present,straight,mode,fail,pending[n],errors[e],mutate,debug);
        assert(c.error==rs.error && c.cpu==rs.cpu && c.alloc==rs.alloc && c.walk==rs.walk &&
                c.flush==rs.flush && c.freed==rs.freed && c.debug==rs.debug &&
                c.observed_free==rs.observed_free && c.log==rs.log && c.trace==rs.trace);
        digest=(digest ^ rs.trace)*0x100000001b3UL;
        digest=(digest ^ (unsigned long)rs.error)*0x100000001b3UL;
        ++cases;
    }
    printf("clear_range actual-C/Rust ok cases=%lu digest=%016lx\n",cases,digest);
    return 0;
}
