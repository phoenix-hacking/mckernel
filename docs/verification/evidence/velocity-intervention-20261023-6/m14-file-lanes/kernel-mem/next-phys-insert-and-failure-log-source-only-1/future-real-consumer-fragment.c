/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Future actual-body consumer fragment only; no main/driver/second queue.
 * Actual full Rust helper/orchestrator runs; allocator and IRQ endpoints are
 * controlled. Hosted real vsnprintf formatting is required for log comparison.
 */
#include "/home/holden/mckernel-work/host-preparation/velocity-intervention-20261023-6/m14-file-lanes/kernel-mem/two-VM-fixture-preparation-1/fixture/actual_kernel_declarations.h"
typedef struct page *(*physical_inserter)(uint64_t);
struct insert_snapshot {unsigned allocations;unsigned logs;unsigned event_count;unsigned char event_bytes[64];};
/* Future controller records exactalloc80/critical1 and provider sequence. It
 * keeps Page storage live for both calls and compares fresh identical hash,
 * locks, existing Page and candidate allocation initial bytes. No fake ACK.
 */
static int phys_insert_actual_result(struct page *returned,struct page *expected,
 uint64_t physical,int newly_allocated,const struct insert_snapshot *s,
 unsigned allocations,unsigned logs)
{
 if(returned!=expected||s->allocations!=allocations||s->logs!=logs)return 1;
 if(returned&&newly_allocated){
  if(returned->phys!=physical||returned->mode||returned->count.counter||
     returned->list.next!=&returned->list||returned->list.prev!=&returned->list)return 2;
  if(returned->hash.next->prev!=&returned->hash||returned->hash.prev->next!=&returned->hash)return 3;
 }
 return 0;
}
/* Vectors: emptybucket+allocNULL (onealloc/unlockbeforeonelog), emptybucket+
 * allocatedPage(count0/phys/mode/list/hash; offset/mapped/pgshift retained),
 * existingexactphys(oneborrowedreturn,noalloc/nolog/noincrement), collisions
 * preservingchainorder, phys0/PAGESIZE-1/PAGESIZE/PAGESIZE+1/UINT64_MAX and
 * first/middle/lastbuckets. RepeatnewPage lookupmustreturnexistingPagewithout
 * anotheralloc. NULLlogger eventbytes mustbeexact
 * "phys_to_page_insert_hash: error allocating page\n". Loggerphysargument is
 * ignored for0/max; realvarargs%s reads exactliteral, no Rustfile!/line!.
 * Lock->lookup->[alloc->insert]->unlock->log(NULLonly)->return ordering and
 * savedIRQ/preempt balance are strict. Existingcaller aloneincrementscount.
 */
