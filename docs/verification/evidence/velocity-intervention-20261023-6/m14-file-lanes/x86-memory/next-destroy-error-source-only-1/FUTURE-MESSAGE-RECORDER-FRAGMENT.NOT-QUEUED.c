/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Returning endpoint is permitted by the actual void C declaration. It tests
 * callback reason/message choice only, never real panic termination/unwinding.
 */
#include <assert.h>
#include <string.h>
static unsigned panic_calls;
static const char *panic_message;
void panic(const char *s) { ++panic_calls; panic_message=s; }
static void future_reason_case(void (*original)(int),void (*rust)(int),int reason)
{
    unsigned start=panic_calls; original(reason);
    unsigned count=panic_calls-start; const char *expected=panic_message;
    rust(reason); assert(panic_calls==start+2*count);
    if(count)assert(strcmp(panic_message,expected)==0);
    assert(count==(unsigned)(reason==1 || reason==2));
}
/* Reason vectors: INT_MIN,-1,0,1,2,3,INT_MAX. Both known messages are static
 * strings; unknown reasons perform no endpoint call. Use the exact original C
 * body and exact Rust callback body; no driver/second queue is prepared here.
 */
