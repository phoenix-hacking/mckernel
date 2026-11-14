#define _GNU_SOURCE

#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

int main(void) {
    pthread_mutexattr_t attr; pthread_mutex_t mutex;
    if (pthread_mutexattr_init(&attr) != 0 || pthread_mutexattr_settype(&attr, PTHREAD_MUTEX_ERRORCHECK) != 0 ||
        pthread_mutex_init(&mutex, &attr) != 0) return EXIT_FAILURE;
    int first = pthread_mutex_lock(&mutex);
    int relock = pthread_mutex_lock(&mutex);
    int unlock = pthread_mutex_unlock(&mutex);
    int relock_after = pthread_mutex_lock(&mutex);
    int unlock_after = pthread_mutex_unlock(&mutex);
    pthread_mutex_destroy(&mutex); pthread_mutexattr_destroy(&attr);
    printf("first=%d relock=%d unlock=%d relock_after=%d unlock_after=%d deadlock=%d\n",
           first, relock, unlock, relock_after, unlock_after, relock == EDEADLK);
    return (first == 0 && relock == EDEADLK && unlock == 0 && relock_after == 0 &&
            unlock_after == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
