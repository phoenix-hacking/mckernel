/* Keep the displaced dynamic-debug selector as declarative C ABI data.
 * Rust owns both event branches, field reads and the existing variadic logger.
 * The source-bound original success callsite remains selectable at line 2086.
 */
struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_vm_range_insert_debug = {
    .file = __FILE__,
    .func = "vm_range_insert_log_bridge",
    .line = 2086,
    .flags = DDEBUG_DEFAULT,
};
