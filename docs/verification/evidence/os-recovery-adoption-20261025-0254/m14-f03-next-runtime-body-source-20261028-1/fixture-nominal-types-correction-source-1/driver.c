/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * HOST-only mapping provider records calls; no syscall/PMU/guest effects. */
#include <types.h>
#include <kmsg.h>
#include <ihk/cpu.h>
#include <cpulocal.h>
#include <errno.h>
#include <cls.h>
#include <syscall.h>
#include <ihk/lock.h>
#include <process.h>
#include <ihk/debug.h>
#include <mc_perf_event.h>
#include <mman.h>
#include <ihk/memconst.h>

typedef intptr_t (*perf_do_mmap_fn_t)(uintptr_t addr, size_t len, int prot,
        int flags, int fd, off_t off, const int vrf0, void *private_data);
extern long perf_mmap_body_result(unsigned long,size_t,int,int,int,long,int,int,
                                size_t,size_t,unsigned long,perf_do_mmap_fn_t);
static unsigned calls;
static unsigned long recorded[8];
static long outcome;
intptr_t do_mmap(uintptr_t addr,size_t len,int prot,int flags,int fd,off_t off,
             int vrf0,void *private_data)
{
    ++calls;
    recorded[0]=addr; recorded[1]=len; recorded[2]=(unsigned long)(long)prot;
    recorded[3]=(unsigned long)(long)flags; recorded[4]=(unsigned long)(long)fd;
    recorded[5]=(unsigned long)off; recorded[6]=(unsigned long)(long)vrf0;
    recorded[7]=(unsigned long)private_data;
    return outcome;
}
#include "../perf-mmap-binding.C.inc"
#undef perf_mmap
#define perf_mmap c_reference_perf_mmap
#include "../perf-mmap-original.C.inc"
#undef perf_mmap
static long (*selected_callback)(struct mckfd *,ihk_mc_user_context_t *) = f03_perf_mmap_v1;
extern const unsigned long F03_PERF_MMAP_ABI[18];
extern int puts(const char *);

static int one(ihk_mc_user_context_t *ctx,long error,unsigned long initial_cap,
               int use_rust,struct perf_event_mmap_page *page)
{
    unsigned char saved_context[sizeof(*ctx)],expected[sizeof(*page)];
    unsigned long expected_args[8]={ctx->gpr.rdi,ctx->gpr.rsi,
        (unsigned long)(long)((int)ctx->gpr.rdx|PROT_WRITE),
        (unsigned long)(long)((int)ctx->gpr.r10|MAP_ANONYMOUS),
        (unsigned long)(long)(int)ctx->gpr.r8,ctx->gpr.r9,0,0};
    __builtin_memset(page,0xa5,sizeof(*page));
    page->capabilities=initial_cap;
    __builtin_memcpy(expected,page,sizeof(*page));
    __builtin_memcpy(saved_context,ctx,sizeof(*ctx));
    if(!error) {
        unsigned long head=16,cap=initial_cap|(1UL<<2);
        __builtin_memcpy(expected+__builtin_offsetof(struct perf_event_mmap_page,data_head),&head,sizeof(head));
        __builtin_memcpy(expected+__builtin_offsetof(struct perf_event_mmap_page,capabilities),&cap,sizeof(cap));
    }
    calls=0; outcome=error?error:(long)page;
    long result=use_rust?selected_callback(NULL,ctx):c_reference_perf_mmap(NULL,ctx);
    if(result!=outcome || calls!=1)return 1;
    if(__builtin_memcmp(recorded,expected_args,sizeof recorded))return 2;
    if(__builtin_memcmp(page,expected,sizeof(*page)))return 3;
    if(__builtin_memcmp(ctx,saved_context,sizeof(*ctx)))return 4;
    return 0;
}
int main(void)
{
    const unsigned long abi[18]={sizeof(ihk_mc_user_context_t),__alignof__(ihk_mc_user_context_t),
        __builtin_offsetof(ihk_mc_user_context_t,gpr.rdi),__builtin_offsetof(ihk_mc_user_context_t,gpr.rsi),
        __builtin_offsetof(ihk_mc_user_context_t,gpr.rdx),__builtin_offsetof(ihk_mc_user_context_t,gpr.r10),
        __builtin_offsetof(ihk_mc_user_context_t,gpr.r8),__builtin_offsetof(ihk_mc_user_context_t,gpr.r9),
        sizeof(struct f03_perf_mmap_binding),__alignof__(struct f03_perf_mmap_binding),
        __builtin_offsetof(struct f03_perf_mmap_binding,map_anonymous),
        __builtin_offsetof(struct f03_perf_mmap_binding,prot_write),
        __builtin_offsetof(struct f03_perf_mmap_binding,data_head),
        __builtin_offsetof(struct f03_perf_mmap_binding,capabilities),
        __builtin_offsetof(struct f03_perf_mmap_binding,cap_user_rdpmc),
        __builtin_offsetof(struct f03_perf_mmap_binding,do_mmap),
        sizeof(perf_do_mmap_fn_t),sizeof(selected_callback)};
    if(__builtin_memcmp(abi,F03_PERF_MMAP_ABI,sizeof abi))return 10;
    const unsigned long words[]={0,1,0x7fffffffUL,0x80000000UL,0xffffffffUL,
        0x100000000UL,0x8000000000000000UL,~0UL};
    const long errors[]={0,-1,-12,-22,-4095};
    const unsigned long caps[]={0,4,~0UL,0x123456789abcdef0UL};
    struct { unsigned long before; struct perf_event_mmap_page page; unsigned long after; } area;
    unsigned pairs=0;
    for(unsigned i=0;i<8;i++)for(unsigned e=0;e<5;e++)for(unsigned c=0;c<4;c++) {
        ihk_mc_user_context_t ctx;
        __builtin_memset(&ctx,0x5a,sizeof ctx);
        ctx.gpr.rdi=words[i];ctx.gpr.rsi=words[(i+1)%8];ctx.gpr.rdx=words[(i+2)%8];
        ctx.gpr.r10=words[(i+3)%8];ctx.gpr.r8=words[(i+4)%8];ctx.gpr.r9=words[(i+5)%8];
        area.before=0x123456789abcdef0UL;area.after=~area.before;
        for(unsigned r=0;r<2;r++) {
            int result=one(&ctx,errors[e],caps[c],r,&area.page);
            if(result)return 20+result;
            if(area.before!=0x123456789abcdef0UL || area.after!=~area.before)return 30;
        }
        ++pairs;
    }
    if(pairs!=160)return 31;
    puts("PASS perf-mmap actual-context ABI18; 160 C/Rust pairs; 320 exact-call/context/full-page/canary oracles");
    return 0;
}
