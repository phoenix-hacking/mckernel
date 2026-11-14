#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static const char marker[] = "STATIC";
int main(int argc, char **argv) {
    const char *lang = getenv("LANG");
    int valid = argc == 1 && argv != NULL && argv[0] != NULL && lang != NULL && strcmp(lang, "C") == 0 && marker[0] == 'S';
    printf("argc=%d argv0_present=%d lang=%s marker=%s valid=%d\n", argc, argv[0] != NULL, lang ? lang : "", marker, valid);
    return valid ? EXIT_SUCCESS : EXIT_FAILURE;
}
