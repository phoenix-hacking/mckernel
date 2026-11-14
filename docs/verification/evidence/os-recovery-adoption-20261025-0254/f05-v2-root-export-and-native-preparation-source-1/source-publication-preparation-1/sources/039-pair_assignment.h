/* Linux control plane only. Wire record shared by this boot helper and PID1. */
#ifndef PAIR_ASSIGNMENT_H
#define PAIR_ASSIGNMENT_H
struct pair_assignment {
    unsigned long magic, nonce[2];
    unsigned int os, count;
    unsigned long generation;
    int physical[2];
};
_Static_assert(sizeof(struct pair_assignment)==48,"LP64 assignment record");
#define PAIR_MAGIC 0x3155504344524150UL
#define PAIR_CHALLENGE "/case/evidence/pair.challenge"
#define PAIR_ASSIGNMENT "/case/evidence/pair.assignment"
#define PAIR_LOG_LIMIT 262144
/* Checked decimal parsing: never accept overflow or a partial field. */
static inline int pair_literal(const char **p,const char *end,const char *text)
{
    const char *q=*p;
    while(*text) { if(q==end || *q++!=*text++)return -1; }
    *p=q;return 0;
}
static inline int pair_number(const char **p,const char *end,unsigned long *out)
{
    const char *q=*p;unsigned long n=0;
    if(q==end || *q<'0' || *q>'9')return -1;
    while(q!=end && *q>='0' && *q<='9') {
        unsigned long d=(unsigned long)(*q++-'0');
        if(n>(~0UL-d)/10)return -1;
        n=n*10+d;
    }
    *p=q;*out=n;return 0;
}
/* Existing kernel control-acceptance records identify the live OS generation
 * and rank mapping. Reject duplicate/mismatched generations rather than taking
 * the last record. This runs before any application is started. */
static inline int pair_routes(const char *log,unsigned long size,
                              const struct pair_assignment *a,unsigned long *generation)
{
    unsigned seen=0;unsigned long gen=0;
    const char *end=log+size;
    for(const char *line=log;line<end;) {
        const char *next=line;while(next<end && *next!='\n')next++;
        for(const char *p=line;p<next;p++) {
            const char *q=p;unsigned long os,g,port,rank,cpu;
            if(pair_literal(&q,next,"IHK-SMP: control accepted os="))continue;
            if(pair_number(&q,next,&os) || pair_literal(&q,next," generation=") ||
               pair_number(&q,next,&g) || pair_literal(&q,next," port=") ||
               pair_number(&q,next,&port))return -1;
            if(os!=a->os || port!=501)continue;
            if(pair_literal(&q,next," guest_cpu=") || pair_number(&q,next,&rank) ||
               pair_literal(&q,next," linux_cpu=") || pair_number(&q,next,&cpu) ||
               pair_literal(&q,next," cookie=") || !g || rank>=2 ||
               cpu!=(unsigned long)a->physical[rank] || (seen&(1U<<rank)) ||
               (seen && gen!=g))return -1;
            gen=g;seen|=1U<<rank;
        }
        line=next<end?next+1:end;
    }
    if(seen!=3)return -1;
    *generation=gen;return 0;
}
static inline int pair_assignment_valid(const struct pair_assignment *a,
                                      const unsigned long nonce[2])
{
    return a->magic==PAIR_MAGIC && a->nonce[0]==nonce[0] &&
        a->nonce[1]==nonce[1] && (nonce[0]||nonce[1]) && a->os==0 &&
        a->count==2 && a->generation>0 && a->physical[0]==1 && a->physical[1]==2;
}
#endif
