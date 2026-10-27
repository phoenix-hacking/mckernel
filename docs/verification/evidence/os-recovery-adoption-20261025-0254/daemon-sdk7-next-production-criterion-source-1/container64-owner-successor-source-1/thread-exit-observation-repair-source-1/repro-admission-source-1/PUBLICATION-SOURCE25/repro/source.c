/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE ONLY: execute only under an actual bounded owner/admission. No daemon,
 * mock endpoints, sleeps, cleanup, detached threads or altered thread oracle.
 * The existing fixture Owner.run(..., timeout=8) must bound this process.
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <errno.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/syscall.h>
#include <unistd.h>

static pthread_barrier_t ready;
struct worker { pid_t tid; char stat[4096]; };
static int task_stat(pid_t tid, char *buf, size_t capacity) {
    char path[80];
    snprintf(path, sizeof(path), "/proc/self/task/%d/stat", tid);
    FILE *file = fopen(path, "r");
    if (!file) return errno == ENOENT ? 0 : -1;
    if (!fgets(buf, capacity, file)) { fclose(file); return -1; }
    if (fclose(file)) return -1;
    buf[strcspn(buf, "\n")] = 0;
    return 1;
}
static void *finish(void *arg) {
    struct worker *worker = arg;
    worker->tid = syscall(SYS_gettid);
    if (task_stat(worker->tid, worker->stat, sizeof(worker->stat)) != 1) abort();
    int result = pthread_barrier_wait(&ready);
    if (result && result != PTHREAD_BARRIER_SERIAL_THREAD) abort();
    return NULL;
}
static void quoted(const char *value) {
    putchar('"');
    for (const unsigned char *p = (const unsigned char *)value; *p; ++p) {
        if (*p == '"' || *p == '\\') putchar('\\');
        if (*p < 32) printf("\\u%04x", *p); else putchar(*p);
    }
    putchar('"');
}
/* Preserve every enumerated row; never subtract a joined task from the count. */
static int snapshot(struct worker workers[2], int iteration, int record) {
    struct row { pid_t tid; int known, read; char stat[4096]; } rows[64];
    DIR *tasks = opendir("/proc/self/task");
    if (!tasks) return -1;
    int count = 0, unknown = 0;
    struct dirent *entry;
    errno = 0;
    while ((entry = readdir(tasks))) {
        if (entry->d_name[0] == '.') continue;
        if (count == 64) { closedir(tasks); return -1; }
        char *end;
        long number = strtol(entry->d_name, &end, 10);
        if (*end || number <= 0) { closedir(tasks); return -1; }
        struct row *row = &rows[count++];
        row->tid = number;
        row->known = row->tid == getpid() || row->tid == workers[0].tid || row->tid == workers[1].tid;
        unknown |= !row->known;
        row->stat[0] = 0;
        row->read = task_stat(row->tid, row->stat, sizeof(row->stat));
        if (row->read < 0) { closedir(tasks); return -1; }
        errno = 0;
    }
    if (errno) { closedir(tasks); return -1; }
    if (closedir(tasks)) return -1;
    if (record || count > 1 || unknown) {
        printf("{\"iteration\":%d,\"rows\":[", iteration);
        for (int i = 0; i < count; ++i) {
            struct row *row = &rows[i];
            if (i) putchar(',');
            printf("{\"tid\":%d,\"known_joined_or_main\":%s,\"stat_read\":%d,\"raw_stat\":", row->tid, row->known ? "true" : "false", row->read);
            quoted(row->stat); putchar('}');
        }
        printf("],\"literal_threads\":%d,\"unknown\":%s}\n", count, unknown ? "true" : "false");
    }
    return unknown ? -1 : count;
}

int main(void) {
    setbuf(stdout, NULL);
    /* Fixed minimized observation budget; no automatic daemon/case replay. */
    for (int iteration = 0; iteration < 256; ++iteration) {
        struct worker workers[2] = {0};
        pthread_t threads[2];
        if (pthread_barrier_init(&ready, NULL, 3)) return 3;
        for (int i = 0; i < 2; ++i)
            if (pthread_create(&threads[i], NULL, finish, &workers[i])) abort();
        int barrier = pthread_barrier_wait(&ready);
        if (barrier && barrier != PTHREAD_BARRIER_SERIAL_THREAD) abort();
        for (int i = 0; i < 2; ++i) if (pthread_join(threads[i], NULL)) abort();
        int count = snapshot(workers, iteration, 0);
        if (count < 1) return 3;
        if (count > 1) {
            printf("{\"status\":\"OBSERVED_JOINED_TASK_ENUMERATION\",\"iteration\":%d,\"immediate_literal_threads\":%d,\"real_pthread_join_returned_zero\":true,\"workers\":[", iteration, count);
            for (int i = 0; i < 2; ++i) {
                if (i) putchar(',');
                printf("{\"tid\":%d,\"initial_raw_stat\":", workers[i].tid);
                quoted(workers[i].stat); putchar('}');
            }
            puts("]}");
            if (snapshot(workers, iteration, 1) < 1) return 3;
            /* Only these positively joined TIDs may finish disappearing.
             * The unchanged external 8-second fixture owner is the deadline. */
            for (;;) {
                int absent = 0;
                for (int i = 0; i < 2; ++i) {
                    char path[80]; struct stat info;
                    snprintf(path, sizeof(path), "/proc/self/task/%d", workers[i].tid);
                    if (!stat(path, &info)) continue;
                    if (errno != ENOENT) return 3;
                    absent++;
                }
                if (absent == 2) break;
                sched_yield();
            }
            int final_count = snapshot(workers, iteration, 1);
            printf("{\"status\":\"FINAL_LITERAL_THREAD_CHECK\",\"threads\":%d}\n", final_count);
            return final_count == 1 ? 0 : 3;
        }
        if (pthread_barrier_destroy(&ready)) return 3;
    }
    puts("{\"status\":\"NOT_REPRODUCED\",\"iterations\":256,\"historical_extra_task_identity\":null}");
    return 2;
}
