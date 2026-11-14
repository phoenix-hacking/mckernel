/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Real C debug macro/type; exact original providers and exact extracted Rust bodies.
 * Downstream page free is controlled: no physical allocation/free proof.
 */
#include <assert.h>
#include <limits.h>
#include <stdint.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "EXACT-REAL-C-DEBUG-CLOSURE.inc"
const char x86_pt_free_pages_file[] = __FILE__;
const int x86_pt_free_pages_line = 807;
const int x86_pt_free_pages_flag = IHK_MC_PG_KERNEL;
struct ddebug __aligned(8) __attribute__((section("__verbose")))
x86_clear_effect_child_free_debug = {
    .file = __FILE__, .func = "x86_clear_effect_log_bridge", .fmt = NULL,
    .line = 1391, .flags = DDEBUG_DEFAULT,
};
struct ddebug __aligned(8) __attribute__((section("__verbose")))
x86_clear_effect_free_anon_debug = {
    .file = __FILE__, .func = "x86_clear_effect_log_bridge", .fmt = NULL,
    .line = 1380, .flags = DDEBUG_DEFAULT,
};
struct ddebug __aligned(8) __attribute__((section("__verbose")))
x86_clear_effect_free_unmapped_debug = {
    .file = __FILE__, .func = "x86_clear_effect_log_bridge", .fmt = NULL,
    .line = 1387, .flags = DDEBUG_DEFAULT,
};
struct ddebug __aligned(8) __attribute__((section("__verbose")))
x86_clear_effect_xpmem_keep_debug = {
    .file = __FILE__, .func = "x86_clear_effect_log_bridge", .fmt = NULL,
    .line = 1384, .flags = DDEBUG_DEFAULT,
};
struct ddebug __aligned(8) __attribute__((section("__verbose")))
x86_clear_range_large_phys_debug = {
    .file = __FILE__, .func = "x86_clear_range_log_bridge", .fmt = NULL,
    .line = 1446, .flags = DDEBUG_DEFAULT,
};
#define X86_MEMORY_PUBLIC_BRIDGE static
extern void rust_ptfree(void*,int) __asm__("x86_pt_free_pages_bridge");
extern void rust_effect(int,unsigned long,unsigned long,size_t) __asm__("x86_clear_effect_log_bridge");
extern void rust_range(int,void*,unsigned long*,unsigned long,unsigned long,unsigned long,int,int,unsigned long) __asm__("x86_clear_range_log_bridge");
static void x86_pt_free_pages_bridge(void*,int) __asm__("original_C_ptfree");
static void x86_clear_effect_log_bridge(int,unsigned long,unsigned long,size_t) __asm__("original_C_effect");
static void x86_clear_range_log_bridge(int,void*,unsigned long*,unsigned long,unsigned long,unsigned long,int,int,unsigned long) __asm__("original_C_range");
static struct free_event {void *ptr; int pages,flag; char *file; int line;} seen_free;
static unsigned free_calls,log_calls;
static int logger_return;
static char log_text[1024];
void _ihk_mc_free_pages(void *p,int n,int f,char *file,int line)
{ ++free_calls; seen_free=(struct free_event){p,n,f,file,line}; }
int kprintf(const char *format,...)
{
    va_list ap;va_start(ap,format);++log_calls;
    int n=vsnprintf(log_text,sizeof(log_text),format,ap);va_end(ap);
    assert(n>=0 && (unsigned)n<sizeof(log_text));return logger_return;
}
#line 805
X86_MEMORY_PUBLIC_BRIDGE void x86_pt_free_pages_bridge(void *pt, int nr_pages)
{
	_ihk_mc_free_pages(pt, nr_pages, IHK_MC_PG_KERNEL, __FILE__, __LINE__);
}
#line 1375
static void x86_clear_effect_log_bridge(int event, unsigned long base,
		unsigned long phys, size_t pgsize)
{
	switch (event) {
	case X86_CLEAR_EFFECT_FREE_ANON:
		dkprintf("%lx-,%s: freed anonymous page,base=%lx,size=%ld,pgsize=%ld\n",
				phys, __FUNCTION__, base, pgsize, pgsize);
		break;
	case X86_CLEAR_EFFECT_XPMEM_KEEP:
		dkprintf("%s: XPMEM attach,phys=%lx\n", __FUNCTION__, phys);
		break;
	case X86_CLEAR_EFFECT_FREE_UNMAPPED:
		dkprintf("%lx-,%s: freed unmapped memobj page,base=%lx,size=%ld,pgsize=%ld\n",
				phys, __FUNCTION__, base, pgsize, pgsize);
		break;
	case X86_CLEAR_EFFECT_CHILD_FREE:
		dkprintf("%s: freed child page table at base=%lx,size=%ld\n",
				__FUNCTION__, base, pgsize);
		break;
	default:
		break;
	}
}
#line 1421
static void x86_clear_range_log_bridge(int event, void *args,
		unsigned long *ptep, unsigned long base, unsigned long start,
		unsigned long end, int error, int level_shift, unsigned long phys)
{
	const char *fn;

	switch (level_shift) {
	case PTL2_SHIFT:
		fn = "clear_range_l2";
		break;
	case PTL3_SHIFT:
		fn = "clear_range_l3";
		break;
	default:
		fn = "clear_range_l4";
		break;
	}

	switch (event) {
	case X86_CLEAR_RANGE_LOG_SPLIT:
		ekprintf("%s(%p,%p,%lx,%lx,%lx):"
				"split page. %d\n",
				fn, args, ptep, base, start, end, error);
		break;
	case X86_CLEAR_RANGE_LOG_LARGE_PHYS:
		dkprintf("%s: phys=%ld, pte_get_phys(&old),PTL3_SIZE\n",
				fn, phys);
		break;
	default:
		break;
	}
}

