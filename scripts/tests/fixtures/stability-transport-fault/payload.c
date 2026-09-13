/* SPDX-License-Identifier: GPL-2.0-only */
/* Ordinary libc payload: the guest controller kills its blocked read. */
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#define CHECK(x) do { if (!(x)) { dprintf(2, "NATIVE_FAILURE_APPLICATION FAIL line=%d errno=%d\n", __LINE__, errno); return 1; } } while (0)
int main(void)
{
    static const char ready[] = "NATIVE_FAILURE_READY\n";
    static const char passed[] = "NATIVE_FAILURE_PASS\n";
    unsigned char buffer[32];
    memset(buffer, 0x5a, sizeof buffer);
    CHECK(write(1, ready, sizeof ready - 1) == (ssize_t)(sizeof ready - 1));
    CHECK(read(0, buffer + 8, 16) == 16);
    for (unsigned i = 0; i < sizeof buffer; ++i)
        CHECK(buffer[i] == ((i >= 8 && i < 24) ? 0xa5 : 0x5a));
    CHECK(write(1, passed, sizeof passed - 1) == (ssize_t)(sizeof passed - 1));
    return 37;
}
