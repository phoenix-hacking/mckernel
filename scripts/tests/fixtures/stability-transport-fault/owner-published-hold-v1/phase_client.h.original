/* SPDX-License-Identifier: GPL-2.0-only */
/* Private verification ABI, bound to stability_phase.rs version 1, SHA-256
 * 5ce35193f9d88d7b990b92cc90287437ffe9c2e6b3f409ddfa2190b1ebfb9e54.
 * Source prepared only. Neither a successful ioctl nor this client accepts a guest. */
#ifndef STABILITY_OWNER_PHASE_CLIENT_V1_H
#define STABILITY_OWNER_PHASE_CLIENT_V1_H
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <limits.h>
#include <poll.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define OP_COMMAND UINT32_C(0xc100f501)
#define OP_BYTES 256u
#define OP_SELECT 1u
#define OP_TERMINAL 2u
#define OP_QUIET 3u
#define OP_RECOVERY 4u
#define OP_AFTER_HELLO 5u
#define OP_QUERY 6u
#define OP_MAX_ATTEMPTS 48u /* Four artifacts each; total tree remains <256 entries. */
enum op_result { OP_FAILED = -1, OP_OK = 0, OP_RETRY = 1 };
struct op_identity {
    uint32_t os;
    int32_t pid;
    uint64_t generation, nonce_low, nonce_high, sequence;
    unsigned attempt;
    bool selected;
    unsigned char key[80]; /* exact immutable output offsets 80..159 */
};
struct op_observation {
    unsigned char reply[OP_BYTES];
    int open_result, open_errno, ioctl_result, ioctl_errno, raw_wait;
    bool ioctl_called, response_received, reaped, timed_out, consumed;
    uint64_t begin_ns, end_ns;
};

