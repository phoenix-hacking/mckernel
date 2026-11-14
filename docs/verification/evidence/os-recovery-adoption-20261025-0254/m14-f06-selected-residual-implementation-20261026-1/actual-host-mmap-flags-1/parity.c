/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Exact original-C and public-provider masks; no mmap/syscall effect occurs.
 */
#include <mman.h>
extern int puts(const char *);
_Static_assert(sizeof(int)==4, "C int width");
_Static_assert(MAP_32BIT==0x40 && MAP_GROWSDOWN==0x100, "map constants1");
_Static_assert(MAP_DENYWRITE==0x800 && MAP_EXECUTABLE==0x1000, "map constants2");
_Static_assert(MAP_NORESERVE==0x4000 && MAP_NONBLOCK==0x10000, "map constants3");
_Static_assert(MAP_STACK==0x20000 && MAP_HUGE_SHIFT==26, "map constants4");
#ifdef USE_NOCACHE_MMAP
#error exact retained selected configuration requires USE_NOCACHE_MMAP undefined
#endif
#define arch_mmap_supported_flags_bridge original_supported
#define arch_mmap_ignored_flags_bridge original_ignored
#define arch_mmap_error_flags_bridge original_error
#include "original-flags.inc"
#undef arch_mmap_supported_flags_bridge
#undef arch_mmap_ignored_flags_bridge
#undef arch_mmap_error_flags_bridge
extern int arch_mmap_supported_flags_bridge(void);
extern int arch_mmap_ignored_flags_bridge(void);
extern int arch_mmap_error_flags_bridge(void);
static int (* const providers[3])(void)={arch_mmap_supported_flags_bridge,
    arch_mmap_ignored_flags_bridge,arch_mmap_error_flags_bridge};
static int (* const originals[3])(void)={original_supported,original_ignored,original_error};
int main(void)
{
    unsigned int expected[3],actual[3],i,flags,case_index;
    const unsigned int extra[4]={0,0xffffffffU,0xfc000000U,0xdeadbeefU};
    for(i=0;i<3;i++) {
        expected[i]=(unsigned int)originals[i]();
        actual[i]=(unsigned int)providers[i]();
        if(expected[i]!=actual[i]) { puts("FAIL mmap flag mask parity");return 1; }
    }
    for(case_index=0;case_index<36;case_index++) {
        flags=case_index<32 ? (1U<<case_index) : extra[case_index-32];
        if((flags&expected[2])!=(flags&actual[2])
           ||(flags&~(expected[0]|expected[1]))!=(flags&~(actual[0]|actual[1]))) {
            puts("FAIL mmap flag classification parity");return 2;
        }
    }
    puts("PASS mmap flags original-C/provider parity masks3 classification36 ABI3");
    return 0;
}
