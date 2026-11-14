/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * PRIVATE, UNCOMPILED source. One closed case per separately admitted operation.
 * Root must bind the NEW qualified balanced DSO, its libc/provider graph, an
 * exclusive empty GLOBAL reservation baseline and a genuinely bounded ALL ratio.
 * This program is not an admission/permission mechanism or a physical-restoration oracle.
 * Rejected worker01a1c48d-4d96-7cc3-b733-73a97973152f /
 * turn01a1ce01-20cf-7e03-9442-f6d521fb8b02 collector/equivalents remain excluded.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <limits.h>
#include <stdarg.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <unistd.h>
#include <ihk/ihklib.h>
#include <ihk/ihklib_private.h>

#define NEW_DSO "/input/libihk-balanced.so"
#define MAX_ROWS 2048
#define MAX_IO 32
#define MAX_ALLOC 64
#define MAX_CLOSE 64
#define MIB 1048576UL

_Static_assert(sizeof(unsigned long)==8 && sizeof(void *)==8, "selected LP64 ABI");
_Static_assert(sizeof(struct ihk_mem_chunk)==16 && offsetof(struct ihk_mem_chunk,numa_node_number)==8, "qualified chunk ABI");
_Static_assert(sizeof(struct ihk_mem_req)==32 && offsetof(struct ihk_mem_req,num_chunks)==16, "qualified request ABI");
_Static_assert(sizeof(struct ihklib_reserve_mem_conf)==24 && offsetof(struct ihklib_reserve_mem_conf,timeout)==20, "qualified config ABI");

enum phase { OFF, BASELINE, SETTERS, RESERVE, POST, CLEANUP, AFTER };
struct snapshot {
 int n,min,ratio,timeout,arrays;
 uintptr_t sizes_ptr,nodes_ptr;
 unsigned long sizes[MAX_ROWS]; int nodes[MAX_ROWS];
};
struct io_row {
 unsigned long seq,op; enum phase phase; int fd,ret,error,identity_ok;
 unsigned long long dev,ino,rdev;
 struct snapshot before,after;
 struct ihklib_reserve_mem_conf config_before;
};
struct allocation { unsigned long seq,free_seq; enum phase phase; size_t n,size; uintptr_t ptr; int error; };
struct close_row { unsigned long seq; enum phase phase; int fd,ret,error,identity_ok; unsigned long long dev,ino,rdev; };
static struct io_row ios[MAX_IO];
static struct allocation allocs[MAX_ALLOC];
static struct close_row closes[MAX_CLOSE];
static unsigned nio,nalloc,nclose; static unsigned long sequence;
static enum phase phase; static int trace_bad;
static void *(*real_calloc)(size_t,size_t);
static void (*real_free)(void *);
static int (*real_close)(int);
static int (*real_ioctl)(int,unsigned long,...);
static struct ihklib_reserve_mem_conf *configuration;

/* Unbound bootstrap/overflow never produces a synthetic successful backend row.
 * An unbound callback exits the owned process; Root retains any unproved family.
 * Actual libc symbol/version/bootstrap correctness remains a changed-caller proof.
 */
