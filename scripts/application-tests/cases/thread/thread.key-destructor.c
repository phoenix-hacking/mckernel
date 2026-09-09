#define _GNU_SOURCE

#include <pthread.h>
#include <stdatomic.h>
#include <stdio.h>
#include <stdlib.h>

static pthread_key_t key;
static _Atomic int destructor_calls, destructor_value_ok;
static int token = 0x2a;
static void destructor(void *value) {
    if (value == &token) atomic_store(&destructor_value_ok, 1);
    atomic_fetch_add(&destructor_calls, 1);
}
static void *worker(void *unused) {
    (void)unused;
    if (pthread_setspecific(key, &token) != 0) return (void *)1;
    return NULL;
}

int main(void) {
    pthread_t tid; void *result = NULL;
    if (pthread_key_create(&key, destructor) != 0 || pthread_create(&tid, NULL, worker, NULL) != 0) return EXIT_FAILURE;
    if (pthread_join(tid, &result) != 0) return EXIT_FAILURE;
    int calls = atomic_load(&destructor_calls), value_ok = atomic_load(&destructor_value_ok);
    pthread_key_delete(key);
    printf("join_ok=%d result_ok=%d destructor_calls=%d value_ok=%d\n",
           result == NULL, result == NULL, calls, value_ok);
    return (result == NULL && calls == 1 && value_ok == 1) ? EXIT_SUCCESS : EXIT_FAILURE;
}
