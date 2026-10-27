/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "genuine_prologue.inc"
#include "f06_rt_sigreturn_origin.h"
_Static_assert(sizeof(size_t)==8 && sizeof(int)==4 && sizeof(ihk_mc_ap_flag)==8, "tracked allocator ABI");
extern int puts(const char *);
static const char expected_origin[]=MCKERNEL_F06_RT_SIGRETURN_ORIGIN;
static unsigned int calls,metadata_error;
static void *seen_pointer;
static unsigned free_calls;
static int seen_size,expected_line;
static ihk_mc_ap_flag seen_flags;
static unsigned long result_bits;
static const char *expected_file;
static int same(const char *left,const char *right)
{
    if(!left || !right) return 0;
    while(*left && *left==*right) { ++left;++right; }
    return *left==*right;
}
void *kmalloc_tracked(int size,ihk_mc_ap_flag flags,char *file,int line)
{
    ++calls;seen_size=size;seen_flags=flags;
    if(!same(file,expected_file) || line!=expected_line) metadata_error=1;
    return (void *)result_bits;
}
void kfree_tracked(void *ptr,char *file,int line)
{
    ++free_calls;seen_pointer=ptr;
    if(!same(file,expected_file) || line!=expected_line) metadata_error=1;
}
#define arch_rt_sigreturn_free_bridge original_free_bridge
#define arch_rt_sigreturn_alloc_bridge original_alloc_bridge
#include "original_bridge.inc"
#undef arch_rt_sigreturn_alloc_bridge
#undef arch_rt_sigreturn_free_bridge
extern void arch_rt_sigreturn_free_bridge(void *);
extern void *arch_rt_sigreturn_alloc_bridge(size_t,unsigned long);
int main(void)
{
    const size_t sizes[]={0,1,0x7fffffffULL,0x80000000ULL,0xffffffffULL,0x100000000ULL,
        0x100000001ULL,0x7fffffffffffffffULL,0x8000000000000000ULL,0xffffffffffffffffULL,65535,65536,4096};
    const unsigned long words[]={0,1,0xffffffffUL,0x100000000UL,0x8000000000000000UL,
        0xffffffffffffffffUL,0x123456789abcdef0UL,0xaaaaaaaa55555555UL};
    unsigned int i,j,k,cases=0;
    for(i=0;i<13;i++) for(j=0;j<8;j++) for(k=0;k<8;k++) {
        unsigned int original_calls;
        int original_size;
        ihk_mc_ap_flag original_flags;
        unsigned long original_result,actual_result;
        result_bits=words[k];calls=0;metadata_error=0;
        expected_file=expected_origin;expected_line=385;
        original_result=(unsigned long)original_alloc_bridge(sizes[i],words[j]);
        if(metadata_error) { puts("FAIL C tracking provenance");return 3; }
        original_calls=calls;original_size=seen_size;original_flags=seen_flags;calls=0;metadata_error=0;
        expected_file=expected_origin;expected_line=385;
        actual_result=(unsigned long)arch_rt_sigreturn_alloc_bridge(sizes[i],words[j]);
        if(original_calls!=1 || calls!=1 || metadata_error || seen_size!=original_size || seen_size!=(int)sizes[i]
           || seen_flags!=original_flags || seen_flags!=words[j] || original_result!=actual_result || actual_result!=words[k]) {
            puts("FAIL signal-alloc adapter parity");return 1;
        }
        ++cases;
    }
    if(cases!=832) { puts("FAIL allocation cardinality");return 2; }
    for(i=0;i<8;i++) {
        void *original_pointer;
        expected_line=391;free_calls=0;metadata_error=0;
        original_free_bridge((void *)words[i]);
        if(free_calls!=1 || metadata_error) return 4;
        original_pointer=seen_pointer;free_calls=0;metadata_error=0;
        arch_rt_sigreturn_free_bridge((void *)words[i]);
        if(free_calls!=1 || metadata_error || seen_pointer!=original_pointer ||
           seen_pointer!=(void *)words[i]) return 5;
    }
    puts("PASS F06 alloc832/free8 original-C ABI and provenance");return 0;
}
