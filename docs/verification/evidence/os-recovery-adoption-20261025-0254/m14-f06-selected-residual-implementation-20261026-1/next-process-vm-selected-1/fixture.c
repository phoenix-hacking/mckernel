/* Functional McKernel OS/apps and Rust/assembly migration only; no security testing.
 * Original C and exact existing Rust adapter share one controlled provider.
 * No privileged instruction is executed by this fixture.
 */
#include <ihk/cpu.h>

_Static_assert(sizeof(enum ihk_asr_type) == 4, "genuine register enum must be32bits");
_Static_assert(sizeof(int) == 4, "C int ABI must be32bits");
_Static_assert(sizeof(unsigned long) == 8, "C value ABI must be64bits");

extern int puts(const char *);
static unsigned int calls;
static unsigned int seen_type;
static unsigned long seen_value;
static int provider_result;

int ihk_mc_arch_set_special_register(enum ihk_asr_type type, unsigned long value)
{
    ++calls;
    seen_type = (unsigned int)type;
    seen_value = value;
    return provider_result;
}

#define arch_prctl_set_register_bridge original_arch_prctl_set_register_bridge
#include "original_bridge.inc"
#undef arch_prctl_set_register_bridge
extern int arch_prctl_set_register_bridge(int, unsigned long);

int main(void)
{
    const int types[] = {0, 1, -1, 2, 3, 7, 255, 256, 65535, 65536,
                         0x7fffffff, (-2147483647 - 1), -65536};
    const unsigned long values[] = {0, 1, 0xffffffffUL, 0x100000000UL,
        0x8000000000000000UL, 0xffffffffffffffffUL,
        0x123456789abcdef0UL, 0xaaaaaaaa55555555UL};
    const int results[] = {0, -22, -14, -1, 1, 0x7fffffff, (-2147483647 - 1)};
    unsigned int i, j, k;
    unsigned long cases = 0;
    for (i = 0; i < sizeof(types) / sizeof(types[0]); ++i) {
        for (j = 0; j < sizeof(values) / sizeof(values[0]); ++j) {
            for (k = 0; k < sizeof(results) / sizeof(results[0]); ++k) {
                unsigned int original_calls, original_type;
                unsigned long original_value;
                int original_result, rust_result;
                provider_result = results[k];
                calls = 0;
                original_result = original_arch_prctl_set_register_bridge(types[i], values[j]);
                original_calls = calls;
                original_type = seen_type;
                original_value = seen_value;
                calls = 0;
                rust_result = arch_prctl_set_register_bridge(types[i], values[j]);
                if (original_calls != 1 || calls != 1 || original_type != seen_type
                    || seen_type != (unsigned int)types[i] || original_value != seen_value
                    || seen_value != values[j] || original_result != rust_result
                    || rust_result != results[k]) {
                    puts("FAIL prctl set-register adapter parity");
                    return 1;
                }
                ++cases;
            }
        }
    }
    if (cases != 728) {
        puts("FAIL case cardinality");
        return 2;
    }
    puts("PASS prctl set-register adapter parity728");
    return 0;
}
