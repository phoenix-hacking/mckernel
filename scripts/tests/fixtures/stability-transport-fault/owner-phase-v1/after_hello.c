/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "phase_client.h"

int main(int argc, char **argv)
{
    /* Actual eight HELLO launches and same-OS provenance are external evidence. */
    if (argc != 7 || strcmp(argv[1], "--after-eight-hello") || argv[5][0] != '/' || argv[6][0] != '/') return 2;
    struct op_identity identity;
    if (!op_initialize(&identity, argv[2], argv[3], argv[4], 0)) return 2;
    if (mkdir(argv[6], 0700) < 0) return 2;
    int directory = open(argv[6], O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC);
    if (directory < 0) return 2;
    if (!op_load_recovery(&identity, argv[5], directory)) return 2;
    signal(SIGPIPE, SIG_IGN); signal(SIGCHLD, SIG_DFL);
    struct op_observation observation;
    enum op_result result = OP_FAILED;
    uint64_t begin = op_now(), deadline = begin + UINT64_C(10000000000);
    uint64_t current;
    while (begin && (current = op_now()) && current < deadline) {
        result = op_call(&identity, OP_AFTER_HELLO, directory, NULL, &observation);
        if (result != OP_RETRY) break;
        (void)poll(NULL, 0, 250);
    }
    current = op_now();
    bool ok = result == OP_OK && current && current < deadline;
    char record[1024];
    int n = snprintf(record, sizeof record,
        "{\"schema_version\":1,\"scope\":\"verification-phase-client-only\",\"phase\":\"AfterEightHello\",\"status\":\"%s\",\"os\":%u,\"generation\":%" PRIu64 ",\"selected_pid\":%d,\"last_consumed_sequence\":%" PRIu64 ",\"application_acceptance\":false,\"transport_acceptance\":false,\"eight_hello_launches_verified\":false}\n",
        ok ? "OBSERVATION_COLLECTED" : "FAIL", identity.os, identity.generation, identity.pid, identity.sequence);
    if (n <= 0 || (size_t)n >= sizeof record || !op_artifact(directory, "after-hello-result.json", record, (size_t)n)) return 1;
    return ok ? 0 : 1;
}
