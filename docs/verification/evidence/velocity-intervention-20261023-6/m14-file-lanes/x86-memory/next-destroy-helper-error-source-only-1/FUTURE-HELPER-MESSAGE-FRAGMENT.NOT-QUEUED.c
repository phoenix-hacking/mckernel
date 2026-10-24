/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Endpoint records and returns according to its actual C declaration. It does
 * not test production panic termination, CPU stop, monitor publication or unwind.
 */
#include <assert.h>
#include <string.h>
static unsigned endpoint_calls;
static const char *endpoint_message;
void panic(const char *message) { ++endpoint_calls;endpoint_message=message; }
static void future_helper_message_case(void (*original)(void),void (*rust)(void))
{
    unsigned before=endpoint_calls;original();
    assert(endpoint_calls==before+1);
    assert(strcmp(endpoint_message,"destroy_page_table: helper failed")==0);
    const char *expected=endpoint_message;rust();
    assert(endpoint_calls==before+2 && strcmp(endpoint_message,expected)==0);
}
/* Use the exact saved original body and exact Rust body. Existing destroy
 * orchestration's ret!=0 branch must retain its same call position. This is a
 * source fragment only, not an extra driver or executable queue.
 */
