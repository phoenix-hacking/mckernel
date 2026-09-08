/* SPDX-License-Identifier: GPL-2.0 */
/* Small real libc applications for the pre-handoff execution baseline. */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

#define CHECK(value) do { if (!(value)) { \
    fprintf(stderr, "NATIVE_CORE FAIL line=%d errno=%d\n", __LINE__, errno); \
    exit(1); \
} } while (0)

static void memory_case(void)
{
    const size_t length = 64 * 4096;
    unsigned char *heap = malloc(length), *mapped;
    CHECK(heap != NULL);
    mapped = mmap(NULL, length, PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    CHECK(mapped != MAP_FAILED);
    for (size_t i = 0; i < length; ++i) {
        heap[i] = (unsigned char)((i * 17) ^ (i >> 8));
        mapped[i] = heap[i] ^ 0xa5;
    }
    CHECK(mprotect(mapped, 4096, PROT_READ) == 0);
    for (size_t i = 0; i < length; ++i)
        CHECK(mapped[i] == (unsigned char)(heap[i] ^ 0xa5));
    CHECK(mprotect(mapped, 4096, PROT_READ | PROT_WRITE) == 0);
    mapped[0] = 0x39;
    CHECK(mapped[0] == 0x39);
    CHECK(munmap(mapped, length) == 0);
    free(heap);
}

static void files_case(void)
{
    unsigned char expected[8209], actual[8209];
    char path[96];
    struct stat status;
    CHECK(snprintf(path, sizeof(path), "/tmp/native-core-%ld.dat", (long)getpid()) > 0);
    for (size_t i = 0; i < sizeof(expected); ++i) expected[i] = (unsigned char)(i * 29);
    int fd = open(path, O_CREAT | O_EXCL | O_RDWR, 0600);
    CHECK(fd >= 0);
    CHECK(write(fd, expected, sizeof(expected)) == (ssize_t)sizeof(expected));
    CHECK(fstat(fd, &status) == 0 && status.st_size == (off_t)sizeof(expected));
    CHECK(lseek(fd, 0, SEEK_SET) == 0);
    CHECK(read(fd, actual, sizeof(actual)) == (ssize_t)sizeof(actual));
    CHECK(memcmp(actual, expected, sizeof(actual)) == 0);
    CHECK(read(fd, actual, 1) == 0);
    expected[4096] ^= 0x71;
    CHECK(pwrite(fd, expected + 4096, 1, 4096) == 1);
    CHECK(pread(fd, actual, sizeof(actual), 0) == (ssize_t)sizeof(actual));
    CHECK(memcmp(actual, expected, sizeof(actual)) == 0);
    CHECK(fsync(fd) == 0);
    CHECK(close(fd) == 0);
    fd = open(path, O_RDONLY);
    CHECK(fd >= 0);
    CHECK(read(fd, actual, sizeof(actual)) == (ssize_t)sizeof(actual));
    CHECK(memcmp(actual, expected, sizeof(actual)) == 0);
    CHECK(close(fd) == 0 && unlink(path) == 0);
    errno = 0;
    CHECK(open(path, O_RDONLY) == -1 && errno == ENOENT);
}

static pthread_barrier_t start;
static pthread_mutex_t counter_lock = PTHREAD_MUTEX_INITIALIZER;
static unsigned counter;
static _Thread_local uintptr_t local_value;

static void barrier(void)
{
    int result = pthread_barrier_wait(&start);
    CHECK(result == 0 || result == PTHREAD_BARRIER_SERIAL_THREAD);
}

static void *count_thread(void *argument)
{
    CHECK(local_value == 0);
    local_value = (uintptr_t)argument;
    barrier();
    for (unsigned i = 0; i < 1000; ++i) {
        CHECK(pthread_mutex_lock(&counter_lock) == 0);
        ++counter;
        CHECK(pthread_mutex_unlock(&counter_lock) == 0);
    }
    CHECK(local_value == (uintptr_t)argument);
    return (void *)local_value;
}

static void threads_case(void)
{
    pthread_t workers[2];
    CHECK(pthread_barrier_init(&start, NULL, 3) == 0);
    for (uintptr_t i = 0; i < 2; ++i)
        CHECK(pthread_create(&workers[i], NULL, count_thread, (void *)(i + 1)) == 0);
    barrier();
    for (uintptr_t i = 0; i < 2; ++i) {
        void *result = NULL;
        CHECK(pthread_join(workers[i], &result) == 0 && result == (void *)(i + 1));
    }
    CHECK(counter == 2000 && local_value == 0);
    CHECK(pthread_barrier_destroy(&start) == 0);
    CHECK(pthread_mutex_destroy(&counter_lock) == 0);
}

static volatile sig_atomic_t received, used_alternate;
static uintptr_t alternate_begin, alternate_end;

static void handler(int number)
{
    unsigned char stack_byte;
    uintptr_t stack = (uintptr_t)&stack_byte;
    if (number == SIGUSR1) ++received;
    if (stack >= alternate_begin && stack < alternate_end) ++used_alternate;
}

static void signals_case(void)
{
    void *alternate = malloc(65536);
    CHECK(alternate != NULL);
    alternate_begin = (uintptr_t)alternate;
    alternate_end = alternate_begin + 65536;
    stack_t stack = {.ss_sp = alternate, .ss_size = 65536}, old_stack;
    struct sigaction action = {.sa_handler = handler, .sa_flags = SA_ONSTACK}, old_action;
    sigset_t blocked, old_mask, pending;
    CHECK(sigemptyset(&action.sa_mask) == 0);
    CHECK(sigaltstack(&stack, &old_stack) == 0);
    CHECK(sigaction(SIGUSR1, &action, &old_action) == 0);
    CHECK(sigemptyset(&blocked) == 0 && sigaddset(&blocked, SIGUSR1) == 0);
    CHECK(sigprocmask(SIG_BLOCK, &blocked, &old_mask) == 0);
    CHECK(raise(SIGUSR1) == 0 && received == 0);
    CHECK(sigpending(&pending) == 0 && sigismember(&pending, SIGUSR1) == 1);
    CHECK(sigprocmask(SIG_UNBLOCK, &blocked, NULL) == 0);
    CHECK(received == 1 && used_alternate == 1);
    CHECK(raise(SIGUSR1) == 0 && received == 2 && used_alternate == 2);
    CHECK(sigaction(SIGUSR1, &old_action, NULL) == 0);
    CHECK(sigprocmask(SIG_SETMASK, &old_mask, NULL) == 0);
    CHECK(sigaltstack(&old_stack, NULL) == 0);
    free(alternate);
}

int main(int argc, char **argv)
{
    CHECK(argc == 2);
    if (strcmp(argv[1], "memory") == 0) memory_case();
    else if (strcmp(argv[1], "files") == 0) files_case();
    else if (strcmp(argv[1], "threads") == 0) threads_case();
    else if (strcmp(argv[1], "signals") == 0) signals_case();
    else CHECK(0);
    CHECK(printf("NATIVE_CORE PASS %s\n", argv[1]) > 0);
    CHECK(fflush(stdout) == 0);
    return 37;
}
