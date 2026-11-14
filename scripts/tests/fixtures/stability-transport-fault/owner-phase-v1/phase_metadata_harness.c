/* SPDX-License-Identifier: GPL-2.0-only */
/* Synthetic metadata only. Includes the actual client validator. No ioctl,
 * fork, guest, payload, clock replacement or runtime acceptance. */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "phase_client.h"

static unsigned checks, failures;
/* Independent literal ABI bytes: OS2, PID123, generation9, sequence1,
 * low nonce0123456789abcdef/high noncefedcba9876543210. */
static const unsigned char request_one[256] = {
    [0]=1, [4]=1, [8]=2, [12]=123, [16]=9, [24]=1,
    [32]=0xef, [33]=0xcd, [34]=0xab, [35]=0x89, [36]=0x67, [37]=0x45, [38]=0x23, [39]=1,
    [40]=0x10, [41]=0x32, [42]=0x54, [43]=0x76, [44]=0x98, [45]=0xba, [46]=0xdc, [47]=0xfe
};
static const unsigned char reply_one[256] = {
    [0]=1, [4]=1, [8]=2, [12]=123, [16]=9, [24]=1,
    [32]=0xef, [33]=0xcd, [34]=0xab, [35]=0x89, [36]=0x67, [37]=0x45, [38]=0x23, [39]=1,
    [40]=0x10, [41]=0x32, [42]=0x54, [43]=0x76, [44]=0x98, [45]=0xba, [46]=0xdc, [47]=0xfe,
    [64]=1, [80]=11, [88]=12, [96]=13, [104]=14, [112]=3,
    [121]=0x10, [128]=0x28, [129]=0x10, [136]=123, [140]=1,
    [144]=0xc8, [145]=1, [148]=2, [152]=9, [160]=1, [200]=1
};

static void check(bool condition, const char *name)
{
    ++checks;
    if (!condition) { ++failures; dprintf(2, "PHASE_METADATA_ASSERTION_FAILURE %s\n", name); }
}

static void initial(struct op_identity *id, unsigned char *request, struct op_observation *out)
{
    memset(id, 0, sizeof *id);
    id->os=2; id->pid=123; id->generation=9;
    id->nonce_low=UINT64_C(0x0123456789abcdef); id->nonce_high=UINT64_C(0xfedcba9876543210);
    memcpy(request, request_one, 256);
    memset(out, 0, sizeof *out);
    memcpy(out->reply, reply_one, 256);
    out->open_result=7; out->ioctl_called=true; out->response_received=true; out->reaped=true;
}

static void selected(struct op_identity *id, unsigned char *request, struct op_observation *out, unsigned phase)
{
    initial(id, request, out);
    enum op_result result=op_validate(id, OP_SELECT, request, out);
    check(result==OP_OK && id->selected && id->sequence==1 && out->consumed &&
          !memcmp(id->key, reply_one+80, 80), "literal-selection-prerequisite");
    request[4]=(unsigned char)phase; request[24]=2; request[48]=13; request[56]=14;
    memcpy(out->reply, request, 64);
    out->reply[64]=3; out->reply[160]=3; out->reply[168]=2; out->reply[200]=2;
    out->consumed=false;
    if (phase==OP_TERMINAL) { out->reply[176]=0xe8; out->reply[177]=3; }
}

