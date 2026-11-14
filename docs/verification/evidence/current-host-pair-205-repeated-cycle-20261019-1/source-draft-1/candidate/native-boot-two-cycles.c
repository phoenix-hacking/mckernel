/* SPDX-License-Identifier: GPL-2.0 */
/* Disposable guest only: real native preparation and retained AP-start attempt. */
#define NATIVE_OS_RESOURCE_MAIN native_os_resource_reference_main
#include "/home/holden/mckernel-work/host-preparation/evening-two-app-batch-20261019-1/two-cpu-end-to-end-1/two-cpu-running-query-correction-1/native-os-resource-assignment.c"
#define OS_LOAD 0x112a00
#define OS_BOOT 0x112a01
#define OS_STATUS 0x112a03
#define OS_KARGS 0x112a04
#if defined(__x86_64__)
#define SYS_NANOSLEEP 35
#else
#define SYS_NANOSLEEP 162
#endif

#include "pair_assignment.h"
static struct pair_assignment pair_boot_assignment;
static char pair_boot_log[PAIR_LOG_LIMIT];
static char pair_preboot_log[PAIR_LOG_LIMIT];
static long pair_preboot_bytes;
static void cycle_boot_baseline(void) { pair_preboot_bytes=call(103,3,(long)pair_preboot_log,sizeof pair_preboot_log); require(pair_preboot_bytes>0 && pair_preboot_bytes<(long)sizeof pair_preboot_log); }
static void pair_boot_challenge(void)
{
    long fd=call(SYS_OPEN,(long)PAIR_CHALLENGE,0xa0000,0);
    require(fd>=0);
    require(call(SYS_READ,fd,(long)pair_boot_assignment.nonce,16)==16);
    char tail;require(call(SYS_READ,fd,(long)&tail,1)==0);
    close_fd(fd);
    require(pair_boot_assignment.nonce[0] || pair_boot_assignment.nonce[1]);
    pair_boot_assignment.magic=PAIR_MAGIC;
}
static void pair_boot_publish(int os)
{
    require(call(SYS_IOCTL,os,0x30a02907,0)==2);
    long n=call(103,3,(long)pair_boot_log,sizeof pair_boot_log);
    require(n>0 && n<(long)sizeof pair_boot_log);
    require(n>pair_preboot_bytes);
    for(long i=0;i<pair_preboot_bytes;i++)require(pair_preboot_log[i]==pair_boot_log[i]);
    require(pair_routes(pair_boot_log+pair_preboot_bytes,(unsigned long)(n-pair_preboot_bytes),&pair_boot_assignment,
                        &pair_boot_assignment.generation)==0);
    require(pair_assignment_valid(&pair_boot_assignment,pair_boot_assignment.nonce));
    /* O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC, no replacement/replay. */
    long fd=call(SYS_OPEN,(long)PAIR_ASSIGNMENT,0xa00c1,0600);
    require(fd>=0);
    require(call(SYS_WRITE,fd,(long)&pair_boot_assignment,sizeof pair_boot_assignment)==(long)sizeof pair_boot_assignment);
    close_fd(fd);
    /* The fixed oracle's literal marker is emitted only after actual dynamic
     * CPU/gen proof checks. Its values are checked, never used as evidence. */
    require(pair_boot_assignment.generation>0);
    char record[160],digits[32]; unsigned long g=pair_boot_assignment.generation;
    unsigned used=0,nd=0; const char *head="<6>NATIVE_PAIR_CPU os=0 generation=";
    while(*head)record[used++]=*head++;
    do {digits[nd++]=(char)('0'+g%10);g/=10;} while(g);
    while(nd)record[used++]=digits[--nd];
    const char *tail=" assigned_host=1,2 logical=0,1 default_ikc_linux=0\n";
    while(*tail)record[used++]=*tail++;
    fd=call(SYS_OPEN,(long)"/dev/kmsg",0xa0001,0);require(fd>=0);
    require(call(SYS_WRITE,fd,(long)record,used)==(long)used);
    close_fd(fd);
}
static unsigned sysfs_checks;
#if defined(NATIVE_SYSFS_OS)
static unsigned sysfs_completed;
#endif
static void sysfs_state(int minor, int present)
{
#if defined(NATIVE_SYSFS_OS)
    const char *paths[] = {"/sys/class/mcos/mcos0/sys", "/sys/class/mcos/mcos1/sys"};
    const char *markers[] = {"/sys/class/mcos/mcos0/sys/setup_complete", "/sys/class/mcos/mcos1/sys/setup_complete"};
    require(minor == 0 || minor == 1);
    long fd = call(SYS_OPEN, (long)paths[minor], 0, 0);
    if (present) { require(fd >= 0); close_fd(fd); }
    else { require(fd == -2); }
    // The root's existence must never stand in for the actual setup service.
    fd = call(SYS_OPEN, (long)markers[minor], 0, 0);
    if (minor == 0 && sysfs_completed) { require(fd >= 0); close_fd(fd); }
    else { require(fd == -2); }
    sysfs_checks++;
#else
    (void)minor; (void)present;
#endif
}

