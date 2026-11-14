/* Actual complete producer body and source structs follow verbatim.
 * TEST ADAPTER: stop at first CREATE_PPD ioctl after copying its bytes.
 * No actual fork, fd, kernel ioctl, VM/provider or native ownership exercised. */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <stdarg.h>
#include <setjmp.h>
#include <pthread.h>
#include <semaphore.h>
#include <sys/mman.h>
#include <unistd.h>
#include <sched.h>
#define MCEXEC_UP_CREATE_PPD 0x30a0290e
#define MCEXEC_UP_GET_NUM_POOL_THREADS 0x30a02926
struct syscall_request {
	/* TID of requesting thread */
	int rtid;
	/*
	 * TID of target thread. Remote page fault response needs to designate the
	 * thread that must serve the request, 0 indicates any thread from the pool
	 */
	int ttid;
	unsigned long valid;
	unsigned long number;
	unsigned long args[6];
};

struct syscall_wait_desc {
	unsigned long cpu;
	struct syscall_request sr;
	int pid;
};

struct rpgtable_desc {
	uintptr_t rpgtable;
	uintptr_t start;
	uintptr_t len;
};
struct fork_sync {
	int status;
	volatile int success;
	sem_t sem;
};

struct fork_sync_container {
	pid_t pid;
	struct fork_sync_container *next;
	struct fork_sync *fs;
};

static int fd=77, ischild, n_threads;
static char dev[]="TEST-ADAPTER-NO-DEVICE";
static void *thread_data;
static struct fork_sync_container *fork_sync_top;
static pthread_mutex_t fork_sync_mutex=PTHREAD_MUTEX_INITIALIZER;
static jmp_buf stop_at_ioctl;
static unsigned char captured[24];
static int fixture_close(int ignored) { (void)ignored;return 0; }
static int opendev(void) { return 77; }
static void init_sigaction(void) { abort(); }
static int init_worker_threads(int ignored) { (void)ignored;abort(); }
static void join_all_threads(void) { abort(); }
static int fixture_ioctl(int f,unsigned long command,...) {
    if(f!=77||command!=MCEXEC_UP_CREATE_PPD) abort();
    va_list ap;va_start(ap,command);const void *p=va_arg(ap,const void *);
    memcpy(captured,p,sizeof captured);va_end(ap);longjmp(stop_at_ioctl,1);
}
#define close fixture_close
#define ioctl fixture_ioctl
#define __dprintf(...) ((void)0)
_Static_assert(sizeof(struct rpgtable_desc)==24,"LP64 descriptor only");
_Static_assert(offsetof(struct rpgtable_desc,rpgtable)==0,"root offset");
_Static_assert(offsetof(struct rpgtable_desc,start)==8,"start offset");
_Static_assert(offsetof(struct rpgtable_desc,len)==16,"length offset");

long mcexec_clone_child_bridge(struct syscall_wait_desc *w, void *sync)
{
	struct fork_sync *fs = sync;
	struct fork_sync_container *fp;
	struct fork_sync_container *fb;
	struct rpgtable_desc rpt;
	int ret = 1;

	ischild = 1;
	close(fd);
	fd = opendev();
	if (fd < 0) {
		fs->status = -errno;
		fprintf(stderr, "ERROR: opening %s\n", dev);
		goto fork_child_sync_pipe;
	}

	rpt.start = w->sr.args[1];
	rpt.len = w->sr.args[2];
	rpt.rpgtable = w->sr.args[3];
	if (ioctl(fd, MCEXEC_UP_CREATE_PPD, &rpt)) {
		fs->status = -errno;
		fprintf(stderr, "ERROR: creating PPD %s\n", dev);
		goto fork_child_sync_pipe;
	}

	init_sigaction();
	thread_data = NULL;
	__dprintf("pid(%d): signals and syscall threads OK\n", getpid());

	if ((ret = ioctl(fd, MCEXEC_UP_GET_NUM_POOL_THREADS)) < 0) {
		fprintf(stderr, "Error: obtaining thread pool count\n");
	}

	if (ret == 1) {
		n_threads = 4;
	}

	if ((ret = init_worker_threads(fd)) != 0) {
		fprintf(stderr, "%s: Error: creating worker threads: %s\n",
			__func__, strerror(-ret));
		close(fd);
		exit(1);
	}

fork_child_sync_pipe:
	for (fp = fork_sync_top; fp;) {
		fb = fp->next;
		if (fp->fs && fp->fs != fs) {
			munmap(fp->fs, sizeof(struct fork_sync));
		}
		free(fp);
		fp = fb;
	}
	fork_sync_top = NULL;

	sem_post(&fs->sem);
	if (fs->status) {
		exit(1);
	}

	pthread_mutex_init(&fork_sync_mutex, NULL);

	while (getppid() != 1 && fs->success == 0) {
		sched_yield();
	}

	if (fs->success == 0) {
		exit(1);
	}

	sem_destroy(&fs->sem);
	munmap(fs, sizeof(struct fork_sync));
	join_all_threads();
	return ret;
}

/* Only invented values are distinct fixture arguments, never saved guest facts. */
int fixture_capture_descriptor(uint64_t start,uint64_t length,uint64_t root,unsigned char *output) {
    struct syscall_wait_desc w={0};struct fork_sync fs={0};
    w.sr.args[1]=start;w.sr.args[2]=length;w.sr.args[3]=root;
    if(setjmp(stop_at_ioctl)==0) { mcexec_clone_child_bridge(&w,&fs);abort(); }
    memcpy(output,captured,sizeof captured);return 0;
}
