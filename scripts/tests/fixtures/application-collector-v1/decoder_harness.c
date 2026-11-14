/* SPDX-License-Identifier: GPL-2.0-only */
/* Source-only infrastructure fixture. Calls the real decoder; never execs. */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "request.h"
#include "literal_vector.h"
#include <errno.h>
#include <fcntl.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

/* Numeric offsets/values here come from the independent wire specification,
 * not from decoder-private helpers or C structure layout. */
enum operation {
    LITERAL, COPY_INPUT, COPY_OUTPUT, UNALIGNED, GUARD, GUARD_SHORT,
    NULL_INPUT, NULL_OUTPUT, SHORT, OVER_MAX, SET32, SET64, ZERO,
    TEXT, STRING_LENGTH, STRING_NUL, TRUNCATE_PREFIX, TRUNCATE_STRING,
    TRAILING, ROLE_TWO, STDIN_FILE, STDIN_EMPTY_FILE, ENV_EMPTY, ARGV_MAX,
    ENV_MAX, STRING_MAX, TOTAL_MAX, RAW_BYTES, ARTIFACT_MAX
};
struct test_case {
    const char *name, *expected;
    enum operation operation;
    unsigned a;
    uint64_t b;
    const char *text;
};
static const struct test_case cases[] = {
    {"literal-argv-empty", "OK", LITERAL, 0, 0, NULL},
    {"owned-copy-after-input-change", "OK", COPY_INPUT, 0, 0, NULL},
    {"output-struct-copy", "OK", COPY_OUTPUT, 0, 0, NULL},
    {"unaligned-wire", "OK", UNALIGNED, 0, 0, NULL},
    {"guard-page-exact-wire", "OK", GUARD, 0, 0, NULL},
    {"guard-page-truncated-string", "TRUNCATED", GUARD_SHORT, 0, 0, NULL},
    {"null-input", "ARGUMENT", NULL_INPUT, 0, 0, NULL},
    {"null-output", "ARGUMENT", NULL_OUTPUT, 0, 0, NULL},
    {"header-one-byte-short", "SIZE", SHORT, 0, 255, NULL},
    {"zero-length", "SIZE", SHORT, 0, 0, NULL},
    {"wire-one-byte-over", "SIZE", OVER_MAX, 0, 0, NULL},
    {"magic", "MAGIC", SET32, 0, 0, NULL},
    {"version-zero", "VERSION", SET32, 8, 0, NULL},
    {"version-future", "VERSION", SET32, 8, 2, NULL},
    {"header-length", "HEADER", SET32, 12, 255, NULL},
    {"declared-length-short", "LENGTH", SET32, 16, 399, NULL},
    {"declared-length-wrap", "LENGTH", SET32, 16, UINT32_MAX, NULL},
    {"flags", "RESERVED", SET32, 20, 1, NULL},
    {"reserved-first", "RESERVED", SET32, 216, 1, NULL},
    {"reserved-last", "RESERVED", SET32, 252, UINT32_C(0x01000000), NULL},
    {"unknown-role", "ROLE", SET32, 24, 3, NULL},
    {"unknown-profile", "PROFILE", SET32, 28, 2, NULL},
    {"uid", "PROFILE", SET32, 32, 1, NULL},
    {"gid", "PROFILE", SET32, 36, 1, NULL},
    {"group-count", "PROFILE", SET32, 40, 0, NULL},
    {"group-value", "PROFILE", SET32, 44, 1, NULL},
    {"umask", "PROFILE", SET32, 48, 22, NULL},
    {"argc-zero", "COUNTS", SET32, 52, 0, NULL},
    {"argc-over", "COUNTS", SET32, 52, 65, NULL},
    {"envc-over", "COUNTS", SET32, 56, 65, NULL},
    {"stdin-mode", "STREAM", SET32, 60, 2, NULL},
    {"stdout-inherit", "STREAM", SET32, 64, 0, NULL},
    {"stderr-merge", "STREAM", SET32, 68, 2, NULL},
    {"timeout-zero", "LIMIT", SET32, 72, 0, NULL},
    {"timeout-increased", "LIMIT", SET32, 72, 10001, NULL},
    {"cleanup-increased", "LIMIT", SET32, 76, 15001, NULL},
    {"stdout-limit-decreased", "LIMIT", SET32, 80, 65535, NULL},
    {"stderr-limit-increased", "LIMIT", SET32, 84, 65537, NULL},
    {"executable-empty", "IDENTITY", SET64, 88, 0, NULL},
    {"executable-size-over", "IDENTITY", SET64, 88, UINT64_C(99614720), NULL},
    {"executable-size-high-word", "IDENTITY", SET64, 88, UINT64_C(0x100000001), NULL},
    {"stdin-size-over", "IDENTITY", SET64, 96, UINT64_C(99614720), NULL},
    {"devnull-size", "IDENTITY", SET64, 96, 1, NULL},
    {"devnull-hash", "IDENTITY", SET32, 168, 1, NULL},
    {"missing-selected-hash", "IDENTITY", ZERO, 104, 32, NULL},
    {"missing-executable-hash", "IDENTITY", ZERO, 136, 32, NULL},
    {"missing-attempt-id", "IDENTITY", ZERO, 200, 16, NULL},
    {"file-missing-hash", "IDENTITY", SET32, 60, 1, NULL},
    {"prefix-truncated", "TRUNCATED", TRUNCATE_PREFIX, 0, 0, NULL},
    {"string-truncated", "TRUNCATED", TRUNCATE_STRING, 0, 0, NULL},
    {"string-length-over", "STRING", STRING_LENGTH, 0, 4096, NULL},
    {"string-length-wrap", "STRING", STRING_LENGTH, 0, UINT32_MAX, NULL},
    {"argv-embedded-nul", "STRING", STRING_NUL, 5, 0, NULL},
    {"case-empty", "CASE_ID", TEXT, 0, 0, ""},
    {"case-leading-dot", "CASE_ID", TEXT, 0, 0, ".case"},
    {"case-slash", "CASE_ID", TEXT, 0, 0, "startup/case"},
    {"exec-relative", "PATH", TEXT, 1, 0, "apps/app"},
    {"exec-root", "PATH", TEXT, 1, 0, "/"},
    {"exec-double-slash", "PATH", TEXT, 1, 0, "/apps//app"},
    {"cwd-dot", "PATH", TEXT, 2, 0, "/case/./work"},
    {"cwd-parent", "PATH", TEXT, 2, 0, "/case/../work"},
    {"cwd-trailing-slash", "PATH", TEXT, 2, 0, "/case/work/"},
    {"devnull-path-mismatch", "PATH", TEXT, 3, 0, "/case/input"},
    {"argv0-empty", "ARGV", TEXT, 4, 0, ""},
    {"env-no-equals", "ENV", TEXT, 8, 0, "PATH"},
    {"env-empty-name", "ENV", TEXT, 8, 0, "=value"},
    {"env-invalid-name", "ENV", TEXT, 8, 0, "P-ATH=value"},
    {"env-leading-digit", "ENV", TEXT, 8, 0, "1PATH=value"},
    {"env-duplicate-different-value", "DUPLICATE_ENV", TEXT, 9, 0, "PATH=elsewhere"},
    {"env-duplicate-same-value", "DUPLICATE_ENV", TEXT, 9, 0, "PATH=/apps:/bin:/usr/bin"},
    {"trailing-byte", "TRAILING", TRAILING, 0, 0, NULL},
    {"launcher-role-is-metadata", "OK", ROLE_TWO, 0, 0, NULL},
    {"regular-stdin", "OK", STDIN_FILE, 0, 0, NULL},
    {"empty-regular-stdin", "OK", STDIN_EMPTY_FILE, 0, 0, NULL},
    {"empty-complete-environment", "OK", ENV_EMPTY, 0, 0, NULL},
    {"maximum-argc", "OK", ARGV_MAX, 0, 0, NULL},
    {"maximum-envc", "OK", ENV_MAX, 0, 0, NULL},
    {"maximum-string", "OK", STRING_MAX, 0, 0, NULL},
    {"maximum-wire", "OK", TOTAL_MAX, 0, 0, NULL},
    {"literal-high-bytes", "OK", RAW_BYTES, 0, 0, NULL},
    {"maximum-executable-size", "OK", ARTIFACT_MAX, 0, 0, NULL},
    {"cwd-root", "OK", TEXT, 2, 0, "/"},
    {"env-value-equals", "OK", TEXT, 9, 0, "EMPTY=a=b"},
    {"env-prefix-distinct", "OK", TEXT, 9, 0, "PATH_SUFFIX=x"}
};