static inline uint64_t op_now(void)
{
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t) < 0) return 0;
    return (uint64_t)t.tv_sec * UINT64_C(1000000000) + (uint64_t)t.tv_nsec;
}
static inline uint32_t op_u32(const unsigned char *b, unsigned offset)
{
    return (uint32_t)b[offset] | (uint32_t)b[offset + 1] << 8 |
           (uint32_t)b[offset + 2] << 16 | (uint32_t)b[offset + 3] << 24;
}
static inline uint64_t op_u64(const unsigned char *b, unsigned offset)
{
    return (uint64_t)op_u32(b, offset) | (uint64_t)op_u32(b, offset + 4) << 32;
}
static inline void op_put32(unsigned char *b, unsigned offset, uint32_t value)
{
    for (unsigned i = 0; i < 4; ++i) b[offset + i] = (unsigned char)(value >> (i * 8));
}
static inline void op_put64(unsigned char *b, unsigned offset, uint64_t value)
{
    for (unsigned i = 0; i < 8; ++i) b[offset + i] = (unsigned char)(value >> (i * 8));
}
static inline bool op_zero(const unsigned char *b, unsigned begin, unsigned end)
{
    for (unsigned i = begin; i < end; ++i) if (b[i]) return false;
    return true;
}
static inline bool op_write_all(int fd, const void *data, size_t length)
{
    const unsigned char *bytes = data;
    while (length) {
        ssize_t n = write(fd, bytes, length);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return false;
        bytes += n; length -= (size_t)n;
    }
    return true;
}
static inline bool op_artifact(int directory, const char *name, const void *data, size_t length)
{
    int fd = openat(directory, name, O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (fd < 0) return false;
    bool ok = op_write_all(fd, data, length);
    if (close(fd) < 0) ok = false;
    return ok;
}
static inline bool op_decimal(const char *text, uint64_t maximum, uint64_t *value)
{
    if (!text[0] || (text[0] == '0' && text[1])) return false;
    uint64_t parsed = 0;
    for (const char *p = text; *p; ++p) {
        if (*p < '0' || *p > '9' || (unsigned)(*p - '0') > maximum ||
            parsed > (maximum - (unsigned)(*p - '0')) / 10) return false;
        parsed = parsed * 10 + (unsigned)(*p - '0');
    }
    *value = parsed;
    return true;
}
static inline bool op_initialize(struct op_identity *id, const char *os, const char *generation,
                                 const char *nonce, int32_t pid)
{
    memset(id, 0, sizeof *id);
    uint64_t slot, gen;
    if (!op_decimal(os, 63, &slot) || !op_decimal(generation, UINT64_MAX, &gen) || !gen || pid < 0 || strlen(nonce) != 32) return false;
    uint64_t words[2] = {0, 0};
    for (unsigned i = 0; i < 32; ++i) {
        unsigned digit;
        if (nonce[i] >= '0' && nonce[i] <= '9') digit = (unsigned)(nonce[i] - '0');
        else if (nonce[i] >= 'a' && nonce[i] <= 'f') digit = (unsigned)(nonce[i] - 'a') + 10;
        else return false;
        words[i / 16] = words[i / 16] * 16 + digit;
    }
    if (!(words[0] | words[1])) return false;
    id->os = (uint32_t)slot; id->generation = gen; id->pid = pid;
    id->nonce_low = words[0]; id->nonce_high = words[1];
    return true;
}

static inline bool op_key_valid(const struct op_identity *id, const unsigned char *reply)
{
    uint64_t physical = op_u64(reply, 120), end = op_u64(reply, 128);
    return op_u64(reply, 80) && op_u64(reply, 88) && op_u64(reply, 96) && op_u64(reply, 104) &&
        physical && end > physical && end - physical == 40 &&
        op_u32(reply, 136) > 0 && op_u32(reply, 136) <= INT32_MAX &&
        op_u32(reply, 136) == (uint32_t)id->pid && op_u32(reply, 140) <= INT32_MAX &&
        op_u32(reply, 144) > 0 && op_u32(reply, 144) <= INT32_MAX &&
        op_u32(reply, 148) == id->os && op_u64(reply, 152) == id->generation;
}

/* All dispatched requests, including EAGAIN, consume their sequence. Only an
 * explicit untouched output region with ioctl EAGAIN is a safe nonconsumed
 * busy-Permit retry. Copyout errors and inconsistent replies are always fatal. */
static inline enum op_result op_validate(struct op_identity *id, uint32_t phase,
                                         const unsigned char *request, struct op_observation *out)
{
    if (!out->response_received || !out->reaped || out->timed_out ||
        !WIFEXITED(out->raw_wait) || WEXITSTATUS(out->raw_wait) != 0 || !out->ioctl_called ||
        memcmp(out->reply, request, 64) || !op_zero(out->reply, 208, OP_BYTES)) return OP_FAILED;
    uint64_t sequence = op_u64(request, 24);
    if (op_zero(out->reply, 64, OP_BYTES))
        return out->ioctl_result == -1 && out->ioctl_errno == EAGAIN ? OP_RETRY : OP_FAILED;
    if (op_u64(out->reply, 200) != sequence) return OP_FAILED;
    out->consumed = true;
    id->sequence = sequence;
    uint64_t phase_error = op_u64(out->reply, 72), verification_error = op_u64(out->reply, 184);
    if (!op_key_valid(id, out->reply) || (id->selected && memcmp(id->key, out->reply + 80, sizeof id->key)) ||
        verification_error || op_u64(out->reply, 160) > 3) return OP_FAILED;
    if (out->ioctl_result == -1) {
        if (out->ioctl_errno != EAGAIN || phase_error != (uint64_t)(int64_t)-EAGAIN || op_u64(out->reply, 64) != 0) return OP_FAILED;
        return phase == OP_SELECT ? OP_FAILED : OP_RETRY;
    }
    if (out->ioctl_result != 0 || out->ioctl_errno != 0 || phase_error) return OP_FAILED;
    uint64_t snapshot = op_u64(out->reply, 64), stage = op_u64(out->reply, 160);
    if (phase == OP_SELECT) {
        if (id->selected || sequence != 1 || snapshot != 1 || stage != 1 ||
            op_u64(out->reply, 168) || op_u64(out->reply, 176) || op_u64(out->reply, 192)) return OP_FAILED;
        memcpy(id->key, out->reply + 80, sizeof id->key);
        id->selected = true;
    } else {
        if (!id->selected || stage != 3 || op_u64(out->reply, 168) != 2) return OP_FAILED;
        if (phase == OP_TERMINAL || phase == OP_RECOVERY) { if (snapshot != 3) return OP_FAILED; }
        else if (phase == OP_QUIET || phase == OP_AFTER_HELLO) { if (snapshot != 4) return OP_FAILED; }
        else return OP_FAILED;
        if ((phase == OP_TERMINAL || phase == OP_QUIET) != (op_u64(out->reply, 176) != 0)) return OP_FAILED;
    }
    return OP_OK;
}

static inline enum op_result op_call(struct op_identity *id, uint32_t phase, int directory,
                                     void (*progress)(unsigned), struct op_observation *out)
{
    memset(out, 0, sizeof *out); out->raw_wait = -1; out->open_result = -1;
    if (id->sequence == UINT64_MAX || id->attempt >= OP_MAX_ATTEMPTS || phase < OP_SELECT || phase > OP_AFTER_HELLO) return OP_FAILED;
    unsigned char request[OP_BYTES] = {0};
    op_put32(request, 0, 1); op_put32(request, 4, phase); op_put32(request, 8, id->os);
    op_put32(request, 12, (uint32_t)id->pid); op_put64(request, 16, id->generation);
    op_put64(request, 24, id->sequence + 1); op_put64(request, 32, id->nonce_low); op_put64(request, 40, id->nonce_high);
    if (id->selected) { op_put64(request, 48, op_u64(id->key, 16)); op_put64(request, 56, op_u64(id->key, 24)); }
    char name[80];
    unsigned attempt = ++id->attempt;
    snprintf(name, sizeof name, "owner-phase-%03u-request.bin", attempt);
    if (!op_artifact(directory, name, request, sizeof request)) return OP_FAILED;
    int channel[2];
    if (pipe2(channel, O_CLOEXEC | O_NONBLOCK) < 0) return OP_FAILED;
    out->begin_ns = op_now();
    if (!out->begin_ns) { close(channel[0]); close(channel[1]); return OP_FAILED; }
    pid_t child = fork();
    if (child < 0) { close(channel[0]); close(channel[1]); return OP_FAILED; }
    if (!child) {
        close(channel[0]);
        struct op_observation message;
        memset(&message, 0, sizeof message);
        memcpy(message.reply, request, sizeof request);
        message.open_result = open("/dev/mcd0", O_RDWR | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
        message.open_errno = message.open_result < 0 ? errno : 0;
        if (message.open_result >= 0) {
            message.ioctl_called = true;
            errno = 0;
            message.ioctl_result = ioctl(message.open_result, OP_COMMAND, message.reply);
            message.ioctl_errno = message.ioctl_result < 0 ? errno : 0;
            close(message.open_result);
        }
        _exit(op_write_all(channel[1], &message, sizeof message) ? 0 : 127);
    }
    close(channel[1]);
    struct op_observation message;
    memset(&message, 0, sizeof message);
    size_t received = 0;
    uint64_t deadline = out->begin_ns + UINT64_C(5000000000);
    uint64_t current;
    while ((current = op_now()) && current < deadline) {
        if (received < sizeof message) {
            ssize_t n = read(channel[0], (unsigned char *)&message + received, sizeof message - received);
            if (n > 0) received += (size_t)n;
            else if (n < 0 && errno != EAGAIN && errno != EINTR) break;
        }
        if (!out->reaped) {
            pid_t result = waitpid(child, &out->raw_wait, WNOHANG);
            if (result == child) out->reaped = true;
            else if (result < 0 && errno != EINTR) break;
        }
        if (out->reaped && received == sizeof message) break;
        if (progress) progress(5);
        else { struct pollfd p = {.fd = channel[0], .events = POLLIN}; (void)poll(&p, 1, 5); }
    }
    out->end_ns = op_now();
    out->timed_out = !out->end_ns || out->end_ns >= deadline;
    if (!out->reaped) {
        /* The direct child remains unreaped; no numeric PID can be reused. */
        (void)kill(child, SIGKILL);
        uint64_t cleanup_begin = op_now(), cleanup_deadline = cleanup_begin + UINT64_C(15000000000);
        while (cleanup_begin && (current = op_now()) && current < cleanup_deadline) {
            if (waitpid(child, &out->raw_wait, WNOHANG) == child) { out->reaped = true; break; }
            if (progress) progress(5);
            else (void)poll(NULL, 0, 5);
        }
    }
    close(channel[0]);
    if (received == sizeof message) {
        out->response_received = true;
        memcpy(out->reply, message.reply, OP_BYTES);
        out->open_result = message.open_result; out->open_errno = message.open_errno;
        out->ioctl_called = message.ioctl_called;
        out->ioctl_result = message.ioctl_result; out->ioctl_errno = message.ioctl_errno;
    }
    enum op_result result = op_validate(id, phase, request, out);
    snprintf(name, sizeof name, "owner-phase-%03u-probe.bin", attempt);
    bool probe_retained = op_artifact(directory, name, &message, received);
    snprintf(name, sizeof name, "owner-phase-%03u-response.bin", attempt);
    bool retained = op_artifact(directory, name, out->reply, out->response_received ? OP_BYTES : 0);
    char report[2048];
    int n = snprintf(report, sizeof report,
        "{\"schema_version\":1,\"application_acceptance\":false,\"transport_acceptance\":false,\"phase\":%u,\"attempt\":%u,\"request_sequence\":%" PRIu64 ","
        "\"probe_pid\":%d,\"probe_reaped\":%s,\"probe_raw_wait\":%d,\"begin_ns\":%" PRIu64 ",\"observed_ns\":%" PRIu64 ",\"timed_out\":%s,"
        "\"probe_bytes_received\":%zu,\"response_received\":%s,\"open_result\":%d,\"open_errno\":%d,\"ioctl_called\":%s,\"ioctl_result\":%d,\"ioctl_errno\":%d,\"request_consumed\":%s,\"client_result\":%d}\n",
        phase, attempt, op_u64(request, 24), child, out->reaped ? "true" : "false", out->raw_wait, out->begin_ns, out->end_ns,
        out->timed_out ? "true" : "false", received, out->response_received ? "true" : "false", out->open_result, out->open_errno,
        out->ioctl_called ? "true" : "false", out->ioctl_result, out->ioctl_errno, out->consumed ? "true" : "false", result);
    snprintf(name, sizeof name, "owner-phase-%03u-result.json", attempt);
    if (n <= 0 || (size_t)n >= sizeof report || !op_artifact(directory, name, report, (size_t)n) || !retained || !probe_retained) return OP_FAILED;
    return result;
}

static inline bool op_load_recovery(struct op_identity *id, const char *path, int directory)
{
    unsigned char reply[OP_BYTES];
    int fd = open(path, O_RDONLY | O_NONBLOCK | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0) return false;
    struct stat st, after;
    bool ok = fstat(fd, &st) == 0 && S_ISREG(st.st_mode) && st.st_size == OP_BYTES;
    size_t used = 0;
    while (ok && used < sizeof reply) {
        ssize_t n = read(fd, reply + used, sizeof reply - used);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) { ok = false; break; }
        used += (size_t)n;
    }
    if (ok && (fstat(fd, &after) < 0 || st.st_dev != after.st_dev || st.st_ino != after.st_ino ||
        st.st_size != after.st_size || st.st_mtim.tv_sec != after.st_mtim.tv_sec ||
        st.st_mtim.tv_nsec != after.st_mtim.tv_nsec || st.st_ctim.tv_sec != after.st_ctim.tv_sec ||
        st.st_ctim.tv_nsec != after.st_ctim.tv_nsec)) ok = false;
    close(fd);
    if (!op_artifact(directory, "recovery-input.bin", reply, used)) return false;
    if (ok) {
        char metadata[1024];
        int n = snprintf(metadata, sizeof metadata,
            "{\"schema_version\":1,\"scope\":\"recovery-input-file-observation-only\",\"device\":%" PRIuMAX ",\"inode\":%" PRIuMAX ",\"bytes\":%" PRIuMAX ",\"mtime_seconds\":%" PRIdMAX ",\"mtime_nanoseconds\":%ld,\"ctime_seconds\":%" PRIdMAX ",\"ctime_nanoseconds\":%ld,\"stat_unchanged_during_read\":true,\"application_acceptance\":false,\"transport_acceptance\":false}\n",
            (uintmax_t)st.st_dev, (uintmax_t)st.st_ino, (uintmax_t)st.st_size,
            (intmax_t)st.st_mtim.tv_sec, st.st_mtim.tv_nsec, (intmax_t)st.st_ctim.tv_sec, st.st_ctim.tv_nsec);
        if (n <= 0 || (size_t)n >= sizeof metadata || !op_artifact(directory, "recovery-input-stat.json", metadata, (size_t)n)) return false;
    }
    if (!ok || !op_zero(reply, 208, OP_BYTES) || op_u32(reply, 0) != 1 || op_u32(reply, 4) != OP_RECOVERY ||
        op_u32(reply, 8) != id->os || op_u64(reply, 16) != id->generation ||
        op_u64(reply, 32) != id->nonce_low || op_u64(reply, 40) != id->nonce_high ||
        op_u64(reply, 64) != 3 || op_u64(reply, 72) || op_u64(reply, 160) != 3 ||
        op_u64(reply, 168) != 2 || op_u64(reply, 176) || op_u64(reply, 184) ||
        !op_u64(reply, 200) || op_u64(reply, 24) != op_u64(reply, 200) ||
        op_u64(reply, 48) != op_u64(reply, 96) || op_u64(reply, 56) != op_u64(reply, 104) ||
        op_u32(reply, 12) != op_u32(reply, 136)) return false;
    id->pid = (int32_t)op_u32(reply, 136);
    if (!op_key_valid(id, reply)) return false;
    id->sequence = op_u64(reply, 200); id->selected = true;
    memcpy(id->key, reply + 80, sizeof id->key);
    return true;
}
#endif
