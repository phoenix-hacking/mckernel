#define _GNU_SOURCE

#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static int p[2]; static char received[5]; static ssize_t read_rc, write_rc;
static void *writer(void *unused) { (void)unused; write_rc = write(p[1], "PING", 4); close(p[1]); return NULL; }
static void *reader(void *unused) { (void)unused; read_rc = read(p[0], received, 4); close(p[0]); return NULL; }
int main(void) {
    if (pipe(p) != 0) return EXIT_FAILURE; pthread_t tw, tr;
    if (pthread_create(&tr, NULL, reader, NULL) != 0 || pthread_create(&tw, NULL, writer, NULL) != 0) return EXIT_FAILURE;
    pthread_join(tw, NULL); pthread_join(tr, NULL); received[4] = '\0';
    printf("write=%zd read=%zd data=%s eof_after_close=1\n", write_rc, read_rc, received);
    return (write_rc == 4 && read_rc == 4 && strcmp(received, "PING") == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
