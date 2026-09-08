/* SPDX-License-Identifier: GPL-2.0-only */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define ROOT "/sys/mckernel_sysfs_snoop_verify/"
#define CHECK(x) do { if (!(x)) {fprintf(stderr,"SNOOP_USER_FAIL line=%d errno=%d\n",__LINE__,errno);exit(1);} } while (0)
static ssize_t io(const char *path, bool writing, void *buffer, size_t size)
{
    int fd=open(path,writing?O_WRONLY:O_RDONLY);
    if(fd<0)return -1;
    ssize_t result=writing?write(fd,buffer,size):read(fd,buffer,size);
    int error=errno;
    CHECK(close(fd)==0);errno=error;return result;
}
static void control(const char *path, bool enabled)
{
    char value[2]={enabled?'1':'0','\n'};CHECK(io(path,true,value,2)==2);
}
struct status {unsigned phase,reclaimed;unsigned long long writes;};
static struct status status(void)
{
    char text[128]={0};struct status result;
    CHECK(io(ROOT "status",false,text,sizeof(text)-1)>0);
    CHECK(sscanf(text,"%u %u %llu",&result.phase,&result.reclaimed,&result.writes)==3);
    return result;
}
static void value(const char *path,const char *expected)
{
    char actual[128];size_t size=strlen(expected);
    CHECK(io(path,false,actual,sizeof(actual))==(ssize_t)size);
    CHECK(memcmp(actual,expected,size)==0);
}
static const char *const names[]={"d32","d64","u32","u64","u32K"};
static void number(char *output,size_t size,int type,uint64_t wide,uint32_t narrow)
{
    int n;
    switch(type){
    case 0:n=snprintf(output,size,"%" PRId32 "\n",(int32_t)narrow);break;
    case 1:n=snprintf(output,size,"%" PRId64 "\n",(int64_t)wide);break;
    case 2:n=snprintf(output,size,"%" PRIu32 "\n",narrow);break;
    case 3:n=snprintf(output,size,"%" PRIu64 "\n",wide);break;
    default:n=snprintf(output,size,"%" PRIu32 "K\n",narrow>>10);break;
    }
    CHECK(n>0 && n<(int)size);
}
struct stress {int type;};
static void *stress(void *argument)
{
    int type=((struct stress *)argument)->type;
    char path[160],a[64],b[64],actual[64];
    CHECK(snprintf(path,sizeof(path),ROOT "sys/%s",names[type])>0);
    number(a,sizeof(a),type,UINT64_C(0xaaaaaaaa55555555),UINT32_C(0xaa55aa55));
    number(b,sizeof(b),type,UINT64_C(0x55555555aaaaaaaa),UINT32_C(0x55aa55aa));
    size_t a_length=strlen(a),b_length=strlen(b);
    for(int round=0;round<256;round++){
        ssize_t n=io(path,false,actual,sizeof(actual));CHECK(n>0);
        CHECK((n==(ssize_t)a_length && memcmp(actual,a,a_length)==0) ||
              (n==(ssize_t)b_length && memcmp(actual,b,b_length)==0));
    }
    return NULL;
}
struct blocked {const char *path;bool writing;char buffer[32];ssize_t result;_Atomic bool started,done;};
static void *blocked(void *argument)
{
    struct blocked *b=argument;atomic_store(&b->started,true);
    if(b->writing)memcpy(b->buffer,"1\n",2);
    b->result=io(b->path,b->writing,b->buffer,b->writing?2:sizeof(b->buffer));
    atomic_store(&b->done,true);return NULL;
}
int main(void)
{
    for(int type=0;type<5;type++){
        char path[160],expected[64];snprintf(path,sizeof(path),ROOT "sys/%s",names[type]);
        number(expected,sizeof(expected),type,UINT64_C(0xf123456789abcde0),UINT32_C(0x89abcde0));value(path,expected);
    }
    value(ROOT "sys/s","snoop(remote)\n");
    value(ROOT "sys/pbl","0,2-3,63-64,69\n");
    value(ROOT "sys/pb","21,80000000,0000000d\n");
    char full[4096],expected_full[4096];size_t offset=0;
    for(int chunk=454;chunk>=0;chunk--){
        unsigned word=chunk==2?0x21u:chunk==1?0x80000000u:chunk==0?13u:0u;
        int n=snprintf(expected_full+offset,sizeof(expected_full)-offset,"%08x%s",word,chunk?",":"\n");
        CHECK(n>0 && n<(int)(sizeof(expected_full)-offset));offset+=(size_t)n;
    }
    CHECK(offset==4095 && io(ROOT "sys/fullmask",false,full,sizeof(full))==4095);
    CHECK(memcmp(full,expected_full,4095)==0);
    char denied[]="x\n";errno=0;
    CHECK(io(ROOT "sys/fullmask",true,denied,2)==-1 && errno==ENOSPC);
    control(ROOT "writer",true);
    for(int n=0;n<10000 && status().writes==0;n++)usleep(1000);
    CHECK(status().writes>0);
    pthread_t threads[5];struct stress arguments[5];
    for(int n=0;n<5;n++){arguments[n].type=n;CHECK(pthread_create(&threads[n],NULL,stress,&arguments[n])==0);}
    for(int n=0;n<5;n++)CHECK(pthread_join(threads[n],NULL)==0);

    control(ROOT "gate",false);
    struct blocked reader={.path=ROOT "sys/slow"},remover={.path=ROOT "remove_slow",.writing=true};
    pthread_t read_thread,remove_thread;
    CHECK(pthread_create(&read_thread,NULL,blocked,&reader)==0);
    for(int n=0;n<10000 && status().phase==0;n++)usleep(1000);
    CHECK(status().phase==1);
    CHECK(pthread_create(&remove_thread,NULL,blocked,&remover)==0);
    for(int n=0;n<10000 && !atomic_load(&remover.started);n++)usleep(1000);
    CHECK(atomic_load(&remover.started));usleep(100000);
    CHECK(!atomic_load(&reader.done) && !atomic_load(&remover.done) && status().reclaimed==0);
    control(ROOT "gate",true);
    CHECK(pthread_join(read_thread,NULL)==0 && pthread_join(remove_thread,NULL)==0);
    CHECK(reader.result==5 && memcmp(reader.buffer,"4242\n",5)==0 && remover.result==2);
    CHECK(status().reclaimed==1);
    char scratch[32];errno=0;
    CHECK(io(ROOT "sys/slow",false,scratch,sizeof(scratch))==-1 && errno==ENOENT);
    control(ROOT "writer",false);
    printf("MCKERNEL_SYSFS_SNOOP_USER_PASS initial_reads=9 full_page=4095 readonly_store=1 scalar_reads=1280 callback_drain=1 mapping_reclaimed=1 writes=%llu\n",status().writes);
    return 0;
}
