# 1 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
# 1 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1//"
# 1 "<built-in>"
# 1 "<command-line>"
# 1 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"


# 1 "/home/holden/mckernel/lib/include/types.h" 1
# 21 "/home/holden/mckernel/lib/include/types.h"
typedef _Bool bool;


# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/ihk/types.h" 1
# 17 "/home/holden/mckernel/arch/x86_64/kernel/include/ihk/types.h"
typedef unsigned char uint8_t;
typedef unsigned short uint16_t;
typedef unsigned int uint32_t;
typedef unsigned long long uint64_t;
typedef signed char int8_t;
typedef signed short int16_t;
typedef signed int int32_t;
typedef signed long long int64_t;

typedef int64_t ptrdiff_t;
typedef int64_t intptr_t;
typedef uint64_t uintptr_t;
typedef uint64_t size_t;
typedef int64_t ssize_t;
typedef int64_t off_t;

typedef int32_t key_t;
typedef uint32_t uid_t;
typedef uint32_t gid_t;
typedef int64_t time_t;
typedef int32_t pid_t;
# 25 "/home/holden/mckernel/lib/include/types.h" 2
# 4 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 2
# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/prctl.h" 1
# 5 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 2
# 1 "/home/holden/mckernel/lib/include/ihk/debug.h" 1



# 1 "/home/holden/mckernel/kernel/include/lwk/compiler.h" 1
# 60 "/home/holden/mckernel/kernel/include/lwk/compiler.h"
# 1 "/home/holden/mckernel/kernel/include/lwk/compiler-gcc.h" 1
# 61 "/home/holden/mckernel/kernel/include/lwk/compiler.h" 2
# 89 "/home/holden/mckernel/kernel/include/lwk/compiler.h"
struct ftrace_branch_data {
 const char *func;
 const char *file;
 unsigned line;
 union {
  struct {
   unsigned long correct;
   unsigned long incorrect;
  };
  struct {
   unsigned long miss;
   unsigned long hit;
  };
  unsigned long miss_hit[2];
 };
};

struct ftrace_likely_data {
 struct ftrace_branch_data data;
 unsigned long constant;
};
# 490 "/home/holden/mckernel/kernel/include/lwk/compiler.h"
extern void *memcpy(void *dest, const void *src, size_t n);

static inline __attribute__((always_inline,unused)) __attribute__((no_instrument_function)) __attribute__((always_inline)) void __read_once_size(const volatile void *p, void *res, int size)
{
 switch (size) {
 case 1: *(unsigned char *)res = *(volatile unsigned char *)p; break;
 case 2: *(unsigned short *)res = *(volatile unsigned short *)p; break;
 case 4: *(unsigned int *)res = *(volatile unsigned int *)p; break;
 case 8: *(unsigned long long *)res = *(volatile unsigned long long *)p; break;
 default:
  __asm__ __volatile__("": : :"memory");
  memcpy((void *)res, (const void *)p, size);
  __asm__ __volatile__("": : :"memory");
 }
}

static inline __attribute__((always_inline,unused)) __attribute__((no_instrument_function)) __attribute__((always_inline)) void __write_once_size(volatile void *p, void *res, int size)
{
 switch (size) {
 case 1: *(volatile unsigned char *)p = *(unsigned char *)res; break;
 case 2: *(volatile unsigned short *)p = *(unsigned short *)res; break;
 case 4: *(volatile unsigned int *)p = *(unsigned int *)res; break;
 case 8: *(volatile unsigned long long *)p = *(unsigned long long *)res; break;
 default:
  __asm__ __volatile__("": : :"memory");
  memcpy((void *)p, (const void *)res, size);
  __asm__ __volatile__("": : :"memory");
 }
}
# 564 "/home/holden/mckernel/kernel/include/lwk/compiler.h"
static inline __attribute__((always_inline,unused)) __attribute__((no_instrument_function)) void *ERR_PTR(long error)
{
 return (void *)error;
}

static inline __attribute__((always_inline,unused)) __attribute__((no_instrument_function)) long PTR_ERR(const void *ptr)
{
 return (long)ptr;
}

static inline __attribute__((always_inline,unused)) __attribute__((no_instrument_function)) long IS_ERR(const void *ptr)
{
 return (((unsigned long)ptr) >= (unsigned long)-4095);
}

static inline __attribute__((always_inline,unused)) __attribute__((no_instrument_function)) long IS_ERR_OR_NULL(const void *ptr)
{
 return !ptr || (((unsigned long)ptr) >= (unsigned long)-4095);
}
# 5 "/home/holden/mckernel/lib/include/ihk/debug.h" 2

void panic(const char *);


int kprintf(const char *format, ...);
unsigned long kprintf_lock(void);
void kprintf_unlock(unsigned long irqflags);
int __kprintf(const char *format, ...);

