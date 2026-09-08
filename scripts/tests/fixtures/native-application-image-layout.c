/* SPDX-License-Identifier: GPL-2.0 */
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <sys/types.h>
#include <sys/resource.h>
#include "../../../executer/include/uprotocol.h"
#include "native-application-c-reference.h"

_Static_assert(SCD_MSG_PROCFS_TID_DELETE == 0x45, "existing guest deletion message");

int main(void)
{
#define FIELD(name) offsetof(struct program_load_desc, name)
    const unsigned long long values[] = {
        sizeof(struct program_load_desc), _Alignof(struct program_load_desc),
        sizeof(struct program_image_section), _Alignof(struct program_image_section),
        FIELD(sections), PLD_MAGIC, FIELD(num_sections), FIELD(cpu), FIELD(pid),
        FIELD(cred), FIELD(entry), FIELD(user_start), FIELD(user_end), FIELD(rprocess),
        FIELD(rpgtable), FIELD(args), FIELD(args_len), FIELD(envs), FIELD(envs_len),
        FIELD(interp_align), FIELD(cpu_set), FIELD(profile),
    };
    for (size_t i = 0; i < sizeof(values) / sizeof(values[0]); ++i)
        printf("%llu%c", values[i], i + 1 == sizeof(values) / sizeof(values[0]) ? '\n' : ' ');
    return 0;
}
