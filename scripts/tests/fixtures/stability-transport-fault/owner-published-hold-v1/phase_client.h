/* SPDX-License-Identifier: GPL-2.0-only */
/* Private verification ABI, version 2 of the new published-hold fixture.
 * Exact native-source binding remains a separately reviewed build requirement.
 * Source prepared only. Neither a successful ioctl nor this client accepts a guest. */
#ifndef STABILITY_OWNER_PUBLISHED_HOLD_CLIENT_V1_H
#define STABILITY_OWNER_PUBLISHED_HOLD_CLIENT_V1_H
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

#define OP_COMMAND UINT32_C(0xc100f502)
#define OP_BYTES 256u
#define OP_SELECT 1u
#define OP_TERMINAL 2u
#define OP_QUIET 3u
#define OP_RECOVERY 4u
#define OP_AFTER_HELLO 5u
#define OP_QUERY 6u
#define OP_ACCEPTED_STATUS 7u
#define OP_RELEASE_ACCEPTED 8u
#define OP_MAX_ATTEMPTS 24u /* Four artifacts each; total tree remains <256 entries. */
enum op_result { OP_FAILED = -1, OP_OK = 0, OP_RETRY = 1 };
struct op_identity {
    uint32_t os;
    int32_t pid;
    uint64_t generation, nonce_low, nonce_high, sequence;
    unsigned attempt;
    bool selected, held, released, release_possible;
    uint32_t mode;
    uint64_t last_snapshot, timer_seconds, held_ns, terminal_ns, barrier_calls, host_hold_calls;
    unsigned char capture_digest[32];
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
                                 const char *nonce, int32_t pid, const char *mode)
{
    memset(id, 0, sizeof *id);
    if (!strcmp(mode, "postpublish-notify")) id->mode = 2;
    else if (!strcmp(mode, "recoverable-backpressure")) id->mode = 3;
    else return false;
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

/* Validate complete child collection and defined native output. Fresh status
 * queries can consume successive sequences. A release is never redispatched,
 * including an untouched predispatch busy result: publication is conservatively
 * possible after its first submission. No response-memory read occurs here. */
static inline bool op_phase_allowed(const struct op_identity *id, uint32_t phase)
{
    return (id->mode == 2 || id->mode == 3) &&
        (phase == OP_SELECT || phase == OP_ACCEPTED_STATUS || phase == OP_RELEASE_ACCEPTED ||
         (id->mode == 2 && (phase == OP_TERMINAL || phase == OP_QUIET)) ||
         (id->mode == 3 && (phase == OP_RECOVERY || phase == OP_AFTER_HELLO)));
}
static inline bool op_deadline(uint64_t timer, uint64_t *deadline)
{
    if (timer > UINT64_MAX / UINT64_C(1000000000) - 5) return false;
    *deadline = (timer + 5) * UINT64_C(1000000000);
    return true;
}
static inline bool op_capture_digest(struct op_identity *id, const char *hex, unsigned sequence)
{
    if (!id->held || id->release_possible || sequence != 2 || strlen(hex) != 64) return false;
    unsigned char digest[32];
    for (unsigned i = 0; i < 64; ++i) {
        unsigned value;
        if (hex[i] >= '0' && hex[i] <= '9') value = (unsigned)(hex[i] - '0');
        else if (hex[i] >= 'a' && hex[i] <= 'f') value = (unsigned)(hex[i] - 'a') + 10;
        else return false;
        if (!(i & 1)) digest[i / 2] = (unsigned char)(value << 4);
        else digest[i / 2] |= (unsigned char)value;
    }
    if (op_zero(digest, 0, sizeof digest)) return false;
    memcpy(id->capture_digest, digest, sizeof digest);
    return true;
}
static inline bool op_request_valid(const struct op_identity *id, uint32_t phase, const unsigned char *request)
{
    if (op_u32(request, 0) != 2 || op_u32(request, 4) != phase ||
        op_u32(request, 8) != id->os || op_u32(request, 12) != (uint32_t)id->pid ||
        op_u64(request, 16) != id->generation || op_u64(request, 32) != id->nonce_low ||
        op_u64(request, 40) != id->nonce_high ||
        op_u64(request, 48) != (id->selected ? op_u64(id->key, 16) : 0) ||
        op_u64(request, 56) != (id->selected ? op_u64(id->key, 24) : 0)) return false;
    if (phase != OP_RELEASE_ACCEPTED) return op_zero(request, 64, OP_BYTES);
    return op_u64(request, 64) == 2 && op_u64(request, 72) == 2 &&
        !op_zero(request, 80, 112) && !memcmp(request + 80, id->capture_digest, 32) &&
        op_zero(request, 112, OP_BYTES);
}
static inline enum op_result op_validate(struct op_identity *id, uint32_t phase,
                                         const unsigned char *request, struct op_observation *out)
{
    if (!op_phase_allowed(id, phase) || !op_request_valid(id, phase, request) || !out->response_received || !out->reaped || out->timed_out ||
        !WIFEXITED(out->raw_wait) || WEXITSTATUS(out->raw_wait) != 0 || !out->ioctl_called ||
        out->open_result < 0 || out->open_errno || !out->begin_ns || out->end_ns < out->begin_ns ||
        memcmp(out->reply, request, 64)) return OP_FAILED;
    uint64_t sequence = op_u64(request, 24);
    if (id->sequence == UINT64_MAX || sequence != id->sequence + 1 ||
        op_u32(request, 0) != 2 || op_u32(request, 4) != phase) return OP_FAILED;
    if (!memcmp(out->reply, request, OP_BYTES))
        return phase != OP_RELEASE_ACCEPTED && out->ioctl_result == -1 && out->ioctl_errno == EAGAIN ? OP_RETRY : OP_FAILED;
    if (op_u64(out->reply, 200) != sequence) return OP_FAILED;
    out->consumed = true;
    id->sequence = sequence;
    const unsigned char *r = out->reply;
    uint64_t snapshot = op_u64(r, 64), phase_error = op_u64(r, 72), stage = op_u64(r, 160);
    uint64_t accepted = op_u64(r, 168), terminal = op_u64(r, 176), barrier = op_u64(r, 192);
    uint64_t timer = op_u64(r, 208), present = op_u64(r, 216), held = op_u64(r, 224);
    uint64_t holds = op_u64(r, 232), native_begin = op_u64(r, 240), native_end = op_u64(r, 248);
    if (!op_key_valid(id, r) || (id->selected && memcmp(id->key, r + 80, sizeof id->key)) ||
        op_u64(r, 184) || stage < 1 || stage > 5 || present > 1 || holds > UINT64_C(1000000) ||
        (!present && (timer || held)) || native_begin < out->begin_ns || native_end < native_begin ||
        native_end > out->end_ns || (held && held > native_end) || (terminal && terminal > native_end)) return OP_FAILED;
    if (id->held && (present != 1 || timer != id->timer_seconds || held != id->held_ns ||
        barrier != id->barrier_calls || holds < id->host_hold_calls || accepted != 2)) return OP_FAILED;
    if (id->terminal_ns && terminal != id->terminal_ns) return OP_FAILED;
    if (out->ioctl_result == -1) {
        if (out->ioctl_errno != EAGAIN || phase_error != (uint64_t)(int64_t)-EAGAIN || snapshot ||
            phase == OP_SELECT || phase == OP_RELEASE_ACCEPTED) return OP_FAILED;
        if (phase == OP_ACCEPTED_STATUS) {
            if (!id->selected || id->held || id->release_possible ||
                (stage != 1 && stage != 2) || accepted || terminal || present || held || holds) return OP_FAILED;
        } else if (!id->released || stage != 3 || accepted != 2) return OP_FAILED;
        return OP_RETRY;
    }
    if (out->ioctl_result != 0 || out->ioctl_errno || phase_error) return OP_FAILED;
    if (phase == OP_SELECT) {
        if (id->selected || sequence != 1 || snapshot != 1 || stage != 1 || accepted || terminal ||
            barrier || timer || present || held || holds) return OP_FAILED;
        memcpy(id->key, r + 80, sizeof id->key);
        id->selected = true;
    } else if (phase == OP_ACCEPTED_STATUS) {
        uint64_t deadline;
        if (!id->selected || id->held || id->release_possible || id->last_snapshot != 1 ||
            snapshot != 2 || stage != 5 || accepted != 2 || terminal || present != 1 || !held ||
            held > native_begin || !op_deadline(timer, &deadline) || native_end >= deadline) return OP_FAILED;
        id->held = true; id->timer_seconds = timer; id->held_ns = held; id->barrier_calls = barrier;
    } else if (phase == OP_RELEASE_ACCEPTED) {
        uint64_t deadline, reserve = id->mode == 3 ? UINT64_C(2000000000) : 0;
        if (!id->held || !id->release_possible || id->released || id->last_snapshot != 2 ||
            snapshot != 2 || stage != 3 || accepted != 2 || terminal || !op_deadline(timer, &deadline) ||
            native_end >= deadline || reserve >= deadline - native_end) return OP_FAILED;
        id->released = true;
    } else {
        if (!id->released || stage != 3 || accepted != 2) return OP_FAILED;
        if (phase == OP_TERMINAL || phase == OP_RECOVERY) {
            if (id->last_snapshot != 2 || snapshot != 3) return OP_FAILED;
        } else if (id->last_snapshot != 3 || snapshot != 4) return OP_FAILED;
        if ((phase == OP_TERMINAL || phase == OP_QUIET) != (terminal != 0)) return OP_FAILED;
        if (phase == OP_QUIET && (native_begin < terminal || native_begin - terminal < UINT64_C(5000000000))) return OP_FAILED;
        id->terminal_ns = terminal;
    }
    id->host_hold_calls = holds;
    id->last_snapshot = snapshot;
    return OP_OK;
}

static inline enum op_result op_call(struct op_identity *id, uint32_t phase, int directory,
                                     void (*progress)(unsigned), struct op_observation *out)
{
    memset(out, 0, sizeof *out); out->raw_wait = -1; out->open_result = -1;
    if (id->sequence == UINT64_MAX || id->attempt >= OP_MAX_ATTEMPTS || !op_phase_allowed(id, phase)) return OP_FAILED;
    unsigned char request[OP_BYTES] = {0};
    op_put32(request, 0, 2); op_put32(request, 4, phase); op_put32(request, 8, id->os);
    op_put32(request, 12, (uint32_t)id->pid); op_put64(request, 16, id->generation);
    op_put64(request, 24, id->sequence + 1); op_put64(request, 32, id->nonce_low); op_put64(request, 40, id->nonce_high);
    if (id->selected) { op_put64(request, 48, op_u64(id->key, 16)); op_put64(request, 56, op_u64(id->key, 24)); }
    if (phase == OP_RELEASE_ACCEPTED) {
        if (!id->held || id->released || id->release_possible || op_zero(id->capture_digest, 0, 32)) return OP_FAILED;
        op_put64(request, 64, 2); op_put64(request, 72, 2);
        memcpy(request + 80, id->capture_digest, 32);
        /* Conservative before any fork/ioctl attempt; never clear on error. */
        id->release_possible = true;
    }
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

#endif
