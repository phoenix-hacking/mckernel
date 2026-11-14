/* SPDX-License-Identifier: GPL-2.0 */
/* Exact C launcher producer; the harness supplies its unchanged body. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "native-application-flat-c-reference.h"

static void emit(char **prefix, char **strings)
{
    char *pre = NULL, *flat = NULL;
    if (prefix && flatten_strings(NULL, prefix, &pre) <= 0) exit(1);
    int size = flatten_strings(pre, strings, &flat);
    if (size <= 0 || !flat) exit(2);
    printf("%d ", size);
    for (int i = 0; i < size; i++) printf("%02x", (unsigned char)flat[i]);
    putchar('\n');
    free(flat);
    free(pre);
}

int main(void)
{
    char *empty[] = {NULL};
    char *blank[] = {"", NULL};
    char *one[] = {"/bin/native-application-hello", NULL};
    char *multiple[] = {"one", "", "three", "\xc3\xa9", NULL};
    char *prefix[] = {"/bin/interpreter", "-e", NULL};
    emit(NULL, empty);
    emit(NULL, blank);
    emit(NULL, one);
    emit(NULL, multiple);
    emit(prefix, empty);
    emit(prefix, multiple);
    return 0;
}
