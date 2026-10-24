#define __aligned(x)		__attribute__((aligned(x)))
struct ddebug {
	const char *file;
	const char *func;
	const char *fmt;
	unsigned int line:24;
	unsigned int flags:8;
} __aligned(8);
#define DDEBUG_NONE  0x0
#define DDEBUG_PRINT 0x1
#define DDEBUG_DEFAULT DDEBUG_NONE
#define dkprintf(fmt, args...)        \
do {                                  \
	static struct ddebug __aligned(8) \
	__attribute__((section("__verbose"))) ddebug = { \
		.file = __FILE__,        \
		.func = __func__,        \
		.line = __LINE__,        \
		.flags = DDEBUG_DEFAULT, \
	};                            \
	if (ddebug.flags)             \
		kprintf(fmt, ##args); \
} while (0)
#define ekprintf(fmt, args...) kprintf(fmt, ##args)

#define PTL2_SHIFT         21     
#define PTL3_SHIFT         30
#define X86_CLEAR_EFFECT_FREE_ANON	2
#define X86_CLEAR_EFFECT_XPMEM_KEEP	3
#define X86_CLEAR_EFFECT_FREE_UNMAPPED	4
#define X86_CLEAR_EFFECT_CHILD_FREE	5
#define X86_CLEAR_RANGE_LOG_SPLIT	8
#define X86_CLEAR_RANGE_LOG_LARGE_PHYS	9
#define IHK_MC_PG_KERNEL       0
