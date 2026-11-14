/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Future actual wrapper+existing-init-consumer fragment only; no main/driver.
 * Pair actual original C callbacks against new Rust adapters; actual retained
 * mem_virtual_allocator_init_body_result executes, provider boundary controlled.
 */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/two-VM-fixture-preparation-1/fixture/actual_kernel_declarations.h"
typedef int(*prepare_cb)(page_table_t,void*,unsigned long,enum ihk_mc_pt_prepare_flag);
struct prepare_call{unsigned calls;page_table_t pt;void *virt;unsigned long size;enum ihk_mc_pt_prepare_flag flag;};
static struct prepare_call seen;static int provider_result;
int ihk_mc_pt_prepare_map(page_table_t pt,void *virt,unsigned long size,enum ihk_mc_pt_prepare_flag flag){seen.calls++;seen.pt=pt;seen.virt=virt;seen.size=size;seen.flag=flag;return provider_result;}
static int prepare_actual_pair(prepare_cb original,prepare_cb replacement,page_table_t pt,void *virt,unsigned long size,enum ihk_mc_pt_prepare_flag flag,int result){struct prepare_call saved;provider_result=result;memset(&seen,0,sizeof seen);int a=original(pt,virt,size,flag);saved=seen;memset(&seen,0,sizeof seen);int b=replacement(pt,virt,size,flag);return a!=result||a!=b||saved.calls!=1||seen.calls!=1||memcmp(&saved,&seen,sizeof seen);}
/* ABI: use actual page_table_t pointer and enum declaration from ihk/mm.h;
 * require sizeof(enum)==sizeof(int) and direct actual C function-type witness.
 * Inputs NULL/liveopaquePT, arbitrarypointervirt (neverdereferenced byadapter),
 * size0/PAGESIZE/ULONGMAX, FIRST_LEVEL/LAST_LEVEL and exact32-bit cast patterns;
 * outputsINTMIN/-EINVAL/-1/0/1/INTMAX forwarded unchanged once.
 *
 * Integration extension uses actual existing Rust
 * mem_virtual_allocator_init_body_result(&slot,start,size,unit,first,init,prep)
 * with originalcallbacks vs newcallbacks. Strict trace: allocator-init once,
 * store exactreturneddescriptor (includingNULL) into slot BEFORE prepare,
 * prepare(NULL,(void*)start,size,first) once. Return samepreparestatus; outer
 * original C virtual_allocator_init continues to discard it unchanged.
 * No fake PT allocation/mapping acknowledgement or allocator cleanup on error.
 * Existing fullRust+wholememTU actualallocatedcallback/partial is required for
 * binding public x86Rustprovider, not claimed by controlled provider fixture.
 */
