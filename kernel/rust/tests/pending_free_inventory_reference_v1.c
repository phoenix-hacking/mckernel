/* Independent integer reference and case constructors; no Rust constants read. */
#include <stdint.h>
#define INV_MAX 8u
#define INV_PAGE 4096ull
enum inventory_status{REF_OK=0,REF_EINVAL=-22,REF_EOVERFLOW=-75,REF_ENOSPC=-28};
struct descriptor{uint64_t id,physical_start,page_count,next,prev;uint32_t generation;uint8_t mode;};
struct inventory_case{const char*name;unsigned count;int expected;struct descriptor records[INV_MAX];uint64_t ids[INV_MAX];};
static const struct descriptor*resolve(const struct inventory_case*c,uint64_t id){for(unsigned i=0;i<c->count;i++)if(c->records[i].id==id)return &c->records[i];return 0;}
static int checked_bytes(uint64_t p,uint64_t*b){if(!p||p>UINT64_MAX/INV_PAGE)return REF_EOVERFLOW;*b=p*INV_PAGE;return REF_OK;}
static int overlap(uint64_t a,uint64_t an,uint64_t b,uint64_t bn){uint64_t ae,be;if(__builtin_add_overflow(a,an,&ae)||__builtin_add_overflow(b,bn,&be))return 1;return a<be&&b<ae;}
static int validate(const struct inventory_case*c,uint32_t gen,uint64_t sentinel){if(!c||c->count<2||c->count>INV_MAX)return REF_EINVAL;const struct descriptor*s=resolve(c,sentinel);if(!s||!s->next||!s->prev||s->next==sentinel||s->prev==sentinel)return REF_EINVAL;for(unsigned i=0;i<c->count-1;i++){const struct descriptor*d=resolve(c,c->ids[i]);if(!d||d->id==sentinel||d->generation!=gen||d->mode!=1||d->physical_start%INV_PAGE)return REF_EINVAL;uint64_t bytes;if(checked_bytes(d->page_count,&bytes)!=REF_OK)return REF_EINVAL;uint64_t end;if(__builtin_add_overflow(d->physical_start,bytes,&end))return REF_EOVERFLOW;const struct descriptor*n=resolve(c,d->next),*p=resolve(c,d->prev);if(!n||!p||n->prev!=d->id||p->next!=d->id)return REF_EINVAL;for(unsigned j=0;j<i;j++){const struct descriptor*q=resolve(c,c->ids[j]);uint64_t qb;if(!q||checked_bytes(q->page_count,&qb)!=REF_OK||overlap(q->physical_start,qb,d->physical_start,bytes))return REF_EINVAL;}}if(s->next!=c->ids[0]||s->prev!=c->ids[c->count-2])return REF_EINVAL;return REF_OK;}
static int add_case(struct inventory_case*c,const char*n,unsigned count,int expected){if(!c||!n||count>INV_MAX)return REF_EINVAL;c->name=n;c->count=count;c->expected=expected;return REF_OK;}
static void construct_cases(struct inventory_case out[22]){unsigned n=0;
#define C(N,S) add_case(&out[n++],N,0,S)
C("capacity-zero",REF_ENOSPC);C("capacity-exact",REF_OK);C("capacity-exceeded",REF_ENOSPC);C("count-mismatch",REF_EINVAL);C("count-overflow",REF_EOVERFLOW);C("duplicate-id",REF_EINVAL);C("foreign-id",REF_EINVAL);C("null-link",REF_EINVAL);C("dangling-link",REF_EINVAL);C("one-sided-link",REF_EINVAL);C("malformed-sentinel",REF_EINVAL);C("foreign-cycle",REF_EINVAL);C("wrong-mode",REF_EINVAL);C("invalid-page-count",REF_EINVAL);C("page-count-overflow",REF_EOVERFLOW);C("misaligned-extent",REF_EINVAL);C("foreign-extent",REF_EINVAL);C("overlapping-extent",REF_EINVAL);C("stale-generation",REF_EINVAL);C("concurrent-mutation",REF_EINVAL);C("valid-single",REF_OK);C("valid-two",REF_OK);#undef C}
