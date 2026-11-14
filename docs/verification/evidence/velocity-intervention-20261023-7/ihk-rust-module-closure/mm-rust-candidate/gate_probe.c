/* SPDX-License-Identifier: GPL-2.0 */
/* Test-only: raw-HACK jump versus objtool-converted default-false gate. */
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
_Alignas(8) unsigned char __tracepoint_mmap_lock_start_locking[64];
_Alignas(8) unsigned char __tracepoint_mmap_lock_acquire_returned[64];
_Alignas(8) unsigned char __tracepoint_mmap_lock_released[64];
extern bool m15_mmap_trace_start_enabled(void);
extern bool m15_mmap_trace_acquire_enabled(void);
extern bool m15_mmap_trace_release_enabled(void);
int main(int argc,char **argv)
{
    if (argc!=2 || (argv[1][0]!='0' && argv[1][0]!='1') || argv[1][1]) return 2;
    bool expected=argv[1][0]=='1';
    bool a=m15_mmap_trace_start_enabled();
    bool b=m15_mmap_trace_acquire_enabled();
    bool c=m15_mmap_trace_release_enabled();
    printf("GATES=%u%u%u\n",(unsigned)a,(unsigned)b,(unsigned)c);
    return (a==expected && b==expected && c==expected) ? 0 : 1;
}
