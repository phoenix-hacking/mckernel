/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
int log_count;
void kprintf(const char *fmt, ...) { (void)fmt; ++log_count; }
