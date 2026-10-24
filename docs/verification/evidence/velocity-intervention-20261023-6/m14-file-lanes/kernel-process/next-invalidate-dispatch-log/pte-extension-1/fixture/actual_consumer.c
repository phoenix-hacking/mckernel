/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * The unchanged Rust invalidate_one_page entry passes these function pointers
 * directly to its existing owner. This witness exposes their exact C ABI. */
#include <process.h>
extern void process_pte_make_fileoff_bridge(long,size_t,void *);
extern void process_pte_xchg_bridge(void *,void *);
void (*const actual_encode_consumer)(long,size_t,void *)=process_pte_make_fileoff_bridge;
void (*const actual_exchange_consumer)(void *,void *)=process_pte_xchg_bridge;
