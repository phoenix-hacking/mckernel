#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    static const char *const expected[] = {"app", "A", "", "B"};
    if (argc != 4 || argv[argc] != NULL) {
        fputs("unexpected argc or argv terminator\n", stderr);
        return 41;
    }
    for (int i = 0; i < argc; ++i) {
        if (argv[i] == NULL || strcmp(argv[i], expected[i]) != 0) {
            fputs("unexpected argument bytes\n", stderr);
            return 42;
        }
    }
    if (printf("{\"case\":\"startup.argv-empty\",\"argc\":%d,"
               "\"argv\":[\"%s\",\"%s\",\"%s\",\"%s\"],"
               "\"terminator_is_null\":true}\n",
               argc, argv[0], argv[1], argv[2], argv[3]) < 0 ||
        fflush(stdout) != 0) {
        return 43;
    }
    return 0;
}
