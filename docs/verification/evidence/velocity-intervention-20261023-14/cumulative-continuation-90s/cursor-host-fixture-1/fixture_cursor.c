/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * PRIVATE HOST FIXTURE SOURCE ONLY. Actual filesystem identity checks; no guest.
 * 7 cases compare original66ad member with frozen candidate and preserve data. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
static unsigned pair_active_round;
static int pair_seen_pids[4096];
static struct { int pid; } pair_results[2];
static char pair_evidence_dir[PATH_MAX];
#define PAIR_LOG_LIMIT 1048576
struct pair_assignment { unsigned long generation; };
static int pair_routes(const char *p,size_t n,const struct pair_assignment *a,unsigned long *g)
{ (void)p;(void)n;(void)a;(void)g;return -1; }
static int save_file(const char *p,const char *data,size_t bytes)
{ int fd=open(p,O_CREAT|O_EXCL|O_WRONLY|O_NOFOLLOW|O_CLOEXEC,0600);if(fd<0)return -1;ssize_t n=write(fd,data,bytes);int bad=n!=(ssize_t)bytes;if(close(fd))bad=1;return bad?-1:0; }
static size_t scans;
static void *fixture_memchr(const void *p,int c,size_t n) { scans++;return memchr(p,c,n); }
#define memchr fixture_memchr
#include "long_trace_retention.inc"
static int pair_trace_member_original(const char *line,size_t length,int pid,size_t *cursor)
{
    for(unsigned round=0;round<pair_active_round && round<2048;round++) {
        struct pair_trace_record *r=&pair_trace_records[round];struct stat current;
        if(pid>0 && pid!=r->pids[0] && pid!=r->pids[1])continue;
        if(!r->bytes || long_trace_stat(r,&current) || !pair_trace_same(&r->identity,&current))return -1;
        size_t off=r->offset,end=r->offset+r->bytes;
        while(off<end) {
            const char *lf=memchr(pair_trace_authenticated+off,'\n',end-off);if(!lf)return -1;
            size_t count=(size_t)(lf-(pair_trace_authenticated+off))+1;
            if(off>=*cursor && count==length && !memcmp(pair_trace_authenticated+off,line,length)){*cursor=off+count;return 1;}
            off+=count;
        }
    }
    return 0;
}

#undef memchr
static unsigned serial_case;
static char fixture_root[PATH_MAX];
static void fresh(void)
{
 char dir[PATH_MAX];int n=snprintf(dir,sizeof dir,"%s/case%u",fixture_root,++serial_case);assert(n>0 && (size_t)n<sizeof dir);assert(!mkdir(dir,0700));strcpy(pair_evidence_dir,dir);
 memset(pair_trace_records,0,sizeof pair_trace_records);pair_trace_total=0;pair_active_round=0;scans=0;
}
static void record_at(unsigned i,const char *data,int p0,int p1)
{
 struct pair_trace_record *r=&pair_trace_records[i];int n=snprintf(r->path,sizeof r->path,"%s/r%u",pair_evidence_dir,i);assert(n>0 && (size_t)n<sizeof r->path);r->bytes=strlen(data);r->offset=pair_trace_total;r->pids[0]=p0;r->pids[1]=p1;assert(!save_file(r->path,data,r->bytes));assert(!stat(r->path,&r->identity));memcpy(pair_trace_authenticated+r->offset,data,r->bytes);pair_trace_total+=r->bytes;pair_active_round=i+1;
}
static int same_query(const char *line,int pid,size_t *cursor)
{
 size_t a=*cursor,b=*cursor;int x=pair_trace_member_original(line,strlen(line),pid,&a),y=pair_trace_member(line,strlen(line),pid,&b);assert(x==y && a==b);*cursor=b;return y;
}
static void ordered(void)
{ fresh();record_at(0,"a\nb\nc\n",10,11);size_t c=0;assert(same_query("a\n",10,&c)==1);assert(same_query("c\n",10,&c)==1);assert(same_query("b\n",10,&c)==0); }
static void boundaries(void)
{ fresh();record_at(0,"a\nb\n",10,11);record_at(1,"a\nc\n",20,21);size_t cs[]={0,2,4,6,8};for(unsigned i=0;i<sizeof cs/sizeof *cs;i++){size_t c=cs[i];(void)same_query("a\n",0,&c);} }
static void skipped_identity(void)
{ fresh();record_at(0,"a\n",10,11);record_at(1,"b\n",20,21);char old[PATH_MAX];assert(snprintf(old,sizeof old,"%s.old",pair_trace_records[0].path)>0);assert(!rename(pair_trace_records[0].path,old));size_t c=2;assert(same_query("b\n",0,&c)==-1); }
static void hardlink_identity(void)
{ fresh();record_at(0,"a\n",10,11);char linked[PATH_MAX];assert(snprintf(linked,sizeof linked,"%s.link",pair_trace_records[0].path)>0);assert(!link(pair_trace_records[0].path,linked));size_t c=0;assert(same_query("a\n",10,&c)==-1); }
static void pid_filter(void)
{ fresh();record_at(0,"same\n",10,11);record_at(1,"same\n",20,21);size_t c=0;assert(same_query("same\n",20,&c)==1 && c==10);c=0;assert(same_query("same\n",99,&c)==0); }
static void repeated_text_and_order(void)
{ fresh();record_at(0,"a\na\nb\n",10,11);size_t c=0;assert(same_query("a\n",10,&c)==1 && c==2);assert(same_query("a\n",10,&c)==1 && c==4);assert(same_query("b\n",10,&c)==1 && c==6);assert(same_query("a\n",10,&c)==0); }
static void operation_count(void)
{
 fresh();enum { N=1024 };static char data[N*16];size_t used=0;for(unsigned i=0;i<N;i++){int n=snprintf(data+used,sizeof data-used,"line%04u\n",i);assert(n>0);used+=(size_t)n;}record_at(0,data,10,11);
 size_t a=0,b=0;scans=0;for(unsigned i=0;i<N;i++){char line[16];assert(snprintf(line,sizeof line,"line%04u\n",i)>0);assert(pair_trace_member_original(line,strlen(line),10,&a)==1);}size_t original=scans;
 scans=0;for(unsigned i=0;i<N;i++){char line[16];assert(snprintf(line,sizeof line,"line%04u\n",i)>0);assert(pair_trace_member(line,strlen(line),10,&b)==1);}assert(a==b && a==used);assert(original==(size_t)N*(N+1)/2 && scans==N);printf("cursor scans original=%zu candidate=%zu\n",original,scans);
}
int main(int argc,char **argv)
{
 assert(argc==2);int n=snprintf(fixture_root,sizeof fixture_root,"%s.XXXXXX",argv[1]);assert(n>0 && (size_t)n<sizeof fixture_root && mkdtemp(fixture_root));
 ordered();boundaries();skipped_identity();hardlink_identity();pid_filter();repeated_text_and_order();operation_count();printf("HOST cursor7cases PASS data=%s\n",fixture_root);return 0;
}
