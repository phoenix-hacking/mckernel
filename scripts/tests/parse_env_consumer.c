#define _GNU_SOURCE
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ihk/ihklib_private.h>
/* Exact private function signature in the retained ihklib.c definition.
 * ihklib_private.h defines its bounds but does not declare this private root. */
extern int parse_env(const char *, int, char ***, char ***);
extern void *__real_calloc(size_t, size_t);
extern char *__real_strndup(const char *, size_t);
extern char *__real_strdup(const char *);
extern void __real_free(void *);
static void *owned[32];
static int active, attempts, fail_at, live, checks, failures;
static int fail(void) { if (!active) return 0; ++attempts; if (attempts != fail_at) return 0; errno=ENOMEM; return 1; }
static void *record(void *p) { if (active && p) { for (int i=0;i<32;i++) if (!owned[i]) { owned[i]=p; ++live; return p; } abort(); } return p; }
void *__wrap_calloc(size_t n,size_t s) { return fail()?NULL:record(__real_calloc(n,s)); }
char *__wrap_strndup(const char *p,size_t n) { return fail()?NULL:record(__real_strndup(p,n)); }
char *__wrap_strdup(const char *p) { return fail()?NULL:record(__real_strdup(p)); }
void __wrap_free(void *p) {
 if (active && p) { int found=0; for (int i=0;i<32;i++) if (owned[i]==p) { owned[i]=NULL; --live; found=1; break; } if (!found) abort(); }
 __real_free(p);
}
static void reset(int ordinal) { if(live) abort(); active=1; attempts=0; fail_at=ordinal; }
static int discard(void) { int reclaimed=0; active=0; for(int i=0;i<32;i++) if(owned[i]) { __real_free(owned[i]); owned[i]=NULL; ++reclaimed; } live=0; return reclaimed; }
static void failure(const char *text,int count,int ordinal,int expected) {
 char *first=NULL,*second=NULL; char **names=&first,**values=&second;
 reset(ordinal); int result=parse_env(text,count,&names,&values);
 int ok=result==expected && names==&first && values==&second && live==0;
 ++checks; if(!ok) { ++failures; printf("FAIL failure-point=%d result=%d live=%d outputs_unchanged=%d\n",ordinal,result,live,names==&first&&values==&second); }
 discard();
}
static void success(const char *text,int count,const char *n0,const char *v0,const char *n1,const char *v1) {
 char **names=NULL,**values=NULL; reset(0); int result=parse_env(text,count,&names,&values);
 int ok=result==0 && names && values;
 if(ok) { ok=names[0] && values[0] && !strcmp(names[0],n0) && !strcmp(values[0],v0); if(count==2) ok=ok && names[1] && values[1] && !strcmp(names[1],n1) && !strcmp(values[1],v1); }
 if(result==0 && names && values) { for(int i=0;i<count;i++) { __wrap_free(names[i]); __wrap_free(values[i]); } __wrap_free(names); __wrap_free(values); }
 ok=ok && live==0; ++checks; if(!ok) { ++failures; printf("FAIL success result=%d live=%d\n",result,live); } discard();
}
int run_consumer(int baseline) {
 if(baseline) {
  char *first=NULL,*second=NULL; char **names=&first,**values=&second;
  reset(2); int result=parse_env("A=one\0B=two",2,&names,&values);
  int observed_live=live, unchanged=names==&first && values==&second;
  int reclaimed=discard();
  ++checks; if(result!=-ENOMEM || !unchanged || observed_live!=1 || reclaimed!=1 || live!=0) ++failures;
  printf("baseline expected-leak observed-live=%d reclaimed=%d restored-live=%d result=%d outputs-unchanged=%d\n",observed_live,reclaimed,live,result,unchanged);
  printf("baseline checks=%d failures=%d\n",checks,failures); return failures?1:0;
 }
 for(int point=1;point<=8;point++) failure("A=one\0B=two",2,point,-ENOMEM);
 success("A=one\0B=two",2,"A","one","B","two");
 success("BARE",1,"BARE","",NULL,NULL);
 success("=value",1,"","value",NULL,NULL);
 success("A=x=y",1,"A","x=y",NULL,NULL);
 failure("",1,0,-EINVAL); failure(NULL,1,0,-EINVAL); failure("A=x",0,0,-EINVAL); failure("A=x",IHKLIB_MAX_NUM_ENV+1,0,-EINVAL);
 char *region=malloc(IHKLIB_MAX_SIZE_ENV); if(!region) abort();
 memset(region,'x',IHKLIB_MAX_SIZE_ENV); region[IHKLIB_MAX_SIZE_ENV-1]=0; failure(region,1,0,-EINVAL);
 memcpy(region,"A=x\0",4); region[IHKLIB_MAX_SIZE_ENV-1]=0; failure(region,2,0,-EINVAL); free(region);
 printf("candidate checks=%d failures=%d\n",checks,failures); return failures?1:0;
}
