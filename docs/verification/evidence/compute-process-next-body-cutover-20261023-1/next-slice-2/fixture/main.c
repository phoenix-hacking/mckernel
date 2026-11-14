/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing. */
#include <stdio.h>
#include <stdlib.h>
void fixture_fail(unsigned line) { fprintf(stderr,"fixture assertion line=%u\n",line);exit(1); }
unsigned long leaf_fixture_run(void);
int main(void) { unsigned long n=leaf_fixture_run();if(n!=37500)return 2;printf("PASS pairs=%lu actual_body_pairs=6250; real headers/types; mocked callbacks; no target state instructions\n",n);return 0; }
