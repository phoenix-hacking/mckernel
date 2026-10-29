#line 1 "kernel/syscall.c"
/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
struct ddebug __attribute__((aligned(8),section("__verbose"))) f03_util_register_desc_debug_v1[1]={
    {.file=__FILE__,.func="syscall_util_register_desc_log_bridge",.line=28605,.flags=DDEBUG_DEFAULT}
};
extern void syscall_util_register_desc_log_bridge(int,unsigned long);
static const unsigned EXPECTED_DEBUG_LINE=28605;
