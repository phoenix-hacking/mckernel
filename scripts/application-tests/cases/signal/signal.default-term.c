#define _GNU_SOURCE

#include <stdio.h>
#include <unistd.h>

int main(void) {
    fputs("ready\n", stdout); fflush(stdout);
    for (;;) pause();
}
