#include <stdio.h>

int main(int argc, char **argv) {
    printf("[startup.argv-empty]\n");
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