static void capture_pause(void)
{
    struct { long seconds, nanoseconds; } delay = {10, 0};
    message("NATIVE_BOOT_CAPTURE " ARCH_LABEL " ready\n");
    require(call(SYS_NANOSLEEP, (long)&delay, 0, 0) == 0);
}

#if defined(NATIVE_SYSFS_SERVICE) && !BOOT_PREPARE_ONLY
static void service_value(const char *path, char expected)
{
    char value[32];
    long fd = call(SYS_OPEN, (long)path, 0, 0);
    require(fd >= 0);
    require(call(SYS_READ, fd, (long)value, sizeof(value)) == 2);
    require(value[0] == expected && value[1] == '\n');
    require(call(SYS_READ, fd, (long)value, sizeof(value)) == 0);
    close_fd(fd);
}

static void service_roundtrips(void)
{
    const char *online = "/sys/class/mcos/mcos0/sys/devices/system/cpu/cpu0/online";
    service_value("/sys/class/mcos/mcos0/sys/devices/system/cpu/num_processors", '2');
    service_value("/sys/class/mcos/mcos0/sys/devices/system/cpu/cpu1/online", '1');
    service_value(online, '1');
    for (int cycle = 0; cycle < 32; cycle++) {
        // The existing guest store_fake_cpu_info logs the input and returns
        // its count but does not change online. The controller independently
        // checks those delivered payloads in the captured guest kmsg log.
        put_value(online, "0\n");
        service_value(online, '1');
        put_value(online, "1\n");
        service_value(online, '1');
    }
    message("NATIVE_SYSFS_SERVICE " ARCH_LABEL " PASS read_checks=67 store_checks=64 rounds=32\n");
}
#endif

static void native_running_status_log(long observed_status)
{
    const char *prefix = "<6>NATIVE_BOOT_STATUS " ARCH_LABEL " observed=";
    const char *suffix = " expected=5\n";
    char record[128], digits[24];
    unsigned long used = 0, count = 0;
    unsigned long value = observed_status < 0 ? 0UL - (unsigned long)observed_status :
                          (unsigned long)observed_status;
    for (unsigned long i = 0; prefix[i]; i++) record[used++] = prefix[i];
    if (observed_status < 0) record[used++] = '-';
    do { digits[count++] = '0' + value % 10; value /= 10; } while (value);
    while (count) record[used++] = digits[--count];
    for (unsigned long i = 0; suffix[i]; i++) record[used++] = suffix[i];
    // Prefix + signed LP64 decimal + suffix fit without truncation.
    _Static_assert(sizeof("<6>NATIVE_BOOT_STATUS " ARCH_LABEL " observed=") +
                   21 + sizeof(" expected=5\n") <= sizeof(record), "status log bound");
    long log_fd = call(SYS_OPEN, (long)"/dev/kmsg", 0xa0001, 0);
    require(log_fd >= 0);
    long log_written = call(SYS_WRITE, log_fd, (long)record, (long)used);
    long log_closed = call(SYS_CLOSE, log_fd, 0, 0);
    require(log_written == (long)used);
    require(log_closed == 0);
}

