/* Existing diagnostic selector identity from the displaced C callsite.
 * This is declarative __verbose data consumed by the existing Rust registry. */
struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_sched_migrate_debug = {
    .file = __FILE__,
    .func = "process_sched_migrate_log_bridge",
    .line = 422, /* source-bound original dkprintf line; keep control selectors */
    .flags = DDEBUG_DEFAULT,
};
