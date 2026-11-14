/* SPDX-License-Identifier: GPL-2.0-only */
/* Standalone adaptation of the retained Linux SHA256 round/constants and base
 * padding. See consulted-inputs.json in the source review capture.
 * Copyright (c) Jean-Luc Cooke <jlcooke@certainkey.com>
 * Copyright (c) Andrew McDonald <andrew@mcdonald.org.uk>
 * Copyright (c) 2002 James Morris <jmorris@intercode.com.au>
 * Copyright (c) 2014 Red Hat Inc.
 * Copyright (C) 2015 Linaro Ltd <ard.biesheuvel@linaro.org>
 */
#include "sha256.h"
#include <string.h>

static const uint32_t constants[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
};

static uint32_t rotate(uint32_t x, unsigned n) { return x >> n | x << (32 - n); }

static void transform(struct ac_sha256 *s, const unsigned char *p)
{
    uint32_t w[64];
    for (unsigned i = 0; i < 16; ++i)
        w[i] = (uint32_t)p[4*i] << 24 | (uint32_t)p[4*i+1] << 16 |
               (uint32_t)p[4*i+2] << 8 | (uint32_t)p[4*i+3];
    for (unsigned i = 16; i < 64; ++i) {
        uint32_t a = w[i-15], b = w[i-2];
        w[i] = (rotate(a, 7) ^ rotate(a, 18) ^ a >> 3) + w[i-16] +
               (rotate(b, 17) ^ rotate(b, 19) ^ b >> 10) + w[i-7];
    }
    uint32_t a=s->state[0], b=s->state[1], c=s->state[2], d=s->state[3];
    uint32_t e=s->state[4], f=s->state[5], g=s->state[6], h=s->state[7];
    for (unsigned i = 0; i < 64; ++i) {
        uint32_t t1 = h + (rotate(e, 6) ^ rotate(e, 11) ^ rotate(e, 25)) +
                      (g ^ (e & (f ^ g))) + constants[i] + w[i];
        uint32_t t2 = (rotate(a, 2) ^ rotate(a, 13) ^ rotate(a, 22)) +
                      ((a & b) | (c & (a | b)));
        h=g; g=f; f=e; e=d+t1; d=c; c=b; b=a; a=t1+t2;
    }
    s->state[0]+=a; s->state[1]+=b; s->state[2]+=c; s->state[3]+=d;
    s->state[4]+=e; s->state[5]+=f; s->state[6]+=g; s->state[7]+=h;
}

void ac_sha256_init(struct ac_sha256 *s)
{
    static const uint32_t initial[8] = {
        0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
        0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
    };
    memset(s, 0, sizeof *s);
    memcpy(s->state, initial, sizeof initial);
}

bool ac_sha256_update(struct ac_sha256 *s, const void *raw, size_t n)
{
    if ((raw == NULL && n != 0) || s->bytes > UINT64_MAX / 8 || n > UINT64_MAX / 8 - s->bytes) return false;
    const unsigned char *p = raw;
    s->bytes += n;
    while (n != 0) {
        size_t take = 64 - s->used;
        if (take > n) take = n;
        memcpy(s->block + s->used, p, take);
        s->used += take; p += take; n -= take;
        if (s->used == 64) { transform(s, s->block); s->used = 0; }
    }
    return true;
}

void ac_sha256_final(const struct ac_sha256 *input, unsigned char out[32])
{
    struct ac_sha256 s = *input;
    s.block[s.used++] = 0x80;
    if (s.used > 56) {
        memset(s.block + s.used, 0, 64 - s.used);
        transform(&s, s.block); s.used = 0;
    }
    memset(s.block + s.used, 0, 56 - s.used);
    uint64_t bits = s.bytes * 8;
    for (unsigned i = 0; i < 8; ++i) s.block[63-i] = (unsigned char)(bits >> (i*8));
    transform(&s, s.block);
    for (unsigned i = 0; i < 8; ++i)
        for (unsigned j = 0; j < 4; ++j) out[i*4+j] = (unsigned char)(s.state[i] >> (24-j*8));
}

void ac_hex(const unsigned char *p, size_t n, char *out)
{
    static const char digits[] = "0123456789abcdef";
    for (size_t i = 0; i < n; ++i) { out[i*2] = digits[p[i] >> 4]; out[i*2+1] = digits[p[i] & 15]; }
    out[n*2] = 0;
}
