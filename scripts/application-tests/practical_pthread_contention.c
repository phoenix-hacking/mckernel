/* Deterministic contention diagnostic. Frozen success oracle:
 * stdout: try_busy=1 timed_out=1 handoff=1 joined=1 tls=1\n
 * stderr: empty; status: 0. This is not the original core-thread fixture.
 * Main retains primary until the worker reports EBUSY and ETIMEDOUT through
 * a different mutex/condition variable. No scheduler ordering can avoid that
 * contention. Destruction happens only after successful worker join.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <unistd.h>

static pthread_mutex_t primary;
static pthread_mutex_t report_mutex;
static pthread_cond_t report_changed;
static int reported;
static int counter;
static int worker_tls;
static _Thread_local int tls_value;
static char joined_token;
_Alignas(4096) static unsigned char worker_stack[262144];

static void fatal(const char *operation, int error) {
    /* Process exit retains the stack and synchronization storage until every
     * thread exits; a failed join never triggers destroy or stack reuse. */
    (void)fprintf(stderr, "fatal=%s error=%d\n", operation, error);
    _Exit(EXIT_FAILURE);
}
static void check(const char *operation, int error) {
    if (error != 0) fatal(operation, error);
}
static struct timespec deadline(long milliseconds) {
    struct timespec result;
    if (clock_gettime(CLOCK_REALTIME, &result) != 0) fatal("clock_gettime", errno);
    result.tv_sec += milliseconds / 1000;
    result.tv_nsec += (milliseconds % 1000) * 1000000L;
    if (result.tv_nsec >= 1000000000L) {
        ++result.tv_sec;
        result.tv_nsec -= 1000000000L;
    }
    return result;
}
static void *worker(void *unused) {
    (void)unused;
    tls_value = 202;
    int result = pthread_mutex_trylock(&primary);
    if (result != EBUSY) fatal("trylock_expected_EBUSY", result);
    struct timespec until = deadline(100);
    result = pthread_mutex_timedlock(&primary, &until);
    if (result != ETIMEDOUT) fatal("timedlock_expected_ETIMEDOUT", result);

    check("report_lock_worker", pthread_mutex_lock(&report_mutex));
    reported = 1;
    check("report_signal", pthread_cond_signal(&report_changed));
    check("report_unlock_worker", pthread_mutex_unlock(&report_mutex));

    check("handoff_lock", pthread_mutex_lock(&primary));
    ++counter;
    worker_tls = tls_value;
    check("handoff_unlock", pthread_mutex_unlock(&primary));
    return &joined_token;
}
int main(void) {
    /* Default SIGALRM bounds a broken lock/join path even before the external
     * runner's 10-second timeout. No handler touches shared synchronization. */
    if (signal(SIGALRM, SIG_DFL) == SIG_ERR) fatal("signal", errno);
    (void)alarm(9);
    tls_value = 101;
    check("primary_init", pthread_mutex_init(&primary, NULL));
    check("report_init", pthread_mutex_init(&report_mutex, NULL));
    check("condition_init", pthread_cond_init(&report_changed, NULL));
    pthread_attr_t attr;
    check("attr_init", pthread_attr_init(&attr));
    check("attr_setstack", pthread_attr_setstack(&attr, worker_stack, sizeof(worker_stack)));
    check("primary_lock_main", pthread_mutex_lock(&primary));
    pthread_t thread;
    check("create", pthread_create(&thread, &attr, worker, NULL));

    check("report_lock_main", pthread_mutex_lock(&report_mutex));
    struct timespec until = deadline(5000);
    while (!reported)
        check("report_wait", pthread_cond_timedwait(&report_changed, &report_mutex, &until));
    check("report_unlock_main", pthread_mutex_unlock(&report_mutex));
    check("primary_unlock_main", pthread_mutex_unlock(&primary));
    void *returned = NULL;
    check("join", pthread_join(thread, &returned));
    if (returned != &joined_token || counter != 1 || worker_tls != 202 || tls_value != 101)
        fatal("handoff_join_TLS", EIO);

    check("attr_destroy", pthread_attr_destroy(&attr));
    check("condition_destroy", pthread_cond_destroy(&report_changed));
    check("report_destroy", pthread_mutex_destroy(&report_mutex));
    check("primary_destroy", pthread_mutex_destroy(&primary));
    (void)alarm(0);
    if (printf("try_busy=1 timed_out=1 handoff=1 joined=1 tls=1\n") < 0 || fflush(stdout) != 0)
        fatal("stdout", errno);
    return EXIT_SUCCESS;
}