static void unbound(void) { _exit(119); }
void *calloc(size_t n,size_t size)
{
 if (!real_calloc) unbound();
 void *p=real_calloc(n,size); int error=errno;
 if (phase!=OFF) {
  if (nalloc==MAX_ALLOC) trace_bad=1;
  else allocs[nalloc++]=(struct allocation){++sequence,0,phase,n,size,(uintptr_t)p,error};
 }
 errno=error; return p;
}
void free(void *p)
{
 if (!real_free) unbound();
 uintptr_t address=(uintptr_t)p;
 real_free(p); int error=errno;
 if (phase!=OFF && address) {
  unsigned i=nalloc;
  while (i) { --i; if (allocs[i].ptr==address && !allocs[i].free_seq) { allocs[i].free_seq=++sequence; break; } }
 }
 errno=error;
}
static int fd_identity(int fd,unsigned long long *dev,unsigned long long *ino,unsigned long long *rdev)
{
 struct stat s;
 if (fstat(fd,&s)!=0) return 0;
 *dev=(unsigned long long)s.st_dev; *ino=(unsigned long long)s.st_ino; *rdev=(unsigned long long)s.st_rdev;
 return S_ISCHR(s.st_mode);
}
int close(int fd)
{
 if (!real_close) unbound();
 struct close_row row={0}; int entry=errno;
 if (phase!=OFF) {
  row.seq=++sequence;row.phase=phase;row.fd=fd;
  row.identity_ok=fd>=0 && fd_identity(fd,&row.dev,&row.ino,&row.rdev);
 }
 errno=entry; int ret=real_close(fd); int error=errno;
 if (phase!=OFF) {
  row.ret=ret;row.error=error;
  if (nclose==MAX_CLOSE) trace_bad=1; else closes[nclose++]=row;
 }
 errno=error; return ret;
}
static void snapshot(struct snapshot *out,const struct ihk_mem_req *r)
{
 out->n=r->num_chunks;out->min=r->min_chunk_size;out->ratio=r->max_size_ratio_all;out->timeout=r->timeout;
 out->sizes_ptr=(uintptr_t)r->sizes;out->nodes_ptr=(uintptr_t)r->numa_ids;
 if (r->num_chunks<0 || r->num_chunks>MAX_ROWS) { trace_bad=1; return; }
 if (r->num_chunks && r->sizes && r->numa_ids) {
  out->arrays=1;
  for (int i=0;i<r->num_chunks;++i) { out->sizes[i]=(unsigned long)r->sizes[i];out->nodes[i]=r->numa_ids[i]; }
 }
}
int ioctl(int fd,unsigned long op,...)
{
 if (!real_ioctl) unbound();
 va_list ap;va_start(ap,op);void *arg=va_arg(ap,void *);va_end(ap);
 struct io_row *row=NULL;int entry=errno;
 if (phase!=OFF) {
  if (nio==MAX_IO) trace_bad=1;
  else {
   row=&ios[nio++];row->seq=++sequence;row->phase=phase;row->fd=fd;row->op=op;
   row->identity_ok=fd_identity(fd,&row->dev,&row->ino,&row->rdev);
   if (configuration) row->config_before=*configuration;
   if (arg && (op==IHK_DEVICE_RESERVE_MEM || op==IHK_DEVICE_QUERY_MEM || op==IHK_DEVICE_RELEASE_MEM || op==IHK_DEVICE_RELEASE_MEM_PARTIALLY)) snapshot(&row->before,arg);
   else trace_bad=1;
  }
 }
 errno=entry;int ret=real_ioctl(fd,op,arg);int error=errno;
 if (row) { row->ret=ret;row->error=error; if (ret==0) snapshot(&row->after,arg); }
 errno=error;return ret;
}