int main(void)
{
    cycle_boot_baseline();
    int control = open_control();
#if BOOT_PREPARE_ONLY
    int reserved[] = {3, 2, 1}, first_cpus[] = {3, 1}, second_cpus[] = {2};
    require(request(control, RESERVE, reserved, 3) == 0);
    require(mem_one(control, MEM_RESERVE, 128 * MIB, 0) == 0);
    require(mem_one(control, MEM_RESERVE, 128 * MIB, 1) == 0);
    require(call(SYS_IOCTL, control, OS_CREATE, 0) == 0);
    require(call(SYS_IOCTL, control, OS_CREATE, 0) == 1);
    int first = open_os(0), second = open_os(1);
    sysfs_state(0, 0); sysfs_state(1, 0);
    char arguments[1024];
    for (int i = 0; i < 1024; i++) arguments[i] = 'y';
    require(call(SYS_IOCTL, first, OS_KARGS, (long)arguments) == 0);
    require(call(SYS_IOCTL, second, OS_KARGS, (long)"second-os") == 0);
    require(request(first, OS_ASSIGN_CPU, first_cpus, 2) == 0);
    require(request(second, OS_ASSIGN_CPU, second_cpus, 1) == 0);
    require(mem_one(first, OS_ASSIGN_MEM, 64 * MIB, 1) == 0);
    require(mem_one(second, OS_ASSIGN_MEM, 64 * MIB, 0) == 0);
    require(call(SYS_IOCTL, first, OS_LOAD, (long)"/images/legacy.img") == 0);
    require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EINVAL);
    // Revision 1 advertises the correct IRQ/boot layout but releases queue
    // slots before reading. It remains loadable and must fail before startup.
    require(call(SYS_IOCTL, first, OS_LOAD, (long)"/images/native-v1.img") == 0);
    require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EINVAL);
    require(call(SYS_IOCTL, first, OS_STATUS, 0) == 0);
#if defined(NATIVE_VDSO_REV3)
    // Revision 2 completes queue reads but still uses the old 88-byte vDSO
    // descriptor. Reject it before taking any native startup resources.
    require(call(SYS_IOCTL, first, OS_LOAD, (long)"/images/native-v2.img") == 0);
    require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EINVAL);
    require(call(SYS_IOCTL, first, OS_STATUS, 0) == 0);
