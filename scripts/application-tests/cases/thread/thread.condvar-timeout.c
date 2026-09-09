#define _GNU_SOURCE

#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <time.h>

static long long ns(const struct timespec *t) { return (long long)t->tv_sec * 1000000000LL + t->tv_nsec; }

int main(void) {
    pthread_condattr_t attr; pthread_cond_t cond; pthread_mutex_t mutex;
    struct timespec now, deadline;
    int predicate = 0;
    if (pthread_condattr_init(&attr) != 0 || pthread_condattr_setclock(&attr, CLOCK_MONOTONIC) != 0 ||
        pthread_cond_init(&cond, &attr) != 0 || pthread_mutex_init(&mutex, NULL) != 0 ||
        clock_gettime(CLOCK_MONOTONIC, &now) != 0) return EXIT_FAILURE;
    deadline = now; deadline.tv_nsec += 20000000L;
    if (deadline.tv_nsec >= 1000000000L) { ++deadline.tv_sec; deadline.tv_nsec -= 1000000000L; }
    pthread_mutex_lock(&mutex);
    int rc = pthread_cond_timedwait(&cond, &mutex, &deadline);
    int unchanged = predicate == 0;
    int unlock = pthread_mutex_unlock(&mutex);
    printf("rc=%d timedout=%d predicate=%d unchanged=%d unlock=%d\n", rc, rc == ETIMEDOUT,
           predicate, unchanged, unlock);
    pthread_mutex_destroy(&mutex); pthread_cond_destroy(&cond); pthread_condattr_destroy(&attr);
    return (rc == ETIMEDOUT && unchanged && unlock == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
