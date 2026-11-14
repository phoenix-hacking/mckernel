/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "genuine_prologue.inc"
_Static_assert(sizeof(enum ihk_mc_pt_attribute)==8 && sizeof(uintptr_t)==8 && sizeof(void *)==8, "real range/attribute ABI");
extern int puts(const char *);
struct record { page_table_t pt;struct process_vm *vm;void *start,*end;uintptr_t physical;
    enum ihk_mc_pt_attribute attribute;int shift;struct vm_range *range;int overwrite; };
static struct record seen;
static unsigned int calls;
static int provider_result;
int ihk_mc_pt_set_range(page_table_t pt,struct process_vm *vm,void *start,void *end,
    uintptr_t physical,enum ihk_mc_pt_attribute attribute,int shift,struct vm_range *range,int overwrite)
{
    ++calls;seen.pt=pt;seen.vm=vm;seen.start=start;seen.end=end;seen.physical=physical;
    seen.attribute=attribute;seen.shift=shift;seen.range=range;seen.overwrite=overwrite;
    return provider_result;
}
#define arch_vdso_set_range_bridge original_set_bridge
#include "original_bridge.inc"
#undef arch_vdso_set_range_bridge
extern int arch_vdso_set_range_bridge(page_table_t,struct process_vm *,unsigned long,unsigned long,unsigned long,unsigned long,struct vm_range *);
int main(void)
{
    const unsigned long words[]={0,1,0xffffffffUL,0x100000000UL,0x8000000000000000UL,
        0xffffffffffffffffUL,0x123456789abcdef0UL,0xaaaaaaaa55555555UL};
    const int results[]={0,-22,-14,-1,1,0x7fffffff,(-2147483647-1)};
    unsigned int i,k,cases=0;
    for(i=0;i<8;i++) for(k=0;k<7;k++) {
        struct record original;unsigned int original_calls;
        page_table_t pt=(page_table_t)words[i];struct process_vm *vm=(struct process_vm *)words[(i+1)%8];
        unsigned long start=words[(i+2)%8],end=words[(i+3)%8],physical=words[(i+4)%8],attribute=words[(i+5)%8];
        struct vm_range *range=(struct vm_range *)words[(i+6)%8];int original_result,actual_result;
        provider_result=results[k];calls=0;
        original_result=original_set_bridge(pt,vm,start,end,physical,attribute,range);
        original=seen;original_calls=calls;calls=0;
        actual_result=arch_vdso_set_range_bridge(pt,vm,start,end,physical,attribute,range);
        if(original_calls!=1 || calls!=1 || seen.pt!=original.pt || seen.pt!=pt || seen.vm!=original.vm || seen.vm!=vm
           || seen.start!=original.start || seen.start!=(void *)start || seen.end!=original.end || seen.end!=(void *)end
           || seen.physical!=original.physical || seen.physical!=(uintptr_t)physical
           || seen.attribute!=original.attribute || (unsigned long)seen.attribute!=attribute
           || seen.shift!=original.shift || seen.shift || seen.range!=original.range || seen.range!=range
           || seen.overwrite!=original.overwrite || seen.overwrite || original_result!=actual_result || actual_result!=results[k]) {
            puts("FAIL vdso-set-range adapter parity");return 1;
        }
        ++cases;
    }
    if(cases!=56) { puts("FAIL set-range cardinality");return 2; }
    puts("PASS vdso-set-range adapter parity56");return 0;
}
