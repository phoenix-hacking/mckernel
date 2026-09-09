#define _GNU_SOURCE

#include <dirent.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

int main(void) {
    const char *dir = "/case/work/entries-026"; const char *names[] = {"alpha", "beta", "gamma"}; rmdir(dir); if (mkdir(dir, 0700) != 0) return EXIT_FAILURE;
    char path[128]; for (size_t i = 0; i < 3; ++i) { snprintf(path, sizeof(path), "%s/%s", dir, names[i]); int fd = creat(path, 0600); if (fd < 0) return EXIT_FAILURE; close(fd); }
    DIR *d = opendir(dir); if (!d) return EXIT_FAILURE; int seen[3] = {0, 0, 0}, extras = 0, duplicates = 0; struct dirent *e;
    while ((e = readdir(d)) != NULL) { if (strcmp(e->d_name, ".") == 0 || strcmp(e->d_name, "..") == 0) continue; int found = -1; for (int i = 0; i < 3; ++i) if (strcmp(e->d_name, names[i]) == 0) found = i; if (found < 0) ++extras; else if (seen[found]) ++duplicates; else seen[found] = 1; }
    closedir(d); int complete = seen[0] && seen[1] && seen[2]; printf("complete=%d extras=%d duplicates=%d\n", complete, extras, duplicates);
    for (size_t i = 0; i < 3; ++i) { snprintf(path, sizeof(path), "%s/%s", dir, names[i]); unlink(path); } rmdir(dir);
    return (complete && extras == 0 && duplicates == 0) ? EXIT_SUCCESS : EXIT_FAILURE;
}
