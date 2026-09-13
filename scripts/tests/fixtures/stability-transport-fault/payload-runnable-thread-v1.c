/* SPDX-License-Identifier: GPL-2.0-only */
/* Additive scheduling fixture. The original payload.c remains immutable.
 * No kernel/response writes: a real runnable peer lets the normal delegated
 * read path deschedule. The controller must independently observe wake == 2.
 * The controller and outer host watchdog bound both loops; there is no clock
 * or syscall in the spinner while the selected read is outstanding. */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include <errno.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

_Static_assert(ATOMIC_INT_LOCK_FREE == 2, "spinner requires lock-free unsigned atomics");

static atomic_uint spinner_started;
static atomic_uint spinner_done;
static int spinner_return_token;

static void *spin_until_done(void *argument)
{
    (void)argument;
    atomic_store_explicit(&spinner_started, 1, memory_order_release);
    while (!atomic_load_explicit(&spinner_done, memory_order_acquire)) {
        /* The atomic load is the complete loop body; no delegated operation. */
    }
    return &spinner_return_token;
}

static void diagnostic(const char *stage, int pthread_error, int syscall_error)
{
    dprintf(2, "NATIVE_FAILURE_APPLICATION FAIL stage=%s pthread_error=%d errno=%d\n",
            stage, pthread_error, syscall_error);
}

static int stop_and_join(pthread_t spinner, int status)
{
    void *result = NULL;
    atomic_store_explicit(&spinner_done, 1, memory_order_release);
    int error = pthread_join(spinner, &result);
    if (error) {
        diagnostic("pthread-join", error, 0);
        return 1;
    }
    if (result != &spinner_return_token) {
        diagnostic("pthread-result", 0, 0);
        return 1;
    }
    return status;
}

int main(void)
{
    static const char ready[] = "NATIVE_FAILURE_READY\n";
    static const char passed[] = "NATIVE_FAILURE_PASS\n";
    pthread_attr_t attributes;
    pthread_t spinner;
    int error = pthread_attr_init(&attributes);
    if (error) {
        diagnostic("pthread-attr-init", error, 0);
        return 1;
    }
    error = pthread_attr_setstacksize(&attributes, 256U * 1024U);
    if (error) {
        diagnostic("pthread-stack-size", error, 0);
        int destroy_error = pthread_attr_destroy(&attributes);
        if (destroy_error) diagnostic("pthread-attr-destroy", destroy_error, 0);
        return 1;
    }
    error = pthread_create(&spinner, &attributes, spin_until_done, NULL);
    int destroy_error = pthread_attr_destroy(&attributes);
    if (error) {
        diagnostic("pthread-create", error, 0);
        if (destroy_error) diagnostic("pthread-attr-destroy", destroy_error, 0);
        return 1;
    }
    if (destroy_error) {
        diagnostic("pthread-attr-destroy", destroy_error, 0);
        return stop_and_join(spinner, 1);
    }
    while (!atomic_load_explicit(&spinner_started, memory_order_acquire)) {
        /* READY follows a store executed by the actual created thread. */
    }

    unsigned char buffer[32];
    memset(buffer, 0x5a, sizeof buffer);
    ssize_t result = write(1, ready, sizeof ready - 1);
    int saved_errno = result < 0 ? errno : 0;
    if (result != (ssize_t)(sizeof ready - 1)) {
        diagnostic("ready-write", 0, saved_errno);
        return stop_and_join(spinner, 1);
    }
    result = read(0, buffer + 8, 16);
    saved_errno = result < 0 ? errno : 0;
    if (result != 16) {
        diagnostic("read16", 0, saved_errno);
        return stop_and_join(spinner, 1);
    }
    for (unsigned i = 0; i < sizeof buffer; ++i) {
        if (buffer[i] != ((i >= 8 && i < 24) ? 0xa5 : 0x5a)) {
            diagnostic("guarded-buffer", 0, 0);
            return stop_and_join(spinner, 1);
        }
    }
    if (stop_and_join(spinner, 0)) return 1;
    result = write(1, passed, sizeof passed - 1);
    saved_errno = result < 0 ? errno : 0;
    if (result != (ssize_t)(sizeof passed - 1)) {
        diagnostic("pass-write", 0, saved_errno);
        return 1;
    }
    return 37;
}
