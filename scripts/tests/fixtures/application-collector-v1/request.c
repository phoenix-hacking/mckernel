/* SPDX-License-Identifier: GPL-2.0-only */
#include "request.h"
#include <stdbool.h>
#include <string.h>

struct cursor { const uint8_t *bytes; size_t length, position; };

static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0] | (uint32_t)p[1] << 8 |
           (uint32_t)p[2] << 16 | (uint32_t)p[3] << 24;
}

static uint64_t le64(const uint8_t *p)
{
    return (uint64_t)le32(p) | (uint64_t)le32(p + 4) << 32;
}

static bool any_byte(const uint8_t *p, size_t n)
{
    for (size_t i = 0; i < n; ++i) if (p[i] != 0) return true;
    return false;
}

static bool letter(uint8_t c)
{
    return (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z');
}

static bool digit(uint8_t c) { return c >= '0' && c <= '9'; }

static enum acrq_error take_string(struct cursor *c, struct acrq_request *out,
                                  struct acrq_slice *slice)
{
    if (c->length - c->position < 4) return ACRQ_TRUNCATED;
    uint32_t n = le32(c->bytes + c->position);
    c->position += 4;
    if (n > ACRQ_STRING_MAX) return ACRQ_STRING;
    if ((size_t)n > c->length - c->position) return ACRQ_TRUNCATED;
    if (memchr(c->bytes + c->position, 0, n) != NULL) return ACRQ_STRING;
    if ((size_t)n + 1 > sizeof out->storage - out->storage_used) return ACRQ_SIZE;
    slice->offset = out->storage_used;
    slice->length = n;
    memcpy(out->storage + out->storage_used, c->bytes + c->position, n);
    out->storage_used += n;
    out->storage[out->storage_used++] = 0;
    c->position += n;
    return ACRQ_OK;
}

static bool case_name(const char *p, uint32_t n)
{
    if (n == 0 || n > 96 || (!letter((uint8_t)p[0]) && !digit((uint8_t)p[0]))) return false;
    for (uint32_t i = 0; i < n; ++i) {
        uint8_t b = (uint8_t)p[i];
        if (!letter(b) && !digit(b) && b != '.' && b != '_' && b != '-') return false;
    }
    return true;
}

static bool absolute_path(const char *p, uint32_t n, bool allow_root)
{
    if (n == 0 || p[0] != '/') return false;
    if (n == 1) return allow_root;
    uint32_t start = 1;
    for (uint32_t i = 1; i <= n; ++i) {
        if (i != n && p[i] != '/') continue;
        uint32_t component = i - start;
        if (component == 0 || (component == 1 && p[start] == '.') ||
            (component == 2 && p[start] == '.' && p[start + 1] == '.')) return false;
        start = i + 1;
    }
    return true;
}

/* Returns the length of a valid NAME prefix, or zero for an invalid entry. */
static uint32_t env_name(const char *p, uint32_t n)
{
    if (n < 2 || (!letter((uint8_t)p[0]) && p[0] != '_')) return 0;
    for (uint32_t i = 1; i < n; ++i) {
        uint8_t b = (uint8_t)p[i];
        if (b == '=') return i;
        if (!letter(b) && !digit(b) && b != '_') return 0;
    }
    return 0;
}

enum acrq_error acrq_decode(const void *bytes, size_t length,
                           struct acrq_request *out)
{
    if (out == NULL) return ACRQ_ARGUMENT;
    memset(out, 0, sizeof *out);
    enum acrq_error error = ACRQ_OK;
    if (bytes == NULL) { error = ACRQ_ARGUMENT; goto fail; }
    if (length < 256 || length > ACRQ_WIRE_MAX) { error = ACRQ_SIZE; goto fail; }
    const uint8_t *p = bytes;
    if (memcmp(p, "ACRQ0001", 8) != 0) { error = ACRQ_MAGIC; goto fail; }
    if (le32(p + 8) != 1) { error = ACRQ_VERSION; goto fail; }
    if (le32(p + 12) != 256) { error = ACRQ_HEADER; goto fail; }
    if (le32(p + 16) != length) { error = ACRQ_LENGTH; goto fail; }
    if (le32(p + 20) != 0 || any_byte(p + 216, 40)) { error = ACRQ_RESERVED; goto fail; }
    out->schema_version = 1;
    out->role = le32(p + 24);
    if (out->role != 1 && out->role != 2) { error = ACRQ_ROLE; goto fail; }
    out->profile = le32(p + 28);
    out->uid = le32(p + 32); out->gid = le32(p + 36);
    out->group_count = le32(p + 40); out->group = le32(p + 44);
    out->umask_value = le32(p + 48);
    if (out->profile != 1 || out->uid != 0 || out->gid != 0 ||
        out->group_count != 1 || out->group != 0 || out->umask_value != 18) {
        error = ACRQ_PROFILE; goto fail;
    }
    out->argc = le32(p + 52); out->envc = le32(p + 56);
    if (out->argc == 0 || out->argc > ACRQ_LIST_MAX || out->envc > ACRQ_LIST_MAX) {
        error = ACRQ_COUNTS; goto fail;
    }
    out->stdin_mode = le32(p + 60);
    out->stdout_mode = le32(p + 64); out->stderr_mode = le32(p + 68);
    if (out->stdin_mode > 1 || out->stdout_mode != 1 || out->stderr_mode != 1) {
        error = ACRQ_STREAM; goto fail;
    }
    out->timeout_ms = le32(p + 72); out->cleanup_timeout_ms = le32(p + 76);
    out->stdout_limit = le32(p + 80); out->stderr_limit = le32(p + 84);
    if (out->timeout_ms != 10000 || out->cleanup_timeout_ms != 15000 ||
        out->stdout_limit != 65536 || out->stderr_limit != 65536) {
        error = ACRQ_LIMIT; goto fail;
    }
    out->executable_size = le64(p + 88); out->stdin_size = le64(p + 96);
    if (out->executable_size == 0 || out->executable_size > ACRQ_ARTIFACT_MAX ||
        out->stdin_size > ACRQ_ARTIFACT_MAX || !any_byte(p + 104, 32) ||
        !any_byte(p + 136, 32) || !any_byte(p + 200, 16) ||
        (out->stdin_mode == 0 && (out->stdin_size != 0 || any_byte(p + 168, 32))) ||
        (out->stdin_mode == 1 && !any_byte(p + 168, 32))) {
        error = ACRQ_IDENTITY; goto fail;
    }
    memcpy(out->selected_inputs_sha256, p + 104, 32);
    memcpy(out->executable_sha256, p + 136, 32);
    memcpy(out->stdin_sha256, p + 168, 32);
    memcpy(out->attempt_id, p + 200, 16);
    struct cursor c = {.bytes = p, .length = length, .position = 256};
    error = take_string(&c, out, &out->case_id);
    if (error != ACRQ_OK) goto fail;
    if (!case_name(out->storage + out->case_id.offset, out->case_id.length)) {
        error = ACRQ_CASE_ID; goto fail;
    }
    error = take_string(&c, out, &out->executable_path);
    if (error != ACRQ_OK) goto fail;
    if (!absolute_path(out->storage + out->executable_path.offset, out->executable_path.length, false)) {
        error = ACRQ_PATH; goto fail;
    }
    error = take_string(&c, out, &out->cwd);
    if (error != ACRQ_OK) goto fail;
    if (!absolute_path(out->storage + out->cwd.offset, out->cwd.length, true)) {
        error = ACRQ_PATH; goto fail;
    }
    error = take_string(&c, out, &out->stdin_path);
    if (error != ACRQ_OK) goto fail;
    if (!absolute_path(out->storage + out->stdin_path.offset, out->stdin_path.length, false) ||
        (out->stdin_mode == 0 && strcmp(out->storage + out->stdin_path.offset, "/dev/null") != 0)) {
        error = ACRQ_PATH; goto fail;
    }
    for (uint32_t i = 0; i < out->argc; ++i) {
        error = take_string(&c, out, &out->argv[i]);
        if (error != ACRQ_OK) goto fail;
        if (i == 0 && out->argv[i].length == 0) { error = ACRQ_ARGV; goto fail; }
    }
    for (uint32_t i = 0; i < out->envc; ++i) {
        error = take_string(&c, out, &out->env[i]);
        if (error != ACRQ_OK) goto fail;
        const char *entry = out->storage + out->env[i].offset;
        uint32_t name_length = env_name(entry, out->env[i].length);
        if (name_length == 0) { error = ACRQ_ENV; goto fail; }
        for (uint32_t j = 0; j < i; ++j) {
            const char *earlier = out->storage + out->env[j].offset;
            if (env_name(earlier, out->env[j].length) == name_length &&
                memcmp(entry, earlier, name_length) == 0) {
                error = ACRQ_DUPLICATE_ENV; goto fail;
            }
        }
    }
    if (c.position != length) { error = ACRQ_TRAILING; goto fail; }
    return ACRQ_OK;
fail:
    memset(out, 0, sizeof *out);
    return error;
}

const char *acrq_error_name(enum acrq_error error)
{
    static const char *const names[] = {
        "OK", "ARGUMENT", "SIZE", "MAGIC", "VERSION", "HEADER", "LENGTH",
        "RESERVED", "ROLE", "PROFILE", "COUNTS", "STREAM", "LIMIT", "IDENTITY",
        "TRUNCATED", "STRING", "CASE_ID", "PATH", "ARGV", "ENV",
        "DUPLICATE_ENV", "TRAILING"
    };
    if ((unsigned)error >= sizeof names / sizeof names[0]) return "UNKNOWN";
    return names[(unsigned)error];
}
