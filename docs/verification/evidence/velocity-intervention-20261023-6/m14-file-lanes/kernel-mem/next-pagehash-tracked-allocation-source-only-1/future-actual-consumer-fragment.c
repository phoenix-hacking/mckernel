/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Actual future boundary-consumer code, intentionally no main/driver/commands.
 * Provider below is fixture-only; production still uses existing Rust allocator.
 */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/two-VM-fixture-preparation-1/fixture/actual_kernel_declarations.h"
struct allocation_observation {int size;ihk_mc_ap_flag flag;char *file;int line;unsigned calls;};
static struct allocation_observation observed;
static void *controlled_allocation_return;
void *kmalloc_tracked(int size,ihk_mc_ap_flag flag,char *file,int line)
{
 observed.size=size;observed.flag=flag;observed.file=file;observed.line=line;observed.calls++;
 return controlled_allocation_return;
}
typedef struct page *(*page_alloc_callback)(unsigned long,int);
/* Original and Rust callbacks are actual extracted bodies, not reimplementations.
 * Expected origins are supplied by a source-bound future driver from real C
 * preprocessing metadata; no guessed productionline/#line/padding is used. */
static int page_alloc_actual_pair(page_alloc_callback original,page_alloc_callback replacement,
 unsigned long size,int flag,struct page *result,
 const char *original_file,int original_line,const char *replacement_file,int replacement_line)
{
 struct allocation_observation first;
 memset(&observed,0,sizeof observed);controlled_allocation_return=result;
 struct page *a=original(size,flag);first=observed;
 memset(&observed,0,sizeof observed);
 struct page *b=replacement(size,flag);
 return a!=result||b!=result||first.calls!=1||observed.calls!=1||
 first.size!=(int)size||observed.size!=first.size||
 first.flag!=(ihk_mc_ap_flag)flag||observed.flag!=first.flag||
 strcmp(first.file,original_file)||first.line!=original_line||
 strcmp(observed.file,replacement_file)||observed.line!=replacement_line||
 observed.file!=replacement_file;
}