struct text { const unsigned char *bytes; size_t length; };
struct builder {
    struct text prefix[4], argv[64], env[64];
    unsigned argc, envc, role, stdin_mode;
    uint64_t executable_size, stdin_size;
};
static struct builder build;
static unsigned char wire[70000], long_text[4096];
_Alignas(8) static unsigned char unaligned[70001];
static char env_text[64][16];
static size_t wire_size, positions[132];
static struct { uint64_t before; struct acrq_request output; uint64_t after; } guarded;
static struct acrq_request copied;
static unsigned checks, failures;
static const char *active_name;

static void check(bool condition, const char *name)
{
    ++checks;
    if (!condition) {
        ++failures;
        fprintf(stderr, "ACRQ_ASSERTION_FAILURE case=%s assertion=%s errno=%d\n", active_name, name, errno);
    }
}

static struct text text(const char *s)
{
    return (struct text){.bytes = (const unsigned char *)s, .length = strlen(s)};
}

static void put32(unsigned char *p, uint32_t n)
{
    for (unsigned i = 0; i < 4; ++i) p[i] = (unsigned char)(n >> (i * 8));
}

static void put64(unsigned char *p, uint64_t n)
{
    for (unsigned i = 0; i < 8; ++i) p[i] = (unsigned char)(n >> (i * 8));
}

