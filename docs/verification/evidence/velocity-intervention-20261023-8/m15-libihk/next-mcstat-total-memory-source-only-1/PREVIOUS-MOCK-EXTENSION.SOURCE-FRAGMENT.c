/* Functional OS/apps and Rust migration only; no security testing.
 * Append inside previous mcstat equivalence source TU, not a new runtime provider.
 * Prevent last negative OS-open vector leaking into subsequent total-memory tests. */
void mcstat_fragment_set_os_open_success(void) {
 scenario=(typeof(scenario)){0,0,0,0,0};ne=0;errno=0;
}
