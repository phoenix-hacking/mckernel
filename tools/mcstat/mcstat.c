/*
 * mcstat -- reports McKernel statistis
 *	mcstat [-h] 
 *	mcstat [-n]  [delay [ count]]
 *	mcstat [-s] 
 *	mcstat [-c] 
 */
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/ioctl.h>
#include <fcntl.h>
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <getopt.h>
#include <errno.h>

#include <ihk/ihklib.h>
#include <ihk/ihk_host_user.h>
#include <ihk/ihk_rusage.h>	// ihk_os_rusage is defined here

#define MAX_CPUS	256
#define MiB100		(100*1024*1024) // 100 MiB
#define MiB		(1024*1024)
#define GiB		(1024*1024*1024)
#define CONV_UNIT(d)	(((float)(d))/scale)

#ifdef MCSTAT_RUST_HELPERS
extern unsigned long mcstat_memory_scale_result(unsigned long max_usage);
extern const char *mcstat_memory_unit_result(unsigned long max_usage);
extern unsigned char mcstat_update_counter_result(unsigned char counter);
extern int mcstat_parse_i32_result(const char *arg);
extern int mcstat_mcos_path_result(char *path, int index);
extern unsigned long mcstat_memory_total_result(const unsigned long *values,
		int count);
extern unsigned long mcstat_memory_current_result(unsigned long kmem_usage,
		const unsigned long *numa_values, int count);
extern unsigned long mcstat_memory_max_result(unsigned long kmem_max_usage,
		unsigned long user_max_usage);
extern const char *mcstat_monstatus_result(int status);
extern const char *mcstat_os_status_result(int status);
#else
static unsigned long mcstat_memory_scale_result(unsigned long max_usage)
{
	return max_usage < MiB100 ? MiB : GiB;
}

static const char *mcstat_memory_unit_result(unsigned long max_usage)
{
	return max_usage < MiB100 ? "MB" : "GB";
}

static unsigned char mcstat_update_counter_result(unsigned char counter)
{
	return (counter + 1) % 10;
}

static int mcstat_parse_i32_result(const char *arg)
{
	return atoi(arg);
}
#endif

struct my_rusage {
	struct ihk_os_rusage rusage;

	/* Initial amount posted to allocator. Note that the amount
	 * used before the initialization is not included.
	 */
	unsigned long memory_total;

	/* Current of sum of kernel and user */
	unsigned long memory_cur_usage;

	/* Max of sum of kernel and user */
	unsigned long memory_max_usage;
};

struct my_rusage rbuf;

static void	mcstatistics(int idx, int once, int delay, int count);
static int	mcstatus(int idx, int delay, int count);
static void	mcosusage(int idx, int once, int delay, int count);

static void
usage()
{
    fprintf(stderr, "Usage: mcstat [-h|-n|-s] [delay [count]]\n");
}

int
main(int argc, char **argv)
{
	int rc;
    int		opt;
    int		idx = 0;	/* index of OS instance */
    int		sflag = 0;	/* statistic option */
    int		cflag = 0;	/* cpu info */
    int		once = 0;	/* header is shown once */
    int		delay = 0;	/* delay in second */
    int		count = 1;	/* */

    if (argc > 1) {
        while ((opt = getopt(argc, argv, "chns")) != -1) {
            switch (opt) {
	    case 'c':	/* cpu info */
		cflag = 1; break;
	    case 'h':
		usage(); exit(0);
	    case 'n':
		once = 1; break;
	    case 's':	/* status */
		sflag = 1; break;
	    }
	}
    }
	if (optind < argc) { /* interval */
	delay = mcstat_parse_i32_result(argv[optind]);
	if (optind + 1 < argc) { /* count */
	    count = mcstat_parse_i32_result(argv[optind+1]);
	} else {
	    count = -1; /* inifi */
	}
    }

	if (sflag) {
		if ((rc = mcstatus(idx, delay, count)) < 0) {
			goto out;
		}
	} else if (cflag) {
		mcosusage(idx, once, delay, count);
	} else {
		mcstatistics(idx, once, delay, count);
	}

	rc = 0;
out:
	return rc;
}

static int
devopen(int idx)
{
    int		fd;
    char	fn[128];

#ifdef MCSTAT_RUST_HELPERS
    mcstat_mcos_path_result(fn, idx);
#else
    snprintf(fn, 128, "/dev/mcos%d", idx);
#endif
    fd = open(fn, O_RDONLY);
    return fd;
}

static void
statistics_header(const char *unit)
{
    printf("------- memory (%s) ------- ------- tsc ------ --- thread ---\n",
	   unit);
    printf("    total  current      max    system     user current max\n");
}

