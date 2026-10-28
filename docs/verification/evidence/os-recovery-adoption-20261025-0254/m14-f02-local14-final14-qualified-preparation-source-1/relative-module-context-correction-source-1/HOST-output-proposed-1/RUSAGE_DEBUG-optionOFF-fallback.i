# 1 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 1 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1//"
# 1 "<built-in>"
# 1 "<command-line>"
# 1 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 24 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 1 "/home/holden/mckernel/kernel/include/process.h" 1
# 17 "/home/holden/mckernel/kernel/include/process.h"
# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/ihk/context.h" 1
# 17 "/home/holden/mckernel/arch/x86_64/kernel/include/ihk/context.h"
# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/registers.h" 1
# 19 "/home/holden/mckernel/arch/x86_64/kernel/include/registers.h"
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
# 20 "/home/holden/mckernel/arch/x86_64/kernel/include/registers.h" 2
# 77 "/home/holden/mckernel/arch/x86_64/kernel/include/registers.h"
unsigned long CVAL(unsigned int event, unsigned int mask);
unsigned long CVAL2(unsigned int event, unsigned int mask,
  unsigned int inv, unsigned int count);

unsigned long xgetbv(unsigned int index);
void xsetbv(unsigned int index, unsigned long val);
void wrmsr(unsigned int idx, unsigned long value);
unsigned long rdpmc(unsigned int counter);
unsigned long rdmsr(unsigned int index);
unsigned long rdtsc(void);
void ihk_mc_mb(void);
unsigned long REGS_GET_STACK_POINTER(const void *regs);

struct x86_desc_ptr {
        uint16_t size;
        uint64_t address;
} __attribute__((packed));

struct tss64 {
        unsigned int reserved0;
        unsigned long rsp0;
        unsigned long rsp1;
        unsigned long rsp2;
        unsigned int reserved1, reserved2;
        unsigned long ist[7];
        unsigned int reserved3, reserved4;
        unsigned short reserved5;
        unsigned short iomap_address;
} __attribute__((packed));

struct x86_basic_regs {
 unsigned long r15;
 unsigned long r14;
 unsigned long r13;
 unsigned long r12;
 unsigned long rbp;
 unsigned long rbx;
 unsigned long r11;
 unsigned long r10;
 unsigned long r9;
 unsigned long r8;
 unsigned long rax;
 unsigned long rcx;
 unsigned long rdx;
 unsigned long rsi;
 unsigned long rdi;
 union {
  unsigned long orig_rax;
  unsigned long error;
 };
 unsigned long rip;
 unsigned long cs;
 unsigned long rflags;
 unsigned long rsp;
 unsigned long ss;
};

struct x86_sregs {
 unsigned long fs_base;
 unsigned long gs_base;
 unsigned long ds;
 unsigned long es;
 unsigned long fs;
 unsigned long gs;
};
# 156 "/home/holden/mckernel/arch/x86_64/kernel/include/registers.h"
enum x86_pf_error_code {
 PF_PROT = 1 << 0,
 PF_WRITE = 1 << 1,
 PF_USER = 1 << 2,
 PF_RSVD = 1 << 3,
 PF_INSTR = 1 << 4,

 PF_PATCH = 1 << 29,
 PF_POPULATE = 1 << 30,
};

struct i387_fxsave_struct {
 unsigned short cwd;
 unsigned short swd;
 unsigned short twd;
 unsigned short fop;
 union {
  struct {
   unsigned long rip;
   unsigned long rdp;
  };
  struct {
   unsigned int fip;
   unsigned int fcs;
   unsigned int foo;
   unsigned int fos;
  };
 };
 unsigned int mxcsr;
 unsigned int mxcsr_mask;
 unsigned int st_space[32];
 unsigned int xmm_space[64];
 unsigned int padding[12];
 union {
  unsigned int padding1[12];
  unsigned int sw_reserved[12];
 };

} __attribute__((aligned(16)));

struct ymmh_struct {
 unsigned int ymmh_space[64];
};

struct lwp_struct {
 unsigned char reserved[128];
};

struct bndreg {
 unsigned long lower_bound;
 unsigned long upper_bound;
} __attribute__((packed));

struct bndcsr {
 unsigned long bndcfgu;
 unsigned long bndstatus;
} __attribute__((packed));

struct xsave_hdr_struct {
 unsigned long xstate_bv;
 unsigned long xcomp_bv;
 unsigned long reserved[6];
} __attribute__((packed));

struct xsave_struct {
 struct i387_fxsave_struct i387;
 struct xsave_hdr_struct xsave_hdr;
 struct ymmh_struct ymmh;
 struct lwp_struct lwp;
 struct bndreg bndreg[4];
 struct bndcsr bndcsr;
} __attribute__ ((packed, aligned (64)));

typedef struct xsave_struct fp_regs_struct;
# 18 "/home/holden/mckernel/arch/x86_64/kernel/include/ihk/context.h" 2

struct x86_kregs {
 unsigned long rsp, rbp, rbx, rsi, rdi, r12, r13, r14, r15, rflags;
 unsigned long rsp0;
};

typedef struct x86_kregs ihk_mc_kernel_context_t;


struct x86_user_context {
 struct x86_sregs sr;


 uint8_t is_gpr_valid;
 uint8_t is_sr_valid;
 uint8_t spare_flags6;
 uint8_t spare_flags5;
 uint8_t spare_flags4;
 uint8_t spare_flags3;
 uint8_t spare_flags2;
 uint8_t spare_flags1;
 struct x86_basic_regs gpr;

};
typedef struct x86_user_context ihk_mc_user_context_t;

unsigned long ihk_mc_syscall_arg0(const ihk_mc_user_context_t *uc);
unsigned long ihk_mc_syscall_arg1(const ihk_mc_user_context_t *uc);
unsigned long ihk_mc_syscall_arg2(const ihk_mc_user_context_t *uc);
unsigned long ihk_mc_syscall_arg3(const ihk_mc_user_context_t *uc);
unsigned long ihk_mc_syscall_arg4(const ihk_mc_user_context_t *uc);
unsigned long ihk_mc_syscall_arg5(const ihk_mc_user_context_t *uc);

void ihk_mc_syscall_set_arg0(ihk_mc_user_context_t *uc, unsigned long value);
void ihk_mc_syscall_set_arg1(ihk_mc_user_context_t *uc, unsigned long value);
void ihk_mc_syscall_set_arg2(ihk_mc_user_context_t *uc, unsigned long value);
void ihk_mc_syscall_set_arg3(ihk_mc_user_context_t *uc, unsigned long value);
void ihk_mc_syscall_set_arg4(ihk_mc_user_context_t *uc, unsigned long value);
void ihk_mc_syscall_set_arg5(ihk_mc_user_context_t *uc, unsigned long value);

unsigned long ihk_mc_syscall_ret(const ihk_mc_user_context_t *uc);
void ihk_mc_syscall_set_ret(ihk_mc_user_context_t *uc, unsigned long value);
unsigned long ihk_mc_syscall_number(const ihk_mc_user_context_t *uc);

unsigned long ihk_mc_syscall_pc(const ihk_mc_user_context_t *uc);
unsigned long ihk_mc_syscall_sp(const ihk_mc_user_context_t *uc);
# 18 "/home/holden/mckernel/kernel/include/process.h" 2
# 1 "/home/holden/mckernel/lib/include/ihk/cpu.h" 1
# 17 "/home/holden/mckernel/lib/include/ihk/cpu.h"
# 1 "/home/holden/mckernel/lib/include/list.h" 1







struct list_head {
 struct list_head *next, *prev;
};
# 36 "/home/holden/mckernel/lib/include/list.h"
void INIT_LIST_HEAD(struct list_head *list);
void __list_add(struct list_head *new, struct list_head *prev,
  struct list_head *next);
void list_add(struct list_head *new, struct list_head *head);
void list_add_tail(struct list_head *new, struct list_head *head);
void __list_del(struct list_head *prev, struct list_head *next);
void __list_del_entry(struct list_head *entry);
void list_del(struct list_head *entry);
void list_replace(struct list_head *old, struct list_head *new);
void list_replace_init(struct list_head *old, struct list_head *new);
void list_del_init(struct list_head *entry);
void list_move(struct list_head *list, struct list_head *head);
void list_move_tail(struct list_head *list, struct list_head *head);
int list_is_last(const struct list_head *list, const struct list_head *head);
int list_empty(const struct list_head *head);
int list_empty_careful(const struct list_head *head);
void list_rotate_left(struct list_head *head);
int list_is_singular(const struct list_head *head);
void __list_cut_position(struct list_head *list, struct list_head *head,
  struct list_head *entry);
void list_cut_position(struct list_head *list, struct list_head *head,
  struct list_head *entry);
void __list_splice(const struct list_head *list, struct list_head *prev,
  struct list_head *next);
void list_splice(const struct list_head *list, struct list_head *head);
void list_splice_tail(struct list_head *list, struct list_head *head);
void list_splice_init(struct list_head *list, struct list_head *head);
void list_splice_tail_init(struct list_head *list, struct list_head *head);
# 18 "/home/holden/mckernel/lib/include/ihk/cpu.h" 2

# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/arch/cpu.h" 1
# 16 "/home/holden/mckernel/arch/x86_64/kernel/include/arch/cpu.h"
void mb(void);
void rmb(void);
void wmb(void);
void smp_mb(void);
void smp_rmb(void);
void smp_wmb(void);
void arch_barrier(void);

unsigned long read_tsc(void);
unsigned long smp_load_acquire_ulong(const unsigned long *p);
unsigned int smp_load_acquire_uint(const unsigned int *p);
int smp_load_acquire_int(const int *p);
void *smp_load_acquire_ptr(void *const *p);
void smp_store_release_ulong(unsigned long *p, unsigned long v);
void smp_store_release_uint(unsigned int *p, unsigned int v);
void smp_store_release_int(int *p, int v);

void arch_flush_icache_all(void);
# 20 "/home/holden/mckernel/lib/include/ihk/cpu.h" 2
# 1 "/home/holden/mckernel/lib/include/mc_perf_event.h" 1





# 1 "/home/holden/mckernel/ihk/cokernel/smp/x86_64/include/march.h" 1






extern int perf_counters_discovered;
extern int NUM_PERF_COUNTERS;
extern unsigned long PERF_COUNTERS_MASK;


extern int NUM_FIXED_PERF_COUNTERS;
extern unsigned long FIXED_PERF_COUNTERS_MASK;
# 27 "/home/holden/mckernel/ihk/cokernel/smp/x86_64/include/march.h"
enum extra_reg_type {
 EXTRA_REG_NONE = -1,

 EXTRA_REG_RSP_0 = 0,
 EXTRA_REG_RSP_1 = 1,
 EXTRA_REG_LBR = 2,
 EXTRA_REG_LDLAT = 3,
 EXTRA_REG_FE = 4,

 EXTRA_REG_MAX
};
# 7 "/home/holden/mckernel/lib/include/mc_perf_event.h" 2
# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/ihk/atomic.h" 1
# 16 "/home/holden/mckernel/arch/x86_64/kernel/include/ihk/atomic.h"
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
# 17 "/home/holden/mckernel/arch/x86_64/kernel/include/ihk/atomic.h" 2





typedef struct {
 int counter;
} ihk_atomic_t;

int ihk_atomic_inc_return(ihk_atomic_t *v);
int ihk_atomic_dec_return(ihk_atomic_t *v);
int ihk_atomic_read(const ihk_atomic_t *v);
void ihk_atomic_set(ihk_atomic_t *v, int i);
void ihk_atomic_add(int i, ihk_atomic_t *v);
void ihk_atomic_sub(int i, ihk_atomic_t *v);
void ihk_atomic_inc(ihk_atomic_t *v);
void ihk_atomic_dec(ihk_atomic_t *v);
int ihk_atomic_dec_and_test(ihk_atomic_t *v);
int ihk_atomic_inc_and_test(ihk_atomic_t *v);
int ihk_atomic_add_return(int i, ihk_atomic_t *v);
int ihk_atomic_sub_return(int i, ihk_atomic_t *v);





typedef struct {
 long counter64;
} ihk_atomic64_t;

long ihk_atomic64_read(const ihk_atomic64_t *v);
void ihk_atomic64_set(ihk_atomic64_t *v, long i);
void ihk_atomic64_inc(ihk_atomic64_t *v);
long ihk_atomic64_add_return(long i, ihk_atomic64_t *v);
long ihk_atomic64_sub_return(long i, ihk_atomic64_t *v);





unsigned long xchg8(unsigned long *ptr, unsigned long x);
int xchg4(int *ptr, int x);
unsigned long atomic_xchg_ulong(unsigned long *ptr, unsigned long x);
void *atomic_xchg_ptr(void **ptr, void *x);

unsigned long atomic_cmpxchg8(unsigned long *addr,
  unsigned long oldval, unsigned long newval);
unsigned long atomic_cmpxchg4(unsigned int *addr,
  unsigned int oldval, unsigned int newval);
int atomic_cmpxchg_int(int *addr, int oldval, int newval);
unsigned long atomic_cmpxchg_ulong(unsigned long *addr,
  unsigned long oldval, unsigned long newval);
void *atomic_cmpxchg_ptr(void **addr, void *oldval, void *newval);
# 78 "/home/holden/mckernel/arch/x86_64/kernel/include/ihk/atomic.h"
void ihk_atomic_add_long(long i, long *v);
void ihk_atomic_add_ulong(long i, unsigned long *v);
unsigned long ihk_atomic_add_long_return(long i, long *v);
# 8 "/home/holden/mckernel/lib/include/mc_perf_event.h" 2

struct perf_event_attr;
# 20 "/home/holden/mckernel/lib/include/mc_perf_event.h"
enum perf_type_id {
        PERF_TYPE_HARDWARE = 0,
        PERF_TYPE_SOFTWARE = 1,
        PERF_TYPE_TRACEPOINT = 2,
        PERF_TYPE_HW_CACHE = 3,
        PERF_TYPE_RAW = 4,
        PERF_TYPE_BREAKPOINT = 5,

        PERF_TYPE_MAX,
};

enum perf_event_read_format {
        PERF_FORMAT_TOTAL_TIME_ENABLED = 1U << 0,
        PERF_FORMAT_TOTAL_TIME_RUNNING = 1U << 1,
        PERF_FORMAT_ID = 1U << 2,
        PERF_FORMAT_GROUP = 1U << 3,

        PERF_FORMAT_MAX = 1U << 4,
};

enum perf_hw_id {



        PERF_COUNT_HW_CPU_CYCLES = 0,
        PERF_COUNT_HW_INSTRUCTIONS = 1,
        PERF_COUNT_HW_CACHE_REFERENCES = 2,
        PERF_COUNT_HW_CACHE_MISSES = 3,
        PERF_COUNT_HW_BRANCH_INSTRUCTIONS = 4,
        PERF_COUNT_HW_BRANCH_MISSES = 5,
        PERF_COUNT_HW_BUS_CYCLES = 6,
        PERF_COUNT_HW_STALLED_CYCLES_FRONTEND = 7,
        PERF_COUNT_HW_STALLED_CYCLES_BACKEND = 8,
        PERF_COUNT_HW_REF_CPU_CYCLES = 9,

        PERF_COUNT_HW_MAX,
};
# 65 "/home/holden/mckernel/lib/include/mc_perf_event.h"
enum perf_hw_cache_id {
 PERF_COUNT_HW_CACHE_L1D = 0,
 PERF_COUNT_HW_CACHE_L1I = 1,
 PERF_COUNT_HW_CACHE_LL = 2,
 PERF_COUNT_HW_CACHE_DTLB = 3,
 PERF_COUNT_HW_CACHE_ITLB = 4,
 PERF_COUNT_HW_CACHE_BPU = 5,
 PERF_COUNT_HW_CACHE_NODE = 6,

 PERF_COUNT_HW_CACHE_MAX,
};

enum perf_hw_cache_op_id {
 PERF_COUNT_HW_CACHE_OP_READ = 0,
 PERF_COUNT_HW_CACHE_OP_WRITE = 1,
 PERF_COUNT_HW_CACHE_OP_PREFETCH = 2,

 PERF_COUNT_HW_CACHE_OP_MAX,
};

enum perf_hw_cache_op_result_id {
 PERF_COUNT_HW_CACHE_RESULT_ACCESS = 0,
 PERF_COUNT_HW_CACHE_RESULT_MISS = 1,

 PERF_COUNT_HW_CACHE_RESULT_MAX,
};




struct perf_event_attr {




 unsigned int type;




 unsigned int size;




 unsigned long config;

 union {
  unsigned long sample_period;
  unsigned long sample_freq;
 };

 unsigned long sample_type;
 unsigned long read_format;

 unsigned long disabled : 1,
    inherit : 1,
    pinned : 1,
    exclusive : 1,
    exclude_user : 1,
    exclude_kernel : 1,
    exclude_hv : 1,
    exclude_idle : 1,
    mmap : 1,
    comm : 1,
    freq : 1,
    inherit_stat : 1,
    enable_on_exec : 1,
    task : 1,
    watermark : 1,
# 145 "/home/holden/mckernel/lib/include/mc_perf_event.h"
    precise_ip : 2,
    mmap_data : 1,
    sample_id_all : 1,

    exclude_host : 1,
    exclude_guest : 1,

    exclude_callchain_kernel : 1,
    exclude_callchain_user : 1,
    mmap2 : 1,




    comm_exec : 1,
    __reserved_1 : 39;


 union {
  unsigned int wakeup_events;
  unsigned int wakeup_watermark;
 };

 unsigned int bp_type;
 union {
  unsigned long bp_addr;
  unsigned long config1;
 };
 union {
  unsigned long bp_len;
  unsigned long config2;
 };
 unsigned long branch_sample_type;





 unsigned long sample_regs_user;




 unsigned int sample_stack_user;


 unsigned int __reserved_2;
# 201 "/home/holden/mckernel/lib/include/mc_perf_event.h"
 unsigned long sample_regs_intr;

};

struct hw_perf_event_extra {
 unsigned long config;
 unsigned int reg;
 int idx;
};

struct hw_perf_event {




 ihk_atomic64_t prev_count;




 uint64_t sample_period;




 uint64_t last_period;






 ihk_atomic64_t period_left;
};




enum perf_event_state {
 PERF_EVENT_STATE_INACTIVE = 0,
 PERF_EVENT_STATE_ACTIVE = 1,
};

struct mc_perf_event {
 struct perf_event_attr attr;
 struct hw_perf_event_extra extra_reg;
 unsigned long hw_config;
 unsigned long hw_config_ext;
 enum perf_event_state state;
 int cpu_id;
 int counter_id;
 ihk_atomic64_t count;
 unsigned long child_count_total;
 unsigned long pmc_status;
 unsigned long sample_freq;

 struct mc_perf_event *parent;
 struct mc_perf_event *group_leader;
 struct list_head sibling_list;
 int nr_siblings;
 int pid;
 struct list_head group_entry;
 int use_invariant_tsc;
 long long base_user_tsc;
 long long stopped_user_tsc;
 long long user_accum_count;
 long long base_system_tsc;
 long long stopped_system_tsc;
 long long system_accum_count;
 struct hw_perf_event hw;
};

struct perf_event_mmap_page {
 unsigned int version;
 unsigned int compat_version;
 unsigned int lock;
 unsigned int index;
 long offset;
 unsigned long time_enabled;
 unsigned long time_running;
 union {
  unsigned long capabilities;
  struct {
   unsigned long cap_bit0 : 1,
                  cap_bit0_is_deprecated : 1,
    cap_user_rdpmc : 1,
    cap_user_time : 1,
    cap_user_time_zero : 1,
    cap_____res : 59;
  };
 };
 unsigned short pmc_width;
 unsigned short time_shift;
 unsigned int time_mult;
 unsigned long time_offset;
 unsigned long time_zero;
 unsigned int size;

 unsigned char __reserved[118*8+4];
 unsigned long data_head;
 unsigned long data_tail;
};
# 21 "/home/holden/mckernel/lib/include/ihk/cpu.h" 2

extern int num_processors;

void cpu_enable_interrupt(void);
void cpu_disable_interrupt(void);
int cpu_interrupt_disabled(void);
void cpu_halt(void);



void cpu_safe_halt(void);
void cpu_restore_interrupt(unsigned long);
void cpu_pause(void);

unsigned long cpu_disable_interrupt_save(void);
unsigned long cpu_enable_interrupt_save(void);

struct ihk_mc_interrupt_handler {
 struct list_head list;
 void (*func)(void *);
 void *priv;
};
int ihk_mc_register_interrupt_handler(int vector,
                                      struct ihk_mc_interrupt_handler *h);
int ihk_mc_unregister_interrupt_handler(int vector,
                                        struct ihk_mc_interrupt_handler *h);

enum ihk_mc_gv_type {
 IHK_GV_IKC = 1,
 IHK_GV_QUERY_FREE_MEM = 2
};

int ihk_mc_get_vector(enum ihk_mc_gv_type type);
int ihk_mc_interrupt_host(int cpu, int vector);

struct ihk_mc_cpu_info {
 int ncpus;
 int *hw_ids;
 int *nodes;
 int *linux_cpu_ids;
 int *ikc_cpus;
};

struct ihk_mc_cpu_info *ihk_mc_get_cpu_info(void);
void ihk_mc_boot_cpu(int cpuid, unsigned long pc);
int ihk_mc_get_processor_id(void);
int ihk_mc_get_hardware_processor_id(void);
int ihk_mc_get_numa_id(void);
int ihk_mc_get_nr_cores(void);
int ihk_mc_get_nr_linux_cores(void);
int ihk_mc_get_osnum(void);
int ihk_mc_get_core(int id, unsigned long *linux_core_id, unsigned long *apic_id,
                    int *numa_id);
int ihk_mc_get_ikc_cpu(int id);
int ihk_mc_get_apicid(int linux_core_id);

void ihk_mc_delay_us(int us);
void ihk_mc_set_syscall_handler(long (*handler)(int, ihk_mc_user_context_t *));

void ihk_mc_init_ap(void);

void ihk_mc_init_context(ihk_mc_kernel_context_t *new_ctx,
                         void *stack_pointer,
                         void (*next_function)(void));
void *ihk_mc_get_linux_kernel_pgt(void);

int ihk_mc_get_extra_reg_id(unsigned long hw_config, unsigned long hw_config_ext);
unsigned int ihk_mc_get_nr_extra_regs(void);
int ihk_mc_get_extra_reg_idx(int id);
unsigned int ihk_mc_get_extra_reg_msr(int id);
unsigned long ihk_mc_get_extra_reg_event(int id);
unsigned long ihk_mc_hw_event_map(unsigned long hw_event);
unsigned long ihk_mc_hw_cache_event_map(unsigned long hw_cache_event);
unsigned long ihk_mc_hw_cache_extra_reg_map(unsigned long hw_cache_event);
unsigned long ihk_mc_raw_event_map(unsigned long raw_event);
int ihk_mc_validate_event(unsigned long hw_config);
int hw_perf_event_init(struct mc_perf_event *event);
int ihk_mc_event_set_period(struct mc_perf_event *event);
uint64_t ihk_mc_event_update(struct mc_perf_event *event);
int is_sampling_event(struct mc_perf_event *event);


void *ihk_mc_switch_context(ihk_mc_kernel_context_t *old_ctx,
                           ihk_mc_kernel_context_t *new_ctx,
      void *prev);
int ihk_mc_get_interrupt_id(int cpu);
int ihk_mc_interrupt_cpu(int cpu, int vector);

void ihk_mc_init_user_process(ihk_mc_kernel_context_t *ctx,
                              ihk_mc_user_context_t **puctx,
                              void *stack_pointer, unsigned long user_pc,
                              unsigned long user_sp);

void ihk_mc_init_user_tlsbase(ihk_mc_user_context_t *ctx,
                              unsigned long tls_base_addr);





enum ihk_mc_user_context_regtype {
 IHK_UCR_STACK_POINTER = 1,
 IHK_UCR_PROGRAM_COUNTER = 2,
};

struct thread;
void arch_clone_thread(struct thread *othread, unsigned long pc,
   unsigned long sp, struct thread *nthread);

void ihk_mc_modify_user_context(ihk_mc_user_context_t *uctx,
                                enum ihk_mc_user_context_regtype reg,
                                unsigned long value);

void ihk_mc_debug_show_interrupt_context(const void *reg);

enum ihk_asr_type {
 IHK_ASR_X86_FS,
 IHK_ASR_X86_GS,
};





int ihk_mc_arch_set_special_register(enum ihk_asr_type, unsigned long value);
int ihk_mc_arch_get_special_register(enum ihk_asr_type, unsigned long *value);

extern unsigned int ihk_ikc_irq;
extern unsigned int ihk_ikc_irq_apicid;

extern int gettime_local_support;

void init_tick(void);
void init_delay(void);
void sync_tick(void);

struct pvclock_vsyscall_time_info {
 long contents[64/sizeof(long)];
};

extern struct pvclock_vsyscall_time_info *pvti;
extern int pvti_npages;

int arch_setup_pvclock(void);
void arch_start_pvclock(void);

struct cpu_mapping;
int arch_get_cpu_mapping(struct cpu_mapping **buf, int *nelemsp);
int ihk_mc_ikc_arch_issue_host_ipi(int cpu, int vector);

void smp_func_call_handler(void);
int ihk_mc_get_smp_handler_irq(void);
# 19 "/home/holden/mckernel/kernel/include/process.h" 2
# 1 "/home/holden/mckernel/lib/include/ihk/mm.h" 1
# 19 "/home/holden/mckernel/lib/include/ihk/mm.h"
# 1 "/home/holden/mckernel/lib/include/memory.h" 1
# 17 "/home/holden/mckernel/lib/include/memory.h"
# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/arch-memory.h" 1
# 20 "/home/holden/mckernel/arch/x86_64/kernel/include/arch-memory.h"
# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/errno.h" 1



# 1 "/home/holden/mckernel/lib/include/generic-errno.h" 1
# 5 "/home/holden/mckernel/arch/x86_64/kernel/include/errno.h" 2
# 21 "/home/holden/mckernel/arch/x86_64/kernel/include/arch-memory.h" 2

struct memobj;
# 73 "/home/holden/mckernel/arch/x86_64/kernel/include/arch-memory.h"
struct vm_regions;
unsigned long STACK_TOP(const struct vm_regions *region);
# 148 "/home/holden/mckernel/arch/x86_64/kernel/include/arch-memory.h"
typedef unsigned long pte_t;
# 157 "/home/holden/mckernel/arch/x86_64/kernel/include/arch-memory.h"
uint64_t PM_STATUS(uint64_t nr);



uint64_t PM_PSHIFT(uint64_t x);

uint64_t PM_PFRAME(uint64_t x);
# 174 "/home/holden/mckernel/arch/x86_64/kernel/include/arch-memory.h"
enum ihk_mc_pt_attribute {
 PTATTR_ACTIVE = 0x01,
 PTATTR_WRITABLE = 0x02,
 PTATTR_USER = 0x04,
 PTATTR_DIRTY = 0x40,
 PTATTR_LARGEPAGE = 0x80,
 PTATTR_FILEOFF = ((pte_t)1 << 11),
 PTATTR_NO_EXECUTE = 0x8000000000000000,
 PTATTR_UNCACHABLE = 0x10000,
 PTATTR_FOR_USER = 0x20000,
 PTATTR_WRITE_COMBINED = 0x40000,
};

extern enum ihk_mc_pt_attribute attr_mask;

int pfn_is_write_combined(uintptr_t pfn);
int pte_is_null(pte_t *ptep);
int pte_is_present(pte_t *ptep);
int pte_is_writable(pte_t *ptep);
int pte_is_dirty(pte_t *ptep, size_t pgsize);
int pte_is_fileoff(pte_t *ptep, size_t pgsize);
void pte_update_phys(pte_t *ptep, unsigned long phys);
uintptr_t pte_get_phys(pte_t *ptep);
off_t pte_get_off(pte_t *ptep, size_t pgsize);
enum ihk_mc_pt_attribute pte_get_attr(pte_t *ptep, size_t pgsize);
void pte_make_null(pte_t *ptep, size_t pgsize);
void pte_make_fileoff(off_t off, enum ihk_mc_pt_attribute ptattr,
        size_t pgsize, pte_t *ptep);
void pte_xchg(pte_t *ptep, pte_t *valp);
void pte_clear_dirty(pte_t *ptep, size_t pgsize);
void pte_set_dirty(pte_t *ptep, size_t pgsize);
int pte_is_contiguous(pte_t *ptep);
int pgsize_is_contiguous(size_t pgsize);
int pgsize_to_tbllv(size_t pgsize);
int pgsize_to_pgshift(size_t pgsize);
size_t tbllv_to_pgsize(int level);
size_t tbllv_to_contpgsize(int level);
int tbllv_to_contpgshift(int level);
pte_t *get_contiguous_head(pte_t *__ptep, size_t __pgsize);
pte_t *get_contiguous_tail(pte_t *__ptep, size_t __pgsize);
int split_contiguous_pages(pte_t *ptep, size_t pgsize,
  uint32_t memobj_flags);
int page_is_contiguous_head(pte_t *ptep, size_t pgsize);
int page_is_contiguous_tail(pte_t *ptep, size_t pgsize);
struct page_table;
void arch_adjust_allocate_page_size(struct page_table *pt,
        uintptr_t fault_addr,
        pte_t *ptep,
        void **pgaddrp,
        size_t *pgsizep);

int split_contiguous_pages(pte_t *ptep, size_t pgsize,
  uint32_t memobj_flags);
void set_pte(pte_t *ppte, unsigned long phys, enum ihk_mc_pt_attribute attr);
pte_t *get_pte(struct page_table *pt, void *virt, enum ihk_mc_pt_attribute attr);

void *early_alloc_pages(int nr_pages);
void *get_last_early_heap(void);
void flush_tlb(void);
void flush_tlb_single(unsigned long addr);

void *map_fixed_area(unsigned long phys, unsigned long size, int uncachable);

extern unsigned long ap_trampoline;
# 18 "/home/holden/mckernel/lib/include/memory.h" 2

struct process_vm;

unsigned long virt_to_phys(void *v);
void *phys_to_virt(unsigned long p);
int phys_to_nid(unsigned long p);
int lookup_node(struct process_vm *vm, void *addr);
int copy_from_user(void *dst, const void *src, size_t siz);
int strlen_user(const char *s);
int strcpy_from_user(char *dst, const char *src);
long getlong_user(long *dest, const long *p);
int getint_user(int *dest, const int *p);
int verify_process_vm(struct process_vm *vm,
  const void *usrc, size_t size);
int read_process_vm(struct process_vm *vm, void *kdst, const void *usrc, size_t siz);
int copy_to_user(void *dst, const void *src, size_t siz);
int setlong_user(long *dst, long data);
int setint_user(int *dst, int data);
int write_process_vm(struct process_vm *vm, void *udst, const void *ksrc, size_t siz);
int patch_process_vm(struct process_vm *vm, void *udst, const void *ksrc, size_t siz);

int is_mckernel_memory(unsigned long start, unsigned long end);
# 20 "/home/holden/mckernel/lib/include/ihk/mm.h" 2
# 1 "/home/holden/mckernel/lib/include/ihk/lock.h" 1
# 16 "/home/holden/mckernel/lib/include/ihk/lock.h"
# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/arch-lock.h" 1
# 10 "/home/holden/mckernel/arch/x86_64/kernel/include/arch-lock.h"
# 1 "/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/owner-work/output/build/config.h" 1
# 11 "/home/holden/mckernel/arch/x86_64/kernel/include/arch-lock.h" 2
# 19 "/home/holden/mckernel/arch/x86_64/kernel/include/arch-lock.h"
typedef unsigned short __ticket_t;
typedef unsigned int __ticketpair_t;

typedef struct ihk_spinlock {
 union {
  __ticketpair_t head_tail;
  struct __raw_tickets {
   __ticket_t head, tail;
  } tickets;
 };
} ihk_spinlock_t;

extern void preempt_enable(void);
extern void preempt_disable(void);





void ihk_mc_spinlock_init(ihk_spinlock_t *lock);
int __ihk_mc_spinlock_trylock_noirq(ihk_spinlock_t *lock);
unsigned long __ihk_mc_spinlock_trylock(ihk_spinlock_t *lock, int *result);
void __ihk_mc_spinlock_lock_noirq(ihk_spinlock_t *lock);
unsigned long __ihk_mc_spinlock_lock(ihk_spinlock_t *lock);
void __ihk_mc_spinlock_unlock_noirq(ihk_spinlock_t *lock);
void __ihk_mc_spinlock_unlock(ihk_spinlock_t *lock, unsigned long flags);
# 55 "/home/holden/mckernel/arch/x86_64/kernel/include/arch-lock.h"
typedef struct mcs_rwlock_node {
 ihk_atomic_t count;
 char type;



 char locked;


 char dmy1;
 char dmy2;
 struct mcs_rwlock_node *next;

} __attribute__((aligned(64))) mcs_rwlock_node_t;




typedef struct mcs_rwlock_node_irqsave {



 unsigned long irqsave;

} __attribute__((aligned(64))) mcs_rwlock_node_irqsave_t;




typedef struct mcs_rwlock_lock {

 ihk_spinlock_t slock;





} __attribute__((aligned(64))) mcs_rwlock_lock_t;




void mcs_rwlock_init(struct mcs_rwlock_lock *lock);
void __mcs_rwlock_writer_lock_noirq(struct mcs_rwlock_lock *lock,
 struct mcs_rwlock_node *node);
void __mcs_rwlock_writer_unlock_noirq(struct mcs_rwlock_lock *lock,
 struct mcs_rwlock_node *node);
void __mcs_rwlock_reader_lock_noirq(struct mcs_rwlock_lock *lock,
 struct mcs_rwlock_node *node);
void __mcs_rwlock_reader_unlock_noirq(struct mcs_rwlock_lock *lock,
 struct mcs_rwlock_node *node);
void __mcs_rwlock_writer_lock(struct mcs_rwlock_lock *lock,
 struct mcs_rwlock_node_irqsave *node);
void __mcs_rwlock_writer_unlock(struct mcs_rwlock_lock *lock,
 struct mcs_rwlock_node_irqsave *node);
void __mcs_rwlock_reader_lock(struct mcs_rwlock_lock *lock,
 struct mcs_rwlock_node_irqsave *node);
void __mcs_rwlock_reader_unlock(struct mcs_rwlock_lock *lock,
 struct mcs_rwlock_node_irqsave *node);
# 123 "/home/holden/mckernel/arch/x86_64/kernel/include/arch-lock.h"
int irqflags_can_interrupt(unsigned long flags);

struct ihk_rwlock {
 union {
  long lock;
  struct {
   unsigned int read;
   int write;
  };
 } lock;
};

void ihk_mc_rwlock_init(struct ihk_rwlock *rw);
void ihk_mc_read_lock(struct ihk_rwlock *rw);
void ihk_mc_write_lock(struct ihk_rwlock *rw);
int ihk_mc_read_trylock(struct ihk_rwlock *rw);
int ihk_mc_write_trylock(struct ihk_rwlock *rw);
void ihk_mc_read_unlock(struct ihk_rwlock *rw);
void ihk_mc_write_unlock(struct ihk_rwlock *rw);
int ihk_mc_write_can_lock(struct ihk_rwlock *rw);
int ihk_mc_read_can_lock(struct ihk_rwlock *rw);
# 17 "/home/holden/mckernel/lib/include/ihk/lock.h" 2




typedef struct {
 ihk_atomic_t v;
} __attribute__((aligned(4))) ihk_rwspinlock_t;

void ihk_rwspinlock_init(ihk_rwspinlock_t *lock);
void __ihk_rwspinlock_read_lock(ihk_rwspinlock_t *lock);
int __ihk_rwspinlock_read_trylock(ihk_rwspinlock_t *lock);
void __ihk_rwspinlock_read_unlock(ihk_rwspinlock_t *lock);
void __ihk_rwspinlock_write_lock(ihk_rwspinlock_t *lock);
void __ihk_rwspinlock_write_unlock(ihk_rwspinlock_t *lock);
void ihk_rwspinlock_read_lock_noirq(ihk_rwspinlock_t *lock);
int ihk_rwspinlock_read_trylock_noirq(ihk_rwspinlock_t *lock);
void ihk_rwspinlock_write_lock_noirq(ihk_rwspinlock_t *lock);
void ihk_rwspinlock_read_unlock_noirq(ihk_rwspinlock_t *lock);
void ihk_rwspinlock_write_unlock_noirq(ihk_rwspinlock_t *lock);
unsigned long ihk_rwspinlock_read_lock(ihk_rwspinlock_t *lock);
unsigned long ihk_rwspinlock_write_lock(ihk_rwspinlock_t *lock);
void ihk_rwspinlock_read_unlock(ihk_rwspinlock_t *lock,
 unsigned long irqstate);
void ihk_rwspinlock_write_unlock(ihk_rwspinlock_t *lock,
 unsigned long irqstate);







typedef struct mcs_lock_node {

 unsigned long locked;
 struct mcs_lock_node *next;

 unsigned long irqsave;




} __attribute__((aligned(64))) mcs_lock_node_t;




typedef mcs_lock_node_t mcs_lock_t;

void mcs_lock_init(struct mcs_lock_node *node);
void __mcs_lock_lock(struct mcs_lock_node *lock,
 struct mcs_lock_node *node);
void __mcs_lock_unlock(struct mcs_lock_node *lock,
 struct mcs_lock_node *node);
void mcs_lock_lock_noirq(struct mcs_lock_node *lock,
 struct mcs_lock_node *node);
void mcs_lock_unlock_noirq(struct mcs_lock_node *lock,
 struct mcs_lock_node *node);
void mcs_lock_lock(struct mcs_lock_node *lock,
 struct mcs_lock_node *node);
void mcs_lock_unlock(struct mcs_lock_node *lock,
 struct mcs_lock_node *node);
# 89 "/home/holden/mckernel/lib/include/ihk/lock.h"
void linux_spin_lock(void *lock);
void linux_spin_unlock(void *lock);
void linux_spin_lock_irqsave(void *lock, unsigned long *flags);
void linux_spin_unlock_irqrestore(void *lock, unsigned long flags);
# 21 "/home/holden/mckernel/lib/include/ihk/mm.h" 2

# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/arch/mm.h" 1



struct process_vm;

void flush_nfo_tlb(void);
void flush_nfo_tlb_mm(struct process_vm *vm);
# 23 "/home/holden/mckernel/lib/include/ihk/mm.h" 2
# 1 "/home/holden/mckernel/kernel/include/page.h" 1
# 18 "/home/holden/mckernel/kernel/include/page.h"
struct page {
 struct list_head list;
 struct list_head hash;
 uint8_t mode;
 uint64_t phys;
 ihk_atomic_t count;
 ihk_atomic64_t mapped;
 off_t offset;
 int pgshift;
};


enum page_mode {
 PM_NONE = 0x00,
 PM_PENDING_FREE = 0x01,
 PM_WILL_PAGEIO = 0x02,
 PM_PAGEIO = 0x03,
 PM_DONE_PAGEIO = 0x04,
 PM_PAGEIO_EOF = 0x05,
 PM_PAGEIO_ERROR = 0x06,
 PM_MAPPED = 0x07,
};

struct page *phys_to_page(uintptr_t phys);
uintptr_t page_to_phys(struct page *page);
int page_unmap(struct page *page);
void page_map_count_inc_result(struct page *page);
void page_map_body_result(struct page *page,
  void (*count_inc_fn)(struct page *page));
struct page *phys_to_page_insert_hash(uint64_t phys);
int page_mode_in_memobj_result(int mode);
int page_multi_mapped_result(int count);
int page_is_in_memobj_body_result(struct page *page);
int page_is_multi_mapped_body_result(struct page *page);

void begin_free_pages_pending(void);
void finish_free_pages_pending(void);
void page_map(struct page *page);
int page_is_in_memobj(struct page *page);
int page_is_multi_mapped(struct page *page);


extern int anon_on_demand;



extern int xpmem_page_in_remote_on_attach;
# 24 "/home/holden/mckernel/lib/include/ihk/mm.h" 2
# 1 "/home/holden/mckernel/lib/include/ihk/debug.h" 1





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
# 25 "/home/holden/mckernel/lib/include/ihk/mm.h" 2

struct memobj;
struct process_vm;
struct vm_range;

enum ihk_mc_gma_type {
 IHK_MC_GMA_MAP_START,
 IHK_MC_GMA_MAP_END,
 IHK_MC_GMA_AVAIL_START,
 IHK_MC_GMA_AVAIL_END,
 IHK_MC_GMA_HEAP_START,
 IHK_MC_NR_RESERVED_AREAS,
 IHK_MC_RESERVED_AREA_START,
 IHK_MC_RESERVED_AREA_END,
};

extern unsigned long bootstrap_mem_end;

enum ihk_mc_ma_type {
 IHK_MC_MA_AVAILABLE,
 IHK_MC_MA_RESERVED,
 IHK_MC_MA_SPECIAL,
};

typedef unsigned long ihk_mc_ap_flag;
# 66 "/home/holden/mckernel/lib/include/ihk/mm.h"
enum ihk_mc_pt_prepare_flag {
 IHK_MC_PT_FIRST_LEVEL,
 IHK_MC_PT_LAST_LEVEL,
};

enum visit_pte_flag {
 VPTEF_SKIP_NULL = 0x0001,

 VPTEF_DEFAULT = 0,
};

struct ihk_mc_memory_area {
 unsigned long start;
 unsigned long size;
 enum ihk_mc_ma_type type;
};

struct ihk_mc_memory_node {
 int node;
 int nareas;
 struct ihk_mc_memory_area *areas;
};

unsigned long ihk_mc_get_memory_address(enum ihk_mc_gma_type, int);

struct ihk_page_allocator_desc;
void ihk_mc_reserve_arch_pages(struct ihk_page_allocator_desc *pa_allocator,
  unsigned long start, unsigned long end,
  void (*cb)(struct ihk_page_allocator_desc *,
   unsigned long, unsigned long, int));

struct ihk_mc_pa_ops {
 void *(*alloc_page)(int, int, ihk_mc_ap_flag, int node, int is_user, uintptr_t virt_addr);
 void (*free_page)(void *, int, int is_user);

 void *(*alloc)(int, ihk_mc_ap_flag);
 void (*free)(void *);
};

void ihk_mc_set_page_allocator(struct ihk_mc_pa_ops *);
void ihk_mc_set_page_fault_handler(void (*h)(void *, uint64_t, void *));

unsigned long ihk_mc_map_memory(void *os, unsigned long phys,
                                unsigned long size);
void ihk_mc_unmap_memory(void *os, unsigned long phys, unsigned long size);

void *ihk_mc_map_virtual(unsigned long phys, int npages,
                         enum ihk_mc_pt_attribute attr);
void ihk_mc_unmap_virtual(void *va, int npages);

extern void *sbox_base;
extern unsigned int free_bitmap_micpa;
void ihk_mc_map_micpa(unsigned long host_pa, unsigned long* mic_pa);
int ihk_mc_free_micpa(unsigned long mic_pa);
void ihk_mc_clean_micpa(void);

void *_ihk_mc_alloc_aligned_pages_node(int npages, int p2align,
 ihk_mc_ap_flag flag, int node, int is_user, uintptr_t virt_addr, char *file, int line);
void *ihk_mc_alloc_aligned_pages_node(int npages, int p2align,
 ihk_mc_ap_flag flag, int node);
void *ihk_mc_alloc_aligned_pages_node_user(int npages, int p2align,
 ihk_mc_ap_flag flag, int node, uintptr_t virt_addr);
void *ihk_mc_alloc_aligned_pages(int npages, int p2align,
 ihk_mc_ap_flag flag);
void *ihk_mc_alloc_aligned_pages_user(int npages, int p2align,
 ihk_mc_ap_flag flag, uintptr_t virt_addr);
void *ihk_mc_alloc_pages(int npages, ihk_mc_ap_flag flag);
void *ihk_mc_alloc_pages_user(int npages, ihk_mc_ap_flag flag,
 uintptr_t virt_addr);

void _ihk_mc_free_pages(void *ptr, int npages, int is_user, char *file, int line);
void ihk_mc_free_pages(void *ptr, int npages);
void ihk_mc_free_pages_user(void *ptr, int npages);

void *ihk_mc_allocate(int size, int flag);
void ihk_mc_free(void *p);

int arch_get_smaller_page_size(void *args, size_t origsize, size_t *sizep, int *p2alignp);

typedef void *page_table_t;

int ihk_mc_pt_set_page(page_table_t pt, void *virt, unsigned long phys,
                       enum ihk_mc_pt_attribute attr);
int ihk_mc_pt_set_large_page(page_table_t pt, void *virt,
                       unsigned long phys, enum ihk_mc_pt_attribute attr);
int ihk_mc_pt_change_page(page_table_t pt, void *virt,
                          enum ihk_mc_pt_attribute);
int ihk_mc_pt_clear_page(page_table_t pt, void *virt);
int ihk_mc_pt_clear_large_page(page_table_t pt, void *virt);
int ihk_mc_clear_kernel_range(void *start, void *end);
int ihk_mc_pt_clear_range(page_table_t pt, struct process_vm *vm,
  void *start, void *end);
int ihk_mc_pt_free_range(page_table_t pt, struct process_vm *vm,
  void *start, void *end, struct memobj *memobj);
int ihk_mc_pt_change_attr_range(page_table_t pt, void *start, void *end,
  enum ihk_mc_pt_attribute clrattr,
  enum ihk_mc_pt_attribute setattr);
pte_t *ihk_mc_pt_lookup_pte(page_table_t pt, void *virt, int pgshift, void **pgbasep, size_t *pgsizep, int *p2alignp);
pte_t *ihk_mc_pt_lookup_fault_pte(struct process_vm *vm, void *virt,
  int pgshift, void **basep, size_t *sizep, int *p2alignp);
int ihk_mc_pt_set_range(page_table_t pt, struct process_vm *vm, void *start,
  void *end, uintptr_t phys, enum ihk_mc_pt_attribute attr,
  int pgshift, struct vm_range *range, int overwrite);
int ihk_mc_pt_set_pte(page_table_t pt, pte_t *ptep, size_t pgsize, uintptr_t phys, enum ihk_mc_pt_attribute attr);
int ihk_mc_pt_prepare_map(page_table_t pt, void *virt, unsigned long size,
                          enum ihk_mc_pt_prepare_flag);
int ihk_mc_pt_split(page_table_t pt, struct process_vm *vm,
  struct vm_range *range, void *addr);
int is_splitable(struct page *page, uint32_t memobj_flags);

typedef int pte_visitor_t(void *arg, page_table_t pt, pte_t *ptep,
  void *pgaddr, int pgshift);
int visit_pte_range(page_table_t pt, void *start, void *end, int pgshift,
  enum visit_pte_flag flags, pte_visitor_t *funcp, void *arg);
int visit_pte_range_safe(page_table_t pt, void *start, void *end, int pgshift,
  enum visit_pte_flag flags, pte_visitor_t *funcp, void *arg);
int move_pte_range(page_table_t pt, struct process_vm *vm,
       void *src, void *dest, size_t size, struct vm_range *range);

struct page_table *ihk_mc_pt_create(ihk_mc_ap_flag ap_flag);

void ihk_mc_pt_destroy(struct page_table *pt);
void ihk_mc_load_page_table(struct page_table *pt);
int ihk_mc_pt_virt_to_phys_size(struct page_table *pt,
                           const void *virt,
         unsigned long *phys,
         unsigned long *size);
int ihk_mc_pt_virt_to_phys(struct page_table *pt,
                           const void *virt, unsigned long *phys);
uint64_t ihk_mc_pt_virt_to_pagemap(struct page_table *pt, unsigned long virt);

int ihk_mc_get_nr_numa_nodes(void);
struct ihk_mc_numa_node *ihk_mc_get_numa_node_by_distance(int i);
void ihk_numa_zero_free_pages(struct ihk_mc_numa_node *__node);
extern int zero_at_free;

struct smp_coreset;
int ihk_mc_get_numa_node(int id, int *linux_numa_id, int *type);
int ihk_mc_get_numa_distance(int i, int j);
int ihk_mc_get_nr_memory_chunks(void);
int ihk_mc_get_linux_default_huge_page_shift(void);
int ihk_mc_get_memory_chunk(int id,
 unsigned long *start,
 unsigned long *end,
 int *numa_id);






void remote_flush_tlb_cpumask(struct process_vm *vm,
  unsigned long addr, int cpu_id);
void remote_flush_tlb_array_cpumask(struct process_vm *vm,
  unsigned long *addr,
  int nr_addr,
  int cpu_id);

int ihk_get_kmsg_buf(unsigned long *addr, unsigned long *size);
char *ihk_get_kargs(void);

int ihk_set_monitor(unsigned long addr, unsigned long size);
int ihk_set_rusage(unsigned long addr, unsigned long size);
int ihk_set_multi_intr_mode_addr(unsigned long addr);
int ihk_set_nmi_mode_addr(unsigned long addr);

extern void (*__tlb_flush_handler)(int vector);

struct tlb_flush_entry {
 struct process_vm *vm;
 unsigned long *addr;
 int nr_addr;
 ihk_atomic_t pending;
 ihk_spinlock_t lock;
} __attribute__((aligned(64)));

extern struct tlb_flush_entry tlb_flush_vector[64];

void ihk_mc_set_dump_level(unsigned int level);
unsigned int ihk_mc_get_dump_level(void);
struct ihk_dump_page_set *ihk_mc_get_dump_page_set(void);
struct ihk_dump_page *ihk_mc_get_dump_page(void);
void ihk_mc_query_mem_areas(void);
void ihk_mc_clear_dump_page_completion(void);
void ihk_mc_query_mem_user_page(void *dump_page_set);
void ihk_mc_query_mem_free_page(void *dump_page_set);
int ihk_mc_chk_page_address(pte_t mem_addr);
int ihk_mc_get_mem_user_page(void *arg0, page_table_t pt, pte_t *ptep, void *pgaddr, int pgshift);

extern int zero_at_free;





struct ihk_mc_page_cache_header;

struct ihk_mc_page_cache_header {
 struct ihk_mc_page_cache_header *next;
};

void ihk_mc_page_cache_free(struct ihk_mc_page_cache_header *cache, void *page);
void ihk_mc_page_cache_prealloc(struct ihk_mc_page_cache_header *cache,
  int nr_pages, int nr_elem);
void *ihk_mc_page_cache_alloc(struct ihk_mc_page_cache_header *cache,
  int nr_pages);
# 20 "/home/holden/mckernel/kernel/include/process.h" 2


# 1 "/home/holden/mckernel/kernel/include/rbtree.h" 1
# 34 "/home/holden/mckernel/kernel/include/rbtree.h"
# 1 "/home/holden/mckernel/kernel/include/lwk/stddef.h" 1
# 35 "/home/holden/mckernel/kernel/include/rbtree.h" 2

struct rb_node {
 unsigned long __rb_parent_color;
 struct rb_node *rb_right;
 struct rb_node *rb_left;
} __attribute__((aligned(sizeof(long))));


struct rb_root {
 struct rb_node *rb_node;
};


struct rb_node *rb_parent(const struct rb_node *r);



int rb_empty_root(const struct rb_root *root);



int rb_empty_node(const struct rb_node *node);
void rb_clear_node(struct rb_node *node);





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


extern void rb_replace_node(struct rb_node *victim, struct rb_node *new,
       struct rb_root *root);

void rb_link_node(struct rb_node *node, struct rb_node *parent,
    struct rb_node **rb_link);

struct rb_node *rb_preorder_dfs_search(const struct rb_root *root,
 bool (*__cond)(struct rb_node *, void *arg), void *__cond_arg);
# 23 "/home/holden/mckernel/kernel/include/process.h" 2
# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/signal.h" 1
# 21 "/home/holden/mckernel/arch/x86_64/kernel/include/signal.h"
typedef unsigned long int __sigset_t;
int valid_signal(unsigned long sig);
__sigset_t __sigmask(unsigned long sig);

typedef struct {
 __sigset_t __val[(64 / 64)];
} sigset_t;





struct sigaction {
 void (*sa_handler)(int);
 unsigned long sa_flags;
 void (*sa_restorer)(int);
 sigset_t sa_mask;
};

typedef void __sig_fn_t(int);
typedef __sig_fn_t *__sig_handler_t;
# 54 "/home/holden/mckernel/arch/x86_64/kernel/include/signal.h"
struct k_sigaction {
        struct sigaction sa;
};

typedef struct sigaltstack {
 void *ss_sp;
 int ss_flags;
 size_t ss_size;
} stack_t;





typedef union sigval {
 int sival_int;
 void *sival_ptr;
} sigval_t;




typedef struct siginfo {
 int si_signo;
 int si_errno;

 int si_code;
# 145 "/home/holden/mckernel/arch/x86_64/kernel/include/signal.h"
 union {
  int _pad[((128 / sizeof (int)) - 4)];


  struct {
   int si_pid;
   int si_uid;
  } _kill;


  struct {
   int si_tid;
   int si_overrun;
   sigval_t si_sigval;
  } _timer;


  struct {
   int si_pid;
   int si_uid;
   sigval_t si_sigval;
  } _rt;


  struct {
   int si_pid;
   int si_uid;
   int si_status;
   long si_utime;
   long si_stime;
  } _sigchld;


  struct {
   void *si_addr;
  } _sigfault;


  struct {
   long int si_band;
   int si_fd;
  } _sigpoll;
 } _sifields;
} siginfo_t;

struct signalfd_siginfo {
 unsigned int ssi_signo;
 int ssi_errno;
 int ssi_code;
 unsigned int ssi_pid;
 unsigned int ssi_uid;
 int ssi_fd;
 unsigned int ssi_tid;
 unsigned int ssi_band;
 unsigned int ssi_overrun;
 unsigned int ssi_trapno;
 int ssi_status;
 int ssi_int;
 unsigned long ssi_ptr;
 unsigned long ssi_utime;
 unsigned long ssi_stime;
 unsigned long ssi_addr;
 unsigned short ssi_addr_lsb;

 char __pad[46];
};
# 24 "/home/holden/mckernel/kernel/include/process.h" 2
# 1 "/home/holden/mckernel/kernel/include/memobj.h" 1
# 23 "/home/holden/mckernel/kernel/include/memobj.h"
# 1 "/home/holden/mckernel/kernel/include/pager.h" 1
# 16 "/home/holden/mckernel/kernel/include/pager.h"
# 1 "/home/holden/mckernel/lib/include/limits.h" 1
# 29 "/home/holden/mckernel/lib/include/limits.h"
typedef uint64_t phys_addr_t;
# 17 "/home/holden/mckernel/kernel/include/pager.h" 2

enum pager_op {
 PAGER_REQ_CREATE = 0x0001,
 PAGER_REQ_RELEASE = 0x0002,
 PAGER_REQ_READ = 0x0003,
 PAGER_REQ_WRITE = 0x0004,
 PAGER_REQ_MAP = 0x0005,
 PAGER_REQ_PFN = 0x0006,
 PAGER_REQ_UNMAP = 0x0007,
};




struct pager_create_result {
 uintptr_t handle;
 int maxprot;
 uint32_t flags;
 size_t size;
 int pgshift;
 char path[4096];
};
# 48 "/home/holden/mckernel/kernel/include/pager.h"
struct pager_map_result {
 uintptr_t handle;
 int maxprot;
 int8_t padding[4];
 char path[4096];
};
# 24 "/home/holden/mckernel/kernel/include/memobj.h" 2

# 1 "/home/holden/mckernel/kernel/include/object_helpers.h" 1
# 127 "/home/holden/mckernel/kernel/include/object_helpers.h"
int memobj_unref_should_free_result(int refcnt);
int memobj_op_present_result(uintptr_t op);
int memobj_missing_page_op_result(void);
uintptr_t memobj_missing_copy_page_result(void);
int memobj_default_page_op_result(void);
int memobj_has_pager_flags_result(unsigned int flags);
int memobj_is_removable_flags_result(unsigned int flags);
int memobj_flushable_page_result(int has_page, int page_in_memobj);
int memobj_flushable_obj_result(int has_memobj, unsigned int flags);
int memobj_is_freeable_result(int has_memobj, unsigned int flags);
int memobj_callable_remap_file_pages_result(int has_memobj,
         unsigned int flags);

int fileobj_page_hash_result(off_t off);
int fileobj_page_mode_valid_result(int mode);
int fileobj_lookup_ref_keep_result(int refcnt_after_inc);
int fileobj_create_base_flags_result(int mmap_flags);
int fileobj_apply_result_flags_result(int base_flags, int pager_flags);
int fileobj_status_from_flags_result(int flags);
int fileobj_hugetlbfs_result(int flags);
int fileobj_premap_zerofill_result(int flags);
int fileobj_premap_npages_result(size_t size);
int fileobj_validate_p2align_result(int p2align);
int fileobj_get_page_action_result(int has_page, int page_mode, int *errorp);
int fileobj_pageio_zero_result(int flags);
int fileobj_pageio_mode_after_read_result(ssize_t ssize, size_t pgsize);
int fileobj_flush_skip_result(int flags, int has_page);
int fileobj_initial_refcnt_result(void);
unsigned long fileobj_initial_sref_result(void);
int fileobj_premap_start_node_result(int nr_numa_nodes);
int fileobj_premap_next_node_result(int node, int nr_numa_nodes);
size_t fileobj_pages_bytes_result(int nr_pages);
int fileobj_premap_page_index_result(off_t off);
int fileobj_alloc_npages_result(int p2align);
unsigned long fileobj_alloc_flags_result(int flags);
size_t fileobj_alloc_size_result(int npages);
size_t fileobj_pageio_pgsize_result(int p2align);
int fileobj_pageio_should_schedule_result(int attempts);
int fileobj_new_page_mode_result(void);
int fileobj_mapped_mode_result(void);
int fileobj_path_present_result(unsigned long value);
int fileobj_invalid_page_count_result(int count);
int fileobj_should_free_hashed_page_result(int count, int page_unmap_result);
int fileobj_premap_page_present_result(uintptr_t page);
int fileobj_lookup_page_error_result(int has_page);
unsigned long fileobj_next_sref_result(unsigned long sref);
int fileobj_premap_interleave_result(unsigned long mpol_flags);
typedef void *(*fileobj_phys_to_page_fn_t)(uintptr_t phys);
typedef off_t (*fileobj_page_offset_fn_t)(void *page);
typedef ssize_t (*fileobj_write_fn_t)(uintptr_t handle, off_t offset,
          size_t pgsize, uintptr_t phys);
typedef void (*fileobj_log_fn_t)(int event, void *memobj, void *obj,
     uintptr_t phys, size_t pgsize,
     ssize_t result);
typedef void (*fileobj_lock_fn_t)(void *lock, void *node);
typedef void (*fileobj_unlock_fn_t)(void *lock, void *node);
typedef void *(*fileobj_lookup_fn_t)(void *obj, int hash, off_t off);
typedef uintptr_t (*fileobj_page_phys_fn_t)(void *page);
typedef void *(*fileobj_list_first_fn_t)(void *head);
typedef void *(*fileobj_list_next_fn_t)(void *head, void *obj);
typedef uintptr_t (*fileobj_handle_fn_t)(void *obj);
typedef int (*fileobj_ref_fn_t)(void *obj);
typedef void (*fileobj_dec_fn_t)(void *obj);
typedef int (*fileobj_page_mode_fn_t)(void *page);
typedef void (*fileobj_page_set_mode_fn_t)(void *page, int mode);
typedef void (*fileobj_pageio_zero_fn_t)(uintptr_t phys);
typedef ssize_t (*fileobj_pageio_read_fn_t)(uintptr_t handle, off_t off,
         size_t pgsize, uintptr_t phys);
typedef void (*fileobj_void_fn_t)(void);
typedef void (*fileobj_pageio_log_fn_t)(int event, void *obj, off_t off,
     size_t pgsize, long value);
typedef void (*fileobj_pageio_panic_fn_t)(void *obj, off_t off,
       size_t pgsize, int mode);
typedef void (*fileobj_ptr_void_fn_t)(void *ptr);
typedef void *(*fileobj_ptr_result_fn_t)(void *ptr);
typedef void *(*fileobj_alloc_fn_t)(size_t size, unsigned long flags);
typedef void (*fileobj_copy_fn_t)(void *dst, const void *src, size_t len);
typedef void (*fileobj_ptr_set_fn_t)(void *ptr, void *value);
typedef void (*fileobj_size_set_fn_t)(void *ptr, size_t value);
typedef int (*fileobj_int_get_fn_t)(void *ptr);
typedef void (*fileobj_int_set_fn_t)(void *ptr, int value);
typedef unsigned long (*fileobj_ulong_get_fn_t)(void *ptr);
typedef void (*fileobj_ulong_set_fn_t)(void *ptr, unsigned long value);
typedef void (*fileobj_create_log_fn_t)(int event, void *obj,
     const void *path, long value);
typedef void (*fileobj_memzero_fn_t)(void *ptr, size_t len);
typedef void *(*fileobj_alloc_pages_node_fn_t)(int npages, int p2align,
            unsigned long flags, int node,
            uintptr_t virt_addr);
typedef void *(*fileobj_alloc_pages_fn_t)(int npages, unsigned long flags,
       uintptr_t virt_addr);
typedef void (*fileobj_page_array_set_fn_t)(void *pages, int index,
         void *page);
typedef void *(*fileobj_page_array_cmpxchg_fn_t)(void *pages, int index,
       void *old, void *new_value);
typedef void (*fileobj_rss_add_fn_t)(size_t size, size_t pgsize);
typedef void (*fileobj_create_premap_log_fn_t)(int event, void *obj,
            void *page, long value);
typedef void (*fileobj_get_log_fn_t)(int event, void *obj, off_t off,
         int p2align, uintptr_t virt_addr,
         uintptr_t physp_addr, void *page,
         uintptr_t phys, long value);
typedef uintptr_t (*fileobj_ptr_phys_fn_t)(void *ptr);
typedef void *(*fileobj_phys_to_page_insert_fn_t)(uintptr_t phys);
typedef void (*fileobj_page_offset_set_fn_t)(void *page, off_t off);
typedef void (*fileobj_long_set_fn_t)(void *page, long value);
typedef void (*fileobj_page_hash_insert_fn_t)(void *obj, void *page,
           int hash);
typedef void (*fileobj_pageio_args_set_fn_t)(void *args, void *obj,
          off_t off, size_t pgsize);
typedef void (*fileobj_pgio_set_fn_t)(void *thread, void *pageio_fn,
          void *args);
typedef void (*fileobj_get_regular_log_fn_t)(int event, void *obj, off_t off,
          int p2align, uintptr_t virt_addr,
          uintptr_t physp_addr, void *page,
          uintptr_t phys, uintptr_t value,
          size_t size, int mode, int count);
typedef void (*fileobj_get_regular_panic_fn_t)(void *obj, off_t off,
            void *page, int mode);
typedef void *(*fileobj_phys_to_virt_fn_t)(uintptr_t phys);
typedef int (*fileobj_int_fn_t)(void *ptr);
typedef void (*fileobj_free_pages_fn_t)(void *addr, int npages);
typedef void (*fileobj_rss_sub_fn_t)(size_t size, size_t pgsize);
typedef int (*fileobj_release_fn_t)(uintptr_t handle, unsigned long sref);
typedef void *(*fileobj_page_array_at_fn_t)(void *pages, int index);
typedef void (*fileobj_free_log_fn_t)(int event, void *obj, void *page,
          uintptr_t phys, long value,
          unsigned long flags);
int fileobj_flush_page_body_result(
 void *memobj, void *obj, int flags, uintptr_t handle, uintptr_t phys,
 size_t pgsize, fileobj_phys_to_page_fn_t phys_to_page_fn,
 fileobj_page_offset_fn_t page_offset_fn, fileobj_write_fn_t write_fn,
 fileobj_log_fn_t log_fn);
int fileobj_invalidate_page_body_result(void *memobj, uintptr_t phys,
     size_t pgsize,
     fileobj_log_fn_t log_fn);
int fileobj_lookup_page_body_result(
 void *obj, off_t off, int p2align, uintptr_t *physp, void *lock,
 void *lock_node, fileobj_lock_fn_t lock_fn,
 fileobj_unlock_fn_t unlock_fn, fileobj_lookup_fn_t lookup_fn,
 fileobj_page_phys_fn_t page_phys_fn);
void *fileobj_obj_list_lookup_body_result(
 uintptr_t handle, void *list_head,
 fileobj_list_first_fn_t first_fn,
 fileobj_list_next_fn_t next_fn,
 fileobj_handle_fn_t handle_fn,
 fileobj_ref_fn_t ref_fn,
 fileobj_dec_fn_t dec_fn);
int fileobj_create_publish_body_result(
 void *obj, int is_new, int mmap_flags, int pager_flags,
 size_t result_size, fileobj_ptr_void_fn_t list_insert_fn,
 fileobj_size_set_fn_t size_set_fn,
 fileobj_int_set_fn_t flags_set_fn,
 fileobj_int_set_fn_t status_set_fn,
 fileobj_int_set_fn_t refcnt_set_fn,
 fileobj_ulong_get_fn_t sref_get_fn,
 fileobj_ulong_set_fn_t sref_set_fn);
int fileobj_create_path_body_result(
 void *obj, int path_first, const void *path_src, size_t path_len,
 unsigned long alloc_flags, fileobj_alloc_fn_t alloc_fn,
 fileobj_copy_fn_t copy_fn, fileobj_ptr_set_fn_t path_set_fn,
 fileobj_create_log_fn_t log_fn);
int fileobj_create_premap_body_result(
 void *obj, int flags, size_t result_size, unsigned long mpol_flags,
 int nr_numa_nodes, uintptr_t virt_addr, unsigned long alloc_flags,
 fileobj_alloc_fn_t alloc_fn, fileobj_ptr_set_fn_t pages_set_fn,
 fileobj_int_set_fn_t nr_pages_set_fn,
 fileobj_memzero_fn_t zero_fn,
 fileobj_alloc_pages_node_fn_t alloc_pages_node_fn,
 fileobj_page_array_set_fn_t page_set_fn,
 fileobj_rss_add_fn_t rss_add_fn,
 fileobj_create_premap_log_fn_t log_fn);
int fileobj_get_premap_body_result(
 void *obj, void *pages, off_t off, int p2align, uintptr_t virt_addr,
 uintptr_t *physp, unsigned long alloc_flags,
 fileobj_alloc_pages_fn_t alloc_pages_fn,
 fileobj_memzero_fn_t zero_fn,
 fileobj_page_array_at_fn_t page_at_fn,
 fileobj_page_array_cmpxchg_fn_t cmpxchg_fn,
 fileobj_free_pages_fn_t free_pages_fn,
 fileobj_ptr_phys_fn_t phys_fn,
 fileobj_rss_add_fn_t rss_add_fn,
 fileobj_get_log_fn_t log_fn);
int fileobj_get_regular_body_result(
 void *obj, int flags, off_t off, int p2align, uintptr_t virt_addr,
 uintptr_t *physp, void *thread, void *pageio_fn, void *lock,
 void *lock_node, size_t args_size, unsigned long args_alloc_flags,
 fileobj_lock_fn_t lock_fn, fileobj_unlock_fn_t unlock_fn,
 fileobj_lookup_fn_t lookup_fn, fileobj_alloc_fn_t alloc_fn,
 fileobj_ptr_void_fn_t free_fn, fileobj_alloc_pages_fn_t alloc_pages_fn,
 fileobj_ptr_phys_fn_t phys_fn,
 fileobj_phys_to_page_insert_fn_t page_insert_lookup_fn,
 fileobj_page_mode_fn_t page_mode_fn,
 fileobj_page_offset_set_fn_t page_offset_set_fn,
 fileobj_long_set_fn_t page_count_set_fn,
 fileobj_long_set_fn_t page_mapped_set_fn,
 fileobj_page_hash_insert_fn_t hash_insert_fn,
 fileobj_page_set_mode_fn_t page_mode_set_fn,
 fileobj_ref_fn_t memobj_ref_fn,
 fileobj_pageio_args_set_fn_t args_set_fn,
 fileobj_pgio_set_fn_t pgio_set_fn,
 fileobj_ptr_void_fn_t page_count_inc_fn,
 fileobj_page_phys_fn_t page_phys_fn,
 fileobj_int_fn_t page_count_fn,
 fileobj_ptr_void_fn_t page_remove_fn,
 fileobj_phys_to_virt_fn_t phys_to_virt_fn,
 fileobj_int_fn_t page_unmap_fn,
 fileobj_free_pages_fn_t free_pages_fn,
 fileobj_get_regular_log_fn_t log_fn,
 fileobj_get_regular_panic_fn_t panic_fn);
int fileobj_do_pageio_body_result(
 void *obj, int flags, uintptr_t handle, off_t off, size_t pgsize,
 void *lock, void *lock_node, fileobj_lock_fn_t lock_fn,
 fileobj_unlock_fn_t unlock_fn, fileobj_lookup_fn_t lookup_fn,
 fileobj_page_mode_fn_t page_mode_fn,
 fileobj_page_set_mode_fn_t page_set_mode_fn,
 fileobj_page_phys_fn_t page_phys_fn,
 fileobj_pageio_zero_fn_t zero_fn,
 fileobj_pageio_read_fn_t read_fn,
 fileobj_void_fn_t schedule_fn,
 fileobj_void_fn_t pause_fn,
 fileobj_pageio_log_fn_t log_fn,
 fileobj_pageio_panic_fn_t panic_fn);
int fileobj_free_body_result(
 void *obj, int flags, uintptr_t handle, unsigned long sref,
 void *pages, int nr_pages, void *path, void *list_lock,
 void *lock_node, fileobj_lock_fn_t lock_fn,
 fileobj_unlock_fn_t unlock_fn, fileobj_ptr_void_fn_t list_remove_fn,
 fileobj_ptr_result_fn_t page_first_fn,
 fileobj_ptr_void_fn_t page_remove_fn,
 fileobj_page_phys_fn_t page_phys_fn,
 fileobj_phys_to_virt_fn_t phys_to_virt_fn,
 fileobj_int_fn_t page_count_fn,
 fileobj_int_fn_t page_unmap_fn,
 fileobj_free_pages_fn_t free_pages_fn,
 fileobj_rss_sub_fn_t rss_sub_fn,
 fileobj_ptr_void_fn_t free_fn,
 fileobj_release_fn_t release_fn,
 fileobj_page_array_at_fn_t page_at_fn,
 fileobj_free_log_fn_t log_fn);

size_t devobj_npages_result(size_t len);
size_t devobj_pfn_table_npages_result(size_t npages);
size_t devobj_pfn_table_bytes_result(size_t pfn_npages);
off_t devobj_pgoff_result(off_t off);
int devobj_get_page_index_result(off_t pgoff, off_t base_pgoff,
     size_t npages, int *ixp);
int devobj_cached_pfn_needs_fetch_result(uintptr_t pfn);
int devobj_pfn_present_result(uintptr_t pfn);
uintptr_t devobj_pfn_attr_result(uintptr_t pfn);
uintptr_t devobj_pfn_phys_result(uintptr_t pfn);
int devobj_pfn_absent_error_result(uintptr_t pfn);
int devobj_base_flags_result(void);
int devobj_initial_refcnt_result(void);
off_t devobj_pfn_request_offset_result(off_t off);
int devobj_should_store_pfn_result(uintptr_t current_pfn);
size_t devobj_map_size_result(void);
int devobj_path_present_result(unsigned long value);
int devobj_pfn_table_present_result(uintptr_t pfn_table);
uintptr_t devobj_mapped_pfn_result(uintptr_t mapped_pfn, uintptr_t attr);
typedef int (*devobj_unmap_fn_t)(uintptr_t handle);
typedef void (*devobj_free_pages_fn_t)(void *addr, size_t npages);
typedef void (*devobj_free_fn_t)(void *addr);
typedef void (*devobj_log_fn_t)(int event, void *memobj, void *obj,
    off_t off, off_t pgoff, int p2align,
    int ix, int error, uintptr_t pfn);
typedef void (*devobj_profile_fn_t)(void);
typedef unsigned long (*devobj_lock_fn_t)(void *lock);
typedef void (*devobj_unlock_fn_t)(void *lock, unsigned long irqstate);
typedef uintptr_t (*devobj_pfn_load_fn_t)(void *obj, int ix);
typedef int (*devobj_fetch_pfn_fn_t)(void *memobj, void *obj,
         uintptr_t handle, off_t off,
         int p2align, uintptr_t *pfnp);
typedef int (*devobj_pfn_write_combined_fn_t)(uintptr_t pfn);
typedef uintptr_t (*devobj_map_memory_fn_t)(uintptr_t phys, size_t size);
typedef void (*devobj_pfn_store_fn_t)(void *obj, int ix, uintptr_t pfn);
int devobj_free_body_result(void *obj, void *path, void *pfn_table,
       uintptr_t handle, size_t npages,
       devobj_unmap_fn_t unmap_fn,
       devobj_free_pages_fn_t free_pages_fn,
       devobj_free_fn_t free_fn,
       devobj_log_fn_t log_fn);
int devobj_get_page_body_result(
 void *memobj, void *obj, uintptr_t handle, off_t off, int p2align,
 off_t pfn_pgoff, size_t npages, void *pfn_table_lock,
 uintptr_t *physp, unsigned long *flagp, devobj_profile_fn_t profile_fn,
 devobj_lock_fn_t lock_fn, devobj_unlock_fn_t unlock_fn,
 devobj_pfn_load_fn_t pfn_load_fn, devobj_fetch_pfn_fn_t fetch_pfn_fn,
 devobj_pfn_write_combined_fn_t write_combined_fn,
 devobj_map_memory_fn_t map_memory_fn,
 devobj_pfn_store_fn_t pfn_store_fn,
 devobj_log_fn_t log_fn);

struct ikc_scd_packet;
typedef unsigned long (*procfs_thread_phys_fn_t)(void *addr);
typedef int (*procfs_thread_send_fn_t)(void *channel,
           struct ikc_scd_packet *packet);
typedef void (*procfs_thread_pause_fn_t)(void);
int procfs_thread_ctl_result(void *channel, struct ikc_scd_packet *packet,
        int *donep, int msg, int osnum, int cpu_id,
        int pid, int tid,
        procfs_thread_phys_fn_t phys_fn,
        procfs_thread_send_fn_t send_fn,
        procfs_thread_pause_fn_t pause_fn);
typedef void (*procfs_answer_send_fn_t)(void *channel,
     struct ikc_scd_packet *packet);
int procfs_answer_result(void *channel, struct ikc_scd_packet *request,
    int err, procfs_answer_send_fn_t send_fn);
struct mckernel_procfs_buffer;
struct procfs_read;
typedef struct mckernel_procfs_buffer *(*procfs_buf_alloc_fn_t)(
  unsigned long *phys, long pos);
typedef void (*procfs_buf_free_top_fn_t)(
  struct mckernel_procfs_buffer *top);
typedef void *(*procfs_buf_copy_fn_t)(void *dst, const void *src,
          size_t len);
typedef struct mckernel_procfs_buffer *(*procfs_buf_phys_to_virt_fn_t)(
  unsigned long phys);
typedef void (*procfs_buf_free_page_fn_t)(
  struct mckernel_procfs_buffer *pbuf);
typedef unsigned long (*procfs_buf_phys_fn_t)(
  struct mckernel_procfs_buffer *pbuf);
typedef void *(*procfs_buf_page_alloc_fn_t)(int npages,
         unsigned long flags);
typedef int (*procfs_mem_page_fault_fn_t)(void *vm, unsigned long offset,
       unsigned long reason);
typedef int (*procfs_mem_virt_to_phys_fn_t)(void *page_table,
         unsigned long offset,
         unsigned long *physp);
typedef int (*procfs_mem_is_memory_fn_t)(unsigned long start,
      unsigned long end);
typedef void *(*procfs_mem_phys_to_virt_fn_t)(unsigned long phys);
typedef void *(*procfs_mem_copy_fn_t)(void *dst, const void *src, size_t len);
typedef unsigned long (*procfs_pagemap_value_fn_t)(void *page_table,
         unsigned long addr);
typedef unsigned long (*procfs_range_ulong_fn_t)(void *range, int field);
typedef const char *(*procfs_range_path_fn_t)(void *range);
typedef void *(*procfs_range_next_fn_t)(void *vm, void *range);
typedef int (*procfs_backlog_fn_t)(void *arg);
typedef void *(*procfs_backlog_alloc_fn_t)(unsigned long size,
        unsigned long flags);
typedef void (*procfs_backlog_copy_fn_t)(void *dst,
      struct ikc_scd_packet *src,
      unsigned long size);
typedef int (*procfs_backlog_add_fn_t)(procfs_backlog_fn_t backlog_fn,
           void *arg);
typedef void (*procfs_backlog_free_fn_t)(void *arg);
int procfs_buf_release_result(unsigned long phys,
         procfs_buf_phys_to_virt_fn_t phys_to_virt_fn,
         procfs_buf_free_page_fn_t free_page_fn);
struct mckernel_procfs_buffer *procfs_buf_alloc_result(
  unsigned long *phys, long pos,
  procfs_buf_page_alloc_fn_t alloc_fn,
  procfs_buf_phys_fn_t phys_fn, unsigned long alloc_flags);
int procfs_buf_add_result(struct mckernel_procfs_buffer **top,
     struct mckernel_procfs_buffer **cur,
     const void *buf, int len,
     procfs_buf_alloc_fn_t alloc_fn,
     procfs_buf_free_top_fn_t free_top_fn,
     procfs_buf_copy_fn_t copy_fn);
int procfs_release_request_result(struct procfs_read *request,
      procfs_buf_phys_to_virt_fn_t phys_to_virt_fn,
      procfs_buf_free_page_fn_t free_page_fn);
int procfs_finish_request_result(struct procfs_read *request, int ret, int eof,
     struct mckernel_procfs_buffer *buf_top,
     procfs_buf_phys_fn_t phys_fn);
int procfs_backlog_result(struct ikc_scd_packet *request,
     procfs_backlog_fn_t backlog_fn,
     procfs_backlog_alloc_fn_t alloc_fn,
     procfs_backlog_copy_fn_t copy_fn,
     procfs_backlog_add_fn_t add_fn,
     procfs_backlog_free_fn_t free_fn,
     unsigned long packet_size,
     unsigned long alloc_flags);
int procfs_root_entry_body_result(int entry_kind, const char *version,
      const char *buildid, int num_processors,
      int count,
      struct mckernel_procfs_buffer **top,
      struct mckernel_procfs_buffer **cur,
      procfs_buf_alloc_fn_t alloc_fn,
      procfs_buf_free_top_fn_t free_top_fn,
      procfs_buf_copy_fn_t copy_fn);
int procfs_pid_simple_entry_body_result(int entry_kind, const void *saved_auxv,
     const char *saved_cmdline,
     unsigned int saved_cmdline_len,
     const char *comm_fallback,
     struct mckernel_procfs_buffer **top,
     struct mckernel_procfs_buffer **cur,
     procfs_buf_alloc_fn_t alloc_fn,
     procfs_buf_free_top_fn_t free_top_fn,
     procfs_buf_copy_fn_t copy_fn);
int procfs_maps_body_result(void *vm, void *range, unsigned long vdso_addr,
       unsigned long vvar_addr, unsigned long brk_start,
       unsigned long brk_end_allocated, int count,
       struct mckernel_procfs_buffer **top,
       struct mckernel_procfs_buffer **cur,
       procfs_buf_alloc_fn_t alloc_fn,
       procfs_buf_free_top_fn_t free_top_fn,
       procfs_buf_copy_fn_t copy_fn,
       procfs_range_ulong_fn_t range_ulong_fn,
       procfs_range_path_fn_t range_path_fn,
       procfs_range_next_fn_t range_next_fn);
unsigned long procfs_locked_size_body_result(
  void *vm, void *range, procfs_range_ulong_fn_t range_ulong_fn,
  procfs_range_next_fn_t range_next_fn);
struct procfs_status_body_input {
 int pid;
 int ruid;
 int euid;
 int suid;
 int fsuid;
 int rgid;
 int egid;
 int sgid;
 int fsgid;
 int status;
 int nr_threads;
 unsigned long lockedsize;
 const char *cpu_bitmask;
 const char *cpu_list;
 const char *numa_bitmask;
 const char *numa_list;
};
int procfs_status_body_result(const struct procfs_status_body_input *input,
         int count, struct mckernel_procfs_buffer **top,
         struct mckernel_procfs_buffer **cur,
         procfs_buf_alloc_fn_t alloc_fn,
         procfs_buf_free_top_fn_t free_top_fn,
         procfs_buf_copy_fn_t copy_fn);
struct procfs_stat_body_input {
 int tid;
 const char *comm;
 char state;
 int ppid;
 int pid;
 int nr_threads;
 int cpu_id;
};
int procfs_stat_body_result(const struct procfs_stat_body_input *input,
       int count, struct mckernel_procfs_buffer **top,
       struct mckernel_procfs_buffer **cur,
       procfs_buf_alloc_fn_t alloc_fn,
       procfs_buf_free_top_fn_t free_top_fn,
       procfs_buf_copy_fn_t copy_fn);

int sysfs_path_error_result(ssize_t n, int path_is_absolute, size_t capacity);
int sysfs_special_kind_result(long client_ops);
int sysfs_string_nbits_result(size_t len);
int sysfs_response_error_result(ssize_t ssize);
int sysfs_param_sizes_valid_result(size_t create_size, size_t mkdir_size,
       size_t symlink_size, size_t lookup_size,
       size_t unlink_size, size_t setup_size);
size_t sysfs_data_bufsize_result(void);
int sysfs_packet_error_result(int send_error, int packet_error);
int sysfs_request_busy_result(int busy);
int sysfs_handle_pointer_valid_result(uintptr_t handlep);
ssize_t sysfs_default_response_ssize_result(void);
int sysfs_release_response_error_result(void);
int sysfss_packet_prepare_result(struct ikc_scd_packet *packet, int msg,
     int err, long arg1, long arg2);
int sysfs_request_packet_prepare_result(struct ikc_scd_packet *packet, int msg,
     long arg1);
int sysfs_request_handler_kind_result(int msg);
int sysfs_pointer_missing_result(uintptr_t ptr);
int sysfs_should_call_show_result(uintptr_t show);
int sysfs_should_call_store_result(uintptr_t store);
int sysfs_should_call_release_result(uintptr_t release);
typedef ssize_t (*sysfss_show_fn_t)(void *ops, void *instance, void *buf,
        size_t bufsize);
typedef ssize_t (*sysfss_store_fn_t)(void *ops, void *instance, void *buf,
         size_t size);
typedef void (*sysfss_release_fn_t)(void *ops, void *instance);
typedef int (*sysfss_send_fn_t)(int msg, int err, long arg1, long arg2);
typedef void (*sysfss_packet_show_fn_t)(long nodeh, void *ops,
     void *instance);
typedef void (*sysfss_packet_store_fn_t)(long nodeh, void *ops,
      void *instance, size_t size);
typedef void (*sysfss_packet_release_fn_t)(long nodeh, void *ops,
        void *instance);
typedef void (*sysfss_packet_unknown_fn_t)(int msg, int error, long arg1,
        long arg2, long arg3);
typedef void (*sysfss_req_log_fn_t)(int event, long nodeh, void *ops,
        void *instance, size_t size, int error,
        int packet_err, ssize_t ssize);
typedef int (*sysfs_request_send_fn_t)(int msg, long arg1);
typedef void (*sysfs_request_pause_fn_t)(void);
typedef void (*sysfs_request_barrier_fn_t)(void);
typedef void (*sysfs_request_log_fn_t)(int event, int msg, int error);
typedef void *(*sysfs_init_alloc_fn_t)(int npages, unsigned long flags);
typedef void (*sysfs_init_free_fn_t)(void *addr, int npages);
typedef long (*sysfs_init_phys_fn_t)(void *addr);
struct sysfs_req_create_param;
struct sysfs_bitmap_param;
int sysfs_setup_special_create_result(struct sysfs_req_create_param *param,
          struct sysfs_bitmap_param *pbp,
          sysfs_init_phys_fn_t phys_fn);
int sysfs_request_body_result(int msg, void *param, long param_rpa,
         sysfs_request_send_fn_t send_fn,
         sysfs_request_pause_fn_t pause_fn,
         sysfs_request_barrier_fn_t barrier_fn,
         long *handlep, int *phasep);
int sysfs_request_logged_result(int msg, void *param, long param_rpa,
    sysfs_request_send_fn_t send_fn,
    sysfs_request_pause_fn_t pause_fn,
    sysfs_request_barrier_fn_t barrier_fn,
    long *handle_dstp,
    sysfs_request_log_fn_t log_fn,
    int *phasep);
int sysfs_init_body_result(size_t create_size, size_t mkdir_size,
      size_t symlink_size, size_t lookup_size,
      size_t unlink_size, size_t setup_size,
      void **data_bufp, size_t *data_bufsizep,
      sysfs_init_alloc_fn_t alloc_fn,
      sysfs_init_free_fn_t free_fn,
      sysfs_init_phys_fn_t phys_fn,
      sysfs_request_send_fn_t send_fn,
      sysfs_request_pause_fn_t pause_fn,
      sysfs_request_barrier_fn_t barrier_fn,
      int *stagep, int *phasep);
int sysfss_req_show_body_result(long nodeh, void *ops, void *instance,
    void *data_buf, size_t data_bufsize,
    sysfss_show_fn_t show_fn,
    sysfss_send_fn_t send_fn, ssize_t *ssizep,
    int *packet_errp);
int sysfss_req_show_logged_result(long nodeh, void *ops, void *instance,
      void *data_buf, size_t data_bufsize,
      uintptr_t show, sysfss_show_fn_t show_fn,
      sysfss_send_fn_t send_fn,
      sysfss_req_log_fn_t log_fn,
      ssize_t *ssizep, int *packet_errp);
int sysfss_req_store_body_result(long nodeh, void *ops, void *instance,
     void *data_buf, size_t size,
     sysfss_store_fn_t store_fn,
     sysfss_send_fn_t send_fn, ssize_t *ssizep,
     int *packet_errp);
int sysfss_req_store_logged_result(long nodeh, void *ops, void *instance,
       void *data_buf, size_t size,
       uintptr_t store, sysfss_store_fn_t store_fn,
       sysfss_send_fn_t send_fn,
       sysfss_req_log_fn_t log_fn,
       ssize_t *ssizep, int *packet_errp);
int sysfss_req_release_body_result(long nodeh, void *ops, void *instance,
       sysfss_release_fn_t release_fn,
       sysfss_send_fn_t send_fn,
       int *packet_errp);
int sysfss_req_release_logged_result(long nodeh, void *ops, void *instance,
         uintptr_t release,
         sysfss_release_fn_t release_fn,
         sysfss_send_fn_t send_fn,
         sysfss_req_log_fn_t log_fn,
         int *packet_errp);
int sysfss_packet_handler_body_result(int msg, int error, long arg1,
          long arg2, long arg3,
          sysfss_packet_show_fn_t show_fn,
          sysfss_packet_store_fn_t store_fn,
          sysfss_packet_release_fn_t release_fn,
          int *kindp);
int sysfss_packet_handler_logged_result(int msg, int error, long arg1,
     long arg2, long arg3,
     sysfss_packet_show_fn_t show_fn,
     sysfss_packet_store_fn_t store_fn,
     sysfss_packet_release_fn_t release_fn,
     sysfss_packet_unknown_fn_t unknown_fn,
     int *kindp);

unsigned long procfs_mem_reason_result(int readwrite);
int procfs_mem_chunk_size_result(unsigned long offset, unsigned long left);
int procfs_mem_copy_body_result(void *vm, void *page_table, void *buf,
    unsigned long offset, unsigned long count,
    int readwrite,
    procfs_mem_page_fault_fn_t page_fault_fn,
    procfs_mem_virt_to_phys_fn_t virt_to_phys_fn,
    procfs_mem_is_memory_fn_t is_memory_fn,
    procfs_mem_phys_to_virt_fn_t phys_to_virt_fn,
    procfs_mem_copy_fn_t copy_fn);
int procfs_pagemap_range_result(unsigned long offset, int count,
    unsigned long *startp, unsigned long *endp);
int procfs_pagemap_body_result(void *page_table, unsigned long *buf,
          unsigned long start, unsigned long end, int count,
          procfs_pagemap_value_fn_t value_fn);
int procfs_status_state_result(int status);
char procfs_thread_stat_state_result(int status, int in_syscall_offload);
int procfs_default_count_result(void);
int procfs_remote_count_result(unsigned long mapped_addr, int count);
int procfs_remote_npages_result(int count);
int procfs_format_error_result(int ans, int count);
unsigned long procfs_locked_kb_result(unsigned long lockedsize);
char procfs_maps_read_char_result(unsigned long flags);
char procfs_maps_write_char_result(unsigned long flags);
char procfs_maps_exec_char_result(unsigned long flags);
char procfs_maps_private_char_result(unsigned long flags);



int procfs_maps_path_kind_result(unsigned long range_start,
     unsigned long range_end,
     unsigned long range_flags,
     unsigned long vdso_addr,
     unsigned long vvar_addr,
     unsigned long brk_start,
     unsigned long brk_end_allocated);
unsigned long procfs_pagemap_next_result(unsigned long start);
unsigned int procfs_auxv_limit_result(void);
unsigned int procfs_cmdline_limit_result(uintptr_t saved_cmdline,
      unsigned int saved_cmdline_len);
int procfs_is_release_result(int msg);
int procfs_root_matched_result(int sscanf_ret);
int procfs_osnum_match_result(int osnum, int requested_osnum);
int procfs_zero_length_result(unsigned long left);
unsigned long procfs_locked_size_add_result(unsigned long lockedsize,
         unsigned long range_start,
         unsigned long range_end,
         unsigned long flags);
int procfs_bitmask_next_offset_result(int offset, int written);
int procfs_pbuf_is_empty_result(unsigned long pbuf);
int procfs_backlog_needed_result(uintptr_t resultp);
int procfs_lock_failed_action_result(uintptr_t resultp);
int procfs_lock_retry_result(void);
int procfs_thread_tid_result(int task_match, int parsed_tid, int pid);
int procfs_task_missing_terminal_result(int task_match);
int procfs_pointer_present_result(uintptr_t ptr);
int procfs_buffer_chain_attach_result(unsigned long pbuf, uintptr_t buf_top);
int procfs_entry_kind_result(const char *name);
uintptr_t procfs_comm_basename_result(uintptr_t saved_cmdline);
uintptr_t procfs_comm_name_result(uintptr_t fallback, uintptr_t basename);

int pager_linux_io_retry_result(ssize_t ret);
int pager_linux_io_stop_result(ssize_t ret);
int pager_linux_io_first_result(ssize_t done);
ssize_t pager_linux_io_advance_result(ssize_t done, ssize_t ret);
size_t pager_linux_io_remaining_result(size_t remaining, ssize_t ret);
uintptr_t pager_linux_io_next_buf_result(uintptr_t buf, ssize_t ret);
int pager_linux_io_complete_result(ssize_t done, size_t target);
int pager_copy_fault_retry_result(int faulted);
int pager_copy_fault_error_result(int ret);
int pager_myalloc_fits_result(size_t allocated, size_t request, size_t size);
size_t pager_myalloc_next_alloced_result(size_t allocated, size_t request);
int pager_copy_size_error_result(size_t size);
unsigned long pager_fault_addr_result(unsigned long addr);
size_t pager_read_chunk_size_result(size_t off, size_t size);
int pager_arealist_tail_room_result(int tail_count);
int pager_arealist_count_add_result(int count, int add);
ssize_t pager_addrpair_size_result(unsigned long start, unsigned long end);
ssize_t pager_file_pos_result(ssize_t off, ssize_t total_size);
ssize_t pager_arealist_write_result(ssize_t written, int count,
        size_t entry_size);
int pager_mlock_more_result(unsigned long start);
unsigned long pager_mlock_next_start_result(unsigned long end);
int pager_mlock_container_empty_result(uintptr_t from, uintptr_t tail,
           int ccount, int tail_count);
int pager_mlock_needs_next_result(int ccount, int cur_count);
int pager_mlock_reset_count_result(void);
int pager_mlock_next_count_result(int count);
ssize_t pager_pagein_data_pos_result(unsigned int swap_count,
         unsigned int mlock_count,
         size_t header_size, size_t area_size);
int pager_pageout_args_result(uintptr_t fname, uintptr_t buf, size_t size,
         unsigned long user_start, unsigned long user_end);
int pager_skip_anon_range_result(int has_memobj, unsigned long start,
     unsigned long text_start,
     unsigned long stack_start,
     unsigned long user_start,
     unsigned long user_end,
     unsigned long flags);
int pager_range_locked_result(unsigned long flags);
int pager_skip_physical_removal_result(int flags);
int pager_fd_valid_result(int fd);
int pager_should_unlink_swap_result(long result);
long pager_io_short_result(long result);

int zeroobj_initial_flags_result(void);
int zeroobj_initial_refcnt_result(void);
int zeroobj_initial_page_mode_result(void);
off_t zeroobj_initial_page_offset_result(void);
int zeroobj_get_page_validate_result(off_t off, int p2align, int has_page);
typedef void *(*zeroobj_alloc_fn_t)(size_t size, unsigned long flags);
typedef void *(*zeroobj_page_alloc_fn_t)(int npages, unsigned long flags);
typedef void (*zeroobj_free_page_fn_t)(void *virt, int npages);
typedef void *(*zeroobj_memset_fn_t)(void *dst, int value, size_t len);
typedef uintptr_t (*zeroobj_phys_fn_t)(void *addr);
typedef void *(*zeroobj_page_insert_fn_t)(uintptr_t phys);
typedef int (*zeroobj_page_mode_fn_t)(void *page);
typedef void (*zeroobj_obj_init_fn_t)(void *obj, void *ops);
typedef void (*zeroobj_page_init_fn_t)(void *page);
typedef void (*zeroobj_page_list_insert_fn_t)(void *obj, void *page);
typedef void (*zeroobj_publish_fn_t)(void *obj);
typedef int (*zeroobj_alloc_singleton_fn_t)(void);
typedef void *(*zeroobj_get_singleton_fn_t)(void);
typedef void (*zeroobj_ref_fn_t)(void *memobj);
typedef void (*zeroobj_void_fn_t)(void *arg);
typedef void (*zeroobj_log_fn_t)(int event, int error, void *obj,
     void *page, uintptr_t phys);
int zeroobj_alloc_body_result(
 void *existing_obj, size_t obj_size, void *ops, void *lock,
 zeroobj_log_fn_t log_fn, zeroobj_void_fn_t lock_fn,
 zeroobj_void_fn_t unlock_fn, zeroobj_alloc_fn_t alloc_fn,
 zeroobj_void_fn_t free_fn, zeroobj_memset_fn_t memset_fn,
 zeroobj_obj_init_fn_t obj_init_fn,
 zeroobj_page_alloc_fn_t page_alloc_fn,
 zeroobj_free_page_fn_t page_free_fn,
 zeroobj_phys_fn_t phys_fn,
 zeroobj_page_insert_fn_t page_insert_fn,
 zeroobj_page_mode_fn_t page_mode_fn,
 zeroobj_void_fn_t duplicate_page_fn,
 zeroobj_page_init_fn_t page_init_fn,
 zeroobj_page_list_insert_fn_t page_list_insert_fn,
 zeroobj_publish_fn_t publish_fn);
int zeroobj_create_body_result(void **objp, void *existing_obj,
          zeroobj_alloc_singleton_fn_t alloc_fn,
          zeroobj_get_singleton_fn_t get_singleton_fn,
          zeroobj_ref_fn_t ref_fn,
          zeroobj_log_fn_t log_fn);
int zeroobj_get_page_body_result(void);

int shmobj_init_pgshift_result(int init_pgshift);
size_t shmobj_pgsize_result(int pgshift);
int shmobj_initial_flags_result(void);
int shmobj_indexed_flags_result(int flags);
size_t shmobj_real_segsz_result(size_t segsz, size_t pgsize);
int shmobj_page_contains_offset_result(off_t page_offset, int pgshift,
           off_t off);
int shmobj_destroy_page_npages_result(int pgshift);
size_t shmobj_destroy_page_size_result(int pgshift);
int shmobj_destroy_index_word_result(int index);
unsigned long shmobj_destroy_index_mask_result(int index);
int shmlock_user_locked_result(size_t locked);
int shmlock_user_match_result(int user_ruid, int ruid);
int shmlock_user_is_list_head_result(uintptr_t chain, uintptr_t head);
size_t shmlock_user_after_unlock_result(size_t locked, size_t size);
int shmlock_user_should_free_result(size_t locked);
int shmobj_has_user_result(uintptr_t user);
int shmobj_destroy_page_count_invalid_result(int count);
int shmobj_destroy_page_should_free_result(int count, int page_unmap_result);
int shmobj_should_free_direct_result(int index);
int shmobj_destroy_missing_flag_result(int mode);
int shmobj_initial_refcnt_result(void);
int shmobj_initial_index_result(void);
int shmobj_initial_ds_pgshift_result(void);
int shmobj_get_page_validate_result(size_t real_segsz, off_t off,
        int p2align);
int shmobj_lookup_page_validate_result(size_t real_segsz, off_t off);
int shmobj_page_npages_result(int p2align);
int shmobj_page_pgshift_result(int p2align);
int shmobj_need_alloc_page_result(uintptr_t page);
int shmobj_new_page_mode_result(void);
int shmobj_new_page_count_result(void);
long shmobj_new_page_mapped_result(void);
int shmobj_page_mode_valid_for_new_result(int mode);
int shmobj_lookup_page_missing_error_result(uintptr_t page);
int shmobj_lookup_should_store_phys_result(uintptr_t physp);
typedef void (*shmobj_ref_fn_t)(void *memobj);
typedef void (*shmobj_unref_fn_t)(void *memobj);
typedef void (*shmobj_page_list_lock_fn_t)(void *obj);
typedef void (*shmobj_page_list_unlock_fn_t)(void *obj);
typedef void *(*shmobj_page_lookup_fn_t)(void *obj, off_t off);
typedef uintptr_t (*shmobj_page_phys_fn_t)(void *page);
typedef void (*shmobj_lookup_log_fn_t)(int event, void *memobj,
           off_t off, int p2align, void *physp,
           int error, uintptr_t phys);
int shmobj_lookup_page_body_result(
 void *memobj, void *obj, size_t real_segsz, off_t off, int p2align,
 uintptr_t *physp, uintptr_t *resolved_physp, shmobj_ref_fn_t ref_fn,
 shmobj_unref_fn_t unref_fn, shmobj_page_list_lock_fn_t lock_fn,
 shmobj_page_list_unlock_fn_t unlock_fn,
 shmobj_page_lookup_fn_t lookup_fn, shmobj_page_phys_fn_t page_phys_fn,
 shmobj_lookup_log_fn_t log_fn);
int shmobj_update_args_result(int has_pt, int has_orig_page, int has_vaddr);
size_t shmobj_update_orig_pgsize_result(int pgshift);
uintptr_t shmobj_update_page_phys_result(uintptr_t base_phys, size_t page_off);
off_t shmobj_update_page_offset_result(off_t orig_offset, size_t page_off);
int shmobj_pte_missing_result(uintptr_t pte);
int shmobj_update_has_more_pages_result(size_t page_off, size_t orig_pgsize);
size_t shmobj_update_next_page_off_result(size_t page_off, size_t pte_size);
typedef void *(*shmobj_pte_lookup_fn_t)(void *pt, void *vaddr,
     size_t *pte_sizep, int *p2alignp);
typedef int (*shmobj_page_pgshift_fn_t)(void *page);
typedef void (*shmobj_page_set_pgshift_fn_t)(void *page, int pgshift);
typedef int (*shmobj_page_mode_fn_t)(void *page);
typedef void (*shmobj_page_set_mode_fn_t)(void *page, int mode);
typedef off_t (*shmobj_page_offset_fn_t)(void *page);
typedef void (*shmobj_page_set_offset_fn_t)(void *page, off_t offset);
typedef int (*shmobj_page_count_fn_t)(void *page);
typedef void (*shmobj_page_set_count_fn_t)(void *page, int count);
typedef long (*shmobj_page_mapped_fn_t)(void *page);
typedef void (*shmobj_page_set_mapped_fn_t)(void *page, long mapped);
typedef void *(*shmobj_page_insert_hash_fn_t)(uintptr_t phys);
typedef void (*shmobj_page_list_insert_fn_t)(void *obj, void *page);
typedef void (*shmobj_update_log_fn_t)(int event, void *memobj, void *pt,
           void *orig_page, void *vaddr,
           int error);
int shmobj_update_page_body_result(
 void *memobj, void *obj, void *pt, void *orig_page, void *vaddr,
 shmobj_ref_fn_t ref_fn, shmobj_unref_fn_t unref_fn,
 shmobj_page_phys_fn_t page_phys_fn,
 shmobj_pte_lookup_fn_t pte_lookup_fn,
 shmobj_page_pgshift_fn_t page_pgshift_fn,
 shmobj_page_set_pgshift_fn_t page_set_pgshift_fn,
 shmobj_page_mode_fn_t page_mode_fn,
 shmobj_page_set_mode_fn_t page_set_mode_fn,
 shmobj_page_offset_fn_t page_offset_fn,
 shmobj_page_set_offset_fn_t page_set_offset_fn,
 shmobj_page_count_fn_t page_count_fn,
 shmobj_page_set_count_fn_t page_set_count_fn,
 shmobj_page_mapped_fn_t page_mapped_fn,
 shmobj_page_set_mapped_fn_t page_set_mapped_fn,
 shmobj_page_insert_hash_fn_t page_insert_hash_fn,
 shmobj_page_list_insert_fn_t page_list_insert_fn,
 shmobj_update_log_fn_t log_fn);
typedef void *(*shmobj_alloc_page_fn_t)(int npages, int p2align,
     unsigned long flags,
     uintptr_t virt_addr);
typedef void (*shmobj_free_page_fn_t)(void *virt, int npages);
typedef uintptr_t (*shmobj_virt_to_phys_fn_t)(void *virt);
typedef void *(*shmobj_memset_fn_t)(void *dst, int value, size_t len);
typedef void (*shmobj_page_count_inc_fn_t)(void *page);
typedef void (*shmobj_panic_fn_t)(void);
typedef void (*shmobj_get_log_fn_t)(int event, void *memobj, off_t off,
        int p2align, void *physp, int error,
        void *page, uintptr_t phys);
int shmobj_get_page_body_result(
 void *memobj, void *obj, size_t real_segsz, off_t off, int p2align,
 uintptr_t *physp, uintptr_t virt_addr, shmobj_ref_fn_t ref_fn,
 shmobj_unref_fn_t unref_fn, shmobj_page_list_lock_fn_t lock_fn,
 shmobj_page_list_unlock_fn_t unlock_fn,
 shmobj_page_lookup_fn_t lookup_fn,
 shmobj_alloc_page_fn_t alloc_page_fn,
 shmobj_free_page_fn_t free_page_fn,
 shmobj_virt_to_phys_fn_t virt_to_phys_fn,
 shmobj_page_insert_hash_fn_t page_insert_hash_fn,
 shmobj_page_mode_fn_t page_mode_fn,
 shmobj_page_set_mode_fn_t page_set_mode_fn,
 shmobj_page_set_offset_fn_t page_set_offset_fn,
 shmobj_page_set_pgshift_fn_t page_set_pgshift_fn,
 shmobj_page_set_count_fn_t page_set_count_fn,
 shmobj_page_set_mapped_fn_t page_set_mapped_fn,
 shmobj_page_list_insert_fn_t page_list_insert_fn,
 shmobj_page_count_inc_fn_t page_count_inc_fn,
 shmobj_page_phys_fn_t page_phys_fn, shmobj_memset_fn_t memset_fn,
 shmobj_panic_fn_t panic_fn, shmobj_get_log_fn_t log_fn);
typedef void (*shmobj_user_clear_fn_t)(void *obj);
typedef size_t (*shmobj_user_locked_fn_t)(void *user);
typedef void (*shmobj_user_set_locked_fn_t)(void *user, size_t locked);
typedef void (*shmobj_user_free_fn_t)(void *user);
typedef void *(*shmobj_page_first_fn_t)(void *obj);
typedef void (*shmobj_page_remove_fn_t)(void *obj, void *page);
typedef void *(*shmobj_phys_to_virt_fn_t)(uintptr_t phys);
typedef int (*shmobj_page_unmap_fn_t)(void *page);
typedef void (*shmobj_rss_sub_fn_t)(size_t size, size_t pgsize);
typedef void (*shmobj_free_fn_t)(void *ptr);
typedef void (*shmobj_indexed_free_fn_t)(void *obj, int word,
      unsigned long mask);
typedef void (*shmobj_destroy_log_fn_t)(int event, void *obj, void *page,
     uintptr_t phys, size_t size,
     size_t pgsize);
typedef void (*shmobj_destroy_fn_t)(void *obj);
typedef void (*shmobj_free_log_fn_t)(int event, void *memobj);
typedef void *(*shmobj_alloc_fn_t)(size_t size, unsigned long flags);
typedef int (*shmobj_next_seq_fn_t)(void);
typedef void *(*shmobj_create_init_fn_t)(void *obj, void *ds, int pgshift,
      size_t pgsize, size_t real_segsz,
      int seq);
typedef void (*shmobj_create_log_fn_t)(int event, void *ds, void *objp,
           int error);
typedef int (*shmobj_create_fn_t)(void *ds, void **objp);
typedef int (*shmobj_memobj_flags_fn_t)(void *memobj);
typedef void (*shmobj_memobj_set_flags_fn_t)(void *memobj, int flags);
typedef void *(*shmobj_to_shmobj_fn_t)(void *memobj);
typedef void *(*shmlock_user_first_fn_t)(void);
typedef void *(*shmlock_user_next_fn_t)(void *user);
typedef int (*shmlock_user_ruid_fn_t)(void *user);
typedef void (*shmlock_user_init_fn_t)(void *user, int ruid);
typedef void (*shmlock_user_list_fn_t)(void *user);
int shmobj_destroy_body_result(
 void *obj, void *user, size_t real_segsz, int index,
 shmobj_user_clear_fn_t user_clear_fn, shmobj_user_locked_fn_t user_locked_fn,
 shmobj_user_set_locked_fn_t user_set_locked_fn,
 shmobj_page_list_lock_fn_t users_lock_fn,
 shmobj_page_list_unlock_fn_t users_unlock_fn,
 shmobj_user_free_fn_t user_free_fn,
 shmobj_page_first_fn_t page_first_fn,
 shmobj_page_remove_fn_t page_remove_fn,
 shmobj_page_phys_fn_t page_phys_fn,
 shmobj_phys_to_virt_fn_t phys_to_virt_fn,
 shmobj_page_pgshift_fn_t page_pgshift_fn,
 shmobj_page_count_fn_t page_count_fn,
 shmobj_page_unmap_fn_t page_unmap_fn,
 shmobj_free_page_fn_t free_page_fn,
 shmobj_rss_sub_fn_t rss_sub_fn,
 shmobj_free_fn_t free_fn,
 shmobj_indexed_free_fn_t indexed_free_fn,
 shmobj_destroy_log_fn_t log_fn);
int shmobj_free_body_result(void *memobj, void *obj, int mode,
       shmobj_page_list_lock_fn_t list_lock_fn,
       shmobj_page_list_unlock_fn_t list_unlock_fn,
       shmobj_destroy_fn_t destroy_fn,
       shmobj_free_log_fn_t log_fn);
int shmobj_create_body_result(
 void *ds, void **objp, size_t segsz, int init_pgshift, size_t obj_size,
 shmobj_alloc_fn_t alloc_fn, shmobj_free_fn_t free_fn,
 shmobj_memset_fn_t memset_fn, shmobj_next_seq_fn_t next_seq_fn,
 shmobj_create_init_fn_t init_fn, shmobj_create_log_fn_t log_fn);
int shmobj_create_indexed_body_result(
 void *ds, void **objp, shmobj_create_fn_t create_fn,
 shmobj_memobj_flags_fn_t flags_fn,
 shmobj_memobj_set_flags_fn_t set_flags_fn,
 shmobj_to_shmobj_fn_t to_shmobj_fn);
int shmlock_user_free_body_result(
 void *user, shmobj_user_locked_fn_t user_locked_fn,
 shmlock_user_list_fn_t list_del_fn, shmobj_free_fn_t free_fn,
 shmobj_panic_fn_t panic_fn);
int shmlock_user_get_body_result(
 int ruid, void **userp, size_t user_size,
 shmlock_user_first_fn_t first_fn, shmlock_user_next_fn_t next_fn,
 shmlock_user_ruid_fn_t ruid_fn, shmobj_alloc_fn_t alloc_fn,
 shmlock_user_init_fn_t init_fn, shmlock_user_list_fn_t list_add_fn);

size_t gencore_align32_result(size_t value);
size_t gencore_alignpage_result(size_t value);
int gencore_range_inaccessible_result(unsigned long flags);
int gencore_prstatus_size_result(void);
int gencore_prpsinfo_size_result(void);
int gencore_auxv_size_result(void);
int gencore_fill_elf_header_body_result(void *eh, int segs);
typedef void (*gencore_arch_fill_prstatus_fn_t)(void *prstatus, void *thread,
      void *regs, int sig);
int gencore_fill_prstatus_body_result(
 void *head, void *thread, void *regs, int sig,
 gencore_arch_fill_prstatus_fn_t arch_fill_prstatus_fn);
int gencore_fill_prpsinfo_body_result(void *head, int status, int pid,
          const char *cmdline);
int gencore_fill_auxv_body_result(void *head, const unsigned long *saved_auxv);
int gencore_fill_note_phdr_body_result(void *ph, unsigned long offset,
           long notesize);
int gencore_fill_load_phdr_body_result(void *ph, unsigned long flags,
           unsigned long offset,
           unsigned long start,
           unsigned long size);
int gencore_fill_initial_coretable_body_result(
 void *ct, unsigned long eh_phys, unsigned long ph_phys,
 unsigned long note_phys, long phsize, long alignednotesize);
typedef int (*gencore_pt_virt_to_phys_fn_t)(void *page_table,
         unsigned long vaddr,
         unsigned long *phys);
typedef unsigned long (*gencore_virt_to_phys_fn_t)(unsigned long vaddr);
typedef void (*gencore_coretable_log_fn_t)(int index, long len,
        unsigned long addr,
        unsigned long start);
typedef void *(*gencore_lookup_range_fn_t)(void *vm);
typedef void *(*gencore_next_range_fn_t)(void *vm, void *range);
typedef unsigned long (*gencore_range_ulong_fn_t)(void *range);
typedef long (*gencore_range_offset_fn_t)(void *range);
typedef void (*gencore_range_log_fn_t)(unsigned long start,
           unsigned long end, unsigned long flags,
           long objoff);
int gencore_count_range_chunks_body_result(
 unsigned long start, unsigned long end, unsigned long flags,
 void *page_table, int *chunks,
 gencore_pt_virt_to_phys_fn_t pt_virt_to_phys_fn);
int gencore_scan_ranges_for_counts_body_result(
 void *vm, void *page_table, int *chunks, int *segs,
 gencore_lookup_range_fn_t lookup_fn,
 gencore_next_range_fn_t next_fn,
 gencore_range_ulong_fn_t start_fn,
 gencore_range_ulong_fn_t end_fn,
 gencore_range_ulong_fn_t flag_fn,
 gencore_range_offset_fn_t objoff_fn,
 gencore_range_log_fn_t log_fn,
 gencore_pt_virt_to_phys_fn_t pt_virt_to_phys_fn);
int gencore_fill_load_phdrs_body_result(
 void *vm, void *ph, int *indexp, unsigned long *offsetp,
 gencore_lookup_range_fn_t lookup_fn,
 gencore_next_range_fn_t next_fn,
 gencore_range_ulong_fn_t start_fn,
 gencore_range_ulong_fn_t end_fn,
 gencore_range_ulong_fn_t flag_fn);
int gencore_emit_demand_coretable_body_result(
 void *ct, int *indexp, unsigned long start, unsigned long end,
 void *page_table, gencore_pt_virt_to_phys_fn_t pt_virt_to_phys_fn,
 gencore_coretable_log_fn_t log_fn);
int gencore_emit_linear_coretable_body_result(
 void *ct, int *indexp, unsigned long start, unsigned long end,
 unsigned long user_start, unsigned long user_end, void *page_table,
 gencore_pt_virt_to_phys_fn_t pt_virt_to_phys_fn,
 gencore_virt_to_phys_fn_t virt_to_phys_fn,
 gencore_coretable_log_fn_t log_fn);
int gencore_emit_coretable_ranges_body_result(
 void *vm, void *ct, int *indexp, unsigned long user_start,
 unsigned long user_end, void *page_table, unsigned long *error_startp,
 gencore_lookup_range_fn_t lookup_fn,
 gencore_next_range_fn_t next_fn,
 gencore_range_ulong_fn_t start_fn,
 gencore_range_ulong_fn_t end_fn,
 gencore_range_ulong_fn_t flag_fn,
 gencore_pt_virt_to_phys_fn_t pt_virt_to_phys_fn,
 gencore_virt_to_phys_fn_t virt_to_phys_fn,
 gencore_coretable_log_fn_t log_fn);
typedef void *(*gencore_phys_to_virt_fn_t)(unsigned long phys);
typedef void (*gencore_free_fn_t)(void *ptr);
typedef void *(*gencore_alloc_fn_t)(size_t size, unsigned long flags);
typedef void (*gencore_zero_fn_t)(void *ptr, size_t size);
typedef int (*gencore_get_note_size_fn_t)(void *proc);
typedef void (*gencore_fill_note_fn_t)(void *note, void *proc,
           char *cmdline, int sig);
typedef void (*gencore_alloc_error_log_fn_t)(int stage);
typedef void (*gencore_pt_error_log_fn_t)(unsigned long start, int error);
typedef void *(*gencore_first_thread_fn_t)(void *proc);
typedef void *(*gencore_next_thread_fn_t)(void *proc, void *thread);
typedef int (*gencore_thread_tid_fn_t)(void *thread);
typedef void *(*gencore_thread_regs_fn_t)(void *thread);
typedef int (*gencore_arch_thread_info_size_fn_t)(void);
typedef void (*gencore_fill_prstatus_note_fn_t)(void *note,
      void *thread, int sig);
typedef void (*gencore_arch_fill_thread_info_fn_t)(void *note,
         void *thread, void *regs);
typedef void (*gencore_fill_proc_note_fn_t)(void *note, void *proc,
         char *cmdline);
typedef void (*gencore_fill_auxv_note_fn_t)(void *note, void *proc);
int gencore_freecore_body_result(void **coretablep,
     gencore_phys_to_virt_fn_t phys_to_virt_fn,
     gencore_free_fn_t free_fn);
int gencore_generate_image_body_result(
 void *proc, void *vm, void *page_table, void **coretablep,
 int *chunks, int segs, unsigned long user_start,
 unsigned long user_end, char *cmdline, int sig,
 size_t eh_size, size_t phdr_size, size_t coretable_size,
 gencore_alloc_fn_t alloc_fn, gencore_zero_fn_t zero_fn,
 gencore_free_fn_t free_fn,
 gencore_get_note_size_fn_t get_note_size_fn,
 gencore_fill_note_fn_t fill_note_fn,
 gencore_virt_to_phys_fn_t virt_to_phys_fn,
 gencore_lookup_range_fn_t lookup_fn,
 gencore_next_range_fn_t next_fn,
 gencore_range_ulong_fn_t start_fn,
 gencore_range_ulong_fn_t end_fn,
 gencore_range_ulong_fn_t flag_fn,
 gencore_pt_virt_to_phys_fn_t pt_virt_to_phys_fn,
 gencore_coretable_log_fn_t coretable_log_fn,
 gencore_alloc_error_log_fn_t alloc_error_log_fn,
 gencore_pt_error_log_fn_t pt_error_log_fn);
int gencore_note_size_threads_body_result(
 void *proc, int pid, gencore_first_thread_fn_t first_fn,
 gencore_next_thread_fn_t next_fn,
 gencore_thread_tid_fn_t tid_fn,
 gencore_arch_thread_info_size_fn_t arch_size_fn);
int gencore_fill_note_threads_body_result(
 void *note, void *proc, char *cmdline, int sig, int pid,
 void **end_notep, gencore_first_thread_fn_t first_fn,
 gencore_next_thread_fn_t next_fn,
 gencore_thread_tid_fn_t tid_fn,
 gencore_thread_regs_fn_t regs_fn,
 gencore_arch_thread_info_size_fn_t arch_size_fn,
 gencore_fill_prstatus_note_fn_t fill_prstatus_fn,
 gencore_arch_fill_thread_info_fn_t arch_fill_fn,
 gencore_fill_proc_note_fn_t fill_prpsinfo_fn,
 gencore_fill_auxv_note_fn_t fill_auxv_fn);

int hugefileobj_expected_p2align_result(int pgshift);
int hugefileobj_validate_p2align_result(int p2align, int pgshift);
off_t hugefileobj_page_index_result(off_t off, int pgshift);
int hugefileobj_npages_per_page_result(size_t pgsize);
size_t hugefileobj_pgsize_result(int pgshift);
int hugefileobj_initial_status_result(void);
int hugefileobj_initial_refcnt_result(void);
int hugefileobj_pointer_present_result(uintptr_t ptr);
int hugefileobj_pointer_missing_result(uintptr_t ptr);
int hugefileobj_page_present_result(uintptr_t page);
size_t hugefileobj_page_array_bytes_result(size_t nr_pages);
int hugefileobj_create_nr_pages_result(off_t off, size_t len, int pgshift);
int hugefileobj_needs_grow_result(size_t current_nr_pages,
      int needed_nr_pages);
size_t hugefileobj_copy_bytes_result(size_t current_nr_pages);
size_t hugefileobj_zero_bytes_result(size_t old_nr_pages,
         size_t new_nr_pages);
size_t hugefileobj_zero_start_index_result(size_t old_nr_pages);
typedef void (*hugefileobj_void_fn_t)(void *arg);
typedef int (*hugefileobj_bool_fn_t)(void *arg);
typedef void *(*hugefileobj_first_fn_t)(void *arg);
typedef void *(*hugefileobj_alloc_fn_t)(size_t size, unsigned long flags);
typedef void *(*hugefileobj_alloc_page_fn_t)(int npages, int p2align,
          unsigned long flags,
          uintptr_t virt_addr);
typedef void (*hugefileobj_free_page_fn_t)(void *page, int npages);
typedef void *(*hugefileobj_memcpy_fn_t)(void *dst, const void *src,
      size_t len);
typedef void *(*hugefileobj_memset_fn_t)(void *dst, int value,
      size_t len);
typedef uintptr_t (*hugefileobj_phys_fn_t)(void *addr);
typedef void *(*hugefileobj_page_at_fn_t)(void *obj, long index);
typedef void (*hugefileobj_set_page_fn_t)(void *obj, long index,
       void *page);
typedef void *(*hugefileobj_lookup_fn_t)(uintptr_t handle);
typedef void *(*hugefileobj_to_memobj_fn_t)(void *obj);
typedef void *(*hugefileobj_next_fn_t)(void *head, void *obj);
typedef uintptr_t (*hugefileobj_handle_fn_t)(void *obj);
typedef int (*hugefileobj_ref_fn_t)(void *obj);
typedef void (*hugefileobj_set_handle_fn_t)(void *obj, uintptr_t handle);
typedef void (*hugefileobj_set_pgsize_fn_t)(void *obj, size_t pgsize);
typedef void (*hugefileobj_set_pgshift_fn_t)(void *obj, int pgshift);
typedef void (*hugefileobj_set_flags_fn_t)(void *obj, unsigned int flags);
typedef void (*hugefileobj_set_status_fn_t)(void *obj, int status);
typedef void (*hugefileobj_set_ops_fn_t)(void *obj, void *ops);
typedef void (*hugefileobj_set_refcnt_fn_t)(void *obj, int refcnt);
typedef void (*hugefileobj_set_path_fn_t)(void *obj, void *path);
typedef void (*hugefileobj_copy_path_fn_t)(void *dst, const void *src,
        size_t len);
typedef void (*hugefileobj_dec_fn_t)(void *obj);
typedef void (*hugefileobj_pre_create_log_fn_t)(int event, void *obj);
typedef void (*hugefileobj_alloc_error_fn_t)(int stage);
typedef void (*hugefileobj_set_size_fn_t)(void *obj, size_t size);
typedef void (*hugefileobj_set_nr_pages_fn_t)(void *obj, size_t nr_pages);
typedef void (*hugefileobj_set_pages_fn_t)(void *obj, void *pages);
typedef void (*hugefileobj_log_fn_t)(int event, void *obj, off_t off,
         long index, size_t pgsize,
         uintptr_t virt_addr);
int hugefileobj_free_body_result(void *obj, void *lock,
     hugefileobj_void_fn_t lock_fn,
     hugefileobj_void_fn_t unlock_fn,
     hugefileobj_void_fn_t list_del_fn,
     hugefileobj_void_fn_t free_fn);
int hugefileobj_cleanup_body_result(void *lock, void *list_head,
        hugefileobj_void_fn_t lock_fn,
        hugefileobj_void_fn_t unlock_fn,
        hugefileobj_bool_fn_t list_empty_fn,
        hugefileobj_first_fn_t first_fn,
        hugefileobj_void_fn_t list_del_fn,
        hugefileobj_void_fn_t free_fn);
int hugefileobj_inner_free_body_result(
 void *obj, void *lock, void *path, void *pages, size_t nr_pages,
 size_t pgsize, hugefileobj_void_fn_t lock_fn,
 hugefileobj_void_fn_t unlock_fn, hugefileobj_void_fn_t free_fn,
 hugefileobj_free_page_fn_t free_page_fn,
 hugefileobj_page_at_fn_t page_at_fn,
 hugefileobj_void_fn_t clear_path_fn,
 hugefileobj_log_fn_t log_fn);
int hugefileobj_get_page_body_result(
 void *obj, void *lock, off_t off, int p2align, int pgshift,
 size_t pgsize, uintptr_t virt_addr, uintptr_t *physp,
 hugefileobj_void_fn_t lock_fn, hugefileobj_void_fn_t unlock_fn,
 hugefileobj_page_at_fn_t page_at_fn,
 hugefileobj_set_page_fn_t set_page_fn,
 hugefileobj_alloc_page_fn_t alloc_page_fn,
 hugefileobj_memset_fn_t memset_fn, hugefileobj_phys_fn_t phys_fn,
 hugefileobj_log_fn_t log_fn);
int hugefileobj_create_body_result(
 void *obj, void *lock, size_t len, off_t off, int pgshift,
 size_t pgsize, size_t current_nr_pages, void *current_pages,
 int *pgshiftp, uintptr_t virt_addr, unsigned long alloc_flags,
 hugefileobj_void_fn_t lock_fn, hugefileobj_void_fn_t unlock_fn,
 hugefileobj_alloc_fn_t alloc_fn, hugefileobj_void_fn_t free_fn,
 hugefileobj_memcpy_fn_t memcpy_fn,
 hugefileobj_memset_fn_t memset_fn,
 hugefileobj_set_nr_pages_fn_t set_nr_pages_fn,
 hugefileobj_set_pages_fn_t set_pages_fn,
 hugefileobj_set_size_fn_t set_size_fn,
 hugefileobj_log_fn_t log_fn);
int hugefileobj_pre_create_body_result(
 void *lock, uintptr_t handle, int maxprot, unsigned int flags,
 int pgshift, const char *path, size_t obj_size, size_t path_size,
 void *ops, void **objp, int *maxprotp,
 hugefileobj_void_fn_t lock_fn,
 hugefileobj_void_fn_t unlock_fn,
 hugefileobj_lookup_fn_t lookup_fn,
 hugefileobj_alloc_fn_t alloc_fn,
 hugefileobj_void_fn_t free_fn,
 hugefileobj_to_memobj_fn_t to_memobj_fn,
 hugefileobj_set_handle_fn_t set_handle_fn,
 hugefileobj_set_pgsize_fn_t set_pgsize_fn,
 hugefileobj_set_pgshift_fn_t set_pgshift_fn,
 hugefileobj_set_pages_fn_t set_pages_fn,
 hugefileobj_set_nr_pages_fn_t set_nr_pages_fn,
 hugefileobj_void_fn_t init_lock_fn,
 hugefileobj_set_flags_fn_t set_flags_fn,
 hugefileobj_set_status_fn_t set_status_fn,
 hugefileobj_set_ops_fn_t set_ops_fn,
 hugefileobj_set_refcnt_fn_t set_refcnt_fn,
 hugefileobj_set_path_fn_t set_path_fn,
 hugefileobj_copy_path_fn_t copy_path_fn,
 hugefileobj_void_fn_t list_add_fn,
 hugefileobj_pre_create_log_fn_t log_fn,
 hugefileobj_alloc_error_fn_t alloc_error_fn);
void *hugefileobj_lookup_body_result(
 uintptr_t handle, void *list_head,
 hugefileobj_first_fn_t first_fn,
 hugefileobj_next_fn_t next_fn,
 hugefileobj_handle_fn_t handle_fn,
 hugefileobj_ref_fn_t ref_fn,
 hugefileobj_dec_fn_t dec_fn);
# 26 "/home/holden/mckernel/kernel/include/memobj.h" 2

enum {

 MF_HAS_PAGER = 0x0001,
 MF_SHMDT_OK = 0x0002,
 MF_IS_REMOVABLE = 0x0004,
 MF_PREFETCH = 0x0008,
 MF_ZEROFILL = 0x0010,
 MF_REG_FILE = 0x1000,
 MF_DEV_FILE = 0x2000,
 MF_PREMAP = 0x8000,
 MF_XPMEM = 0x10000,
 MF_ZEROOBJ = 0x20000,
 MF_SHM = 0x40000,
 MF_HUGETLBFS = 0x100000,
 MF_PRIVATE = 0x200000,
 MF_REMAP_FILE_PAGES = 0x400000,
};




struct memobj {
 struct memobj_ops *ops;
 uint32_t flags;
 uint32_t status;
 size_t size;
 ihk_atomic_t refcnt;


 void **pages;
 int nr_pages;
 char *path;
};

typedef void memobj_free_func_t(struct memobj *obj);
typedef int memobj_get_page_func_t(struct memobj *obj, off_t off, int p2align, uintptr_t *physp, unsigned long *flag, uintptr_t virt_addr);
typedef uintptr_t memobj_copy_page_func_t(struct memobj *obj, uintptr_t orgphys, int p2align);
typedef int memobj_flush_page_func_t(struct memobj *obj, uintptr_t phys, size_t pgsize);
typedef int memobj_invalidate_page_func_t(struct memobj *obj, uintptr_t phys, size_t pgsize);
typedef int memobj_lookup_page_func_t(struct memobj *obj, off_t off, int p2align, uintptr_t *physp, unsigned long *flag);
typedef int memobj_update_page_func_t(struct memobj *obj, page_table_t pt,
  struct page *orig_page, void *vaddr);

struct memobj_ops {
 memobj_free_func_t *free;
 memobj_get_page_func_t *get_page;
 memobj_copy_page_func_t *copy_page;
 memobj_flush_page_func_t *flush_page;
 memobj_invalidate_page_func_t *invalidate_page;
 memobj_lookup_page_func_t *lookup_page;
 memobj_update_page_func_t *update_page;
};

int memobj_ref(struct memobj *obj);
int memobj_unref(struct memobj *obj);
int memobj_get_page(struct memobj *obj, off_t off, int p2align,
      uintptr_t *physp, unsigned long *pflag,
      uintptr_t virt_addr);
uintptr_t memobj_copy_page(struct memobj *obj, uintptr_t orgphys,
      int p2align);
int memobj_flush_page(struct memobj *obj, uintptr_t phys, size_t pgsize);
int memobj_invalidate_page(struct memobj *obj, uintptr_t phys, size_t pgsize);
int memobj_lookup_page(struct memobj *obj, off_t off, int p2align,
         uintptr_t *physp, unsigned long *pflag);
int memobj_update_page(struct memobj *obj, page_table_t pt,
         struct page *orig_page, void *vaddr);
int memobj_has_pager(struct memobj *obj);
int memobj_is_removable(struct memobj *obj);

int fileobj_create(int fd, struct memobj **objp, int *maxprotp, int flags,
     uintptr_t virt_addr);
struct shmid_ds;
int shmobj_create(struct shmid_ds *ds, struct memobj **objp);
int zeroobj_create(struct memobj **objp);
int devobj_create(int fd, size_t len, off_t off, struct memobj **objp, int *maxprotp,
 int prot, int populate_flags);
int hugefileobj_pre_create(struct pager_create_result *result,
      struct memobj **objp, int *maxprotp);
int hugefileobj_create(struct memobj *obj, size_t len, off_t off,
         int *pgshiftp, uintptr_t virt_addr);
void hugefileobj_cleanup(void);

int is_flushable(struct page *page, struct memobj *memobj);
int is_freeable(struct memobj *memobj);
int is_callable_remap_file_pages(struct memobj *memobj);
# 25 "/home/holden/mckernel/kernel/include/process.h" 2
# 1 "/home/holden/mckernel/kernel/include/affinity.h" 1
# 28 "/home/holden/mckernel/kernel/include/affinity.h"
typedef unsigned long int __cpu_mask;


typedef struct
{
  __cpu_mask __bits[1024 / (8 * sizeof (__cpu_mask))];
} cpu_set_t;
# 51 "/home/holden/mckernel/kernel/include/affinity.h"
unsigned long CPU_SET(unsigned long cpu, cpu_set_t *cpusetp);
int CPU_ISSET(unsigned long cpu, const cpu_set_t *cpusetp);
void CPU_ZERO(cpu_set_t *cpusetp);
unsigned long CPU_SET_S(unsigned long cpu, unsigned long setsize,
   cpu_set_t *cpusetp);
int CPU_ISSET_S(unsigned long cpu, unsigned long setsize,
  const cpu_set_t *cpusetp);
void CPU_ZERO_S(unsigned long setsize, cpu_set_t *cpusetp);
# 26 "/home/holden/mckernel/kernel/include/process.h" 2
# 1 "/home/holden/mckernel/kernel/include/syscall.h" 1
# 19 "/home/holden/mckernel/kernel/include/syscall.h"
# 1 "/home/holden/mckernel/ihk/cokernel/smp/x86_64/include/ihk/memconst.h" 1
# 20 "/home/holden/mckernel/kernel/include/syscall.h" 2
# 1 "/home/holden/mckernel/ihk/linux/include/ihk/ikc.h" 1
# 11 "/home/holden/mckernel/ihk/linux/include/ihk/ikc.h"
# 1 "/home/holden/mckernel/ihk/ikc/include/ikc/ihk.h" 1
# 28 "/home/holden/mckernel/ihk/ikc/include/ikc/ihk.h"
typedef void * ihk_os_t;
typedef void * ihk_device_t;

typedef void * ihk_wait_t;






# 1 "/home/holden/mckernel/lib/include/string.h" 1
# 17 "/home/holden/mckernel/lib/include/string.h"
# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/arch-string.h" 1





void *__inline_memcpy(void *to, const void *from, size_t n);



void *__inline_memset(void *s, unsigned long c, size_t count);
# 18 "/home/holden/mckernel/lib/include/string.h" 2

size_t strlen(const char *p);
size_t strnlen(const char *p, size_t maxlen);
char *strcpy(char *dest, const char *src);
char *strncpy(char *dest, const char *src, size_t maxlen);
int strcmp(const char *s1, const char *s2);
int strncmp(const char *s1, const char *s2, size_t n);
char *strstr(const char *haystack, const char *needle);
char *strpbrk(const char *haystack, const char *accept);
char *strchr(const char *s, int n);
char *strrchr(const char *s, int n);
void *memcpy(void *dest, const void *src, size_t n);
void *memcpy_long(void *dest, const void *src, size_t n);
int memcmp(const void *s1, const void *s2, size_t n);
void *memset(void *s, int n, size_t l);
# 44 "/home/holden/mckernel/lib/include/string.h"
extern int snprintf(char * buf, size_t size, const char *fmt, ...);
extern int sprintf(char * buf, const char *fmt, ...);
extern int sscanf(const char * buf, const char * fmt, ...);
extern int scnprintf(char * buf, size_t size, const char *fmt, ...);

unsigned long strtol(const char *cp, char **endp, unsigned int base);
int flatten_strings_from_user(char *pre_strings, char **strings, char **flat);
# 39 "/home/holden/mckernel/ihk/ikc/include/ikc/ihk.h" 2
# 102 "/home/holden/mckernel/ihk/ikc/include/ikc/ihk.h"
# 1 "/home/holden/mckernel/ihk/ikc/include/ikc/queue.h" 1
# 10 "/home/holden/mckernel/ihk/ikc/include/ikc/queue.h"
# 1 "/home/holden/mckernel/ihk/ikc/include/ikc/ihk.h" 1
# 11 "/home/holden/mckernel/ihk/ikc/include/ikc/queue.h" 2



struct ihk_ikc_channel_desc;
struct ihk_ikc_queue_desc;

typedef int (*ihk_ikc_ph_t)(struct ihk_ikc_channel_desc *,
                            void *, void *);

struct ihk_ikc_queue_head {

 uint32_t id;
 uint16_t type;
 uint16_t pktsize;
 uint32_t pktcount;
 uint32_t flag;

 uint64_t read_off;
 uint64_t max_read_off;

 uint64_t write_off;
 uint64_t queue_size;

 uint32_t channel_id;
 uint32_t read_cpu;
 uint32_t write_cpu;
 uint32_t dummy2;

};

struct ihk_ikc_queue_desc {
 struct ihk_ikc_queue_head *queue;
 struct ihk_ikc_queue_head cache;
 unsigned long qrphys;
 unsigned long qphys;
 ihk_spinlock_t lock;
 uint32_t intr_cpu;
};

enum ihk_ikc_channel_flag {
 IKC_FLAG_ENABLED = 1,
 IKC_FLAG_DESTROYING = 2,
 IKC_FLAG_DESTROY_ACKED = 4,
 IKC_FLAG_STATUS_MASK = 7,
 IKC_FLAG_NO_COPY = 0x10,
};

struct ihk_ikc_packet_header {
 struct ihk_ikc_channel_desc *channel;
};

struct ihk_ikc_free_packet {
 struct ihk_ikc_packet_header header;
 struct list_head list;
};

struct ihk_ikc_channel_desc {
 struct list_head list_all;
 ihk_os_t remote_os;
 int remote_channel_id;
 uint64_t remote_channel_va;
 struct ihk_ikc_channel_desc *master;
 int port;
 int channel_id;
 struct ihk_ikc_queue_desc recv, send;
 ihk_spinlock_t lock;
 enum ihk_ikc_channel_flag flag;
 ihk_ikc_ph_t handler;
 struct list_head packet_pool;
 ihk_spinlock_t packet_pool_lock;
};

struct ihk_ikc_free_packet *ihk_ikc_alloc_packet(struct ihk_ikc_channel_desc *c);
void ihk_ikc_release_packet(struct ihk_ikc_free_packet *p);

int ihk_ikc_init_queue(struct ihk_ikc_queue_head *q,
                       int id, int type, int size, int packetsize);
int ihk_ikc_queue_is_empty(struct ihk_ikc_queue_head *q);
int ihk_ikc_queue_is_full(struct ihk_ikc_queue_head *q);
int ihk_ikc_read_queue(struct ihk_ikc_queue_head *q, void *packet, int flag);
int ihk_ikc_write_queue(struct ihk_ikc_queue_head *q, void *packet, int flag);

struct ihk_ikc_channel_desc *ihk_ikc_create_channel(ihk_os_t os,
                                                    int port,
                                                    int packet_size,
                                                    unsigned long qsize,
                                                    unsigned long *rq,
                                                    unsigned long *sq,
                                                    enum ihk_ikc_channel_flag);
void ihk_ikc_free_channel(struct ihk_ikc_channel_desc *desc);

void ihk_ikc_enable_channel(struct ihk_ikc_channel_desc *channel);
void ihk_ikc_disable_channel(struct ihk_ikc_channel_desc *channel);

void ihk_ikc_channel_set_cpu(struct ihk_ikc_channel_desc *c, int cpu);



int ihk_ikc_send(struct ihk_ikc_channel_desc *channel, void *p, int opt);
int ihk_ikc_recv(struct ihk_ikc_channel_desc *channel, void *p, int opt);
int ihk_ikc_recv_handler(struct ihk_ikc_channel_desc *channel,
                         ihk_ikc_ph_t h, void *harg, int opt);
int ihk_ikc_set_remote_queue(struct ihk_ikc_queue_desc *q, ihk_os_t os,
                             unsigned long rphys, unsigned long qsize);
void ihk_ikc_system_init(ihk_os_t);
void ihk_ikc_system_exit(ihk_os_t);

void ihk_ikc_init_desc(struct ihk_ikc_channel_desc *c,
                       ihk_os_t ros, int cid,
                       struct ihk_ikc_queue_head *rq,
                       struct ihk_ikc_queue_head *wq,
                       ihk_ikc_ph_t packet_handler,
                       struct ihk_ikc_channel_desc *master);
struct ihk_ikc_channel_desc *ihk_ikc_find_channel(ihk_os_t os, int id);

static inline __attribute__((always_inline,unused)) __attribute__((no_instrument_function)) int ihk_ikc_channel_enabled(struct ihk_ikc_channel_desc *c)
{
 return (c->flag & IKC_FLAG_STATUS_MASK) == IKC_FLAG_ENABLED;
}
# 103 "/home/holden/mckernel/ihk/ikc/include/ikc/ihk.h" 2

struct ihk_ikc_queue_head;
struct ihk_ikc_channel_desc;
struct ihk_ikc_master_wait_struct;

int ihk_ikc_send_interrupt(struct ihk_ikc_channel_desc *c);

struct ihk_ikc_queue_head *ihk_ikc_alloc_queue(int qpages);
void ihk_ikc_free_queue(struct ihk_ikc_queue_head *q);

void *ihk_ikc_malloc(int size);
void ihk_ikc_free(void *);

int call_arch_master_packet_handler(void *os, struct ihk_ikc_channel_desc *c,
                                    void *__packet);

void ihk_ikc_wait_init(ihk_wait_t *wait);
int ihk_ikc_wait_master(struct ihk_ikc_master_wait_struct *wq);
void ihk_ikc_wake_master(struct ihk_ikc_master_wait_struct *wq);

struct ihk_ikc_channel_desc *ihk_ikc_get_master_channel(ihk_os_t os);
struct list_head *ihk_ikc_get_channel_list(ihk_os_t os);
ihk_spinlock_t *ihk_ikc_get_channel_list_lock(ihk_os_t ihk_os);

struct ihk_ikc_channel_desc *ihk_ikc_get_regular_channel(ihk_os_t os, int cpu);
void ihk_ikc_set_regular_channel(ihk_os_t os, struct ihk_ikc_channel_desc *c, int cpu);

int ihk_ikc_get_unique_channel_id(ihk_os_t ihk_os);
void ihk_ikc_notify_remote_read(struct ihk_ikc_channel_desc *c);
void ihk_ikc_notify_remote_write(struct ihk_ikc_channel_desc *c);
# 12 "/home/holden/mckernel/ihk/linux/include/ihk/ikc.h" 2
# 21 "/home/holden/mckernel/kernel/include/syscall.h" 2
# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/rlimit.h" 1
# 17 "/home/holden/mckernel/arch/x86_64/kernel/include/rlimit.h"
enum __rlimit_resource
{

  RLIMIT_CPU = 0,



  RLIMIT_FSIZE = 1,



  RLIMIT_DATA = 2,



  RLIMIT_STACK = 3,



  RLIMIT_CORE = 4,






  __RLIMIT_RSS = 5,



  RLIMIT_NOFILE = 7,
  __RLIMIT_OFILE = RLIMIT_NOFILE,




  RLIMIT_AS = 9,



  __RLIMIT_NPROC = 6,



  __RLIMIT_MEMLOCK = 8,



  __RLIMIT_LOCKS = 10,



  __RLIMIT_SIGPENDING = 11,



  __RLIMIT_MSGQUEUE = 12,





  __RLIMIT_NICE = 13,




  __RLIMIT_RTPRIO = 14,



  __RLIMIT_RTTIME = 15,


  __RLIMIT_NLIMITS = 16,
  __RLIM_NLIMITS = __RLIMIT_NLIMITS


};

# 1 "/home/holden/mckernel/kernel/include/generic-rlimit.h" 1
# 16 "/home/holden/mckernel/kernel/include/generic-rlimit.h"
typedef uint64_t rlim_t;

struct rlimit {
 rlim_t rlim_cur;
 rlim_t rlim_max;
};
# 98 "/home/holden/mckernel/arch/x86_64/kernel/include/rlimit.h" 2
# 22 "/home/holden/mckernel/kernel/include/syscall.h" 2
# 1 "/home/holden/mckernel/kernel/include/time.h" 1
# 28 "/home/holden/mckernel/kernel/include/time.h"
typedef int clockid_t;

typedef long int __time_t;



struct timespec
  {
    __time_t tv_sec;
    long int tv_nsec;
  };




struct timeval
  {
    __time_t tv_sec;
    long tv_usec;
  };




struct timezone
  {
    int tz_minuteswest;
    int tz_dsttime;
  };





struct itimerval {
 struct timeval it_interval;
 struct timeval it_value;
};

void ts_add(struct timespec *ats, const struct timespec *bts);
void ts_sub(struct timespec *ats, const struct timespec *bts);
void tv_add(struct timeval *ats, const struct timeval *bts);
void tv_sub(struct timeval *ats, const struct timeval *bts);
void tv_to_ts(struct timespec *ats, const struct timeval *bts);
void ts_to_tv(struct timeval *ats, const struct timespec *bts);
# 23 "/home/holden/mckernel/kernel/include/syscall.h" 2
# 1 "/home/holden/mckernel/kernel/include/profile.h" 1
# 16 "/home/holden/mckernel/kernel/include/profile.h"
struct profile_event {
 uint32_t cnt;
 uint64_t tsc;
};
# 30 "/home/holden/mckernel/kernel/include/profile.h"
enum profile_event_type {
 PROFILE_tlb_invalidate = (2000 << 1),
 PROFILE_page_fault,
 PROFILE_page_fault_anon_clr,
 PROFILE_page_fault_file,
 PROFILE_page_fault_dev_file,
 PROFILE_page_fault_file_clr,
 PROFILE_remote_page_fault,
 PROFILE_mpol_alloc_missed,
 PROFILE_mmap_anon_contig_phys,
 PROFILE_mmap_anon_straight,
 PROFILE_mmap_anon_not_straight,
 PROFILE_mmap_anon_no_contig_phys,
 PROFILE_mmap_regular_file,
 PROFILE_mmap_device_file,
 PROFILE_tofu_stag_alloc,
 PROFILE_tofu_stag_alloc_new_steering,
 PROFILE_tofu_stag_alloc_new_steering_alloc_mbpt,
 PROFILE_tofu_stag_alloc_new_steering_update_mbpt,
 PROFILE_tofu_stag_free_stags,
 PROFILE_tofu_stag_free_stag,
 PROFILE_tofu_stag_free_stag_pre,
 PROFILE_tofu_stag_free_stag_cqflush,
 PROFILE_tofu_stag_free_stag_dealloc,
 PROFILE_tofu_stag_free_stag_dealloc_free_pages,
 PROFILE_EVENT_MAX
};


struct thread;
struct process;

enum profile_event_type profile_syscall2offload(enum profile_event_type sc);
void profile_event_add(enum profile_event_type type, uint64_t tsc);
void profile_print_thread_stats(struct thread *thread);
void profile_print_proc_stats(struct process *proc);
void profile_print_job_stats(struct process *proc);
void profile_accumulate_events(struct thread *thread, struct process *proc);
int profile_accumulate_and_print_job_events(struct process *proc);
int profile_alloc_events(struct thread *thread);
void profile_dealloc_thread_events(struct thread *thread);
void profile_dealloc_proc_events(struct process *proc);
# 24 "/home/holden/mckernel/kernel/include/syscall.h" 2
# 134 "/home/holden/mckernel/kernel/include/syscall.h"
struct user_desc {
 unsigned int entry_number;
 unsigned int base_addr;
 unsigned int limit;
 unsigned int seg_32bit:1;
 unsigned int contents:2;
 unsigned int read_exec_only:1;
 unsigned int limit_in_pages:1;
 unsigned int seg_not_present:1;
 unsigned int useable:1;
 unsigned int lm:1;
};

struct program_image_section {
 unsigned long vaddr;
 unsigned long len;
 unsigned long remote_pa;
 unsigned long filesz, offset;
 int prot;
 unsigned char interp;
 unsigned char padding[3];
 void *fp;
};
# 179 "/home/holden/mckernel/kernel/include/syscall.h"
typedef unsigned long __cpu_set_unit;
# 190 "/home/holden/mckernel/kernel/include/syscall.h"
enum {
 PLD_MPOL_DEFAULT,
 PLD_MPOL_PREFERRED,
 PLD_MPOL_BIND,
 PLD_MPOL_INTERLEAVE,
 PLD_MPOL_LOCAL,
 PLD_MPOL_MAX,
};



struct program_load_desc {
 unsigned long magic;
 int num_sections;
 int cpu;
 int pid;
 int stack_prot;
 int pgid;
 int cred[8];
 int reloc;
 char enable_vdso;
 char padding[7];
 unsigned long entry;
 unsigned long user_start;
 unsigned long user_end;
 unsigned long rprocess;
 unsigned long rpgtable;
 unsigned long at_phdr;
 unsigned long at_phent;
 unsigned long at_phnum;
 unsigned long at_entry;
 unsigned long at_clktck;
 char *args;
 unsigned long args_len;
 char *envs;
 unsigned long envs_len;
 struct rlimit rlimit[20];
 unsigned long interp_align;
 unsigned long mpol_flags;
 unsigned long mpol_threshold;
 unsigned long heap_extension;
 long stack_premap;
 unsigned long mpol_bind_mask;
 int mpol_mode;
 unsigned long mpol_nodemask[256 /
        (sizeof(unsigned long) * 8)];

 int thp_disable;
 int enable_uti;
 int uti_thread_rank;
 int uti_use_last_cpu;
 int straight_map;
 size_t straight_map_threshold;



 unsigned long mcexec_flags;
 int nr_processes;
 int process_rank;
 __cpu_set_unit cpu_set[(1024 / (8 * sizeof(__cpu_set_unit)))];
 int profile;
 struct program_image_section sections[0];
};

struct ikc_scd_init_param {
 unsigned long request_page;
 unsigned long response_page;
 unsigned long doorbell_page;
 unsigned long post_page;
};

struct syscall_request {

 int rtid;




 int ttid;
 unsigned long valid;
 unsigned long number;
 unsigned long args[6];
};

struct ihk_os_cpu_register {
 unsigned long addr;
 unsigned long val;
 unsigned long addr_ext;
 int sync;
};

enum mcctrl_os_cpu_operation {
 MCCTRL_OS_CPU_READ_REGISTER,
 MCCTRL_OS_CPU_WRITE_REGISTER,
 MCCTRL_OS_CPU_MAX_OP
};

struct ikc_scd_packet {
 struct ihk_ikc_packet_header header;
 int msg;
 int err;
 void *reply;
 union {

  struct {
   int ref;
   int osnum;
   int pid;
   unsigned long arg;
   struct syscall_request req;
   unsigned long resp_pa;
  };


  struct {
   long sysfs_arg1;
   long sysfs_arg2;
   long sysfs_arg3;
  };


  struct {
   int ttid;
  };


  struct {
   unsigned long pdesc;
   enum mcctrl_os_cpu_operation op;
   void *resp;
  };


  struct {
   int eventfd_type;
  };


  struct {
   void *resp;
   int *spin_sleep;
  } futex;


  struct {
   int target_cpu;
   int fault_tid;
   unsigned long fault_address;
   unsigned long fault_reason;
  };
 };

};





struct syscall_response {

 int ttid;

 int stid;
 unsigned long status;
 unsigned long req_thread_status;
 long ret;
 unsigned long fault_address;
 void *pde_data;
};

struct syscall_post {
 unsigned long v[8];
};

extern long do_syscall(struct syscall_request *req, int cpu);
int obtain_clone_cpuid(cpu_set_t *cpu_set, int use_last);
extern long syscall_generic_forwarding(int n, ihk_mc_user_context_t *ctx);

enum {
 __NR_read = 0,
 __NR_write = 1,
 __NR_open = 2,
 __NR_close = 3,
 __NR_stat = 4,
 __NR_fstat = 5,
 __NR_poll = 7,
 __NR_lseek = 8,
 __NR_mmap = 9,
 __NR_mprotect = 10,
 __NR_munmap = 11,
 __NR_brk = 12,
 __NR_rt_sigaction = 13,
 __NR_rt_sigprocmask = 14,
 __NR_rt_sigreturn = 15,
 __NR_ioctl = 16,
 __NR_pread64 = 17,
 __NR_pwrite64 = 18,
 __NR_writev = 20,
 __NR_access = 21,
 __NR_select = 23,
 __NR_sched_yield = 24,
 __NR_mremap = 25,
 __NR_msync = 26,
 __NR_mincore = 27,
 __NR_madvise = 28,
 __NR_shmget = 29,
 __NR_shmat = 30,
 __NR_shmctl = 31,
 __NR_pause = 34,
 __NR_nanosleep = 35,
 __NR_getitimer = 36,
 __NR_setitimer = 38,
 __NR_getpid = 39,
 __NR_clone = 56,
 __NR_fork = 57,
 __NR_vfork = 58,
 __NR_execve = 59,
 __NR_exit = 60,
 __NR_wait4 = 61,
 __NR_kill = 62,
 __NR_uname = 63,
 __NR_semop = 65,
 __NR_shmdt = 67,
 __NR_msgsnd = 69,
 __NR_msgrcv = 70,
 __NR_fcntl = 72,
 __NR_getcwd = 79,
 __NR_unlink = 87,
 __NR_readlink = 89,
 __NR_gettimeofday = 96,
 __NR_getrlimit = 97,
 __NR_getrusage = 98,
 __NR_sysinfo = 99,
 __NR_times = 100,
 __NR_ptrace = 101,
 __NR_getuid = 102,
 __NR_getgid = 104,
 __NR_setuid = 105,
 __NR_setgid = 106,
 __NR_geteuid = 107,
 __NR_getegid = 108,
 __NR_setpgid = 109,
 __NR_getppid = 110,
 __NR_getpgrp = 111,
 __NR_setreuid = 113,
 __NR_setregid = 114,
 __NR_setresuid = 117,
 __NR_getresuid = 118,
 __NR_setresgid = 119,
 __NR_getresgid = 120,
 __NR_setfsuid = 122,
 __NR_setfsgid = 123,
 __NR_rt_sigpending = 127,
 __NR_rt_sigtimedwait = 128,
 __NR_rt_sigqueueinfo = 129,
 __NR_rt_sigsuspend = 130,
 __NR_sigaltstack = 131,
 __NR_sched_setparam = 142,
 __NR_sched_getparam = 143,
 __NR_sched_setscheduler = 144,
 __NR_sched_getscheduler = 145,
 __NR_sched_get_priority_max = 146,
 __NR_sched_get_priority_min = 147,
 __NR_sched_rr_get_interval = 148,
 __NR_mlock = 149,
 __NR_munlock = 150,
 __NR_mlockall = 151,
 __NR_munlockall = 152,
 __NR_prctl = 157,
 __NR_arch_prctl = 158,
 __NR_setrlimit = 160,
 __NR_settimeofday = 164,
 __NR_gettid = 186,
 __NR_tkill = 200,
 __NR_time = 201,
 __NR_futex = 202,
 __NR_sched_setaffinity = 203,
 __NR_sched_getaffinity = 204,
 __NR_io_getevents = 208,
 __NR_remap_file_pages = 216,
 __NR_getdents64 = 217,
 __NR_set_tid_address = 218,
 __NR_semtimedop = 220,
 __NR_clock_gettime = 228,
 __NR_clock_nanosleep = 230,
 __NR_exit_group = 231,
 __NR_epoll_wait = 232,
 __NR_tgkill = 234,
 __NR_mbind = 237,
 __NR_set_mempolicy = 238,
 __NR_get_mempolicy = 239,
 __NR_waitid = 247,
 __NR_migrate_pages = 256,
 __NR_openat = 257,
 __NR_mkdirat = 258,
 __NR_mknodat = 259,
 __NR_fchownat = 260,
 __NR_futimesat = 261,
 __NR_newfstatat = 262,
 __NR_unlinkat = 263,
 __NR_renameat = 264,
 __NR_linkat = 265,
 __NR_symlinkat = 266,
 __NR_readlinkat = 267,
 __NR_fchmodat = 268,
 __NR_faccessat = 269,
 __NR_pselect6 = 270,
 __NR_ppoll = 271,
 __NR_set_robust_list = 273,
 __NR_move_pages = 279,
 __NR_epoll_pwait = 281,
 __NR_signalfd = 282,
 __NR_signalfd4 = 289,

 __NR_perf_event_open = 298,

 __NR_prlimit64 = 302,



 __NR_getcpu = 309,
 __NR_process_vm_readv = 310,
 __NR_process_vm_writev = 311,
 __NR_execveat = 322,
 __NR_clone3 = 435,
 __NR_get_cpu_id = 700,

 __NR_profile = PROFILE_EVENT_MAX,

 __NR_util_migrate_inter_kernel = 730,
 __NR_util_indicate_clone = 731,
 __NR_get_system = 732,
 __NR_util_register_desc = 733,
 __NR_swapout = 801,
 __NR_linux_mlock = 802,
 __NR_suspend_threads = 803,
 __NR_resume_threads = 804,
 __NR_linux_spawn = 811,
};


struct coretable {
 off_t len;
 unsigned long addr;
};

void create_proc_procfs_files(int pid, int cpuid);
void delete_proc_procfs_files(int pid);
void create_os_procfs_files(void);
void delete_os_procfs_files(void);



struct procfs_read {
 unsigned long pbuf;
 unsigned long offset;
 int count;
 int eof;
 int ret;
 int newcpu;
 int readwrite;
 char fname[768];
};

struct procfs_file {
 int status;
 int mode;
 char fname[768];
};

int process_procfs_request(struct ikc_scd_packet *rpacket);
void send_procfs_answer(struct ikc_scd_packet *packet, int err);





struct rusage {
 struct timeval ru_utime;
 struct timeval ru_stime;
 long ru_maxrss;
 long ru_ixrss;
 long ru_idrss;
 long ru_isrss;
 long ru_minflt;
 long ru_majflt;
 long ru_nswap;
 long ru_inblock;
 long ru_oublock;
 long ru_msgsnd;
 long ru_msgrcv;
 long ru_nsignals;
 long ru_nvcsw;
 long ru_nivcsw;
};

struct sysinfo {
 long uptime;
 unsigned long loads[3];
 unsigned long totalram;
 unsigned long freeram;
 unsigned long sharedram;
 unsigned long bufferram;
 unsigned long totalswap;
 unsigned long freeswap;
 unsigned short procs;
 unsigned long totalhigh;
 unsigned long freehigh;
 unsigned int mem_unit;
 char _f[20-2*sizeof(long)-sizeof(int)];
};

extern void terminate(int, int);

struct tod_data_s {
 int8_t do_local;
 int8_t padding[7];
 ihk_atomic64_t version;
 unsigned long clocks_per_sec;
 struct timespec origin;
};
extern struct tod_data_s tod_data;

void tsc_to_ts(unsigned long tsc, struct timespec *ts);
unsigned long timeval_to_jiffy(const struct timeval *ats);
unsigned long timespec_to_jiffy(const struct timespec *ats);

void reset_cputime(void);
enum set_cputime_mode {
 CPUTIME_MODE_K2U = 0,
 CPUTIME_MODE_U2K,
 CPUTIME_MODE_K2K_IN,
 CPUTIME_MODE_K2K_OUT,
};
void set_cputime(enum set_cputime_mode mode);
int do_munmap(void *addr, size_t len, int holding_memory_range_lock);
intptr_t do_mmap(uintptr_t addr0, size_t len0, int prot, int flags, int fd,
  off_t off0, const int vrf0, void *private_data);
long clear_host_pte(uintptr_t addr, size_t len, int holding_memory_range_lock);
typedef int32_t key_t;
int do_shmget(key_t key, size_t size, int shmflg);
struct process_vm;
int arch_map_vdso(struct process_vm *vm);
int arch_setup_vdso(void);
int arch_cpu_read_write_register(struct ihk_os_cpu_register *desc,
  enum mcctrl_os_cpu_operation op);
struct vm_range_numa_policy *vm_range_policy_search(struct process_vm *vm, uintptr_t addr);
void calculate_time_from_tsc(struct timespec *ts);
time_t time(void);
long do_futex(int n, unsigned long arg0, unsigned long arg1,
     unsigned long arg2, unsigned long arg3,
     unsigned long arg4, unsigned long arg5,
     unsigned long _uti_clv,
     void *uti_futex_resp,
     void *_linux_wait_event,
     void *_linux_printk,
     void *_linux_clock_gettime);

struct cpu_mapping {
 int cpu_number;
 int hw_id;
};

struct get_cpu_mapping_req {
 int busy;
 int error;
 long buf_rpa;
 int buf_elems;
 int padding;





};

enum perf_ctrl_type {
 PERF_CTRL_SET,
 PERF_CTRL_GET,
 PERF_CTRL_ENABLE,
 PERF_CTRL_DISABLE,
};

struct perf_ctrl_desc {
 enum perf_ctrl_type ctrl_type;
 int err;
 union {

  struct {
   unsigned int target_cntr;
   unsigned long config;
   unsigned long read_value;
   unsigned disabled :1,
            pinned :1,
            exclude_user :1,
            exclude_kernel :1,
            exclude_hv :1,
            exclude_idle :1;
  };


  struct {
   unsigned long target_cntr_mask;
  };
 };
};
# 718 "/home/holden/mckernel/kernel/include/syscall.h"
typedef struct uti_attr {


 uint64_t numa_set[((1024) + sizeof(uint64_t) * 8 - 1) /
                    (sizeof(uint64_t) * 8)];
 uint64_t flags;
} uti_attr_t;

struct thread;
long arch_ptrace_syscall_event(struct thread *thread,
          ihk_mc_user_context_t *ctx, long setret);

struct uti_ctx {
 union {
  char ctx[4096];
  struct {
   int uti_refill_tid;
  };
 };
};

struct move_pages_smp_req {
 unsigned long count;
 const void **user_virt_addr;
 int *user_status;
 const int *user_nodes;
 void **virt_addr;
 int *status;
 pte_t **ptep;
 int *nodes;
 int nodes_ready;
 int *nr_pages;
 unsigned long *dst_phys;
 struct process *proc;
 ihk_atomic_t phase_done;
 int phase_ret;
};





extern long (*linux_wait_event)(void *_resp, unsigned long nsec_timeout);
extern int (*linux_printk)(const char *fmt, ...);
extern int (*linux_clock_gettime)(clockid_t clk_id, struct timespec *tp);






extern void terminate_host(int pid, struct thread *thread);
struct sig_pending *getsigpending(struct thread *thread, int delflag);
int interrupt_from_user(void *regs0);
extern unsigned long shmid_index[];
# 27 "/home/holden/mckernel/kernel/include/process.h" 2
# 1 "/home/holden/mckernel/lib/include/bitops.h" 1
# 9 "/home/holden/mckernel/lib/include/bitops.h"
unsigned long find_next_bit(const unsigned long *addr, unsigned long size,
       unsigned long offset);

unsigned long find_next_zero_bit(const unsigned long *addr,
     unsigned long size, unsigned long offset);

unsigned long find_first_bit(const unsigned long *addr,
        unsigned long size);

unsigned long find_first_zero_bit(const unsigned long *addr,
      unsigned long size);

# 1 "/home/holden/mckernel/lib/include/bitops-test_bit.h" 1



int test_bit(int nr, const void *addr);
# 22 "/home/holden/mckernel/lib/include/bitops.h" 2

extern unsigned int __sw_hweight32(unsigned int w);
extern unsigned int __sw_hweight16(unsigned int w);
extern unsigned int __sw_hweight8(unsigned int w);
extern unsigned long __sw_hweight64(uint64_t w);
unsigned long hweight_long(unsigned long w);



unsigned long ihk_bit_word(unsigned long nr);
unsigned long ihk_align_mask(unsigned long x, unsigned long mask);
unsigned long ihk_align(unsigned long x, unsigned long a);
int ihk_is_aligned(unsigned long x, unsigned long a);



# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/arch-bitops.h" 1
# 18 "/home/holden/mckernel/arch/x86_64/kernel/include/arch-bitops.h"
int fls(int x);
int ffs(int x);
unsigned long __ffs(unsigned long word);
unsigned long ffz(unsigned long word);
void set_bit(int nr, volatile unsigned long *addr);
void clear_bit(int nr, volatile unsigned long *addr);
# 39 "/home/holden/mckernel/lib/include/bitops.h" 2
# 28 "/home/holden/mckernel/kernel/include/process.h" 2

# 1 "/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/owner-work/output/build/config.h" 1
# 30 "/home/holden/mckernel/kernel/include/process.h" 2
# 61 "/home/holden/mckernel/kernel/include/process.h"
unsigned long PROT_TO_VR_FLAG(unsigned long prot);
unsigned long VRFLAG_PROT_TO_MAXPROT(unsigned long vrflag);
unsigned long VRFLAG_MAXPROT_TO_PROT(unsigned long vrflag);
# 156 "/home/holden/mckernel/kernel/include/process.h"
int __WEXITSTATUS(int status);


int __WTERMSIG(int status);


int __WSTOPSIG(int status);


int __WIFEXITED(int status);


int __WIFSIGNALED(int status);


int __WIFSTOPPED(int status);
# 190 "/home/holden/mckernel/kernel/include/process.h"
enum {
 MPOL_DEFAULT,
 MPOL_PREFERRED,
 MPOL_BIND,
 MPOL_INTERLEAVE,
 MPOL_LOCAL,
 MPOL_MAX,
};

enum mpol_rebind_step {
 MPOL_REBIND_ONCE,
 MPOL_REBIND_STEP1,
 MPOL_REBIND_STEP2,
 MPOL_REBIND_NSTEP,
};
# 253 "/home/holden/mckernel/kernel/include/process.h"
# 1 "/home/holden/mckernel/kernel/include/waitq.h" 1
# 22 "/home/holden/mckernel/kernel/include/waitq.h"
struct thread;
struct waitq_entry;

typedef int (*waitq_func_t)(struct waitq_entry *wait, unsigned mode,
       int flags, void *key);

int default_wake_function(struct waitq_entry *wait, unsigned mode, int flags,
                 void *key);
int locked_wake_function(struct waitq_entry *wait, unsigned mode, int flags,
                 void *key);

typedef struct waitq {
 ihk_spinlock_t lock;
 struct list_head waitq;
} waitq_t;



typedef struct waitq_entry {
 struct list_head link;
 void *private;
 unsigned int flags;
 waitq_func_t func;
} waitq_entry_t;

extern void waitq_init(waitq_t *waitq);
extern void waitq_init_entry(waitq_entry_t *entry, struct thread *proc);
extern void waitq_init_locked_entry(waitq_entry_t *entry, struct thread *proc);
extern int waitq_active(waitq_t *waitq);
extern void waitq_add_entry(waitq_t *waitq, waitq_entry_t *entry);
extern void waitq_add_entry_locked(waitq_t *waitq, waitq_entry_t *entry);
extern void waitq_prepare_to_wait(waitq_t *waitq,
                                  waitq_entry_t *entry, int state);
extern void waitq_finish_wait(waitq_t *waitq, waitq_entry_t *entry);
extern void waitq_wakeup(waitq_t *waitq);
extern int waitq_wake_nr(waitq_t *waitq, int nr);
extern int waitq_wake_nr_locked(waitq_t *waitq, int nr);
extern void waitq_remove_entry(waitq_t *waitq, waitq_entry_t *entry);
extern void waitq_remove_entry_locked(waitq_t *waitq, waitq_entry_t *entry);
# 254 "/home/holden/mckernel/kernel/include/process.h" 2
# 1 "/home/holden/mckernel/kernel/include/futex.h" 1
# 77 "/home/holden/mckernel/kernel/include/futex.h"
int FUTEX_OP(int op, int oparg, int cmp, int cmparg);
# 89 "/home/holden/mckernel/kernel/include/futex.h"
# 1 "/home/holden/mckernel/kernel/include/process.h" 1
# 90 "/home/holden/mckernel/kernel/include/futex.h" 2

# 1 "/home/holden/mckernel/kernel/include/plist.h" 1
# 79 "/home/holden/mckernel/kernel/include/plist.h"
struct plist_head {
 struct list_head prio_list;
 struct list_head node_list;




};

struct plist_node {
 int prio;
 struct plist_head plist;
};






void plist_head_init(struct plist_head *head, ihk_spinlock_t *lock);






void plist_head_init_raw(struct plist_head *head, ihk_spinlock_t *lock);






void plist_node_init(struct plist_node *node, int prio);

extern void plist_add(struct plist_node *node, struct plist_head *head);
extern void plist_del(struct plist_node *node, struct plist_head *head);





int plist_head_empty(const struct plist_head *head);





int plist_node_empty(const struct plist_node *node);







struct plist_node *plist_first(const struct plist_head *head);
# 92 "/home/holden/mckernel/kernel/include/futex.h" 2
# 108 "/home/holden/mckernel/kernel/include/futex.h"
# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/arch-futex.h" 1
# 18 "/home/holden/mckernel/arch/x86_64/kernel/include/arch-futex.h"
int futex_atomic_cmpxchg_inatomic(int *uaddr, int oldval, int newval);
int futex_atomic_op_inuser(int encoded_op, int *uaddr);
# 109 "/home/holden/mckernel/kernel/include/futex.h" 2
# 123 "/home/holden/mckernel/kernel/include/futex.h"
struct process_vm;

int get_futex_value_locked(uint32_t *dest, uint32_t *from);






struct futex_hash_bucket {
 ihk_spinlock_t lock;
 struct plist_head chain;
};

struct futex_hash_bucket *get_futex_queues(void);

union futex_key {
 struct {
  unsigned long pgoff;
  void *phys;
  int offset;
 } shared;
 struct {
  unsigned long address;
  struct process_vm *mm;
  int offset;
 } private;
 struct {
  unsigned long word;
  void *ptr;
  int offset;
 } both;
};




extern int futex_init(void);

struct cpu_local_var;
extern int
futex(
 uint32_t * uaddr,
 int op,
 uint32_t val,
 uint64_t timeout,
 uint32_t * uaddr2,
 uint32_t val2,
 uint32_t val3,
 int fshared
);
# 195 "/home/holden/mckernel/kernel/include/futex.h"
struct futex_q {
 struct plist_node list;

 struct thread *task;
 ihk_spinlock_t *lock_ptr;
 union futex_key key;
 union futex_key *requeue_pi_key;
 uint32_t bitset;


 void *uti_futex_resp;


 int linux_cpu;


 void *th_spin_sleep;
 void *th_status;
 void *th_spin_sleep_lock;
 void *proc_status;
 void *proc_update_lock;
 void *runq_lock;
 void *clv_flags;
 int intr_id;
 int intr_vector;

 unsigned long th_spin_sleep_pa;
 unsigned long th_status_pa;
 unsigned long th_spin_sleep_lock_pa;
 unsigned long proc_status_pa;
 unsigned long proc_update_lock_pa;
 unsigned long runq_lock_pa;
 unsigned long clv_flags_pa;
};
# 255 "/home/holden/mckernel/kernel/include/process.h" 2

struct resource_set;
struct process_hash;
struct thread_hash;
struct address_space;
struct process;
struct thread;
struct process_vm;
struct vm_regions;
struct vm_range;

struct swapinfo;



struct resource_set {
 struct list_head list;
 char *path;
 struct process_hash *process_hash;
 struct thread_hash *thread_hash;
 struct list_head phys_mem_list;
 mcs_rwlock_lock_t phys_mem_lock;
 cpu_set_t cpu_set;
 mcs_rwlock_lock_t cpu_set_lock;
 struct process *pid1;
};

extern struct list_head resource_set_list;
extern mcs_rwlock_lock_t resource_set_lock;
extern int idle_halt;
extern int allow_oversubscribe;
extern int time_sharing;
extern ihk_spinlock_t runq_reservation_lock;

struct process_hash {
 struct list_head list[73];
 mcs_rwlock_lock_t lock[73];
};

int process_hash(int pid);
int thread_hash(int tid);

struct thread_hash {
 struct list_head list[73];
 mcs_rwlock_lock_t lock[73];
};

struct address_space {
 struct page_table *page_table;
 void *opt;
 void (*free_cb)(struct address_space *, void *);
 ihk_atomic_t refcount;
 cpu_set_t cpu_set;
 ihk_spinlock_t cpu_set_lock;
 int nslots;
 int pids[];
};

struct user_fpregs_struct
{
 unsigned short cwd;
 unsigned short swd;
 unsigned short ftw;
 unsigned short fop;
 unsigned long rip;
 unsigned long rdp;
 unsigned int mxcsr;
 unsigned int mxcr_mask;
 unsigned int st_space[32];
 unsigned int xmm_space[64];
 unsigned int padding[24];
};

struct user_regs_struct
{
 unsigned long r15;
 unsigned long r14;
 unsigned long r13;
 unsigned long r12;
 unsigned long rbp;
 unsigned long rbx;
 unsigned long r11;
 unsigned long r10;
 unsigned long r9;
 unsigned long r8;
 unsigned long rax;
 unsigned long rcx;
 unsigned long rdx;
 unsigned long rsi;
 unsigned long rdi;
 unsigned long orig_rax;
 unsigned long rip;
 unsigned long cs;
 unsigned long eflags;
 unsigned long rsp;
 unsigned long ss;
 unsigned long fs_base;
 unsigned long gs_base;
 unsigned long ds;
 unsigned long es;
 unsigned long fs;
 unsigned long gs;
};

struct user
{
 struct user_regs_struct regs;
 int u_fpvalid;
 struct user_fpregs_struct i387;
 unsigned long int u_tsize;
 unsigned long int u_dsize;
 unsigned long int u_ssize;
 unsigned long start_code;
 unsigned long start_stack;
 long int signal;
 int reserved;
 struct user_regs_struct* u_ar0;
 struct user_fpregs_struct* u_fpstate;
 unsigned long int magic;
 char u_comm [32];
 unsigned long int u_debugreg [8];
};



struct vm_range {
 struct rb_node vm_rb_node;
 unsigned long start, end;
 unsigned long flag;
 unsigned long straight_start;
 struct memobj *memobj;
 off_t objoff;
 int pgshift;
 int padding;



 void *private_data;
};

struct vm_range_numa_policy {
 struct rb_node policy_rb_node;
 unsigned long start, end;
 unsigned long numa_mask[(((256) + (sizeof(long) * 8) - 1) / (sizeof(long) * 8))];
 int numa_mem_policy;
 int il_prev;
};

struct vm_regions {
 unsigned long vm_start, vm_end;
 unsigned long text_start, text_end;
 unsigned long data_start, data_end;
 unsigned long brk_start, brk_end, brk_end_allocated;
 unsigned long map_start, map_end;
 unsigned long stack_start, stack_end;
 unsigned long user_start, user_end;
};

struct process_vm;

struct mckfd {
 struct mckfd *next;
 int fd;
 int sig_no;
 long data;
 void *opt;
 long (*read_cb)(struct mckfd *, ihk_mc_user_context_t *);
 int (*ioctl_cb)(struct mckfd *, ihk_mc_user_context_t *);
 long (*mmap_cb)(struct mckfd *, ihk_mc_user_context_t *);
 int (*close_cb)(struct mckfd *, ihk_mc_user_context_t *);
 int (*fcntl_cb)(struct mckfd *, ihk_mc_user_context_t *);
 int (*dup_cb)(struct mckfd *, ihk_mc_user_context_t *);
};




struct sig_common {
 mcs_rwlock_lock_t lock;
 ihk_atomic_t use;
 struct k_sigaction action[64];
 struct list_head sigpending;
};

struct sig_pending {
 struct list_head list;
 sigset_t sigmask;
 siginfo_t info;
 int ptracecont;
 int interrupted;
};

typedef void pgio_func_t(void *arg);

struct mcexec_tid {
 int tid;
 struct thread *thread;
};





struct process {
 struct list_head hash_list;
 mcs_rwlock_lock_t update_lock;


 struct process_vm *vm;


 struct list_head threads_list;
 struct list_head report_threads_list;






 struct thread *main_thread;
 mcs_rwlock_lock_t threads_lock;

 struct mcexec_tid *tids;
 int nr_tids;



 struct process *parent;
 struct process *ppid_parent;
 struct list_head children_list;
 struct list_head ptraced_children_list;
 mcs_rwlock_lock_t children_lock;
 struct list_head siblings_list;
 struct list_head ptraced_siblings_list;

 ihk_atomic_t refcount;


 int status;
# 509 "/home/holden/mckernel/kernel/include/process.h"
 unsigned long group_exit_status;




 struct waitq waitpid_q;


 int pid;
 int pgid;
 int ruid;
 int euid;
 int suid;
 int fsuid;
 int rgid;
 int egid;
 int sgid;
 int fsgid;
 int execed;
 int nohost;
 int nowait;
 struct rlimit rlimit[20];
 unsigned long saved_auxv[38];
 char *saved_cmdline;
 long saved_cmdline_len;
 cpu_set_t cpu_set;


 int termsig;

 ihk_spinlock_t mckfd_lock;
 struct mckfd *mckfd;


 struct timespec stime;
 struct timespec utime;


 struct timespec stime_children;
 struct timespec utime_children;

 long maxrss;
 long maxrss_children;

 unsigned long mpol_flags;
 size_t mpol_threshold;
 unsigned long heap_extension;
 unsigned long mpol_bind_mask;
 int mpol_mode;

 int enable_uti;
 int uti_thread_rank;
 int uti_use_last_cpu;
 int clone_count;
 int thp_disable;

 int straight_map;



 size_t straight_map_threshold;
 unsigned long mcexec_flags;


 int perf_status;




 struct mc_perf_event *monitoring_event;

 int profile;
 mcs_lock_node_t profile_lock;
 struct profile_event *profile_events;
 unsigned long profile_elapsed_ts;

 int nr_processes;
 int process_rank;

 void *straight_va;
 size_t straight_len;
 unsigned long straight_pa;

 int coredump_barrier_count, coredump_barrier_count2;
 mcs_rwlock_lock_t coredump_lock;





};
# 620 "/home/holden/mckernel/kernel/include/process.h"
struct sched_param {
 int sched_priority;
};

struct thread {
 struct list_head hash_list;

 int cpu_id;
 int tid;
 char pthread_routine[4096 + 64];
 int status;







 int exit_status;





 int signal_flags;

 int termsig;


 struct process_vm *vm;


 ihk_mc_kernel_context_t ctx;
 ihk_mc_user_context_t *uctx;


 struct process *proc;
 struct list_head siblings_list;


 struct list_head sched_list;
 int sched_policy;
 struct sched_param sched_param;

 ihk_spinlock_t spin_sleep_lock;
 int spin_sleep;


 struct process *report_proc;
 struct list_head report_siblings_list;





 int ptrace;





 unsigned long ptrace_eventmsg;
 ihk_mc_user_context_t ptrace_saved_uctx;
 int ptrace_saved_uctx_valid;

 ihk_atomic_t refcount;

 int *clear_child_tid;
 unsigned long tlsblock_base, tlsblock_limit;


 cpu_set_t cpu_set;
 fp_regs_struct *fp_regs;
 int in_syscall_offload;


 int profile;
 struct profile_event *profile_events;
 unsigned long profile_start_ts;
 unsigned long profile_elapsed_ts;



 struct sig_common *sigcommon;
 sigset_t sigmask;
 stack_t sigstack;
 struct list_head sigpending;
 mcs_rwlock_lock_t sigpendinglock;
 volatile int sigevent;


 pgio_func_t *pgio_fp;
 void *pgio_arg;


 unsigned long *ptrace_debugreg;
 struct sig_pending *ptrace_recvsig;
 struct sig_pending *ptrace_sendsig;







 unsigned long system_tsc;
 unsigned long user_tsc;
 unsigned long base_tsc;
 int times_update;
 int in_kernel;


 int itimer_enabled;
 struct itimerval itimer_virtual;
 struct itimerval itimer_prof;
 struct timespec itimer_virtual_value;
 struct timespec itimer_prof_value;


 struct waitq scd_wq;

 unsigned long clone_pthread_start_routine;
 int uti_state;
 int mod_clone;
 struct uti_attr *mod_clone_arg;
 int parent_cpuid;
 int uti_refill_tid;
 struct futex_q futex_q;



 unsigned long pmc_alloc_map;
 unsigned long extra_reg_alloc_map;


 void *coredump_regs;
 struct waitq coredump_wq;
 int coredump_status;

 void (*rpf_backlog)(void *arg);
 void *rpf_arg;





};






struct process_vm {
 struct address_space *address_space;
 struct rb_root vm_range_tree;
 struct vm_regions region;
 struct process *proc;
 void *opt;
 void (*free_cb)(struct process_vm *, void *);
 void *vdso_addr;
 void *vvar_addr;

 ihk_spinlock_t page_table_lock;
 ihk_rwspinlock_t memory_range_lock;





 int is_memory_range_lock_taken;


 ihk_atomic_t refcount;
 int exiting;

 long currss;
 unsigned long numa_mask[(((256) + (sizeof(long) * 8) - 1) / (sizeof(long) * 8))];
 int numa_mem_policy;
 int il_prev;

 struct rb_root vm_range_numa_policy_tree;
 struct vm_range *range_cache[4];
 int range_cache_ind;
 struct swapinfo *swapinfo;






};

int has_cap_ipc_lock(struct thread *th);
int has_cap_sys_admin(struct thread *th);

void hold_address_space(struct address_space *);
void release_address_space(struct address_space *);
struct thread *create_thread(unsigned long user_pc,
  unsigned long *__cpu_set, size_t cpu_set_size);
struct thread *clone_thread(struct thread *org, unsigned long pc,
                              unsigned long sp, int clone_flags);
void destroy_thread(struct thread *thread);
int hold_thread(struct thread *thread);
void release_thread(struct thread *thread);


int release_thread_checked(struct thread *thread);
void flush_process_memory(struct process_vm *vm);
void hold_process_vm(struct process_vm *vm);
void release_process_vm(struct process_vm *vm);

int release_process_vm_checked(struct process_vm *vm);
void hold_process(struct process *);
void release_process(struct process *);
void free_all_process_memory_range(struct process_vm *vm);
void free_process_memory_ranges(struct process_vm *vm);
int populate_process_memory(struct process_vm *vm, void *start, size_t len);

int add_process_memory_range(struct process_vm *vm,
  unsigned long start, unsigned long end,
  unsigned long phys, unsigned long flag,
  struct memobj *memobj, off_t offset,
  int pgshift, void *private_data, struct vm_range **rp);
int remove_process_memory_range(struct process_vm *vm, unsigned long start,
  unsigned long end, int *ro_freedp);
int split_process_memory_range(struct process_vm *vm,
  struct vm_range *range, uintptr_t addr, struct vm_range **splitp);
int join_process_memory_range(struct process_vm *vm, struct vm_range *surviving,
  struct vm_range *merging);
int change_prot_process_memory_range(
  struct process_vm *vm, struct vm_range *range,
  unsigned long newflag);
int remap_process_memory_range(struct process_vm *vm, struct vm_range *range,
  uintptr_t start, uintptr_t end, off_t off);
int sync_process_memory_range(struct process_vm *vm, struct vm_range *range,
  uintptr_t start, uintptr_t end);
int invalidate_process_memory_range(struct process_vm *vm,
  struct vm_range *range, uintptr_t start, uintptr_t end);
struct vm_range *lookup_process_memory_range(
  struct process_vm *vm, uintptr_t start, uintptr_t end);
struct vm_range *next_process_memory_range(
  struct process_vm *vm, struct vm_range *range);
struct vm_range *previous_process_memory_range(
  struct process_vm *vm, struct vm_range *range);
int extend_up_process_memory_range(struct process_vm *vm,
  struct vm_range *range, uintptr_t newend);

int page_fault_process_memory_range(struct process_vm *vm,
        struct vm_range *range,
        uintptr_t fault_addr, uint64_t reason);
int page_fault_process_vm(struct process_vm *fault_vm, void *fault_addr,
  uint64_t reason);
int remove_process_region(struct process_vm *vm,
                          unsigned long start, unsigned long end);
struct program_load_desc;
int init_process_stack(struct thread *thread, struct program_load_desc *pn,
                        unsigned long at_base, int argc, char **argv,
                        int envc, char **env);
unsigned long extend_process_region(struct process_vm *vm,
  unsigned long end_allocated,
  unsigned long address, unsigned long flag);
extern enum ihk_mc_pt_attribute arch_vrflag_to_ptattr(unsigned long flag, uint64_t fault, pte_t *ptep);
enum ihk_mc_pt_attribute common_vrflag_to_ptattr(unsigned long flag, uint64_t fault, pte_t *ptep);

void schedule(void);
void spin_sleep_or_schedule(void);
void runq_add_thread(struct thread *thread, int cpu_id);
void runq_del_thread(struct thread *thread, int cpu_id);
int sched_wakeup_thread(struct thread *thread, int valid_states);
int sched_wakeup_thread_locked(struct thread *thread, int valid_states);

void sched_request_migrate(int cpu_id, struct thread *thread);
void check_need_resched(void);

void cpu_set(int cpu, cpu_set_t *cpu_set, ihk_spinlock_t *lock);
void cpu_clear(int cpu, cpu_set_t *cpu_set, ihk_spinlock_t *lock);
void cpu_clear_and_set(int c_cpu, int s_cpu,
  cpu_set_t *cpu_set, ihk_spinlock_t *lock);

void release_cpuid(int cpuid);

struct thread *find_thread(int pid, int tid);
void thread_unlock(struct thread *thread);
struct process *find_process(int pid, struct mcs_rwlock_node_irqsave *lock);
void process_unlock(struct process *proc, struct mcs_rwlock_node_irqsave *lock);
void chain_process(struct process *);
void chain_thread(struct thread *);
void proc_init(void);
void set_timer(int runq_locked);
struct sig_pending *hassigpending(struct thread *thread);
extern int do_signal(unsigned long rc, void *regs0, struct thread *thread,
       struct sig_pending *pending, int num);
extern void check_signal(unsigned long rc, void *regs0, int num);
extern unsigned long do_kill(struct thread *thread, int pid, int tid, int sig,
        struct siginfo *info, int ptracecont);
extern void set_signal(int sig, void *regs, struct siginfo *info);
extern void check_sig_pending(void);
void clear_single_step(struct thread *thread);

void release_fp_regs(struct thread *proc);
int save_fp_regs(struct thread *proc);
int copy_fp_regs(struct thread *from, struct thread *to);
void restore_fp_regs(struct thread *proc);
void clear_fp_regs(void);



int access_ok(struct process_vm *vm, int type, uintptr_t addr, size_t len);
# 25 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c" 2
# 1 "/home/holden/mckernel/kernel/include/process_helpers.h" 1






struct list_head;
struct mckfd;
struct memobj;
struct program_load_desc;
struct process_vm;
struct process;
struct rb_root;
struct thread;
struct vm_range;







struct process_init_state_offsets {
 unsigned long pid_offset;
 unsigned long status_offset;
 unsigned long parent_offset;
 unsigned long ppid_parent_offset;
 unsigned long pgid_offset;
 unsigned long ruid_offset;
 unsigned long euid_offset;
 unsigned long suid_offset;
 unsigned long fsuid_offset;
 unsigned long rgid_offset;
 unsigned long egid_offset;
 unsigned long sgid_offset;
 unsigned long fsgid_offset;
 unsigned long mpol_flags_offset;
 unsigned long mpol_threshold_offset;
 unsigned long thp_disable_offset;
 unsigned long rlimit_offset;
 unsigned long rlimit_size;
 unsigned long cpu_set_offset;
 unsigned long cpu_set_size;
 unsigned long enable_uti_offset;
};

typedef struct vm_range *(*process_add_range_alloc_fn_t)(unsigned long size);
typedef void (*process_add_range_free_fn_t)(struct vm_range *range);
typedef int (*process_add_range_insert_fn_t)(struct process_vm *vm,
          struct vm_range *range);
typedef int (*process_add_range_update_fn_t)(struct process_vm *vm,
          struct vm_range *range,
          unsigned long phys,
          unsigned long attr);
typedef void (*process_add_range_remove_fn_t)(struct process_vm *vm,
           unsigned long start,
           unsigned long end);
typedef void (*process_add_range_mark_xpmem_fn_t)(struct vm_range *range);
typedef void (*process_add_range_memclear_fn_t)(unsigned long phys,
      unsigned long bytes);
typedef void (*process_add_range_log_fn_t)(int event, int rc,
        unsigned long start,
        unsigned long end);
typedef void (*process_vm_range_insert_log_fn_t)(int event,
       struct process_vm *vm,
       struct vm_range *newrange,
       struct vm_range *range);
typedef void (*process_vm_range_insert_dump_fn_t)(struct process_vm *vm);
typedef void (*process_range_public_log_fn_t)(int event,
           struct process_vm *vm,
           struct vm_range *range,
           unsigned long start,
           unsigned long end,
           int error);
typedef void (*process_range_memobj_ref_fn_t)(struct memobj *memobj);
typedef int (*process_split_range_insert_fn_t)(struct process_vm *vm,
            struct vm_range *range);
typedef struct vm_range *(*process_split_range_alloc_fn_t)(
 unsigned long size, unsigned long flags);
typedef void (*process_split_range_alloc_log_fn_t)(
 struct process_vm *vm, struct vm_range *range,
 unsigned long addr, void *splitp);
typedef int (*process_split_range_pt_split_fn_t)(void *page_table,
       struct process_vm *vm,
       struct vm_range *range,
       void *addr);
typedef void (*process_split_range_pt_log_fn_t)(int error);
typedef void (*process_split_range_publish_log_fn_t)(int error);
typedef int (*process_split_shm_lookup_page_fn_t)(struct memobj *obj,
        long off, int p2align,
        uintptr_t *physp,
        unsigned long *pflag);
typedef void *(*process_split_shm_phys_to_page_fn_t)(unsigned long phys);
typedef int (*process_split_shm_update_page_fn_t)(struct memobj *obj,
        void *page_table,
        void *page, void *vaddr);
typedef void (*process_split_shm_log_fn_t)(int event, int error);
typedef void (*process_join_range_free_fn_t)(struct vm_range *range);
typedef int (*process_join_range_tofu_fn_t)(struct process_vm *vm,
         struct vm_range *surviving,
         struct vm_range *merging);
typedef int (*process_free_range_page_size_fn_t)(size_t current,
       size_t *nextp);
typedef void *(*process_free_range_phys_to_virt_fn_t)(unsigned long phys);
typedef void (*process_free_range_pages_fn_t)(void *addr,
           unsigned long pages);
typedef int (*process_free_range_clear_main_fn_t)(struct process_vm *vm,
        unsigned long start,
        unsigned long end);
typedef void (*process_free_range_free_fn_t)(struct vm_range *range);
typedef int (*process_free_range_pt_free_fn_t)(void *page_table,
            struct process_vm *vm,
            unsigned long start,
            unsigned long end,
            void *memobj);
typedef int (*process_free_range_pt_clear_fn_t)(void *page_table,
      struct process_vm *vm,
      unsigned long start,
      unsigned long end);
typedef int (*process_free_range_tofu_remove_fn_t)(struct process_vm *vm,
         struct vm_range *range);
typedef void (*process_free_range_log_fn_t)(int event,
         struct process_vm *vm,
         struct vm_range *range,
         unsigned long start,
         unsigned long end,
         int error);
typedef int (*process_visit_pte_range_fn_t)(void *page_table,
         unsigned long start,
         unsigned long end, int pgshift,
         int flags, void *visit_fn,
         void *arg);
typedef struct vm_range *(*process_copy_range_lookup_fn_t)(
 struct process_vm *vm, unsigned long start, unsigned long end);
typedef struct vm_range *(*process_copy_range_next_fn_t)(
 struct process_vm *vm, struct vm_range *range);
typedef void (*process_copy_user_ranges_log_fn_t)(
 struct process_vm *orgvm, struct vm_range *range, long fault_addr);
typedef void *(*process_lookup_pte_fn_t)(void *page_table,
      unsigned long addr, int pgshift,
      size_t *pgsizep);
typedef int (*process_pte_test_fn_t)(void *ptep);
typedef int (*process_pte_pgsize_test_fn_t)(void *ptep, size_t pgsize);
typedef int (*process_split_contiguous_pages_fn_t)(void *ptep,
         size_t pgsize,
         unsigned int memobj_flags);
typedef uintptr_t (*process_pte_get_phys_fn_t)(void *ptep);
typedef void *(*process_phys_to_page_fn_t)(uintptr_t phys);
typedef long (*process_page_offset_fn_t)(void *page);
typedef void (*process_pte_make_fileoff_fn_t)(long off, size_t pgsize,
           void *ptep);
typedef void (*process_pte_xchg_fn_t)(void *ptep, void *valp);
typedef void (*process_flush_tlb_single_fn_t)(unsigned long addr);
typedef int (*process_pgsize_to_tbllv_fn_t)(size_t pgsize);
typedef size_t (*process_tbllv_to_contpgsize_fn_t)(int level);
typedef int (*process_page_unmap_fn_t)(void *page);
typedef void (*process_panic_fn_t)(const char *message);
typedef int (*process_memobj_invalidate_page_fn_t)(struct memobj *memobj,
         uintptr_t phys,
         size_t pgsize);
typedef void (*process_invalidate_one_page_log_fn_t)(void *arg,
           void *page_table,
           void *ptep,
           unsigned long pte_value,
           void *pgaddr,
           int pgshift,
           int error);
typedef void (*process_sync_range_log_fn_t)(struct process_vm *vm,
         struct vm_range *range,
         unsigned long start,
         unsigned long end,
         int error);
typedef void (*process_remap_range_log_fn_t)(int event,
          struct process_vm *vm,
          struct vm_range *range,
          unsigned long start,
          unsigned long end,
          long off,
          int old_pgshift,
          int error);
typedef int (*process_memory_range_free_fn_t)(struct process_vm *vm,
           struct vm_range *range);
typedef void (*process_memory_range_log_fn_t)(struct process_vm *vm,
           struct vm_range *range,
           int error);
typedef void (*process_mckfd_free_fn_t)(struct mckfd *fdp);
typedef int (*process_mckfd_dup_fn_t)(struct mckfd *fdp, void *ctx);
typedef void (*process_policy_free_fn_t)(void *policy);
typedef void (*process_detach_address_space_fn_t)(void *address_space,
        int pid);
typedef void (*process_release_process_fn_t)(void *process);
typedef void (*process_optional_free_fn_t)(void *ptr);
typedef void (*process_release_fp_regs_fn_t)(struct thread *thread);
typedef void (*process_ref_inc_fn_t)(void *object, unsigned long ref_offset);
typedef int (*process_ref_dec_and_test_fn_t)(void *object,
          unsigned long ref_offset);
typedef int (*process_default_ncpus_fn_t)(void);
typedef void (*process_create_cpu_log_fn_t)(int event, int pid, int cpu);
typedef void (*process_hold_thread_warn_fn_t)(void *thread);
typedef void *(*process_current_resource_set_fn_t)(void);
typedef void (*process_resource_process_action_fn_t)(void *resource_set,
           void *process);
typedef void (*process_process_action_fn_t)(void *process);
typedef void (*process_resource_set_action_fn_t)(void *resource_set);
typedef void (*process_tid_log_fn_t)(int tid, void *thread, int new_tid);
typedef void (*process_thread_profile_fn_t)(void *thread, void *process);
typedef void (*process_thread_action_fn_t)(void *thread);
typedef void (*process_thread_proc_action_fn_t)(void *process, void *thread);
typedef void (*process_thread_tid_action_fn_t)(void *process, void *thread,
            int new_tid);
typedef void (*process_vm_action_fn_t)(void *vm);

typedef int (*process_vm_release_checked_fn_t)(void *vm);
typedef void (*process_mcs_rwlock_fn_t)(unsigned long lock_addr, void *node);
typedef int (*process_alloc_debugreg_fn_t)(void *thread);
typedef void (*process_ptrace_traceme_log_fn_t)(int event, int pid,
      unsigned long value,
      int error);
typedef unsigned long (*process_spin_lock_fn_t)(unsigned long lock_addr);
typedef void (*process_spin_unlock_fn_t)(unsigned long lock_addr,
      unsigned long irqstate);
typedef void (*process_free_fn_t)(void *ptr);
typedef void (*process_address_space_free_cb_fn_t)(void *address_space,
         void *opt);
typedef void (*process_address_space_action_fn_t)(void *address_space);
typedef void (*process_vm_free_cb_fn_t)(void *vm, void *opt);
typedef void (*process_pt_destroy_fn_t)(void *page_table);
typedef void *(*process_alloc_fn_t)(unsigned long size, unsigned long flags);
typedef void *(*process_pt_create_fn_t)(unsigned long flags);
typedef void (*process_ref_set_fn_t)(void *object, unsigned long ref_offset,
         int value);
typedef void (*process_spin_init_fn_t)(unsigned long lock_addr);
typedef void (*process_rwlock_init_fn_t)(unsigned long lock_addr);
typedef void (*process_vm_init_numa_log_fn_t)(int numa_id);
typedef void (*process_waitq_init_fn_t)(unsigned long waitq_addr);
typedef void (*process_mcs_lock_init_fn_t)(unsigned long lock_addr);
typedef void *(*process_alloc_pages_fn_t)(int npages, unsigned long flags);
typedef void *(*process_create_address_space_fn_t)(int nslots);
typedef void (*process_release_address_space_fn_t)(void *address_space);
typedef int (*process_init_process_fn_t)(void *process, void *parent);
typedef int (*process_init_process_vm_fn_t)(void *owner, void *address_space,
         void *vm);
typedef void (*process_init_user_process_fn_t)(void *thread,
            unsigned long stack_top,
            unsigned long user_pc,
            unsigned long user_sp);
typedef void (*process_sched_init_context_fn_t)(void *thread);
typedef int (*process_sched_save_fp_fn_t)(void *thread);
typedef void (*process_sched_timer_init_fn_t)(int cpu);
typedef unsigned long (*process_virt_to_phys_fn_t)(void *addr);
typedef void *(*process_phys_to_virt_fn_t)(unsigned long phys);
typedef void (*process_memset_fn_t)(void *addr, int value, size_t len);
typedef void (*process_memset_smp_log_fn_t)(int event, int cpu_index,
         int nr_cpus, unsigned long phys,
         size_t len, unsigned long start,
         unsigned long end);
typedef int (*process_smp_call_fn_t)(void *cpu_set, void *handler,
         void *arg);
typedef unsigned long (*process_attr_from_vrflag_fn_t)(unsigned long flag,
             unsigned long fault,
             void *ptep);
typedef void (*process_noirq_lock_fn_t)(unsigned long lock_addr);
typedef void (*process_noirq_unlock_fn_t)(unsigned long lock_addr);
typedef int (*process_pt_change_attr_fn_t)(void *page_table,
        unsigned long start,
        unsigned long end,
        unsigned long clrattr,
        unsigned long setattr);
typedef int (*process_pt_set_range_fn_t)(void *page_table,
       struct process_vm *vm,
       unsigned long start,
       unsigned long end,
       unsigned long phys,
       unsigned long attr,
       int pgshift,
       struct vm_range *range,
       int flags);
typedef void (*process_update_page_table_log_fn_t)(int error);
typedef void (*process_change_prot_public_log_fn_t)(int event,
          struct process_vm *vm,
          struct vm_range *range,
          unsigned long protflag,
          int error);
typedef void (*process_access_ok_log_fn_t)(struct process_vm *vm,
        int verify_type, unsigned long addr,
        size_t len, int error);
typedef int (*process_fault_range_fn_t)(struct process_vm *vm,
     struct vm_range *range,
     unsigned long fault_addr,
     unsigned long reason);
typedef int (*process_zeroobj_match_fn_t)(void *memobj);
typedef int (*process_page_fault_vm_fn_t)(struct process_vm *vm,
       unsigned long fault_addr,
       unsigned long reason);
typedef void (*process_preempt_fn_t)(void);
typedef void (*process_pgio_dispatch_fn_t)(void *fp, void *arg);
typedef void (*process_populate_warn_fn_t)(struct process_vm *vm,
        unsigned long addr,
        unsigned long reason,
        unsigned long off,
        size_t len, int error);
typedef int (*process_remove_range_split_fn_t)(struct process_vm *vm,
            struct vm_range *range,
            unsigned long addr,
            struct vm_range **splitp);
typedef void (*process_remove_range_xpmem_fn_t)(struct process_vm *vm,
      struct vm_range *range);
typedef void (*process_remove_range_log_fn_t)(int event,
           struct process_vm *vm,
           unsigned long start,
           unsigned long end,
           struct vm_range *range,
           int error);
typedef int (*process_remove_region_clear_fn_t)(void *page_table,
      struct process_vm *vm,
      unsigned long start,
      unsigned long end);
typedef void (*process_remove_region_log_fn_t)(struct process_vm *vm,
            unsigned long start,
            unsigned long end);
typedef void *(*process_init_stack_alloc_aligned_fn_t)(int npages,
             int p2align,
             unsigned long flags,
             unsigned long virt_addr);
typedef void (*process_init_stack_free_pages_fn_t)(void *addr, int npages);
typedef int (*process_init_stack_add_range_fn_t)(struct process_vm *vm,
       unsigned long start,
       unsigned long end,
       unsigned long phys,
       unsigned long flag,
       int pgshift,
       struct vm_range **rangep);
typedef unsigned long (*process_init_stack_virt_to_phys_fn_t)(void *addr);
typedef int (*process_init_stack_pt_set_range_fn_t)(void *page_table,
          struct process_vm *vm,
          unsigned long start,
          unsigned long end,
          unsigned long phys,
          unsigned long attr,
          int pgshift,
          struct vm_range *range,
          int flags);
typedef unsigned long (*process_init_stack_hwcap_fn_t)(void);
typedef void (*process_init_stack_modify_context_fn_t)(void *uctx, int reg,
             unsigned long value);
typedef void (*process_init_stack_log_fn_t)(int event,
         const unsigned long *args);
# 413 "/home/holden/mckernel/kernel/include/process_helpers.h"
int process_split_pgshift_result(int pgshift, uintptr_t addr);
int process_add_range_bounds_result(unsigned long user_start,
        unsigned long user_end,
        unsigned long start,
        unsigned long end);
int process_add_range_init_result(struct vm_range *range, unsigned long start,
      unsigned long end, unsigned long flag,
      void *memobj, off_t offset, int pgshift,
      void *private_data);
int process_add_range_mapping_result(unsigned long phys, unsigned long flag,
         unsigned long range_flag,
         unsigned long *attrp,
         int *memclearp);
struct vm_range *process_add_range_alloc_result(
 unsigned long range_size, process_add_range_alloc_fn_t alloc_fn);
int process_add_range_free_result(
 struct vm_range *range, process_add_range_free_fn_t free_fn);
int process_add_range_insert_result(
 struct process_vm *vm, struct vm_range *range,
 process_add_range_insert_fn_t insert_fn);
int process_add_range_update_result(
 struct process_vm *vm, struct vm_range *range, unsigned long phys,
 unsigned long attr, process_add_range_update_fn_t update_fn);
int process_add_range_remove_result(
 struct process_vm *vm, unsigned long start, unsigned long end,
 process_add_range_remove_fn_t remove_fn);
int process_add_range_mark_xpmem_result(
 struct vm_range *range,
 process_add_range_mark_xpmem_fn_t mark_xpmem_fn);
int process_add_range_memclear_result(
 unsigned long phys, unsigned long bytes,
 process_add_range_memclear_fn_t memclear_fn);
int process_add_range_log_result(
 int event, int rc, unsigned long start, unsigned long end,
 process_add_range_log_fn_t log_fn);
int process_add_range_orchestrate_result(
 struct process_vm *vm, unsigned long range_size, unsigned long start,
 unsigned long end, unsigned long phys, unsigned long flag,
 struct memobj *memobj, off_t offset, int pgshift, void *private_data,
 struct vm_range **rp, process_add_range_alloc_fn_t alloc_fn,
 process_add_range_free_fn_t free_fn,
 process_add_range_insert_fn_t insert_fn,
 process_add_range_update_fn_t update_fn,
 process_add_range_remove_fn_t remove_fn,
 process_add_range_mark_xpmem_fn_t mark_xpmem_fn,
 process_add_range_memclear_fn_t memclear_fn,
 process_add_range_log_fn_t log_fn);
int process_add_range_public_body_result(
 struct process_vm *vm, unsigned long range_size,
 unsigned long user_start, unsigned long user_end,
 unsigned long start, unsigned long end, unsigned long phys,
 unsigned long flag, struct memobj *memobj, off_t offset,
 int pgshift, void *private_data, struct vm_range **rp,
 process_add_range_alloc_fn_t alloc_fn,
 process_add_range_free_fn_t free_fn,
 process_add_range_insert_fn_t insert_fn,
 process_add_range_update_fn_t update_fn,
 process_add_range_remove_fn_t remove_fn,
 process_add_range_mark_xpmem_fn_t mark_xpmem_fn,
 process_add_range_memclear_fn_t memclear_fn,
 process_add_range_log_fn_t log_fn);
int process_vm_range_insert_log_result(
 int event, struct process_vm *vm, struct vm_range *newrange,
 struct vm_range *range, process_vm_range_insert_log_fn_t log_fn);
int process_vm_range_insert_dump_result(
 struct process_vm *vm, process_vm_range_insert_dump_fn_t dump_fn);
int process_vm_range_insert_result(struct rb_root *root,
       struct vm_range *newrange,
       struct process_vm *vm,
       process_vm_range_insert_log_fn_t log_fn,
       process_vm_range_insert_dump_fn_t dump_fn);
int process_extend_up_result(unsigned long current_end,
        unsigned long user_end, int has_next,
        unsigned long next_start,
        unsigned long newend);
unsigned long process_change_prot_newflag_result(unsigned long oldflag,
       unsigned long protflag);
void process_attr_delta_result(unsigned long oldattr, unsigned long newattr,
          unsigned long *clrattrp,
          unsigned long *setattrp);
unsigned long process_private_file_setattr_result(int has_memobj,
        unsigned long range_flags,
        unsigned int memobj_flags,
        unsigned long setattr);
int process_noirq_lock_result(unsigned long lock_addr,
         process_noirq_lock_fn_t lock_fn);
int process_noirq_unlock_result(unsigned long lock_addr,
    process_noirq_unlock_fn_t unlock_fn);
int process_pt_change_attr_result(void *page_table, unsigned long start,
      unsigned long end, unsigned long clrattr,
      unsigned long setattr,
      process_pt_change_attr_fn_t change_attr_fn);
int process_pt_set_range_result(void *page_table, struct process_vm *vm,
    unsigned long start, unsigned long end,
    unsigned long phys, unsigned long attr,
    int pgshift, struct vm_range *range, int flags,
    process_pt_set_range_fn_t pt_set_range_fn);
int process_update_page_table_log_result(
 int error, process_update_page_table_log_fn_t log_fn);
int process_zeroobj_match_result(void *memobj,
     process_zeroobj_match_fn_t zeroobj_match_fn);
int process_fault_range_result(struct process_vm *vm, struct vm_range *range,
          unsigned long fault_addr, unsigned long reason,
          process_fault_range_fn_t fault_fn);
int process_remove_region_alignment_result(unsigned long start,
        unsigned long end);
int process_access_initial_result(int has_range, unsigned long range_start,
      unsigned long addr);
int process_access_adjacent_result(unsigned long range_end, int has_next,
       unsigned long next_start);
int process_access_permission_result(int verify_type, unsigned long flags);
int process_range_cache_hit_result(unsigned long cache_start,
       unsigned long cache_end,
       unsigned long start,
       unsigned long end);
int process_lookup_range_relation_result(unsigned long start,
      unsigned long end,
      unsigned long range_start,
      unsigned long range_end);
int process_range_cache_replace_result(struct vm_range **cache, int count,
           struct vm_range *from,
           struct vm_range *to);
int process_range_cache_store_result(struct vm_range **cache, int count,
         int *indexp, struct vm_range *match);
struct vm_range *process_lookup_memory_range_body_result(
 struct process_vm *vm, unsigned long start, unsigned long end);
struct vm_range *process_next_memory_range_body_result(struct vm_range *range);
struct vm_range *process_previous_memory_range_body_result(
 struct vm_range *range);
int process_extend_up_body_result(struct process_vm *vm,
      struct vm_range *range,
      unsigned long newend);
int process_range_public_log_result(
 int event, struct process_vm *vm, struct vm_range *range,
 unsigned long start, unsigned long end, int error,
 process_range_public_log_fn_t log_fn);
struct vm_range *process_lookup_memory_range_public_result(
 struct process_vm *vm, unsigned long start, unsigned long end,
 process_range_public_log_fn_t log_fn);
struct vm_range *process_next_memory_range_public_result(
 struct process_vm *vm, struct vm_range *range,
 process_range_public_log_fn_t log_fn);
struct vm_range *process_previous_memory_range_public_result(
 struct process_vm *vm, struct vm_range *range,
 process_range_public_log_fn_t log_fn);
int process_extend_up_public_result(struct process_vm *vm,
        struct vm_range *range,
        unsigned long newend,
        process_range_public_log_fn_t log_fn);
int process_change_prot_body_result(struct process_vm *vm,
        struct vm_range *range,
        unsigned long protflag,
        process_attr_from_vrflag_fn_t attr_fn,
        process_noirq_lock_fn_t lock_fn,
        process_noirq_unlock_fn_t unlock_fn,
        process_pt_change_attr_fn_t change_attr_fn);
int process_change_prot_public_log_result(
 int event, struct process_vm *vm, struct vm_range *range,
 unsigned long protflag, int error,
 process_change_prot_public_log_fn_t log_fn);
int process_change_prot_public_result(
 struct process_vm *vm, struct vm_range *range, unsigned long protflag,
 process_attr_from_vrflag_fn_t attr_fn,
 process_noirq_lock_fn_t lock_fn,
 process_noirq_unlock_fn_t unlock_fn,
 process_pt_change_attr_fn_t change_attr_fn,
 process_change_prot_public_log_fn_t log_fn);
int process_update_page_table_body_result(
 struct process_vm *vm, struct vm_range *range, unsigned long phys,
 unsigned long populate_fault, process_attr_from_vrflag_fn_t attr_fn,
 process_spin_lock_fn_t lock_fn,
 process_spin_unlock_fn_t unlock_fn,
 process_pt_set_range_fn_t pt_set_range_fn,
 process_update_page_table_log_fn_t log_fn);
int process_update_page_table_public_result(
 struct process_vm *vm, struct vm_range *range, unsigned long phys,
 unsigned long flag, process_attr_from_vrflag_fn_t attr_fn,
 process_spin_lock_fn_t lock_fn,
 process_spin_unlock_fn_t unlock_fn,
 process_pt_set_range_fn_t pt_set_range_fn,
 process_update_page_table_log_fn_t log_fn);
int process_access_ok_body_result(struct process_vm *vm, int verify_type,
      unsigned long addr, size_t len);
int process_access_ok_log_result(
 struct process_vm *vm, int verify_type, unsigned long addr, size_t len,
 int error, process_access_ok_log_fn_t log_fn);
int process_access_ok_public_result(
 struct process_vm *vm, int verify_type, unsigned long addr, size_t len,
 process_access_ok_log_fn_t log_fn);
int process_do_page_fault_vm_body_result(
 struct process_vm *vm, struct process_vm *current_vm,
 unsigned long fault_addr, unsigned long reason, int current_cpu,
 process_noirq_lock_fn_t read_lock_fn,
 process_noirq_unlock_fn_t read_unlock_fn,
 process_noirq_lock_fn_t write_lock_fn,
 process_noirq_unlock_fn_t write_unlock_fn,
 process_zeroobj_match_fn_t zeroobj_match_fn,
 process_fault_range_fn_t normal_fault_fn,
 process_fault_range_fn_t xpmem_fault_fn);
int process_page_fault_vm_dispatch_result(
 struct process_vm *vm, unsigned long fault_addr, unsigned long reason,
 process_page_fault_vm_fn_t fault_fn);
int process_preempt_result(process_preempt_fn_t preempt_fn);
int process_pgio_dispatch_pending_result(
 void *thread, unsigned long pgio_fp_offset,
 unsigned long pgio_arg_offset,
 process_pgio_dispatch_fn_t pgio_dispatch_fn);
int process_populate_warn_result(struct process_vm *vm, unsigned long addr,
     unsigned long reason, unsigned long off,
     size_t len, int error,
     process_populate_warn_fn_t warn_fn);
int process_page_fault_vm_retry_body_result(
 struct process_vm *vm, unsigned long fault_addr, unsigned long reason,
 void *thread, unsigned long pgio_fp_offset,
 unsigned long pgio_arg_offset, process_page_fault_vm_fn_t do_fault_fn,
 process_preempt_fn_t preempt_enable_fn,
 process_preempt_fn_t preempt_disable_fn,
 process_pgio_dispatch_fn_t pgio_dispatch_fn);
int process_page_fault_vm_public_result(
 struct process_vm *vm, struct process_vm *current_vm,
 unsigned long fault_addr, unsigned long reason, int current_cpu,
 void *thread, unsigned long pgio_fp_offset,
 unsigned long pgio_arg_offset,
 process_noirq_lock_fn_t read_lock_fn,
 process_noirq_unlock_fn_t read_unlock_fn,
 process_noirq_lock_fn_t write_lock_fn,
 process_noirq_unlock_fn_t write_unlock_fn,
 process_zeroobj_match_fn_t zeroobj_match_fn,
 process_fault_range_fn_t normal_fault_fn,
 process_fault_range_fn_t xpmem_fault_fn,
 process_preempt_fn_t preempt_enable_fn,
 process_preempt_fn_t preempt_disable_fn,
 process_pgio_dispatch_fn_t pgio_dispatch_fn);
int process_populate_memory_body_result(
 struct process_vm *vm, unsigned long start, size_t len,
 unsigned long page_size, unsigned long reason,
 process_page_fault_vm_fn_t page_fault_fn,
 process_preempt_fn_t preempt_disable_fn,
 process_preempt_fn_t preempt_enable_fn,
 process_populate_warn_fn_t warn_fn);
int process_populate_memory_public_result(
 struct process_vm *vm, struct process_vm *current_vm,
 unsigned long start, size_t len, unsigned long page_size,
 unsigned long reason, int current_cpu, void *thread,
 unsigned long pgio_fp_offset, unsigned long pgio_arg_offset,
 process_noirq_lock_fn_t read_lock_fn,
 process_noirq_unlock_fn_t read_unlock_fn,
 process_noirq_lock_fn_t write_lock_fn,
 process_noirq_unlock_fn_t write_unlock_fn,
 process_zeroobj_match_fn_t zeroobj_match_fn,
 process_fault_range_fn_t normal_fault_fn,
 process_fault_range_fn_t xpmem_fault_fn,
 process_preempt_fn_t preempt_disable_fn,
 process_preempt_fn_t preempt_enable_fn,
 process_pgio_dispatch_fn_t pgio_dispatch_fn,
 process_populate_warn_fn_t warn_fn);
int process_range_end_commit_result(struct vm_range *range, uintptr_t newend);
int process_range_flag_commit_result(struct vm_range *range,
         unsigned long newflag);
int process_range_stack_start_commit_result(struct vm_range *range,
         uintptr_t fault_addr,
         int pgshift);
void process_remove_range_step_result(unsigned long range_start,
          unsigned long range_end,
          unsigned long remove_start,
          unsigned long remove_end,
          unsigned long range_flags,
          unsigned long private_data,
          int *split_startp, int *split_endp,
          int *ro_freedp, int *xpmem_removep);
int process_split_range_init_result(const struct vm_range *low,
        struct vm_range *high, uintptr_t addr);
void process_split_range_commit_result(struct vm_range *low, uintptr_t addr);
int process_memobj_ref_direct_result(struct memobj *memobj);
int process_memobj_unref_direct_result(struct memobj *memobj);
int process_range_memobj_ref_result(struct memobj *memobj,
        process_range_memobj_ref_fn_t memobj_ref_fn);
int process_range_optional_memobj_ref_result(
 struct memobj *memobj,
 process_range_memobj_ref_fn_t memobj_ref_fn);
int process_range_memobj_ref_or_direct_result(
 struct memobj *memobj,
 process_range_memobj_ref_fn_t memobj_ref_fn);
int process_range_memobj_unref_or_direct_result(
 struct memobj *memobj,
 process_range_memobj_ref_fn_t memobj_unref_fn);
int process_range_optional_memobj_ref_or_direct_result(
 struct memobj *memobj,
 process_range_memobj_ref_fn_t memobj_ref_fn);
int process_range_optional_memobj_unref_or_direct_result(
 struct memobj *memobj,
 process_range_memobj_ref_fn_t memobj_unref_fn);
int process_split_range_insert_result(
 struct process_vm *vm, struct vm_range *range,
 process_split_range_insert_fn_t insert_fn);
int process_split_range_publish_result(
 struct process_vm *vm, struct vm_range *low, struct vm_range *high,
 uintptr_t addr, struct vm_range **splitp,
 process_range_memobj_ref_fn_t memobj_ref_fn,
 process_split_range_insert_fn_t insert_fn);
struct vm_range *process_split_range_alloc_init_body_result(
 struct process_vm *vm, struct vm_range *range, unsigned long addr,
 void *splitp, unsigned long range_size, unsigned long alloc_flags,
 int *errorp, process_split_range_alloc_fn_t alloc_fn,
 process_split_range_alloc_log_fn_t log_fn);
int process_split_range_publish_body_result(
 struct process_vm *vm, struct vm_range *low, struct vm_range *high,
 uintptr_t addr, struct vm_range **splitp,
 process_range_memobj_ref_fn_t memobj_ref_fn,
 process_split_range_insert_fn_t insert_fn,
 process_split_range_publish_log_fn_t log_fn);
int process_split_range_pt_body_result(
 struct process_vm *vm, struct vm_range *range, unsigned long addr,
 process_split_range_pt_split_fn_t split_fn,
 process_split_range_pt_log_fn_t log_fn);
int process_split_shm_update_body_result(
 struct process_vm *vm, struct vm_range *range, unsigned long addr,
 unsigned long page_pgshift_offset,
 process_split_shm_lookup_page_fn_t lookup_page_fn,
 process_split_shm_phys_to_page_fn_t phys_to_page_fn,
 process_split_shm_update_page_fn_t update_page_fn,
 process_split_shm_log_fn_t log_fn);
int process_join_range_prepare_result(struct vm_range *surviving,
          const struct vm_range *merging);
int process_join_range_free_result(struct vm_range *range,
       process_join_range_free_fn_t free_fn);
int process_join_range_tofu_result(struct process_vm *vm,
       struct vm_range *surviving,
       struct vm_range *merging,
       process_join_range_tofu_fn_t tofu_fn);
int process_join_range_body_result(
 struct process_vm *vm, struct rb_root *root, struct vm_range **cache,
 int cache_count, struct vm_range *surviving, struct vm_range *merging,
 process_range_memobj_ref_fn_t memobj_unref_fn,
 process_join_range_free_fn_t free_fn,
 process_join_range_tofu_fn_t tofu_fn);
int process_free_range_page_size_result(
 size_t current, size_t *nextp,
 process_free_range_page_size_fn_t page_size_fn);
int process_free_range_pt_plan_result(
 const struct vm_range *range, unsigned long straight_va, int has_prev,
 unsigned long prev_end, int has_next, unsigned long next_start,
 int has_memobj, unsigned int memobj_flags, unsigned long *startp,
 unsigned long *endp, int *actionp,
 process_free_range_page_size_fn_t page_size_fn);
int process_free_range_finalize_result(
 struct process_vm *vm, struct rb_root *root, struct vm_range **cache,
 int cache_count, struct vm_range *range, unsigned long straight_va,
 size_t *straight_lenp, unsigned long straight_pa,
 process_free_range_phys_to_virt_fn_t phys_to_virt_fn,
 process_free_range_pages_fn_t free_pages_fn,
 process_free_range_clear_main_fn_t clear_main_fn,
 process_free_range_free_fn_t free_fn);
void *process_free_range_phys_to_virt_result(
 unsigned long phys, process_free_range_phys_to_virt_fn_t phys_to_virt_fn);
int process_free_range_free_pages_result(
 void *addr, unsigned long pages,
 process_free_range_pages_fn_t free_pages_fn);
int process_free_range_clear_main_result(
 struct process_vm *vm, unsigned long start, unsigned long end,
 process_free_range_clear_main_fn_t clear_main_fn);
int process_free_range_free_result(struct vm_range *range,
       process_free_range_free_fn_t free_fn);
int process_free_range_pt_free_result(
 void *page_table, struct process_vm *vm, unsigned long start,
 unsigned long end, void *memobj,
 process_free_range_pt_free_fn_t pt_free_fn);
int process_free_range_pt_clear_result(
 void *page_table, struct process_vm *vm, unsigned long start,
 unsigned long end, process_free_range_pt_clear_fn_t pt_clear_fn);
int process_free_range_tofu_remove_result(
 struct process_vm *vm, struct vm_range *range,
 process_free_range_tofu_remove_fn_t tofu_remove_fn);
int process_free_range_log_result(
 int event, struct process_vm *vm, struct vm_range *range,
 unsigned long start, unsigned long end, int error,
 process_free_range_log_fn_t log_fn);
int process_free_memory_range_body_result(
 struct process_vm *vm, struct vm_range *range,
 unsigned long straight_va, size_t *straight_lenp,
 unsigned long straight_pa, int tofu_enabled,
 process_free_range_page_size_fn_t page_size_fn,
 process_noirq_lock_fn_t lock_fn,
 process_noirq_unlock_fn_t unlock_fn,
 process_range_memobj_ref_fn_t memobj_ref_fn,
 process_range_memobj_ref_fn_t memobj_unref_fn,
 process_free_range_pt_free_fn_t pt_free_fn,
 process_free_range_pt_clear_fn_t pt_clear_fn,
 process_free_range_tofu_remove_fn_t tofu_remove_fn,
 process_free_range_phys_to_virt_fn_t phys_to_virt_fn,
 process_free_range_pages_fn_t free_pages_fn,
 process_free_range_clear_main_fn_t clear_main_fn,
 process_free_range_free_fn_t free_fn,
 process_free_range_log_fn_t log_fn);
int process_sync_memory_range_body_result(
 struct process_vm *vm, struct vm_range *range,
 unsigned long start, unsigned long end, void *arg,
 void *visit_step_fn, process_noirq_lock_fn_t lock_fn,
 process_noirq_unlock_fn_t unlock_fn,
 process_visit_pte_range_fn_t visit_fn,
 process_sync_range_log_fn_t log_fn);
int process_remap_memory_range_body_result(
 struct process_vm *vm, struct vm_range *range,
 unsigned long start, unsigned long end, long off, void *arg,
 void *visit_step_fn, process_noirq_lock_fn_t lock_fn,
 process_noirq_unlock_fn_t unlock_fn,
 process_visit_pte_range_fn_t visit_fn,
 process_remap_range_log_fn_t log_fn);
int process_invalidate_memory_range_body_result(
 struct process_vm *vm, struct vm_range *range,
 unsigned long start, unsigned long end, void *arg,
 void *visit_step_fn, process_noirq_lock_fn_t lock_fn,
 process_noirq_unlock_fn_t unlock_fn,
 process_lookup_pte_fn_t lookup_pte_fn,
 process_pte_test_fn_t pte_contiguous_fn,
 process_pte_pgsize_test_fn_t pte_head_fn,
 process_pte_pgsize_test_fn_t pte_tail_fn,
 process_split_contiguous_pages_fn_t split_fn,
 process_free_range_pt_free_fn_t pt_free_fn,
 process_visit_pte_range_fn_t visit_fn,
 process_sync_range_log_fn_t log_fn);
int process_invalidate_one_page_body_result(
 void *arg, void *page_table, void *ptep, void *pgaddr, int pgshift,
 process_pte_test_fn_t pte_null_fn,
 process_pte_pgsize_test_fn_t pte_fileoff_fn,
 process_pte_get_phys_fn_t pte_get_phys_fn,
 process_phys_to_page_fn_t phys_to_page_fn,
 process_page_offset_fn_t page_offset_fn,
 process_pte_make_fileoff_fn_t pte_make_fileoff_fn,
 process_pte_xchg_fn_t pte_xchg_fn,
 process_flush_tlb_single_fn_t flush_tlb_single_fn,
 process_pte_test_fn_t pte_contiguous_fn,
 process_pte_pgsize_test_fn_t pte_head_fn,
 process_pgsize_to_tbllv_fn_t pgsize_to_tbllv_fn,
 process_tbllv_to_contpgsize_fn_t tbllv_to_contpgsize_fn,
 process_page_unmap_fn_t page_unmap_fn,
 process_panic_fn_t panic_fn,
 process_memobj_invalidate_page_fn_t memobj_invalidate_page_fn,
 process_invalidate_one_page_log_fn_t log_fn);
int process_remove_straight_convert_result(
 unsigned long straight_va, size_t straight_len,
 const struct vm_range *range, unsigned long start, unsigned long end,
 unsigned long *new_startp, unsigned long *new_endp,
 unsigned long *lenp);
int process_remove_range_split_result(
 struct process_vm *vm, struct vm_range *range, unsigned long addr,
 struct vm_range **splitp, process_remove_range_split_fn_t split_fn);
int process_remove_range_xpmem_result(
 struct process_vm *vm, struct vm_range *range,
 process_remove_range_xpmem_fn_t xpmem_remove_fn);
int process_remove_range_free_result(
 struct process_vm *vm, struct vm_range *range,
 process_memory_range_free_fn_t free_fn);
int process_remove_range_log_result(
 int event, struct process_vm *vm, unsigned long start,
 unsigned long end, struct vm_range *range, int error,
 process_remove_range_log_fn_t log_fn);
int process_remove_memory_range_body_result(
 struct process_vm *vm, unsigned long start, unsigned long end,
 int *ro_freedp, unsigned long straight_va, size_t straight_len,
 process_remove_range_split_fn_t split_fn,
 process_remove_range_xpmem_fn_t xpmem_remove_fn,
 process_memory_range_free_fn_t free_fn,
 process_remove_range_log_fn_t log_fn);
int process_remove_region_body_result(
 struct process_vm *vm, unsigned long start, unsigned long end,
 process_noirq_lock_fn_t lock_fn, process_noirq_unlock_fn_t unlock_fn,
 process_remove_region_clear_fn_t clear_fn,
 process_remove_region_log_fn_t log_fn);
int process_remove_region_clear_result(
 void *page_table, struct process_vm *vm, unsigned long start,
 unsigned long end, process_remove_region_clear_fn_t clear_fn);
int process_remove_region_log_result(
 struct process_vm *vm, unsigned long start, unsigned long end,
 process_remove_region_log_fn_t log_fn);
void *process_init_stack_alloc_aligned_result(
 int npages, int p2align, unsigned long flags, unsigned long virt_addr,
 process_init_stack_alloc_aligned_fn_t alloc_aligned_fn);
int process_init_stack_free_pages_result(
 void *addr, int npages, process_init_stack_free_pages_fn_t free_pages_fn);
int process_init_stack_add_range_result(
 struct process_vm *vm, unsigned long start, unsigned long end,
 unsigned long phys, unsigned long flag, int pgshift,
 struct vm_range **rangep,
 process_init_stack_add_range_fn_t add_range_fn);
unsigned long process_init_stack_virt_to_phys_result(
 void *addr, process_init_stack_virt_to_phys_fn_t virt_to_phys_fn);
unsigned long process_attr_from_vrflag_result(
 unsigned long flag, unsigned long fault, void *ptep,
 process_attr_from_vrflag_fn_t attr_fn);
int process_init_stack_pt_set_range_result(
 void *page_table, struct process_vm *vm, unsigned long start,
 unsigned long end, unsigned long phys, unsigned long attr, int pgshift,
 struct vm_range *range, int flags,
 process_init_stack_pt_set_range_fn_t pt_set_range_fn);
unsigned long process_init_stack_hwcap_result(
 process_init_stack_hwcap_fn_t hwcap_fn);
int process_init_stack_modify_context_result(
 void *uctx, int reg, unsigned long value,
 process_init_stack_modify_context_fn_t modify_context_fn);
int process_init_stack_log_result(int event, const unsigned long *args,
      process_init_stack_log_fn_t log_fn);
int process_init_stack_body_result(
 struct thread *thread, struct program_load_desc *pn,
 unsigned long at_base, int argc, char **argv, int envc, char **env,
 unsigned long page_size, int page_shift,
 unsigned long user_stack_page_mask, int user_stack_page_shift,
 unsigned long user_stack_prepage_size,
 unsigned long stack_alloc_size_override, int user_stack_page_p2align,
 unsigned long alloc_nowait, unsigned long alloc_user,
 unsigned long mpol_no_stack, int user_context_sp_reg,
 unsigned long pf_populate,
 process_init_stack_alloc_aligned_fn_t alloc_aligned_fn,
 process_init_stack_free_pages_fn_t free_pages_fn,
 process_init_stack_add_range_fn_t add_range_fn,
 process_init_stack_virt_to_phys_fn_t virt_to_phys_fn,
 process_attr_from_vrflag_fn_t attr_fn,
 process_init_stack_pt_set_range_fn_t pt_set_range_fn,
 process_init_stack_hwcap_fn_t hwcap_fn,
 process_init_stack_modify_context_fn_t modify_context_fn,
 process_init_stack_log_fn_t log_fn);
int process_ref_release_should_destroy_result(int dec_and_test);
int process_release_address_space_should_destroy_result(int dec_and_test);
int process_release_address_space_should_run_free_cb_result(
 unsigned long free_cb_addr);
int process_ref_dec_and_test_result(
 void *object, unsigned long ref_offset,
 process_ref_dec_and_test_fn_t dec_fn);
int process_ref_set_result(void *object, unsigned long ref_offset, int value,
      process_ref_set_fn_t ref_set_fn);
int process_ref_inc_direct_result(void *object, unsigned long ref_offset);
int process_ref_dec_and_test_direct_result(void *object,
        unsigned long ref_offset);
int process_ref_set_direct_result(void *object, unsigned long ref_offset,
      int value);
void *process_alloc_result(unsigned long size, unsigned long flags,
      process_alloc_fn_t alloc_fn);
int process_free_callback_result(void *ptr, process_free_fn_t free_fn);
void *process_pt_create_result(unsigned long flags,
          process_pt_create_fn_t pt_create_fn);
int process_pt_destroy_result(void *page_table,
         process_pt_destroy_fn_t pt_destroy_fn);
int process_spin_init_result(unsigned long lock_addr,
        process_spin_init_fn_t spin_init_fn);
int process_address_space_free_cb_result(
 void *asp, void *opt, process_address_space_free_cb_fn_t free_cb);
int process_address_space_action_result(
 void *asp, process_address_space_action_fn_t action_fn);
int process_release_address_space_body_result(
 void *asp, unsigned long refcount_offset, unsigned long free_cb_offset,
 unsigned long opt_offset, unsigned long page_table_offset,
 process_ref_dec_and_test_fn_t dec_fn,
 process_pt_destroy_fn_t pt_destroy_fn, process_free_fn_t free_fn);
int process_hold_address_space_public_result(
 void *asp, unsigned long refcount_offset, process_ref_inc_fn_t inc_fn);
int process_release_address_space_public_result(
 void *asp, unsigned long refcount_offset, unsigned long free_cb_offset,
 unsigned long opt_offset, unsigned long page_table_offset,
 process_ref_dec_and_test_fn_t dec_fn,
 process_pt_destroy_fn_t pt_destroy_fn, process_free_fn_t free_fn);
int process_detach_address_space_body_result(
 void *asp, int pid, unsigned long pids_offset,
 unsigned long nslots_offset, process_address_space_action_fn_t release_fn);
int process_detach_address_space_public_result(
 void *asp, int pid, unsigned long pids_offset,
 unsigned long nslots_offset, process_address_space_action_fn_t release_fn);
void *process_create_address_space_body_result(
 int nslots, unsigned long address_space_size,
 unsigned long pid_slot_size, unsigned long nowait_flag,
 unsigned long page_table_offset, unsigned long refcount_offset,
 unsigned long cpu_set_offset, unsigned long cpu_set_size,
 unsigned long cpu_set_lock_offset, unsigned long nslots_offset,
 process_alloc_fn_t alloc_fn, process_free_fn_t free_fn,
 process_pt_create_fn_t pt_create_fn, process_ref_set_fn_t ref_set_fn,
 process_spin_init_fn_t spin_init_fn);
int process_create_cpu_allowed_result(int cpu, int num_processors);
int process_create_use_default_cpu_set_result(int cpu_set_empty);
int process_create_cpu_sets_body_result(
 unsigned long requested_cpu_set_addr, unsigned long requested_bits,
 unsigned long thread_cpu_set_addr, unsigned long proc_cpu_set_addr,
 int output_cpu_set_bits, int num_processors, int pid,
 process_default_ncpus_fn_t default_ncpus_fn,
 process_create_cpu_log_fn_t log_fn);
int process_allocated_object_zero_body_result(void *object,
           unsigned long object_size);
int process_vm_init_body_result(
 struct process_vm *vm, struct process *owner, void *asp,
 int nr_numa_nodes, process_rwlock_init_fn_t memory_lock_init_fn,
 process_spin_init_fn_t spin_init_fn,
 process_vm_init_numa_log_fn_t numa_log_fn);
void *process_new_resource_set_body_result(
 unsigned long resource_set_size, unsigned long process_hash_size,
 unsigned long thread_hash_size, unsigned long process_size,
 unsigned long nowait_flag, int hash_size, int init_pid,
 process_alloc_fn_t alloc_fn, process_free_fn_t free_fn,
 process_init_process_fn_t init_process_fn,
 process_rwlock_init_fn_t rwlock_init_fn);
int process_memset_smp_handler_body_result(
 int cpu_index, int nr_cpus, unsigned long phys, size_t len, int value,
 process_phys_to_virt_fn_t phys_to_virt_fn,
 process_memset_fn_t memset_fn,
 process_memset_smp_log_fn_t log_fn);
int process_memset_smp_body_result(
 void *cpu_set, void *addr, int value, size_t len,
 unsigned long *phys_slot, size_t *len_slot, int *value_slot,
 void *handler, void *request,
 process_virt_to_phys_fn_t virt_to_phys_fn,
 process_smp_call_fn_t smp_call_fn);
int process_proc_init_body_result(
 void *resource_set, struct list_head *resource_set_list,
 unsigned long resource_set_lock_addr, int num_processors,
 int cpu_set_bits, unsigned long path_size, unsigned long nowait_flag,
 process_alloc_fn_t alloc_fn, process_rwlock_init_fn_t rwlock_init_fn);
int process_sched_init_body_result(
 unsigned long cpu_local_addr, struct list_head *resource_set_list,
 int current_cpu, process_init_process_fn_t init_process_fn,
 process_rwlock_init_fn_t memory_lock_init_fn,
 process_spin_init_fn_t spin_init_fn,
 process_sched_init_context_fn_t init_context_fn,
 process_sched_save_fp_fn_t save_fp_fn,
 process_sched_timer_init_fn_t timer_init_fn);
int process_init_state_body_result(
 void *process, const void *parent,
 const struct process_init_state_offsets *offsets,
 int initial_pid, int running_status);
int process_init_links_body_result(
 void *process, unsigned long hash_list_offset,
 unsigned long siblings_list_offset,
 unsigned long ptraced_siblings_list_offset,
 unsigned long update_lock_offset,
 unsigned long report_threads_list_offset,
 unsigned long threads_list_offset,
 unsigned long children_list_offset,
 unsigned long ptraced_children_list_offset,
 unsigned long threads_lock_offset,
 unsigned long children_lock_offset,
 unsigned long coredump_lock_offset,
 unsigned long mckfd_lock_offset,
 unsigned long waitpid_q_offset,
 unsigned long refcount_offset,
 unsigned long monitoring_event_offset,
 process_rwlock_init_fn_t rwlock_init_fn,
 process_spin_init_fn_t spin_init_fn,
 process_waitq_init_fn_t waitq_init_fn,
 process_ref_set_fn_t ref_set_fn);
int process_init_profile_body_result(
 void *process, unsigned long profile_lock_offset,
 unsigned long profile_events_offset,
 process_mcs_lock_init_fn_t lock_init_fn);
int process_clone_thread_base_state_body_result(
 void *thread, const void *origin, unsigned long cpu_set_offset,
 unsigned long cpu_set_size, unsigned long in_kernel_offset);
int process_clone_thread_sched_state_body_result(
 void *thread, const void *origin, unsigned long sched_policy_offset,
 unsigned long sched_priority_offset);
int process_thread_sched_default_body_result(
 void *thread, unsigned long sched_policy_offset, int default_policy);
int process_create_thread_link_state_body_result(
 void *thread, void *process, void *vm, unsigned long thread_vm_offset,
 unsigned long thread_proc_offset, unsigned long process_vm_offset,
 unsigned long process_main_thread_offset);
int process_thread_exit_status_init_body_result(
 void *thread, unsigned long exit_status_offset, int exit_status);
int process_thread_spin_sleep_init_body_result(
 void *thread, unsigned long spin_sleep_lock_offset,
 unsigned long spin_sleep_offset, process_spin_init_fn_t spin_init_fn);
int process_thread_sigmask_copy_body_result(
 void *thread, const void *origin, unsigned long sigmask_offset,
 unsigned long sigmask_size);
int process_clone_profile_state_body_result(
 void *thread, const void *origin, const void *process,
 unsigned long thread_profile_offset, unsigned long process_profile_offset);
int process_clone_fork_process_termsig_body_result(
 void *process, unsigned long termsig_offset, int termsig);
int process_clone_fork_saved_cmdline_body_result(
 void *process, const void *origin_process,
 unsigned long saved_cmdline_len_offset,
 unsigned long saved_cmdline_offset, unsigned long nowait_flag,
 process_alloc_fn_t alloc_fn);
int process_clone_fork_vm_policy_body_result(
 void *dst_vm, const void *src_vm, unsigned long numa_mask_offset,
 unsigned long numa_mask_size, unsigned long numa_mem_policy_offset,
 unsigned long region_offset, unsigned long region_size);
int process_clone_thread_shared_vm_state_body_result(
 void *thread, void *process, void *vm, unsigned long thread_vm_offset,
 unsigned long thread_proc_offset);
int process_clone_sigcommon_share_body_result(
 void *thread, const void *origin, unsigned long sigcommon_offset,
 unsigned long sigcommon_use_offset, process_ref_inc_fn_t ref_inc_fn);
int process_clone_sigcommon_action_copy_body_result(
 void *dst_sigcommon, const void *src_sigcommon,
 unsigned long action_offset, unsigned long action_size);
int process_clone_user_context_body_result(
 void *thread, const void *origin, unsigned long uctx_offset,
 unsigned long uctx_size, int stack_pointer_reg, unsigned long sp,
 int program_counter_reg, unsigned long pc,
 process_init_stack_modify_context_fn_t modify_context_fn);
int process_clone_fork_profile_body_result(
 void *process, const void *origin_process, unsigned long profile_offset);
int process_clone_on_fork_vm_body_result(
 void *cpu_local, unsigned long on_fork_vm_offset, void *vm);
int process_mckfd_copy_body_result(void *dst, const void *src,
       unsigned long mckfd_size);
int process_copy_user_range_metadata_body_result(
 struct vm_range *dst, const struct vm_range *src,
 process_range_memobj_ref_fn_t memobj_ref_fn);
int process_copy_user_pte_args_init_body_result(
 void *args, unsigned long new_vm_offset,
 unsigned long new_vrflag_offset, unsigned long range_offset,
 unsigned long fault_addr_offset, void *vm, unsigned long vrflag,
 void *range, long fault_addr);
int process_copy_user_pte_buffer_body_result(void *dst, const void *src,
          size_t len, int wipe);
int process_copy_user_ranges_body_result(
 struct process_vm *vm, struct process_vm *orgvm,
 unsigned long range_size, unsigned long alloc_flags, void *copy_args,
 unsigned long new_vm_offset, unsigned long new_vrflag_offset,
 unsigned long range_offset, unsigned long fault_addr_offset,
 void *copy_pte_fn, int visit_flags,
 process_noirq_lock_fn_t read_lock_fn,
 process_noirq_unlock_fn_t read_unlock_fn,
 process_copy_range_lookup_fn_t lookup_fn,
 process_copy_range_next_fn_t next_fn,
 process_add_range_alloc_fn_t alloc_fn,
 process_add_range_free_fn_t free_fn,
 process_add_range_insert_fn_t insert_fn,
 process_visit_pte_range_fn_t visit_fn,
 process_memory_range_free_fn_t free_range_fn,
 process_copy_user_ranges_log_fn_t log_fn);
void *process_sigcommon_alloc_init_body_result(
 unsigned long sigcommon_size, unsigned long flags,
 unsigned long use_offset, unsigned long lock_offset,
 unsigned long sigpending_offset, process_alloc_fn_t alloc_fn,
 process_free_fn_t free_fn, process_ref_set_fn_t ref_set_fn,
 process_rwlock_init_fn_t rwlock_init_fn);
int process_thread_sigpending_init_body_result(
 void *thread, unsigned long lock_offset, unsigned long sigpending_offset,
 process_rwlock_init_fn_t rwlock_init_fn);
int process_thread_alloc_init_body_result(
 void *thread, unsigned long thread_size, unsigned long refcount_offset,
 unsigned long hash_list_offset, unsigned long siblings_list_offset,
 process_ref_set_fn_t ref_set_fn);
int process_thread_sigstack_disable_body_result(
 void *thread, unsigned long sigstack_offset, unsigned long sp_offset,
 unsigned long flags_offset, unsigned long size_offset, int disable_flag);
void *process_create_thread_body_result(
 unsigned long user_pc, unsigned long requested_cpu_set_addr,
 unsigned long requested_bits, unsigned long thread_pages,
 unsigned long thread_size, unsigned long process_size,
 unsigned long vm_size, unsigned long nowait_flag,
 unsigned long kernel_stack_bytes, int cpu_set_bits, int num_processors,
 int sched_normal, int ss_disable, int current_cpu,
 void *parent_process, unsigned long process_pid_offset,
 unsigned long thread_refcount_offset,
 unsigned long thread_hash_list_offset,
 unsigned long thread_siblings_list_offset,
 unsigned long thread_cpu_set_offset,
 unsigned long thread_sched_policy_offset,
 unsigned long thread_sigcommon_offset,
 unsigned long thread_sigpendinglock_offset,
 unsigned long thread_sigpending_offset,
 unsigned long thread_sigstack_offset,
 unsigned long sigstack_sp_offset,
 unsigned long sigstack_flags_offset,
 unsigned long sigstack_size_offset,
 unsigned long thread_vm_offset, unsigned long thread_proc_offset,
 unsigned long process_cpu_set_offset,
 unsigned long process_vm_offset,
 unsigned long process_main_thread_offset,
 unsigned long vm_address_space_offset,
 unsigned long address_space_cpu_set_offset,
 unsigned long address_space_cpu_set_lock_offset,
 unsigned long thread_exit_status_offset,
 unsigned long thread_spin_sleep_lock_offset,
 unsigned long thread_spin_sleep_offset,
 unsigned long sigcommon_size,
 unsigned long sigcommon_use_offset,
 unsigned long sigcommon_lock_offset,
 unsigned long sigcommon_sigpending_offset,
 process_alloc_pages_fn_t alloc_pages_fn,
 process_alloc_fn_t alloc_fn,
 process_free_fn_t free_fn,
 process_create_address_space_fn_t create_address_space_fn,
 process_release_address_space_fn_t release_address_space_fn,
 process_init_process_fn_t init_process_fn,
 process_init_process_vm_fn_t init_process_vm_fn,
 process_init_user_process_fn_t init_user_process_fn,
 process_default_ncpus_fn_t default_ncpus_fn,
 process_create_cpu_log_fn_t cpu_log_fn,
 process_rwlock_init_fn_t rwlock_init_fn,
 process_spin_init_fn_t spin_init_fn,
 process_spin_lock_fn_t spin_lock_fn,
 process_spin_unlock_fn_t spin_unlock_fn,
 process_thread_action_fn_t free_thread_fn);
int process_address_space_pid_detach_result(int *pids, int nslots, int pid);
int process_clone_shares_vm_result(int clone_flags);
int process_clone_shares_sighand_result(int clone_flags);
int process_mckfd_should_dup_result(unsigned long dup_cb_addr);
int process_mckfd_dup_result(struct mckfd *fdp,
        process_mckfd_dup_fn_t dup_fn);
int process_clone_copy_vm_thread_state_result(
 void *dst_vm, const void *src_vm, unsigned long vdso_offset,
 unsigned long vvar_offset, void *dst_thread, const void *src_thread,
 unsigned long sigstack_offset, size_t sigstack_size);
int process_tid_index_for_thread_result(const void *tids, int nr_tids,
     unsigned long entry_stride,
     unsigned long thread_offset,
     unsigned long thread_addr);
int process_tid_index_found_result(int index);
int process_tid_release_slot_result(void *tids, int index,
        unsigned long entry_stride,
        unsigned long thread_offset);
int process_tid_replace_slot_result(void *tids, int index,
        unsigned long entry_stride,
        unsigned long tid_offset,
        unsigned long thread_offset,
        int new_tid);
int process_sigpending_cleanup_needed_result(int list_empty);
void *process_sigpending_pop_front_result(struct list_head *head,
       unsigned long list_offset);
int process_sigpending_drain_free_result(struct list_head *head,
      unsigned long list_offset,
      process_free_fn_t free_fn);
int process_list_is_linked_result(const struct list_head *entry);
void process_list_detach_result(struct list_head *entry);
int process_list_detach_counted_result(struct list_head *entry,
           size_t *lenp);
void process_list_add_tail_result(struct list_head *entry,
      struct list_head *head);
int process_list_add_tail_counted_result(struct list_head *entry,
      struct list_head *head,
      size_t *lenp);
int process_list_move_tail_result(struct list_head *entry,
      struct list_head *head);
int process_list_del_init_result(struct list_head *entry);
int process_child_reparent_result(void *child,
      unsigned long ppid_parent_offset,
      unsigned long parent_offset,
      void *new_parent,
      struct list_head *entry,
      struct list_head *head,
      int update_parent);
int process_thread_report_attach_result(void *thread,
     unsigned long termsig_offset,
     int update_termsig, int termsig,
     unsigned long report_proc_offset,
     void *report_proc,
     struct list_head *entry,
     struct list_head *head);
int process_thread_report_detach_result(void *thread,
     unsigned long report_proc_offset,
     void *report_proc,
     struct list_head *entry);
int process_ptrace_main_detach_reparent_result(void *process,
           unsigned long parent_offset,
           void *parent,
           struct list_head *ptraced_entry,
           struct list_head *sibling_entry,
           struct list_head *children_head);
int process_ptrace_main_attach_reparent_result(void *process,
           unsigned long parent_offset,
           void *parent,
           struct list_head *sibling_entry,
           struct list_head *children_head);
int process_thread_termsig_clear_result(void *thread,
     unsigned long termsig_offset,
     int clear_termsig);
void *process_thread_ptrace_cleanup_result(void *thread,
        unsigned long ptrace_offset,
        unsigned long saved_valid_offset,
        unsigned long debugreg_offset);
int process_thread_ptrace_saved_context_clear_result(
 void *thread, unsigned long saved_valid_offset);
int process_thread_ptrace_trace_syscall_update_result(
 void *thread, unsigned long ptrace_offset, int trace_syscall);
void *process_thread_ptrace_pending_signal_take_result(
 void *thread, unsigned long sendsig_offset, unsigned long recvsig_offset,
 int source);
struct process_ptrace_traceme_offsets {
 unsigned long thread_proc_offset;
 unsigned long thread_report_proc_offset;
 unsigned long thread_report_siblings_list_offset;
 unsigned long thread_ptrace_offset;
 unsigned long thread_ptrace_debugreg_offset;
 unsigned long proc_pid_offset;
 unsigned long proc_parent_offset;
 unsigned long proc_main_thread_offset;
 unsigned long proc_children_lock_offset;
 unsigned long proc_threads_lock_offset;
 unsigned long proc_ptraced_siblings_list_offset;
 unsigned long proc_ptraced_children_list_offset;
 unsigned long proc_report_threads_list_offset;
};
struct process_ptrace_attach_offsets {
 unsigned long thread_proc_offset;
 unsigned long thread_report_proc_offset;
 unsigned long thread_report_siblings_list_offset;
 unsigned long thread_ptrace_debugreg_offset;
 unsigned long proc_pid_offset;
 unsigned long proc_parent_offset;
 unsigned long proc_main_thread_offset;
 unsigned long proc_children_lock_offset;
 unsigned long proc_threads_lock_offset;
 unsigned long proc_children_list_offset;
 unsigned long proc_siblings_list_offset;
 unsigned long proc_ptraced_siblings_list_offset;
 unsigned long proc_ptraced_children_list_offset;
 unsigned long proc_report_threads_list_offset;
};

struct process_find_thread_offsets {
 unsigned long thread_hash_list_offset;
 unsigned long thread_tid_offset;
 unsigned long thread_proc_offset;
 unsigned long proc_pid_offset;
};

struct process_find_process_offsets {
 unsigned long process_hash_list_offset;
 unsigned long process_pid_offset;
};
int process_ptrace_traceme_body_result(
 void *thread, void *proc, void *parent, void *pid1,
 const struct process_ptrace_traceme_offsets *offsets, void *lock_node,
 process_mcs_rwlock_fn_t lock_fn, process_mcs_rwlock_fn_t unlock_fn,
 process_alloc_debugreg_fn_t alloc_debugreg_fn,
 process_thread_action_fn_t clear_single_step_fn,
 process_thread_action_fn_t hold_thread_fn,
 process_ptrace_traceme_log_fn_t log_fn);
int process_ptrace_attach_thread_body_result(
 void *thread, void *proc,
 const struct process_ptrace_attach_offsets *offsets, void *lock_node,
 process_mcs_rwlock_fn_t lock_fn, process_mcs_rwlock_fn_t unlock_fn,
 process_alloc_debugreg_fn_t alloc_debugreg_fn,
 process_thread_action_fn_t clear_single_step_fn,
 process_thread_action_fn_t hold_thread_fn,
 process_ptrace_traceme_log_fn_t log_fn);
int process_thread_signal_flags_reap_result(void *thread,
         unsigned long signal_flags_offset,
         int options, int clear_mask);
int process_wait_exit_status_reap_result(void *object,
      unsigned long exit_status_offset,
      int options);
int process_optional_ptr_should_free_result(unsigned long ptr_addr);
int process_hold_thread_warn_exited_result(int status);
int process_sigcommon_release_should_destroy_result(int dec_and_test);
int process_destroy_thread_tid_action_result(int has_tids, int is_main_thread,
         int uti_state);
int process_thread_should_free_pages_result(int is_main_thread);
int process_release_vm_should_run_free_cb_result(unsigned long free_cb_addr);
int process_release_mckfd_should_close_result(unsigned long close_cb_addr);
int process_mckfd_push_head_result(struct mckfd **headp, struct mckfd *entry);
struct mckfd *process_mckfd_pop_head_result(struct mckfd **headp);
int process_mckfd_close_all_result(struct mckfd *head,
       unsigned long next_offset,
       unsigned long close_offset);
int process_mckfd_free_result(struct mckfd *fdp,
         process_mckfd_free_fn_t free_fn);
int process_mckfd_drain_free_result(struct mckfd **headp,
        unsigned long next_offset,
        process_mckfd_free_fn_t free_fn);
int process_memory_range_free_result(
 struct process_vm *vm, struct vm_range *range,
 process_memory_range_free_fn_t free_fn);
int process_memory_range_log_result(
 struct process_vm *vm, struct vm_range *range, int error,
 process_memory_range_log_fn_t log_fn);
int process_memory_range_free_all_result(
 struct process_vm *vm, struct rb_root *root, unsigned long node_offset,
 process_memory_range_free_fn_t free_fn,
 process_memory_range_log_fn_t log_fn);
int process_flush_memory_body_result(
 struct process_vm *vm, process_noirq_lock_fn_t lock_fn,
 process_noirq_unlock_fn_t unlock_fn,
 process_memory_range_free_fn_t free_fn,
 process_memory_range_log_fn_t log_fn);
int process_free_all_memory_ranges_body_result(
 struct process_vm *vm, process_noirq_lock_fn_t lock_fn,
 process_noirq_unlock_fn_t unlock_fn,
 process_memory_range_free_fn_t free_fn,
 process_memory_range_log_fn_t log_fn);
int process_cpu_set_update_body_result(
 unsigned long cpu_set_addr, unsigned long lock_addr, int clear_cpu,
 int set_cpu, int cpu_set_bits, process_spin_lock_fn_t lock_fn,
 process_spin_unlock_fn_t unlock_fn);
int process_cpu_set_public_result(
 int cpu, unsigned long cpu_set_addr, unsigned long lock_addr,
 int cpu_set_bits, process_spin_lock_fn_t lock_fn,
 process_spin_unlock_fn_t unlock_fn);
int process_cpu_clear_public_result(
 int cpu, unsigned long cpu_set_addr, unsigned long lock_addr,
 int cpu_set_bits, process_spin_lock_fn_t lock_fn,
 process_spin_unlock_fn_t unlock_fn);
int process_cpu_clear_and_set_public_result(
 int clear_cpu, int set_cpu, unsigned long cpu_set_addr,
 unsigned long lock_addr, int cpu_set_bits,
 process_spin_lock_fn_t lock_fn,
 process_spin_unlock_fn_t unlock_fn);
int process_ref_inc_result(void *object, unsigned long ref_offset,
      process_ref_inc_fn_t inc_fn);
int process_hold_thread_warn_result(void *thread,
        process_hold_thread_warn_fn_t warn_fn);
int process_ref_hold_body_result(void *object, unsigned long ref_offset,
     process_ref_inc_fn_t inc_fn);
int process_hold_thread_body_result(
 void *thread, unsigned long status_offset, unsigned long refcount_offset,
 process_ref_inc_fn_t inc_fn, process_hold_thread_warn_fn_t warn_fn);
void *process_current_resource_set_result(
 process_current_resource_set_fn_t current_resource_set_fn);
int process_resource_process_action_result(
 void *resource_set, void *process,
 process_resource_process_action_fn_t action_fn);
int process_process_action_result(void *process,
      process_process_action_fn_t action_fn);
int process_resource_set_action_result(
 void *resource_set, process_resource_set_action_fn_t action_fn);
int process_thread_action_result(void *thread,
     process_thread_action_fn_t action_fn);
int process_thread_profile_result(void *thread, void *process,
      process_thread_profile_fn_t profile_fn);
int process_vm_action_result(void *vm, process_vm_action_fn_t action_fn);
int process_policy_free_result(void *policy,
          process_policy_free_fn_t policy_free_fn);
int process_vm_free_cb_result(void *vm, void *opt,
         process_vm_free_cb_fn_t free_cb);
unsigned long process_spin_lock_result(unsigned long lock_addr,
           process_spin_lock_fn_t lock_fn);
int process_spin_unlock_result(unsigned long lock_addr,
          unsigned long irqstate,
          process_spin_unlock_fn_t unlock_fn);
int process_release_process_body_result(
 void *proc, unsigned long refcount_offset, unsigned long tids_offset,
 unsigned long main_thread_offset, unsigned long mckfd_offset,
 unsigned long mckfd_lock_offset, unsigned long mckfd_next_offset,
 process_ref_dec_and_test_fn_t dec_fn,
 process_current_resource_set_fn_t current_resource_set_fn,
 process_resource_process_action_fn_t hash_detach_fn,
 process_process_action_fn_t sibling_detach_fn,
 process_process_action_fn_t profile_fn,
 process_thread_action_fn_t free_thread_pages_fn,
 process_spin_lock_fn_t lock_fn, process_spin_unlock_fn_t unlock_fn,
 process_mckfd_free_fn_t mckfd_free_fn, process_free_fn_t free_fn,
 process_resource_set_action_fn_t final_cleanup_fn);
int process_vm_policy_drain_free_result(struct rb_root *root,
     unsigned long node_offset,
     process_policy_free_fn_t free_fn);
int process_detach_address_space_pid_result(
 void *address_space, int pid, process_detach_address_space_fn_t detach_fn);
int process_release_process_action_result(
 void *process, process_release_process_fn_t release_fn);
int process_release_vm_detach_process_result(
 struct process_vm *vm, unsigned long address_space_offset,
 unsigned long proc_offset, unsigned long pid_offset,
 unsigned long proc_vm_offset,
 process_detach_address_space_fn_t detach_fn,
 process_release_process_fn_t release_fn);
int process_release_fp_regs_result(struct thread *thread,
       process_release_fp_regs_fn_t release_fp_fn);
int process_destroy_thread_optional_cleanup_result(
 struct thread *thread, unsigned long debugreg_offset,
 unsigned long recvsig_offset, unsigned long sendsig_offset,
 unsigned long fp_regs_offset, unsigned long coredump_regs_offset,
 process_optional_free_fn_t free_fn,
 process_release_fp_regs_fn_t release_fp_fn);
int process_release_sigcommon_body_result(
 void *sigcommon, int dec_and_test, int sigpending_empty,
 unsigned long sigpending_offset, unsigned long pending_list_offset,
 process_free_fn_t free_fn);
int process_release_sigcommon_public_body_result(
 void *sigcommon, unsigned long use_offset,
 unsigned long sigpending_offset, unsigned long pending_list_offset,
 process_ref_dec_and_test_fn_t dec_fn, process_free_fn_t free_fn);
int process_release_tid_body_result(
 void *tids, int nr_tids, unsigned long tid_stride,
 unsigned long tid_thread_offset, void *thread, int thread_tid,
 process_tid_log_fn_t log_fn);
int process_tid_log_result(int old_tid, void *thread, int new_tid,
      process_tid_log_fn_t log_fn);
int process_replace_tid_body_result(
 void *tids, int nr_tids, unsigned long tid_stride,
 unsigned long tid_offset, unsigned long tid_thread_offset,
 void *thread, int old_tid, int new_tid, process_tid_log_fn_t log_fn);
int process_chain_process_body_result(
 struct list_head *siblings_entry, struct list_head *children_head,
 unsigned long children_lock_addr, struct list_head *hash_entry,
 struct list_head *hash_head, unsigned long hash_lock_addr,
 void *lock_node, process_mcs_rwlock_fn_t lock_fn,
 process_mcs_rwlock_fn_t unlock_fn);
int process_chain_thread_body_result(
 struct list_head *siblings_entry, struct list_head *threads_head,
 unsigned long threads_lock_addr, struct list_head *hash_entry,
 struct list_head *hash_head, unsigned long hash_lock_addr, void *vm,
 unsigned long vm_refcount_offset, void *lock_node,
 process_mcs_rwlock_fn_t lock_fn, process_mcs_rwlock_fn_t unlock_fn,
 process_ref_inc_fn_t ref_inc_fn);
int process_destroy_thread_body_result(
 void *thread, unsigned long thread_proc_offset,
 unsigned long thread_vm_offset, unsigned long thread_cpu_id_offset,
 unsigned long thread_siblings_list_offset,
 unsigned long thread_uti_state_offset,
 unsigned long thread_uti_refill_tid_offset,
 unsigned long thread_sigpending_offset,
 unsigned long thread_sigcommon_offset,
 unsigned long proc_threads_lock_offset, unsigned long proc_tids_offset,
 unsigned long proc_main_thread_offset,
 unsigned long vm_address_space_offset,
 unsigned long address_space_cpu_set_offset,
 unsigned long address_space_cpu_set_lock_offset,
 unsigned long pending_list_offset,
 unsigned long debugreg_offset, unsigned long recvsig_offset,
 unsigned long sendsig_offset, unsigned long fp_regs_offset,
 unsigned long coredump_regs_offset, int cpu_set_bits, void *lock_node,
 process_mcs_rwlock_fn_t lock_fn, process_mcs_rwlock_fn_t unlock_fn,
 process_thread_action_fn_t hash_detach_fn,
 process_thread_action_fn_t time_account_fn,
 process_thread_proc_action_fn_t release_tid_fn,
 process_thread_tid_action_fn_t replace_tid_fn,
 process_spin_lock_fn_t cpu_lock_fn,
 process_spin_unlock_fn_t cpu_unlock_fn,
 process_optional_free_fn_t free_fn,
 process_release_fp_regs_fn_t release_fp_fn,
 process_thread_action_fn_t release_sigcommon_fn,
 process_thread_action_fn_t free_thread_pages_fn);
void *process_find_thread_body_result(
 struct list_head *hash_head, unsigned long hash_lock_addr, void *lock_node,
 int pid, int tid, const struct process_find_thread_offsets *offsets,
 process_mcs_rwlock_fn_t lock_fn, process_mcs_rwlock_fn_t unlock_fn,
 process_thread_action_fn_t hold_fn);
void *process_find_process_body_result(
 struct list_head *hash_head, unsigned long hash_lock_addr, void *lock_node,
 int pid, const struct process_find_process_offsets *offsets,
 process_mcs_rwlock_fn_t lock_fn, process_mcs_rwlock_fn_t unlock_fn);
int process_unlock_found_process_result(
 void *process, unsigned long hash_lock_addr, void *lock_node,
 process_mcs_rwlock_fn_t unlock_fn);
int process_release_thread_body_result(
 void *thread, unsigned long refcount_offset, unsigned long vm_offset,
 unsigned long proc_offset, process_ref_dec_and_test_fn_t dec_fn,
 process_thread_profile_fn_t profile_fn,
 process_thread_action_fn_t procfs_delete_fn,
 process_thread_action_fn_t destroy_thread_fn,
 process_vm_action_fn_t release_vm_fn);
int process_release_vm_body_result(
 void *vm, unsigned long refcount_offset, unsigned long proc_offset,
 unsigned long proc_mckfd_offset, unsigned long proc_mckfd_lock_offset,
 unsigned long mckfd_next_offset, unsigned long mckfd_close_offset,
 unsigned long vm_free_cb_offset, unsigned long vm_opt_offset,
 unsigned long vm_address_space_offset, unsigned long proc_pid_offset,
 unsigned long proc_vm_offset, unsigned long vm_policy_tree_offset,
 unsigned long policy_node_offset,
 process_ref_dec_and_test_fn_t dec_fn,
 process_spin_lock_fn_t lock_fn, process_spin_unlock_fn_t unlock_fn,
 process_vm_action_fn_t flush_fn, process_vm_action_fn_t free_ranges_fn,
 process_detach_address_space_fn_t detach_fn,
 process_release_process_fn_t release_process_fn,
 process_policy_free_fn_t policy_free_fn, process_free_fn_t free_vm_fn);



int process_release_thread_checked_body_result(
 void *thread, unsigned long refcount_offset, unsigned long vm_offset,
 unsigned long proc_offset, process_ref_dec_and_test_fn_t dec_fn,
 process_thread_profile_fn_t profile_fn,
 process_thread_action_fn_t procfs_delete_fn,
 process_thread_action_fn_t destroy_thread_fn,
 process_vm_release_checked_fn_t release_vm_fn);
int process_release_vm_checked_body_result(
 void *vm, unsigned long refcount_offset, unsigned long proc_offset,
 unsigned long proc_mckfd_offset, unsigned long proc_mckfd_lock_offset,
 unsigned long mckfd_next_offset, unsigned long mckfd_close_offset,
 unsigned long vm_free_cb_offset, unsigned long vm_opt_offset,
 unsigned long vm_address_space_offset, unsigned long proc_pid_offset,
 unsigned long proc_vm_offset, unsigned long vm_policy_tree_offset,
 unsigned long policy_node_offset,
 process_ref_dec_and_test_fn_t dec_fn,
 process_spin_lock_fn_t lock_fn, process_spin_unlock_fn_t unlock_fn,
 process_vm_action_fn_t flush_fn, process_vm_action_fn_t free_ranges_fn,
 process_detach_address_space_fn_t detach_fn,
 process_release_process_fn_t release_process_fn,
 process_policy_free_fn_t policy_free_fn, process_free_fn_t free_vm_fn);
# 26 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c" 2
# 1 "/home/holden/mckernel/kernel/include/sched_helpers.h" 1







struct sched_idle_offsets {
 unsigned long cpu_runq_lock_offset;
 unsigned long cpu_runq_irqstate_offset;
 unsigned long cpu_current_offset;
 unsigned long cpu_flags_offset;
 unsigned long cpu_status_offset;
 unsigned long cpu_runq_offset;
 unsigned long thread_sched_list_offset;
 unsigned long thread_status_offset;
 unsigned long monitor_status_offset;
 unsigned long monitor_counter_offset;
};

struct sched_idle_values {
 int cpu_running;
 int cpu_idle;
 int cpu_reserved;
 int thread_running;
 int thread_stopped;
 int thread_interruptible;
 unsigned int need_migrate;
 int monitor_idle;
 int monitor_kernel;
};

struct sched_idle_callbacks {
 unsigned long (*current_cpu)(void);
 unsigned long (*lock)(unsigned long lock_addr);
 void (*unlock)(unsigned long lock_addr, unsigned long irqstate);
 void (*enable_interrupt)(void);
 void (*disable_interrupt)(void);
 void (*schedule)(void);
 void (*migrate)(void);
 void (*consolidate)(void);
 void (*zero_free)(void);
 void (*safe_halt)(void);
};

unsigned long sched_idle_current_cpu_bridge(void);
void process_sched_zero_free_bridge(void);
void sched_idle_begin_body_result(unsigned long cpu_addr,
 const struct sched_idle_offsets *offsets,
 const struct sched_idle_values *values,
 const struct sched_idle_callbacks *callbacks);
void sched_idle_iteration_body_result(unsigned long cpu_addr,
 unsigned long monitor_addr, const struct sched_idle_offsets *offsets,
 const struct sched_idle_values *values,
 const struct sched_idle_callbacks *callbacks);
void sched_idle_loop_body_result(unsigned long cpu_addr,
 unsigned long monitor_addr, const struct sched_idle_offsets *offsets,
 const struct sched_idle_values *values,
 const struct sched_idle_callbacks *callbacks) __attribute__((noreturn));



int sched_idle_runqueue_has_running_result(unsigned long runq_head,
 unsigned long thread_sched_list_offset,
 unsigned long thread_status_offset, int running_status);
# 90 "/home/holden/mckernel/kernel/include/sched_helpers.h"
typedef void (*futex_hb_lock_fn_t)(unsigned long lock_addr);
typedef void (*futex_hb_unlock_fn_t)(unsigned long lock_addr);
typedef void (*futex_wake_scan_fn_t)(unsigned long q_addr);
typedef void (*futex_requeue_scan_fn_t)(unsigned long q_addr,
     unsigned long ctx_addr);
typedef void (*futex_key_refs_fn_t)(unsigned long key_addr);
typedef int (*futex_get_key_vtop_fn_t)(unsigned long mm_addr,
           unsigned long uaddr,
           unsigned long phys_out_addr);
typedef int (*futex_get_key_fault_fn_t)(unsigned long mm_addr,
     unsigned long uaddr, int flags);
typedef void (*futex_get_key_log_fn_t)(int event);
typedef unsigned long (*futex_wake_hash_key_fn_t)(unsigned long key_addr);
typedef unsigned long (*futex_wake_lock_fn_t)(unsigned long lock_addr);
typedef void (*futex_wake_unlock_fn_t)(unsigned long lock_addr,
           unsigned long irqstate);
typedef int (*futex_wait_get_key_fn_t)(unsigned long uaddr, int fshared,
           unsigned long key_addr);
typedef int (*futex_wake_atomic_op_fn_t)(int op, unsigned long uaddr);
typedef unsigned long (*futex_wait_queue_lock_fn_t)(unsigned long q_addr);
typedef int (*futex_wait_get_value_fn_t)(unsigned long value_addr,
      unsigned long uaddr);
typedef void (*futex_wait_queue_unlock_fn_t)(unsigned long q_addr,
          unsigned long hb_addr);
typedef void (*futex_wait_put_key_fn_t)(int fshared, unsigned long key_addr);
typedef unsigned long (*futex_alloc_fn_t)(unsigned long size, int flag);
typedef unsigned int (*futex_hash_fn_t)(unsigned long key_addr);
typedef int (*futex_dispatch_wait_fn_t)(unsigned long uaddr, int fshared,
     uint32_t val, uint64_t timeout,
     uint32_t val3, int clockrt);
typedef int (*futex_dispatch_wake_fn_t)(unsigned long uaddr, int fshared,
     uint32_t val, uint32_t val3);
typedef int (*futex_dispatch_requeue_fn_t)(unsigned long uaddr, int fshared,
        unsigned long uaddr2, uint32_t val,
        uint32_t val2, int cmpval_present,
        uint32_t cmpval, int requeue_pi);
typedef int (*futex_dispatch_wake_op_fn_t)(unsigned long uaddr, int fshared,
        unsigned long uaddr2, uint32_t val,
        uint32_t val2, uint32_t val3);
typedef void (*futex_dispatch_invalid_fn_t)(int cmd);
typedef unsigned long (*futex_wake_linux_channel_by_cpu_fn_t)(int linux_cpu);
typedef int (*futex_wake_send_fn_t)(unsigned long channel_addr,
        unsigned long packet_addr);
typedef void (*futex_wake_thread_fn_t)(unsigned long thread_addr,
           int status);
typedef void (*futex_wake_log_fn_t)(int event, unsigned long thread_addr,
        unsigned long uti_futex_resp,
        int linux_cpu,
        unsigned long channel_addr, int rc);
typedef unsigned long (*futex_virt_to_phys_fn_t)(unsigned long addr);
typedef int (*futex_interrupt_id_fn_t)(int cpu_id);
typedef int (*futex_vector_fn_t)(int vector_key);
typedef unsigned long (*futex_wait_spin_lock_fn_t)(unsigned long lock_addr);
typedef void (*futex_wait_spin_unlock_fn_t)(unsigned long lock_addr,
         unsigned long irqstate);
typedef void (*futex_wait_queue_me_fn_t)(unsigned long q_addr,
      unsigned long hb_addr);
typedef int64_t (*futex_wait_schedule_timeout_fn_t)(uint64_t timeout);
typedef void (*futex_wait_schedule_direct_fn_t)(void);
typedef void (*futex_wait_queue_log_fn_t)(int event,
       unsigned long thread_addr,
       int tid);
typedef int (*futex_wait_setup_call_fn_t)(unsigned long uaddr,
       uint32_t val,
       int fshared,
       unsigned long q_addr,
       unsigned long hb_out_addr);
typedef int64_t (*futex_wait_queue_call_fn_t)(unsigned long hb_addr,
           unsigned long q_addr,
           uint64_t timeout);
typedef int (*futex_wait_unqueue_fn_t)(unsigned long q_addr);
typedef int (*futex_wait_has_signal_fn_t)(unsigned long thread_addr);
typedef void (*futex_wait_log_fn_t)(int event, unsigned long thread_addr,
        int tid, int ret);
typedef unsigned long (*futex_wait_timestamp_fn_t)(void);
typedef int (*futex_wait_body_entry_fn_t)(unsigned long uaddr, int fshared,
       uint32_t val, uint64_t timeout,
       uint32_t bitset,
       unsigned long q_addr,
       unsigned long thread_addr,
       unsigned long uti_futex_resp);
typedef void (*timer_spin_init_fn_t)(unsigned long lock_addr);
typedef unsigned long (*timer_spin_lock_fn_t)(unsigned long lock_addr);
typedef void (*timer_spin_unlock_fn_t)(unsigned long lock_addr,
           unsigned long irqstate);
typedef uint64_t (*timer_rdtsc_fn_t)(void);
typedef void (*timer_void_fn_t)(void);
typedef void (*timer_set_status_fn_t)(unsigned long status_addr, int status);
typedef void (*timer_lapic_enable_fn_t)(unsigned int clocks);
typedef void (*timer_lapic_disable_fn_t)(void);
typedef void (*timer_waitq_wakeup_fn_t)(unsigned long waitq_addr);
typedef void (*timer_log_wake_fn_t)(unsigned long timer_addr,
        unsigned long thread_addr);
typedef unsigned long (*sched_migrate_spin_lock_fn_t)(
 unsigned long lock_addr);
typedef void (*sched_migrate_spin_unlock_fn_t)(unsigned long lock_addr,
            unsigned long irqstate);
typedef void (*sched_migrate_noirq_lock_fn_t)(unsigned long lock_addr);
typedef void (*sched_migrate_noirq_unlock_fn_t)(unsigned long lock_addr);
typedef void (*sched_migrate_waitq_init_fn_t)(unsigned long waitq_addr);
typedef void (*sched_migrate_waitq_prepare_fn_t)(unsigned long waitq_addr,
       unsigned long entry_addr,
       int status);
typedef void (*sched_migrate_waitq_finish_fn_t)(unsigned long waitq_addr,
      unsigned long entry_addr);
typedef int (*sched_migrate_vector_fn_t)(int vector_key);
typedef void (*sched_migrate_interrupt_fn_t)(int cpu, int vector);
typedef void (*sched_migrate_void_fn_t)(void);
typedef void (*sched_migrate_log_fn_t)(unsigned long thread_addr, int tid,
           int cpu_id);
typedef unsigned long (*sched_migrate_cpu_local_fn_t)(int cpu_id);
typedef void (*sched_migrate_waitq_wakeup_fn_t)(unsigned long waitq_addr);
typedef void (*sched_do_migrate_log_fn_t)(unsigned long thread_addr, int tid,
       int old_cpu_id, int new_cpu_id);
typedef void (*sched_runq_rwlock_fn_t)(unsigned long lock_addr,
           unsigned long node_addr);
typedef void (*sched_runq_status_set_fn_t)(unsigned long status_addr,
        int status);
typedef void (*sched_runq_set_timer_fn_t)(int runq_locked);
typedef void (*sched_runq_log_fn_t)(int event, unsigned long arg0,
        unsigned long arg1, int arg2, int arg3);
typedef unsigned long (*sched_runq_irq_save_fn_t)(void);
typedef void (*sched_runq_irq_restore_fn_t)(unsigned long irqstate);
typedef int (*sched_runq_has_signal_fn_t)(unsigned long thread_addr);
typedef void (*sched_runq_void_fn_t)(void);
typedef void (*sched_runq_thread_fn_t)(unsigned long thread_addr);
typedef int (*sched_runq_counter_inc_fn_t)(unsigned long counter_addr);
typedef void (*sched_runq_counter_dec_fn_t)(unsigned long counter_addr);

struct timer_runtime_offsets {
 unsigned long thread_status_offset;
 unsigned long thread_sched_list_offset;
 unsigned long thread_spin_sleep_lock_offset;
 unsigned long thread_spin_sleep_offset;
 unsigned long thread_itimer_enabled_offset;
 unsigned long cpu_runq_lock_offset;
 unsigned long cpu_runq_offset;
 unsigned long cpu_runq_len_offset;
 unsigned long cpu_current_offset;
 unsigned long cpu_timer_enabled_offset;
 unsigned long cpu_backlog_list_offset;
 unsigned long timer_timeout_offset;
 unsigned long timer_waitq_offset;
 unsigned long timer_list_offset;
 unsigned long timer_thread_offset;
};

struct sched_migrate_offsets {
 unsigned long req_list_offset;
 unsigned long req_thread_offset;
 unsigned long req_wq_offset;
 unsigned long thread_cpu_id_offset;
 unsigned long thread_tid_offset;
 unsigned long cpu_migq_lock_offset;
 unsigned long cpu_migq_offset;
 unsigned long cpu_runq_lock_offset;
 unsigned long cpu_flags_offset;
 unsigned long cpu_status_offset;
};

struct sched_do_migrate_offsets {
 unsigned long req_list_offset;
 unsigned long req_thread_offset;
 unsigned long req_wq_offset;
 unsigned long thread_cpu_id_offset;
 unsigned long thread_tid_offset;
 unsigned long thread_cpu_set_offset;
 unsigned long thread_sched_list_offset;
 unsigned long thread_vm_offset;
 unsigned long vm_address_space_offset;
 unsigned long address_space_cpu_set_offset;
 unsigned long address_space_cpu_set_lock_offset;
 unsigned long cpu_migq_lock_offset;
 unsigned long cpu_migq_offset;
 unsigned long cpu_runq_lock_offset;
 unsigned long cpu_runq_offset;
 unsigned long cpu_runq_len_offset;
 unsigned long cpu_flags_offset;
};

struct sched_runqueue_offsets {
 unsigned long thread_cpu_id_offset;
 unsigned long thread_tid_offset;
 unsigned long thread_status_offset;
 unsigned long thread_spin_sleep_lock_offset;
 unsigned long thread_spin_sleep_offset;
 unsigned long thread_sched_list_offset;
 unsigned long thread_sigpending_offset;
 unsigned long thread_sigcommon_offset;
 unsigned long sigcommon_sigpending_offset;
 unsigned long thread_proc_offset;
 unsigned long thread_mod_clone_offset;
 unsigned long proc_pid_offset;
 unsigned long proc_status_offset;
 unsigned long proc_update_lock_offset;
 unsigned long proc_clone_count_offset;
 unsigned long cpu_runq_lock_offset;
 unsigned long cpu_runq_irqstate_offset;
 unsigned long cpu_current_offset;
 unsigned long cpu_prevpid_offset;
 unsigned long cpu_runq_offset;
 unsigned long cpu_runq_len_offset;
 unsigned long cpu_runq_reserved_offset;
 unsigned long cpu_flags_offset;
 unsigned long cpu_status_offset;
 unsigned long cpu_in_interrupt_offset;
 unsigned long cpu_nr_ctx_switches_offset;
};

struct sched_schedule_result {
 unsigned long cpu_addr;
 unsigned long prev_thread_addr;
 unsigned long next_thread_addr;
 int prevpid;
 int switch_ctx;
 int action;
};
# 329 "/home/holden/mckernel/kernel/include/sched_helpers.h"
uint64_t timer_spin_sleep_remaining_result(uint64_t timeout, uint64_t elapsed);
int timer_runq_should_schedule_result(int runq_len);
uint64_t timer_after_spin_remaining_result(uint64_t timeout,
        uint64_t loop_timeout);
uint64_t timer_after_tick_remaining_result(uint64_t timeout,
        uint64_t loop_timeout);
int timer_init_timers_result(unsigned long timers_lock_addr,
        unsigned long timers_head_addr,
        timer_spin_init_fn_t spin_init_fn);
uint64_t timer_schedule_timeout_body_result(
 unsigned long thread_addr, unsigned long cpu_local_addr,
 uint64_t timeout, uint64_t loop_timeout,
 const struct timer_runtime_offsets *offsets,
 timer_rdtsc_fn_t rdtsc_fn, timer_spin_lock_fn_t spin_lock_fn,
 timer_spin_unlock_fn_t spin_unlock_fn,
 timer_set_status_fn_t set_status_fn, timer_void_fn_t schedule_fn,
 timer_void_fn_t zero_free_fn, timer_void_fn_t pause_fn);
int timer_wake_tick_result(unsigned long timers_lock_addr,
      unsigned long timers_head_addr,
      uint64_t loop_timeout,
      const struct timer_runtime_offsets *offsets,
      timer_spin_lock_fn_t lock_fn,
      timer_spin_unlock_fn_t unlock_fn,
      timer_waitq_wakeup_fn_t wake_fn,
      timer_log_wake_fn_t log_fn);
int timer_wake_loop_body_result(unsigned long timers_lock_addr,
    unsigned long timers_head_addr,
    uint64_t loop_timeout, int max_ticks,
    const struct timer_runtime_offsets *offsets,
    timer_rdtsc_fn_t rdtsc_fn,
    timer_void_fn_t pause_fn,
    timer_spin_lock_fn_t lock_fn,
    timer_spin_unlock_fn_t unlock_fn,
    timer_waitq_wakeup_fn_t wake_fn,
    timer_log_wake_fn_t log_fn);
int timer_set_timer_body_result(unsigned long cpu_local_addr, int time_sharing,
    int runq_locked,
    const struct timer_runtime_offsets *offsets,
    timer_spin_lock_fn_t lock_fn,
    timer_spin_unlock_fn_t unlock_fn,
    timer_lapic_enable_fn_t enable_fn,
    timer_lapic_disable_fn_t disable_fn);
int sched_request_migrate_body_result(
 int target_cpu_id, unsigned long target_cpu_addr,
 unsigned long req_addr, unsigned long wait_entry_addr,
 unsigned long thread_addr, int current_cpu_id, int wait_status,
 unsigned int need_resched_flag, unsigned int need_migrate_flag,
 int running_status, int vector_key,
 const struct sched_migrate_offsets *offsets,
 sched_migrate_spin_lock_fn_t lock_fn,
 sched_migrate_spin_unlock_fn_t unlock_fn,
 sched_migrate_noirq_lock_fn_t noirq_lock_fn,
 sched_migrate_noirq_unlock_fn_t noirq_unlock_fn,
 sched_migrate_waitq_init_fn_t waitq_init_fn,
 sched_migrate_waitq_prepare_fn_t waitq_prepare_fn,
 sched_migrate_waitq_finish_fn_t waitq_finish_fn,
 sched_migrate_vector_fn_t vector_fn,
 sched_migrate_interrupt_fn_t interrupt_fn,
 sched_migrate_void_fn_t schedule_fn,
 sched_migrate_log_fn_t log_fn);
int sched_do_migrate_body_result(
 int current_cpu_id, unsigned long current_cpu_addr, int cpu_set_bits,
 unsigned int need_resched_flag, int vector_key,
 const struct sched_do_migrate_offsets *offsets,
 sched_migrate_spin_lock_fn_t lock_fn,
 sched_migrate_spin_unlock_fn_t unlock_fn,
 sched_migrate_noirq_lock_fn_t noirq_lock_fn,
 sched_migrate_noirq_unlock_fn_t noirq_unlock_fn,
 sched_migrate_cpu_local_fn_t cpu_local_fn,
 sched_migrate_waitq_wakeup_fn_t waitq_wakeup_fn,
 sched_migrate_vector_fn_t vector_fn,
 sched_migrate_interrupt_fn_t interrupt_fn,
 sched_do_migrate_log_fn_t log_fn);
int sched_release_cpuid_body_result(
 int cpuid, unsigned long cpu_addr, unsigned long reservation_lock_addr,
 int idle_status, const struct sched_runqueue_offsets *offsets,
 sched_migrate_spin_lock_fn_t lock_fn,
 sched_migrate_spin_unlock_fn_t unlock_fn,
 sched_migrate_noirq_lock_fn_t noirq_lock_fn,
 sched_migrate_noirq_unlock_fn_t noirq_unlock_fn);
int sched_check_need_resched_body_result(
 unsigned long cpu_addr, unsigned int need_resched_flag,
 unsigned int need_migrate_flag,
 const struct sched_runqueue_offsets *offsets,
 sched_migrate_spin_lock_fn_t lock_fn,
 sched_migrate_spin_unlock_fn_t unlock_fn,
 sched_migrate_void_fn_t schedule_fn,
 sched_runq_log_fn_t log_fn);
int sched_runq_add_thread_locked_result(
 unsigned long thread_addr, unsigned long cpu_addr, int cpu_id,
 unsigned int need_resched_flag, int running_status,
 const struct sched_runqueue_offsets *offsets,
 sched_runq_log_fn_t log_fn);
int sched_runq_add_thread_body_result(
 unsigned long thread_addr, unsigned long cpu_addr,
 unsigned long reservation_lock_addr, int cpu_id, int current_cpu_id,
 unsigned int need_resched_flag, int running_status, int vector_key,
 const struct sched_runqueue_offsets *offsets,
 sched_migrate_spin_lock_fn_t lock_fn,
 sched_migrate_spin_unlock_fn_t unlock_fn,
 sched_migrate_noirq_lock_fn_t noirq_lock_fn,
 sched_migrate_noirq_unlock_fn_t noirq_unlock_fn,
 sched_runq_counter_dec_fn_t reserved_dec_fn,
 sched_runq_thread_fn_t procfs_create_fn,
 sched_runq_counter_inc_fn_t clone_count_inc_fn,
 sched_runq_void_fn_t rusage_inc_fn,
 sched_runq_void_fn_t rusage_debug_fn,
 sched_migrate_vector_fn_t vector_fn,
 sched_migrate_interrupt_fn_t interrupt_fn,
 sched_runq_log_fn_t log_fn);
int sched_runq_del_thread_body_result(
 unsigned long thread_addr, unsigned long cpu_addr, int idle_status,
 const struct sched_runqueue_offsets *offsets,
 sched_migrate_spin_lock_fn_t lock_fn,
 sched_migrate_spin_unlock_fn_t unlock_fn);
int sched_wakeup_thread_body_result(
 unsigned long thread_addr, unsigned long cpu_addr,
 unsigned long update_lock_node_addr, int current_cpu_id,
 int valid_states, int runq_locked, int running_status, int exited_status,
 unsigned int need_resched_flag, int vector_key,
 const struct sched_runqueue_offsets *offsets,
 sched_migrate_spin_lock_fn_t lock_fn,
 sched_migrate_spin_unlock_fn_t unlock_fn,
 sched_runq_rwlock_fn_t rwlock_fn,
 sched_runq_rwlock_fn_t rwunlock_fn,
 sched_runq_status_set_fn_t status_set_fn,
 sched_runq_set_timer_fn_t set_timer_fn,
 sched_migrate_vector_fn_t vector_fn,
 sched_migrate_interrupt_fn_t interrupt_fn,
 sched_runq_log_fn_t log_fn);
int sched_spin_sleep_or_schedule_body_result(
 unsigned long thread_addr, unsigned long cpu_addr, int current_cpu_id,
 int idle_halt_enabled, unsigned int need_resched_flag,
 const struct sched_runqueue_offsets *offsets,
 sched_runq_irq_save_fn_t irq_save_fn,
 sched_runq_irq_restore_fn_t irq_restore_fn,
 sched_migrate_spin_lock_fn_t lock_fn,
 sched_migrate_spin_unlock_fn_t unlock_fn,
 sched_migrate_noirq_lock_fn_t noirq_lock_fn,
 sched_migrate_noirq_unlock_fn_t noirq_unlock_fn,
 sched_migrate_void_fn_t schedule_fn,
 sched_migrate_void_fn_t zero_free_fn,
 sched_migrate_void_fn_t pause_fn,
 sched_runq_has_signal_fn_t has_signal_fn,
 sched_runq_log_fn_t log_fn);
int sched_schedule_prepare_body_result(
 unsigned long cpu_addr, unsigned long idle_thread_addr,
 int no_preempt_count, unsigned int need_resched_flag,
 unsigned int need_migrate_flag, int running_status,
 int interruptible_status, int exited_status, int spawning_to_remote,
 int idle_cpu_status, int reserved_cpu_status,
 const struct sched_runqueue_offsets *offsets,
 struct sched_schedule_result *result,
 sched_runq_irq_save_fn_t irq_save_fn,
 sched_runq_irq_restore_fn_t irq_restore_fn,
 sched_migrate_noirq_lock_fn_t noirq_lock_fn,
 sched_migrate_noirq_unlock_fn_t noirq_unlock_fn,
 sched_runq_set_timer_fn_t set_timer_fn,
 sched_runq_void_fn_t reset_cputime_fn,
 sched_runq_has_signal_fn_t has_signal_fn,
 sched_runq_log_fn_t log_fn);
int futex_key_match_result(int has_key1, int has_key2,
      unsigned long word1, unsigned long ptr1,
      unsigned long offset1, unsigned long word2,
      unsigned long ptr2, unsigned long offset2);
int futex_key_prepare_result(unsigned long address, int fshared,
        unsigned long *basep, unsigned long *offsetp,
        int *privatep);
int futex_get_key_result(unsigned long uaddr, int fshared,
    unsigned long key_addr, unsigned long mm_addr,
    unsigned long key_word_offset,
    unsigned long key_ptr_offset,
    unsigned long key_offset_offset,
    unsigned long fut_off_mmshared, int fault_flags,
    futex_key_refs_fn_t key_refs_fn,
    futex_get_key_vtop_fn_t vtop_fn,
    futex_get_key_fault_fn_t fault_fn,
    futex_get_key_log_fn_t log_fn);
int futex_wake_bitset_valid_result(unsigned int bitset);
int futex_waiter_matches_bitset_result(unsigned int waiter_bitset,
           unsigned int requested_bitset);
int futex_wake_limit_reached_result(int woken, int nr_wake);
int futex_wake_scan_result(unsigned long chain_addr,
      unsigned long q_list_offset,
      unsigned long q_key_offset,
      unsigned long q_bitset_offset,
      unsigned long key_word_offset,
      unsigned long key_ptr_offset,
      unsigned long key_offset_offset,
      unsigned long target_word,
      unsigned long target_ptr,
      int target_offset,
      unsigned int requested_bitset,
      int use_bitset,
      int nr_wake,
      futex_wake_scan_fn_t wake_fn);
int futex_wake_body_result(unsigned long uaddr, int fshared, int nr_wake,
      unsigned int bitset, unsigned long key_addr,
      unsigned long hb_lock_offset,
      unsigned long hb_chain_offset,
      unsigned long q_list_offset,
      unsigned long q_key_offset,
      unsigned long q_bitset_offset,
      unsigned long key_word_offset,
      unsigned long key_ptr_offset,
      unsigned long key_offset_offset,
      futex_wait_get_key_fn_t get_key_fn,
      futex_wake_hash_key_fn_t hash_key_fn,
      futex_wake_lock_fn_t lock_fn,
      futex_wake_unlock_fn_t unlock_fn,
      futex_wait_put_key_fn_t put_key_fn,
      futex_wake_scan_fn_t wake_fn);
int futex_wake_op_body_result(
 unsigned long uaddr1, int fshared, unsigned long uaddr2, int nr_wake,
 int nr_wake2, int op, unsigned long key1_addr,
 unsigned long key2_addr, unsigned long hb_lock_offset,
 unsigned long hb_chain_offset, unsigned long q_list_offset,
 unsigned long q_key_offset, unsigned long q_bitset_offset,
 unsigned long key_word_offset, unsigned long key_ptr_offset,
 unsigned long key_offset_offset, futex_wait_get_key_fn_t get_key_fn,
 futex_wake_hash_key_fn_t hash_key_fn, futex_hb_lock_fn_t lock_fn,
 futex_hb_unlock_fn_t unlock_fn, futex_wake_atomic_op_fn_t atomic_fn,
 futex_wait_put_key_fn_t put_key_fn, futex_wake_scan_fn_t wake_fn);
int futex_requeue_should_move_result(unsigned long source_chain,
         unsigned long target_chain);
int futex_requeue_loop_done_result(int task_count, int nr_wake,
       int nr_requeue);
int futex_requeue_should_wake_result(int task_count, int nr_wake);
int futex_requeue_scan_result(unsigned long chain_addr,
         unsigned long q_list_offset,
         unsigned long q_key_offset,
         unsigned long key_word_offset,
         unsigned long key_ptr_offset,
         unsigned long key_offset_offset,
         unsigned long target_word,
         unsigned long target_ptr,
         int target_offset,
         int nr_wake,
         int nr_requeue,
         int *drop_countp,
         futex_requeue_scan_fn_t wake_fn,
         futex_requeue_scan_fn_t requeue_fn,
         unsigned long ctx_addr);
int futex_requeue_body_result(
 unsigned long uaddr1, int fshared, unsigned long uaddr2, int nr_wake,
 int nr_requeue, unsigned long cmpval_addr, unsigned long key1_addr,
 unsigned long key2_addr, unsigned long ctx_addr,
 unsigned long hb_lock_offset, unsigned long hb_chain_offset,
 unsigned long q_list_offset, unsigned long q_key_offset,
 unsigned long key_word_offset, unsigned long key_ptr_offset,
 unsigned long key_offset_offset, unsigned long ctx_hb1_offset,
 unsigned long ctx_hb2_offset, unsigned long ctx_key2_offset,
 futex_wait_get_key_fn_t get_key_fn,
 futex_wake_hash_key_fn_t hash_key_fn, futex_hb_lock_fn_t lock_fn,
 futex_hb_unlock_fn_t unlock_fn,
 futex_wait_get_value_fn_t get_value_fn,
 futex_wait_put_key_fn_t put_key_fn,
 futex_key_refs_fn_t drop_key_refs_fn,
 futex_requeue_scan_fn_t wake_fn, futex_requeue_scan_fn_t requeue_fn);
void futex_double_lock_hb_result(unsigned long hb1_addr,
     unsigned long hb2_addr,
     unsigned long lock_offset,
     futex_hb_lock_fn_t lock_fn);
void futex_double_unlock_hb_result(unsigned long hb1_addr,
       unsigned long hb2_addr,
       unsigned long lock_offset,
       futex_hb_unlock_fn_t unlock_fn);
void futex_wake_mark_woken_result(unsigned long q_addr,
      unsigned long list_offset,
      unsigned long node_plist_offset,
      unsigned long lock_ptr_offset);
int futex_unqueue_detach_result(unsigned long q_addr,
    unsigned long list_offset,
    unsigned long node_plist_offset);
int futex_unqueue_me_result(unsigned long q_addr,
       unsigned long lock_ptr_offset,
       unsigned long list_offset,
       unsigned long node_plist_offset,
       unsigned long key_offset,
       futex_hb_lock_fn_t lock_fn,
       futex_hb_unlock_fn_t unlock_fn,
       futex_key_refs_fn_t drop_key_refs_fn);
int futex_requeue_move_result(unsigned long q_addr,
         unsigned long list_offset,
         unsigned long lock_ptr_offset,
         unsigned long source_chain,
         unsigned long target_chain,
         unsigned long target_lock,
         unsigned long debug_spinlock_offset);
int futex_requeue_key_update_result(unsigned long q_addr,
        unsigned long q_key_offset,
        unsigned long key_addr,
        unsigned long key_size,
        futex_key_refs_fn_t get_refs_fn);
void futex_queue_publish_waiter_result(
 unsigned long q_addr, unsigned long task_offset,
 unsigned long th_spin_sleep_pa_offset,
 unsigned long th_status_pa_offset,
 unsigned long th_spin_sleep_lock_pa_offset,
 unsigned long proc_status_pa_offset,
 unsigned long proc_update_lock_pa_offset,
 unsigned long runq_lock_pa_offset,
 unsigned long clv_flags_pa_offset,
 unsigned long intr_id_offset,
 unsigned long intr_vector_offset,
 unsigned long task, unsigned long th_spin_sleep_pa,
 unsigned long th_status_pa,
 unsigned long th_spin_sleep_lock_pa,
 unsigned long proc_status_pa,
 unsigned long proc_update_lock_pa,
 unsigned long runq_lock_pa,
 unsigned long clv_flags_pa,
 int intr_id, int intr_vector);
void futex_queue_insert_result(unsigned long q_addr,
          unsigned long list_offset,
          unsigned long chain_addr,
          int prio,
          unsigned long debug_spinlock_offset,
          unsigned long lock_addr);
int futex_queue_me_result(
 unsigned long q_addr, unsigned long q_list_offset,
 unsigned long q_task_offset, unsigned long q_th_spin_sleep_pa_offset,
 unsigned long q_th_status_pa_offset,
 unsigned long q_th_spin_sleep_lock_pa_offset,
 unsigned long q_proc_status_pa_offset,
 unsigned long q_proc_update_lock_pa_offset,
 unsigned long q_runq_lock_pa_offset,
 unsigned long q_clv_flags_pa_offset,
 unsigned long q_intr_id_offset,
 unsigned long q_intr_vector_offset,
 unsigned long hb_chain_addr, unsigned long hb_lock_addr,
 int prio, unsigned long debug_spinlock_offset,
 unsigned long thread_addr, unsigned long thread_spin_sleep_offset,
 unsigned long thread_status_offset,
 unsigned long thread_spin_sleep_lock_offset,
 unsigned long thread_proc_offset,
 unsigned long thread_cpu_id_offset,
 unsigned long proc_status_offset,
 unsigned long proc_update_lock_offset,
 unsigned long runq_lock_addr, unsigned long clv_flags_addr,
 int vector_key, futex_virt_to_phys_fn_t virt_to_phys_fn,
 futex_interrupt_id_fn_t interrupt_id_fn,
 futex_vector_fn_t vector_fn, futex_hb_unlock_fn_t unlock_fn);
void futex_wait_prepare_q_result(unsigned long q_addr,
     unsigned long bitset_offset,
     unsigned long requeue_pi_key_offset,
     unsigned long uti_futex_resp_offset,
     unsigned int bitset,
     unsigned long uti_futex_resp);
void futex_wait_key_init_result(unsigned long q_addr,
    unsigned long key_offset,
    unsigned long key_size);
void futex_queue_lock_ptr_store_result(unsigned long q_addr,
           unsigned long lock_ptr_offset,
           unsigned long lock_addr);
int futex_wait_setup_result(unsigned long uaddr,
       unsigned int val,
       int fshared,
       unsigned long q_addr,
       unsigned long *hb_out,
       unsigned long key_offset,
       unsigned long key_size,
       futex_wait_get_key_fn_t get_key_fn,
       futex_wait_queue_lock_fn_t queue_lock_fn,
       futex_wait_get_value_fn_t get_value_fn,
       futex_wait_queue_unlock_fn_t queue_unlock_fn,
       futex_wait_put_key_fn_t put_key_fn);
int futex_wait_mark_interruptible_result(unsigned long thread_addr,
      unsigned long status_offset,
      int interruptible_status);
int futex_wait_spin_sleep_store_result(unsigned long thread_addr,
           unsigned long spin_sleep_offset,
           int value);
int futex_wait_finish_state_result(unsigned long thread_addr,
       unsigned long status_offset,
       unsigned long spin_sleep_offset,
       int running_status);
int futex_wait_schedule_action_result(int queued, uint64_t timeout);
int64_t futex_wait_queue_me_result(
 unsigned long hb_addr, unsigned long q_addr,
 unsigned long q_list_offset, unsigned long q_node_plist_offset,
 unsigned long q_plist_node_list_offset,
 unsigned long thread_addr, unsigned long thread_status_offset,
 unsigned long thread_spin_sleep_offset,
 unsigned long thread_spin_sleep_lock_offset,
 unsigned long thread_tid_offset, int idle_halt_enabled,
 uint64_t timeout, int interruptible_status, int running_status,
 futex_wait_spin_lock_fn_t spin_lock_fn,
 futex_wait_spin_unlock_fn_t spin_unlock_fn,
 futex_wait_queue_me_fn_t queue_me_fn,
 futex_wait_schedule_timeout_fn_t schedule_timeout_fn,
 futex_wait_schedule_direct_fn_t schedule_direct_fn,
 futex_wait_queue_log_fn_t log_fn);
int futex_wait_post_action_result(int unqueued, uint64_t timeout,
      int64_t time_remain,
      int has_pending_signal,
      int restart_sys);
int futex_wait_body_result(
 unsigned long uaddr, int fshared, uint32_t val,
 uint64_t timeout, uint32_t bitset,
 unsigned long q_addr, unsigned long thread_addr,
 unsigned long uti_futex_resp,
 unsigned long q_bitset_offset,
 unsigned long q_requeue_pi_key_offset,
 unsigned long q_uti_futex_resp_offset,
 unsigned long q_key_offset,
 unsigned long thread_tid_offset,
 futex_wait_setup_call_fn_t setup_fn,
 futex_wait_queue_call_fn_t wait_queue_fn,
 futex_wait_unqueue_fn_t unqueue_fn,
 futex_wait_has_signal_fn_t has_signal_fn,
 futex_wait_put_key_fn_t put_key_fn,
 futex_wait_log_fn_t log_fn);
int futex_wait_entry_result(
 unsigned long uaddr, int fshared, uint32_t val,
 uint64_t timeout, uint32_t bitset, unsigned long q_addr,
 unsigned long thread_addr, unsigned long uti_futex_resp,
 int profile_enabled, unsigned long thread_profile_offset,
 unsigned long thread_profile_start_ts_offset,
 unsigned long thread_profile_elapsed_ts_offset,
 futex_wait_timestamp_fn_t timestamp_fn,
 futex_wait_body_entry_fn_t wait_body_fn);
int futex_wake_target_result(unsigned long uti_futex_resp);
unsigned long futex_wake_linux_channel_result(unsigned long linux_channel,
           unsigned long fallback_channel);
void futex_wake_ikc_packet_fill_result(unsigned long packet_addr,
           unsigned long msg_offset,
           unsigned long resp_offset,
           unsigned long spin_sleep_offset,
           int msg, unsigned long resp,
           unsigned long spin_sleep_addr);
int futex_wake_orchestrate_result(
 unsigned long q_addr, unsigned long q_list_offset,
 unsigned long q_node_plist_offset, unsigned long q_lock_ptr_offset,
 unsigned long q_task_offset, unsigned long q_uti_futex_resp_offset,
 unsigned long q_linux_cpu_offset,
 unsigned long thread_spin_sleep_offset,
 unsigned long packet_addr, unsigned long packet_msg_offset,
 unsigned long packet_resp_offset,
 unsigned long packet_spin_sleep_offset, int msg,
 unsigned long fallback_channel, int wake_status,
 futex_wake_linux_channel_by_cpu_fn_t linux_channel_fn,
 futex_wake_send_fn_t send_fn,
 futex_wake_thread_fn_t wake_thread_fn,
 futex_wake_log_fn_t log_fn);
int futex_hash_bucket_table_init_result(unsigned long buckets_addr,
     int bucket_count,
     unsigned long bucket_stride,
     unsigned long lock_offset,
     unsigned long lock_word_offset,
     unsigned long chain_offset,
     unsigned long prio_list_offset,
     unsigned long node_list_offset,
     unsigned long debug_spinlock_offset,
     unsigned long debug_rawlock_offset);
int futex_init_table_result(unsigned long queues_slot_addr, int hashbits,
       unsigned long bucket_stride, int alloc_flag,
       futex_alloc_fn_t alloc_fn,
       unsigned long lock_offset,
       unsigned long lock_word_offset,
       unsigned long chain_offset,
       unsigned long prio_list_offset,
       unsigned long node_list_offset,
       unsigned long debug_spinlock_offset,
       unsigned long debug_rawlock_offset);
unsigned long futex_hash_bucket_result(unsigned long key_addr,
           unsigned long queues_addr,
           int hashbits,
           unsigned long bucket_stride,
           futex_hash_fn_t hash_fn);
int futex_dispatch_result(int op, unsigned long uaddr, uint32_t val,
     uint64_t timeout, unsigned long uaddr2,
     uint32_t val2, uint32_t val3, int fshared,
     futex_dispatch_wait_fn_t wait_fn,
     futex_dispatch_wake_fn_t wake_fn,
     futex_dispatch_requeue_fn_t requeue_fn,
     futex_dispatch_wake_op_fn_t wake_op_fn,
     futex_dispatch_invalid_fn_t invalid_fn);
int syscall_offload_should_schedule_result(int no_preempt, int tid,
        int need_resched, int runq_len,
        int is_sched_setaffinity);
# 27 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c" 2


# 1 "/home/holden/mckernel/kernel/include/kmalloc.h" 1
# 17 "/home/holden/mckernel/kernel/include/kmalloc.h"
# 1 "/home/holden/mckernel/kernel/include/cls.h" 1
# 18 "/home/holden/mckernel/kernel/include/cls.h"
# 1 "/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/owner-work/output/build/config.h" 1
# 19 "/home/holden/mckernel/kernel/include/cls.h" 2




struct kmalloc_cache_header {
 struct kmalloc_cache_header *next;
};

struct kmalloc_header {
 unsigned int front_magic;
 int cpu_id;
 union {
  struct list_head list;
  struct kmalloc_cache_header *cache;
 };
 int size;
 unsigned int end_magic;

};






extern ihk_spinlock_t cpu_status_lock;




typedef int (*smp_func_t)(int cpu_index, int nr_cpus, void *arg);
int smp_call_func(cpu_set_t *__cpu_set, smp_func_t __func, void *__arg);

struct smp_func_call_data {


 int nr_cpus;
 ihk_atomic_t cpus_left;

 smp_func_t func;
 void *arg;
};

struct smp_func_call_request {
 struct smp_func_call_data *sfcd;
 int cpu_index;
 int ret;
 struct list_head list;
};

struct backlog {
 struct list_head list;
 int (*func)(void *arg);
 void *arg;
};

struct cpu_local_var {

 struct list_head free_list;
 struct list_head remote_free_list;
 ihk_spinlock_t remote_free_list_lock;

 struct thread idle;
 struct process idle_proc;
 struct process_vm idle_vm;
 struct address_space idle_asp;

 ihk_spinlock_t runq_lock;
 unsigned long runq_irqstate;
 struct thread *current;
 void *kernel_mode_pf_regs;
 int prevpid;
 struct list_head runq;
 size_t runq_len;
 size_t runq_reserved;

 struct ihk_ikc_channel_desc *ikc2linux;

 struct resource_set *resource_set;

 int status;
 int fs;

 struct list_head pending_free_pages;

 unsigned int flags;

 ihk_spinlock_t migq_lock;
 struct list_head migq;
 int in_interrupt;
 int in_page_fault;
 ihk_atomic_t no_preempt;
 int timer_enabled;
 unsigned long nr_ctx_switches;
 int kmalloc_initialized;
 struct ihk_os_cpu_monitor *monitor;
 struct rusage_percpu *rusage;

 ihk_spinlock_t smp_func_req_lock;
 struct list_head smp_func_req_list;

 struct process_vm *on_fork_vm;

 ihk_spinlock_t backlog_lock;
 struct list_head backlog_list;


 void *uti_futex_resp;




} __attribute__((aligned(64)));

extern int cpu_local_var_initialized;

struct cpu_local_var *get_cpu_local_var(int id);
struct cpu_local_var *get_this_cpu_local_var(void);

int add_backlog(int (*func)(void *arg), void *arg);
void do_backlog(void);
# 18 "/home/holden/mckernel/kernel/include/kmalloc.h" 2


void *kmalloc_tracked(int size, ihk_mc_ap_flag flag, char *file, int line);
void kfree_tracked(void *ptr, char *file, int line);
void *kmalloc(int size, ihk_mc_ap_flag flag);
void kfree(void *ptr);
void *_kmalloc(int size, ihk_mc_ap_flag flag, char *file, int line);
void _kfree(void *ptr, char *file, int line);
void *__kmalloc(int size, ihk_mc_ap_flag flag);
void __kfree(void *ptr);

int _memcheck(void *ptr, char *msg, char *file, int line, int free);
int memcheckall(void);
int freecheck(int runcount);
void kmalloc_consolidate_free_list(void);




void kmalloc_cache_free(void *elem);
void kmalloc_cache_prealloc(struct kmalloc_cache_header *cache,
  size_t size, int nr_elem);
void *kmalloc_cache_alloc(struct kmalloc_cache_header *cache, size_t size);
# 30 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c" 2
# 1 "/home/holden/mckernel/kernel/include/cls.h" 1
# 31 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c" 2

# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/cpulocal.h" 1
# 29 "/home/holden/mckernel/arch/x86_64/kernel/include/cpulocal.h"
struct x86_cpu_local_variables {

 unsigned long processor_id;

 unsigned long apic_id;

 unsigned long kernel_stack;
 unsigned long user_stack;


 struct x86_desc_ptr gdt_ptr;
 unsigned short pad[3];

 uint64_t gdt[16];

 struct tss64 tss;

 unsigned long paniced;
 uint64_t panic_regs[21];

} __attribute__((packed));

struct x86_cpu_local_variables *get_x86_cpu_local_variable(int id);
struct x86_cpu_local_variables *get_x86_this_cpu_local(void);
void *get_x86_cpu_local_kstack(int id);
void *get_x86_this_cpu_kstack(void);
# 33 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c" 2
# 1 "/home/holden/mckernel/kernel/include/auxvec.h" 1




# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/arch/auxvec.h" 1
# 6 "/home/holden/mckernel/kernel/include/auxvec.h" 2
# 34 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c" 2
# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/hwcap.h" 1




static unsigned long arch_get_hwcap(void)
{
 return 0;
}
# 35 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c" 2
# 1 "/home/holden/mckernel/kernel/include/timer.h" 1
# 14 "/home/holden/mckernel/kernel/include/timer.h"
# 1 "/home/holden/mckernel/kernel/include/kmsg.h" 1
# 16 "/home/holden/mckernel/kernel/include/kmsg.h"
void kmsg_init(void);
void kputs(char *buf);
int kprintf(const char *format, ...);
# 15 "/home/holden/mckernel/kernel/include/timer.h" 2
# 24 "/home/holden/mckernel/kernel/include/timer.h"
# 1 "/home/holden/mckernel/kernel/include/amemcpy.h" 1
# 18 "/home/holden/mckernel/kernel/include/amemcpy.h"
static void memcpy_async_wait(unsigned long *notify)
{
 while (!*notify) {
  cpu_pause();
 }
}

int memcpy_async(unsigned long dest, unsigned long src,
                 unsigned long len, int wait, unsigned long *notify);
# 25 "/home/holden/mckernel/kernel/include/timer.h" 2
# 1 "/home/holden/mckernel/kernel/include/uio.h" 1



struct iovec
{
 void *iov_base;
 size_t iov_len;
};
# 17 "/home/holden/mckernel/kernel/include/uio.h"
size_t iov_length(const struct iovec *iov, unsigned long nr_segs);
# 26 "/home/holden/mckernel/kernel/include/timer.h" 2

# 1 "/home/holden/mckernel/lib/include/ctype.h" 1
# 18 "/home/holden/mckernel/lib/include/ctype.h"
extern unsigned char _ctype[];

unsigned char __ismask(int c);
int isalnum(int c);
int isalpha(int c);
int iscntrl(int c);
int isdigit(int c);
int isgraph(int c);
int islower(int c);
int isprint(int c);
int ispunct(int c);
int isspace(int c);
int isupper(int c);
int isxdigit(int c);
int isascii(int c);
int toascii(int c);
unsigned char __tolower(unsigned char c);
unsigned char __toupper(unsigned char c);
int tolower(int c);
int toupper(int c);
# 28 "/home/holden/mckernel/kernel/include/timer.h" 2


# 1 "/home/holden/mckernel/kernel/include/affinity.h" 1
# 51 "/home/holden/mckernel/kernel/include/affinity.h"
unsigned long CPU_SET(unsigned long cpu, cpu_set_t *cpusetp);
int CPU_ISSET(unsigned long cpu, const cpu_set_t *cpusetp);
void CPU_ZERO(cpu_set_t *cpusetp);
unsigned long CPU_SET_S(unsigned long cpu, unsigned long setsize,
   cpu_set_t *cpusetp);
int CPU_ISSET_S(unsigned long cpu, unsigned long setsize,
  const cpu_set_t *cpusetp);
void CPU_ZERO_S(unsigned long setsize, cpu_set_t *cpusetp);
# 31 "/home/holden/mckernel/kernel/include/timer.h" 2




struct timer {
 uint64_t timeout;
 struct waitq processes;
 struct list_head list;
 struct thread *thread;
};

uint64_t schedule_timeout(uint64_t timeout);

void init_timers(void);
void wake_timers_loop(void);
# 36 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c" 2
# 1 "/home/holden/mckernel/kernel/include/mman.h" 1
# 18 "/home/holden/mckernel/kernel/include/mman.h"
# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/arch/mman.h" 1
# 19 "/home/holden/mckernel/kernel/include/mman.h" 2
# 80 "/home/holden/mckernel/kernel/include/mman.h"
extern int sysctl_overcommit_memory;

unsigned long round_up(unsigned long x, unsigned long y);
unsigned long round_down(unsigned long x, unsigned long y);
# 37 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c" 2
# 1 "/home/holden/mckernel/kernel/include/xpmem.h" 1
# 22 "/home/holden/mckernel/kernel/include/xpmem.h"
int xpmem_open(const char *pathname,
        int flags, ihk_mc_user_context_t *ctx);
int xpmem_openat(const char *pathname,
   int flags, ihk_mc_user_context_t *ctx);
int xpmem_remove_process_memory_range(struct process_vm *vm,
 struct vm_range *vmr);
int xpmem_fault_process_memory_range(struct process_vm *vm,
 struct vm_range *vmr, unsigned long vaddr, uint64_t reason);
int xpmem_update_process_page_table(struct process_vm *vm,
 struct vm_range *vmr);

struct xpmem_attachment {
 ihk_rwspinlock_t at_lock;
 unsigned long vaddr;
 unsigned long at_vaddr;
 size_t at_size;
 struct vm_range *at_vmr;
 int flags;
 ihk_atomic_t refcnt;
 struct xpmem_access_permit *ap;
 struct list_head att_list;
 struct process_vm *vm;
};
# 38 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c" 2
# 1 "/home/holden/mckernel/kernel/include/shm.h" 1
# 18 "/home/holden/mckernel/kernel/include/shm.h"
# 1 "/home/holden/mckernel/arch/x86_64/kernel/include/arch/shm.h" 1
# 21 "/home/holden/mckernel/arch/x86_64/kernel/include/arch/shm.h"
struct ipc_perm {
 key_t key;
 uid_t uid;
 gid_t gid;
 uid_t cuid;
 gid_t cgid;
 uint16_t mode;
 uint8_t padding[2];
 uint16_t seq;
 uint8_t padding2[22];
};

struct shmid_ds {
 struct ipc_perm shm_perm;
 size_t shm_segsz;
 time_t shm_atime;
 time_t shm_dtime;
 time_t shm_ctime;
 pid_t shm_cpid;
 pid_t shm_lpid;
 uint64_t shm_nattch;
 uint8_t padding[12];
 int init_pgshift;
};
# 19 "/home/holden/mckernel/kernel/include/shm.h" 2

enum {

 IPC_PRIVATE = 0,


 IPC_CREAT = 01000,
 IPC_EXCL = 02000,

 SHM_HUGETLB = 04000,
 SHM_RDONLY = 010000,
 SHM_RND = 020000,
 SHM_REMAP = 040000,
 SHM_EXEC = 0100000,


 SHM_DEST = 01000,
 SHM_LOCKED = 02000,


 IPC_RMID = 0,
 IPC_SET = 1,
 IPC_STAT = 2,
 IPC_INFO = 3,

 SHM_LOCK = 11,
 SHM_UNLOCK = 12,
 SHM_STAT = 13,
 SHM_INFO = 14,
};

struct shmlock_user;

struct shmobj {
 struct memobj memobj;
 int index;
 int pgshift;
 size_t real_segsz;
 struct shmlock_user * user;
 struct shmid_ds ds;
 struct list_head page_list;
 ihk_spinlock_t page_list_lock;
 struct list_head chain;
};

struct shminfo {
 uint64_t shmmax;
 uint64_t shmmin;
 uint64_t shmmni;
 uint64_t shmseg;
 uint64_t shmall;
 uint8_t padding[32];
};

struct shm_info {
 int32_t used_ids;
 uint8_t padding[4];
 uint64_t shm_tot;
 uint64_t shm_rss;
 uint64_t shm_swp;
 uint64_t swap_attempts;
 uint64_t swap_successes;
};

struct shmlock_user {
 uid_t ruid;
 int padding;
 size_t locked;

 struct list_head chain;
};

extern ihk_spinlock_t shmlock_users_lock_body;

void shmlock_users_lock(void);
void shmlock_users_unlock(void);

void shmobj_list_lock(void);
void shmobj_list_unlock(void);
int shmobj_create_indexed(struct shmid_ds *ds, struct shmobj **objp);
void shmlock_user_free(struct shmlock_user *user);
int shmlock_user_get(uid_t ruid, struct shmlock_user **userp);
struct shmobj *to_shmobj(struct memobj *memobj);
# 39 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c" 2
# 1 "/home/holden/mckernel/kernel/include/rusage_private.h" 1





# 1 "/home/holden/mckernel-work/host-preparation/p-m06-matched-guest-build-binding-20261022-1/full-image-attempt-1/owner-work/output/build/config.h" 1
# 7 "/home/holden/mckernel/kernel/include/rusage_private.h" 2



# 1 "/home/holden/mckernel/kernel/include/rusage.h" 1





# 1 "/home/holden/mckernel/ihk/linux/include/ihk/ihk_rusage.h" 1






enum ihk_os_pgsize {
 IHK_OS_PGSIZE_4KB,
 IHK_OS_PGSIZE_64KB,
 IHK_OS_PGSIZE_2MB,
 IHK_OS_PGSIZE_32MB,
 IHK_OS_PGSIZE_1GB,
 IHK_OS_PGSIZE_16GB,
 IHK_OS_PGSIZE_512MB,
 IHK_OS_PGSIZE_4TB,
 IHK_MAX_NUM_PGSIZES
};

static inline __attribute__((always_inline,unused)) __attribute__((no_instrument_function)) long rusage_pgtype_to_pgsize(enum ihk_os_pgsize pgtype)
{
 long ret;

 switch (pgtype) {
 case IHK_OS_PGSIZE_4KB:
  ret = 1UL << 12;
  break;
 case IHK_OS_PGSIZE_64KB:
  ret = 1UL << 16;
  break;
 case IHK_OS_PGSIZE_2MB:
  ret = 1UL << 21;
  break;
 case IHK_OS_PGSIZE_32MB:
  ret = 1UL << 25;
  break;
 case IHK_OS_PGSIZE_1GB:
  ret = 1UL << 30;
  break;
 case IHK_OS_PGSIZE_16GB:
  ret = 1UL << 34;
  break;
 case IHK_OS_PGSIZE_512MB:
  ret = 1UL << 29;
  break;
 case IHK_OS_PGSIZE_4TB:
  ret = 1UL << 42;
  break;
 default:
  ret = -1;
 }

 return ret;
}

struct ihk_os_rusage {
 unsigned long memory_stat_rss[IHK_MAX_NUM_PGSIZES];
 unsigned long memory_stat_mapped_file[IHK_MAX_NUM_PGSIZES];
 unsigned long memory_max_usage;
 unsigned long memory_kmem_usage;
 unsigned long memory_kmem_max_usage;
 unsigned long memory_numa_stat[1024];
 unsigned long cpuacct_stat_system;
 unsigned long cpuacct_stat_user;
 unsigned long cpuacct_usage;
 unsigned long cpuacct_usage_percpu[1024];
 int num_threads;
 int max_num_threads;
};
# 7 "/home/holden/mckernel/kernel/include/rusage.h" 2



extern struct rusage_global rusage;

struct rusage_percpu {
 unsigned long user_tsc;
 unsigned long system_tsc;
};

struct rusage_global {

 long memory_stat_rss[IHK_MAX_NUM_PGSIZES];
 long memory_stat_mapped_file[IHK_MAX_NUM_PGSIZES];
 long rss_current;
 unsigned long memory_max_usage;
 unsigned long max_num_threads;
 unsigned long num_threads;
 unsigned long memory_kmem_usage;
 unsigned long memory_kmem_max_usage;
 unsigned long memory_numa_stat[1024];


 struct rusage_percpu cpu[1024];


 unsigned long total_memory;
 unsigned long total_memory_usage;
 unsigned long total_memory_max_usage;

 unsigned long total_memory_max_usage_old;


 unsigned long num_numa_nodes;
 unsigned long num_processors;
 unsigned long ns_per_tsc;
};
# 11 "/home/holden/mckernel/kernel/include/rusage_private.h" 2
# 1 "/home/holden/mckernel/ihk/linux/include/ihk/ihk_monitor.h" 1
# 12 "/home/holden/mckernel/ihk/linux/include/ihk/ihk_monitor.h"
struct ihk_os_cpu_monitor {
 int status;
# 25 "/home/holden/mckernel/ihk/linux/include/ihk/ihk_monitor.h"
 int status_bak;
 unsigned long counter;
 unsigned long ocounter;
};

struct ihk_os_monitor {
 unsigned long num_processors;
 unsigned long reserve[128];
 struct ihk_os_cpu_monitor cpu[0];
};




enum ihk_os_eventfd_type {
 IHK_OS_EVENTFD_TYPE_OOM = 0,
 IHK_OS_EVENTFD_TYPE_STATUS = 2,
 IHK_OS_EVENTFD_TYPE_KMSG = 101,


};
# 12 "/home/holden/mckernel/kernel/include/rusage_private.h" 2
# 20 "/home/holden/mckernel/kernel/include/rusage_private.h"
extern void eventfd(int type);

int rusage_pgsize_to_pgtype(size_t pgsize);
void rusage_total_memory_add(unsigned long size);
unsigned long rusage_get_total_memory(void);
unsigned long rusage_get_free_memory(void);
unsigned long rusage_get_usage_memory(void);

void rusage_rss_add(unsigned long size);
void rusage_rss_sub(unsigned long size);

void memory_stat_rss_add(unsigned long size, int pgsize);
void memory_stat_rss_sub(unsigned long size, int pgsize);
void rusage_memory_stat_mapped_file_add(unsigned long size, int pgsize);
void rusage_memory_stat_mapped_file_sub(unsigned long size, int pgsize);

int rusage_memory_stat_add(struct vm_range *range, uintptr_t phys,
      unsigned long size, int pgsize);
int rusage_memory_stat_add_with_page(struct vm_range *range, uintptr_t phys,
         unsigned long size, int pgsize,
         struct page *page);

void rusage_memory_stat_sub(struct memobj *memobj, unsigned long size,
       int pgsize);

void rusage_kmem_add(unsigned long size);
void rusage_kmem_sub(unsigned long size);

void rusage_numa_add(int numa_id, unsigned long size);
void rusage_numa_sub(int numa_id, unsigned long size);

int rusage_check_oom(int numa_id, unsigned long pages, int is_user);
int rusage_check_overmap(size_t len, int pgshift);
void rusage_page_add(int numa_id, unsigned long pages, int is_user);
void rusage_page_sub(int numa_id, unsigned long pages, int is_user);

void rusage_num_threads_inc(void);
void rusage_num_threads_dec(void);
# 100 "/home/holden/mckernel/kernel/include/rusage_private.h"
extern struct rusage_global rusage;
# 40 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c" 2
# 1 "/home/holden/mckernel/lib/include/ihk/monitor.h" 1





extern struct ihk_os_monitor *monitor;
# 41 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c" 2
# 78 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


extern const int process_dump_tree_enabled;
_Static_assert((0) == 0, "process_dump_tree_enabled selected supported configuration");
# 80 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 84 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

extern struct thread *arch_switch_context(struct thread *prev, struct thread *next);
extern long alloc_debugreg(struct thread *proc);
extern void save_debugreg(unsigned long *debugreg);
extern void restore_debugreg(unsigned long *debugreg);
extern void clear_debugreg(void);
extern void clear_single_step(struct thread *proc);

int vm_range_insert(struct process_vm *vm, struct vm_range *newrange);




static struct vm_range *vm_range_find(struct process_vm *vm,
  unsigned long addr);

int copy_user_ranges(struct process_vm *vm, struct process_vm *orgvm);
# 100 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
extern void __runq_add_proc(struct thread *proc, int cpu_id);
extern void lapic_timer_enable(unsigned int clocks);
extern void lapic_timer_disable();


extern const struct timer_runtime_offsets process_timer_runtime_offsets;
# 125 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


unsigned long process_timer_spin_lock_bridge(unsigned long lock_addr);
# 127 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void process_timer_spin_unlock_bridge(unsigned long lock_addr,
          unsigned long irqstate);
# 133 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void process_timer_lapic_enable_bridge(unsigned int clocks);
# 138 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void process_timer_lapic_disable_bridge(void);
# 143 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"



extern int num_processors;
extern ihk_spinlock_t cpuid_head_lock;
int ptrace_detach(int pid, int data);
extern void procfs_create_thread(struct thread *);
extern void procfs_delete_thread(struct thread *);

static int free_process_memory_range(struct process_vm *vm,
     struct vm_range *range);
struct address_space *create_address_space(struct resource_set *res, int n);
void hold_address_space(struct address_space *asp);
void detach_address_space(struct address_space *asp, int pid);
int init_process_vm(struct process *owner, struct address_space *asp,
      struct process_vm *vm);
struct resource_set *new_resource_set(void);
void proc_init(void);
static void free_thread_pages(struct thread *thread);
void process_free_thread_pages_bridge(void *thread);
int update_process_page_table(struct process_vm *vm,
         struct vm_range *range, uint64_t phys,
         enum ihk_mc_pt_attribute flag);
int split_process_memory_range(struct process_vm *vm, struct vm_range *range,
          uintptr_t addr, struct vm_range **splitp);
# 170 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
const char *const process_tracked_allocator_source_file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c";
# 171 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 172 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

extern const int process_mckfd_free_bridge_source_line;
void process_mckfd_free_bridge(struct mckfd *fdp);
# 173 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_mcs_writer_lock_bridge(unsigned long lock_addr, void *node);
# 179 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_mcs_writer_unlock_bridge(unsigned long lock_addr, void *node);
# 185 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_mcs_reader_lock_bridge(unsigned long lock_addr, void *node);
# 191 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_mcs_reader_unlock_bridge(unsigned long lock_addr, void *node);
# 197 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_hold_thread_bridge(void *thread);
# 202 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_ptrace_mcs_lock_noirq_bridge(unsigned long lock_addr, void *node);
# 209 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

void process_ptrace_mcs_unlock_noirq_bridge(unsigned long lock_addr, void *node);
# 215 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

int process_ptrace_alloc_debugreg_bridge(void *thread);
# 220 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

void process_ptrace_clear_single_step_bridge(void *thread);
# 225 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

void process_ptrace_hold_thread_bridge(void *thread);
# 230 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"







_Static_assert(0x0 == 0,
    "Rust process debug flags must match C DDEBUG_DEFAULT");
_Static_assert(__builtin_strcmp("/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c", "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c") == 0,
    "Rust process debug filename must match actual C __FILE__");
extern struct ddebug process_ptrace_traceme_debug[3];
# 238 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_ptrace_traceme_log_bridge(int event, int pid, unsigned long value, int error);
# 249 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 247 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





extern const int process_policy_free_bridge_source_line;
void process_policy_free_bridge(void *policy);
# 255 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


extern const int process_optional_free_bridge_source_line;
void process_optional_free_bridge(void *ptr);
# 260 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


int process_default_ncpus_bridge(void);
# 267 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"




extern struct ddebug process_create_cpu_debug;
# 277 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_create_cpu_log_bridge(int event, int pid, int cpu);
# 283 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_spin_init_bridge(unsigned long lock_addr);
void process_rwlock_init_bridge(unsigned long lock_addr);
void process_waitq_init_bridge(unsigned long waitq_addr);
# 305 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_user_context_modify_bridge(void *, int, unsigned long);







void process_mcs_lock_init_bridge(unsigned long lock_addr);
# 323 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_vm_rwspin_init_bridge(unsigned long lock_addr);
# 332 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_vm_init_numa_log_bridge(int numa_id);
# 337 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


extern const int process_alloc_bridge_source_line;
void *process_alloc_bridge(unsigned long size, unsigned long flags);
# 342 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void *process_pt_create_bridge(unsigned long flags);
unsigned long process_spin_lock_bridge(unsigned long lock_addr);
void process_spin_unlock_bridge(unsigned long lock_addr,
    unsigned long irqstate);
void process_sched_noirq_lock_bridge(unsigned long lock_addr);
void process_sched_noirq_unlock_bridge(unsigned long lock_addr);
void process_rw_read_lock_bridge(unsigned long lock_addr);
void process_rw_read_unlock_bridge(unsigned long lock_addr);
void process_rw_write_lock_bridge(unsigned long lock_addr);
void process_rw_write_unlock_bridge(unsigned long lock_addr);
# 403 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_sched_waitq_init_bridge(unsigned long waitq_addr);
void process_sched_waitq_prepare_bridge(unsigned long waitq_addr,
     unsigned long entry_addr,
     int status);
void process_sched_waitq_finish_bridge(unsigned long waitq_addr,
           unsigned long entry_addr);
# 435 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
extern struct ddebug process_sched_migrate_debug;
# 441 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 450 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


int process_sched_vector_bridge(int vector_key);
void process_sched_interrupt_bridge(int cpu, int vector);
void process_sched_schedule_bridge(void);
unsigned long process_sched_cpu_local_bridge(int cpu_id);
void process_sched_waitq_wakeup_bridge(unsigned long waitq_addr);
# 485 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_sched_do_migrate_log_bridge(unsigned long thread_addr,
      int tid, int old_cpu_id,
      int new_cpu_id);
# 489 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 511 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_release_thread_profile_bridge(void *thread, void *proc);
# 520 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_procfs_delete_thread_bridge(void *thread);
void process_destroy_thread_bridge(void *thread);
void process_release_vm_bridge(void *vm);
int process_release_vm_checked_bridge(void *vm);
void process_flush_vm_bridge(void *vm);
# 555 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_free_all_ranges_bridge(void *vm);
# 558 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


extern const int process_free_vm_bridge_source_line;
void process_free_vm_bridge(void *vm);
# 563 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





extern struct list_head resource_set_list;
extern mcs_rwlock_lock_t resource_set_lock;
extern ihk_spinlock_t runq_reservation_lock;
# 564 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





extern int idle_halt;
extern int allow_oversubscribe;
extern int time_sharing;
# 571 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 613 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void init_process(struct process *proc, struct process *parent);
# 728 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_pt_destroy_bridge(void *page_table);
# 731 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 748 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_release_address_space_action_bridge(void *asp);
# 751 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 764 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
int process_init_process_public_bridge(void *proc, void *parent);
# 768 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_proc_init_panic_bridge(void);
# 773 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 785 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
extern const int process_create_thread_alloc_pages_source_line;
void *process_create_thread_alloc_pages_bridge(int npages, unsigned long flags);
# 790 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"



void *process_create_thread_address_space_bridge(int nslots);
void process_create_thread_release_address_space_bridge(void *asp);
int process_create_thread_init_process_bridge(void *proc, void *parent);
int process_create_thread_init_vm_bridge(void *owner, void *asp,
     void *vm);
void process_create_thread_init_user_bridge(void *thread,
 unsigned long stack_top, unsigned long user_pc,
 unsigned long user_sp);
# 823 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 993 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
struct process_clone_config {
    int stack_pages;
    size_t page_size;
    int page_align;
    unsigned long nowait;
    int kernel,ss_disable,sp_reg,pc_reg;
    const char *file;
    int lines[5];
    struct ddebug *debug[5];
    void (*modify_context)(void *,int,unsigned long);
    int (*copy_ranges)(struct process_vm *,struct process_vm *);
};
# 1005 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
static struct ddebug __attribute__((aligned(8))) __attribute__((section("__verbose")))
process_clone_vm_debug = {
    .file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c", .func = "clone_thread",
    .line = 1098, .flags = 0x0,
};
static struct ddebug __attribute__((aligned(8))) __attribute__((section("__verbose")))
process_clone_ranges_debug = {
    .file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c", .func = "clone_thread",
    .line = 1118, .flags = 0x0,
};
static struct ddebug __attribute__((aligned(8))) __attribute__((section("__verbose")))
process_clone_ranges_ok_debug = {
    .file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c", .func = "clone_thread",
    .line = 1176, .flags = 0x0,
};
static struct ddebug __attribute__((aligned(8))) __attribute__((section("__verbose")))
process_clone_sigcommon_debug = {
    .file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c", .func = "clone_thread",
    .line = 1193, .flags = 0x0,
};
static struct ddebug __attribute__((aligned(8))) __attribute__((section("__verbose")))
process_clone_sigshared_debug = {
    .file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c", .func = "clone_thread",
    .line = 1208, .flags = 0x0,
};
# 1030 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 1030 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
const struct process_clone_config process_clone_config = {
    .stack_pages=32, .page_size=(1UL << 12),
    .page_align=0, .nowait=0x000002,
    .kernel=0, .ss_disable=2,
    .sp_reg=IHK_UCR_STACK_POINTER, .pc_reg=IHK_UCR_PROGRAM_COUNTER,
    .file="/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c", .lines={1002,1063,1083,1144,1153},
    .debug={&process_clone_vm_debug,&process_clone_ranges_debug,
        &process_clone_ranges_ok_debug,&process_clone_sigcommon_debug,
        &process_clone_sigshared_debug},
    .modify_context=process_user_context_modify_bridge,
    .copy_ranges=copy_user_ranges,
};
# 1042 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
struct thread *process_clone_thread_body_result(struct thread *,unsigned long,
        unsigned long,int,const struct process_clone_config *);
struct thread *clone_thread(struct thread *org,unsigned long pc,unsigned long sp,
        int clone_flags);
# 1359 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 1306 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 1407 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
struct copy_args {
 struct process_vm *new_vm;
 unsigned long new_vrflag;
 struct vm_range *range;


 intptr_t fault_addr;
};
# 1417 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
static struct ddebug __attribute__((aligned(8))) __attribute__((section("__verbose")))
process_copy_pte_found_debug = {
    .file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c", .func = "copy_user_pte",
    .line = 1460, .flags = 0x0,
};
static struct ddebug __attribute__((aligned(8))) __attribute__((section("__verbose")))
process_copy_pte_size_debug = {
    .file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c", .func = "copy_user_pte",
    .line = 1461, .flags = 0x0,
};
static struct ddebug __attribute__((aligned(8))) __attribute__((section("__verbose")))
process_copy_pte_allocated_debug = {
    .file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c", .func = "copy_user_pte",
    .line = 1471, .flags = 0x0,
};
static struct ddebug __attribute__((aligned(8))) __attribute__((section("__verbose")))
process_copy_pte_zeroed_debug = {
    .file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c", .func = "copy_user_pte",
    .line = 1494, .flags = 0x0,
};
static struct ddebug __attribute__((aligned(8))) __attribute__((section("__verbose")))
process_copy_pte_copied_debug = {
    .file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c", .func = "copy_user_pte",
    .line = 1496, .flags = 0x0,
};
static struct ddebug __attribute__((aligned(8))) __attribute__((section("__verbose")))
process_copy_pte_installed_debug = {
    .file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c", .func = "copy_user_pte",
    .line = 1514, .flags = 0x0,
};
# 1447 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
struct process_copy_entry_config {
    size_t page_size;
    int page_shift;
    unsigned long nowait;
    int user_category;
    int kernel_category;
    unsigned long wipe_on_fork;
    const char *file;
    int alloc_line;
    int free_line;
    int visit_flags;
    struct ddebug *found_debug;
    struct ddebug *size_debug;
    struct ddebug *allocated_debug;
    struct ddebug *zeroed_debug;
    struct ddebug *copied_debug;
    struct ddebug *installed_debug;
};
# 1465 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
const struct process_copy_entry_config process_copy_entry_config = {
    .page_size = (1UL << 12), .page_shift = 12,
    .nowait = 0x000002, .user_category = 1,
    .kernel_category = 0, .wipe_on_fork = 0x80000000,
    .file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c", .alloc_line = 1464, .free_line = 1520,
    .visit_flags = VPTEF_SKIP_NULL,
    .found_debug = &process_copy_pte_found_debug,
    .size_debug = &process_copy_pte_size_debug,
    .allocated_debug = &process_copy_pte_allocated_debug,
    .zeroed_debug = &process_copy_pte_zeroed_debug,
    .copied_debug = &process_copy_pte_copied_debug,
    .installed_debug = &process_copy_pte_installed_debug,
};
# 1478 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

int process_copy_user_pte_body_result(void *,void *,pte_t *,void *,int,
        size_t,int,unsigned long,int,int,unsigned long,const char *,int,int,
        struct ddebug *,struct ddebug *,struct ddebug *,
        struct ddebug *,struct ddebug *,struct ddebug *);
int copy_user_pte(void *arg0,page_table_t src_pt,pte_t *src_ptep,
        void *pgaddr,int pgshift);
# 1594 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 1525 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

struct vm_range *process_add_range_alloc_bridge(unsigned long size);
void process_add_range_free_bridge(struct vm_range *range);
int process_add_range_insert_bridge(struct process_vm *vm,
        struct vm_range *range);
int process_visit_pte_range_bridge(void *page_table, unsigned long start,
       unsigned long end, int pgshift, int flags,
       void *visit_fn, void *arg);
int process_memory_range_free_bridge(struct process_vm *vm,
         struct vm_range *range);


int copy_user_ranges(struct process_vm *,struct process_vm *);
# 1573 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


unsigned long process_update_page_table_attr_bridge(unsigned long flag,
  unsigned long fault, void *ptep);
# 1576 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





int process_update_page_table_set_range_bridge(void *page_table,
  struct process_vm *vm, unsigned long start, unsigned long end,
  unsigned long phys, unsigned long attr, int pgshift,
  struct vm_range *range, int flags);
# 1585 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void process_update_page_table_log_bridge(int error);
# 1591 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 1609 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
int process_split_shm_lookup_page_bridge(struct memobj *obj, long off,
  int p2align, uintptr_t *physp, unsigned long *pflag);
# 1610 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void *process_split_shm_phys_to_page_bridge(unsigned long phys);
# 1615 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





int process_split_shm_update_page_bridge(struct memobj *obj,
  void *page_table, void *page, void *vaddr);
# 1621 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





extern const int process_split_range_alloc_source_line;
struct vm_range *process_split_range_alloc_bridge(unsigned long size,
  unsigned long flags);
# 1627 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void process_split_range_alloc_log_bridge(struct process_vm *vm,
  struct vm_range *range, unsigned long addr, void *splitp);
# 1635 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void process_split_range_publish_log_bridge(int error);
# 1641 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





int process_split_range_pt_split_bridge(void *page_table,
  struct process_vm *vm, struct vm_range *range, void *addr);
# 1647 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void process_split_range_pt_log_bridge(int error);
# 1653 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void process_split_shm_log_bridge(int event, int error);
# 1669 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





unsigned long process_split_page_pgshift_offset_bridge(void);
# 1676 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


int process_split_range_insert_bridge(struct process_vm *vm,
  struct vm_range *range);
# 1679 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"






extern struct ddebug process_remaining_range_debug[8];
# 1695 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_split_range_public_log_bridge(int event, struct process_vm *vm,
  struct vm_range *range, unsigned long addr,
  struct vm_range **splitp, struct vm_range *newrange, int error);
# 1719 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 1701 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 1816 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
extern const int process_range_kfree_bridge_source_line;
void process_range_kfree_bridge(struct vm_range *range);
# 1819 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_join_range_log_bridge(int event, struct process_vm *vm,
  struct vm_range *surviving, struct vm_range *merging, int error);
# 1834 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 1862 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
int process_free_range_page_size_bridge(size_t current, size_t *nextp);
# 1865 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void *process_free_range_phys_to_virt_bridge(unsigned long phys);
# 1870 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


extern const int process_free_range_pages_source_line;

extern struct ddebug process_free_range_body_debug[3];
# 1879 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 1880 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 1872 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





int process_free_range_clear_main_bridge(struct process_vm *vm,
  unsigned long start, unsigned long end);
# 1888 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_free_range_noirq_lock_bridge(unsigned long lock_addr);
# 1893 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_free_range_noirq_unlock_bridge(unsigned long lock_addr);
# 1898 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


int process_free_range_pt_free_bridge(void *page_table,
  struct process_vm *vm, unsigned long start, unsigned long end,
  void *memobj);
# 1906 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


int process_free_range_pt_clear_bridge(void *page_table,
  struct process_vm *vm, unsigned long start, unsigned long end);
# 1913 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 1957 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 1987 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 1993 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void process_memory_range_free_log_bridge(struct process_vm *vm,
       struct vm_range *range,
       int error);
# 2005 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_flush_memory_log_bridge(struct process_vm *vm,
         struct vm_range *range,
         int error);
# 2014 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_flush_memory_debug_bridge(struct process_vm *vm, int event);
# 2020 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





int process_remove_range_split_bridge(struct process_vm *vm,
          struct vm_range *range,
          unsigned long addr,
          struct vm_range **splitp);
# 2028 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void process_remove_range_xpmem_bridge(struct process_vm *vm,
           struct vm_range *range);
# 2034 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void process_remove_range_log_bridge(int event, struct process_vm *vm,
         unsigned long start,
         unsigned long end,
         struct vm_range *range,
         int error);
# 2066 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2091 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
extern struct ddebug process_vm_range_insert_debug;
# 2097 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2114 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2132 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
extern struct ddebug process_remaining_range_scheduler_debug[18];
# 2152 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_range_public_log_bridge(int event, struct process_vm *vm,
         struct vm_range *range,
         unsigned long start,
         unsigned long end, int error);
# 2208 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2179 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"






struct memset_smp_req {
 unsigned long phys;
 size_t len;
 int val;
};


void *process_memset_smp_phys_to_virt_bridge(unsigned long phys);
# 2192 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"







extern const int process_memset_smp_fast_word_pattern;
_Static_assert((1) == 1, "process_memset_smp_fast_word_pattern selected supported configuration");
# 2199 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2202 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_memset_smp_memset_bridge(void *addr, int value, size_t len);
# 2197 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void process_memset_smp_log_bridge(int event, int cpu_index,
  int nr_cpus, unsigned long phys, size_t len,
  unsigned long start, unsigned long end);
# 2211 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2230 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
unsigned long process_memset_smp_virt_to_phys_bridge(void *addr);
# 2230 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





int process_memset_smp_call_bridge(void *cpu_set, void *handler,
  void *arg);
# 2236 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2255 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
extern const int process_add_range_alloc_bridge_source_line;
struct vm_range *process_add_range_alloc_bridge(unsigned long size);
# 2258 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


extern const int process_add_range_free_bridge_source_line;
void process_add_range_free_bridge(struct vm_range *range);
# 2263 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


int process_add_range_insert_bridge(struct process_vm *vm,
        struct vm_range *range);
# 2266 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





int process_add_range_update_bridge(struct process_vm *vm,
        struct vm_range *range,
        unsigned long phys,
        unsigned long attr);
# 2274 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void process_add_range_remove_bridge(struct process_vm *vm,
         unsigned long start,
         unsigned long end);
# 2281 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void process_add_range_mark_xpmem_bridge(struct vm_range *range);
# 2289 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2291 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"



void (* const process_add_range_arch_memclear_callback)(void *, unsigned long) = ((void *)0);
# 2296 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_add_range_memclear_bridge(unsigned long phys,
           unsigned long bytes);
# 2307 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2296 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"






extern struct ddebug process_remaining_memory_log_debug[5];
# 2309 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_add_range_log_bridge(int event, int rc,
      unsigned long start,
      unsigned long end);
# 2341 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2326 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2381 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
unsigned long process_change_prot_attr_bridge(unsigned long flag,
  unsigned long fault, void *ptep);
# 2382 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





int process_change_prot_pt_change_bridge(void *page_table,
  unsigned long start, unsigned long end,
  unsigned long clrattr, unsigned long setattr);
# 2390 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void process_change_prot_public_log_bridge(int event,
  struct process_vm *vm, struct vm_range *range,
  unsigned long protflag, int error);
# 2414 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2431 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
struct rfp_args {
 off_t off;
 uintptr_t start;
 struct memobj *memobj;
};
# 2440 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
const char *const process_remap_free_file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c";
const int process_remap_free_line = 2469;
# 2442 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

extern struct ddebug process_remap_one_page_entry_debug;
# 2447 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

extern struct ddebug process_remap_one_page_rss_debug;
# 2452 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

extern struct ddebug process_remap_one_page_exit_debug;
# 2457 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2500 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2502 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


int process_visit_pte_range_bridge(void *page_table, unsigned long start,
       unsigned long end, int pgshift, int flags,
       void *visit_fn, void *arg);
# 2509 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void process_remap_range_log_bridge(int event, struct process_vm *vm,
        struct vm_range *range, unsigned long start,
        unsigned long end, long off,
        int old_pgshift, int error);
# 2527 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2556 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
struct sync_args {
 struct memobj *memobj;
};




extern struct ddebug process_sync_one_page_entry_debug;
# 2567 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

extern struct ddebug process_sync_one_page_exit_debug;
# 2572 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2614 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2688 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_invalidate_range_log_bridge(struct process_vm *vm,
  struct vm_range *range, unsigned long start, unsigned long end,
  int error);
# 2683 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

struct invalidate_args {
 struct vm_range *range;
};


int process_pte_is_null_bridge(void *ptep);
# 2692 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


int process_pte_is_fileoff_bridge(void *ptep, size_t pgsize);
# 2697 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


uintptr_t process_pte_get_phys_bridge(void *ptep);
# 2708 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void *process_phys_to_page_bridge(uintptr_t phys);
# 2711 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


long process_page_offset_bridge(void *page);
# 2716 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_pte_make_fileoff_bridge(long off, size_t pgsize,
         void *ptep);
# 2722 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_pte_xchg_bridge(void *ptep, void *valp);
# 2727 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_flush_tlb_single_bridge(unsigned long addr);
# 2732 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


int process_pgsize_to_tbllv_bridge(size_t pgsize);
# 2737 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


size_t process_tbllv_to_contpgsize_bridge(int level);
# 2742 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


int process_page_unmap_bridge(void *page);
# 2747 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_panic_bridge(const char *message);
# 2749 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





int process_memobj_invalidate_page_bridge(struct memobj *memobj,
       uintptr_t phys,
       size_t pgsize);
# 2759 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_invalidate_one_page_log_bridge(void *arg0,
  void *page_table, void *ptep, unsigned long pte_value,
  void *pgaddr, int pgshift, int error);
# 2769 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2832 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
int process_page_fault_cow_dirty_permission_body_result(enum ihk_mc_pt_attribute *);



void process_page_fault_cow_copy_body_result(void *, uintptr_t, size_t);
# 2840 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
const char *const process_page_fault_cow_alloc_file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c";
const int process_page_fault_cow_alloc_line = 3145;
# 2842 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
int process_page_fault_cow_allocate_body_result(struct process_vm *, struct vm_range *,
        struct page *, size_t, int, uintptr_t, uint64_t, void **, int *);
# 2845 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2848 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
const char *const process_page_fault_anon_alloc_file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c";
# 2849 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
extern const int process_page_fault_anon_alloc_line;
int process_page_fault_anon_allocate_body_result(struct process_vm *, struct vm_range *,
        uintptr_t, uint64_t, pte_t **, void **, size_t *, int *, void **, int *);
# 2853 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


unsigned long process_page_fault_mapping_state_body_result(struct vm_range *, uintptr_t,
        unsigned long, uint64_t, pte_t *, struct page **);




extern struct ddebug process_page_fault_profile_path_debug;
# 2865 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

extern struct ddebug process_page_fault_entry_debug;
# 2870 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_page_fault_entry_log_body_result(struct process_vm *, struct vm_range *,
        uintptr_t, uint64_t);
# 2873 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


unsigned long process_page_fault_shared_permission_body_result(struct vm_range *, unsigned long);




extern struct ddebug process_page_fault_pte_state_debug;
# 2884 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_page_fault_pte_state_log_bridge(pte_t *, size_t);
# 2886 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"



extern struct ddebug process_page_fault_page_state_debug;
# 2893 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_page_fault_page_state_log_bridge(struct page *);
# 2895 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2831 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"



extern struct ddebug process_page_fault_prepare_bounds_debug;
# 2838 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
int process_page_fault_prepare_body_result(struct process_vm *, struct vm_range *,
        uintptr_t, uint64_t, pte_t **, void **, size_t *, int *, int *);
# 2841 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"



int process_page_fault_memobj_get_body_result(struct vm_range *, void *, uintptr_t,
        pte_t *, size_t, int, uintptr_t *, unsigned long *, int *);



int process_page_fault_cow_classify_body_result(struct vm_range *, uint64_t, struct page *);




extern struct ddebug process_page_fault_cow_rss_add_debug;
# 2858 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

extern struct ddebug process_page_fault_cow_rss_sub_debug;
# 2863 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_page_fault_cow_commit_body_result(struct vm_range *,uintptr_t *,
        size_t,void *,struct page **,struct ddebug *,struct ddebug *);
# 2866 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"



extern struct ddebug process_page_fault_set_pte_rss_add_debug;
# 2873 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

extern struct ddebug process_page_fault_set_pte_rss_skip_debug;
# 2878 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

extern struct ddebug process_page_fault_set_pte_attr_debug;
# 2883 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
int process_page_fault_set_pte_body_result(struct process_vm *,struct vm_range *,
    uintptr_t,uint64_t,pte_t *,size_t,uintptr_t,enum ihk_mc_pt_attribute,int *,
    int (*)(page_table_t,pte_t *,size_t,uintptr_t,enum ihk_mc_pt_attribute),
    struct ddebug *,struct ddebug *,struct ddebug *);
# 2888 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


int process_page_fault_set_range_body_result(struct process_vm *,struct vm_range *,
    uintptr_t,uint64_t,void *,size_t,uintptr_t,enum ihk_mc_pt_attribute,int *,
    int (*)(page_table_t,struct process_vm *,void *,void *,uintptr_t,
            enum ihk_mc_pt_attribute,int,struct vm_range *,int));
void process_page_fault_finish_body_result(uintptr_t,int *,struct page **);




extern struct ddebug process_page_fault_out_stray_debug;
# 2903 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

extern struct ddebug process_page_fault_out_rss_sub_debug;
# 2908 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

extern struct ddebug process_page_fault_out_return_debug;
# 2913 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
int process_page_fault_out_body_result(struct process_vm *,struct vm_range *,
    uintptr_t,uint64_t,const size_t *,struct page *,int,
    struct ddebug *,struct ddebug *,struct ddebug *);
# 2917 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"



extern struct ddebug process_page_fault_anon_clear_debug;
# 2924 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

extern struct ddebug process_page_fault_anon_map_debug;
# 2929 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_page_fault_anon_clear_body_result(struct vm_range *,void *,size_t,void *,
    struct page *,uintptr_t,uint64_t,uintptr_t *,int,int,struct ddebug *,struct ddebug *);
# 2932 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


int process_page_fault_install_finish_body_result(struct process_vm *,
    struct vm_range *, uintptr_t, uint64_t, pte_t *, void *, size_t,
    uintptr_t, enum ihk_mc_pt_attribute, struct page *,
    int (*)(page_table_t,pte_t *,size_t,uintptr_t,enum ihk_mc_pt_attribute),
    int (*)(page_table_t,struct process_vm *,void *,void *,uintptr_t,
            enum ihk_mc_pt_attribute,int,struct vm_range *,int),
    struct ddebug *,struct ddebug *,struct ddebug *,
    struct ddebug *,struct ddebug *,struct ddebug *);





extern struct ddebug process_page_fault_cow_copy_debug;
# 2951 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


extern const int process_page_fault_anon_clear_profile_event;
_Static_assert((PROFILE_page_fault_anon_clr) == 4002, "process_page_fault_anon_clear_profile_event selected supported configuration");
# 2953 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 2957 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 3285 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"




int process_zeroobj_match_bridge(void *memobj);
# 3295 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"




int process_normal_fault_range_bridge(struct process_vm *vm,
          struct vm_range *range,
          unsigned long fault_addr,
          unsigned long reason);
# 3302 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"




int process_xpmem_fault_range_bridge(struct process_vm *, struct vm_range *,
        unsigned long, unsigned long);
# 3325 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 3332 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"




void process_pgio_dispatch_bridge(void *, void *);
# 3480 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
const char *const process_init_stack_alloc_file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c";
const int process_init_stack_alloc_line = 3481 - 122;
const char *const process_init_stack_free_file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c";
const int process_init_stack_free_line = 3483 - 119;
# 3484 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

extern const int process_init_stack_user_category;
_Static_assert((1) == 1, "process_init_stack_user_category selected supported configuration");
# 3485 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

extern struct ddebug process_init_stack_log_size_debug;
# 3490 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

extern struct ddebug process_init_stack_log_ap_user_debug;
# 3495 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void *process_init_stack_alloc_aligned_bridge(int, int, unsigned long, unsigned long);
void process_init_stack_free_pages_bridge(void *, int);
int process_init_stack_add_range_bridge(struct process_vm *, unsigned long, unsigned long,
        unsigned long, unsigned long, int, struct vm_range **);
unsigned long process_init_stack_virt_to_phys_bridge(void *);
unsigned long process_init_stack_attr_bridge(unsigned long, unsigned long, void *);
int process_init_stack_pt_set_range_bridge(void *, struct process_vm *, unsigned long,
        unsigned long, unsigned long, unsigned long, int, struct vm_range *, int);
unsigned long process_init_stack_hwcap_bridge(void);
void process_init_stack_modify_context_bridge(void *, int, unsigned long);
void process_init_stack_log_bridge(int, const unsigned long *);
# 3507 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 3504 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 3504 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"




struct process_init_stack_entry_config {
    unsigned long page_size;
    int page_shift;
    unsigned long user_stack_page_mask;
    int user_stack_page_shift;
    unsigned long user_stack_prepage_size;
    unsigned long stack_alloc_size_override;
    int user_stack_page_p2align;
    unsigned long alloc_nowait;
    unsigned long alloc_user;
    unsigned long mpol_no_stack;
    int user_context_sp_reg;
    unsigned long pf_populate;
    void *(*alloc_aligned)(int npages, int p2align, unsigned long flags, unsigned long virt_addr);
    void (*free_pages)(void *addr, int npages);
    int (*add_range)(struct process_vm *vm, unsigned long start, unsigned long end, unsigned long phys, unsigned long flag, int pgshift, struct vm_range **rangep);
    unsigned long (*virt_to_phys)(void *addr);
    unsigned long (*attr)(unsigned long flag, unsigned long fault, void *ptep);
    int (*pt_set_range)(void *page_table, struct process_vm *vm, unsigned long start, unsigned long end, unsigned long phys, unsigned long attr, int pgshift, struct vm_range *range, int flags);
    unsigned long (*hwcap)(void);
    void (*modify_context)(void *uctx, int reg, unsigned long value);
    void (*log)(int event, const unsigned long *args);
};
# 3531 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
const struct process_init_stack_entry_config process_init_stack_entry_config = {
    .page_size = (1UL << 12),
    .page_shift = 12,
    .user_stack_page_mask = (~((unsigned long)(1UL << 21) - 1)),
    .user_stack_page_shift = 21,
    .user_stack_prepage_size = (1UL << 21),



    .stack_alloc_size_override = 0,

    .user_stack_page_p2align = (21 - 12),
    .alloc_nowait = 0x000002,
    .alloc_user = 0x001000,
    .mpol_no_stack = 0x02,
    .user_context_sp_reg = IHK_UCR_STACK_POINTER,
    .pf_populate = PF_POPULATE,
    .alloc_aligned = process_init_stack_alloc_aligned_bridge,
    .free_pages = process_init_stack_free_pages_bridge,
    .add_range = process_init_stack_add_range_bridge,
    .virt_to_phys = process_init_stack_virt_to_phys_bridge,
    .attr = process_init_stack_attr_bridge,
    .pt_set_range = process_init_stack_pt_set_range_bridge,
    .hwcap = process_init_stack_hwcap_bridge,
    .modify_context = process_init_stack_modify_context_bridge,
    .log = process_init_stack_log_bridge,
};
# 3558 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
int init_process_stack(struct thread *, struct program_load_desc *, unsigned long,
        int, char **, int, char **);
# 3590 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 3503 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 3506 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
static struct ddebug __attribute__((aligned(8))) __attribute__((section("__verbose")))
process_extend_region_exists_debug = {
    .file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c", .func = "extend_process_region",
    .line = 3394, .flags = 0x0,
};
static struct ddebug __attribute__((aligned(8))) __attribute__((section("__verbose")))
process_extend_region_alloc_debug = {
    .file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c", .func = "extend_process_region",
    .line = 3411, .flags = 0x0,
};
static struct ddebug __attribute__((aligned(8))) __attribute__((section("__verbose")))
process_extend_region_success_debug = {
    .file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c", .func = "extend_process_region",
    .line = 3428, .flags = 0x0,
};
# 3521 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
unsigned long process_extend_region_body_result(
    struct process_vm *,unsigned long,unsigned long,unsigned long,
    size_t,int,unsigned long,size_t,unsigned long,unsigned long,unsigned long,
    int,unsigned long,unsigned long,unsigned long,int,const char *,int,int,
    struct ddebug *,struct ddebug *,struct ddebug *);
struct process_extend_region_entry_config {
    size_t page_size;
    int page_shift;
    unsigned long page_mask;
    size_t large_page_size;
    unsigned long large_page_mask;
    unsigned long large_page_p2align;
    unsigned long page_p2align;
    int large_page_shift;
    unsigned long mpol_no_heap;
    unsigned long ap_nowait;
    unsigned long ap_user;
    int pg_user;
    const char * file;
    int alloc_line;
    int free_line;
    struct ddebug * exists_debug;
    struct ddebug * alloc_debug;
    struct ddebug * success_debug;
};
# 3546 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
const struct process_extend_region_entry_config process_extend_region_entry_config = {
    .page_size = (1UL << 12),
    .page_shift = 12,
    .page_mask = (~((unsigned long)(1UL << 12) - 1)),
    .large_page_size = (1UL << 21),
    .large_page_mask = (~((unsigned long)(1UL << 21) - 1)),
    .large_page_p2align = (21 - 12),
    .page_p2align = 0,
    .large_page_shift = 21,
    .mpol_no_heap = 0x01,
    .ap_nowait = 0x000002,
    .ap_user = 0x001000,
    .pg_user = 1,
    .file = "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c",
    .alloc_line = 3408,
    .free_line = 3423,
    .exists_debug = &process_extend_region_exists_debug,
    .alloc_debug = &process_extend_region_alloc_debug,
    .success_debug = &process_extend_region_success_debug,
};
# 3566 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
unsigned long extend_process_region(struct process_vm *, unsigned long, unsigned long,
        unsigned long);
# 3536 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 3605 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 3432 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"



int process_remove_region_clear_bridge(void *page_table,
           struct process_vm *vm,
           unsigned long start,
           unsigned long end);
void process_remove_region_log_bridge(struct process_vm *vm,
          unsigned long start,
          unsigned long end);
# 3456 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
int process_remove_region_clear_bridge(void *page_table,
           struct process_vm *vm,
           unsigned long start,
           unsigned long end);
# 3462 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void process_remove_region_log_bridge(struct process_vm *vm,
          unsigned long start,
          unsigned long end);
# 3470 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 3500 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
extern const int process_free_thread_pages_source_line;
void process_free_thread_pages_bridge(void *thread);
# 3508 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 3520 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void *process_current_resource_set_bridge(void);
# 3529 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_release_hash_detach_bridge(void *resource_set_arg,
     void *proc_arg);
# 3551 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_release_sibling_detach_bridge(void *proc_arg);
# 3566 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_release_profile_bridge(void *proc_arg);
# 3583 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_release_final_cleanup_bridge(void *resource_set_arg);
# 3641 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_detach_address_space_bridge(void *address_space, int pid);
void process_release_process_bridge(void *proc);
# 3656 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_populate_warn_bridge(struct process_vm *vm,
      unsigned long addr,
      unsigned long reason,
      unsigned long off,
      size_t len, int error);
# 3666 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 3760 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_hold_thread_warn_bridge(void *thread_arg);
# 3766 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 3779 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void hold_sigcommon(struct sig_common *sigcommon);
void release_sigcommon(struct sig_common *sigcommon);
# 3808 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void __release_tid(struct process *proc, struct thread *thread);
# 3820 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void __find_and_replace_tid(struct process *proc, struct thread *thread, int new_tid);
# 3832 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_destroy_thread_hash_detach_bridge(void *thread_arg);
# 3853 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_destroy_thread_time_account_bridge(void *thread_arg);
# 3872 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_destroy_thread_release_tid_bridge(void *proc_arg,
            void *thread_arg);
# 3876 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_destroy_thread_replace_tid_bridge(void *proc_arg,
            void *thread_arg,
            int new_tid);
# 3883 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"


void process_release_sigcommon_bridge(void *sigcommon);
# 3991 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void sched_do_migrate_public(void);






extern const struct sched_idle_offsets process_idle_offsets;
extern const struct sched_idle_values process_idle_values;
_Static_assert((2) == 2 && (1) == 1 && (3) == 3,
    "Rust idle CPU status constants match the original pinned C producer");
_Static_assert(0x1 == 1 && 0x20 == 0x20 && 0x2 == 2,
    "Rust idle thread status constants match the original pinned C producer");
_Static_assert(0x2U == 2U && 1 == 1 && 3 == 3,
    "Rust idle flag and monitor constants match the original pinned C producer");
# 4016 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

extern const struct sched_idle_callbacks process_idle_callbacks;
# 4024 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
_Static_assert(sizeof(unsigned long) == 8 && sizeof(void *) == 8,
 "idle callback ABI requires supported LP64");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct thread *)0)->status), int)
 && sizeof(((struct thread *)0)->status) == 4, "idle thread status is C int/i32");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct cpu_local_var *)0)->status), int)
 && sizeof(((struct cpu_local_var *)0)->status) == 4, "idle CPU status is C int/i32");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct cpu_local_var *)0)->flags), unsigned int)
 && sizeof(((struct cpu_local_var *)0)->flags) == 4, "idle CPU flags are u32");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct ihk_os_cpu_monitor *)0)->status), int)
 && sizeof(((struct ihk_os_cpu_monitor *)0)->status) == 4, "idle monitor status is C int/i32");
_Static_assert(__builtin_types_compatible_p(__typeof__(((struct ihk_os_cpu_monitor *)0)->counter), unsigned long),
 "idle monitor counter is unsigned long");
_Static_assert(__builtin_offsetof(struct list_head, next) == 0, "idle scan requires leading next");
_Static_assert(sizeof(struct sched_idle_offsets) == 80, "idle offsets ABI size");
_Static_assert(sizeof(struct sched_idle_values) == 36, "idle constants ABI size");
_Static_assert(sizeof(struct sched_idle_callbacks) == 80, "idle callback ABI size");

void process_idle_entry(void);
# 4049 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 4146 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void process_sched_init_context_bridge(void *thread_arg);
# 4154 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"




int process_sched_save_fp_bridge(void *thread);
# 4167 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"



const int process_sched_timer_configuration[2] = { 0, 0 };
# 4172 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_sched_timer_init_bridge(int cpu);
# 4184 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 4174 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"





void process_sched_init_panic_bridge(void);
# 4283 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
extern const struct sched_runqueue_offsets process_sched_runqueue_offsets;
# 4317 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

void process_sched_rwlock_bridge(unsigned long lock_addr,
     unsigned long node_addr);
void process_sched_rwunlock_bridge(unsigned long lock_addr,
       unsigned long node_addr);


void process_sched_status_set_bridge(unsigned long status_addr, int status);
void process_sched_set_timer_bridge(int runq_locked);
# 4339 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_sched_runq_log_bridge(int event,
       unsigned long arg0,
       unsigned long arg1, int arg2,
       int arg3);
# 4419 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"




unsigned long process_sched_irq_save_bridge(void);
void process_sched_irq_restore_bridge(unsigned long irqstate);
void process_sched_zero_free_bridge(void);
void process_sched_pause_bridge(void);
int process_sched_has_signal_bridge(unsigned long thread_addr);
void process_sched_reset_cputime_bridge(void);


void process_sched_procfs_create_thread_bridge(unsigned long thread_addr);
int process_sched_counter_inc_bridge(unsigned long counter_addr);
void process_sched_counter_dec_bridge(unsigned long counter_addr);
# 4451 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_sched_rusage_threads_inc_bridge(void);


void process_sched_rusage_debug_bridge(void);
# 4468 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 4469 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 4469 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 4594 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
extern unsigned long sched_schedule_fp_admit(int exited_status);
extern void sched_schedule_debug_handoff(struct thread *prev, struct thread *next);


struct sched_exit_debug {
 const unsigned long *num_threads;
 const unsigned long *total_memory_usage;
 const long *memory_stat_rss;
 const long *memory_stat_mapped_file;
 int page_sizes;
};
extern void sched_schedule_exit_cleanup(struct cpu_local_var *old_cpu,
  struct thread *last, int exited_status,
  const struct sched_exit_debug *debug);

static const struct sched_exit_debug process_sched_exit_debug = {
 &rusage.num_threads, &rusage.total_memory_usage,
 rusage.memory_stat_rss, rusage.memory_stat_mapped_file,
 IHK_MAX_NUM_PGSIZES
};






extern struct ddebug process_schedule_switch_debug;
# 4623 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 4623 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"

const struct sched_exit_debug *const process_schedule_exit_debug_input =
 &process_sched_exit_debug;
# 4629 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void schedule(void);
# 4933 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 4933 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 4918 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
# 4961 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
int __sched_wakeup_thread(struct thread *thread,
  int valid_states, int runq_locked);
# 5096 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void __runq_add_thread(struct thread *thread, int cpu_id);
# 5114 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void runq_add_thread(struct thread *thread, int cpu_id);
# 5226 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void debug_log(unsigned long arg);
# 5300 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
void process_access_ok_log_bridge(struct process_vm *vm, int type,
  unsigned long addr, size_t len, int rc);
# 5306 "/home/holden/mckernel/docs/verification/evidence/os-recovery-adoption-20261025-0254/m14-f02-local14-final14-qualified-preparation-source-1/candidate/kernel/process.c"
