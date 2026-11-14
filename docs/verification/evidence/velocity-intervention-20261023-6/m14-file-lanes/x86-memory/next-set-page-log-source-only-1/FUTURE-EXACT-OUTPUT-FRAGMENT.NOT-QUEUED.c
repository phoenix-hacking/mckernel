/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Original C/Rust callback output comparison with a controlled host formatter;
 * no page-table locking, real EBUSY trigger, or native formatter claim.
 */
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
static unsigned log_calls;
static char log_text[128];
static int formatter_result;
int kprintf(const char *format,...)
{
    va_list ap;va_start(ap,format);++log_calls;
    int n=vsnprintf(log_text,sizeof(log_text),format,ap);va_end(ap);
    assert(n>=0 && (unsigned)n<sizeof(log_text));return formatter_result;
}
static void future_set_page_log_case(void (*original)(unsigned long),
                                     void (*rust)(unsigned long),unsigned long virt)
{
    unsigned before=log_calls;original(virt);char expected[128];strcpy(expected,log_text);
    assert(log_calls==before+1);rust(virt);
    assert(log_calls==before+2 && strcmp(log_text,expected)==0);
}
/* Values0,1,0x123456789abcdef0,1UL<<63,ULONG_MAX and formatter returns-7/0/17.
 * Use exact saved C and Rust bodies. Actual C allocated relocation from the
 * existing __set_pt_page callback argument to Rust must be observed later;
 * syntax/source relation alone does not prove default selection/link/native.
 */
