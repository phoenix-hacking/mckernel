/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef AC_LINUX_SHA256_H
#define AC_LINUX_SHA256_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
struct ac_sha256 { uint32_t state[8]; uint64_t bytes; size_t used; unsigned char block[64]; };
void ac_sha256_init(struct ac_sha256 *state);
bool ac_sha256_update(struct ac_sha256 *state, const void *bytes, size_t length);
void ac_sha256_final(const struct ac_sha256 *state, unsigned char digest[32]);
void ac_hex(const unsigned char *bytes, size_t length, char *output);
#endif
