/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Full-signature original selected-C vs new Rust export; actual context headers.
 * Existing ptrace event internals are a controlled synchronous trace callback. */
#include <ihk/context.h>
extern int printf(const char *, ...);
extern void abort(void);
#define CHECK(x) do { if (!(x)) { printf("FAIL line=%d\n", __LINE__); abort(); } } while (0)
#define WORD_MIN (-__LONG_MAX__ - 1L)
#define WORD_MAX __LONG_MAX__
_Static_assert(sizeof(long)==8 && sizeof(int)==4 && sizeof(void *)==8,"x86 LP64 ABI");
#include "public-declaration.ACTUAL-HEADER.inc"
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_ptrace_syscall_event),long (*)(struct thread *,ihk_mc_user_context_t *,long)),"actual kernel public prototype");
typedef void (*arch_ptrace_syscall_event_fn_t)(void *,int);
extern long arch_ptrace_syscall_event_body_result(void *,void *,long,size_t,arch_ptrace_syscall_event_fn_t);
#include "original-context-providers.ACTUAL-BODY.inc"
static ihk_mc_user_context_t *active_ctx;
static struct thread *expected_thread;
static long expected_setret, replacement;
static int mutate, callbacks;
void ptrace_syscall_event(struct thread *thread)
{
    CHECK(thread==expected_thread);
    CHECK(callbacks==0);
    callbacks++;
    if (active_ctx) {
        CHECK(active_ctx->gpr.rax==(unsigned long)expected_setret);
        if (mutate) active_ctx->gpr.rax=(unsigned long)replacement;
    }
}
#include "original-adapter.ACTUAL-BODY.inc"
#define MCKERNEL_RUST_SYSCALL_POLICY_HELPERS 1
#define arch_ptrace_syscall_event original_selected_entry
#include "original-entry.ACTUAL-BODY.inc"
#undef arch_ptrace_syscall_event
/* Actual default selection excludes the complete C entry: link uses Rust T. */
#include "candidate-entry.ACTUAL-BLOCK.inc"
#undef MCKERNEL_RUST_SYSCALL_POLICY_HELPERS
#define arch_ptrace_syscall_event original_fallback_entry
#include "candidate-entry.ACTUAL-BLOCK.inc"
#undef arch_ptrace_syscall_event
extern size_t fixture_context_size(void);
extern size_t fixture_context_align(void);
extern size_t fixture_rax_offset(void);
struct guarded { unsigned long before[2]; ihk_mc_user_context_t ctx; unsigned long after[2]; };
static void fill(struct guarded *g,unsigned char pattern)
{unsigned char *p=(void *)g;for(size_t i=0;i<sizeof *g;i++)p[i]=pattern;}
static int equal(const void *a,const void *b,size_t size)
{const unsigned char *x=a,*y=b;for(size_t i=0;i<size;i++)if(x[i]!=y[i])return 0;return 1;}
static long invoke(long (*fn)(struct thread *,ihk_mc_user_context_t *,long),struct guarded *g,struct thread *t,long setret)
{active_ctx=g?&g->ctx:0;expected_thread=t;expected_setret=setret;callbacks=0;return fn(t,active_ctx,setret);}
int main(void)
{
    CHECK(fixture_context_size()==sizeof(ihk_mc_user_context_t));
    CHECK(fixture_context_align()==__alignof__(ihk_mc_user_context_t));
    CHECK(fixture_rax_offset()==__builtin_offsetof(ihk_mc_user_context_t,gpr.rax));
    unsigned long tokens[2]={0x1234,0x5678};
    struct thread *threads[]={0,(struct thread *)&tokens[0],(struct thread *)&tokens[1]};
    const long words[]={WORD_MIN,-95,-14,-1,0,37,WORD_MAX};
    unsigned vectors=0,null_vectors=0;
    for(unsigned i=0;i<7;i++)for(unsigned j=0;j<7;j++)for(unsigned k=0;k<3;k++)
    for(unsigned m=0;m<2;m++)for(unsigned p=0;p<2;p++) {
        struct guarded c,r,f,expected;unsigned char pattern=p?0x5a:0xa5;
        fill(&c,pattern);fill(&r,pattern);fill(&f,pattern);fill(&expected,pattern);
        mutate=m;replacement=words[j];
        long cr=invoke(original_selected_entry,&c,threads[k],words[i]);CHECK(callbacks==1);
        long rr=invoke(arch_ptrace_syscall_event,&r,threads[k],words[i]);CHECK(callbacks==1);
        long fr=invoke(original_fallback_entry,&f,threads[k],words[i]);CHECK(callbacks==1);
        expected.ctx.gpr.rax=(unsigned long)(m?words[j]:words[i]);
        CHECK(cr==rr && rr==fr && rr==(long)expected.ctx.gpr.rax);
        CHECK(equal(&c,&r,sizeof c)&&equal(&r,&f,sizeof r)&&equal(&r,&expected,sizeof r));
        CHECK(tokens[0]==0x1234 && tokens[1]==0x5678);vectors++;
    }
    for(unsigned i=0;i<7;i++)for(unsigned k=0;k<3;k++) {
        long c=invoke(original_selected_entry,0,threads[k],words[i]);CHECK(c==-14 && callbacks==0);
        long r=invoke(arch_ptrace_syscall_event,0,threads[k],words[i]);CHECK(r==c && callbacks==0);
        long f=invoke(original_fallback_entry,0,threads[k],words[i]);CHECK(f==0 && callbacks==1);null_vectors++;
    }
    CHECK(vectors==588 && null_vectors==21);
    printf("PASS_ARCH_PTRACE_SYSCALL_EVENT actual_vectors=%u null_vectors=%u store_event_reread=1 actual_context_ABI=1 default_Rust_entry=1 fallback_preserved=1\n",vectors,null_vectors);
    return 0;
}
