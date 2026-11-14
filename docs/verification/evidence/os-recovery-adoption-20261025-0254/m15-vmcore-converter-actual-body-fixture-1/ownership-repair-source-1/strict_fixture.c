/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Test effect leaves for the unchanged full Rust cmd_ldump2mcdump body.
 * This file has no converter state machine; command flow comes from that object.
 */
#define _GNU_SOURCE
#include <assert.h>
#include <stdbool.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <pwd.h>
#include <time.h>
#include <unistd.h>
#include "dump-layout.h"

/* Exact C view of candidate's existing repr(C) CommandTableEntry/ASection and
 * MachdepTable declarations. Opaque Bfd/File/Tm are supplied by these callbacks. */
struct command_entry { char *name; void (*func)(void); char **help; unsigned long flags; };
struct section { const char *name; unsigned id,index; struct section *next,*prev; unsigned flags,bitfields; unsigned long vma,lma,size; };
struct machdep_table { unsigned long flags,kvbase; };
_Static_assert(sizeof(struct ihk_dump_page)==16,"page ABI");
_Static_assert(sizeof(struct ihk_dump_page_set)==24,"set ABI");
_Static_assert(sizeof(dump_mem_chunks_t)==24,"chunks header ABI");
_Static_assert(sizeof(struct dump_mem_chunk)==16,"chunk ABI");
_Static_assert(offsetof(struct section,vma)==40 && sizeof(struct section)==64,"candidate section prefix ABI");

int argcnt=4;
char *args[100];
FILE *fp;
static struct machdep_table md={0,0x100000000UL};
struct machdep_table *machdep=&md;
extern void cmd_ldump2mcdump(void);
static void (*registered)(void);
static char output_path[]="/fixture/exact path.mcdump";
static char user_name[]="fixture-user";
static struct passwd user={.pw_name=user_name};
static struct tm tm_storage;
static char date[]="FIXTURE DATE\n";
static void *owned_handle;
static int handle_live,handles_opened,handles_destroyed,abort_closes,name_checks,last_bfd_event;
static int fail_open,fail_format,fail_time,fail_localtime,fail_make,fail_size,fail_flags,fail_get_phys,fail_abort;
static int make_calls,size_calls,flag_calls;
static char primary_bfd_error[128],primary_perror[128];
static struct section sections[10];
static int nsections,getopt_calls,read_calls,phys_reads,phys_writes,writes,closes,acks,flushes,event,ack_event,close_event,payload_free_event,chunks_free_event;
static int fail_meta,fail_phys,fail_write,fail_close,fail_alloc,missing_physchunks;
static int diagnostic_reads,unexpected_read,bfd_errors;
static char diagnostics[4096],ack_line[8192];
static size_t diagnostic_length;
static unsigned phys_read_mask,phys_write_mask;
struct allocation {void *ptr; size_t size; int live,freed;};
static struct allocation allocations[32];
static int nalloc,alloc_attempts;

