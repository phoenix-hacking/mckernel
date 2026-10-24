/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * FUTURE fixture scaffold fragment only; no execution/second ready cohort.
 * Include actual kernel headers, the exact original C body (rename only), and
 * the proposed Rust callback; use a controlled kmalloc_tracked boundary that
 * records exact size/int narrowing, unsigned-long flag, file pointer/content,
 * line and invocation count, then returns the selected pointer unchanged.
 *
 * Required size inputs: 0,1,sizeof(struct page),INT_MAX,INT_MAX+1UL,
 * UINT_MAX,UINT_MAX+1UL,ULONG_MAX. Required flag inputs: INT_MIN,-1,0,
 * IHK_MC_AP_CRITICAL,IHK_MC_AP_NOWAIT,INT_MAX. Return inputs: NULL and
 * distinct live aligned Page pointers; never dereference a failed allocation.
 * Check exactly one tracked call and exact returned pointer, with no free,
 * callback retry, page initialization, hash insertion or Page ownership action.
 *
 * Original body diagnostics are its real __FILE__/__LINE__. Proposed body
 * diagnostics are descriptor values captured by C at the replaced callsite.
 * Compare exact observed bytes/pointer/line against each actual C origin, and
 * compare original-vs-Rust argument/return behavior. DO NOT assert historic
 * binary line numbers immutable; do not #line/pad or use Rust file!/line!.
 * Descriptor/source-line change is explicit and separately reviewable.
 *
 * Real-header ABI witnesses: unsignedlong size, int flag, structpage* return;
 * kmalloc_tracked(int,ihk_mc_ap_flag,char*,int) and ihk_mc_ap_flag==unsignedlong.
 * Selected/fallback C bodies and allocated metadata references require later
 * fullmemTU/fullRust/partial proof; no allocator internals accepted by this
 * controlled boundary fixture. Actual production kmalloc_tracked is reused.
 */
