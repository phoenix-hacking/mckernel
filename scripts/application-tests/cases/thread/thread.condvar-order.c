#define _GNU_SOURCE

#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

enum { TOTAL = 10000, CAPACITY = 16 };
static pthread_mutex_t mutex;
static pthread_cond_t not_empty, not_full;
static int ring[CAPACITY], head, tail, count, consumed, last = -1;
static long long sum;
static int errors;

static void *producer(void *unused) {
    (void)unused;
    for (int value = 0; value < TOTAL; ++value) {
        pthread_mutex_lock(&mutex);
        while (count == CAPACITY) pthread_cond_wait(&not_full, &mutex);
        ring[tail] = value; tail = (tail + 1) % CAPACITY; ++count;
        pthread_cond_signal(&not_empty); pthread_mutex_unlock(&mutex);
    }
    return NULL;
}

static void *consumer(void *unused) {
    (void)unused;
    for (int i = 0; i < TOTAL; ++i) {
        pthread_mutex_lock(&mutex);
        while (count == 0) pthread_cond_wait(&not_empty, &mutex);
        int value = ring[head]; head = (head + 1) % CAPACITY; --count;
        pthread_cond_signal(&not_full); pthread_mutex_unlock(&mutex);
        if (value != last + 1) ++errors;
        last = value; sum += value; ++consumed;
    }
    return NULL;
}

int main(void) {
    pthread_t p, c;
    if (pthread_mutex_init(&mutex, NULL) != 0 || pthread_cond_init(&not_empty, NULL) != 0 ||
        pthread_cond_init(&not_full, NULL) != 0) return EXIT_FAILURE;
    if (pthread_create(&p, NULL, producer, NULL) != 0 || pthread_create(&c, NULL, consumer, NULL) != 0) return EXIT_FAILURE;
    pthread_join(p, NULL); pthread_join(c, NULL);
    printf("consumed=%d last=%d sum=%lld errors=%d remaining=%d\n", consumed, last, sum, errors, count);
    pthread_cond_destroy(&not_empty); pthread_cond_destroy(&not_full); pthread_mutex_destroy(&mutex);
    return (consumed == TOTAL && last == TOTAL - 1 && sum == 49995000 && errors == 0 && count == 0)
               ? EXIT_SUCCESS : EXIT_FAILURE;
}
