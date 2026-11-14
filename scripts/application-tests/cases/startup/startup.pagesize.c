#define _GNU_SOURCE

#include <asm/auxvec.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/auxv.h>
#include <unistd.h>

int main(void) {
    long first = sysconf(_SC_PAGESIZE);
    long second = sysconf(_SC_PAGESIZE);
    unsigned long aux = getauxval(AT_PAGESZ);

    if (first < 0 || second < 0 || aux == 0) {
        return EXIT_FAILURE;
    }
    printf("sysconf_first=%ld\n", first);
    printf("sysconf_second=%ld\n", second);
    printf("auxv_pagesz=%lu\n", aux);
    return EXIT_SUCCESS;
}