static void reset_builder(void)
{
    memset(&build, 0, sizeof build);
    build.prefix[0] = text("startup.argv-empty"); build.prefix[1] = text("/apps/app");
    build.prefix[2] = text("/case/work"); build.prefix[3] = text("/dev/null");
    build.argc = 4; build.envc = 3; build.role = 1; build.executable_size = 1234;
    build.argv[0] = text("app"); build.argv[1] = text("A");
    build.argv[2] = text(""); build.argv[3] = text("B");
    build.env[0] = text("PATH=/apps:/bin:/usr/bin"); build.env[1] = text("EMPTY=");
    build.env[2] = text("LITERAL=$HOME `x`;\n");
    memset(long_text, 'z', sizeof long_text);
}

static struct text *slot(unsigned n)
{
    if (n < 4) return &build.prefix[n];
    n -= 4;
    if (n < build.argc) return &build.argv[n];
    return &build.env[n - build.argc];
}

static void render(void)
{
    memset(wire, 0, sizeof wire);
    memcpy(wire, literal_request, 256);
    put32(wire + 24, build.role); put32(wire + 52, build.argc);
    put32(wire + 56, build.envc); put32(wire + 60, build.stdin_mode);
    put64(wire + 88, build.executable_size); put64(wire + 96, build.stdin_size);
    if (build.stdin_mode == 1) memset(wire + 168, 0x71, 32);
    wire_size = 256;
    for (unsigned i = 0; i < 4 + build.argc + build.envc; ++i) {
        const struct text *s = slot(i);
        positions[i] = wire_size;
        put32(wire + wire_size, (uint32_t)s->length); wire_size += 4;
        if (s->length != 0) memcpy(wire + wire_size, s->bytes, s->length);
        wire_size += s->length;
    }
    put32(wire + 16, (uint32_t)wire_size);
}