void *__real_malloc(size_t);
void __real_free(void *);
void *__wrap_malloc(size_t n) {
    ++event;++alloc_attempts;
    if(fail_alloc==alloc_attempts)return NULL;
    assert(nalloc<32);
    void *p=__real_malloc(n?n:1);assert(p);
    allocations[nalloc++]=(struct allocation){p,n,1,0};return p;
}
void *__wrap_calloc(size_t n,size_t size) {
    assert(size==0||n<=SIZE_MAX/size);size_t bytes=n*size;void *p=__wrap_malloc(bytes);if(p)memset(p,0,bytes);return p;
}
void __wrap_free(void *p) {
    ++event;
    for(int i=0;i<nalloc;i++)if(allocations[i].ptr==p&&allocations[i].live){
        if(allocations[i].size==40||allocations[i].size==72||allocations[i].size==0x100000)assert(!handle_live);
        allocations[i].live=0;allocations[i].freed=1;
        if(allocations[i].size==0x100000)payload_free_event=event;
        if(allocations[i].size==72)chunks_free_event=event;
        __real_free(p);return;
    }
    assert(!"free of unknown/already freed callback allocation");
}
int __wrap_fprintf(FILE *stream,const char *format,...) {
    (void)stream;++event;
    va_list ap;va_start(ap,format);char text[8192];int n=vsnprintf(text,sizeof(text),format,ap);va_end(ap);assert(n>=0&&(size_t)n<sizeof(text));
    if(!strcmp(format,"MCKERNEL_LDUMP2MCDUMP_SUCCESS %s\n")){
        ++acks;ack_event=event;assert(n<(int)sizeof(ack_line));memcpy(ack_line,text,n+1);
    }else{
        assert(diagnostic_length+(size_t)n<sizeof(diagnostics));memcpy(diagnostics+diagnostic_length,text,n+1);diagnostic_length+=n;
        if(!strcmp(format,"readmem error(%d)\n"))++diagnostic_reads;
    }
    return n;
}
size_t __wrap_fwrite(const void *ptr,size_t size,size_t count,FILE *stream){
    (void)stream;++event;size_t n=size*count;assert(diagnostic_length+n<sizeof(diagnostics));memcpy(diagnostics+diagnostic_length,ptr,n);diagnostic_length+=n;diagnostics[diagnostic_length]=0;return count;
}
int __wrap_fflush(FILE *stream){assert(stream==fp);++flushes;++event;assert(acks==1&&event>ack_event);return 0;}
int __wrap_getopt(int argc,char *const argv[],const char *spec){
    assert(argc==4&&!strcmp(spec,"o:")&&!strcmp(argv[1],"0"));
    if(getopt_calls++==0){optarg=output_path;return 'o';}return -1;
}
int __wrap_gethostname(char *name,size_t n){assert(n>=13);strcpy(name,"fixture-host");return 0;}
uid_t __wrap_getuid(void){return 1000;}
struct passwd *__wrap_getpwuid(uid_t uid){assert(uid==1000);return &user;}
time_t __wrap_time(time_t *out){assert(!out);return fail_time?-1:12345;}
struct tm *__wrap_localtime(const time_t *t){assert(*t==12345);return fail_localtime?NULL:&tm_storage;}
char *__wrap_asctime(const struct tm *t){assert(t==&tm_storage);return date;}
void __wrap_perror(const char *s){++event;assert(s&&strlen(s)<sizeof(primary_perror));strcpy(primary_perror,s);}
void register_extension(struct command_entry *table){
    assert(!strcmp(table[0].name,"ldump2mcdump")&&table[0].func==cmd_ldump2mcdump&&table[1].name==NULL);registered=table[0].func;
}
unsigned long symbol_value(char *s){
    if(!strcmp(s,"dump_page_set_addr"))return 0x1000;
    assert(!strcmp(s,"dump_bootstrap_mem_start"));return 0x1100;
}
int readmem(unsigned long long addr,int type,void *buf,long size,char *message,unsigned long flags){
    ++event;++read_calls;assert(type==1&&message[0]==0&&size>=0);
    int meta=0;
    if(addr==0x1000)meta=1;
    else if(addr==0x2000)meta=2;
    else if(addr==md.kvbase+0x3000)meta=read_calls==3?3:5;
    else if(addr==md.kvbase+0x3010)meta=read_calls==4?4:6;
    else if(addr==0x1100)meta=7;
    if(meta){
        assert(read_calls==meta&&flags==1);
        /* FALSE returns without initializing the supplied bytes. Any downstream
         * callback or unexpected read after metadata failure fails the case. */
        if(fail_meta==meta)return 0;
        if(meta==1){unsigned long v=0x2000;assert(size==8);memcpy(buf,&v,8);}
        else if(meta==2){struct ihk_dump_page_set v={1,1,4096,0x3000};assert(size==sizeof(v));memcpy(buf,&v,sizeof(v));}
        else if(meta==3||meta==5){struct ihk_dump_page v={.start=0x800000,.map_count=1};assert(size==sizeof(v));memcpy(buf,&v,sizeof(v));}
        else if(meta==4||meta==6){unsigned long v=0x15;assert(size==8);memcpy(buf,&v,8);}
        else {unsigned long v=0x1000000;assert(size==8);memcpy(buf,&v,8);}
        return 1;
    }
    assert(flags==3&&size==4096);
    unsigned long offset=addr-md.kvbase-0x800000;
    if(offset%8192||offset/8192>=3){++unexpected_read;return 0;}
    int index=(int)(offset/8192);++phys_reads;phys_read_mask|=1U<<index;
    if(fail_phys==index+1)return 0;
    memset(buf,0x31+index,(size_t)size);return 1;
}
static void validate_borrowed_names(void){
    for(int j=0;j<nsections;j++){
        const char *name=sections[j].name;
        if(j<4){assert(!strcmp(name,(const char*[]){"date","hostname","user","physchunks"}[j]));continue;}
        int owner_live=0;
        for(int i=0;i<nalloc;i++)if(allocations[i].live&&(uintptr_t)name>=(uintptr_t)allocations[i].ptr&&(uintptr_t)name<(uintptr_t)allocations[i].ptr+allocations[i].size)owner_live=1;
        assert(owner_live);char expected[32];snprintf(expected,sizeof(expected),"physmem%d",j-4);assert(!strcmp(name,expected));++name_checks;
    }
}
static void check_handle(void *bfd){assert(handle_live&&bfd==owned_handle);validate_borrowed_names();last_bfd_event=event;}
void bfd_init(void){++event;}
void *bfd_fopen(const char *filename,const char *target,const char *mode,int fd){
    ++event;assert(!strcmp(filename,output_path)&&target==NULL&&!strcmp(mode,"w")&&fd==-1);
    if(fail_open)return NULL;
    assert(!handle_live);owned_handle=__real_malloc(8);assert(owned_handle);handle_live=1;++handles_opened;return owned_handle;
}
void bfd_perror(const char *s){++event;++bfd_errors;assert(s&&strlen(s)<sizeof(primary_bfd_error));strcpy(primary_bfd_error,s);}
int bfd_set_format(void *bfd,int format){++event;check_handle(bfd);assert(format==1);return !fail_format;}
struct section *bfd_make_section_anyway(void *bfd,const char *name){
    ++event;check_handle(bfd);++make_calls;if(fail_make==make_calls)return NULL;
    assert(nsections<10);struct section *s=&sections[nsections++];s->name=name;validate_borrowed_names();return s;
}
int bfd_set_section_size(void *bfd,struct section *s,unsigned long size){++event;check_handle(bfd);if(fail_size==++size_calls)return 0;s->size=size;return 1;}
int bfd_set_section_flags(void *bfd,struct section *s,unsigned flags){++event;check_handle(bfd);if(fail_flags==++flag_calls)return 0;s->flags=flags;return 1;}
struct section *bfd_get_section_by_name(void *bfd,const char *name){
    ++event;check_handle(bfd);
    if(missing_physchunks&&!strcmp(name,"physchunks"))return NULL;
    if(!strncmp(name,"physmem",7)&&fail_get_phys==atoi(name+7)+1)return NULL;
    for(int i=0;i<nsections;i++)if(!strcmp(name,sections[i].name))return &sections[i];
    assert(!"unexpected section lookup");return NULL;
}
int bfd_set_section_contents(void *bfd,struct section *s,const void *data,long offset,unsigned long count){
    ++event;check_handle(bfd);assert(data&&offset==0);++writes;
    if(fail_write==writes)return 0;
    if(!strcmp(s->name,"date")){assert(count==strlen(date)-1&&!memcmp(data,date,count));}
    else if(!strcmp(s->name,"hostname")){assert(count==12&&!memcmp(data,"fixture-host",12));}
    else if(!strcmp(s->name,"user")){assert(count==12&&!memcmp(data,"fixture-user",12));}
    else if(!strcmp(s->name,"physchunks")){
        assert(count==72&&s->size==72&&s->flags==0x101);
        const dump_mem_chunks_t *m=data;assert(m->nr_chunks==3&&m->kernel_base==0x1200000&&m->phys_start==0);
        for(int i=0;i<3;i++)assert(m->chunks[i].addr==0x800000UL+8192UL*i&&m->chunks[i].size==4096);
    }else{
        assert(!strncmp(s->name,"physmem",7));int i=atoi(s->name+7);assert(i>=0&&i<3&&count==4096&&s->size==4096&&s->vma==0x800000UL+8192UL*i&&s->lma==s->vma&&(s->bitfields&1)&&s->flags==0x101);
        const unsigned char *p=data;for(unsigned j=0;j<count;j++)assert(p[j]==0x31+i);
        ++phys_writes;phys_write_mask|=1U<<i;
    }
    return 1;
}
static void consume_handle(void *bfd){check_handle(bfd);__real_free(owned_handle);owned_handle=NULL;handle_live=0;++handles_destroyed;}
int bfd_close(void *bfd){++event;++closes;close_event=event;consume_handle(bfd);return !fail_close;}
bool bfd_close_all_done(void *bfd){++event;++abort_closes;consume_handle(bfd);return !fail_abort;}

