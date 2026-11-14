/* SPDX-License-Identifier: GPL-2.0-only */
/* Literal SHA256 known answers; links the actual implementation separately. */
#include "sha256.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>

static int answer(const char *name, const void *bytes, size_t length, size_t chunk, const char *expected)
{
    struct ac_sha256 state; ac_sha256_init(&state);
    const unsigned char *p = bytes;
    for (size_t offset = 0; offset < length;) {
        size_t n = length - offset < chunk ? length - offset : chunk;
        if (!ac_sha256_update(&state, p + offset, n)) return 1;
        offset += n;
    }
    struct ac_sha256 before = state;
    unsigned char digest[32]; char hex[65];
    ac_sha256_final(&state, digest); ac_hex(digest, 32, hex);
    if (memcmp(&before, &state, sizeof state) || strcmp(hex, expected)) {
        fprintf(stderr, "FAIL %s actual=%s expected=%s\n", name, hex, expected); return 1;
    }
    printf("PASS %s\n", name); return 0;
}

int main(void)
{
    static const char multi[] = "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq";
    if (answer("empty", "", 0, 1, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855") ||
        answer("abc", "abc", 3, 1, "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad") ||
        answer("multi-56", multi, sizeof multi - 1, 7, "248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1")) return 1;
    /* Independently frozen Python hashlib results for bytes(range(n)), n<256. */
    static const struct { size_t length; const char *digest; } boundaries[] = {
        {55, "463eb28e72f82e0a96c0a4cc53690c571281131f672aa229e0d45ae59b598b59"},
        {56, "da2ae4d6b36748f2a318f23e7ab1dfdf45acdc9d049bd80e59de82a60895f562"},
        {63, "29af2686fd53374a36b0846694cc342177e428d1647515f078784d69cdb9e488"},
        {64, "fdeab9acf3710362bd2658cdc9a29e8f9c757fcf9811603a8c447cd1d9151108"},
        {65, "4bfd2c8b6f1eec7a2afeb48b934ee4b2694182027e6d0fc075074f2fabb31781"}
    };
    unsigned char bytes[65]; for (unsigned i = 0; i < sizeof bytes; ++i) bytes[i] = (unsigned char)i;
    for (size_t i = 0; i < sizeof boundaries / sizeof *boundaries; ++i) {
        char name[32]; snprintf(name, sizeof name, "boundary-%zu", boundaries[i].length);
        if (answer(name, bytes, boundaries[i].length, 13, boundaries[i].digest)) return 1;
    }
    struct ac_sha256 state, before; ac_sha256_init(&state); before = state;
    if (ac_sha256_update(&state, NULL, 1) || memcmp(&state, &before, sizeof state)) return 1;
    if (!ac_sha256_update(&state, NULL, 0) || memcmp(&state, &before, sizeof state)) return 1;
    state.bytes = UINT64_MAX / 8; before = state;
    if (ac_sha256_update(&state, "a", 1) || memcmp(&state, &before, sizeof state)) return 1;
    puts("PASS rejected-update-preserves-state"); return 0;
}
