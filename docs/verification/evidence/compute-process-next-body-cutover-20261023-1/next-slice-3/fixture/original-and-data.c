/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual selected macro + actual declared descriptor; hosted diagnostic sink only. */
#include <ihk/debug.h>
#define PROCESS_SCHED_PUBLIC_BRIDGE
void process_sched_migrate_log_bridge(unsigned long,int,int) __asm__("leaf_original_migrate_log");
#line 418 "/src/kernel/process.c"
PROCESS_SCHED_PUBLIC_BRIDGE void process_sched_migrate_log_bridge(unsigned long thread_addr,
					     int tid, int cpu_id)
{
	(void)thread_addr;
	dkprintf("%s: tid: %d -> cpu: %d\n",
		 "sched_request_migrate", tid, cpu_id);
}
#line 1 "private-descriptor-consumer.c"
/* Existing diagnostic selector identity from the displaced C callsite.
 * This is declarative __verbose data consumed by the existing Rust registry. */
struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_sched_migrate_debug = {
    .file = "/src/kernel/process.c",
    .func = "process_sched_migrate_log_bridge",
    .line = 422, /* source-bound original dkprintf line; keep control selectors */
    .flags = DDEBUG_DEFAULT,
};