/*
 * Device should be open in each ioctl time. Otherwise, this command grabs
 * the device, and cannot be rebooted by others.
 */
static int
mygetrusage(int idx, struct my_rusage *rbp)
{
	int rc;
	int num_numa_nodes;
#ifndef MCSTAT_RUST_HELPERS
	int i;
#endif
	unsigned long *memtotal = NULL;

	rc = ihk_os_getrusage(idx, &rbp->rusage,
			      sizeof(struct ihk_os_rusage));
	if (rc) {
		printf("%s: error: ihk_os_getrusage: %s\n",
		       __func__, strerror(-rc));
		goto out;
	}

	num_numa_nodes = ihk_os_get_num_numa_nodes(idx);
	if (num_numa_nodes <= 0) {
		printf("%s: error: ihk_os_get_num_numa_nodes: %d\n",
		       __func__, num_numa_nodes);
		rc = num_numa_nodes < 0 ? num_numa_nodes : -EINVAL;
		goto out;
	}

	/* Calculate total by taking a sum over NUMA nodes */

	memtotal = calloc(num_numa_nodes, sizeof(unsigned long));
	if (!memtotal) {
		printf("%s: error: assigining memory\n",
		       __func__);
		rc = -ENOMEM;
		goto out;
	}

	rc = ihk_os_query_total_mem(idx, memtotal, num_numa_nodes);
	if (rc) {
		printf("%s: error: ihk_os_query_total_mem: %s\n",
		       __func__, strerror(-rc));
		goto out;
	}

#ifdef MCSTAT_RUST_HELPERS
	rbp->memory_total =
		mcstat_memory_total_result(memtotal, num_numa_nodes);
#else
	rbp->memory_total = 0;
	for (i = 0; i < num_numa_nodes; i++) {
		rbp->memory_total += memtotal[i];
	}
#endif

	/* Calculate current by taking a sum over NUMA nodes */

#ifdef MCSTAT_RUST_HELPERS
	rbp->memory_cur_usage =
		mcstat_memory_current_result(rbp->rusage.memory_kmem_usage,
				rbp->rusage.memory_numa_stat, num_numa_nodes);
#else
	rbp->memory_cur_usage = rbp->rusage.memory_kmem_usage;
	for (i = 0; i < num_numa_nodes; i++) {
		rbp->memory_cur_usage += rbp->rusage.memory_numa_stat[i];
	}
#endif

	/* Calculate max by taking a sum of kernel and user */

#ifdef MCSTAT_RUST_HELPERS
	rbp->memory_max_usage =
		mcstat_memory_max_result(rbp->rusage.memory_kmem_max_usage,
				rbp->rusage.memory_max_usage);
#else
	rbp->memory_max_usage = rbp->rusage.memory_kmem_max_usage +
		rbp->rusage.memory_max_usage;
#endif

	rc = 0;
out:
	free(memtotal);
	return rc;
}

static void
mcstatistics(int idx, int once, int delay, int count)
{
    int		i;
    unsigned long scale;
    const char	*unit;
    unsigned char show = 0;

    if (mygetrusage(idx, &rbuf) < 0) {
	printf("Device has not been created.\n");
	exit(-1);
    }
	scale = mcstat_memory_scale_result(rbuf.rusage.memory_max_usage);
	unit = mcstat_memory_unit_result(rbuf.rusage.memory_max_usage);
    statistics_header(unit);
    for (;;) {

	printf("%9.3f%9.3f%9.3f %9ld%9ld %7d %3d\n",
	       CONV_UNIT(rbuf.memory_total),
	       CONV_UNIT(rbuf.memory_cur_usage),
	       CONV_UNIT(rbuf.memory_max_usage),
	       rbuf.rusage.cpuacct_stat_system, rbuf.rusage.cpuacct_stat_user,
	       rbuf.rusage.num_threads, rbuf.rusage.max_num_threads);
	if (count > 0 && --count == 0) break;
	sleep(delay);
	if (mygetrusage(idx, &rbuf) < 0) {
	    printf("Device is now invisible.\n");
	    break;
	}
	if (!once) {
	    show = mcstat_update_counter_result(show);
	    if (show == 0) {
		statistics_header(unit);
	    }
	}
    }
/*
	?? /1000000
  	rusage->cpuacct_stat_system = st / 10000000;
	rusage->cpuacct_stat_user = ut / 10000000;
	rusage->cpuacct_usage = ut;
	printf("cpuacct_usage = %x\n", rbuf.rusage.cpuacct_usage);
*/
	for (i = 0; i < rbuf.rusage.max_num_threads; i++) {
		printf("cpuacct_usage_percpu[%d] = %ld\n",
		       i, rbuf.rusage.cpuacct_usage_percpu[i]);
	}
}

