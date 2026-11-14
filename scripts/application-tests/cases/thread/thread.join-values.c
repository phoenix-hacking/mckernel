#define _GNU_SOURCE

#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

static void *worker(void *arg) {
    return (void *)(intptr_t)(0x100 + *(int *)arg);
}

static int run(int n) {
    pthread_t tids[8]; int args[8];
    for (int i = 0; i < n; ++i) {
        args[i] = i;
        if (pthread_create(&tids[i], NULL, worker, &args[i]) != 0) return 0;
    }
    for (int i = 0; i < n; ++i) {
        void *value = NULL;
        if (pthread_join(tids[i], &value) != 0 || value != (void *)(intptr_t)(0x100 + i)) return 0;
    }
    return 1;
}

int main(void) {
    int ok2 = run(2), ok4 = run(4), ok8 = run(8);
    printf("n=2 join_ok=%d n=4 join_ok=%d n=8 join_ok=%d\n", ok2, ok4, ok8);
    return (ok2 && ok4 && ok8) ? EXIT_SUCCESS : EXIT_FAILURE;
}
