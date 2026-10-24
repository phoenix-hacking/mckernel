/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * No main or execution recipe. Extend the one existing controlled fixture after grant.
 * stat/fopen/getline/fclose are controlled; prior OS-open wrappers remain selected. */
#define _GNU_SOURCE
#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
extern int ihklib_os_query_mem_sysfs(int,char*,ssize_t,const char*),ref_ihklib_os_query_mem_sysfs(int,char*,ssize_t,const char*);
extern void mcstat_fragment_set_os_open_success(void);
extern int ihk_os_query_total_mem(int,unsigned long*,int),ref_ihk_os_query_total_mem(int,unsigned long*,int);
extern size_t ihklib_mcstat_stat_storage_size(void),ihklib_mcstat_stat_storage_align(void);
struct test_case {const char *node0,*node1,*node2;int fopen_fail,getline_fail;};
static const struct test_case cases[]={
 {"Node 0 MemTotal: 4096 kB\n","Node 1 MemTotal: 8192 kB\n",NULL,0,0},
 {NULL,NULL,NULL,0,0},
 {"Node 0 MemFree: 12 kB\n",NULL,NULL,0,0},
 {"Node 0 MemTotal: 4 kB\n",NULL,"Node 2 MemTotal: 99 kB\n",0,0},
 {"Node 99 MemTotal: 4 kB\n",NULL,NULL,0,0},
 {"not-a-row\nNode 0 MemTotal: 4 kB\n",NULL,NULL,0,0},
 {"Node 0 MemTotal: 1 kB\nNode 0 MemTotal: 2 kB\n",NULL,NULL,0,0},
 {"Node 0 MemTotal: 4 kB\n",NULL,NULL,1,0},
 {"Node 0 MemTotal: 4 kB\n",NULL,NULL,0,1},
 {"Node 0 MemTotal: 1844674407370955 kB\n",NULL,NULL,0,0},
};
static const struct test_case *current;static int opened,position,events[64],ne;
static const char *input;
static void record(int code){assert(ne<64);events[ne++]=code;}
static int do_stat(const char *p,struct stat *st){
 int node=-1;assert(sscanf(p,"/sys/devices/virtual/mcos/mcos7/sys/devices/system/node/node%d/meminfo",&node)==1);record(10+node);
 const char *row=node==0?current->node0:node==1?current->node1:node==2?current->node2:NULL;
 if(!row){errno=ENOENT;return -1;}memset(st,0,sizeof *st);input=row;return 0;
}
int __wrap___xstat(int version,const char *p,struct stat *st){assert(version==1);return do_stat(p,st);}
int __wrap_stat(const char *p,struct stat *st){return do_stat(p,st);}
FILE *__wrap_fopen(const char *p,const char *mode){(void)p;assert(strcmp(mode,"r")==0);record(20);if(current->fopen_fail){errno=EACCES;return NULL;}opened=1;position=0;return (FILE*)&opened;}
ssize_t __wrap_getline(char **out,size_t *capacity,FILE *file){assert(file==(FILE*)&opened&&opened);record(21);if(current->getline_fail){errno=ENOMEM;return -1;}if(!input[position])return -1;const char *start=input+position;const char *end=strchr(start,'\n');size_t n=end?(size_t)(end-start+1):strlen(start);*out=malloc(n+1);assert(*out);memcpy(*out,start,n);(*out)[n]=0;*capacity=n+1;position+=(int)n;return (ssize_t)n;}
int __wrap_fclose(FILE *file){assert(file==(FILE*)&opened&&opened);record(22);opened=0;errno=EBADF;return -1;}
static void reset(void){ne=opened=position=0;errno=0;}
unsigned test_total_memory_source_fragment(void){
 assert(ihklib_mcstat_stat_storage_size()==sizeof(struct stat));assert(ihklib_mcstat_stat_storage_align()==_Alignof(struct stat));
 unsigned vectors=0;char huge_kind[1100];memset(huge_kind,'x',sizeof huge_kind);huge_kind[1099]=0;
 for(unsigned i=0;i<sizeof cases/sizeof cases[0];i++){
  current=&cases[i];
  /* Exactly one-format truncation is defined; no subsequent out-of-bounds write is tested. */
  for(int small=0;small<2;small++){
   if(small&&i!=4)continue;char out[16384],want[16384];memset(out,0xa5,sizeof out);ssize_t cap=small?5:sizeof out;
   reset();int rc=ref_ihklib_os_query_mem_sysfs(7,out,cap,"MemTotal"),err=errno;memcpy(want,out,sizeof out);int en=ne,trace[64];memcpy(trace,events,sizeof trace);
   memset(out,0xa5,sizeof out);reset();int got=ihklib_os_query_mem_sysfs(7,out,cap,"MemTotal");assert(got==rc&&errno==err&&ne==en&&!memcmp(trace,events,(size_t)ne*sizeof events[0])&&!memcmp(want,out,sizeof out));vectors++;
  }
  for(int count=0;count<=3;count++){
   unsigned long output[4],expected[4];for(int j=0;j<4;j++)output[j]=0xa5a5a5a5UL;
   mcstat_fragment_set_os_open_success();reset();int rc=ref_ihk_os_query_total_mem(7,output,count),err=errno;memcpy(expected,output,sizeof output);int en=ne,trace[64];memcpy(trace,events,sizeof trace);
   for(int j=0;j<4;j++)output[j]=0xa5a5a5a5UL;mcstat_fragment_set_os_open_success();reset();int got=ihk_os_query_total_mem(7,output,count);assert(got==rc&&errno==err&&ne==en&&!memcmp(trace,events,(size_t)ne*sizeof events[0])&&!memcmp(expected,output,sizeof output));vectors++;
  }
 }
 /* Additional merge vectors: NULL output/kind, capacity0/-1, long kind error,
  * strdup/calloc failure at each parser allocation, a first out-of-range node
  * after an earlier valid assignment (retain partial output), bytes exactly fitting
  * last format vs one-format truncation. Unknown later-write overflow is C debt. */
 return vectors;
}