int main(void)
{
    struct op_identity id;
    struct op_observation out;
    unsigned char request[256];
    check(op_initialize(&id,"2","9","0123456789abcdeffedcba9876543210",123) &&
          id.os==2 && id.generation==9 && id.pid==123 && id.sequence==0 && !id.selected &&
          id.nonce_low==UINT64_C(0x0123456789abcdef) && id.nonce_high==UINT64_C(0xfedcba9876543210),
          "literal-nonce-word-order");
    check(!op_initialize(&id,"02","9","0123456789abcdeffedcba9876543210",123), "leading-zero-os");
    check(!op_initialize(&id,"64","9","0123456789abcdeffedcba9876543210",123), "os-range");
    check(!op_initialize(&id,"2","0","0123456789abcdeffedcba9876543210",123), "zero-generation");
    check(!op_initialize(&id,"2","18446744073709551616","0123456789abcdeffedcba9876543210",123), "generation-overflow");
    check(!op_initialize(&id,"2","9","00000000000000000000000000000000",123), "zero-nonce");
    check(!op_initialize(&id,"2","9","0123456789ABCDEFFEDCBA9876543210",123), "uppercase-nonce");
    initial(&id,request,&out);
    check(op_validate(&id,OP_SELECT,request,&out)==OP_OK && id.selected && id.sequence==1 &&
          out.consumed && !memcmp(id.key,reply_one+80,80), "valid-literal-SELECT");
    /* Each alteration has an independent expected rejection; no decoding or
     * expected bytes are obtained from the implementation's endian helpers. */
    static const unsigned changed[] = {0,4,8,12,16,24,32,40,48,56,64,128,136,148,152,160,168,176,184,192,200,208,255};
    for (unsigned i=0;i<sizeof changed/sizeof changed[0];++i) {
        initial(&id,request,&out); out.reply[changed[i]]^=1;
        char name[64]; snprintf(name,sizeof name,"SELECT-byte-%u-mismatch",changed[i]);
        check(op_validate(&id,OP_SELECT,request,&out)==OP_FAILED,name);
    }
    static const unsigned required[] = {80,88,96,104};
    for (unsigned i=0;i<sizeof required/sizeof required[0];++i) {
        initial(&id,request,&out); out.reply[required[i]]=0;
        char name[64]; snprintf(name,sizeof name,"SELECT-zero-required-identity-%u",required[i]);
        check(op_validate(&id,OP_SELECT,request,&out)==OP_FAILED,name);
    }
    initial(&id,request,&out); out.reply[140]=0xff; out.reply[141]=0xff; out.reply[142]=0xff; out.reply[143]=0xff;
    check(op_validate(&id,OP_SELECT,request,&out)==OP_FAILED,"negative-cpu");
    initial(&id,request,&out); out.reply[144]=0; out.reply[145]=0;
    check(op_validate(&id,OP_SELECT,request,&out)==OP_FAILED,"zero-requester");
    initial(&id,request,&out); out.response_received=false;
    check(op_validate(&id,OP_SELECT,request,&out)==OP_FAILED,"missing-response");
    initial(&id,request,&out); out.reaped=false;
    check(op_validate(&id,OP_SELECT,request,&out)==OP_FAILED,"unreaped-probe");
    initial(&id,request,&out); out.raw_wait=9;
    check(op_validate(&id,OP_SELECT,request,&out)==OP_FAILED,"synthetic-signaled-wait");
    initial(&id,request,&out); out.raw_wait=137<<8;
    check(op_validate(&id,OP_SELECT,request,&out)==OP_FAILED,"synthetic-exit137-is-not-success");
    initial(&id,request,&out); out.timed_out=true;
    check(op_validate(&id,OP_SELECT,request,&out)==OP_FAILED,"late-complete-observation");
    initial(&id,request,&out); out.ioctl_called=false;
    check(op_validate(&id,OP_SELECT,request,&out)==OP_FAILED,"no-ioctl-call");
    initial(&id,request,&out); memset(out.reply+64,0,192); out.ioctl_result=-1; out.ioctl_errno=EAGAIN;
    check(op_validate(&id,OP_SELECT,request,&out)==OP_RETRY && !out.consumed && id.sequence==0 && !id.selected,
          "unchanged-EAGAIN-does-not-consume");
    initial(&id,request,&out); memset(out.reply+64,0,192); out.ioctl_result=-1; out.ioctl_errno=EFAULT;
    check(op_validate(&id,OP_SELECT,request,&out)==OP_FAILED && !out.consumed && id.sequence==0,
          "ambiguous-copyout-never-retried");
    selected(&id,request,&out,OP_TERMINAL);
    check(op_validate(&id,OP_TERMINAL,request,&out)==OP_OK && out.consumed && id.sequence==2,"valid-Terminal");
    selected(&id,request,&out,OP_RECOVERY);
    check(op_validate(&id,OP_RECOVERY,request,&out)==OP_OK && out.consumed && id.sequence==2,"valid-Recovery");
    selected(&id,request,&out,OP_TERMINAL); out.reply[176]=0; out.reply[177]=0;
    check(op_validate(&id,OP_TERMINAL,request,&out)==OP_FAILED,"Terminal-needs-terminal-time");
    selected(&id,request,&out,OP_RECOVERY); out.reply[176]=1;
    check(op_validate(&id,OP_RECOVERY,request,&out)==OP_FAILED,"Recovery-cannot-be-terminal");
    selected(&id,request,&out,OP_TERMINAL); out.reply[88]=13;
    check(op_validate(&id,OP_TERMINAL,request,&out)==OP_FAILED,"changed-selected-worker");
    selected(&id,request,&out,OP_TERMINAL); out.reply[200]=1;
    check(op_validate(&id,OP_TERMINAL,request,&out)==OP_FAILED && id.sequence==1 && !out.consumed,"stale-consumption-sequence");
    selected(&id,request,&out,OP_TERMINAL); out.reply[64]=0; out.reply[160]=2; out.reply[168]=0;
    out.reply[176]=0; out.reply[177]=0; memset(out.reply+72,0xff,8); out.reply[72]=0xf5;
    out.ioctl_result=-1; out.ioctl_errno=EAGAIN;
    check(op_validate(&id,OP_TERMINAL,request,&out)==OP_RETRY && out.consumed && id.sequence==2,
          "dispatched-EAGAIN-consumes-sequence");
    selected(&id,request,&out,OP_TERMINAL); out.reply[184]=1;
    check(op_validate(&id,OP_TERMINAL,request,&out)==OP_FAILED,"verification-invalid-never-qualifies");
    selected(&id,request,&out,OP_TERMINAL); out.reply[168]=1;
    check(op_validate(&id,OP_TERMINAL,request,&out)==OP_FAILED,"missing-AcceptedReturn-sequence");
    selected(&id,request,&out,OP_QUIET); out.reply[64]=4; out.reply[176]=0xe8; out.reply[177]=3;
    check(op_validate(&id,OP_QUIET,request,&out)==OP_OK,"valid-TerminalPlusFive-shape");
    selected(&id,request,&out,OP_AFTER_HELLO); out.reply[64]=4;
    check(op_validate(&id,OP_AFTER_HELLO,request,&out)==OP_OK,"valid-AfterEightHello-shape");
    dprintf(1,"{\"schema_version\":1,\"scope\":\"synthetic-owner-phase-metadata-only\",\"status\":\"%s\",\"checks\":%u,\"failures\":%u,\"actual_ioctl_executed\":false,\"application_acceptance\":false,\"transport_acceptance\":false}\n",
            failures ? "FAIL" : "PASS",checks,failures);
    return failures ? 1 : 0;
}
