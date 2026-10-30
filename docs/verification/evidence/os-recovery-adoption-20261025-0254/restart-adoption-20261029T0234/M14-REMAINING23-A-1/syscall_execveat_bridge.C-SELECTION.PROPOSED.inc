/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * The exact source selection is bridge-selection-frozen119.patch. Bridge-enabled
 * original do_execveat changes static linkage to external without altering its C
 * body; its Rust successor must export the same do_execveat symbol. Rust bridge
 * replaces the selected C bridge only. Both #line restorations preserve the
 * frozen logical source positions. The compositor owns integration/rebasing. */