static void max_wire(void)
{
    build.argc = 17; build.envc = 0;
    for (unsigned i = 1; i < 16; ++i) build.argv[i] = (struct text){long_text, 4095};
    build.argv[16] = (struct text){long_text, 3722};
}

static void configure(const struct test_case *tc)
{
    reset_builder();
    switch (tc->operation) {
    case TEXT: *slot(tc->a) = text(tc->text); break;
    case ROLE_TWO: build.role = 2; break;
    case STDIN_FILE: case STDIN_EMPTY_FILE:
        build.stdin_mode = 1; build.stdin_size = tc->operation == STDIN_FILE ? 16 : 0;
        build.prefix[3] = text("/case/input"); break;
    case ENV_EMPTY: build.envc = 0; break;
    case ARGV_MAX:
        build.argc = 64;
        for (unsigned i = 4; i < 64; ++i) build.argv[i] = text("");
        break;
    case ENV_MAX:
        build.envc = 64;
        for (unsigned i = 0; i < 64; ++i) {
            int n = snprintf(env_text[i], sizeof env_text[i], "KEY_%02u=value", i);
            check(n > 0 && (size_t)n < sizeof env_text[i], "fixture-environment-name");
            build.env[i] = text(env_text[i]);
        }
        break;
    case STRING_MAX: build.argv[1] = (struct text){long_text, 4095}; break;
    case TOTAL_MAX: case OVER_MAX: max_wire(); break;
    case RAW_BYTES: {
        static const unsigned char raw[] = {0xff, 0x80, '\n', '$', '`', ';', '\\'};
        build.argv[1] = (struct text){raw, sizeof raw}; break;
    }
    case ARTIFACT_MAX: build.executable_size = UINT64_C(99614719); break;
    default: break;
    }
    render();
    switch (tc->operation) {
    case LITERAL:
        check(wire_size == 400 && sizeof literal_request == 400 &&
              memcmp(wire, literal_request, 400) == 0, "independent-literal-wire"); break;
    case SET32: put32(wire + tc->a, (uint32_t)tc->b); break;
    case SET64: put64(wire + tc->a, tc->b); break;
    case ZERO: memset(wire + tc->a, 0, (size_t)tc->b); break;
    case SHORT: wire_size = (size_t)tc->b; break;
    case STRING_LENGTH: put32(wire + positions[tc->a], (uint32_t)tc->b); break;
    case STRING_NUL: wire[positions[tc->a] + 4 + (size_t)tc->b] = 0; break;
    case TRUNCATE_PREFIX: wire_size = 258; put32(wire + 16, 258); break;
    case TRUNCATE_STRING: case GUARD_SHORT:
        --wire_size; put32(wire + 16, (uint32_t)wire_size); break;
    case TRAILING: wire[wire_size++] = 0xa5; put32(wire + 16, (uint32_t)wire_size); break;
    case TOTAL_MAX: check(wire_size == 65536, "fixture-exact-wire-bound"); break;
    case OVER_MAX:
        check(wire_size == 65536, "fixture-over-bound-origin");
        wire[wire_size++] = 0xa5; put32(wire + 16, (uint32_t)wire_size); break;
    default: break;
    }
}

static bool write_all(int fd, const void *raw, size_t size)
{
    const unsigned char *p = raw;
    while (size != 0) {
        ssize_t n = write(fd, p, size);
        if (n > 0) { p += n; size -= (size_t)n; }
        else if (n < 0 && errno == EINTR) continue;
        else return false;
    }
    return true;
}

