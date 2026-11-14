/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef APPLICATION_COLLECTOR_REQUEST_V1_H
#define APPLICATION_COLLECTOR_REQUEST_V1_H

#include <stddef.h>
#include <stdint.h>

#define ACRQ_WIRE_MAX 65536U
#define ACRQ_STRING_MAX 4095U
#define ACRQ_LIST_MAX 64U
#define ACRQ_ARTIFACT_MAX UINT64_C(99614719)

enum acrq_error {
    ACRQ_OK = 0, ACRQ_ARGUMENT, ACRQ_SIZE, ACRQ_MAGIC, ACRQ_VERSION,
    ACRQ_HEADER, ACRQ_LENGTH, ACRQ_RESERVED, ACRQ_ROLE, ACRQ_PROFILE,
    ACRQ_COUNTS, ACRQ_STREAM, ACRQ_LIMIT, ACRQ_IDENTITY, ACRQ_TRUNCATED,
    ACRQ_STRING, ACRQ_CASE_ID, ACRQ_PATH, ACRQ_ARGV, ACRQ_ENV,
    ACRQ_DUPLICATE_ENV, ACRQ_TRAILING
};

struct acrq_slice { uint32_t offset, length; };

/* Desired values and opaque declared hashes only. No observed process fields.
 * Slices reference this object's storage; a successful struct copy is valid. */
struct acrq_request {
    uint32_t schema_version, role, profile;
    uint32_t uid, gid, group_count, group, umask_value;
    uint32_t argc, envc, stdin_mode, stdout_mode, stderr_mode;
    uint32_t timeout_ms, cleanup_timeout_ms, stdout_limit, stderr_limit;
    uint64_t executable_size, stdin_size;
    uint8_t selected_inputs_sha256[32], executable_sha256[32];
    uint8_t stdin_sha256[32], attempt_id[16];
    uint32_t execution_enabled; /* Always zero, even after ACRQ_OK. */
    struct acrq_slice case_id, executable_path, cwd, stdin_path;
    struct acrq_slice argv[ACRQ_LIST_MAX], env[ACRQ_LIST_MAX];
    uint32_t storage_used;
    char storage[ACRQ_WIRE_MAX];
};

/* Input/output must be valid, disjoint ranges. All output bytes are cleared on
 * failure if output is nonnull. The decoder never opens or executes anything. */
enum acrq_error acrq_decode(const void *bytes, size_t length,
                           struct acrq_request *output);
const char *acrq_error_name(enum acrq_error error);

#endif
