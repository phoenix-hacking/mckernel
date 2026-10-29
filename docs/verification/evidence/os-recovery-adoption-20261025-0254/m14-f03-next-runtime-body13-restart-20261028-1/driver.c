/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * New Rust-owned debug storage plus unchanged BODY12 Rust logger object.
 * All printing and dynamic-debug updates are local HOST fixture effects. */
#include <types.h>
#include <kmsg.h>
#include <ihk/debug.h>
#include <stdarg.h>
void syscall_util_register_desc_log_bridge(int,unsigned long) __asm__("c_reference_syscall_util_register_desc_log_bridge");
#include "original.fixture.C.inc"
#include "storage-consumer.C.inc"
extern void rust_util_register_desc_logger(int,unsigned long) __asm__("syscall_util_register_desc_log_bridge");
extern const unsigned long F03_UTIL_DESC_LOG_ABI[10];
extern struct ddebug __start___verbose[],__stop___verbose[];
extern int puts(const char *);
typedef void (*descriptor_logger_t)(int,unsigned long);
static struct ddebug *original_debug;
static unsigned char initial_original[sizeof(struct ddebug)],initial_Rust_storage[sizeof(struct ddebug)];
static unsigned char saved_original[sizeof(struct ddebug)],saved_Rust_storage[sizeof(struct ddebug)];
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
    va_end(args);return -5;
}

static int discover(void)
{
    unsigned count=0;
    for(struct ddebug *record=__start___verbose;record<__stop___verbose;record++) {
        ++count;
        if(__builtin_strcmp(record->file,EXPECTED_SOURCE_FILE) || __builtin_strcmp(record->func,"syscall_util_register_desc_log_bridge") || record->fmt || record->flags || record->line!=EXPECTED_DEBUG_LINE)return 1;
        unsigned padding;
        __builtin_memcpy(&padding,(unsigned char *)record+28,sizeof padding);
        if(padding)return 2;
        if(record!=f03_util_register_desc_debug_v1) {if(original_debug)return 3;original_debug=record;}
    }
    if(count!=2 || !original_debug)return 4;
    __builtin_memcpy(initial_original,original_debug,sizeof initial_original);
    __builtin_memcpy(initial_Rust_storage,f03_util_register_desc_debug_v1,sizeof initial_Rust_storage);
    return 0;
}

static int one(unsigned flag,int rust)
{
    original_debug->flags=flag;f03_util_register_desc_debug_v1[0].flags=flag;
    unsigned original_word,Rust_word;
    __builtin_memcpy(&original_word,(unsigned char *)original_debug+24,sizeof original_word);
    __builtin_memcpy(&Rust_word,(unsigned char *)f03_util_register_desc_debug_v1+24,sizeof Rust_word);
    if(original_word!=(EXPECTED_DEBUG_LINE|(flag<<24)) || Rust_word!=original_word)return 1;
    __builtin_memcpy(saved_original,original_debug,sizeof saved_original);
    __builtin_memcpy(saved_Rust_storage,f03_util_register_desc_debug_v1,sizeof saved_Rust_storage);
    expected_tid=(flag&1)?(-0x7fffffff-1):0;expected_descriptor=(flag&1)?~0UL:0x100000000UL;
    expected_calls=!!flag;calls=invalid=0;
    if(rust)rust_util_register_desc_logger(expected_tid,expected_descriptor);
    else syscall_util_register_desc_log_bridge(expected_tid,expected_descriptor);
    if(invalid || calls!=expected_calls)return 2;
    if(__builtin_memcmp(saved_original,original_debug,sizeof saved_original) || __builtin_memcmp(saved_Rust_storage,f03_util_register_desc_debug_v1,sizeof saved_Rust_storage))return 3;
    return 0;
}
int main(void)
{
    const unsigned long ABI_C[10]={sizeof(struct ddebug),__alignof__(struct ddebug),
        __builtin_offsetof(struct ddebug,file),__builtin_offsetof(struct ddebug,func),__builtin_offsetof(struct ddebug,fmt),
        __builtin_offsetof(struct ddebug,fmt)+sizeof(const char *),sizeof(int),sizeof(unsigned long),
        sizeof(descriptor_logger_t),sizeof f03_util_register_desc_debug_v1/sizeof(struct ddebug)};
    if(__builtin_memcmp(ABI_C,F03_UTIL_DESC_LOG_ABI,sizeof ABI_C) || sizeof(struct ddebug)!=32)return 10;
    int metadata=discover();if(metadata)return 20+metadata;
    unsigned pairs=0;
    for(unsigned flag=0;flag<256;flag++) {
        for(int rust=0;rust<2;rust++) {int result=one(flag,rust);if(result)return 30+result;}
        ++pairs;
    }
    original_debug->flags=0;f03_util_register_desc_debug_v1[0].flags=0;
    if(__builtin_memcmp(initial_original,original_debug,sizeof initial_original) || __builtin_memcmp(initial_Rust_storage,f03_util_register_desc_debug_v1,sizeof initial_Rust_storage))return 40;
    if(pairs!=256)return 41;
    puts("PASS Rust-owned util-desc debug storage; ABI10 reused; 256 C/Rust flag pairs; exact symbol/metadata/flags/full-record oracles");
    return 0;
}
