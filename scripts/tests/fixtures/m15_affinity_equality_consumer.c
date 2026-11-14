#include <stddef.h>
#include <stdio.h>
#include <limits.h>

#if defined(__cpu_set_t_defined) || defined(_BITS_CPU_SET_H)
#error "The public IHK header must provide its own cpu_set_t branch"
#endif
#include <ihk/affinity.h>
#if !defined(__cpu_set_t_defined) || defined(_BITS_CPU_SET_H)
#error "The public IHK own-type branch was not selected"
#endif

_Static_assert(sizeof(cpu_set_t) > 2 * sizeof(__cpu_mask),
               "The actual IHK type must contain the tested two-word prefix");

static unsigned checks;
static unsigned failures;

static void check(int condition, const char *name)
{
    ++checks;
    if (!condition) {
        ++failures;
        fprintf(stderr, "FAIL: %s\n", name);
    }
}

int main(int argc, char **argv)
{
    cpu_set_t left, right;
    const size_t word = sizeof(__cpu_mask);
    const size_t boundary_cpu = word * CHAR_BIT;
    const size_t last_cpu = CPU_SETSIZE - 1;
    /* Keep a real runtime operand, with both possible values in the valid set. */
    const size_t first_cpu = (size_t)(argc > 1);
    (void)argv;

    CPU_ZERO(&left);
    CPU_ZERO(&right);
    check(CPU_EQUAL(&left, &right), "CPU_EQUAL empty sets");
    check(CPU_EQUAL_S(sizeof(left), &left, &right), "CPU_EQUAL_S empty sets");

    CPU_SET(first_cpu, &left);
    CPU_SET(boundary_cpu, &left);
    CPU_SET(last_cpu, &left);
    CPU_SET(first_cpu, &right);
    CPU_SET(boundary_cpu, &right);
    CPU_SET(last_cpu, &right);
    check(CPU_EQUAL(&left, &right), "CPU_EQUAL matching cross-word bits");
    check(CPU_EQUAL_S(sizeof(left), &left, &right), "CPU_EQUAL_S matching bits");

    CPU_CLR(first_cpu, &right);
    check(!CPU_EQUAL(&left, &right), "CPU_EQUAL first-word difference");
    check(!CPU_EQUAL(&right, &left), "CPU_EQUAL reverse operands differ");
    CPU_SET(first_cpu, &right);
    CPU_CLR(last_cpu, &right);
    check(!CPU_EQUAL(&left, &right), "CPU_EQUAL final-word difference");
    check(!CPU_EQUAL_S(sizeof(left), &left, &right), "CPU_EQUAL_S final-word difference");
    check(CPU_EQUAL_S(word, &left, &right), "one-word prefix excludes final bit");
    check(CPU_EQUAL_S(2 * word, &left, &right), "two-word prefix excludes final bit");

    CPU_SET(last_cpu, &right);
    CPU_CLR(boundary_cpu, &right);
    check(CPU_EQUAL_S(word, &left, &right), "one-word prefix excludes second-word bit");
    check(!CPU_EQUAL_S(2 * word, &left, &right), "two-word prefix includes second-word bit");
    check(CPU_EQUAL_S(0, &left, &right), "zero-word prefix compares no words");
    check(!CPU_EQUAL_S(sizeof(left), &left, &right), "full-size comparison includes difference");

    if (failures)
        return 1;
    printf("PASS ihk affinity equality: %u checks\n", checks);
    return 0;
}
