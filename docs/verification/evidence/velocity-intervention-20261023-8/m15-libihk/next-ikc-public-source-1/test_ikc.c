/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stddef.h>
#include <stdint.h>
#include <ihk/ihklib_private.h>
#include <unistd.h>
_Static_assert(sizeof(struct ihk_ikc_req)==24,"IKC size");
_Static_assert(offsetof(struct ihk_ikc_req,num_cpus)==16,"IKC count");
int loglevel=0;
/* Functional fixture prevents logging to a real /dev/kmsg even if launched by root. */
uid_t geteuid(void){return 1000;}
extern int ikc_str2count(char*),ref_ikc_str2count(char*);
extern int ikc_str2req(char*,int,struct ihk_ikc_req*),ref_ikc_str2req(char*,int,struct ihk_ikc_req*);
extern char *ikc_req2str(struct ihk_ikc_req*),*ref_ikc_req2str(struct ihk_ikc_req*);
extern size_t ihklib_ikc_req_size(void),ihklib_ikc_req_count_offset(void);
static int checks;
#define CHECK(x) do {checks++;if(!(x)){fprintf(stderr,"line%d check%d\n",__LINE__,checks);exit(1);}}while(0)
static int fail_malloc,fail_calloc,call_calloc;
void *__real_malloc(size_t); void *__real_calloc(size_t,size_t);
void *__wrap_malloc(size_t n){if(fail_malloc)return NULL;return __real_malloc(n);}
void *__wrap_calloc(size_t a,size_t b){if(fail_calloc&&++call_calloc==fail_calloc)return NULL;return __real_calloc(a,b);}
static void reset(int m,int c){fail_malloc=m;fail_calloc=c;call_calloc=0;}
static void format(int *s,int *d,int n,int m,int ca){
 struct ihk_ikc_req req={s,d,n};reset(m,ca);char*a=ref_ikc_req2str(&req);reset(m,ca);char*b=ikc_req2str(&req);reset(0,0);
 CHECK((a==NULL)==(b==NULL));if(a&&b)CHECK(strcmp(a,b)==0);free(a);free(b);
}
int main(void){
 CHECK(ihklib_ikc_req_size()==sizeof(struct ihk_ikc_req));CHECK(ihklib_ikc_req_count_offset()==offsetof(struct ihk_ikc_req,num_cpus));
 const char* v[]={NULL,"","0:0","0-3:2","1,3,5:4+2,6:0","0:1+","+0:1","0::1",":1","0:","0","a:1","0-:1","2-0:1","0:-1","0: 2","0:2 ","0:2147483648","0:0+0:1","0-1023:0","0-1024:0","0,0:0","0:1+1:0+2:1"};
 for(size_t k=0;k<sizeof(v)/sizeof(v[0]);k++){
  char*a=v[k]?strdup(v[k]):NULL,*b=v[k]?strdup(v[k]):NULL;
  CHECK(ref_ikc_str2count(a)==ikc_str2count(b));
  for(int lim=-1;lim<=8;lim++)for(int nulls=0;nulls<4;nulls++){
   int as[16],ad[16],bs[16],bd[16];for(int j=0;j<16;j++)as[j]=ad[j]=bs[j]=bd[j]=0x12345678;
   struct ihk_ikc_req ar={nulls&1?NULL:as,nulls&2?NULL:ad,99},br={nulls&1?NULL:bs,nulls&2?NULL:bd,99};
   CHECK(ref_ikc_str2req(a,lim,&ar)==ikc_str2req(b,lim,&br));CHECK(ar.num_cpus==br.num_cpus);
   CHECK(!memcmp(as,bs,sizeof(as))&&!memcmp(ad,bd,sizeof(ad)));
  }free(a);free(b);
 }
 CHECK(ref_ikc_str2req(NULL,0,NULL)==ikc_str2req(NULL,0,NULL));
 int s[256],d[256];for(int i=0;i<256;i++){s[i]=i;d[i]=(i*7)%19;}
 for(int n=0;n<=256;n+=8)format(s,d,n,0,0);
 s[0]=4;s[1]=4;s[2]=7;d[0]=2;d[1]=2;d[2]=0;format(s,d,3,0,0);
 for(int f=1;f<=5;f++)format(s,d,3,0,f);format(s,d,3,1,0);
 printf("PASS IKC %d checks; ABI24/count16; defined C domain only\n",checks);return 0;
}
