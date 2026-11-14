/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Source fragment only: no main/driver/cohort. Existing production provider
 * implementations remain unchanged. These controlled endpoint functions never
 * acquire a real lock or change IRQ flags. Original C bodies are included with
 * original_* names and compared against the exact actual extracted Rust bodies.
 */
static unsigned long returned_flags, observed_flags;
static unsigned int lock_calls, unlock_calls;
unsigned long kprintf_lock(void){++lock_calls;return returned_flags;}
void kprintf_unlock(unsigned long flags){++unlock_calls;observed_flags=flags;}
/* Future matrix: 0/1/IFbit9/bit31/bit32/bit63/~0 plus alternating flags.
 * Require lock exactly once, full64 return equality; unlock exactly once with
 * full64 flags, no extra lock call. Compare original and Rust calls individually
 * and across the same lock/log/unlock outer sequence; retain lock ownership and
 * IRQ span, no runtime spinlock/IRQ/native claim. Real-header TU must assert
 * void(unsigned long) and unsigned long(void) against actual ihk/debug.h.
 */
