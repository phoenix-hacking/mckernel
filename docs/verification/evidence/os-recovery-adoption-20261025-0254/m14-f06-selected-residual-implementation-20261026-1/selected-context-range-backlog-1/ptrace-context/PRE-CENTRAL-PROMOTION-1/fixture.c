/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "genuine_prologue.inc"
_Static_assert(sizeof(void *)==8 && sizeof(unsigned long)==8, "raw pointer ABI");
extern int puts(const char *);
static unsigned int calls;
static unsigned long seen_thread,result_bits;
ihk_mc_user_context_t *lookup_user_context(struct thread *thread)
{
    ++calls;seen_thread=(unsigned long)thread;
    return (ihk_mc_user_context_t *)result_bits;
}
#define arch_ptrace_lookup_user_context_bridge original_context_bridge
#include "original_bridge.inc"
#undef arch_ptrace_lookup_user_context_bridge
extern void *arch_ptrace_lookup_user_context_bridge(void *);
int main(void)
{
    const unsigned long words[]={0,1,0xffffffffUL,0x100000000UL,0x8000000000000000UL,
        0xffffffffffffffffUL,0x123456789abcdef0UL,0xaaaaaaaa55555555UL};
    unsigned int i,j,cases=0;
    for(i=0;i<8;i++) for(j=0;j<8;j++) {
        unsigned int original_calls;
        unsigned long original_thread,original_result,actual_result;
        result_bits=words[j];calls=0;
        original_result=(unsigned long)original_context_bridge((void *)words[i]);
        original_calls=calls;original_thread=seen_thread;calls=0;
        actual_result=(unsigned long)arch_ptrace_lookup_user_context_bridge((void *)words[i]);
        if(original_calls!=1 || calls!=1 || seen_thread!=original_thread || seen_thread!=words[i]
           || original_result!=actual_result || actual_result!=words[j]) {
            puts("FAIL ptrace-context adapter parity");return 1;
        }
        ++cases;
    }
    if(cases!=64) { puts("FAIL context cardinality");return 2; }
    puts("PASS ptrace-context adapter parity64");return 0;
}
