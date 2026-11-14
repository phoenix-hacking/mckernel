/* Actual production scheduler/save and Rust preparation bodies are inserted.
 * Only allocation, XSAVE, IRQ, locks, restore, switch and panic are boundaries.
 * panic longjmp observes a terminal boundary; production panic never returns. */
#include <assert.h>
#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#define PAGE_SIZE 4096
#define PAGE_SHIFT 12
#define PAGE_P2ALIGN 0
#define IHK_MC_AP_NOWAIT 2
#define IHK_MC_PG_KERNEL 1
#define PS_RUNNING 1
#define PS_INTERRUPTIBLE 2
#define PS_EXITED 8
#define CPU_FLAG_NEED_RESCHED 1
#define CPU_FLAG_NEED_MIGRATE 2
#define SPAWNING_TO_REMOTE 1001
#define CPU_STATUS_IDLE 0
#define CPU_STATUS_RESERVED 2
#define SCHED_SCHEDULE_ACTION_SWITCH 3
#define dkprintf(...) do { } while (0)
#define kprintf(...) do { } while (0)
#define ihk_atomic_read(p) (*(p))
typedef struct { unsigned char bytes[4096]; } fp_regs_struct;
struct list_head { struct list_head *next, *prev; };
struct process { int pid; };
struct address_space { void *page_table; };
struct vm { struct address_space *address_space; };
struct thread { fp_regs_struct *fp_regs; int tid, status; void *ptrace_debugreg, *uctx; struct process *proc; struct vm *vm; struct list_head sched_list, sigpending; void *sigcommon; int mod_clone; };
struct cpu_local_var { struct thread idle; unsigned long nr_ctx_switches; size_t runq_len; int prevpid, runq_lock; unsigned long runq_irqstate; struct thread *current; struct list_head runq; unsigned flags; int status, no_preempt; };
// RUST_C_ABI
static struct cpu_local_var cpu, before_cpu;
static struct thread previous, following, before_previous, before_following;
static int allocations, last_save_errno, saves, restores, switches, prepares, locks, unlocks;
static int order, save_order, restore_order, switch_order, panic_seen;
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
static int prepare_order;
#endif
static unsigned long irq_enabled, entry_irq;
static int allocation_fails = 1, xsave_available = 1, xsave_size = 2696;
static uint64_t xsave_mask = 0xe7;
static void *allocated;
static size_t allocated_bytes;
static jmp_buf panic_boundary;
static struct cpu_local_var *get_this_cpu_local_var(void) { return &cpu; }
static unsigned long cpu_disable_interrupt_save(void) { unsigned long old=irq_enabled; irq_enabled=0; return old; }
static void cpu_restore_interrupt(unsigned long state) { assert(!cpu.runq_lock); irq_enabled=state; }
static void ihk_mc_spinlock_lock_noirq(int *lock) { assert(!irq_enabled && !*lock); *lock=1; ++locks; }
static void ihk_mc_spinlock_unlock_noirq(int *lock) { assert(!irq_enabled && *lock); *lock=0; ++unlocks; }
static void panic(const char *message) { assert(strstr(message,"floating point")); assert(!irq_enabled); ++panic_seen; longjmp(panic_boundary,1); }
static void *_ihk_mc_alloc_aligned_pages_node(int pages, int align, int flags, int node, int type, int map, const char *file, int line) {
    (void)file; (void)line;
    assert(align==PAGE_P2ALIGN && flags==IHK_MC_AP_NOWAIT && node==-1 && type==IHK_MC_PG_KERNEL && map==-1);
    assert(pages==(xsave_size+PAGE_SIZE-1)/PAGE_SIZE && !irq_enabled);
    ++allocations;
    if(allocation_fails) return NULL;
    assert(!allocated);
    allocated_bytes=(size_t)pages*PAGE_SIZE;
    allocated=aligned_alloc(PAGE_SIZE,allocated_bytes); assert(allocated);
    memset(allocated,0xa5,allocated_bytes); return allocated;
}
static void observe_xsave(fp_regs_struct *regs, unsigned low, unsigned high) {
    assert(regs && !((uintptr_t)regs&63) && !irq_enabled);
    assert(low==(unsigned)xsave_mask && high==(unsigned)(xsave_mask>>32));
    assert(allocated_bytes>=(size_t)xsave_size);
    for(size_t i=0;i<allocated_bytes;++i) assert(!((unsigned char *)regs)[i]);
    ++saves;
}
// PRODUCTION_ALLOCATION_SAVE
static int observed_save(struct thread *thread) {
    save_order=++order; last_save_errno=save_fp_regs(thread); return last_save_errno;
}
#define save_fp_regs observed_save
static unsigned long process_sched_irq_save_bridge(void) { return cpu_disable_interrupt_save(); }
static void process_sched_irq_restore_bridge(unsigned long state) { cpu_restore_interrupt(state); }
static void process_sched_noirq_lock_bridge(unsigned long lock) { ihk_mc_spinlock_lock_noirq((int *)lock); }
static void process_sched_noirq_unlock_bridge(unsigned long lock) { ihk_mc_spinlock_unlock_noirq((int *)lock); }
static void process_sched_set_timer_bridge(int locked) { assert(locked && cpu.runq_lock); }
static void process_sched_reset_cputime_bridge(void) { assert(cpu.runq_lock); }
static int process_sched_has_signal_bridge(unsigned long thread) { (void)thread; return 0; }
static void process_sched_runq_log_bridge(int e,unsigned long a,unsigned long b,int c,int d) { (void)e;(void)a;(void)b;(void)c;(void)d; }
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
#define sched_schedule_prepare_body_result(...) (++prepares, prepare_order=++order, sched_schedule_prepare_body_result(__VA_ARGS__))
#endif
#define ihk_mc_get_processor_id() 0
#define ihk_mc_syscall_pc(...) 0UL
#define ihk_mc_syscall_sp(...) 0UL
#define save_debugreg(...) do { } while (0)
#define clear_debugreg() do { } while (0)
#define restore_debugreg(...) do { } while (0)
static void restore_fp_regs(struct thread *thread) { assert(thread==&following || thread==&previous); assert(cpu.runq_lock && !irq_enabled); ++restores;restore_order=++order; }
#define ihk_mc_load_page_table(...) do { } while (0)
#define arch_flush_icache_all() do { } while (0)
static struct thread *arch_switch_context(struct thread *prev, struct thread *next) {
    (void)prev; assert(cpu.runq_lock && !irq_enabled && cpu.current==next);
    assert(next==&following || next==&cpu.idle); ++switches; switch_order=++order; return NULL;
}
#define release_thread(...) do { } while (0)
#define rusage_num_threads_dec() do { } while (0)
static void init_list(struct list_head *h) { h->next=h; h->prev=h; }
static void process_list_add_tail_counted_result(struct list_head *e,struct list_head *h,size_t *len) {
    e->prev=h->prev; e->next=h; h->prev->next=e; h->prev=e; ++*len;
}
static void process_list_detach_counted_result(struct list_head *e,size_t *len) {
    e->prev->next=e->next; e->next->prev=e->prev; --*len;
}
#define hassigpending(t) (0)
#define reset_cputime() process_sched_reset_cputime_bridge()
#define set_timer(n) process_sched_set_timer_bridge(n)
// PRODUCTION_SCHEDULE
int main(int argc,char **argv) {
    assert(argc==3); const char *mode=argv[1]; entry_irq=(unsigned long)strtoul(argv[2],NULL,10); irq_enabled=entry_irq;
    static struct process process={1}; static struct address_space space; static struct vm vm={&space};
    previous=(struct thread){.tid=1,.status=PS_RUNNING,.proc=&process,.vm=&vm};
    following=(struct thread){.tid=2,.status=PS_RUNNING,.proc=&process,.vm=&vm};
    cpu.idle=(struct thread){.tid=0,.status=PS_RUNNING,.proc=&process,.vm=&vm};
    init_list(&cpu.runq); init_list(&previous.sigpending); init_list(&following.sigpending);
    init_list(&previous.sched_list); init_list(&following.sched_list);
    cpu.current=&previous;
    process_list_add_tail_counted_result(&previous.sched_list,&cpu.runq,&cpu.runq_len);
    if(strncmp(mode,"no-switch",9)) process_list_add_tail_counted_result(&following.sched_list,&cpu.runq,&cpu.runq_len);
    if(!strcmp(mode,"positive") || !strcmp(mode,"large") || !strcmp(mode,"no-switch")) allocation_fails=0;
    if(!strcmp(mode,"large")) xsave_size=8193;
    if(!strcmp(mode,"no-xsave")) xsave_available=0;
    if(!strcmp(mode,"no-preempt")) cpu.no_preempt=1;
    if(!strcmp(mode,"idle") || !strcmp(mode,"null")) {
        process_list_detach_counted_result(&previous.sched_list,&cpu.runq_len);
        cpu.current=!strcmp(mode,"idle")?&cpu.idle:NULL;
    }
    if(!strcmp(mode,"exited")) previous.status=PS_EXITED;
    before_cpu=cpu; before_previous=previous; before_following=following;
    if(!setjmp(panic_boundary)) schedule();
#ifdef OLD_CANDIDATE
    assert(!strcmp(mode,"failure"));
    assert(last_save_errno==-ENOMEM && allocations==1 && restores==1 && switches==1 && !panic_seen);
    assert(save_order<restore_order && restore_order<switch_order);
    assert(cpu.current==&following && cpu.nr_ctx_switches==1 && irq_enabled==entry_irq && !cpu.runq_lock);
    puts("OLD_UNSAFE save_errno=-12 allocations=1 restore=1 switch=1");
#else
    if(strstr(mode,"failure")) {
        assert(panic_seen==1 && last_save_errno==-ENOMEM && allocations==1 && !saves);
        assert(!prepares && !locks && !unlocks && !restores && !switches && !irq_enabled);
        assert(!memcmp(&cpu,&before_cpu,sizeof cpu));
        assert(!memcmp(&previous,&before_previous,sizeof previous));
        assert(!memcmp(&following,&before_following,sizeof following));
    } else {
        assert(!panic_seen && irq_enabled==entry_irq && !cpu.runq_lock && locks==unlocks);
        if(!strcmp(mode,"no-preempt")) {
            assert(!allocations && !saves && !restores && !switches && (cpu.flags&CPU_FLAG_NEED_RESCHED));
            assert(cpu.current==&previous && cpu.runq_len==2);
        } else if(!strcmp(mode,"no-switch")) {
            assert(allocations==1 && saves==1 && !restores && !switches && cpu.current==&previous && cpu.runq_len==1);
        } else {
            assert(switches==1 && cpu.nr_ctx_switches==1);
            if(!strcmp(mode,"positive") || !strcmp(mode,"large")) assert(allocations==1 && saves==1 && restores==1);
            else assert(!allocations && !saves);
            if(!strcmp(mode,"exited")) assert(!restores && cpu.current==&cpu.idle);
            else assert(restores==1 && cpu.current==&following);
        }
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
        assert(prepares==1);
        if(saves) assert(save_order<prepare_order);
#endif
    }
    printf("PASS %s irq=%lu allocations=%d saves=%d prepares=%d locks=%d restore=%d switch=%d panic=%d\n",mode,entry_irq,allocations,saves,prepares,locks,restores,switches,panic_seen);
#endif
    free(allocated); return 0;
}
