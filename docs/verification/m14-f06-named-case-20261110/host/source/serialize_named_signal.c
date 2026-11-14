/* HOST serializer unit only. The renamed guest main is never called. */
#define main native_guest_main_not_called_by_this_unit
#include "/home/holden/mckernel-work/m14-blocker-resolution-20261110/f06-default-promotion-1/native-request-1/named-case-binding-1/candidate/scripts/application-tests/native_diagnostic_guest_collector.c"
#undef main

int main(void)
{
    struct result value = {0};
    char output[FRAME_LIMIT];
    value.clean = 1;
    value.started = 11;
    value.reaped = 22;
    value.finished = 33;
    value.out.eof = value.err.eof = 1;
    value.out.eof_ns = value.err.eof_ns = 23;
    int size = frame(output, &value, 1);
    if (size < 0) return 1;
    return fwrite(output, 1, (size_t)size, stdout) == (size_t)size ? 0 : 1;
}
