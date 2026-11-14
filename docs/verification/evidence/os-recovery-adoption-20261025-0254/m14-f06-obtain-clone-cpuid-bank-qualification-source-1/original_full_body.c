/* Functional OS only; no security testing. Exact full C baseline, original name until objcopy. */
#include <process.h>
#include <cls.h>
#include <affinity.h>
#include <ihk/debug.h>
extern int num_processors;
extern unsigned long fixture_clone_lock(ihk_spinlock_t *);
extern void fixture_clone_unlock(ihk_spinlock_t *,unsigned long);
extern void fixture_clone_noirq_lock(ihk_spinlock_t *);
extern void fixture_clone_noirq_unlock(ihk_spinlock_t *);
#undef ihk_mc_spinlock_lock
#undef ihk_mc_spinlock_unlock
#undef ihk_mc_spinlock_lock_noirq
#undef ihk_mc_spinlock_unlock_noirq
#define ihk_mc_spinlock_lock fixture_clone_lock
#define ihk_mc_spinlock_unlock fixture_clone_unlock
#define ihk_mc_spinlock_lock_noirq fixture_clone_noirq_lock
#define ihk_mc_spinlock_unlock_noirq fixture_clone_noirq_unlock
#line 884 "/src/arch/x86_64/kernel/syscall.c"
int obtain_clone_cpuid(cpu_set_t *cpu_set, int use_last) {
	int min_queue_len = -1;
	int cpu, min_cpu = -1, uti_cpu = -1;
	unsigned long irqstate;
	
	irqstate = ihk_mc_spinlock_lock(&runq_reservation_lock);
	/* Find the first allowed core with the shortest run queue */
	for (cpu = 0; cpu < num_processors; ++cpu) {
		struct cpu_local_var *v;

		if (!CPU_ISSET(cpu, cpu_set)) continue;

		v = get_cpu_local_var(cpu);
		ihk_mc_spinlock_lock_noirq(&v->runq_lock);
		dkprintf("%s: cpu=%d,runq_len=%d,runq_reserved=%d\n", __FUNCTION__, cpu, v->runq_len, v->runq_reserved);
		if (min_queue_len == -1 || v->runq_len + v->runq_reserved < min_queue_len) {
			min_queue_len = v->runq_len + v->runq_reserved;
			min_cpu = cpu;
		}

		/* Record the last tie CPU */
		if (min_cpu != cpu && v->runq_len + v->runq_reserved == min_queue_len) {
			uti_cpu = cpu;
		}
		dkprintf("%s: cpu=%d,runq_len=%d,runq_reserved=%d,min_cpu=%d,uti_cpu=%d\n", __FUNCTION__, cpu, v->runq_len, v->runq_reserved, min_cpu, uti_cpu);
		ihk_mc_spinlock_unlock_noirq(&v->runq_lock);
#if 0
		if (min_queue_len == 0)
			break;
#endif
	}

	min_cpu = use_last ? uti_cpu : min_cpu;
	if (min_cpu != -1) {
		if (get_cpu_local_var(min_cpu)->status != CPU_STATUS_RESERVED)
			get_cpu_local_var(min_cpu)->status = CPU_STATUS_RESERVED;
		__sync_fetch_and_add(&get_cpu_local_var(min_cpu)->runq_reserved, 1);
	}
	ihk_mc_spinlock_unlock(&runq_reservation_lock, irqstate);

    return min_cpu;
}
