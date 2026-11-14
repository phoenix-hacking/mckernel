#define _GNU_SOURCE
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define main candidate_pid1_never_called
#include "collector-typed-avx-final-release.c"
#undef main
static int baseline_publish_lifecycle_stream(int console, const char *name,
                                    const struct stream *stream)
{
    char b[FRAME_LIMIT]; size_t n = 0;
    if (append(b, &n, "ND_LIFECYCLE_STREAM {\"name\":\"%s\",\"capture\":", name) ||
        stream_json(b, &n, stream) || append(b, &n, "}\n") || n > PIPE_BUF)
        return -1;
    return write_all(console, b, n);
}

static int baseline_publish_lifecycle(int console, const struct result *r, int helper_rc)
{
    char b[FRAME_LIMIT]; size_t n = 0;
    if (append(b, &n, "ND_LIFECYCLE {\"argv\":[\"/bin/native-lifecycle-probe\",\"0\"],"
               "\"helper_result\":%d,\"raw_wait_status\":%d,\"fault\":%d,"
               "\"timeout\":%d,\"clean\":%d,\"child_stage\":%d,\"child_errno\":%d,"
               "\"started_ns\":%llu,\"reaped_ns\":%llu,\"finished_ns\":%llu}\n",
               helper_rc, r->status, r->fault, r->timeout, r->clean,
               r->child_stage, r->child_errno, (unsigned long long)r->started,
               (unsigned long long)r->reaped, (unsigned long long)r->finished) ||
        n > PIPE_BUF || write_all(console, b, n) ||
        baseline_publish_lifecycle_stream(console, "stdout", &r->out) ||
        baseline_publish_lifecycle_stream(console, "stderr", &r->err))
        return -1;
    return 0;
}

static int baseline_publish_resource_stream(int console, const char *name,
                                   const struct stream *s)
{
    char b[FRAME_LIMIT]; size_t n = 0;
    if (append(b, &n, "ND_RESOURCE_STREAM {\"name\":\"%s\",\"eof\":%s,"
        "\"observed\":%llu,\"retained\":%zu,\"discarded\":%llu,\"limit\":%zu,"
        "\"eof_ns\":%llu}\n", name, s->eof ? "true" : "false",
        (unsigned long long)s->observed, s->kept,
        (unsigned long long)(s->observed - s->kept), s->limit,
        (unsigned long long)s->eof_ns) || n > PIPE_BUF || write_all(console, b, n))
        return -1;
    for (size_t offset = 0; offset < s->kept; offset += 512) {
        size_t count = s->kept - offset;
        if (count > 512) count = 512;
        char hex[1025]; const char *digits = "0123456789abcdef";
        for (size_t i = 0; i < count; ++i) {
            hex[2*i] = digits[s->data[offset+i] >> 4];
            hex[2*i+1] = digits[s->data[offset+i] & 15];
        }
        hex[2*count] = 0; n = 0;
        if (append(b, &n, "ND_RESOURCE_CHUNK {\"name\":\"%s\",\"offset\":%zu,\"hex\":\"%s\"}\n",
                   name, offset, hex) || n > PIPE_BUF || write_all(console, b, n))
            return -1;
    }
    return 0;
}

static int baseline_publish_resource(int console, const struct result *r, int rc)
{
    char b[FRAME_LIMIT]; size_t n = 0;
    if (append(b, &n, "ND_RESOURCE {\"argv\":[\"/bin/native-resource-release-probe\"],"
        "\"helper_result\":%d,\"raw_wait_status\":%d,\"fault\":%d,\"timeout\":%d,"
        "\"clean\":%d,\"child_stage\":%d,\"child_errno\":%d,\"started_ns\":%llu,"
        "\"reaped_ns\":%llu,\"finished_ns\":%llu}\n", rc, r->status,
        r->fault, r->timeout, r->clean, r->child_stage, r->child_errno,
        (unsigned long long)r->started, (unsigned long long)r->reaped,
        (unsigned long long)r->finished) || n > PIPE_BUF || write_all(console, b, n) ||
        baseline_publish_resource_stream(console, "stdout", &r->out) ||
        baseline_publish_resource_stream(console, "stderr", &r->err)) return -1;
    return 0;
}

