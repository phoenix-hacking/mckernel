/* SPDX-License-Identifier: GPL-2.0-only */
/* Replay retained procfs bytes through the exact candidate parser/classifier.
 * The renamed controller CLI is compiled but never invoked. */
#define main stability_controller_uninvoked_main
#include "controller.c"
#undef main
#include "poll_cases.h"

int main(int argc, char **argv)
{
    if (argc != 2 || argv[1][0] != '/' || mkdir(argv[1], 0700) < 0) return 2;
    attempt_fd = open(argv[1], O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (attempt_fd < 0) return 2;
    unsigned failures = 0;
    for (unsigned i = 0; i < sizeof poll_cases / sizeof poll_cases[0]; ++i) {
        const struct poll_case *fixture = &poll_cases[i];
        struct sample sample = {.nr = -1, .error = fixture->error};
        size_t size = strlen(fixture->raw);
        if (size >= sizeof sample.raw) return 2;
        memcpy(sample.raw, fixture->raw, size + 1);
        sample.raw_length = (int)size;
        if (!sample.error) parse_syscall_sample(&sample);
        enum return_sample_kind observed = classify_return_sample(&sample);
        bool ok = observed == fixture->expected;
        char name[96], result[512];
        int length = snprintf(name, sizeof name, "%s.raw", fixture->name);
        if (length < 0 || (size_t)length >= sizeof name) return 2;
        int fd = new_file(name);
        if (fd < 0 || !put_all(fd, sample.raw, size) || fsync(fd) < 0 || close(fd) < 0) return 2;
        length = snprintf(name, sizeof name, "%s.json", fixture->name);
        if (length < 0 || (size_t)length >= sizeof name) return 2;
        length = snprintf(result, sizeof result,
            "{\"case\":\"%s\",\"status\":\"%s\",\"error\":%d,\"parsed\":%d,\"nr\":%ld,\"expected_kind\":%d,\"observed_kind\":%d,\"application_acceptance\":false,\"transport_acceptance\":false}\n",
            fixture->name, ok ? "PASS" : "FAIL", sample.error, sample.parsed, sample.nr,
            fixture->expected, observed);
        if (length < 0 || (size_t)length >= sizeof result) return 2;
        fd = new_file(name);
        if (fd < 0 || !put_all(fd, result, (size_t)length) || fsync(fd) < 0 || close(fd) < 0) return 2;
        printf("RETURN_POLL_CASE %s %s\n", fixture->name, ok ? "PASS" : "FAIL");
        if (!ok) { ++failures; break; }
    }
    if (fsync(attempt_fd) < 0 || close(attempt_fd) < 0 || fflush(stdout) < 0) return 2;
    return failures ? 1 : 0;
}
