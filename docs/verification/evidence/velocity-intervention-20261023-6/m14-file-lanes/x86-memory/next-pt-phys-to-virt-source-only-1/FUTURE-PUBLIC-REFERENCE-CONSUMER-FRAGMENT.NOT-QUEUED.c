/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source fragment only, not a second executable queue. Link the actual existing
 * Rust phys_to_virt; state_samples belongs to the fixture's recorded, synchronous
 * x86_addr_init_pt_loaded_bridge callback. Run separately for both state values.
 */
#include <assert.h>
extern void *phys_to_virt(unsigned long);
extern void *x86_pt_phys_to_virt_bridge(unsigned long);
static void *original_x86_pt_phys_to_virt_bridge(unsigned long phys)
{
	return phys_to_virt(phys);
}
static void future_public_provider_case(unsigned long physical,
                                       volatile unsigned long *state_samples)
{
    unsigned long before = *state_samples;
    void *original = original_x86_pt_phys_to_virt_bridge(physical);
    assert(*state_samples == before + 1);
    void *actual = x86_pt_phys_to_virt_bridge(physical);
    assert(*state_samples == before + 2);
    assert(original == actual);
}
/* Real fallback translation, wrapping boundary geometry, full header and unique
 * selected provider/partial-link checks remain separately needed. This fragment
 * checks the retired PUBLIC C wrapper against the same existing Rust translator.
 */