/* ihk_os_status enum is defined in ihk/linux/include/ihk/status.h */
#ifndef MCSTAT_RUST_HELPERS
static char *charstat[] = {
	[IHK_OS_STATUS_NOT_BOOTED] = "None",
	[IHK_OS_STATUS_BOOTING] = "Booting",
	[IHK_OS_STATUS_BOOTED] = "Booted",	/* OS booted and acked */
	[IHK_OS_STATUS_READY] = "Ready",	/* OS is ready and fully functional */
	[IHK_OS_STATUS_RUNNING] = "Running",	/* OS is running */
	[IHK_OS_STATUS_FREEZING] = "Freezing",	/* OS is freezing */
	[IHK_OS_STATUS_FROZEN] = "Frozen",	/* OS is frozen */
	[IHK_OS_STATUS_SHUTDOWN] = "Shutdown",	/* OS is shutting down */
	[IHK_OS_STATUS_FAILED] = "Panic",	/* OS panics or failed to boot */
	[IHK_OS_STATUS_HUNGUP] = "Hangup",	/* OS is hungup */
	[IHK_OS_STATUS_COUNT] = NULL,		/* End mark */
};

static const char *
mcstat_os_status_result(int status)
{
	return charstat[status];
}
#endif

/* Return value:
 *	Zero or positive:	IHK_OS_STATUS value
 *	Negative:		Error
 */
static int
mcstatus(int idx, int delay, int count)
{
	int fd = -1, rc = 0;

	for (;;) {
		if ((fd = devopen(idx)) == -1) {
			rc = -errno;
			printf("Device not found\n");
			goto next;
		}

		rc = ioctl(fd, IHK_OS_STATUS, 0);
		if (rc == -1) {
			rc = -errno;
			printf("%s: error: IHK_OS_STATUS: %s\n",
			       __func__, strerror(-rc));
			break;
		}

		close(fd);
		fd = -1;

		if (rc < 0 && rc >= IHK_OS_STATUS_COUNT) {
			printf("%s: error: status (%d) out of range\n",
			       __func__, rc);
			rc = -EINVAL;
			break;
		}

		printf("McKernel status: %s\n",
		       mcstat_os_status_result(rc) ? : "Unknown");

next:
		if (count > 0 && --count == 0) {
			break;
		}
		sleep(delay);
	}

	if (fd != -1) {
		close(fd);
	}
	return rc;
}

/* status is not contiguous numbers */
#ifndef MCSTAT_RUST_HELPERS
static const char *
monstatus(int status)
{
    switch (status) {
    case IHK_OS_MONITOR_NOT_BOOT:	return "boot";
    case IHK_OS_MONITOR_IDLE:		return "idle";
    case IHK_OS_MONITOR_USER:		return "user mode";
    case IHK_OS_MONITOR_KERNEL:		return "kernel mode";
    case IHK_OS_MONITOR_KERNEL_HEAVY:   return "kernel mode";
    case IHK_OS_MONITOR_KERNEL_OFFLOAD:	return "offload";
    case IHK_OS_MONITOR_KERNEL_FREEZING:return "freezing";
    case IHK_OS_MONITOR_KERNEL_FROZEN:	return "frozen";
    case IHK_OS_MONITOR_KERNEL_THAW:	return "thaw";
    case IHK_OS_MONITOR_PANIC:	return "panic";
    }
    return "";
}
#else
#define monstatus mcstat_monstatus_result
#endif

static void
osusage_header()
{
    printf("--cpu-- --status-- --count--\n");
}

static void
mcosusage(int idx, int once, int delay, int count)
{
    int		fd, i, rc;
    int		ncpus;
    unsigned char show = 0;
    struct ihk_os_cpu_monitor	mon[MAX_CPUS];

	if (mygetrusage(idx, &rbuf) < 0) {
		printf("Device has not been created.\n");
	}
	ncpus = rbuf.rusage.max_num_threads;
    osusage_header();
    for(;;) {
	if ((fd = devopen(idx)) < 0) {
	    printf("Devide is not created\n");
	} else {
	    rc = ioctl(fd, IHK_OS_GET_CPU_USAGE, &mon);
	    close(fd);
	    if (rc != 0) {
		printf("ioctl error(IHK_OS_GET_CPU_USAGE)\n");
		break;
	    }
	    for (i = 0; i < ncpus; i++) {
		printf("%6d: %10s %9ld\n",
		       i, monstatus(mon[i].status), mon[i].counter);
	    }
	}
	if (count > 0 && --count == 0) break;
	sleep(delay);
	if (!once) {
	    show = mcstat_update_counter_result(show);
	    if (show == 0) {
		osusage_header();
	    }
	}
    }
}
