/* Preserve displaced remap diagnostics and tracked-free source identity as
 * static C ABI data only. Rust owns the complete callback computation. */
const char *const process_remap_free_file = __FILE__;
const int process_remap_free_line = 2469;
struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_remap_one_page_entry_debug = {
    .file = __FILE__, .func = "remap_one_page",
    .line = 2448, .flags = DDEBUG_DEFAULT,
};
struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_remap_one_page_rss_debug = {
    .file = __FILE__, .func = "remap_one_page",
    .line = 2470, .flags = DDEBUG_DEFAULT,
};
struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_remap_one_page_exit_debug = {
    .file = __FILE__, .func = "remap_one_page",
    .line = 2476, .flags = DDEBUG_DEFAULT,
};