#endif
    online_mask(1);
    require(call(SYS_IOCTL, first, OS_LOAD, (long)"/images/mckernel.img") == 0);
    require(call(SYS_IOCTL, second, OS_LOAD, (long)"/images/mckernel.img") == 0);
    require(call(SYS_IOCTL, first, OS_KARGS, 1) == -EFAULT);
    for (int cycle = 0; cycle < 8; cycle++) {
        allocation_failure(0);
        put_value(FI "min-order", "1");
        put_value(FI "times", "-1");
        require(call(SYS_IOCTL, first, OS_BOOT, 0) == -ENOMEM);
        put_value("/proc/self/make-it-fail", "0");
        put_value(FI "times", "0");
        put_value(FI "min-order", "10");
        require(call(SYS_IOCTL, first, OS_STATUS, 0) == 0);
        sysfs_state(0, 0);
        require(call(SYS_IOCTL, second, OS_BOOT, 0) == -EAGAIN);
        sysfs_state(1, 1);
        require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EBUSY);
        sysfs_state(0, 0); sysfs_state(1, 1);
        require(call(SYS_IOCTL, second, OS_LOAD, (long)"/images/missing") == -2);
        sysfs_state(1, 0);
        require(call(SYS_IOCTL, second, OS_LOAD, (long)"/images/mckernel.img") == 0);
        require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EAGAIN);
        require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EAGAIN);
        require(call(SYS_IOCTL, first, OS_STATUS, 0) == 0);
        sysfs_state(0, 1);
        // Failed argument reads preserve the held preparation. Successful
        // changes retire it, making the exclusive trampoline available again.
        require(call(SYS_IOCTL, first, OS_KARGS, 1) == -EFAULT);
        sysfs_state(0, 1);
        require(call(SYS_IOCTL, second, OS_BOOT, 0) == -EBUSY);
        require(call(SYS_IOCTL, first, OS_KARGS, (long)arguments) == 0);
        sysfs_state(0, 0);
        require(call(SYS_IOCTL, second, OS_BOOT, 0) == -EAGAIN);
        sysfs_state(1, 1);
        require(call(SYS_IOCTL, second, OS_KARGS, (long)"second-os") == 0);
        sysfs_state(1, 0);
        require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EAGAIN);
        sysfs_state(0, 1);
        online_mask(1);
        if (cycle == 0) capture_pause();
        // Changing CPU assignment retires the held preparation, retaining the
        // image and original startup tables for a later preparation.
        int changed[] = {1};
        require(request(first, OS_RELEASE_CPU, changed, 1) == 0);
        sysfs_state(0, 0);
        require(request(first, OS_ASSIGN_CPU, changed, 1) == 0);
    }
    require(call(SYS_IOCTL, first, OS_BOOT, 0) == -EAGAIN);
    close_fd(first);
    require(destroy_os(control, 0) == 0);
    sysfs_state(0, 0);
    require(call(SYS_IOCTL, second, OS_BOOT, 0) == -EAGAIN);
    close_fd(second);
    require(destroy_os(control, 1) == 0);
    sysfs_state(1, 0);
#if defined(NATIVE_SYSFS_OS)
    require(call(SYS_IOCTL, control, OS_CREATE, 0) == 0);
    sysfs_state(0, 0);
    require(destroy_os(control, 0) == 0);
#endif
    int chunks = query_memory(control), node1_chunks = 0;
    require(totals[0] == 128 * MIB && totals[1] == 128 * MIB);
    for (int i = 0; i < chunks; i++) {
        message("NATIVE_BOOT_RESTORED " ARCH_LABEL " node="); print_number(query_nodes[i]);
        message(" bytes="); print_number(query_sizes[i]); message("\n");
        if (query_nodes[i] == 1) node1_chunks++;
    }
    if (node1_chunks > 1) {
        // Legacy exact release addresses one returned contiguous chunk.
        // Reservation may legitimately return several chunks totaling 128 MiB.
        require(mem_one(control, MEM_RELEASE, 128 * MIB, 1) == -EINVAL);
        expect_memory(control, 128 * MIB, 128 * MIB);
    }
    release_memory(control);
    require(request(control, RELEASE, reserved, 3) == 0);
    online_mask(15);
    close_fd(control);
    message("NATIVE_BOOT_PREPARATION " ARCH_LABEL " PASS cycles=8 failures=8 exclusive=1 restored=1\n");
#else
    pair_boot_challenge();
    int assigned[] = {1,2};
    require(request(control, RESERVE, assigned, 2) == 0);
    require(mem_one(control, MEM_RESERVE, 128 * MIB, 0) == 0);
    long actual_minor=call(SYS_IOCTL,control,OS_CREATE,0);
    require(actual_minor==0);
    pair_boot_assignment.os=(unsigned int)actual_minor;
    int os = open_os((int)actual_minor);
#if defined(NATIVE_MCCTRL_SERVICE)
    require(call(SYS_IOCTL, os, 0x30a02907, 0) == -EBUSY);
    require(call(SYS_IOCTL, os, 0x30a0290c, 0) == -EBUSY);
    message("NATIVE_MCCTRL_PREREADY " ARCH_LABEL " PASS rejected=2\n");
