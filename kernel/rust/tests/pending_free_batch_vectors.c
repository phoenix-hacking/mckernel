/* Independent finite descriptor model: integer identities, no Rust translation. */
#include <assert.h>
#include <stdio.h>
#include <string.h>
struct links { int next,prev; };
struct page { struct links list,hash; int mode,phys,count,mapped,offset,pgshift; };
struct world { struct links source,other,batch; int state,owner; struct page p[4]; int cb[32][3],nc; };
static struct links *link(struct world *w,int id) {
    if(id==1)return &w->source;
    if(id==2)return &w->other;
    if(id==3)return &w->batch;
    assert(id>=10&&id<14);return &w->p[id-10].list;
}
static void init(struct world*w) {int i;memset(w,0,sizeof(*w));for(i=0;i<4;i++){w->p[i].phys=100+i;w->p[i].count=70+i;w->p[i].mapped=80+i;w->p[i].pgshift=12+i;}}
static int begin(struct world*w,int h){struct links*l=link(w,h);if(l->next)return -22;l->next=h;l->prev=h;return 0;}
static int enqueue(struct world*w,int p,int h,int n){struct links*l=link(w,h);struct page*q=&w->p[p];int id=10+p;if(!l->next)return 0;q->mode=1;q->offset=n;q->list=(struct links){h,l->prev};link(w,l->prev)->next=id;l->prev=id;return 1;}
static void setup(struct world*w,int n,int other){int i;assert(begin(w,1)==0);for(i=0;i<n;i++)assert(enqueue(w,i,1,i+1)==1);if(other){assert(begin(w,2)==0);assert(enqueue(w,3,2,4)==1);}for(i=0;i<4;i++)w->p[i].hash=(struct links){20+i,20+i};}
static int valid(struct world*w,int h){struct links*l=link(w,h);int id=l->next,prev=h,seen=0;if(!id||!l->prev)return 0;while(id!=h){struct page*p;if(id<10||id>13||(seen&(1<<(id-10))))return 0;seen|=1<<(id-10);p=&w->p[id-10];if(p->mode!=1||p->list.prev!=prev)return 0;prev=id;id=p->list.next;}return prev==l->prev;}
static int detach(struct world*w,int h){struct links*l;if(!h||h==3||w->state||w->batch.next||w->batch.prev)return -22;if(!valid(w,h))return -22;l=link(w,h);w->batch=(struct links){3,3};if(l->next!=h){w->batch=*l;link(w,l->next)->prev=3;link(w,l->prev)->next=3;}*l=(struct links){0,0};w->state=1;w->owner=h;return 0;}
static void release(struct world*w,int id){struct page*p=&w->p[id-10];struct links*l=&p->list;link(w,l->next)->prev=l->prev;link(w,l->prev)->next=l->next;l->next=90;l->prev=91;p->mode=0;assert(w->nc<32);w->cb[w->nc][0]=p->phys;w->cb[w->nc][1]=p->offset;w->cb[w->nc++][2]=1;}
static int finish(struct world*w,int h){struct links*l=link(w,h);int count=0;if(!l->next)return 0;while(l->next!=h){int id=l->next;if(w->p[id-10].mode!=1)return -22;release(w,id);count++;}*l=(struct links){0,0};return count;}
static int drain(struct world*w,int h,int callback){int count;if(!callback||w->state!=1||w->owner!=h||!valid(w,3))return -22;count=finish(w,3);w->state=2;w->owner=0;return count;}
static void links(struct links l){printf("{\"next\":%d,\"prev\":%d}",l.next,l.prev);}
static void snapshot(struct world*w){int i;printf("{\"source\":");links(w->source);printf(",\"other\":");links(w->other);printf(",\"batch\":{\"head\":");links(w->batch);printf(",\"state\":%d,\"source\":%d},\"pages\":[",w->state,w->owner);for(i=0;i<4;i++){struct page*p=&w->p[i];printf("%s{\"list\":",i?",":"");links(p->list);printf(",\"hash\":");links(p->hash);printf(",\"mode\":%d,\"phys\":%d,\"count\":%d,\"mapped\":%d,\"offset\":%d,\"pgshift\":%d}",p->mode,p->phys,p->count,p->mapped,p->offset,p->pgshift);}printf("]}");}
static void emit(struct world*w,const char*name,const char*op,int rc,struct world*before){int i;printf("JSON|{\"case\":\"%s\",\"op\":\"%s\",\"rc\":%d,\"before\":",name,op,rc);snapshot(before);printf(",\"after\":");snapshot(w);printf(",\"callbacks\":[");for(i=0;i<w->nc;i++)printf("%s[%d,%d,%d]",i?",":"",w->cb[i][0],w->cb[i][1],w->cb[i][2]);printf("]}\n");if(rc<0)assert(!memcmp(before,w,sizeof(*w)));}
static struct world before(struct world*w){memset(w->cb,0,sizeof(w->cb));w->nc=0;return *w;}
static void retained_destination(struct world*w,struct world*saved){assert(w->state==1&&w->state==saved->state&&w->owner==saved->owner);assert(!memcmp(&w->batch,&saved->batch,sizeof(w->batch)));assert(!memcmp(w->p,saved->p,2*sizeof(w->p[0])));}
static void d(struct world*w,const char*name,int h){struct world b=before(w);int rc=detach(w,h);emit(w,name,"detach",rc,&b);}
static void r(struct world*w,const char*name,int wrong,int cb){struct world b=before(w);int rc=drain(w,wrong?2:1,cb);emit(w,name,"drain",rc,&b);}
int main(void){struct world w,b,retained;int i,rc;const char*names[]={"empty","one","three-order"};int counts[]={0,1,3};
    for(i=0;i<3;i++){init(&w);setup(&w,counts[i],0);d(&w,names[i],1);r(&w,names[i],0,1);}
    init(&w);setup(&w,2,0);d(&w,"later-invalid-setup",1);w.p[1].mode=0;r(&w,"later-invalid",0,1);w.p[1].mode=1;r(&w,"later-invalid-repair",0,1);
    init(&w);setup(&w,1,0);d(&w,"missing-callback-setup",1);r(&w,"missing-callback",0,0);r(&w,"missing-callback-recovery",0,1);
    init(&w);setup(&w,1,1);d(&w,"wrong-source-setup",1);r(&w,"wrong-source",1,1);r(&w,"wrong-source-recovery",0,1);
    init(&w);setup(&w,1,0);d(&w,"repeated-setup",1);d(&w,"repeated-detach",1);r(&w,"repeated-recovery",0,1);r(&w,"repeated-drain",0,1);
    init(&w);setup(&w,0,0);d(&w,"null-source",0);
    init(&w);d(&w,"inactive-empty",1);
    init(&w);setup(&w,1,0);d(&w,"alias-destination",3);
    init(&w);setup(&w,1,0);w.batch.next=1;d(&w,"mixed-destination-links",1);
    init(&w);setup(&w,1,0);w.state=1;d(&w,"mixed-destination-state",1);
    init(&w);setup(&w,2,1);d(&w,"two-head-isolation",1);retained=w;
    b=before(&w);rc=begin(&w,1);emit(&w,"source-reuse","begin",rc,&b);
    retained_destination(&w,&retained);assert(w.nc==0);
    b=before(&w);rc=enqueue(&w,2,1,7);emit(&w,"source-reuse","enqueue",rc,&b);
    retained_destination(&w,&retained);assert(w.nc==0);
    b=before(&w);rc=finish(&w,1);emit(&w,"source-reuse","finish",rc,&b);
    retained_destination(&w,&retained);assert(w.nc==1&&w.cb[0][0]==102&&w.cb[0][1]==7&&w.cb[0][2]==1);
    r(&w,"two-head-isolation",0,1);assert(w.nc==2&&w.cb[0][0]==100&&w.cb[0][1]==1&&w.cb[0][2]==1&&w.cb[1][0]==101&&w.cb[1][1]==2&&w.cb[1][2]==1);
    b=before(&w);rc=finish(&w,2);emit(&w,"other-head-finish","finish",rc,&b);
    return 0;
}