int main(int argc,char **argv){
    assert(argc==3&&registered==cmd_ldump2mcdump);
    const char *kind=argv[1];int position=atoi(argv[2]);
    if(!strcmp(kind,"metadata"))fail_meta=position;
    else if(!strcmp(kind,"physical"))fail_phys=position;
    else if(!strcmp(kind,"write"))fail_write=position;
    else if(!strcmp(kind,"close"))fail_close=1;
    else if(!strcmp(kind,"physchunks-null"))missing_physchunks=1;
    else if(!strcmp(kind,"allocation"))fail_alloc=position;
    else if(!strcmp(kind,"open"))fail_open=1;
    else if(!strcmp(kind,"format"))fail_format=1;
    else if(!strcmp(kind,"time"))fail_time=1;
    else if(!strcmp(kind,"localtime"))fail_localtime=1;
    else if(!strcmp(kind,"make"))fail_make=position;
    else if(!strcmp(kind,"size"))fail_size=position;
    else if(!strcmp(kind,"flags"))fail_flags=position;
    else if(!strcmp(kind,"get-phys"))fail_get_phys=position;
    else if(!strcmp(kind,"abort-false")){fail_format=1;fail_abort=1;}
    else assert(!strcmp(kind,"success"));
    args[0]="ldump2mcdump";args[1]="0";args[2]="-o";args[3]=output_path;fp=stdout;
    registered();
    int live=0,live_bytes=0,map_freed=0,map_live=0;
    for(int i=0;i<nalloc;i++){if(allocations[i].live){live++;live_bytes+=(int)allocations[i].size;}if(allocations[i].size==8){map_freed+=allocations[i].freed;map_live+=allocations[i].live;}}
    int ack_expected=EXPECT_ACK&&!strcmp(kind,"success");assert(acks==ack_expected&&flushes==ack_expected&&!unexpected_read);
    if(acks){char expected[8192];snprintf(expected,sizeof(expected),"MCKERNEL_LDUMP2MCDUMP_SUCCESS %s\n",output_path);assert(!strcmp(ack_line,expected));assert(close_event>0&&close_event<payload_free_event&&payload_free_event<chunks_free_event&&chunks_free_event<ack_event&&name_checks>0);}
    if(!strcmp(kind,"metadata")){assert(read_calls==position&&!phys_reads&&!writes&&!closes);assert(map_live==0);if(position==4)assert(map_freed==1);if(position==6)assert(map_freed==2);}
    if(!strcmp(kind,"physical")){assert(read_calls==10&&phys_reads==3&&phys_read_mask==7&&phys_writes==2&&phys_write_mask==(7U^(1U<<(position-1)))&&diagnostic_reads==1&&closes==1);assert(!strcmp(diagnostics,"readmem error(0)\n"));}
    if(!strcmp(kind,"success")){assert(read_calls==10&&writes==7&&phys_writes==3&&closes==1&&map_freed==2);}
    if(!strcmp(kind,"write")){assert(writes==position&&bfd_errors==1&&!closes);}
    if(!strcmp(kind,"close")){assert(closes==1&&bfd_errors==1&&payload_free_event>close_event&&chunks_free_event>payload_free_event&&!abort_closes);}
    if(!strcmp(kind,"physchunks-null")){assert(phys_reads==3&&phys_writes==3&&writes==6&&closes==1);}
    assert(live==0&&live_bytes==0&&!handle_live&&handles_opened==handles_destroyed);
    assert(closes+abort_closes==handles_opened);
    if(!strcmp(kind,"write"))assert(abort_closes==1);
    if(!strcmp(kind,"open"))assert(!handles_opened&&!closes&&!abort_closes&&!strcmp(primary_bfd_error,"bfd_fopen"));
    if(!strcmp(kind,"format")||!strcmp(kind,"abort-false"))assert(abort_closes==1&&!strcmp(primary_bfd_error,"bfd_set_format"));
    if(!strcmp(kind,"time"))assert(abort_closes==1&&!strcmp(primary_perror,"time"));
    if(!strcmp(kind,"localtime"))assert(abort_closes==1&&!strcmp(primary_perror,"localtime"));
    if(!strcmp(kind,"make")){const char *names[]={"date","hostname","user","physchunks","physmem","physmem","physmem"};char expected[128];snprintf(expected,sizeof(expected),"bfd_make_section_anyway(%s)",names[position-1]);assert(abort_closes==1&&!strcmp(primary_bfd_error,expected));}
    if(!strcmp(kind,"size"))assert(abort_closes==1&&!strcmp(primary_bfd_error,"bfd_set_section_size"));
    if(!strcmp(kind,"flags"))assert(abort_closes==1&&!strcmp(primary_bfd_error,"bfd_set_setction_flags"));
    if(!strcmp(kind,"get-phys"))assert(abort_closes==1&&!strcmp(primary_bfd_error,"err bfd_get_section_by_name(physmem_name)"));
    printf("STRICT_OWNERSHIP handles=%d destroyed=%d normal_close=%d abort_close=%d name_checks=%d last_bfd_event=%d live_project=%d\n",handles_opened,handles_destroyed,closes,abort_closes,name_checks,last_bfd_event,live);
    printf("{\"kind\":\"%s\",\"position\":%d,\"ack\":%d,\"flushes\":%d,\"read_calls\":%d,\"physical_reads\":%d,\"physical_writes\":%d,\"physical_read_mask\":%u,\"physical_write_mask\":%u,\"writes\":%d,\"closes\":%d,\"read_diagnostics\":%d,\"bfd_errors\":%d,\"alloc_attempts\":%d,\"allocations\":%d,\"map_buffers_freed\":%d,\"map_buffers_live\":%d,\"live_allocations\":%d,\"live_bytes\":%d,\"close_event\":%d,\"payload_free_event\":%d,\"chunks_free_event\":%d,\"ack_event\":%d,\"ownership_complete\":%s}\n",kind,position,acks,flushes,read_calls,phys_reads,phys_writes,phys_read_mask,phys_write_mask,writes,closes,diagnostic_reads,bfd_errors,alloc_attempts,nalloc,map_freed,map_live,live,live_bytes,close_event,payload_free_event,chunks_free_event,ack_event,live?"false":"true");
    return 0;
}
