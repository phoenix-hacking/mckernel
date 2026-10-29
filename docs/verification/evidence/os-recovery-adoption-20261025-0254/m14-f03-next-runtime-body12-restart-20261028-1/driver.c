/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Genuine debug macro and scalar mocked printing; no registration/OS effects. */
#include <types.h>
#include <kmsg.h>
#include <ihk/debug.h>
#include <stdarg.h>
/* Test link alias preserves the C identifier and therefore its actual __func__. */
void syscall_util_register_desc_log_bridge(int,unsigned long) __asm__("c_reference_syscall_util_register_desc_log_bridge");
#include "original.fixture.C.inc"
#include "binding.fixture.C.inc"
extern void rust_util_register_desc_logger(int,unsigned long) __asm__("syscall_util_register_desc_log_bridge");
typedef void (*descriptor_logger_t)(int,unsigned long);
#include "abi.C.inc"
extern const unsigned long F03_UTIL_DESC_LOG_ABI[10];
extern struct ddebug __start___verbose[],__stop___verbose[];
extern int puts(const char *);
static struct ddebug *original_debug;
static unsigned char saved_original[sizeof(struct ddebug)],saved_candidate[sizeof f03_util_register_desc_debug_v1];
static int expected_tid;
static unsigned long expected_descriptor;
static unsigned expected_calls,calls,invalid;

int kprintf(const char *format,...)
{
    ++calls;
    if(!expected_calls || __builtin_strcmp(format,"%s: tid=%d,uti_desc=%lx\n")) {invalid=1;return -1;}
    va_list args;va_start(args,format);
    if(__builtin_strcmp(va_arg(args,const char *),"sys_util_register_desc"))invalid=1;
    if(va_arg(args,int)!=expected_tid)invalid=1;
    if(va_arg(args,unsigned long)!=expected_descriptor)invalid=1;
    va_end(args);return expected_tid?(-0x7fffffff-1):0x7fffffff;
}

static int discover(void)
{
    unsigned count=0;
    for(struct ddebug *record=__start___verbose;record<__stop___verbose;record++) {
        ++count;
        if(__builtin_strcmp(record->file,"kernel/syscall.c") || __builtin_strcmp(record->func,"syscall_util_register_desc_log_bridge") || record->fmt || record->flags || record->line!=EXPECTED_DEBUG_LINE)return 1;
        if(record!=f03_util_register_desc_debug_v1) {if(original_debug)return 2;original_debug=record;}
    }
    return count!=2 || !original_debug;
}

static int one(unsigned flag,int tid,unsigned long descriptor,int rust)
{
    original_debug->flags=flag;f03_util_register_desc_debug_v1[0].flags=flag;
    __builtin_memcpy(saved_original,original_debug,sizeof saved_original);
    __builtin_memcpy(saved_candidate,f03_util_register_desc_debug_v1,sizeof saved_candidate);
    expected_tid=tid;expected_descriptor=descriptor;expected_calls=!!flag;calls=invalid=0;
    if(rust)rust_util_register_desc_logger(tid,descriptor);
    else syscall_util_register_desc_log_bridge(tid,descriptor);
    if(invalid || calls!=expected_calls)return 1;
    if(__builtin_memcmp(saved_original,original_debug,sizeof saved_original) || __builtin_memcmp(saved_candidate,f03_util_register_desc_debug_v1,sizeof saved_candidate))return 2;
    return 0;
}

int main(void)
{
    if(__builtin_memcmp(ABI_C,F03_UTIL_DESC_LOG_ABI,sizeof ABI_C))return 10;
    int metadata=discover();if(metadata)return 20+metadata;
    const unsigned flags[]={0,1,2,128,255};
    const int tids[]={0,1,-1,(-0x7fffffff-1),0x7fffffff};
    const unsigned long descriptors[]={0,1,0x7fffffffUL,0x80000000UL,0xffffffffUL,0x100000000UL,0x8000000000000000UL,~0UL};
    unsigned pairs=0;
    for(unsigned f=0;f<5;f++)for(unsigned t=0;t<5;t++)for(unsigned d=0;d<8;d++) {
        for(int rust=0;rust<2;rust++) {int rc=one(flags[f],tids[t],descriptors[d],rust);if(rc)return 30+rc;}
        ++pairs;
    }
    if(pairs!=200)return 40;
    puts("PASS util-desc-log genuine-header ABI10; exact lexical metadata pair; 200 C/Rust pairs; debug-gate/int-TID/unsigned-descriptor/global-symbol/full-record oracles");
    return 0;
}
