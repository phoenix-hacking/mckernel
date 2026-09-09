#define _GNU_SOURCE

#include <pthread.h>
#include <sched.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>

static _Thread_local int tls_value;
static _Atomic int tls_ok;
static unsigned char stacks[8][262144];
struct arg { int id; };
static void *worker(void *opaque) {
    struct arg *a = opaque;
    tls_value = 1000 + a->id;
    if (tls_value == 1000 + a->id) atomic_fetch_add(&tls_ok, 1);
    return NULL;
}

static int run(int n) {
    pthread_t tids[8]; struct arg args[8]; pthread_attr_t attr;
    int parent = 77, created = 0;
    tls_value = parent; atomic_store(&tls_ok, 0);
    if (pthread_attr_init(&attr) != 0) return 0;
    for (int i = 0; i < n; ++i) {
        args[i].id = i;
        if (pthread_attr_setstack(&attr, stacks[i], sizeof(stacks[i])) != 0 ||
            pthread_create(&tids[i], &attr, worker, &args[i]) != 0) break;
        ++created;
    }
    for (int i = 0; i < created; ++i) pthread_join(tids[i], NULL);
    pthread_attr_destroy(&attr);
    return created == n && atomic_load(&tls_ok) == n && tls_value == parent;
}

int main(void) {
    int ok2 = run(2), ok4 = run(4), ok8 = run(8);
    printf("n=2 tls_ok=%d n=4 tls_ok=%d n=8 tls_ok=%d parent_tls_ok=%d\n",
           ok2, ok4, ok8, tls_value == 77);
    return (ok2 && ok4 && ok8 && tls_value == 77) ? EXIT_SUCCESS : EXIT_FAILURE;
}
