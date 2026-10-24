/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "fixture-prelude.h"
int mcosid;
int fd;
int ischild;
int enable_vdso = 1;
int mpol_no_heap = 0;
int mpol_no_stack = 0;
int mpol_no_bss = 0;
int mpol_shm_premap = 0;
int no_bind_ikc_map = 0;
int straight_map = 0;
int profile = 0;
int disable_sched_yield = 0;
int uti_thread_rank = 0;
int uti_use_last_cpu = 0;
int enable_uti = 0;
int nr_processes = 0;
int nr_threads = -1;
pid_t master_tid;
int ncpu;
int nnodes;
int n_threads;
unsigned long straight_map_threshold = (1024*1024);
unsigned long mpol_threshold = 0;
unsigned long heap_extension = -1;
unsigned long mcexec_flags = 0;
unsigned long page_size;
unsigned long page_mask;
long stack_premap = (2ULL << 20);
long stack_max = -1;
#ifdef ENABLE_TOFU
int enable_tofu = 0;
#endif
char *exec_path = NULL;
char *altroot;
char *mpol_bind_nodes = NULL;
unsigned char *dma_buf;
void *numa_nodes;
size_t cpu_set_size;
char dev[64];
struct rlimit rlim_stack;
cpu_set_t mcexec_partition_cpu_set_storage;
#ifdef DEBUG
int debug=1;
#else
int debug;
#endif
#ifdef USE_SYSCALL_MOD_CALL
int __glob_argc=-1;
char **__glob_argv=0;
#endif
struct thread_data_s {
	struct thread_data_s *next;
	pthread_t thread_id;
	int cpu;
	int ret;
	pid_t	tid;
	int terminate;
	int remote_tid;
	int remote_cpu;
	int joined, detached;
	pthread_mutex_t *lock;
	pthread_barrier_t *init_ready;
} *thread_data;
struct fork_sync_container *fork_sync_top;
pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
pthread_mutex_t fork_sync_mutex = PTHREAD_MUTEX_INITIALIZER;
pthread_barrier_t init_ready;
pthread_barrier_t uti_init_ready;
pthread_spinlock_t overlay_fd_lock;
struct list_head overlay_fd_list = { &(overlay_fd_list), &(overlay_fd_list) };
struct option mcexec_options[] = {
#ifndef __aarch64__
	{
		.name =		"disable-vdso",
		.has_arg =	no_argument,
		.flag =		&enable_vdso,
		.val =		0,
	},
	{
		.name =		"enable-vdso",
		.has_arg =	no_argument,
		.flag =		&enable_vdso,
		.val =		1,
	},
#endif /*__aarch64__*/
	{
		.name =		"profile",
		.has_arg =	no_argument,
		.flag =		&profile,
		.val =		1,
	},
	{
		.name =		"mpol-no-heap",
		.has_arg =	no_argument,
		.flag =		&mpol_no_heap,
		.val =		1,
	},
	{
		.name =		"mpol-no-stack",
		.has_arg =	no_argument,
		.flag =		&mpol_no_stack,
		.val =		1,
	},
	{
		.name =		"mpol-no-bss",
		.has_arg =	no_argument,
		.flag =		&mpol_no_bss,
		.val =		1,
	},
	{
		.name =		"mpol-shm-premap",
		.has_arg =	no_argument,
		.flag =		&mpol_shm_premap,
		.val =		1,
	},
	{
		.name =		"no-bind-ikc-map",
		.has_arg =	no_argument,
		.flag =		&no_bind_ikc_map,
		.val =		1,
	},
	{
		.name =		"mpol-threshold",
		.has_arg =	required_argument,
		.flag =		NULL,
		.val =		'M',
	},
	{
		.name =		"enable-straight-map",
		.has_arg =	no_argument,
		.flag =		&straight_map,
		.val =		1,
	},
	{
		.name =		"straight-map-threshold",
		.has_arg =	required_argument,
		.flag =		NULL,
		.val =		'S',
	},
	{
		.name =		"disable-sched-yield",
		.has_arg =	no_argument,
		.flag =		&disable_sched_yield,
		.val =		1,
	},
	{
		.name =		"extend-heap-by",
		.has_arg =	required_argument,
		.flag =		NULL,
		.val =		'h',
	},
	{
		.name =		"stack-premap",
		.has_arg =	required_argument,
		.flag =		NULL,
		.val =		's',
	},
	{
		.name =		"uti-thread-rank",
		.has_arg =	required_argument,
		.flag =		NULL,
		.val =		'u',
	},
	{
		.name =		"uti-use-last-cpu",
		.has_arg =	no_argument,
		.flag =		&uti_use_last_cpu,
		.val =		1,
	},
	{
		.name =		"enable-uti",
		.has_arg =	no_argument,
		.flag =		&enable_uti,
		.val =		1,
	},
#ifdef ENABLE_TOFU
	{
		.name =		"enable-tofu",
		.has_arg =	no_argument,
		.flag =		&enable_tofu,
		.val =		1,
	},
#endif
	{
		.name =		"debug-mcexec",
		.has_arg =	no_argument,
		.flag =		&debug,
		.val =		1,
	},
	{
		.name =		"flags",
		.has_arg =	required_argument,
		.flag =		NULL,
		.val =		'f',
	},
	/* end */
	{ NULL, 0, NULL, 0, },
};
