/* SPDX-License-Identifier: GPL-2.0 */
/* Actual packet declarations and original C producer are extracted verbatim. */
#include <assert.h>
#include <errno.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <sys/resource.h>
#include "../../../executer/include/uprotocol.h"
#include "native-procfs-answer-reference.h"

static unsigned char answer[128];
static void capture(void *channel, struct ikc_scd_packet *packet)
{
    assert(channel == answer);
    memcpy(answer, packet, sizeof(answer));
}

int main(void)
{
    const int errors[] = {0, -1, -5, -4095, INT32_MIN, INT32_MAX};
    _Static_assert(sizeof(struct ikc_scd_packet) == 128, "packet size");
    _Static_assert(offsetof(struct ikc_scd_packet, resp_pa) == 120, "unused reply field");
    _Static_assert(sizeof(struct procfs_read) == 808, "request size");
    for (unsigned i = 0; i < sizeof(errors) / sizeof(errors[0]); ++i) {
        struct ikc_scd_packet request = {0};
        request.msg = 0x12;
        request.ref = i % 4;
        request.pid = i % 2 ? 41 : 0;
        request.osnum = 7;
        request.arg = 0x1000UL * (i + 1);
        request.reply = (void *)(uintptr_t)(0x1234UL + i);
        request.resp_pa = UINT64_MAX;
        assert(procfs_answer_result(answer, &request, errors[i], capture) == 0);
        printf("ANSWER %u ", i);
        for (unsigned j = 0; j < sizeof(answer); ++j) printf("%02x", answer[j]);
        putchar('\n');
    }
    return 0;
}
