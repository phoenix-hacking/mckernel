struct ddebug arch_prctl_log_debug __asm__("mckernel_f06_arch_prctl_debug")
    __attribute__((section("__verbose"),aligned(8))) = {
    .file = __FILE__,
    .func = "arch_prctl_log_bridge",
    .fmt = 0,
    .line = 669,
    .flags = DDEBUG_DEFAULT,
};
