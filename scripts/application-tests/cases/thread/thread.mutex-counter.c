#define _GNU_SOURCE

#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>

static pthread_mutex_t mutex;
static int counter;
static _Atomic int errors;
static void *worker(void *unused) {
    (void)unused;
    for (int i = 0; i < 1000; ++i) {
        if (pthread_mutex_lock(&mutex) != 0) { atomic_fetch_add(&errors, 1); continue; }
        ++counter;
        if (pthread_mutex_unlock(&mutex) != 0) atomic_fetch_add(&errors, 1);
    }
    return NULL;
}

static int run(int n) {
    pthread_t tids[8]; counter = 0; atomic_store(&errors, 0);
    if (pthread_mutex_init(&mutex, NULL) != 0) return 0;
    int created = 0;
    for (; created < n; ++created)
        if (pthread_create(&tids[created], NULL, worker, NULL) != 0) break;
    for (int i = 0; i < created; ++i) pthread_join(tids[i], NULL);
    int ok = created == n && counter == n * 1000 && atomic_load(&errors) == 0;
    pthread_mutex_destroy(&mutex);
    return ok;
}

int main(void) {
    int ok2 = run(2), ok4 = run(4), ok8 = run(8);
    printf("n=2 counter_ok=%d n=4 counter_ok=%d n=8 counter_ok=%d\n", ok2, ok4, ok8);
    return (ok2 && ok4 && ok8) ? EXIT_SUCCESS : EXIT_FAILURE;
}
