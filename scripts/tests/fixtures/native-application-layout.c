/* SPDX-License-Identifier: GPL-2.0 */
#include <stddef.h>
#include <stdio.h>
#include "native-application-c-reference.h"
int main(void)
{
    printf("%zu %zu %zu %zu %zu %zu %zu %zu %zu %zu %zu %zu %d %d\n",
        sizeof(struct ikc_scd_packet), _Alignof(struct ikc_scd_packet),
        offsetof(struct ikc_scd_packet, header), offsetof(struct ikc_scd_packet, msg),
        offsetof(struct ikc_scd_packet, err), offsetof(struct ikc_scd_packet, reply),
        offsetof(struct ikc_scd_packet, ref), offsetof(struct ikc_scd_packet, osnum),
        offsetof(struct ikc_scd_packet, pid), offsetof(struct ikc_scd_packet, arg),
        offsetof(struct ikc_scd_packet, req), offsetof(struct ikc_scd_packet, resp_pa),
        SCD_MSG_CLEANUP_PROCESS, SCD_MSG_CLEANUP_PROCESS_RESP);
    return 0;
}