struct ddebug {
 const char *file;
 const char *func;
 const char *fmt;
 unsigned int line:24;
 unsigned int flags:8;
} __attribute__((aligned(8)));
# 6 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 2
# 1 "/usr/lib/gcc/x86_64-linux-gnu/9/include/stdarg.h" 1 3 4
# 40 "/usr/lib/gcc/x86_64-linux-gnu/9/include/stdarg.h" 3 4

# 40 "/usr/lib/gcc/x86_64-linux-gnu/9/include/stdarg.h" 3 4
typedef __builtin_va_list __gnuc_va_list;
# 99 "/usr/lib/gcc/x86_64-linux-gnu/9/include/stdarg.h" 3 4
typedef __gnuc_va_list va_list;
# 7 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 2

# 7 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
extern int vsnprintf(char *,size_t,const char *,va_list);
struct fixture_trace{unsigned long calls;int cpu,printer_return;unsigned long value;char format[96],rendered[128];int rendered_length,padding;};
static struct fixture_trace trace;
static int configured_return;
void fixture_reset(int printer_return)
{
    unsigned char *bytes=(unsigned char *)&trace;
    for(size_t i=0;i<sizeof(trace);i++)bytes[i]=0;
    configured_return=printer_return;
}
int kprintf(const char *format,...)
{
    trace.calls++;size_t length=0;while(format[length]&&length<95){trace.format[length]=format[length];length++;}trace.format[length]=0;
    va_list arguments,render_arguments;
# 20 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 3 4
                                      __builtin_va_start(
# 20 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
                                      arguments
# 20 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 3 4
                                      ,
# 20 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
                                      format
# 20 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 3 4
                                      )
# 20 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
                                                                ;
# 20 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 3 4
                                                                 __builtin_va_copy(
# 20 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
                                                                 render_arguments
# 20 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 3 4
                                                                 ,
# 20 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
                                                                 arguments
# 20 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 3 4
                                                                 )
# 20 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
                                                                                                    ;
    trace.cpu=
# 21 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 3 4
             __builtin_va_arg(
# 21 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
             arguments
# 21 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 3 4
             ,
# 21 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
             int
# 21 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 3 4
             )
# 21 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
                                  ;trace.value=
# 21 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 3 4
                                               __builtin_va_arg(
# 21 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
                                               arguments
# 21 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 3 4
                                               ,
# 21 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
                                               unsigned long
# 21 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 3 4
                                               )
# 21 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
                                                                              ;
    trace.rendered_length=vsnprintf(trace.rendered,sizeof(trace.rendered),format,render_arguments);
    
# 23 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 3 4
   __builtin_va_end(
# 23 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
   render_arguments
# 23 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 3 4
   )
# 23 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
                           ;
# 23 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 3 4
                            __builtin_va_end(
# 23 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
                            arguments
# 23 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c" 3 4
                            )
# 23 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/oracle.c"
                                             ;trace.printer_return=configured_return;return configured_return;
}
void fixture_read_trace(struct fixture_trace *out){*out=trace;}

extern struct ddebug arch_prctl_log_debug __asm__("mckernel_f06_arch_prctl_debug");

void arch_prctl_log_bridge(int event,int cpu,unsigned long value) __asm__("original_arch_prctl_log_bridge");
# 665 "/src/arch/x86_64/kernel/syscall.c"
void
arch_prctl_log_bridge(int event, int cpu, unsigned long value)
{
 if (event == 0x1002) {
  do { static struct ddebug __attribute__((aligned(8))) __attribute__((section("__verbose"))) ddebug = { .file = "/src/arch/x86_64/kernel/syscall.c", .func = __func__, .line = 669, .flags = 0x0, }; if (ddebug.flags) kprintf("[%d] arch_prctl: ARCH_SET_FS: 0x%lX\n", cpu, value); } while (0);
 }
}

extern struct ddebug __start___verbose[],__stop___verbose[];
struct ddebug *fixture_original_descriptor(void)
{
    struct ddebug *found=0;
    for(unsigned long address=(unsigned long)__start___verbose;address<(unsigned long)__stop___verbose;address+=sizeof(struct ddebug)){
        struct ddebug *row=(struct ddebug *)address;
        if(row==&arch_prctl_log_debug)continue;
        if(found)return 0;found=row;
    }
    return found;
}
size_t fixture_descriptor_count(void){return ((unsigned long)__stop___verbose-(unsigned long)__start___verbose)/sizeof(struct ddebug);}
void fixture_set_flags(struct ddebug *descriptor,unsigned int flags){descriptor->flags=flags;}
unsigned int fixture_original_flag_field(struct ddebug *descriptor){return descriptor->flags;}