static int fake_calls, fake_procfs=1, fake_result_code;
static struct result fake_capture;
static int fake_helper_capture(const char *tag,const char *path,char *const av[],int *safe,struct result *out)
{
    assert(!strcmp(tag,"final-lifecycle") || !strcmp(tag,"final-resource-release"));
    assert(!strcmp(path,"/bin/native-lifecycle-probe") || !strcmp(path,"/bin/native-resource-release-probe"));
    assert(!strcmp(av[0],path)); fake_calls++;
    *out=fake_capture; if(!out->clean)*safe=0;
    return fake_result_code;
}
static int fake_retired_at(const char *path) { assert(!strcmp(path,"/proc/mcos0"));return fake_procfs; }
#define helper_capture fake_helper_capture
#define retired_at fake_retired_at
static int fixture_final_lifecycle_after_reboot(const struct reboot_capture *reboot,
    int reboot_rc, int good, int *safe, int *attempted, struct result *capture)
{
    const struct result *r=&reboot->boot;
    *attempted=0;
    if (!good || !*safe || reboot_rc || !reboot->boot_attempted || reboot->helper_rc ||
        r->status || r->fault || r->timeout || !r->clean || !r->out.eof ||
        !r->err.eof || r->out.observed!=r->out.kept || r->err.observed ||
        retired_at("/proc/mcos0")!=1) return -1;
    *attempted=1;
    return helper_capture("final-lifecycle", "/bin/native-lifecycle-probe",
        (char *const[]){"/bin/native-lifecycle-probe","0",NULL},safe,capture);
}

static int fixture_final_resource_after_lifecycle(const struct result *payload,
    const struct result *lifecycle, int lifecycle_rc, int good, int *safe,
    int *attempted, struct result *capture)
{
    *attempted=0;
    if (!resource_prerequisites(payload,lifecycle,good,*safe,lifecycle_rc)) return -1;
    *attempted=1;
    return helper_capture("final-resource-release", "/bin/native-resource-release-probe",
        (char *const[]){"/bin/native-resource-release-probe",NULL},safe,capture);
}

#undef retired_at
#undef helper_capture
static void read_result(struct result *r,const char *path,size_t limit,unsigned long long start,unsigned long long end)
{
    memset(r,0,sizeof *r);r->clean=1;r->out.limit=r->err.limit=limit;
    r->out.eof=r->err.eof=1;r->started=start;r->reaped=end-1;r->finished=end;
    r->out.eof_ns=r->err.eof_ns=start+1;
    FILE *file=fopen(path,"rb");assert(file);
    r->out.kept=fread(r->out.data,1,limit,file);assert(!ferror(file) && feof(file) && fclose(file)==0);
    r->out.observed=r->out.kept;
}
int main(int argc,char **argv)
{
    assert(argc==5);unsigned long long base=strtoull(argv[4],NULL,10);
    struct result payload,life,pool;read_result(&payload,argv[1],1024,1,10);
    read_result(&life,argv[2],1024,base+1000,base+2000);
    read_result(&pool,argv[3],4096,base+3000,base+4000);
    assert(typed_avx_stdout(payload.out.data,payload.out.kept));
    for(int scenario=0;scenario<9;scenario++) {
        struct reboot_capture reboot;memset(&reboot,0,sizeof reboot);
        reboot.boot=life;reboot.boot_attempted=1;reboot.boot.finished=base;
        struct result captured_life,captured_pool,test_payload=payload;
        int safe=1,good=1,reboot_rc=0,la=0,pa=0;
        fake_capture=life;fake_calls=0;fake_procfs=1;fake_result_code=0;
        if(scenario==1)safe=0;
        if(scenario==2)reboot_rc=-1;
        if(scenario==3)reboot.boot.clean=0;
        if(scenario==4)fake_procfs=0;
        if(scenario==5)fake_result_code=-1;
        if(scenario==6)test_payload.out.data[0]='X';
        if(scenario==7)fake_capture.status=1;
        if(scenario==8) {char *p=strstr((char*)fake_capture.out.data,"\"return\":5");assert(p);p[9]='4';}
        int lr=fixture_final_lifecycle_after_reboot(&reboot,reboot_rc,good,&safe,&la,&captured_life);
        fake_capture=pool;
        int pr=fixture_final_resource_after_lifecycle(&test_payload,&captured_life,lr,good,&safe,&pa,&captured_pool);
        if(scenario==0)assert(lr==0 && pr==0 && la==1 && pa==1 && fake_calls==2);
        else {assert(pr!=0 && pa==0);assert(fake_calls==(scenario>=5?1:0));}
    }
    assert(puts("BASELINE_BEGIN")>=0 && fflush(stdout)==0);
    assert(baseline_publish_lifecycle(1,&life,0)==0 && baseline_publish_resource(1,&pool,0)==0);
    assert(puts("FIRST_BEGIN")>=0 && fflush(stdout)==0);
    assert(publish_lifecycle(1,&life,0,0)==0 && publish_resource(1,&pool,0,0)==0);
    assert(puts("FINAL_BEGIN")>=0 && fflush(stdout)==0);
    assert(publish_lifecycle(1,&life,0,1)==0 && publish_resource(1,&pool,0,1)==0);
    assert(puts("END")>=0 && fflush(stdout)==0);return 0;
}
