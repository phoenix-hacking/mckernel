# 1 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/consumer.c"
# 1 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1//"
# 1 "<built-in>"
# 1 "<command-line>"
# 1 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/consumer.c"

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
# 3 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/consumer.c" 2
# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/prctl.h" 1
# 4 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/consumer.c" 2
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
# 5 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f06-next-runtime-body11-restart-20261028-1/consumer.c" 2
typedef int (*print_abi)(const char *,...);
typedef void (*log_abi)(int,int,unsigned long);
extern void arch_prctl_log_bridge(int,int,unsigned long);
_Static_assert(__builtin_types_compatible_p(__typeof__(&kprintf),print_abi),"genuine existing printer ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_prctl_log_bridge),log_abi),"original public logger ABI");
_Static_assert(sizeof(int)==4 && sizeof(unsigned long)==8 && sizeof(void *)==8,"int32/unsigned LP64");
_Static_assert(0x1002==0x1002 && 0x1003==0x1003,"actual architecture event values");
_Static_assert(sizeof(struct ddebug)==32 && __alignof__(struct ddebug)==8,"actual descriptor size/alignment");
_Static_assert(__builtin_offsetof(struct ddebug,file)==0 && __builtin_offsetof(struct ddebug,func)==8 && __builtin_offsetof(struct ddebug,fmt)==16,"actual descriptor pointer fields");
int f06_prctl_logger_real_header_abi_witness;

extern struct ddebug arch_prctl_log_debug __asm__("mckernel_f06_arch_prctl_debug");

struct ddebug *fixture_selected_descriptor(void){return &arch_prctl_log_debug;}
void fixture_consumer_set_flags(unsigned int flags){arch_prctl_log_debug.flags=flags;}
unsigned int fixture_consumer_read_flags(void){return arch_prctl_log_debug.flags;}
void fixture_consumer_call(int event,int cpu,unsigned long value){arch_prctl_log_bridge(event,cpu,value);}
