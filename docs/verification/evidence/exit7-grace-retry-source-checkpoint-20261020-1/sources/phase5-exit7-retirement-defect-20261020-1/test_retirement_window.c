#define _GNU_SOURCE
#include <assert.h>
#include <dirent.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#define MS 1000000ull
static uint64_t collector_deadline;
static const uint64_t origin = 33649000000ull;
static uint64_t fake_now;
static unsigned scenario, directory_cursor, sleeps, retry_opportunities;
static int current_has_pid;
static int fake_clock_gettime(clockid_t clock, struct timespec *value)
{
    assert(clock == CLOCK_MONOTONIC);
    value->tv_sec = (time_t)(fake_now / 1000000000ull);
    value->tv_nsec = (long)(fake_now % 1000000000ull);
    return 0;
}
static DIR *fake_opendir(const char *path)
{
    assert(!strcmp(path, "/proc/mcos0"));
    directory_cursor = 0;
    if (scenario == 3 && fake_now >= origin + 2000 * MS) {
        errno = EIO; return NULL;
    }
    current_has_pid = (scenario == 1 && fake_now < origin + 500 * MS) ||
                      (scenario == 2 && fake_now >= origin + 4000 * MS) ||
                      scenario == 5;
    return (DIR *)(uintptr_t)1;
}
static struct dirent *fake_readdir(DIR *directory)
{
    static struct dirent entry;
    assert(directory == (DIR *)(uintptr_t)1);
    const char *name = directory_cursor == 0 ? "." :
                       directory_cursor == 1 ? ".." :
                       directory_cursor == 2 && current_has_pid ? "257" : NULL;
    directory_cursor++;
    if (!name) {
        if (scenario == 6 && fake_now >= origin + 2000 * MS) errno = EIO;
        return NULL;
    }
    strcpy(entry.d_name, name);
    return &entry;
}
static int fake_closedir(DIR *directory)
{
    assert(directory == (DIR *)(uintptr_t)1); return 0;
}
static int fake_nanosleep(const struct timespec *request, struct timespec *remaining)
{
    assert(!remaining && request->tv_sec == 0 && request->tv_nsec == 10000000);
    fake_now += 10 * MS;
    sleeps++;
    /* A retry OPPORTUNITY after the actual HOST66 next-second deadline;
     * this is deliberately no ACK, service execution, or retirement proof. */
    if (fake_now >= 34000000000ull) retry_opportunities++;
    return 0;
}
#define clock_gettime fake_clock_gettime
#define opendir fake_opendir
#define readdir fake_readdir
#define closedir fake_closedir
#include "actual_retirement_functions.inc"
#undef clock_gettime
#undef opendir
#undef readdir
#undef closedir
#define nanosleep fake_nanosleep
static int run_actual_retirement_loop(void)
{
    int empty = 0;
#include "actual_retirement_loop.inc"
    return empty;
}
#undef nanosleep
static void check(unsigned which, uint64_t cap_ms, int expected_empty,
                  uint64_t elapsed_ms)
{
    scenario = which; fake_now = origin; sleeps = retry_opportunities = 0;
    collector_deadline = cap_ms ? origin + cap_ms * MS : 0;
    int empty = run_actual_retirement_loop();
    assert(empty == expected_empty);
    assert(fake_now == origin + elapsed_ms * MS);
    assert(sleeps == elapsed_ms / 10);
    assert(retry_opportunities > 0);
}
int main(void)
{
    check(0, 0, 1, 5000); /* initially empty cannot terminate retry window */
    check(1, 0, 1, 5000); /* changing nonempty to empty does not terminate */
    check(2, 0, 0, 5000); /* late registration invalidates prior emptiness */
    check(3, 0, 0, 2000); /* unreadable directory refuses prior emptiness */
    check(0, 2000, 1, 2000); /* existing global deadline remains authoritative */
    check(5, 0, 0, 5000); /* persistent registration refuses empty */
    check(6, 0, 0, 2000); /* readdir error refuses earlier empty */
    puts("PASS 7 actual retirement-loop/clock/deadline/procfs-body vectors; no ACK or guest execution");
    return 0;
}
