/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "genuine_prologue.inc"
_Static_assert(sizeof(unsigned long)==8 && sizeof(void *)==8 && sizeof(off_t)==8, "range ABI");
_Static_assert((unsigned long)NOPHYS==~0UL && PAGE_SHIFT==12, "original range constants");
extern int puts(const char *);
struct record { struct process_vm *vm;unsigned long start,end,physical,flags;struct memobj *object;
    off_t offset;int shift;void *private_data;struct vm_range **output; };
static struct record seen;
static unsigned int calls;
static int provider_result;
static struct vm_range *provider_range;
int add_process_memory_range(struct process_vm *vm,unsigned long start,unsigned long end,
    unsigned long physical,unsigned long flags,struct memobj *object,off_t offset,
    int shift,void *private_data,struct vm_range **output)
{
    ++calls;seen.vm=vm;seen.start=start;seen.end=end;seen.physical=physical;seen.flags=flags;
    seen.object=object;seen.offset=offset;seen.shift=shift;seen.private_data=private_data;seen.output=output;
    if(output) *output=provider_range;
    return provider_result;
}
#define arch_vdso_add_range_bridge original_add_bridge
#include "original_bridge.inc"
#undef arch_vdso_add_range_bridge
extern int arch_vdso_add_range_bridge(struct process_vm *,unsigned long,unsigned long,unsigned long,struct vm_range **);
int main(void)
{
    const unsigned long words[]={0,1,0xffffffffUL,0x100000000UL,0x8000000000000000UL,
        0xffffffffffffffffUL,0x123456789abcdef0UL,0xaaaaaaaa55555555UL};
    const int results[]={0,-22,-14,-1,1,0x7fffffff,(-2147483647-1)};
    unsigned int i,k,null_output,cases=0;
    for(i=0;i<8;i++) for(k=0;k<7;k++) for(null_output=0;null_output<2;null_output++) {
        struct record original;unsigned int original_calls;
        struct vm_range *slot=0,*original_slot;
        struct vm_range **output=null_output ? (struct vm_range **)0 : &slot;
        struct process_vm *vm=(struct process_vm *)words[i];
        unsigned long start=words[(i+1)%8],end=words[(i+2)%8],flags=words[(i+3)%8];
        int original_result,actual_result;
        provider_result=results[k];provider_range=(struct vm_range *)words[(i+4)%8];calls=0;
        original_result=original_add_bridge(vm,start,end,flags,output);
        original=seen;original_calls=calls;original_slot=slot;slot=0;calls=0;
        actual_result=arch_vdso_add_range_bridge(vm,start,end,flags,output);
        if(original_calls!=1 || calls!=1 || seen.vm!=original.vm || seen.vm!=vm
           || seen.start!=original.start || seen.start!=start || seen.end!=original.end || seen.end!=end
           || seen.flags!=original.flags || seen.flags!=flags || seen.physical!=original.physical || seen.physical!=~0UL
           || seen.object!=original.object || seen.object || seen.offset!=original.offset || seen.offset
           || seen.shift!=original.shift || seen.shift!=12 || seen.private_data!=original.private_data || seen.private_data
           || seen.output!=original.output || seen.output!=output || slot!=original_slot || (!null_output && slot!=provider_range)
           || original_result!=actual_result || actual_result!=results[k]) {
            puts("FAIL vdso-add-range adapter parity");return 1;
        }
        ++cases;
    }
    if(cases!=112) { puts("FAIL add-range cardinality");return 2; }
    puts("PASS vdso-add-range adapter parity112");return 0;
}
