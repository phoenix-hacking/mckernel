#include <process.h>
#include <sched_helpers.h>
#include <cls.h>
#include <cpulocal.h>
const unsigned long idle_production_abi[] = {
 sizeof(struct thread), offsetof(struct thread, status), offsetof(struct thread, sched_list),
 sizeof(((struct thread *)0)->status), offsetof(struct cpu_local_var, runq),
 offsetof(struct cpu_local_var, status), sizeof(unsigned long), sizeof(void *),
 PS_RUNNING, CPU_STATUS_IDLE, CPU_STATUS_RESERVED, CPU_STATUS_RUNNING
};
int idle_actual_header_consumer(struct cpu_local_var *v) {
			_Static_assert(__builtin_types_compatible_p(
				__typeof__(((struct thread *)0)->status), int),
				"idle runqueue status must be a C int");
			_Static_assert(sizeof(((struct thread *)0)->status) == 4,
				"idle runqueue status must match Rust i32");
			_Static_assert(offsetof(struct list_head, next) == 0,
				"idle runqueue next must be the first list field");
			if (sched_idle_runqueue_has_running_result(
				(unsigned long)&v->runq,
				offsetof(struct thread, sched_list),
				offsetof(struct thread, status), PS_RUNNING))
				v->status = CPU_STATUS_RUNNING;

 return v->status;
}
static struct cpu_local_var cpu;
static struct thread thread;
int main(void) {
 cpu.runq.next=&cpu.runq; cpu.runq.prev=&cpu.runq;
 cpu.status=CPU_STATUS_IDLE;
 if(idle_actual_header_consumer(&cpu)!=CPU_STATUS_IDLE) return 21;
 cpu.runq.next=&thread.sched_list; cpu.runq.prev=&thread.sched_list;
 thread.sched_list.next=&cpu.runq; thread.sched_list.prev=&cpu.runq;
 thread.status=PS_STOPPED; thread.spin_sleep=1; cpu.status=CPU_STATUS_RESERVED;
 if(idle_actual_header_consumer(&cpu)!=CPU_STATUS_RESERVED) return 22;
 thread.status=PS_RUNNING;
 if(idle_actual_header_consumer(&cpu)!=CPU_STATUS_RUNNING) return 23;
 return 0;
}
