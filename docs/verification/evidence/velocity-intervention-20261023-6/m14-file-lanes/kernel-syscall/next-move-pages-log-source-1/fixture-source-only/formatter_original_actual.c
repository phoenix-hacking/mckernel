/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * SOURCE ONLY. Original C body versus exact new Rust entry; external logging controlled.
 * Hosted vsnprintf observes the varargs boundary; this does not execute kernel kprintf.
 */
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include <stdint.h>
#include <assert.h>
static char capture[512];
static int calls;
int kprintf(const char *format, ...) {
    va_list args;
    va_start(args, format);
    int result = vsnprintf(capture, sizeof(capture), format, args);
    va_end(args);
    assert(result >= 0 && (unsigned int)result < sizeof(capture));
    ++calls;
    return result;
}
#define MOVE_PAGES_LOG_UNSUPPORTED_PID 1
#define MOVE_PAGES_LOG_UNSUPPORTED_MOVE_ALL 2
#define MOVE_PAGES_LOG_INIT_MALLOC 3
#define MOVE_PAGES_LOG_INIT_VERIFY 4
#define MOVE_PAGES_LOG_PARALLEL 5
#define move_pages_log_bridge original_move_pages_log_bridge
#include "../move_pages_log.ORIGINAL-C.inc"
#undef move_pages_log_bridge
extern void move_pages_log_bridge(int, unsigned long, int);
_Static_assert(sizeof(int)==4 && sizeof(unsigned long)==8, "actual x86_64 ABI");
_Static_assert(__builtin_types_compatible_p(__typeof__(&move_pages_log_bridge),
    void (*)(int, unsigned long, int)), "export ABI");
int main(void) {
    const int events[] = {INT_MIN,-1,0,1,2,3,4,5,6,INT_MAX};
    const unsigned long values[] = {0,1,1UL<<63,ULONG_MAX};
    const int errors[] = {INT_MIN,0,INT_MAX};
    unsigned long pairs = 0;
    for (unsigned int i=0;i<sizeof(events)/sizeof(events[0]);++i)
      for (unsigned int j=0;j<sizeof(values)/sizeof(values[0]);++j)
        for (unsigned int k=0;k<sizeof(errors)/sizeof(errors[0]);++k) {
          char expected[sizeof(capture)];
          capture[0]=0; calls=0;
          original_move_pages_log_bridge(events[i],values[j],errors[k]);
          int expected_calls=calls;
          memcpy(expected,capture,sizeof(capture));
          capture[0]=0;calls=0;
          move_pages_log_bridge(events[i],values[j],errors[k]);
          assert(calls==expected_calls && strcmp(capture,expected)==0);
          assert(calls==((events[i]>=1 && events[i]<=5)?1:0));
          ++pairs;
        }
    assert(pairs==120);
    puts("PASS_CONTROLLED_FORMATTER_120_PAIRS");
    return 0;
}
