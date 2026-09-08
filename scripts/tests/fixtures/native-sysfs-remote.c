/* SPDX-License-Identifier: GPL-2.0-only */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <signal.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define ROOT "/sys/mckernel_sysfs_remote_verify/"
#define CHECK(x) do { if (!(x)) {fprintf(stderr,"REMOTE_USER_FAIL line=%d errno=%d\n",__LINE__,errno);exit(1);} } while (0)
static ssize_t io(const char *path, bool writing, void *buffer, size_t size)
{
    int fd=open(path,writing?O_WRONLY:O_RDONLY);
    if(fd<0)return -1;
    ssize_t result=writing?write(fd,buffer,size):read(fd,buffer,size);
    int error=errno;
    CHECK(close(fd)==0);
    errno=error;
    return result;
}
static void gate(bool open)
{
    char value[2]={open?'1':'0','\n'};
    CHECK(io(ROOT "gate",true,value,2)==2);
}
struct status {unsigned long long phase,released,requests,retries;};
static struct status status(void)
{
    char text[160]={0};struct status s;
    ssize_t n=io(ROOT "status",false,text,sizeof(text)-1);
    CHECK(n>0);
    CHECK(sscanf(text,"%llu %llu %llu %llu",&s.phase,&s.released,&s.requests,&s.retries)==4);
    return s;
}
static void wait_phase(unsigned long long phase)
{
    for(int n=0;n<5000;n++){if(status().phase==phase)return;usleep(1000);}
    CHECK(false);
}
struct stress {int number;};
static void *stress(void *arg)
{
    int number=((struct stress *)arg)->number;char path[160];
    CHECK(snprintf(path,sizeof(path),ROOT "sys/value%d",number)>0);
    for(int round=0;round<64;round++){
        char value[64],actual[64];int length=snprintf(value,sizeof(value),"thread=%d round=%d\n",number,round);
        CHECK(length>0 && length<(int)sizeof(value));
        CHECK(io(path,true,value,(size_t)length)==length);
        CHECK(io(path,false,actual,sizeof(actual))==length);
        CHECK(memcmp(actual,value,(size_t)length)==0);
    }
    return NULL;
}
struct blocked {
    const char *path;bool writing;
    char buffer[128];ssize_t result;int error;
    _Atomic bool started,done;
};
static void *blocked(void *arg)
{
    struct blocked *b=arg;
    atomic_store(&b->started,true);
    if(b->writing)memcpy(b->buffer,"1\n",2);
    b->result=io(b->path,b->writing,b->buffer,b->writing?2:sizeof(b->buffer));b->error=errno;
    atomic_store(&b->done,true);
    return NULL;
}
static void wait_started(struct blocked *b)
{
    for(int n=0;n<5000;n++){if(atomic_load(&b->started))return;usleep(1000);}
    CHECK(false);
}
static void signal_handler(int signal){(void)signal;}

int main(void)
{
    for(int n=1;n<=4;n++){
        char path[160],value[32];snprintf(path,sizeof(path),ROOT "sys/value%d",n);
        CHECK(io(path,false,value,sizeof(value))==8);CHECK(memcmp(value,"initial\n",8)==0);
    }
    pthread_t threads[4];struct stress args[4];
    for(int n=0;n<4;n++){args[n].number=n+1;CHECK(pthread_create(&threads[n],NULL,stress,&args[n])==0);}
    for(int n=0;n<4;n++)CHECK(pthread_join(threads[n],NULL)==0);
    char page[4096];
    CHECK(io(ROOT "sys/boundary",false,page,sizeof(page))==4095);
    for(int n=0;n<4095;n++)CHECK(page[n]=='z');
    memset(page,'k',sizeof(page));CHECK(io(ROOT "sys/boundary",true,page,sizeof(page))==4096);
    errno=0;CHECK(io(ROOT "sys/overflow",false,page,sizeof(page))==-1 && errno==EOVERFLOW);
    errno=0;CHECK(io(ROOT "sys/overflow",true,page,4)==-1 && errno==EOVERFLOW);
    errno=0;CHECK(io(ROOT "sys/error",false,page,sizeof(page))==-1 && errno==EINVAL);
    errno=0;CHECK(io(ROOT "sys/error",true,page,4)==-1 && errno==EINVAL);

    struct sigaction action={.sa_handler=signal_handler};sigemptyset(&action.sa_mask);
    CHECK(sigaction(SIGUSR1,&action,NULL)==0);
    gate(false);
    struct blocked interrupted={.path=ROOT "sys/interrupt"};pthread_t interrupted_thread;
    CHECK(pthread_create(&interrupted_thread,NULL,blocked,&interrupted)==0);wait_phase(8);
    CHECK(pthread_kill(interrupted_thread,SIGUSR1)==0);CHECK(pthread_join(interrupted_thread,NULL)==0);
    CHECK(interrupted.result==-1 && interrupted.error==EINTR);
    struct blocked following={.path=ROOT "sys/value1"};pthread_t following_thread;
    CHECK(pthread_create(&following_thread,NULL,blocked,&following)==0);wait_started(&following);usleep(100000);
    CHECK(!atomic_load(&following.done));CHECK(status().phase==8);
    gate(true);CHECK(pthread_join(following_thread,NULL)==0);
    const char expected[]="thread=1 round=63\n";
    CHECK(following.result==(ssize_t)sizeof(expected)-1 && memcmp(following.buffer,expected,sizeof(expected)-1)==0);

    gate(false);
    struct blocked reader={.path=ROOT "sys/slow"},remover={.path=ROOT "remove_slow",.writing=true};
    pthread_t reader_thread,remover_thread;
    CHECK(pthread_create(&reader_thread,NULL,blocked,&reader)==0);wait_phase(7);
    CHECK(pthread_create(&remover_thread,NULL,blocked,&remover)==0);wait_started(&remover);usleep(100000);
    CHECK(!atomic_load(&reader.done) && !atomic_load(&remover.done));CHECK((status().released&(1ULL<<7))==0);
    gate(true);CHECK(pthread_join(reader_thread,NULL)==0);CHECK(pthread_join(remover_thread,NULL)==0);
    CHECK(reader.result==5 && memcmp(reader.buffer,"slow\n",5)==0);CHECK(remover.result==2);
    CHECK((status().released&(1ULL<<7))!=0);
    errno=0;CHECK(io(ROOT "sys/slow",false,page,sizeof(page))==-1 && errno==ENOENT);
    struct status s=status();CHECK(s.requests==526 && s.retries==526 && s.released==(1ULL<<7));
    printf("MCKERNEL_SYSFS_REMOTE_USER_PASS parallel_roundtrips=256 requests=%llu retries=%llu interrupted=1 late_response=1 callback_drain=1 release_drain=1 boundaries=2 errors=4\n",s.requests,s.retries);
    return 0;
}
