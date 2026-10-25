/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual C/Rust lookup delegates and genuine accepted lookup closure. Sequential
 * HOST fixture: real VM/RB/cache types, independent linear/cache oracle.
 */
#include "../../new-window-source-11/fixture-source/fixture-endpoints.h"
extern int printf(const char *,...);
extern struct vm_range *fixture_original_lookup(void *,unsigned long,unsigned long);
extern struct vm_range *arch_process_vm_rw_lookup_range_bridge(void *,unsigned long,unsigned long);
extern void arch_process_vm_rw_read_lock_bridge(void *);
extern void arch_process_vm_rw_read_unlock_bridge(void *);
extern unsigned long fixture_lookup_ABI(unsigned long);
_Static_assert(__builtin_types_compatible_p(__typeof__(&arch_process_vm_rw_lookup_range_bridge),struct vm_range *(*)(void *,unsigned long,unsigned long)),"lookup ABI");
static struct process_vm vm;
static struct vm_range ranges[7];
static int depth,bad,logn;
static unsigned long query_start,query_end;
static struct vm_range *want_range;
static int *word(void){return (int *)&vm.memory_range_lock;}
void preempt_disable(void){++depth;}
void preempt_enable(void){if(depth!=1)bad=1;--depth;}
void cpu_pause(void){bad=1;}
void process_range_public_log_bridge(int event,void *v,struct vm_range *r,unsigned long s,unsigned long e,int error)
{
    if(v!=&vm || s!=query_start || e!=query_end || error || depth!=1 ||
       __atomic_load_n(word(),__ATOMIC_SEQ_CST)!=8 || event!=logn+1 ||
       r!=(logn?want_range:0))bad=1;
    ++logn;
}
static void zero(void *p,size_t n){unsigned char *q=p;while(n--)*q++=0;}
static int equal(const void *a,const void *b,size_t n)
{const unsigned char *x=a,*y=b;while(n--)if(*x++!=*y++)return 0;return 1;}
static void setup(int count,int order,int warm)
{
    const int orders[3][7]={{0,1,2,3,4,5,6},{6,5,4,3,2,1,0},{3,1,5,0,2,4,6}};
    int k;zero(&vm,sizeof vm);zero(ranges,sizeof ranges);
    for(k=0;k<7;++k){ranges[k].start=16UL+32UL*k;ranges[k].end=ranges[k].start+16;}
    for(k=0;k<7;++k){int i=orders[order][k];struct rb_node **link=&vm.vm_range_tree.rb_node,*parent=0;
        if(i>=count)continue;
        while(*link){struct vm_range *r=(struct vm_range *)*link;parent=*link;
            link=ranges[i].start<r->start?&parent->rb_left:&parent->rb_right;}
        /* Use actual RB insertion/color owner, rather than invented layout. */
        rb_link_node(&ranges[i].vm_rb_node,parent,link);
        rb_insert_color(&ranges[i].vm_rb_node,&vm.vm_range_tree);
    }
    vm.range_cache_ind=warm%VM_RANGE_CACHE_SIZE;
    if(warm && count)for(k=0;k<VM_RANGE_CACHE_SIZE;++k)vm.range_cache[k]=&ranges[(k+warm)%count];
    __atomic_store_n(word(),7,__ATOMIC_SEQ_CST);depth=bad=logn=0;
}
static struct vm_range *oracle(int count,unsigned long s,unsigned long e,struct vm_range **cache,int *index)
{
    int i;if(e<=s)return 0;
    for(i=0;i<VM_RANGE_CACHE_SIZE;++i){struct vm_range *r=cache[(*index+i)%VM_RANGE_CACHE_SIZE];
        if(r && r->start<=s && r->end>=e)return r;}
    /* Independent ascending linear overlap scan; never walks the RB tree. */
    for(i=0;i<count;++i)if(s<ranges[i].end && e>ranges[i].start){
        *index=*index?*index-1:VM_RANGE_CACHE_SIZE-1;cache[*index]=&ranges[i];return &ranges[i];}
    return 0;
}
int main(void)
{
    const unsigned long abi[]={sizeof(struct process_vm),_Alignof(struct process_vm),sizeof(struct vm_range),_Alignof(struct vm_range),
      __builtin_offsetof(struct process_vm,vm_range_tree),__builtin_offsetof(struct process_vm,range_cache),
      __builtin_offsetof(struct process_vm,range_cache_ind),__builtin_offsetof(struct vm_range,vm_rb_node),
      __builtin_offsetof(struct vm_range,start),__builtin_offsetof(struct vm_range,end),sizeof(struct rb_node),VM_RANGE_CACHE_SIZE};
    const unsigned long queries[][2]={{0,1},{0,16},{0,17},{16,17},{16,32},{17,31},{31,33},{32,48},{32,49},{47,49},
      {48,64},{64,80},{1,250},{208,224},{224,225},{0,~0UL},{~0UL-1,~0UL},{17,17},{32,16}};
    const int counts[]={0,1,7};int a,c,o,w,mode,q,repetition,cases=0;
    for(a=0;a<12;++a)if(abi[a]!=fixture_lookup_ABI(a))return 1;
    for(c=0;c<3;++c)for(o=0;o<3;++o)for(w=0;w<=VM_RANGE_CACHE_SIZE;++w)for(mode=0;mode<2;++mode){
        struct vm_range *expected_cache[VM_RANGE_CACHE_SIZE];int expected_index;
        struct vm_range range_before[7];setup(counts[c],o,w);
        for(a=0;a<VM_RANGE_CACHE_SIZE;++a){expected_cache[a]=vm.range_cache[a];}
        expected_index=vm.range_cache_ind;
        __builtin_memcpy(range_before,ranges,sizeof ranges);
        for(repetition=0;repetition<2;++repetition)for(q=0;q<(int)(sizeof queries/sizeof queries[0]);++q){
            struct vm_range *got;struct process_vm expected_vm;
            query_start=queries[q][0];query_end=queries[q][1];logn=0;
            want_range=oracle(counts[c],query_start,query_end,expected_cache,&expected_index);
            __builtin_memcpy(&expected_vm,&vm,sizeof vm);
            for(a=0;a<VM_RANGE_CACHE_SIZE;++a){expected_vm.range_cache[a]=expected_cache[a];}
            expected_vm.range_cache_ind=expected_index;
            arch_process_vm_rw_read_lock_bridge(&vm);
            got=mode?arch_process_vm_rw_lookup_range_bridge(&vm,query_start,query_end):fixture_original_lookup(&vm,query_start,query_end);
            /* Borrow is consumed while real lock remains held. */
            if(got!=want_range || (got && !(got->start<query_end && got->end>query_start)) ||
               depth!=1 || __atomic_load_n(word(),__ATOMIC_SEQ_CST)!=8 || logn!=2 || bad)return 2;
            arch_process_vm_rw_read_unlock_bridge(&vm);
            if(depth || bad || !equal(&vm,&expected_vm,sizeof vm) || !equal(ranges,range_before,sizeof ranges))return 3;
            ++cases;
        }
    }
    printf("PASS process_VM_lookup cases=%d ABI=12 linear_overlap=1 cache_oracle=1 log_events=1 borrowed_under_real_lock=1 lock_restored=1\n",cases);
    return 0;
}
