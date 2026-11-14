/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Runs only parser functions, never collector PID1, a guest, klogctl or root. */
#define main collector_pid1_main
#include "native_diagnostic_guest_collector.c"
#undef main
#include <stdlib.h>

static void expect(const char *name, const char *log, int wanted)
{
    int actual = native_retirement_state(log);
    if (actual != wanted) {
        fprintf(stderr, "%s: got %d expected %d\n", name, actual, wanted);
        exit(1);
    }
}
#define REG "mcctrl: application_process=registered os=0 generation=1 pid=254\n"
#define PHASE REG \
    "mcctrl: application_syscall=delivered os=0 generation=1 pid=254 worker=6 delivery=512 cpu=0 number=231\n" \
    "mcctrl: application_process=cleanup_requested os=0 generation=1 pid=254 intent_errno=0\n" \
    "ihk: application cleanup ACK os=0 generation=1 pid=254 token=3 errno=0 abandoned=1\n"
#define AGAIN "ihk: application retirement os=0 generation=1 pid=254 token=513 errno=-11\n"
#define DONE "ihk: application retirement os=0 generation=1 pid=254 token=514 errno=0\n"
int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    expect("no query is pending", PHASE, 0);
    expect("EAGAIN is pending", PHASE AGAIN, 0);
    expect("genuine retry success", PHASE AGAIN DONE, 1);
    expect("immediate genuine success", PHASE DONE, 1);
    expect("foreign PID cannot complete", PHASE AGAIN
           "ihk: application retirement os=0 generation=1 pid=255 token=514 errno=0\n", 0);
    expect("foreign generation cannot complete", PHASE AGAIN
           "ihk: application retirement os=0 generation=2 pid=254 token=514 errno=0\n", 0);
    expect("real error is failure", PHASE AGAIN
           "ihk: application retirement os=0 generation=1 pid=254 token=514 errno=-5\n", -1);
    expect("duplicate success is failure", PHASE DONE DONE, -1);
    expect("query after success is failure", PHASE DONE AGAIN, -1);
    expect("zero token is failure", PHASE
           "ihk: application retirement os=0 generation=1 pid=254 token=0 errno=0\n", -1);
    expect("malformed row is failure", PHASE
           "ihk: application retirement os=0 generation=1 pid=254 token=x errno=0\n", -1);
    expect("incomplete snapshot is failure", PHASE "unterminated", -1);
    expect("missing registration is failure", DONE, -1);
    expect("duplicate registration is failure", REG PHASE DONE, -1);
    expect("missing terminal cannot retire", REG
           "ihk: application cleanup ACK os=0 generation=1 pid=254 token=3 errno=0 abandoned=1\n" DONE, -1);
    expect("missing ACK cannot retire", REG
           "mcctrl: application_syscall=delivered os=0 generation=1 pid=254 worker=6 delivery=512 cpu=0 number=231\n" DONE, -1);
    expect("intent alone is pending", REG
           "mcctrl: application_process=cleanup_requested os=0 generation=1 pid=254 intent_errno=0\n", 0);
    expect("reused query token is failure", PHASE AGAIN
           "ihk: application retirement os=0 generation=1 pid=254 token=513 errno=0\n", -1);
    expect("foreign ACK cannot authorize", REG
           "mcctrl: application_syscall=delivered os=0 generation=1 pid=254 worker=6 delivery=512 cpu=0 number=231\n"
           "mcctrl: application_process=cleanup_requested os=0 generation=1 pid=254 intent_errno=0\n"
           "ihk: application cleanup ACK os=0 generation=1 pid=255 token=3 errno=0 abandoned=1\n" DONE, -1);
    expect("ACK alone cannot complete", PHASE, 0);
    expect("ambiguous registration is failure", PHASE
           "mcctrl: application_process=registered os=0 generation=1 pid=255\n" DONE, -1);
    FILE *file = fopen(argv[1], "rb");
    if (!file) return 3;
    char *saved = malloc(1024 * 1024);
    if (!saved) return 4;
    size_t count = fread(saved, 1, 1024 * 1024 - 1, file);
    if (ferror(file) || !feof(file) || fclose(file)) return 5;
    size_t kept = 0;
    for (size_t i = 0; i < count; ++i) if (saved[i] != '\r') saved[kept++] = saved[i];
    saved[kept] = 0;
    expect("saved real EAGAIN-only trace stays pending", saved, 0);
    free(saved);
    puts("PASS 22 collector retirement parser controls; no guest or kernel action");
    return 0;
}