static bool save(int dirfd, const char *name, const void *raw, size_t size)
{
    int fd = openat(dirfd, name, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (fd < 0) return false;
    bool ok = write_all(fd, raw, size);
    if (fsync(fd) != 0) ok = false;
    if (close(fd) != 0) ok = false;
    return ok;
}

static bool all_zero(const void *raw, size_t size)
{
    const unsigned char *p = raw;
    for (size_t i = 0; i < size; ++i) if (p[i] != 0) return false;
    return true;
}

static void check_slice(const struct acrq_request *out, struct acrq_slice slice,
                        const struct text *expected)
{
    bool bound = slice.offset < out->storage_used &&
        slice.length < out->storage_used - slice.offset && out->storage_used <= 65536;
    check(bound, "owned-slice-bounds");
    if (!bound) return;
    check(slice.length == expected->length, "literal-string-length");
    if (slice.length == expected->length)
        check(memcmp(out->storage + slice.offset, expected->bytes, slice.length) == 0, "literal-string-bytes");
    check(out->storage[slice.offset + slice.length] == 0, "owned-terminator");
}

static void check_values(const struct acrq_request *out)
{
    check(out->schema_version == 1 && out->profile == 1 && out->role == build.role, "declared-role-profile");
    check(out->uid == 0 && out->gid == 0 && out->group_count == 1 && out->group == 0 && out->umask_value == 18, "desired-identity");
    check(out->argc == build.argc && out->envc == build.envc, "list-counts");
    check(out->stdin_mode == build.stdin_mode && out->stdout_mode == 1 && out->stderr_mode == 1, "stream-modes");
    check(out->timeout_ms == 10000 && out->cleanup_timeout_ms == 15000 &&
          out->stdout_limit == 65536 && out->stderr_limit == 65536, "fixed-limits");
    check(out->executable_size == build.executable_size && out->stdin_size == build.stdin_size, "declared-file-sizes");
    for (unsigned i = 0; i < 32; ++i) {
        check(out->selected_inputs_sha256[i] == i + 1, "declared-input-hash");
        check(out->executable_sha256[i] == i + 33, "declared-executable-hash");
        check(out->stdin_sha256[i] == (build.stdin_mode ? 0x71 : 0), "declared-stdin-hash");
    }
    for (unsigned i = 0; i < 16; ++i) check(out->attempt_id[i] == i + 160, "declared-attempt-id");
    check(out->execution_enabled == 0, "execution-remains-disabled");
    check_slice(out, out->case_id, &build.prefix[0]);
    check_slice(out, out->executable_path, &build.prefix[1]);
    check_slice(out, out->cwd, &build.prefix[2]);
    check_slice(out, out->stdin_path, &build.prefix[3]);
    for (unsigned i = 0; i < build.argc; ++i) check_slice(out, out->argv[i], &build.argv[i]);
    for (unsigned i = 0; i < build.envc; ++i) check_slice(out, out->env[i], &build.env[i]);
}

static bool run_case(int rootfd, const struct test_case *tc)
{
    active_name = tc->name; checks = 0; failures = 0;
    if (mkdirat(rootfd, tc->name, 0700) != 0) return false;
    int dirfd = openat(rootfd, tc->name, O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (dirfd < 0) return false;
    configure(tc);
    check(save(dirfd, "request.bin", wire, wire_size), "retain-original-request");
    const void *input = wire;
    void *mapping = MAP_FAILED;
    size_t mapping_size = 0;
    if (tc->operation == NULL_INPUT) input = NULL;
    if (tc->operation == UNALIGNED) { memcpy(unaligned + 1, wire, wire_size); input = unaligned + 1; }
    if (tc->operation == GUARD || tc->operation == GUARD_SHORT) {
        long page = sysconf(_SC_PAGESIZE);
        check(page > 0 && (uint64_t)page <= 65536, "host-page-size");
        if (page > 0 && (uint64_t)page <= 65536) {
            size_t middle = ((wire_size + (size_t)page - 1) / (size_t)page) * (size_t)page;
            mapping_size = middle + 2 * (size_t)page;
            mapping = mmap(NULL, mapping_size, PROT_NONE, MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
            check(mapping != MAP_FAILED, "guard-mmap");
            if (mapping != MAP_FAILED) {
                unsigned char *start = (unsigned char *)mapping + (size_t)page;
                bool writable = mprotect(start, middle, PROT_READ | PROT_WRITE) == 0;
                check(writable, "guard-mprotect");
                if (writable) { input = start + middle - wire_size; memcpy((void *)input, wire, wire_size); }
            }
        }
    }
    guarded.before = UINT64_C(0x1020304050607080); guarded.after = UINT64_C(0xfedcba9876543210);
    memset(&guarded.output, 0xa5, sizeof guarded.output);
    struct acrq_request *out = tc->operation == NULL_OUTPUT ? NULL : &guarded.output;
    enum acrq_error error = acrq_decode(input, wire_size, out);
    const char *actual = acrq_error_name(error);
    check(strcmp(actual, tc->expected) == 0, "independent-error-category");
    check(guarded.before == UINT64_C(0x1020304050607080) &&
          guarded.after == UINT64_C(0xfedcba9876543210), "output-canaries");
    bool cleared = out != NULL && all_zero(out, sizeof *out);
    if (error != ACRQ_OK && out != NULL) check(cleared, "failure-clears-all-output");
    if (error == ACRQ_OK && out != NULL) {
        if (tc->operation == COPY_INPUT) memset(wire, 0x55, wire_size);
        if (tc->operation == COPY_OUTPUT) { memcpy(&copied, out, sizeof copied); memset(out, 0, sizeof *out); out = &copied; }
        check_values(out);
    }
    if (mapping != MAP_FAILED) check(munmap(mapping, mapping_size) == 0, "guard-munmap");
    char report[1536];
    int n = snprintf(report, sizeof report,
        "{\n  \"schema_version\": 1,\n  \"kind\": \"application-request-decoder-fixture\",\n"
        "  \"case\": \"%s\",\n  \"status\": \"%s\",\n  \"expected_error\": \"%s\",\n"
        "  \"actual_error\": \"%s\",\n  \"wire_size\": %zu,\n  \"checks\": %u,\n  \"failures\": %u,\n"
        "  \"null_input\": %s,\n  \"null_output\": %s,\n  \"output_cleared\": %s,\n"
        "  \"application_execution\": \"NOT_RUN\",\n  \"application_acceptance\": false\n}\n",
        tc->name, failures ? "FAIL" : "PASS", tc->expected, actual, wire_size, checks, failures,
        tc->operation == NULL_INPUT ? "true" : "false", out == NULL ? "true" : "false", cleared ? "true" : "false");
    check(n > 0 && (size_t)n < sizeof report, "report-size");
    if (n > 0 && (size_t)n < sizeof report) check(save(dirfd, "result.json", report, (size_t)n), "retain-result");
    check(fsync(dirfd) == 0, "case-directory-fsync");
    check(close(dirfd) == 0, "case-directory-close");
    printf("ACRQ_DECODER_CASE %s %s\n", tc->name, failures ? "FAIL" : "PASS");
    fflush(stdout);
    return failures == 0;
}

int main(int argc, char **argv)
{
    if (argc != 3 || argv[2][0] != '/') {
        fprintf(stderr, "usage: decoder-harness CASE|--all /absolute/fresh-attempt\n"); return 2;
    }
    bool all = strcmp(argv[1], "--all") == 0;
    size_t selected = 0;
    for (size_t i = 0; i < sizeof cases / sizeof cases[0]; ++i)
        if (all || strcmp(argv[1], cases[i].name) == 0) ++selected;
    if (selected == 0 || mkdir(argv[2], 0700) != 0) { perror("decoder-harness fresh attempt"); return 2; }
    int rootfd = open(argv[2], O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (rootfd < 0) { perror("decoder-harness attempt open"); return 2; }
    bool ok = true;
    for (size_t i = 0; i < sizeof cases / sizeof cases[0]; ++i) {
        if (!all && strcmp(argv[1], cases[i].name) != 0) continue;
        if (!run_case(rootfd, &cases[i])) { ok = false; break; }
    }
    if (fsync(rootfd) != 0) ok = false;
    if (close(rootfd) != 0) ok = false;
    if (ok) printf("ACRQ_DECODER_SUITE %zu PASS\n", selected);
    return ok ? 0 : 1;
}
