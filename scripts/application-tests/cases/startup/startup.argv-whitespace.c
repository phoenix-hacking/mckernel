#define _GNU_SOURCE

#include <stdio.h>
#include <string.h>

int main(int argc, char **argv) {
    printf("argc=%d\n", argc);
    for (int i = 0; i <= argc; i++) {
        if (argv[i] == NULL) {
            printf("argv[%d]=NULL\n", i);
        } else {
            printf("argv[%d]=%s\n", i, argv[i]);
        }
    }

    return 0;
}
