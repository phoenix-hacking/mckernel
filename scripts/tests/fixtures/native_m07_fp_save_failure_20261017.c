/* Complete retained942 check_and_allocate_fp_regs/save_fp_regs/schedule bodies.
 * Kernel preparation/allocation/restore/switch boundaries are mocked. XSAVE
 * remains in the production save body but cannot execute in tested paths:
 * allocation always fails or xsave_available=0. No hardware switch executes. */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define MCKERNEL_RUST_PROCESS_HELPERS 1
#define PAGE_SIZE 4096
#define PAGE_SHIFT 12
#define PAGE_P2ALIGN 0
#define IHK_MC_AP_NOWAIT 2
#define IHK_MC_PG_KERNEL 1
#define PS_EXITED 8
#define SCHED_SCHEDULE_ACTION_SWITCH 1
#define dkprintf(...) do { } while (0)
#define kprintf(...) do { } while (0)
typedef struct { unsigned char bytes[4096]; } fp_regs_struct;
struct process { int pid; };
struct address_space { void *page_table; };
struct vm { struct address_space *address_space; };
struct thread { fp_regs_struct *fp_regs; int tid, status; void *ptrace_debugreg, *uctx; struct process *proc; struct vm *vm; };
struct cpu_local_var { struct thread idle; unsigned long nr_ctx_switches; int runq_len, prevpid, runq_lock; unsigned long runq_irqstate; };
struct sched_schedule_result { unsigned long cpu_addr, prev_thread_addr, next_thread_addr; int prevpid; };
static struct cpu_local_var cpu;
static struct thread previous, following;
static int allocations, last_save_errno, restores, switches, order, save_order, restore_order, switch_order;
static int no_switch;
static int xsave_available=1, xsave_size=2696;
static uint64_t xsave_mask=7;
static struct cpu_local_var *get_this_cpu_local_var(void) { return &cpu; }
static void * _ihk_mc_alloc_aligned_pages_node(int pages, int align, int flags, int node, int type, int map, const char *file, int line) {
    (void)align;(void)node;(void)type;(void)map;(void)file;(void)line;
    if(pages!=1 || flags!=IHK_MC_AP_NOWAIT) abort();
    ++allocations; return NULL;
}
// PRODUCTION_ALLOCATION_SAVE
static int observed_save(struct thread *thread) {
    save_order=++order;last_save_errno=save_fp_regs(thread);return last_save_errno;
}
#define save_fp_regs observed_save
static int prepare(struct sched_schedule_result *out) {
    out->cpu_addr=(uintptr_t)&cpu;out->prev_thread_addr=(uintptr_t)&previous;
    out->next_thread_addr=(uintptr_t)&following;out->prevpid=1;
    return no_switch ? 0 : SCHED_SCHEDULE_ACTION_SWITCH;
}
#define sched_schedule_prepare_body_result(...) prepare(&schedule_result)
#define ihk_mc_get_processor_id() 0
#define ihk_mc_syscall_pc(...) 0UL
#define ihk_mc_syscall_sp(...) 0UL
#define save_debugreg(...) do { } while (0)
#define clear_debugreg() do { } while (0)
#define restore_debugreg(...) do { } while (0)
static void restore_fp_regs(struct thread *thread) { if(thread!=&following)abort();++restores;restore_order=++order; }
#define ihk_mc_load_page_table(...) do { } while (0)
#define arch_flush_icache_all() do { } while (0)
static struct thread *arch_switch_context(struct thread *prev, struct thread *next) {
    if(prev!=&previous || next!=&following) { abort(); }
    ++switches;switch_order=++order;return NULL;
}
#define ihk_mc_spinlock_unlock_noirq(...) do { } while (0)
#define cpu_restore_interrupt(...) do { } while (0)
#define release_thread(...) do { } while (0)
#define rusage_num_threads_dec() do { } while (0)
// PRODUCTION_SCHEDULE
int main(int argc,char **argv) {
    static struct process process={1};
    static struct address_space space;
    static struct vm vm={&space};
    previous=(struct thread){.tid=1,.status=1,.proc=&process,.vm=&vm};
    following=(struct thread){.tid=2,.status=1,.proc=&process,.vm=&vm};
    if(argc==2 && !strcmp(argv[1],"no-xsave")) xsave_available=0;
    if(argc==2 && !strcmp(argv[1],"no-switch")) no_switch=1;
    schedule();
    int mismatch=last_save_errno==-ENOMEM && allocations==1 && restores==1 && switches==1
        && save_order<restore_order && restore_order<switch_order && previous.fp_regs==NULL;
    printf("M07_%s save_errno=%d allocations=%d restore=%d switch=%d\n",
           mismatch?"MISMATCH":"NO_MISMATCH",last_save_errno,allocations,restores,switches);
    return mismatch?0:2;
}
