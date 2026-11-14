/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/two-VM-fixture-preparation-1/fixture/actual_kernel_declarations.h"
extern unsigned long page_hash_lock_bridge(unsigned long);
extern void page_hash_unlock_bridge(unsigned long,unsigned long);
extern void page_hash_lock_init_bridge(unsigned long);
extern long page_get_offset(const struct page *);
#include "actual-original-three-lock-providers.inc"
struct page_lock_event{unsigned long code,flags;};
static struct page_lock_event page_events[4],saved_events[4];
static unsigned page_event_count;static unsigned long page_controlled_flags;
static ihk_spinlock_t *page_observed_lock;static unsigned short page_expected_head;
static int page_provider_error;
static void page_event(unsigned long code,unsigned long flags){if(page_event_count>=4){page_provider_error=1;return;}page_events[page_event_count++]=(struct page_lock_event){code,flags};}
unsigned long cpu_disable_interrupt_save(void){page_event(1,page_controlled_flags);return page_controlled_flags;}
void preempt_disable(void){page_event(2,0);}
void preempt_enable(void){if(page_observed_lock->tickets.head!=page_expected_head)page_provider_error=1;page_event(3,0);}
void cpu_restore_interrupt(unsigned long flags){if(flags!=page_controlled_flags)page_provider_error=1;page_event(4,flags);}
void cpu_pause(void){page_provider_error=1;} /* This finite fragment uses head==tail; busy-wait is not fabricated. */
static void page_reset_events(ihk_spinlock_t *lock,unsigned short head,unsigned long flags){page_event_count=page_provider_error=0;memset(page_events,0,sizeof page_events);page_observed_lock=lock;page_expected_head=head;page_controlled_flags=flags;}
static int page_hash_actual_provider_pair(unsigned short initial_ticket,unsigned long flags){
 ihk_spinlock_t original,replacement;original.head_tail=replacement.head_tail=~0U;
 original_page_hash_lock_init_bridge((unsigned long)&original);page_hash_lock_init_bridge((unsigned long)&replacement);
 if(original.head_tail||replacement.head_tail)return 1;
 original.head_tail=replacement.head_tail=(unsigned)initial_ticket|((unsigned)initial_ticket<<16);
 unsigned short expected=(unsigned short)(initial_ticket+2);
 page_reset_events(&original,expected,flags);unsigned long a=original_page_hash_lock_bridge((unsigned long)&original);
 original_page_hash_unlock_bridge((unsigned long)&original,a);unsigned count=page_event_count;int error=page_provider_error;memcpy(saved_events,page_events,sizeof page_events);
 page_reset_events(&replacement,expected,flags);unsigned long b=page_hash_lock_bridge((unsigned long)&replacement);
 page_hash_unlock_bridge((unsigned long)&replacement,b);
 return error||page_provider_error||a!=flags||a!=b||count!=4||page_event_count!=4||memcmp(saved_events,page_events,sizeof page_events)||original.head_tail!=replacement.head_tail||replacement.tickets.head!=expected||replacement.tickets.tail!=expected||page_events[0].code!=1||page_events[1].code!=2||page_events[2].code!=3||page_events[3].code!=4;
}

static long original_process_page_offset_bridge(void *page) { return ((struct page *)page)->offset; }
_Static_assert(sizeof(struct page)==80 && _Alignof(struct page)==8,"actualPage80align8");
_Static_assert(__builtin_offsetof(struct page,offset)==64,"actualPageoffset64");
_Static_assert(sizeof(((struct page*)0)->offset)==sizeof(long),"actualOffTlongwidth");
static int offset_pair(long value,unsigned which) {
 struct page pages[3],before[3];memset(pages,0xa5,sizeof pages);pages[which].offset=value;memcpy(before,pages,sizeof pages);
 long a=original_process_page_offset_bridge(&pages[which]);long b=page_get_offset(&pages[which]);
 return a!=value||a!=b||memcmp(before,pages,sizeof pages);
}
int main(void) {
 const unsigned short tickets[]={0,2,32766,65532,65534,65535};
 const unsigned long flags[]={0,0x200,0x246,~0UL};
 const long offsets[]={(-9223372036854775807L-1),-4096,-1,0,1,4095,4096,9223372036854775807L};
 unsigned locks=0,offsets_tested=0;
 for(unsigned i=0;i<sizeof(tickets)/sizeof(tickets[0]);i++)for(unsigned j=0;j<sizeof(flags)/sizeof(flags[0]);j++){if(page_hash_actual_provider_pair(tickets[i],flags[j]))return 11;locks++;}
 for(unsigned i=0;i<sizeof(offsets)/sizeof(offsets[0]);i++)for(unsigned j=0;j<3;j++){if(offset_pair(offsets[i],j))return 12;offsets_tested++;}
 __builtin_printf("PASS actualOriginalC_Rust pagehash=%u offset=%u total=%u\n",locks,offsets_tested,locks+offsets_tested);return 0;
}
