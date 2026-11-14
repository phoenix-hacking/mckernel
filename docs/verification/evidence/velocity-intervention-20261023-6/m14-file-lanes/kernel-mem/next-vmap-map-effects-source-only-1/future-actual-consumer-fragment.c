/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Future real4-body consumer fragment, no main/driver/secondqueue. Set/clear/
 * TLB privileged effects are controlled publicprovider boundaries. Barrier
 * MUST execute the actual safe existing Rust empty-asm arch_barrier; never
 * replace C barrier with a fabricated observable endpoint just to force parity.
 */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/two-VM-fixture-preparation-1/fixture/actual_kernel_declarations.h"
struct effect_call{unsigned count,kind;page_table_t pt;void *virt;unsigned long phys;enum ihk_mc_pt_attribute attr;};
static struct effect_call effect;static int provider_result;
int ihk_mc_pt_set_page(page_table_t pt,void *virt,unsigned long phys,enum ihk_mc_pt_attribute attr){effect.count++;effect.kind=1;effect.pt=pt;effect.virt=virt;effect.phys=phys;effect.attr=attr;return provider_result;}
int ihk_mc_pt_clear_page(page_table_t pt,void *virt){effect.count++;effect.kind=2;effect.pt=pt;effect.virt=virt;return provider_result;}
void flush_tlb_single(unsigned long addr){effect.count++;effect.kind=3;effect.phys=addr;}
typedef int(*set_cb)(page_table_t,void*,unsigned long,enum ihk_mc_pt_attribute);
typedef int(*clear_cb)(page_table_t,void*);
typedef void(*flush_cb)(unsigned long);
typedef void(*barrier_cb)(void);
static int set_actual_pair(set_cb a,set_cb b,page_table_t pt,void *virt,unsigned long phys,enum ihk_mc_pt_attribute attr,int result){struct effect_call first;provider_result=result;memset(&effect,0,sizeof effect);int x=a(pt,virt,phys,attr);memcpy(&first,&effect,sizeof first);memset(&effect,0,sizeof effect);int y=b(pt,virt,phys,attr);return x!=result||x!=y||effect.count!=1||memcmp(&first,&effect,sizeof effect);}
static int clear_actual_pair(clear_cb a,clear_cb b,page_table_t pt,void *virt,int result){struct effect_call first;provider_result=result;memset(&effect,0,sizeof effect);int x=a(pt,virt);memcpy(&first,&effect,sizeof first);memset(&effect,0,sizeof effect);int y=b(pt,virt);return x!=result||x!=y||effect.count!=1||memcmp(&first,&effect,sizeof effect);}
static int flush_actual_pair(flush_cb a,flush_cb b,unsigned long addr){struct effect_call first;memset(&effect,0,sizeof effect);a(addr);memcpy(&first,&effect,sizeof first);memset(&effect,0,sizeof effect);b(addr);return effect.count!=1||memcmp(&first,&effect,sizeof effect);}
static int barrier_actual_pair(barrier_cb a,barrier_cb b,unsigned char *memory,unsigned long n,unsigned char *before){memcpy(before,memory,n);memset(&effect,0,sizeof effect);a();if(effect.count||memcmp(before,memory,n))return 1;b();return effect.count||memcmp(before,memory,n);}
/* Requiredsetvectors preserveNULL/liveopaquePT, unaligned/arbitraryvirt/phys,
 * all64attribute bits includingNO_EXECUTEbit63/zero/allones, exactsignedint
 * negative/zero/positive returns. Clearvalues/errorresults unchanged. Flush
 * addresses0/boundaries/ULONGMAX passedonce tocontrolledendpoint, nohostinvlpg.
 * RealheaderABIs require enumattribute8B/pt-pointer/unsignedlong64 and exact
 * functiontypes. Source/codegen witnesses bind Ccompiler-gcc.h barrier macro
 * emptyvolatileasm+memoryclobber and actualRustarch_barrieremptyasm with
 * defaultmemoryeffects(no nomem); no thread/native/hardware-fence claim.
 * Existingactualmem_map_virtual_body_result/rollback consumer shouldthenuse
 * actualold/newcallbacks: successset/flushorder andbarrierafterlastflush;
 * errorsclear/freepreviousmappings andnobarrier, unchangedreturnoffsets.
 */
