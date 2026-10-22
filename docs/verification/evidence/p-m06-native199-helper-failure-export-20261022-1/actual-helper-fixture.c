/* Actual selected candidate helper/serializer bodies; adapters only at
 * supervise, save_file and console writer. No guest/subprocess in this model. */
#include <assert.h>
#include <errno.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define STREAM_LIMIT 1024u
#define FRAME_LIMIT 4096u
struct stream {
    unsigned char data[STREAM_LIMIT];
    size_t kept;
    uint64_t observed, eof_ns;
    int eof;
};
struct result {
    struct stream out, err;
    int status, fault, timeout, clean;
    int child_stage, child_errno;
    uint64_t started, reaped, finished;
};

static int mode,write_calls;
static char captured[16384];static size_t capture_size;
static char *const helper_env[]={"PATH=/usr/bin:/bin",NULL};
static unsigned helper_timeout_ms(const char *path){assert(!strcmp(path,"/bin/native-boot"));return 60000;}
static int write_all(int fd,const void *data,size_t bytes)
{
    assert(fd==99);write_calls++;
    if(mode==5){errno=EIO;return -1;}
    assert(bytes<=sizeof captured-capture_size);memcpy(captured+capture_size,data,bytes);capture_size+=bytes;return 0;
}
static int save_file(const char *path,const void *data,size_t bytes)
{
    (void)data;(void)bytes;
    if(mode==4 && strstr(path,".stdout"))return -1;
    return 0;
}
static void supervise(const char *path,char *const av[],char *const env[],const char *cwd,unsigned timeout,struct result *r)
{
    (void)av;(void)env;assert(cwd==NULL && timeout==60000 && !strcmp(path,"/bin/native-boot"));
    memset(r,0,sizeof *r);r->clean=1;r->out.eof=r->err.eof=1;r->started=1;r->reaped=2;r->finished=3;
    const char *text="boot assertion source line215\n";
    if(mode==1 || mode==5)r->status=256;
    if(mode==1){r->out.kept=strlen(text);r->out.observed=r->out.kept;memcpy(r->out.data,text,r->out.kept);}
    if(mode==2){memset(r->out.data,'A',1024);r->out.kept=1024;r->out.observed=1025;}
    if(mode==3){r->clean=0;r->fault=1;r->status=-1;r->out.eof=r->err.eof=0;}
}
#include "actual-helper-functions.inc"
int main(void)
{
    for(mode=0;mode<6;mode++) {
        captured[0]=0;capture_size=0;write_calls=0;int safe=1;
        errno=ESTALE; /* save_file can fail without assigning a new errno. */
        int code=helper("boot","/bin/native-boot",(char *const[]){"/bin/native-boot",NULL},&safe,99);
        assert(code==(mode?-1:0));assert(safe==(mode==3?0:1));
        if(mode==0)assert(capture_size==0 && write_calls==0);
        else if(mode==5)assert(capture_size==0 && write_calls==1);
        else assert(capture_size>0 && write_calls==3);
        printf("HELPER_CASE {\"mode\":%d,\"return\":%d,\"safe\":%d,\"writes\":%d}\n",mode,code,safe,write_calls);
        assert(fwrite(captured,1,capture_size,stdout)==capture_size);
    }
    return 0;
}
