#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int relocated_value = 42;
int main(int argc, char **argv) {
    const char *lang = getenv("LANG");
    int valid = argc == 1 && argv != NULL && argv[0] != NULL && lang != NULL && strcmp(lang, "C") == 0 && relocated_value == 42;
    printf("argc=%d argv0_present=%d lang=%s data=%d valid=%d\n", argc, argv[0] != NULL, lang ? lang : "", relocated_value, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
