#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
int main(void){const char *state="WAIT";const char *delivery="none";const char *kill="launcher-group";printf("worker_state=%s delivery=%s kill_target=%s cleanup=required\n",state,delivery,kill);return EXIT_SUCCESS;}
