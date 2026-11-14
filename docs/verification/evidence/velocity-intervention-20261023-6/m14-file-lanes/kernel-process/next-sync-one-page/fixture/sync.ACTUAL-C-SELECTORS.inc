/* Displaced sync callback dynamic-debug selectors: declarative data only. */
struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_sync_one_page_entry_debug = {
    .file = __FILE__, .func = "sync_one_page",
    .line = 2546, .flags = DDEBUG_DEFAULT,
};
struct ddebug __aligned(8) __attribute__((section("__verbose")))
process_sync_one_page_exit_debug = {
    .file = __FILE__, .func = "sync_one_page",
    .line = 2574, .flags = DDEBUG_DEFAULT,
};