extern struct ddebug __start___verbose[],__stop___verbose[];
static const char *const selector_func[]={"x86_clear_effect_log_bridge","x86_clear_effect_log_bridge","x86_clear_effect_log_bridge","x86_clear_effect_log_bridge","x86_clear_range_log_bridge"};
static const unsigned selector_line[]={1380,1384,1387,1391,1446};
static void select_flags(const unsigned flags[5])
{
    unsigned hits[5]={0};
    for(struct ddebug *d=__start___verbose;d<__stop___verbose;++d) {
        assert(d->fmt==NULL && strcmp(d->file,x86_pt_free_pages_file)==0);
        unsigned i;
        for(i=0;i<5;++i)if(d->line==selector_line[i] && strcmp(d->func,selector_func[i])==0)break;
        assert(i<5);d->flags=flags[i];assert(d->line==selector_line[i]);++hits[i];
    }
    for(unsigned i=0;i<5;++i)assert(hits[i]==2);
}
static void reset_log(void) { log_calls=0;strcpy(log_text,"<NO OUTPUT>"); }
static unsigned char observer_owned[8192] __attribute__((aligned(4096)));
int main(void)
{
    _Static_assert(sizeof(struct ddebug)==32 && _Alignof(struct ddebug)==8,"actual C descriptor ABI");
    unsigned flagsets[22][5]={{0}},configs=1;
    static const unsigned enabled[]={1,2,128,255};
    for(unsigned d=0;d<5;++d)for(unsigned v=0;v<4;++v)flagsets[configs++][d]=enabled[v];
    for(unsigned d=0;d<5;++d)flagsets[configs][d]=255;
    ++configs;assert(configs==22);
    unsigned zero[5]={0};select_flags(zero);
    static const int pages[]={INT_MIN,-2,-1,0,1,2,8,511,INT_MAX};
    void *pointers[]={NULL,observer_owned,observer_owned+4096,(void*)(uintptr_t)1,(void*)(uintptr_t)UINTPTR_MAX};
    unsigned free_pairs=0,effect_pairs=0,range_pairs=0;
    for(unsigned i=0;i<9;++i)for(unsigned j=0;j<5;++j) {
        unsigned before=free_calls,logs=log_calls;
        x86_pt_free_pages_bridge(pointers[j],pages[i]);struct free_event expected=seen_free;
        assert(free_calls==before+1);rust_ptfree(pointers[j],pages[i]);
        assert(free_calls==before+2 && log_calls==logs);
        assert(seen_free.ptr==expected.ptr && seen_free.pages==expected.pages && seen_free.flag==expected.flag);
        assert(strcmp(seen_free.file,expected.file)==0 && seen_free.line==expected.line);
        assert(seen_free.ptr==pointers[j] && seen_free.pages==pages[i] && seen_free.flag==0 && seen_free.line==807);
        assert(seen_free.file==x86_pt_free_pages_file);++free_pairs;
    }
    static const unsigned long values[]={0,0x123456789abcdef0UL,ULONG_MAX};
    static const int errors[]={0,-7,INT_MIN};
    static const int events[]={2,3,4,5,INT_MIN,INT_MAX};
    static const int range_events[]={8,9,INT_MIN,INT_MAX},levels[]={21,30,12,-1};
    for(unsigned cfg=0;cfg<configs;++cfg) {
        select_flags(flagsets[cfg]);
        for(unsigned event=0;event<6;++event)for(unsigned v=0;v<3;++v) {
            unsigned before=free_calls;logger_return=errors[v];reset_log();
            x86_clear_effect_log_bridge(events[event],values[v],values[2-v],values[v]);
            unsigned calls=log_calls;char expected[1024];strcpy(expected,log_text);
            unsigned should=event<4 && flagsets[cfg][event]!=0;
            assert(calls==should);reset_log();
            rust_effect(events[event],values[v],values[2-v],values[v]);
            assert(log_calls==calls && strcmp(log_text,expected)==0 && free_calls==before);++effect_pairs;
        }
        for(unsigned event=0;event<4;++event)for(unsigned level=0;level<4;++level)for(unsigned v=0;v<3;++v) {
            void *args=pointers[v];unsigned long *pte=(unsigned long*)pointers[4-v];
            unsigned before=free_calls;logger_return=errors[v];reset_log();
            x86_clear_range_log_bridge(range_events[event],args,pte,values[v],values[2-v],values[v],errors[v],levels[level],values[2-v]);
            unsigned calls=log_calls;char expected[1024];strcpy(expected,log_text);
            unsigned should=event==0 || (event==1 && flagsets[cfg][4]!=0);
            assert(calls==should);reset_log();
            rust_range(range_events[event],args,pte,values[v],values[2-v],values[v],errors[v],levels[level],values[2-v]);
            assert(log_calls==calls && strcmp(log_text,expected)==0 && free_calls==before);++range_pairs;
        }
    }
    select_flags(zero);
    assert(free_pairs==45 && effect_pairs==396 && range_pairs==1056);
    puts("PASS PTfree/loggers:1497 actual-original-C/Rust pairs (45 free,396 effect,1056 range);10 real selectors;downstream free controlled");
    return 0;
}
