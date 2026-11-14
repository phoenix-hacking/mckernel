/* SPDX-License-Identifier: GPL-2.0-only */
/* Actual C metadata validator with independent literal input/output vectors.
 * No ioctl, fork, guest, response-memory read or controller-main execution. */
#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif
#include "phase_client.h"
struct vector {
    const char *name;
    uint32_t phase;
    struct op_identity identity;
    unsigned char request[OP_BYTES];
    struct op_observation observation;
    enum op_result expected;
    bool consumed;
    struct op_identity after;
};
#include "metadata_vectors.h"

static bool same_identity(const struct op_identity *a, const struct op_identity *b)
{
#define EQ(field) (a->field == b->field)
    return EQ(os) && EQ(pid) && EQ(generation) && EQ(nonce_low) && EQ(nonce_high) &&
        EQ(sequence) && EQ(attempt) && EQ(selected) && EQ(held) && EQ(released) && EQ(release_possible) &&
        EQ(mode) && EQ(last_snapshot) && EQ(timer_seconds) && EQ(held_ns) && EQ(terminal_ns) &&
        EQ(barrier_calls) && EQ(host_hold_calls) && !memcmp(a->key,b->key,sizeof a->key) &&
        !memcmp(a->capture_digest,b->capture_digest,sizeof a->capture_digest);
#undef EQ
}
static bool retain(int directory, const char *name, const void *bytes, size_t count)
{
    int fd=openat(directory,name,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);
    if(fd<0) return false;
    bool ok=op_write_all(fd,bytes,count) && fsync(fd)==0;
    if(close(fd)<0) ok=false;
    return ok;
}
int main(int argc,char **argv)
{
    if(argc!=2 || argv[1][0]!='/' || mkdir(argv[1],0700)<0) return 2;
    int directory=open(argv[1],O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);
    if(directory<0) return 2;
    for(size_t i=0;i<sizeof vectors/sizeof vectors[0];++i) {
        const struct vector *v=&vectors[i];
        struct op_identity id=v->identity;
        struct op_observation out=v->observation;
        enum op_result actual=op_validate(&id,v->phase,v->request,&out);
        bool pass=actual==v->expected && out.consumed==v->consumed && same_identity(&id,&v->after);
        char name[160],report[1024];
        /* Preserve every actual field, including failure-only changes, using
         * this pinned ELF/header's native struct layout. Padding is opaque. */
        snprintf(name,sizeof name,"%s.identity.bin",v->name);
        if(!retain(directory,name,&id,sizeof id)) return 3;
        snprintf(name,sizeof name,"%s.observation.bin",v->name);
        if(!retain(directory,name,&out,sizeof out)) return 3;
        snprintf(name,sizeof name,"%s.request.bin",v->name);
        if(!retain(directory,name,v->request,sizeof v->request)) return 3;
        snprintf(name,sizeof name,"%s.reply.bin",v->name);
        if(!retain(directory,name,v->observation.reply,OP_BYTES)) return 3;
        int n=snprintf(report,sizeof report,
            "{\"case\":\"%s\",\"status\":\"%s\",\"actual_result\":%d,\"expected_result\":%d,\"consumed\":%s,\"expected_consumed\":%s,\"identity_matches\":%s,\"sequence\":%" PRIu64 ",\"selected\":%s,\"held\":%s,\"release_possible\":%s,\"released\":%s,\"actual_ioctl_executed\":false,\"application_acceptance\":false,\"transport_acceptance\":false}\n",
            v->name,pass?"PASS":"FAIL",actual,v->expected,out.consumed?"true":"false",v->consumed?"true":"false",same_identity(&id,&v->after)?"true":"false",id.sequence,id.selected?"true":"false",id.held?"true":"false",id.release_possible?"true":"false",id.released?"true":"false");
        snprintf(name,sizeof name,"%s.result.json",v->name);
        if(n<=0 || (size_t)n>=sizeof report || !retain(directory,name,report,(size_t)n) || fsync(directory)<0) return 3;
        dprintf(pass?1:2,"PUBLISHED_CLIENT_METADATA %s %s\n",v->name,pass?"PASS":"FAIL");
        if(!pass) {close(directory);return 1;}
    }
    if(close(directory)<0) return 3;
    return 0;
}
