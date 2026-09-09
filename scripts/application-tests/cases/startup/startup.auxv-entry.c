#define _GNU_SOURCE

#include <elf.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/auxv.h>

extern char etext;

int main(void) {
    unsigned long entry = getauxval(AT_ENTRY);
    unsigned long phdr = getauxval(AT_PHDR);
    unsigned long phnum = getauxval(AT_PHNUM);
    uintptr_t local_entry = (uintptr_t)&main;

    if (entry == 0 || phdr == 0 || phnum == 0) {
        return EXIT_FAILURE;
    }
    printf("at_entry=0x%lx\n", entry);
    printf("at_phdr=0x%lx\n", phdr);
    printf("at_phnum=%lu\n", phnum);
    printf("main_address=0x%" PRIxPTR "\n", local_entry);
    return EXIT_SUCCESS;
}