struct operand_case { const char *name;int count,best,variance,expected;unsigned long requested[3],R[3],partial[3]; };
static const struct operand_case cases[]={
 {"equal-capacity-zero-first-and-second-donor-counts",2,0,0,0,{8*MIB,8*MIB,0},{8*MIB,8*MIB,0},{0,0,0}},
 {"positive-first-donors-zero-second-donors-with-positive-M2",3,0,75,0,{4*MIB,4*MIB,4*MIB},{MIB,5*MIB,6*MIB},{0,0,0}},
 {"no-active-capacity-nodes-best-effort",1,1,0,-ENOMEM,{8*MIB,0,0},{0,0,0},{0,0,0}},
 {"positive-divisor-distribution-and-real-partial-release",2,0,50,0,{8*MIB,8*MIB,0},{4*MIB,20*MIB,0},{0,8*MIB,0}}
};
static int conf_default(const struct ihklib_reserve_mem_conf *c)
{ return c->balanced_enable==0 && c->balanced_best_effort==0 && c->balanced_variance_limit==0 && c->min_chunk_size==4096 && c->max_size_ratio_all==98 && c->timeout==30; }
static int conf_matches(const struct ihklib_reserve_mem_conf *c,const int *v)
{ return c->balanced_enable==v[0] && c->balanced_best_effort==v[1] && c->balanced_variance_limit==v[2] && c->min_chunk_size==v[3] && c->max_size_ratio_all==v[4] && c->timeout==v[5]; }
static int origin(void *symbol,const struct stat *expected)
{
 Dl_info d;struct stat s;
 return dladdr(symbol,&d) && d.dli_fname && stat(d.dli_fname,&s)==0 && S_ISREG(s.st_mode) && s.st_dev==expected->st_dev && s.st_ino==expected->st_ino;
}
static int decimal(const char *s,int maximum,int *out)
{
 char *end;errno=0;long v=strtol(s,&end,10);
 if (!*s || *end || errno || v<0 || v>maximum) return 0;
 *out=(int)v;return 1;
}
static int aggregate(const struct snapshot *s,unsigned long *r)
{
 memset(r,0,1024*sizeof(*r));
 if (!s->arrays || s->n<1 || s->n>MAX_ROWS) return 0;
 for (int i=0;i<s->n;++i) {
  int node=s->nodes[i];if (node<0 || node>=1024 || ULONG_MAX-r[node]<s->sizes[i]) return 0;
  r[node]+=s->sizes[i];
 }
 return 1;
}
static int exact_case_observed(const struct operand_case *c,int ratio)
{
 unsigned reserves=0,partials=0,releases=0,zero_queries=0,queries=0;int have_R=0,have_scratch=0,order=0;
 unsigned long second_query_seq=0,rollback_query_seq=0;
 for (unsigned i=0;i<nio;++i) if (ios[i].phase==RESERVE) {
  struct io_row *x=&ios[i]; if (x->ret!=0 || !x->identity_ok) return 0;
  if (x->op==IHK_DEVICE_RESERVE_MEM) {
   if (order!=0) return 0;
   order=1;
   ++reserves;
   if (x->before.n!=c->count || !x->before.arrays || x->before.min!=4096 || x->before.ratio!=ratio || x->before.timeout!=30) return 0;
   for (int j=0;j<c->count;++j) if (x->before.nodes[j]!=j || x->before.sizes[j]!=ULONG_MAX) return 0;
  } else if (x->op==IHK_DEVICE_QUERY_MEM) {
   if (order!=1) return 0;
   ++queries;if (queries==2) second_query_seq=x->seq;if (queries==3 && c->expected!=0) rollback_query_seq=x->seq;
   if (x->before.n==0 && x->after.n==0) ++zero_queries;
   if (!have_R && x->before.n>0) {
    unsigned long r[1024];if (!aggregate(&x->after,r)) return 0;
    for (int j=0;j<1024;++j) if (r[j]!=(j<3?c->R[j]:0)) return 0;
    have_R=1;
   }
  } else if (x->op==IHK_DEVICE_RELEASE_MEM_PARTIALLY) {
   if (order!=1 || c->expected!=0 || queries!=3 || !have_R) return 0;
   order=2;
   ++partials;if (x->before.n!=1024 || !x->before.arrays) return 0;
   for (int j=0;j<1024;++j) if (x->before.nodes[j]!=j || x->before.sizes[j]!=(j<3?c->partial[j]:0)) return 0;
  } else if (x->op==IHK_DEVICE_RELEASE_MEM) {
   if (order!=1 || c->expected==0 || queries!=4 || zero_queries!=4) return 0;
   order=2;
   ++releases;if (!conf_default(&x->config_before)) return 0;
  } else return 0;
 }
 for (unsigned i=0;i<nalloc;++i)
  if (allocs[i].phase==RESERVE && allocs[i].n==1024 && allocs[i].size==sizeof(size_t) && allocs[i].ptr && allocs[i].free_seq && (c->expected==0 || (allocs[i].seq>second_query_seq && allocs[i].seq<rollback_query_seq))) have_scratch=1;
 if (reserves!=1 || !have_scratch || order!=2) return 0;
 if (c->expected==0) return have_R && partials==1 && releases==0;
 return !have_R && zero_queries==4 && partials==0 && releases==1;
}
static int custody_observed(void)
{
 for (unsigned i=0;i<nalloc;++i) if (allocs[i].ptr && !allocs[i].free_seq) return 0;
 for (unsigned i=0;i<nclose;++i) if (closes[i].fd<0 || closes[i].ret!=0 || !closes[i].identity_ok) return 0;
 for (unsigned i=0;i<nio;++i) {
  if (!ios[i].identity_ok || ios[i].dev!=ios[0].dev || ios[i].ino!=ios[0].ino || ios[i].rdev!=ios[0].rdev) return 0;
  int joined=0;
  for (unsigned j=0;j<nclose;++j) if (closes[j].seq>ios[i].seq && closes[j].fd==ios[i].fd && closes[j].dev==ios[i].dev && closes[j].ino==ios[i].ino && closes[j].rdev==ios[i].rdev && closes[j].ret==0) { joined=1;break; }
  if (!joined) return 0;
 }
 return !trace_bad;
}
static void print_snapshot(const struct snapshot *s)
{
 printf("{\"num_chunks\":%d,\"min_chunk_size\":%d,\"max_size_ratio_all\":%d,\"timeout\":%d,\"sizes_pointer\":\"%llx\",\"numa_ids_pointer\":\"%llx\",\"arrays_observed\":%s,\"rows\":[",s->n,s->min,s->ratio,s->timeout,(unsigned long long)s->sizes_ptr,(unsigned long long)s->nodes_ptr,s->arrays?"true":"false");
 if (s->arrays) for (int i=0;i<s->n && i<MAX_ROWS;++i) printf("%s[%d,%lu]",i?",":"",s->nodes[i],s->sizes[i]);
 printf("]}");
}
static void print_trace(void)
{
 printf("\"ioctls\":[");
 for (unsigned i=0;i<nio;++i) {
  struct io_row *x=&ios[i];printf("%s{\"seq\":%lu,\"phase\":%d,\"fd\":%d,\"op\":%lu,\"return\":%d,\"errno\":%d,\"identity_ok\":%s,\"dev\":%llu,\"inode\":%llu,\"rdev\":%llu,\"config_before\":[%d,%d,%d,%d,%d,%d],\"config_default_before\":%s,\"before\":",i?",":"",x->seq,x->phase,x->fd,x->op,x->ret,x->error,x->identity_ok?"true":"false",x->dev,x->ino,x->rdev,x->config_before.balanced_enable,x->config_before.balanced_best_effort,x->config_before.balanced_variance_limit,x->config_before.min_chunk_size,x->config_before.max_size_ratio_all,x->config_before.timeout,conf_default(&x->config_before)?"true":"false");print_snapshot(&x->before);printf(",\"after\":");if (x->ret==0) print_snapshot(&x->after);else printf("null");printf("}");
 }
 printf("],\"calloc_free\":[");
 for (unsigned i=0;i<nalloc;++i) printf("%s{\"seq\":%lu,\"phase\":%d,\"n\":%zu,\"size\":%zu,\"pointer\":\"%llx\",\"errno\":%d,\"free_seq\":%lu}",i?",":"",allocs[i].seq,allocs[i].phase,allocs[i].n,allocs[i].size,(unsigned long long)allocs[i].ptr,allocs[i].error,allocs[i].free_seq);
 printf("],\"closes\":[");
 for (unsigned i=0;i<nclose;++i) printf("%s{\"seq\":%lu,\"phase\":%d,\"fd\":%d,\"return\":%d,\"errno\":%d,\"identity_ok\":%s,\"dev\":%llu,\"inode\":%llu,\"rdev\":%llu}",i?",":"",closes[i].seq,closes[i].phase,closes[i].fd,closes[i].ret,closes[i].error,closes[i].identity_ok?"true":"false",closes[i].dev,closes[i].ino,closes[i].rdev);
 printf("]");
}
int main(int argc,char **argv)
{
 if (argc!=4) return 120;
 const struct operand_case *c=NULL;
 for (unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);++i) if (!strcmp(argv[1],cases[i].name)) c=&cases[i];
 int index,ratio;if (!c || !decimal(argv[2],INT_MAX,&index) || !decimal(argv[3],98,&ratio) || ratio<1) return 120;
 real_calloc=(void *(*)(size_t,size_t))dlvsym(RTLD_NEXT,"calloc","GLIBC_2.2.5");
 real_free=(void (*)(void *))dlvsym(RTLD_NEXT,"free","GLIBC_2.2.5");
 real_close=(int (*)(int))dlvsym(RTLD_NEXT,"close","GLIBC_2.2.5");
 real_ioctl=(int (*)(int,unsigned long,...))dlvsym(RTLD_NEXT,"ioctl","GLIBC_2.2.5");
 if (!real_calloc || !real_free || !real_close || !real_ioctl) return 121;
 void *library=dlopen(NEW_DSO,RTLD_NOW|RTLD_LOCAL);if (!library) return 121;
 int (*set)(int,int,void *)=(int (*)(int,int,void *))dlsym(library,"ihk_reserve_mem_conf");
 int (*reserve)(int,struct ihk_mem_chunk *,int)=(int (*)(int,struct ihk_mem_chunk *,int))dlsym(library,"ihk_reserve_mem");
 int (*count)(int)=(int (*)(int))dlsym(library,"ihk_get_num_reserved_mem_chunks");
 int (*query)(int,struct ihk_mem_chunk *,int)=(int (*)(int,struct ihk_mem_chunk *,int))dlsym(library,"ihk_query_mem");
 int (*release)(int,struct ihk_mem_chunk *,int)=(int (*)(int,struct ihk_mem_chunk *,int))dlsym(library,"ihk_release_mem");
 configuration=(struct ihklib_reserve_mem_conf *)dlsym(library,"reserve_mem_conf");
 if (!set || !reserve || !count || !query || !release || !configuration) { dlclose(library);return 121; }
 Dl_info symbol;struct stat input,mapped;
 if (!dladdr((void *)reserve,&symbol) || !symbol.dli_fname || stat(NEW_DSO,&input) || stat(symbol.dli_fname,&mapped) || input.st_dev!=mapped.st_dev || input.st_ino!=mapped.st_ino || !S_ISREG(input.st_mode) || !conf_default(configuration)) { dlclose(library);return 121; }
 if (!origin((void *)set,&input) || !origin((void *)count,&input) || !origin((void *)query,&input) || !origin((void *)release,&input) || !origin(configuration,&input)) { dlclose(library);return 121; }
 Dl_info libc_origin;struct stat libc_file;
 if (!dladdr((void *)real_ioctl,&libc_origin) || !libc_origin.dli_fname || stat(libc_origin.dli_fname,&libc_file) || !S_ISREG(libc_file.st_mode) || (libc_file.st_dev==input.st_dev && libc_file.st_ino==input.st_ino) || !origin((void *)real_calloc,&libc_file) || !origin((void *)real_free,&libc_file) || !origin((void *)real_close,&libc_file)) { dlclose(library);return 121; }
 struct ihk_mem_chunk chunks[3]={0},saved[3]={0},post[MAX_ROWS]={0};
 for (int i=0;i<c->count;++i) { chunks[i].size=c->requested[i];chunks[i].numa_node_number=i; }memcpy(saved,chunks,sizeof(chunks));
 int setter[6]={INT_MIN,INT_MIN,INT_MIN,INT_MIN,INT_MIN,INT_MIN};int settings[6]={1,c->best,c->variance,4096,ratio,30};
 int baseline=-1,api=INT_MIN,api_errno=0,post_n=-1,post_ret=INT_MIN,cleanup=INT_MIN,after=-1,reset=0,unchanged=0,observed=0;
 phase=BASELINE;baseline=count(index);phase=OFF;
 if (baseline==0) {
  phase=SETTERS;int valid=1;
  for (int key=0;key<6;++key) { setter[key]=set(index,key,&settings[key]);if (setter[key]!=0) { valid=0;break; } }
  if (valid && !conf_matches(configuration,settings)) valid=0;
  phase=OFF;
  if (valid) {
   phase=RESERVE;api=reserve(index,chunks,c->count);api_errno=errno;phase=OFF;
   reset=conf_default(configuration);unchanged=!memcmp(saved,chunks,sizeof(chunks));observed=exact_case_observed(c,ratio);
   phase=POST;post_n=count(index);if (post_n>=0 && post_n<=MAX_ROWS) post_ret=query(index,post,post_n);phase=OFF;
   /* Baseline0 and Root's real GLOBAL-exclusive authority are prerequisites.
    * This is separate OWNED cleanup, never a replacement for the SUT rollback.
    * No planned residual is substituted for these actual queried rows.
    */
   if (post_n==0 && post_ret==0) cleanup=0;
   else if (post_n>0 && post_n<=MAX_ROWS && post_ret==0) {
    struct ihk_mem_chunk all={ULONG_MAX,0};phase=CLEANUP;cleanup=release(index,&all,1);phase=OFF;
   }
   phase=AFTER;after=count(index);phase=OFF;
  }
 }
 int good=baseline==0 && api==c->expected && reset && unchanged && observed && post_ret==0 && cleanup==0 && after==0 && custody_observed();
 int closed=dlclose(library);
 if (closed!=0) good=0;
 printf("{\"schema\":\"mckernel.F05.real-balanced-four-case-observation.v1\",\"case\":\"%s\",\"index\":%d,\"ratio\":%d,\"status\":\"%s\",\"library_dev\":%llu,\"library_inode\":%llu,\"setters\":[%d,%d,%d,%d,%d,%d],\"baseline_count\":%d,\"API_return\":%d,\"API_errno\":%d,\"one_shot_default_reset\":%s,\"caller_chunks_unchanged\":%s,\"exact_internal_operand_case_observed\":%s,\"post_count\":%d,\"post_query_return\":%d,\"post_rows\":[",c->name,index,ratio,good?"PASS_LOGICAL_CASE_PHYSICAL_RESTORATION_PENDING":"REFUSE_OR_FAIL_PRESERVED_REAL_OBSERVATIONS",(unsigned long long)input.st_dev,(unsigned long long)input.st_ino,setter[0],setter[1],setter[2],setter[3],setter[4],setter[5],baseline,api,api_errno,reset?"true":"false",unchanged?"true":"false",observed?"true":"false",post_n,post_ret);
 if (post_ret==0) for (int i=0;i<post_n && i<MAX_ROWS;++i) printf("%s[%d,%lu]",i?",":"",post[i].numa_node_number,post[i].size);
 printf("],\"owned_cleanup_return\":%d,\"after_cleanup_count\":%d,\"library_dlclose_return\":%d,\"libc_dev\":%llu,\"libc_inode\":%llu,\"trace_overflow_or_unsupported_shape\":%s,\"physical_restoration_proved\":false,\"resource_retired\":false,\"original_F05_acceptance\":false,",cleanup,after,closed,(unsigned long long)libc_file.st_dev,(unsigned long long)libc_file.st_ino,trace_bad?"true":"false");print_trace();printf("}\n");
 return good ? 0 : 1;
}
