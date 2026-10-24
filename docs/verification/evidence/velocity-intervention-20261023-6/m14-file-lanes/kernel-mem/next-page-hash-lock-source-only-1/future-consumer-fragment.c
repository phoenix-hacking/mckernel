/* Functional OS/Rust only; no security testing. Future source fragment only,
 * not executable-ready. Link the actual Rust spinlock_helpers providers. */
#include "../two-VM-fixture-preparation-1/fixture/actual_kernel_declarations.h"
extern unsigned long page_hash_lock_bridge(unsigned long);
extern void page_hash_unlock_bridge(unsigned long,unsigned long);
extern void page_hash_lock_init_bridge(unsigned long);
static unsigned long original_page_hash_lock_bridge(unsigned long address){return ihk_mc_spinlock_lock((ihk_spinlock_t*)address);}
static void original_page_hash_unlock_bridge(unsigned long address,unsigned long flags){ihk_mc_spinlock_unlock((ihk_spinlock_t*)address,flags);}
static void original_page_hash_lock_init_bridge(unsigned long address){ihk_mc_spinlock_init((ihk_spinlock_t*)address);}
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
/* Future real driver enumerates flags {0,0x200,~0UL} and tickets {0,65534,65535}.
 * No host IRQ instruction, native mapping, allocated-page lifetime or unmap
 * completion is claimed. This file has no main/compiler command and is not a
 * second executable cohort. */
