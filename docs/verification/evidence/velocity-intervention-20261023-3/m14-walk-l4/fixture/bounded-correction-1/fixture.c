/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Exact original C wrapper and candidate Rust entry share actual production Rust
 * walk_pte_l4. Controlled callback replaces retained private clear_range_l4 only;
 * this is wrapper/ABI/walker contract proof, not C callback-chain retirement. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include <stdlib.h>
typedef unsigned long pte_t;
typedef int (*callback_t)(void *,pte_t *,uint64_t,uint64_t,uint64_t);
extern int walk_pte_l4(void *,unsigned long,unsigned long,unsigned long,callback_t,void *);
extern int x86_clear_range_walk_l4_bridge(void *,unsigned long,unsigned long,unsigned long,void *);
_Static_assert(__builtin_types_compatible_p(__typeof__(&x86_clear_range_walk_l4_bridge),int(*)(void*,unsigned long,unsigned long,unsigned long,void*)),"complete production Rust export ABI");
struct event { unsigned long index,base,start,end,before; };
struct state { pte_t *pt; unsigned count; int mode; struct event events[512]; };
static int clear_range_l4(void *arg,pte_t *pte,uint64_t base,uint64_t start,uint64_t end)
{
 struct state *s=arg; if(!s || s->count>=512 || pte<s->pt || pte>=s->pt+512) abort();
 unsigned n=s->count++; s->events[n]=(struct event){pte-s->pt,base,start,end,*pte};
 *pte ^= (0x100UL+n);
 switch(s->mode) {
 case 0:return 0;
 case 1:return -2;
 case 2:return -5;
 case 3:return n==2?-12:0;
 case 4:return n==1?INT_MIN:-2;
 case 5:return n==1?7:0;
 default:return n%2?-2:0;
 }
}
/* Same typed immutable identity emitted in selected production C. */
int (*const x86_clear_range_l4_callback)(void*,pte_t*,uint64_t,uint64_t,uint64_t)=&clear_range_l4;
#include "../original-body.inc"
static void require(int ok,const char *why) { if(!ok){fprintf(stderr,"FAIL %s\n",why);exit(1);} }
int main(void)
{
 const unsigned long u=1UL<<39;
 const unsigned long bounds[][2]={{0,0},{0,1},{0,u},{1,u+1},{u,4*u},{u-1,3*u+1},{4*u,4*u},{0,512*u}};
 const unsigned long bases[]={0,0xffff000000000000UL};
 unsigned pairs=0;
 for(unsigned b=0;b<2;b++)for(unsigned v=0;v<8;v++)for(int mode=0;mode<7;mode++)for(unsigned nullpt=0;nullpt<2;nullpt++) {
  pte_t a[512],c[512];for(unsigned i=0;i<512;i++)a[i]=c[i]=(unsigned long)i*0x1001UL;
  struct state sa={.pt=a,.mode=mode},sc={.pt=c,.mode=mode};
  unsigned long start=bases[b]+bounds[v][0],end=bases[b]+bounds[v][1];
  int ra=original_walk_l4(nullpt?NULL:a,bases[b],start,end,&sa);
  int rc=x86_clear_range_walk_l4_bridge(nullpt?NULL:c,bases[b],start,end,&sc);
  require(ra==rc && sa.count==sc.count,"return/callback count");
  require(!memcmp(sa.events,sc.events,sizeof sa.events),"callback identity/order/args/entry values");
  require(!memcmp(a,c,sizeof a),"synchronous PTE mutations");
  if(nullpt)require(ra==-2 && !sa.count,"actual walker null table policy");
  if(!nullpt && end!=0 && bounds[v][0]==bounds[v][1])require(ra==-2 && !sa.count,"empty bounds");
  if(!nullpt && end==0 && mode==0)require(ra==0 && sa.count==512,"end0 full512 sentinel");
  if(!nullpt && sa.count && mode==2)require(ra==-5 && sa.count==1,"first hard error stops");
  if(!nullpt && sa.count && mode==1)require(ra==-2,"ENOENT aggregation");
  pairs++;
 }
 printf("PASS %u original-C/Rust pairs; actual production walk_pte_l4; callback ABI/order/mutations/errors; no callback retained\n",pairs);
 return 0;
}
