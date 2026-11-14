int kprintf(const char *format, ...);
#define ekprintf(fmt, args...) kprintf(fmt, ##args)
#define X86_CLEAR_TOP_LOG_INVALID	6
#define X86_CLEAR_TOP_LOG_ALLOC_FAILED	7
