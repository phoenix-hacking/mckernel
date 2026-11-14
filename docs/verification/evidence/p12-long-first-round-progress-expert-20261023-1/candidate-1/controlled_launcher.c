/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Linux-only controlled launch provider. This is not McKernel runtime proof. */
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include "pair_round_oracles.h"
int main(void) {
    const char *cpu=getenv("PAIR_CPU");
    if(!cpu || (strcmp(cpu,"0") && strcmp(cpu,"1")))return 91;
    usleep(100000);
    const unsigned char *b=!strcmp(cpu,"0")?pair_round_stdout_0:pair_round_stdout_1;
    size_t n=!strcmp(cpu,"0")?sizeof pair_round_stdout_0:sizeof pair_round_stdout_1;
    return write(1,b,n)==(ssize_t)n?0:92;
}