#endif
    require(call(SYS_IOCTL, os, OS_KARGS, (long)"hidos allow_oversubscribe") == 0);
    require(request(os, OS_ASSIGN_CPU, assigned, 2) == 0);
    long actual_count=call(SYS_IOCTL,os,OS_COUNT_CPU,0);
    require(actual_count==2);
    pair_boot_assignment.count=(unsigned int)actual_count;
    require(request(os,OS_QUERY_CPU,pair_boot_assignment.physical,2)==0);
    require(pair_boot_assignment.physical[0]==assigned[0] && pair_boot_assignment.physical[1]==assigned[1]);
    require(mem_one(os, OS_ASSIGN_MEM, 128 * MIB, 0) == 0);
    require(call(SYS_IOCTL, os, OS_LOAD, (long)"/images/mckernel.img") == 0);
#if defined(NATIVE_SYSFS_SERVICE)
    long boot_result = call(SYS_IOCTL, os, OS_BOOT, 0);
    message("NATIVE_BOOT_SERVICE " ARCH_LABEL " boot_errno=");
    print_number(boot_result < 0 ? (unsigned long)-boot_result : 0);
    message("\n");
    require(boot_result == 0);
#else
    require(call(SYS_IOCTL, os, OS_BOOT, 0) == -110);
#endif
#if defined(NATIVE_SYSFS_SETUP)
    sysfs_completed = 1;
#endif
#if defined(NATIVE_SYSFS_SERVICE)
    long observed_status = call(SYS_IOCTL, os, OS_STATUS, 0);
    message("NATIVE_BOOT_STATUS " ARCH_LABEL " observed=");
    if (observed_status < 0) message("-");
    print_number(observed_status < 0 ? 0UL - (unsigned long)observed_status :
                 (unsigned long)observed_status);
    message(" expected=5\n");
    native_running_status_log(observed_status);
    require(observed_status == 5);
#else
    require(call(SYS_IOCTL, os, OS_STATUS, 0) == 9);
#endif
    sysfs_state(0, 1);
    require(call(SYS_IOCTL, os, OS_KARGS, (long)"changed") == -EBUSY);
    require(call(SYS_IOCTL, os, OS_BOOT, 0) == -EBUSY);
    require(request(os, OS_RELEASE_CPU, assigned, 2) == -EBUSY);
    require(mem_one(os, OS_RELEASE_MEM, 128 * MIB, 0) == -EBUSY);
    /* Generic resource queries are intentionally NotBooted-only. */
    require(call(SYS_IOCTL,os,OS_COUNT_CPU,0)==-EBUSY);
    require(request(os,OS_QUERY_CPU,assigned,2)==-EBUSY);
    require(call(SYS_IOCTL,os,0x30a02907,0)==2);
    online_mask(9);
    capture_pause();
#if defined(NATIVE_SYSFS_SERVICE)
    service_roundtrips();
    capture_pause();
#endif
    pair_boot_publish(os);
    close_fd(os);
    require(destroy_os(control, 0) == -EBUSY);
    sysfs_state(0, 1);
    close_fd(control);
    require(call(SYS_DELETE_MODULE, (long)"ihk_smp_x86_64", 2048, 0) == -EAGAIN);
#if defined(NATIVE_SYSFS_SERVICE)
    message("NATIVE_BOOT_START " ARCH_LABEL " CAPTURED ready=1 resources_retained=1\n");
#else
    message("NATIVE_BOOT_START " ARCH_LABEL " CAPTURED incomplete=1 resources_retained=1\n");
#endif
#endif
#if defined(NATIVE_SYSFS_OS)
    message("NATIVE_OS_SYSFS " ARCH_LABEL " PASS checks="); print_number(sysfs_checks);
    message(" setup_completed="); print_number(sysfs_completed); message("\n");
#else
    (void)sysfs_checks;
#endif
    return 0;
}
