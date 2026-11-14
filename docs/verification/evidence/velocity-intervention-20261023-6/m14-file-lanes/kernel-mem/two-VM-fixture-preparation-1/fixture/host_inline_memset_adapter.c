/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * HOST FIXTURE PRIMITIVE ONLY: kernel headers map the recorder's two scratch-array
 * memset calls to this ABI. Delegate byte filling to the already linked host libc.
 * This does not model TLB behavior or change any product callback or assertion.
 */
extern void *memset(void *dest, int byte, __SIZE_TYPE__ count);
_Static_assert(sizeof(unsigned long) == 8 && sizeof(__SIZE_TYPE__) == 8,
               "selected x86_64 kernel size_t/unsigned-long ABI");
void *__inline_memset(void *dest, unsigned long byte, __SIZE_TYPE__ count)
{
    return memset(dest, (unsigned char)byte, count);
}
