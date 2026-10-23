/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. Extracted selected fragment only. */
#include <ihk/debug.h>
#ifdef MCKERNEL_RUST_PROCESS_HELPERS
#define PROCESS_SCHED_PUBLIC_BRIDGE
/* Existing diagnostic selector identity from the displaced C callsite.
 * This is declarative __verbose data consumed by the existing Rust registry. */
struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_sched_migrate_debug = {
    .file = __FILE__,
    .func = "process_sched_migrate_log_bridge",
    .line = 422, /* source-bound original dkprintf line; keep control selectors */
    .flags = DDEBUG_DEFAULT,
};
#else
#define PROCESS_SCHED_PUBLIC_BRIDGE static
PROCESS_SCHED_PUBLIC_BRIDGE void process_sched_migrate_log_bridge(unsigned long thread_addr,
					     int tid, int cpu_id)
{
	(void)thread_addr;
	dkprintf("%s: tid: %d -> cpu: %d\n",
		 "sched_request_migrate", tid, cpu_id);
}
void (*const leaf_fallback_consumer)(unsigned long,int,int) = process_sched_migrate_log_bridge;
#endif
