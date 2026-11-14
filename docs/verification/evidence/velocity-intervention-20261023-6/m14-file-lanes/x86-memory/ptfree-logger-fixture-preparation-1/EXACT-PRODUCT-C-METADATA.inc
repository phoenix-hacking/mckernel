const char x86_pt_free_pages_file[] = __FILE__;
const int x86_pt_free_pages_line = 807;
const int x86_pt_free_pages_flag = IHK_MC_PG_KERNEL;
struct ddebug __aligned(8) __attribute__((section("__verbose")))
x86_clear_effect_child_free_debug = {
    .file = __FILE__, .func = "x86_clear_effect_log_bridge", .fmt = NULL,
    .line = 1391, .flags = DDEBUG_DEFAULT,
};
struct ddebug __aligned(8) __attribute__((section("__verbose")))
x86_clear_effect_free_anon_debug = {
    .file = __FILE__, .func = "x86_clear_effect_log_bridge", .fmt = NULL,
    .line = 1380, .flags = DDEBUG_DEFAULT,
};
struct ddebug __aligned(8) __attribute__((section("__verbose")))
x86_clear_effect_free_unmapped_debug = {
    .file = __FILE__, .func = "x86_clear_effect_log_bridge", .fmt = NULL,
    .line = 1387, .flags = DDEBUG_DEFAULT,
};
struct ddebug __aligned(8) __attribute__((section("__verbose")))
x86_clear_effect_xpmem_keep_debug = {
    .file = __FILE__, .func = "x86_clear_effect_log_bridge", .fmt = NULL,
    .line = 1384, .flags = DDEBUG_DEFAULT,
};
struct ddebug __aligned(8) __attribute__((section("__verbose")))
x86_clear_range_large_phys_debug = {
    .file = __FILE__, .func = "x86_clear_range_log_bridge", .fmt = NULL,
    .line = 1446, .flags = DDEBUG_DEFAULT,
};
