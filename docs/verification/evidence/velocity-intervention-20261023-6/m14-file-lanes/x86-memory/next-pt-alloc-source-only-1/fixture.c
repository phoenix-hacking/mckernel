/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Controlled downstream allocator endpoint proves the wrapper, not allocation.
 */
#include <assert.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include "EXACT-REAL-HEADER-TYPE-CLOSURE.inc"
#define X86_MEMORY_PUBLIC_BRIDGE static
extern void *x86_pt_alloc_pages_bridge(int,int);
const char x86_pt_alloc_pages_file[] = __FILE__;
const int x86_pt_alloc_pages_line = 750;
const int x86_pt_alloc_pages_p2align = PAGE_P2ALIGN;
const int x86_pt_alloc_pages_is_user = IHK_MC_PG_KERNEL;
static struct observed { int pages,align; unsigned long flag; int node,user;
    uintptr_t virt; char *file; int line; } last;
static unsigned calls;
static void *backend_result;
void *_ihk_mc_alloc_aligned_pages_node(int n,int a,ihk_mc_ap_flag f,int node,
                                     int user,uintptr_t v,char *file,int line)
{
    ++calls; last=(struct observed){n,a,f,node,user,v,file,line}; return backend_result;
}
#line 748
X86_MEMORY_PUBLIC_BRIDGE void *original_x86_pt_alloc_pages_bridge(int nr_pages, int ap_flag)
{
	return _ihk_mc_alloc_aligned_pages_node(nr_pages, PAGE_P2ALIGN, (ihk_mc_ap_flag)ap_flag, -1, IHK_MC_PG_KERNEL, -1, __FILE__, __LINE__);
}
static unsigned char owned_by_observer[8192] __attribute__((aligned(4096)));
int main(void)
{
    static const int pages[]={INT_MIN,-2,-1,0,1,2,8,511,INT_MAX};
    static const int flags[]={INT_MIN,-65536,-2,-1,0,1,2,4,0x1000,0x30000,0x40000,INT_MAX,0x5a5a5a5a};
    void *results[]={NULL,owned_by_observer,owned_by_observer+4096,(void*)(uintptr_t)UINTPTR_MAX};
    unsigned pairs=0;
    for(unsigned i=0;i<sizeof(pages)/sizeof(pages[0]);++i)
      for(unsigned j=0;j<sizeof(flags)/sizeof(flags[0]);++j)
        for(unsigned k=0;k<sizeof(results)/sizeof(results[0]);++k) {
            backend_result=results[k]; unsigned before=calls;
            void *old=original_x86_pt_alloc_pages_bridge(pages[i],flags[j]);
            struct observed expected=last;
            assert(calls==before+1);
            void *actual=x86_pt_alloc_pages_bridge(pages[i],flags[j]);
            assert(calls==before+2 && actual==old && actual==backend_result);
            assert(last.pages==expected.pages && last.align==expected.align);
            assert(last.flag==expected.flag && last.node==expected.node && last.user==expected.user);
            assert(last.virt==expected.virt && strcmp(last.file,expected.file)==0 && last.line==expected.line);
            assert(last.pages==pages[i] && last.align==0 && last.flag==(ihk_mc_ap_flag)flags[j]);
            assert(last.node==-1 && last.user==0 && last.virt==UINTPTR_MAX && last.line==750);
            assert(last.file==x86_pt_alloc_pages_file); ++pairs;
        }
    assert(pairs==468);
    puts("PASS PT allocator wrapper:468 actual-original-C/Rust pairs; flags, trace, NULL/raw result; downstream controlled");
    return 0;
}
