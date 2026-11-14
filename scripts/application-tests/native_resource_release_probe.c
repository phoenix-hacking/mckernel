/* SPDX-License-Identifier: GPL-2.0 */
/* Disposable, exclusive Linux-side guest only; external bounded supervisor required.
 * Run ONLY after a separately accepted Running5 -> shutdown0 -> NotBooted0 trace.
 * Profile before boot: OS0 owned CPU1 and 128MiB node0; exclusive guest.
 * Successful matched shutdown already returns CPU1 online/unowned and memory
 * to the reserved pool. Do not release CPU1 again or treat close as teardown.
 * This observes public inventory/release, NOT physical/generation restoration.
 * Stop at first failure; retain guest and logs for dispatcher-owned cleanup.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include <ihk/ihk_host_user.h>

#ifndef RELEASE_OPEN
#define RELEASE_OPEN open
#define RELEASE_IOCTL ioctl
#define RELEASE_CLOSE close
#define RELEASE_READ read
#endif

#define CAPACITY 4096
#define BYTES (128UL * 1024 * 1024)
_Static_assert(sizeof(void *) == 8 && sizeof(size_t) == 8, "LP64 only");
_Static_assert(sizeof(struct ihk_cpu_req) == 16, "CPU request ABI");
_Static_assert(sizeof(struct ihk_mem_req) == 32, "memory request ABI");
_Static_assert(IHK_DEVICE_DESTROY_OS == 0x112901, "destroy ABI");
_Static_assert(IHK_DEVICE_RELEASE_CPU == 0x112903, "CPU release ABI");
_Static_assert(IHK_DEVICE_RELEASE_MEM == 0x112905, "memory release ABI");
_Static_assert(IHK_DEVICE_QUERY_CPU == 0x112906, "CPU query ABI");
_Static_assert(IHK_DEVICE_QUERY_MEM == 0x112907, "memory query ABI");
_Static_assert(IHK_OS_RELEASE_CPU == 0x112a23, "OS CPU release ABI");
_Static_assert(IHK_OS_RELEASE_MEM == 0x112a25, "OS memory release ABI");
_Static_assert(IHK_OS_QUERY_CPU == 0x112a26, "OS CPU query ABI");
_Static_assert(IHK_OS_QUERY_MEM == 0x112a27, "OS memory query ABI");
_Static_assert(IHK_OS_QUERY_STATUS == 0x112a03 && IHK_OS_STATUS_NOT_BOOTED == 0,
               "NotBooted ABI");

static int event(const char *stage, unsigned long request, int rc, int error)
{
    if (printf("{\"stage\":\"%s\",\"request\":%lu,\"return\":%d,\"errno\":%d,"
               "\"linux_result\":%d}\n", stage, request, rc, error,
               rc == -1 ? -error : rc) < 0)
        return -1;
    return fflush(stdout);
}

static int command(int fd, const char *stage, unsigned long request, unsigned long arg)
{
    int rc, error;
    errno = 0;
    rc = RELEASE_IOCTL(fd, request, arg);
    error = errno;
    if (event(stage, request, rc, error) != 0)
        return -1;
    return rc;
}

static int open_logged(const char *path, const char *stage, int flags)
{
    int rc, error;
    errno = 0;
    rc = RELEASE_OPEN(path, flags | O_CLOEXEC | O_NOFOLLOW);
    error = errno;
    if (event(stage, 0, rc, error) != 0) {
        if (rc >= 0) (void)RELEASE_CLOSE(rc);
        return -1;
    }
    return rc;
}

static int close_logged(int fd, const char *stage)
{
    int rc, error;
    errno = 0;
    rc = RELEASE_CLOSE(fd);
    error = errno;
    return event(stage, 0, rc, error) == 0 && rc == 0 ? 0 : -1;
}

static int online(const char *stage, char expected)
{
    char text[3] = {0};
    int fd = open_logged("/sys/devices/system/cpu/cpu1/online", stage, O_RDONLY);
    int good = 0;
    if (fd < 0) return -1;
    errno = 0;
    int rc = (int)RELEASE_READ(fd, text, sizeof(text));
    int error = errno;
    if (event("cpu_online_read", 0, rc, error) == 0 && rc == 2 &&
        text[0] == expected && text[1] == '\n') good = 1;
    if (printf("{\"stage\":\"cpu_online_value\",\"value\":%d}\n",
               rc == 2 ? text[0] - '0' : -1) < 0 || fflush(stdout) != 0) good = 0;
    if (close_logged(fd, "cpu_online_close") != 0) good = 0;
    return good ? 0 : -1;
}

static int cpu_inventory(int fd, const char *stage, unsigned long request, int expected)
{
    int cpus[4] = {-1, -1, -1, -1};
    struct ihk_cpu_req req = {cpus, expected};
    if (command(fd, stage, request, (unsigned long)&req) != 0) return -1;
    if (req.num_cpus < 0 || req.num_cpus > 4) return -1;
    if (printf("{\"stage\":\"cpu_inventory\",\"count\":%d,\"cpus\":[", req.num_cpus) < 0)
        return -1;
    for (int i = 0; i < req.num_cpus; i++)
        if (printf("%s%d", i ? "," : "", cpus[i]) < 0) return -1;
    if (printf("]}\n") < 0 || fflush(stdout) != 0) return -1;
    return req.num_cpus == expected && (expected == 0 || cpus[0] == 1) ? 0 : -1;
}

static size_t sizes[CAPACITY];
static int nodes[CAPACITY];
static int memory_inventory(int fd, const char *stage, unsigned long request,
                            size_t expected, struct ihk_mem_req *out)
{
    struct ihk_mem_req req = {sizes, nodes, CAPACITY, 0, 0, 0};
    if (command(fd, stage, request, (unsigned long)&req) != 0) return -1;
    if (req.num_chunks < 0 || req.num_chunks > CAPACITY) return -1;
    size_t total = 0;
    if (printf("{\"stage\":\"memory_inventory\",\"chunks\":[") < 0) return -1;
    for (int i = 0; i < req.num_chunks; i++) {
        if (sizes[i] == 0 || sizes[i] % 4096 || nodes[i] != 0 || sizes[i] > BYTES - total)
            return -1;
        total += sizes[i];
        if (printf("%s[%zu,%d]", i ? "," : "", sizes[i], nodes[i]) < 0) return -1;
    }
    if (printf("],\"bytes\":%zu}\n", total) < 0 || fflush(stdout) != 0) return -1;
    *out = req;
    return total == expected ? 0 : -1;
}

static int unavailable(int fd, const char *stage, const char *resource,
                       unsigned long request, unsigned long argument)
{
    int rc, error;
    errno = 0;
    rc = RELEASE_IOCTL(fd, request, argument);
    error = errno;
    if (event(stage, request, rc, error) != 0 || rc != -1 || error != EBUSY)
        return -1;
    if (printf("{\"stage\":\"os_inventory_unavailable\",\"resource\":\"%s\","
               "\"reason\":\"closed_admission\"}\n", resource) < 0)
        return -1;
    return fflush(stdout);
}

int main(int argc, char **argv)
{
    int control = -1, os = -1, result = 1;
    int cpu = -1;
    struct ihk_cpu_req cpu_req = {&cpu, 0};
    struct ihk_mem_req mem_req;
    (void)argv;
    if (argc != 1) { fputs("usage: native-resource-release-probe\n", stderr); return 2; }
    control = open_logged("/dev/mcd0", "open_control", O_RDWR);
    if (control < 0) goto out;
    os = open_logged("/dev/mcos0", "open_os", O_RDWR);
    if (os < 0) goto out;
    if (command(os, "status_after_external_stop", IHK_OS_QUERY_STATUS, 0) != 0 ||
        online("online_before_release", '1') != 0 ||
        cpu_inventory(control, "reserved_cpu_before", IHK_DEVICE_QUERY_CPU, 0) != 0 ||
        memory_inventory(control, "reserved_mem_before", IHK_DEVICE_QUERY_MEM, BYTES, &mem_req) != 0 ||
        unavailable(os, "assigned_cpu_unavailable", "cpu", IHK_OS_QUERY_CPU,
                    (unsigned long)&cpu_req) != 0)
        goto out;
    mem_req = (struct ihk_mem_req){sizes, nodes, CAPACITY, 0, 0, 0};
    if (unavailable(os, "assigned_mem_unavailable", "memory", IHK_OS_QUERY_MEM,
                    (unsigned long)&mem_req) != 0) goto out;
    { int fd = os; os = -1; if (close_logged(fd, "close_os") != 0) goto out; }
    if (command(control, "destroy_os", IHK_DEVICE_DESTROY_OS, 0) != 0 ||
        cpu_inventory(control, "reserved_cpu_returned", IHK_DEVICE_QUERY_CPU, 0) != 0 ||
        memory_inventory(control, "reserved_mem_returned", IHK_DEVICE_QUERY_MEM, BYTES, &mem_req) != 0 ||
        command(control, "release_device_mem", IHK_DEVICE_RELEASE_MEM, (unsigned long)&mem_req) != 0 ||
        cpu_inventory(control, "reserved_cpu_final", IHK_DEVICE_QUERY_CPU, 0) != 0 ||
        memory_inventory(control, "reserved_mem_final", IHK_DEVICE_QUERY_MEM, 0, &mem_req) != 0 ||
        online("online_after_release", '1') != 0) goto out;
    result = 0;
out:
    if (os >= 0 && close_logged(os, "close_os_failure") != 0) result = 1;
    if (control >= 0 && close_logged(control, "close_control") != 0) result = 1;
    if (result == 0 && (puts("{\"schema\":\"native-resource-release-v2\",\"result\":\"PASS_PUBLIC_RELEASE\",\"physical_identity_verified\":false,\"generation_verified\":false,\"reboot_verified\":false}") < 0 || fflush(stdout) != 0))
        result = 1;
    return result;
}
